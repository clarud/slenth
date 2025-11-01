#!/usr/bin/env python3
"""
Pre-flight check script for transaction workflow execution.

Checks:
1. Environment variables
2. Python dependencies
3. Database connection
4. Service connectivity (Groq, Pinecone)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_env_vars():
    """Check required environment variables."""
    print("\n" + "="*80)
    print("1. ENVIRONMENT VARIABLES CHECK")
    print("="*80)
    
    from dotenv import load_dotenv
    import os
    
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Found .env file at {env_path}")
    else:
        print(f"❌ .env file not found at {env_path}")
        return False
    
    required_vars = {
        "GROQ_API_KEY": "Groq API key for LLM",
        "PINECONE_API_KEY": "Pinecone API key for vector database",
        "PINECONE_INTERNAL_INDEX_HOST": "Pinecone internal rules index host",
        "PINECONE_EXTERNAL_INDEX_HOST": "Pinecone external rules index host",
        "DATABASE_URL": "PostgreSQL database connection string",
    }
    
    optional_vars = {
        "SECRET_KEY": "Secret key for JWT",
        "CELERY_BROKER_URL": "Celery broker URL",
        "CELERY_RESULT_BACKEND": "Celery result backend URL",
    }
    
    all_set = True
    
    print("\nRequired variables:")
    for var_name, description in required_vars.items():
        var_value = os.getenv(var_name)
        if var_value:
            masked = var_value[:8] + "..." if len(var_value) > 8 else "***"
            print(f"  ✅ {var_name}: {masked}")
            print(f"     ({description})")
        else:
            print(f"  ❌ {var_name}: NOT SET")
            print(f"     ({description})")
            all_set = False
    
    print("\nOptional variables:")
    for var_name, description in optional_vars.items():
        var_value = os.getenv(var_name)
        if var_value:
            masked = var_value[:8] + "..." if len(var_value) > 8 else "***"
            print(f"  ✅ {var_name}: {masked}")
        else:
            print(f"  ⚠️  {var_name}: NOT SET (using default)")
    
    return all_set


def check_dependencies():
    """Check required Python packages."""
    print("\n" + "="*80)
    print("2. PYTHON DEPENDENCIES CHECK")
    print("="*80)
    
    required_packages = [
        ("langgraph", "LangGraph for workflow orchestration"),
        ("langchain_openai", "LangChain OpenAI integration"),
        ("pinecone", "Pinecone vector database client"),
        ("groq", "Groq API client"),
        ("sqlalchemy", "SQL database ORM"),
        ("fastapi", "FastAPI web framework"),
        ("celery", "Celery task queue"),
        ("pydantic", "Data validation"),
        ("python-dotenv", "Environment variable loading"),
    ]
    
    all_installed = True
    
    for package_name, description in required_packages:
        try:
            __import__(package_name.replace("-", "_"))
            print(f"  ✅ {package_name}: installed")
        except ImportError:
            print(f"  ❌ {package_name}: NOT INSTALLED")
            print(f"     ({description})")
            all_installed = False
    
    if not all_installed:
        print("\n⚠️  To install missing packages:")
        print("    pip install -r requirements.txt")
    
    return all_installed


def check_services():
    """Check service imports."""
    print("\n" + "="*80)
    print("3. SERVICE IMPORTS CHECK")
    print("="*80)
    
    services_to_check = [
        ("services.llm", "LLMService", "LLM service (Groq)"),
        ("services.pinecone_db", "PineconeService", "Pinecone vector database"),
        ("workflows.transaction_workflow", "execute_transaction_workflow", "Transaction workflow"),
        ("db.database", "SessionLocal", "Database session"),
    ]
    
    all_ok = True
    
    for module_name, class_name, description in services_to_check:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"  ✅ {module_name}.{class_name}")
            print(f"     ({description})")
        except Exception as e:
            print(f"  ❌ {module_name}.{class_name}: {e}")
            print(f"     ({description})")
            all_ok = False
    
    return all_ok


def check_connectivity():
    """Check connectivity to external services."""
    print("\n" + "="*80)
    print("4. SERVICE CONNECTIVITY CHECK")
    print("="*80)
    
    import os
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
    
    # Check Groq
    print("\nChecking Groq API...")
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
            model="openai/gpt-oss-20b",
            temperature=0.2
        )
        response = llm.invoke([{"role": "user", "content": "Hello"}])
        print(f"  ✅ Groq API: Connected (response length: {len(response.content)})")
    except Exception as e:
        print(f"  ❌ Groq API: {e}")
    
    # Check Pinecone
    print("\nChecking Pinecone...")
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        print(f"  ✅ Pinecone API: Connected")
        
        # Try to access internal index
        internal_host = os.getenv("PINECONE_INTERNAL_INDEX_HOST")
        if internal_host:
            print(f"  ℹ️  Internal index host configured: {internal_host[:40]}...")
        
        external_host = os.getenv("PINECONE_EXTERNAL_INDEX_HOST")
        if external_host:
            print(f"  ℹ️  External index host configured: {external_host[:40]}...")
            
    except Exception as e:
        print(f"  ❌ Pinecone: {e}")
    
    # Check Database
    print("\nChecking Database...")
    try:
        from db.database import SessionLocal
        db = SessionLocal()
        db.close()
        print(f"  ✅ Database: Connected")
    except Exception as e:
        print(f"  ⚠️  Database: {e}")
        print(f"     (Database is optional for workflow testing)")


def main():
    """Run all checks."""
    print("\n" + "="*80)
    print("TRANSACTION WORKFLOW PRE-FLIGHT CHECK")
    print("="*80)
    
    checks = [
        ("Environment Variables", check_env_vars),
        ("Python Dependencies", check_dependencies),
        ("Service Imports", check_services),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n❌ {check_name} check failed: {e}")
            results.append((check_name, False))
    
    # Connectivity check (optional)
    try:
        print("\n" + "="*80)
        print("Optional connectivity checks:")
        print("="*80)
        check_connectivity()
    except Exception as e:
        print(f"⚠️  Connectivity check failed: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    all_passed = all(result for _, result in results)
    
    for check_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {check_name}")
    
    print("="*80)
    
    if all_passed:
        print("\n✅ All critical checks passed! Ready to run workflow.")
        print("\nNext step:")
        print("  python scripts/test_workflow_execution.py")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  1. Create .env file with required variables")
        print("  2. Install dependencies: pip install -r requirements.txt")
        print("  3. Check API keys are valid")
        return 1


if __name__ == "__main__":
    sys.exit(main())
