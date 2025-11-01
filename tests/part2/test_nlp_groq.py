"""
Test NLPValidationAgent with REAL Groq LLM

Tests semantic validation using Groq for fast inference
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    loaded = load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path} (success={loaded})")
    
    # Debug: Check if key is loaded
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print(f"✅ GROQ_API_KEY loaded: {groq_key[:20]}...")
    else:
        print("⚠️  GROQ_API_KEY not found in environment after loading")
except ImportError:
    print("⚠️  python-dotenv not installed")

# Set ALL required env vars (fallbacks)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5432/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test')

# Import directly without going through services/__init__.py
import importlib.util

# Load groq_llm module directly
groq_spec = importlib.util.spec_from_file_location(
    "groq_llm",
    str(Path(__file__).parent.parent.parent / "services" / "groq_llm.py")
)
groq_module = importlib.util.module_from_spec(groq_spec)
groq_spec.loader.exec_module(groq_module)
GroqLLMService = groq_module.GroqLLMService

# Load nlp_validation agent directly
nlp_spec = importlib.util.spec_from_file_location(
    "nlp_validation",
    str(Path(__file__).parent.parent.parent / "agents" / "part2" / "nlp_validation.py")
)
nlp_module = importlib.util.module_from_spec(nlp_spec)
nlp_spec.loader.exec_module(nlp_module)
NLPValidationAgent = nlp_module.NLPValidationAgent


async def test_with_groq():
    """Test NLPValidationAgent with Groq LLM"""
    
    print("=" * 80)
    print("🤖 NLP VALIDATION - GROQ LLM TEST")
    print("=" * 80)
    print()
    
    # Initialize Groq LLM service
    try:
        groq_service = GroqLLMService()
        print(f"✅ Groq LLM service initialized")
        print(f"   Model: {groq_service.default_model}")
        print()
    except ValueError as e:
        print(f"❌ ERROR: {e}")
        print("   Please set GROQ_API_KEY in .env file")
        return
    
    # Initialize agent with LLM
    agent = NLPValidationAgent(llm_service=groq_service)
    
    # Test Case 1: Contradictory Purchase Agreement
    print("-" * 80)
    print("Test 1: Contradictory Purchase Agreement")
    print("-" * 80)
    
    contradictory_text = """
    Purchase Agreement
    
    Buyer: John Doe
    Seller: Jane Smith
    Property: 123 Main Street
    Sale Price: $500,000
    
    The buyer agrees to purchase the property for $500,000.
    However, the final agreed price is $450,000.
    
    Signed on: March 15, 2024
    Effective Date: March 1, 2024
    
    The buyer John Doe agrees to all terms.
    The buyer disagrees with the payment schedule.
    """
    
    state1 = {
        "ocr_text": contradictory_text,
        "document_type": "purchase_agreement",
        "extracted_entities": {
            "dates": ["March 15, 2024", "March 1, 2024"],
            "amounts": ["$500,000", "$450,000"]
        },
        "errors": []
    }
    
    result1 = await agent.execute(state1)
    
    print(f"✅ NLP Valid: {result1['nlp_valid']}")
    print(f"📊 Consistency Score: {result1['consistency_score']}/100")
    print(f"⚠️  Contradictions: {len(result1['contradictions'])}")
    
    if result1['contradictions']:
        print("\n🚨 Contradictions Found:")
        for i, contradiction in enumerate(result1['contradictions'], 1):
            print(f"   {i}. [{contradiction.get('severity', 'N/A')}] {contradiction.get('type', 'N/A')}")
            print(f"      {contradiction.get('description', 'N/A')}")
    
    if result1['timeline_issues']:
        print(f"\n📅 Timeline Issues: {len(result1['timeline_issues'])}")
        for issue in result1['timeline_issues']:
            print(f"   - {issue.get('description', 'N/A')}")
    
    print()
    
    # Test Case 2: Clean Purchase Agreement
    print("-" * 80)
    print("Test 2: Clean Purchase Agreement")
    print("-" * 80)
    
    clean_text = """
    Purchase Agreement
    
    Buyer: John Doe
    Seller: Jane Smith
    Property: 123 Main Street, New York, NY
    Sale Price: $500,000 (Five Hundred Thousand Dollars)
    
    The buyer agrees to purchase the property for $500,000.
    Payment terms: 20% down payment, remainder financed.
    
    Inspection Date: March 1, 2024
    Closing Date: March 15, 2024
    
    Both parties agree to all terms stated herein.
    
    Signed: March 1, 2024
    
    Buyer Signature: ________________
    Seller Signature: ________________
    """
    
    state2 = {
        "ocr_text": clean_text,
        "document_type": "purchase_agreement",
        "extracted_entities": {
            "dates": ["March 1, 2024", "March 15, 2024"],
            "amounts": ["$500,000"]
        },
        "errors": []
    }
    
    result2 = await agent.execute(state2)
    
    print(f"✅ NLP Valid: {result2['nlp_valid']}")
    print(f"📊 Consistency Score: {result2['consistency_score']}/100")
    print(f"⚠️  Contradictions: {len(result2['contradictions'])}")
    print(f"📋 Total Issues: {len(result2.get('semantic_issues', []))}")
    
    if result2.get('semantic_issues'):
        print("\n📋 Issues Found:")
        for issue in result2['semantic_issues']:
            print(f"   - [{issue.get('severity', 'N/A')}] {issue.get('description', 'N/A')}")
    
    print()
    
    # Test Case 3: Invoice with Calculation Error
    print("-" * 80)
    print("Test 3: Invoice with Calculation Errors")
    print("-" * 80)
    
    invoice_text = """
    INVOICE #12345
    Date: October 30, 2024
    
    Bill To: ABC Corporation
    
    Items:
    1. Widget A - Qty: 10 @ $50 each = $500
    2. Widget B - Qty: 5 @ $100 each = $500
    3. Widget C - Qty: 2 @ $200 each = $400
    
    Subtotal: $1,400
    Tax (10%): $140
    Total: $1,650
    
    However, the agreed total is $1,540.
    
    Payment due: November 15, 2024
    """
    
    state3 = {
        "ocr_text": invoice_text,
        "document_type": "invoice",
        "extracted_entities": {
            "dates": ["October 30, 2024", "November 15, 2024"],
            "amounts": ["$50", "$100", "$200", "$500", "$400", "$1,400", "$140", "$1,650", "$1,540"]
        },
        "errors": []
    }
    
    result3 = await agent.execute(state3)
    
    print(f"✅ NLP Valid: {result3['nlp_valid']}")
    print(f"📊 Consistency Score: {result3['consistency_score']}/100")
    print(f"⚠️  Contradictions: {len(result3['contradictions'])}")
    
    if result3.get('semantic_issues'):
        print(f"\n📋 Semantic Issues: {len(result3['semantic_issues'])}")
        for issue in result3['semantic_issues']:
            # Handle both dict and string issues
            if isinstance(issue, dict):
                print(f"   - [{issue.get('severity', 'N/A')}] {issue.get('type', 'N/A')}: {issue.get('description', 'N/A')}")
            else:
                print(f"   - {issue}")
    
    print()
    
    # Summary
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print()
    print(f"Test 1 (Contradictory): {'✅ PASS' if not result1['nlp_valid'] else '❌ FAIL'} (Should detect contradictions)")
    print(f"Test 2 (Clean): {'✅ PASS' if result2['nlp_valid'] else '❌ FAIL'} (Should be valid)")
    print(f"Test 3 (Calculation Error): {'✅ PASS' if not result3['nlp_valid'] else '❌ FAIL'} (Should detect errors)")
    print()
    
    print("🎯 NLP Validation Agent with Groq LLM - Tests Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_with_groq())
