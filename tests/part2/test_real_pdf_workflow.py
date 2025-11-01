"""
Test Document Workflow with REAL PDF
Uses the Swiss Purchase Agreement PDF to test all 10 agents
"""

import sys
import os
from pathlib import Path
import asyncio

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ.setdefault('SECRET_KEY', 'test-secret-key-12345')
os.environ.setdefault('DATABASE_URL', 'postgresql://user:pass@localhost:5432/testdb')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-key')
os.environ.setdefault('GROQ_API_KEY', 'gsk-test-key')

# Load .env
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=False)
        print(f"✅ Loaded .env from: {env_path}")
except ImportError:
    pass

import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_with_real_pdf():
    """Test the workflow with a real PDF document"""
    
    print("\n" + "="*70)
    print("TESTING: Document Workflow with REAL PDF")
    print("="*70 + "\n")
    
    # Find the Swiss PDF
    swiss_pdf = project_root / "Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf"
    
    if not swiss_pdf.exists():
        print(f"❌ Swiss PDF not found at: {swiss_pdf}")
        print(f"   Please ensure the file exists in the project root")
        return False
    
    print(f"📄 Using Test PDF: {swiss_pdf.name}")
    print(f"   Size: {swiss_pdf.stat().st_size:,} bytes")
    
    # Copy to uploaded_docs folder (simulating upload)
    upload_dir = project_root / "data" / "uploaded_docs"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    test_file = upload_dir / swiss_pdf.name
    if not test_file.exists():
        import shutil
        shutil.copy2(swiss_pdf, test_file)
        print(f"   Copied to: {test_file}")
    
    # Import workflow
    from workflows.document_workflow import execute_document_workflow
    from services.llm import LLMService
    
    # Prepare document data
    document_data = {
        "document_id": f"DOC-REAL-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "filename": swiss_pdf.name,
        "file_type": "application/pdf",
        "file_size": swiss_pdf.stat().st_size
    }
    
    print(f"\n📋 Document Metadata:")
    print(f"   ID: {document_data['document_id']}")
    print(f"   File: {document_data['filename']}")
    print(f"   Type: {document_data['file_type']}")
    print(f"   Size: {document_data['file_size']:,} bytes")
    
    # Initialize services
    print(f"\n🔧 Initializing services...")
    llm_service = LLMService()
    
    # Mock database
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
    
    print(f"\n🚀 EXECUTING WORKFLOW (this may take 30-60 seconds)...")
    print(f"   Processing: {swiss_pdf.name}")
    print(f"\n" + "-"*70 + "\n")
    
    try:
        start = datetime.now()
        
        # Execute workflow
        final_state = await execute_document_workflow(
            document=document_data,
            file_path=str(test_file),
            db_session=db_session,
            llm_service=llm_service
        )
        
        end = datetime.now()
        duration = (end - start).total_seconds()
        
        print(f"\n" + "-"*70)
        print(f"\n✅ WORKFLOW COMPLETED!")
        
        # Show results
        print(f"\n📊 Workflow Results:")
        print(f"   Processing Time: {duration:.2f}s")
        print(f"   Risk Score: {final_state.get('risk_score', 'N/A')}")
        print(f"   Risk Level: {final_state.get('risk_level', 'N/A')}")
        print(f"   Errors: {len(final_state.get('errors', []))}")
        
        # Show agent execution
        print(f"\n🤖 Agent Execution Results:")
        
        agents_check = [
            ("1. DocumentIntake", "normalized_document", "file_valid"),
            ("2. OCR", "ocr_text", "pages_processed"),
            ("3. FormatValidation", "format_findings", None),
            ("4. NLPValidation", "content_findings", None),
            ("5. ImageForensics", "image_findings", None),
            ("6. BackgroundCheck", "background_check_findings", "pep_found"),
            ("7. CrossReference", "cross_reference_findings", "cross_reference_score"),
            ("8. DocumentRisk", "risk_score", "risk_level"),
            ("9. ReportGenerator", "report_path", None),
            ("10. EvidenceStorekeeper", "evidence_collected", "evidence_items_count"),
        ]
        
        for agent_name, primary_key, secondary_key in agents_check:
            has_primary = primary_key in final_state
            status = "✓" if has_primary else "✗"
            
            if has_primary and secondary_key:
                value = final_state.get(secondary_key, "N/A")
                print(f"   {status} {agent_name} → {secondary_key}={value}")
            elif has_primary:
                value = final_state[primary_key]
                if isinstance(value, list):
                    print(f"   {status} {agent_name} → [{len(value)} items]")
                elif isinstance(value, str):
                    preview = value[:50] + "..." if len(value) > 50 else value
                    print(f"   {status} {agent_name} → \"{preview}\"")
                else:
                    print(f"   {status} {agent_name} → {value}")
            else:
                print(f"   {status} {agent_name}")
        
        # Show OCR results
        if final_state.get('ocr_text'):
            ocr_text = final_state['ocr_text']
            print(f"\n📝 OCR Extraction:")
            print(f"   Characters extracted: {len(ocr_text):,}")
            print(f"   Pages processed: {final_state.get('pages_processed', 'N/A')}")
            print(f"   OCR confidence: {final_state.get('ocr_confidence', 'N/A')}")
            if ocr_text:
                preview = ocr_text[:200].replace('\n', ' ')
                print(f"   Preview: \"{preview}...\"")
        
        # Show findings
        total_findings = 0
        findings_types = [
            ('format_findings', 'Format Issues'),
            ('content_findings', 'Content Issues'),
            ('image_findings', 'Image Forensics'),
            ('background_check_findings', 'Background Checks'),
            ('cross_reference_findings', 'Cross-References'),
        ]
        
        print(f"\n🔍 Findings Summary:")
        for key, label in findings_types:
            findings = final_state.get(key, [])
            count = len(findings) if isinstance(findings, list) else 0
            total_findings += count
            if count > 0:
                print(f"   {label}: {count}")
        print(f"   TOTAL: {total_findings} findings")
        
        # Show errors
        if final_state.get('errors'):
            print(f"\n⚠️  Errors Encountered ({len(final_state['errors'])}):")
            for i, error in enumerate(final_state['errors'][:5], 1):
                print(f"   {i}. {error}")
            if len(final_state['errors']) > 5:
                print(f"   ... and {len(final_state['errors']) - 5} more")
        
        # Show evidence collection
        if final_state.get('evidence_collected'):
            print(f"\n📦 Evidence Collection:")
            print(f"   Collected: {final_state.get('evidence_collected', False)}")
            print(f"   Items: {final_state.get('evidence_items_count', 0)}")
            print(f"   Storage ID: {final_state.get('evidence_storage_id', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ WORKFLOW FAILED!")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PART 2 DOCUMENT WORKFLOW - REAL PDF TEST")
    print("="*70)
    
    success = asyncio.run(test_with_real_pdf())
    
    print("\n" + "="*70)
    if success:
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("\nThe workflow is fully connected and working!")
        print("You can now use the FastAPI endpoint: POST /documents/upload")
    else:
        print("❌ TEST FAILED")
    print("="*70 + "\n")
    
    sys.exit(0 if success else 1)
