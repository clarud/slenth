"""
Direct Workflow Test - Test the 10-agent workflow WITHOUT FastAPI server

This script demonstrates:
1. How the workflow is triggered
2. Which 10 agents are executed
3. How to test without running the server
"""

import sys
import os
from pathlib import Path
import asyncio

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables BEFORE importing config
os.environ.setdefault('SECRET_KEY', 'test-secret-key-12345')
os.environ.setdefault('DATABASE_URL', 'postgresql://user:pass@localhost:5432/testdb')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-key')
os.environ.setdefault('GROQ_API_KEY', 'gsk-test-key')

# Load .env if exists
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=False)
        print(f"✅ Loaded .env from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed, using defaults")

import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_workflow_trigger():
    """
    Test the workflow trigger WITHOUT FastAPI server.
    
    This demonstrates what happens when you POST to /documents/upload
    """
    
    print("\n" + "="*70)
    print("TESTING: Document Workflow (10 Agents)")
    print("="*70 + "\n")
    
    # Import the workflow function (this is what the endpoint calls)
    from workflows.document_workflow import execute_document_workflow
    from services.llm import LLMService
    
    # Create a test document (simulating uploaded file)
    test_file = project_root / "data" / "uploaded_docs" / "test_document.pdf"
    
    # If test file doesn't exist, create a placeholder
    if not test_file.exists():
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"%PDF-1.4\nTest PDF content")
        print(f"📄 Created test file: {test_file}")
    
    # Prepare document metadata (simulating API request data)
    document_data = {
        "document_id": f"DOC-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "filename": "test_document.pdf",
        "file_type": "application/pdf",
        "file_size": test_file.stat().st_size if test_file.exists() else 0
    }
    
    print(f"\n📋 Document Metadata:")
    print(f"   ID: {document_data['document_id']}")
    print(f"   File: {document_data['filename']}")
    print(f"   Type: {document_data['file_type']}")
    print(f"   Size: {document_data['file_size']} bytes")
    
    # Initialize services
    print(f"\n🔧 Initializing services...")
    llm_service = LLMService()
    
    # Mock database session (for testing without real DB)
    class MockDB:
        def __init__(self):
            self.committed = False
        def commit(self):
            self.committed = True
        def rollback(self):
            pass
        def add(self, obj):
            pass
        def refresh(self, obj):
            pass
    
    db_session = MockDB()
    
    print(f"\n🚀 TRIGGERING WORKFLOW...")
    print(f"   This is what happens when you POST to /documents/upload")
    print(f"\n" + "-"*70)
    
    try:
        # THIS IS THE KEY LINE - This triggers all 10 agents
        final_state = await execute_document_workflow(
            document=document_data,
            file_path=str(test_file),
            db_session=db_session,
            llm_service=llm_service
        )
        
        print(f"\n" + "-"*70)
        print(f"\n✅ WORKFLOW COMPLETED!")
        
        # Show results
        print(f"\n📊 Workflow Results:")
        print(f"   Processing Time: {final_state.get('processing_end_time', 0) - final_state.get('processing_start_time', 0):.2f}s")
        print(f"   Risk Score: {final_state.get('risk_score', 'N/A')}")
        print(f"   Risk Level: {final_state.get('risk_level', 'N/A')}")
        print(f"   Errors: {len(final_state.get('errors', []))}")
        
        # Show which agents executed
        print(f"\n🤖 Agents Executed:")
        agent_outputs = [
            ("1. DocumentIntake", "normalized_document"),
            ("2. OCR", "ocr_text"),
            ("3. FormatValidation", "format_findings"),
            ("4. NLPValidation", "content_findings"),
            ("5. ImageForensics", "image_findings"),
            ("6. BackgroundCheck", "background_check_findings"),
            ("7. CrossReference", "cross_reference_findings"),
            ("8. DocumentRisk", "risk_score"),
            ("9. ReportGenerator", "report_path"),
            ("10. EvidenceStorekeeper", "evidence_collected"),
        ]
        
        for agent_name, output_key in agent_outputs:
            has_output = output_key in final_state
            status = "✓" if has_output else "✗"
            print(f"   {status} {agent_name}")
        
        # Show detailed state
        print(f"\n📦 Final State Keys:")
        for key in sorted(final_state.keys()):
            value = final_state[key]
            if isinstance(value, (str, int, float, bool)):
                print(f"   - {key}: {value}")
            elif isinstance(value, list):
                print(f"   - {key}: [{len(value)} items]")
            elif isinstance(value, dict):
                print(f"   - {key}: {{{len(value)} keys}}")
            else:
                print(f"   - {key}: {type(value).__name__}")
        
        if final_state.get('errors'):
            print(f"\n⚠️  Errors encountered:")
            for error in final_state['errors']:
                print(f"   - {error}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ WORKFLOW FAILED!")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def explain_workflow():
    """Explain how the workflow is triggered"""
    
    print("\n" + "="*70)
    print("EXPLANATION: How the 10-Agent Workflow is Triggered")
    print("="*70 + "\n")
    
    print("📍 When you POST to /documents/upload:")
    print()
    print("   1. FastAPI endpoint: app/api/documents.py:upload_document()")
    print("      ↓")
    print("   2. Saves file to: data/uploaded_docs/")
    print("      ↓")
    print("   3. Creates Document record in database")
    print("      ↓")
    print("   4. Calls: execute_document_workflow()")
    print("      ↓")
    print("   5. LangGraph executes 10 agents in sequence:")
    print()
    print("      Agent 1:  DocumentIntake      - Validate file format")
    print("      Agent 2:  OCR                 - Extract text from images/PDFs")
    print("      Agent 3:  FormatValidation    - Check document structure")
    print("      Agent 4:  NLPValidation       - Semantic content validation")
    print("      Agent 5:  ImageForensics      - Detect tampering")
    print("      Agent 6:  BackgroundCheck     - World-Check API screening")
    print("      Agent 7:  CrossReference      - Compare with transaction history")
    print("      Agent 8:  DocumentRisk        - Calculate risk score")
    print("      Agent 9:  ReportGenerator     - Create PDF report")
    print("      Agent 10: EvidenceStorekeeper - Save findings to database")
    print()
    print("   6. Returns complete results to API endpoint")
    print("      ↓")
    print("   7. Updates Document record with risk assessment")
    print("      ↓")
    print("   8. Returns JSON response to client")
    print()
    print("💡 The workflow is defined in: workflows/document_workflow.py")
    print("💡 Each agent is in: agents/part2/")
    print()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PART 2 DOCUMENT WORKFLOW - DIRECT TEST")
    print("="*70)
    
    # Explain first
    explain_workflow()
    
    # Then test
    success = asyncio.run(test_workflow_trigger())
    
    print("\n" + "="*70)
    if success:
        print("✅ TEST COMPLETED SUCCESSFULLY")
    else:
        print("❌ TEST FAILED")
    print("="*70 + "\n")
    
    sys.exit(0 if success else 1)
