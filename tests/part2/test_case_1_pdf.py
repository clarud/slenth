"""
Test Case 1: Complete Workflow for PDF Format
Tests all agents with Swiss_Home_Purchase_Agreement.pdf
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file FIRST (to get API keys)
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    loaded = load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed")

# Set required env vars (only if not already set by .env)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5432/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test')
os.environ.setdefault('MAX_UPLOAD_SIZE_MB', '50')
os.environ.setdefault('OCR_OUTPUT_DIR', 'data/ocr_output')
# DON'T set CORS_ORIGINS - it has a default value in config.py

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import agents and services using importlib to avoid config loading issues
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load all agents using importlib
groq_module = load_module("groq_llm", project_root / "services" / "groq_llm.py")
GroqLLMService = groq_module.GroqLLMService

intake_module = load_module("document_intake", project_root / "agents" / "part2" / "document_intake.py")
DocumentIntakeAgent = intake_module.DocumentIntakeAgent

ocr_module = load_module("ocr", project_root / "agents" / "part2" / "ocr.py")
OCRAgent = ocr_module.OCRAgent

bg_module = load_module("background_check", project_root / "agents" / "part2" / "background_check.py")
BackgroundCheckAgent = bg_module.BackgroundCheckAgent

format_module = load_module("format_validation", project_root / "agents" / "part2" / "format_validation.py")
FormatValidationAgent = format_module.FormatValidationAgent

nlp_module = load_module("nlp_validation", project_root / "agents" / "part2" / "nlp_validation.py")
NLPValidationAgent = nlp_module.NLPValidationAgent

pdf_module = load_module("pdf_forensics", project_root / "agents" / "part2" / "pdf_forensics.py")
PDFForensicsAgent = pdf_module.PDFForensicsAgent

image_module = load_module("image_forensics", project_root / "agents" / "part2" / "image_forensics.py")
ImageForensicsAgent = image_module.ImageForensicsAgent

risk_module = load_module("document_risk", project_root / "agents" / "part2" / "document_risk.py")
DocumentRiskAgent = risk_module.DocumentRiskAgent


async def test_pdf_workflow():
    """Test complete workflow with PDF document"""
    
    print("\n" + "="*80)
    print("🧪 TEST CASE 1: PDF WORKFLOW")
    print("="*80)
    print("\n📄 Document: Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf")
    print("🔬 Format: PDF")
    print("⚙️  Mode: Full Production Workflow")
    print()
    
    # File path
    file_path = str(project_root / "Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf")
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return
    
    # Initialize state
    state = {
        "file_path": file_path,
        "document_id": f"test_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "document": {"document_type": "purchase_agreement"}
    }
    
    try:
        # Initialize LLM service
        llm_service = GroqLLMService()
        
        # 1. Document Intake
        print("1️⃣  DOCUMENT INTAKE AGENT")
        print("-" * 80)
        intake_agent = DocumentIntakeAgent()
        state = await intake_agent.execute(state)
        print(f"✅ Valid: {state['file_valid']}")
        print(f"📄 Format: {state.get('file_format', 'N/A').upper()}")
        print(f"📊 Pages: {state.get('metadata', {}).get('page_count', 'N/A')}")
        print(f"💾 Size: {state.get('metadata', {}).get('file_size_mb', 0):.2f} MB")
        
        if not state['file_valid']:
            print(f"❌ Validation failed: {state.get('errors')}")
            return
        
        # 2. OCR Agent
        print(f"\n2️⃣  OCR AGENT")
        print("-" * 80)
        ocr_agent = OCRAgent()
        state = await ocr_agent.execute(state)
        print(f"✅ Text Extracted: {state['has_text']}")
        print(f"📝 Characters: {state['text_length']}")
        print(f"📄 Pages: {len(state.get('page_texts', []))}")
        
        # 3. Background Check
        print(f"\n3️⃣  BACKGROUND CHECK AGENT")
        print("-" * 80)
        bg_agent = BackgroundCheckAgent()
        state = await bg_agent.execute(state)
        print(f"👥 Entities Screened: {len(state.get('screened_entities', []))}")
        print(f"🚨 PEP Found: {state.get('pep_found', False)}")
        print(f"⚠️  Sanctions: {state.get('sanctions_found', False)}")
        print(f"📊 Risk Score: {state.get('background_risk_score', 0)}/100")
        
        # 4. Format Validation
        print(f"\n4️⃣  FORMAT VALIDATION AGENT")
        print("-" * 80)
        format_agent = FormatValidationAgent()
        state = await format_agent.execute(state)
        print(f"✅ Valid: {state.get('format_valid', False)}")
        print(f"📊 Quality Score: {state.get('format_quality_score', 0)}/100")
        print(f"📊 Completeness: {state.get('completeness_score', 0)}/100")
        print(f"📝 Spelling Errors: {state.get('spelling_errors', 0)}")
        
        # 5. NLP Validation
        print(f"\n5️⃣  NLP VALIDATION AGENT")
        print("-" * 80)
        nlp_agent = NLPValidationAgent(llm_service=llm_service)
        state = await nlp_agent.execute(state)
        print(f"✅ Valid: {state.get('nlp_valid', False)}")
        print(f"📊 Consistency Score: {state.get('consistency_score', 0)}/100")
        print(f"⚠️  Contradictions: {len(state.get('contradictions', []))}")
        
        # 6. PDF Forensics (PDF-specific)
        print(f"\n6️⃣  PDF FORENSICS AGENT")
        print("-" * 80)
        pdf_agent = PDFForensicsAgent()
        state = await pdf_agent.execute(state)
        print(f"✅ Tampering Detected: {state.get('tampering_detected', False)}")
        print(f"📊 Integrity Score: {state.get('integrity_score', 0)}/100")
        print(f"🛠️  Software Trust: {state.get('software_trust_level', 'unknown').upper()}")
        print(f"⚠️  Indicators: {len(state.get('tampering_indicators', []))}")
        
        # 7. Image Forensics
        print(f"\n7️⃣  IMAGE FORENSICS AGENT")
        print("-" * 80)
        image_agent = ImageForensicsAgent(llm_service=None)
        state = await image_agent.execute(state)
        print(f"🖼️  Images Analyzed: {state.get('images_analyzed', 0)}")
        print(f"🤖 AI-Generated: {state.get('ai_generated_detected', False)}")
        print(f"✂️  Tampering: {state.get('image_tampering_detected', False)}")
        print(f"📊 Forensics Score: {state.get('image_forensics_score', 0)}/100")
        
        # 8. Document Risk Assessment
        print(f"\n8️⃣  DOCUMENT RISK AGENT")
        print("-" * 80)
        risk_agent = DocumentRiskAgent()
        state = await risk_agent.execute(state)
        print(f"📊 Overall Risk Score: {state.get('overall_risk_score', 0):.1f}/100")
        print(f"🚨 Risk Band: {state.get('risk_band', 'UNKNOWN')}")
        print(f"👁️  Manual Review Required: {state.get('requires_manual_review', False)}")
        print(f"⚠️  Risk Factors: {len(state.get('risk_factors', []))}")
        
        # Final Summary
        print(f"\n{'='*80}")
        print(f"✅ PDF WORKFLOW TEST COMPLETE")
        print(f"{'='*80}")
        print(f"\n📊 RESULTS SUMMARY:")
        print(f"   Format: PDF")
        print(f"   Valid: {state['file_valid']}")
        print(f"   OCR Success: {state['has_text']}")
        print(f"   Overall Risk: {state.get('overall_risk_score', 0):.1f}/100")
        print(f"   Risk Band: {state.get('risk_band', 'UNKNOWN')}")
        print(f"   Manual Review: {'YES' if state.get('requires_manual_review') else 'NO'}")
        print()
        
        return state
        
    except Exception as e:
        print(f"\n❌ Error in PDF workflow: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_pdf_workflow())
    
    if result:
        print("✅ Test Case 1 (PDF) - PASSED")
        sys.exit(0)
    else:
        print("❌ Test Case 1 (PDF) - FAILED")
        sys.exit(1)
