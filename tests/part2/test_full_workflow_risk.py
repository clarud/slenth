"""
Full Workflow Test - 6 Agents with Risk Assessment
Tests: DocumentIntake → OCR → FormatValidation → NLPValidation → PDFForensics → DocumentRisk
"""

import sys
import os
from pathlib import Path
import json

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set env vars BEFORE any imports that trigger config loading
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5432/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test')
os.environ.setdefault('MAX_UPLOAD_SIZE_MB', '50')
os.environ.setdefault('OCR_OUTPUT_DIR', 'data/ocr_output')
# CORS_ORIGINS must be valid JSON array string
os.environ.setdefault('CORS_ORIGINS', json.dumps(["http://localhost:3000"]))

# Load .env AFTER setting defaults
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    load_dotenv(env_path, override=False)  # Don't override our test defaults
except ImportError:
    pass

import asyncio

import logging
import fitz
import re
from datetime import datetime
from io import BytesIO

try:
    from PIL import Image
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import modules directly
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load all agents
llm_module = load_module("llm", project_root / "services" / "llm.py")
LLMService = llm_module.LLMService

background_module = load_module("background_check", project_root / "agents" / "part2" / "background_check.py")
BackgroundCheckAgent = background_module.BackgroundCheckAgent

format_module = load_module("format_validation", project_root / "agents" / "part2" / "format_validation.py")
FormatValidationAgent = format_module.FormatValidationAgent

nlp_module = load_module("nlp_validation", project_root / "agents" / "part2" / "nlp_validation.py")
NLPValidationAgent = nlp_module.NLPValidationAgent

pdf_module = load_module("pdf_forensics", project_root / "agents" / "part2" / "pdf_forensics.py")
PDFForensicsAgent = pdf_module.PDFForensicsAgent

image_module = load_module("image_forensics", project_root / "agents" / "part2" / "image_forensics.py")
ImageForensicsAgent = image_module.ImageForensicsAgent

cross_ref_module = load_module("cross_reference", project_root / "agents" / "part2" / "cross_reference.py")
CrossReferenceAgent = cross_ref_module.CrossReferenceAgent

risk_module = load_module("document_risk", project_root / "agents" / "part2" / "document_risk.py")
DocumentRiskAgent = risk_module.DocumentRiskAgent


class SimpleDocumentIntakeAgent:
    """Simple document intake for testing"""
    async def execute(self, state):
        logger.info("Executing DocumentIntakeAgent")
        file_path = state.get("file_path")
        
        if not os.path.exists(file_path):
            state["file_valid"] = False
            state["errors"] = ["File does not exist"]
            return state
        
        doc = fitz.open(file_path)
        metadata = {
            "file_name": Path(file_path).name,
            "file_size": os.path.getsize(file_path),
            "page_count": len(doc),
            "has_images": any(doc[i].get_images() for i in range(len(doc)))
        }
        doc.close()
        
        state["file_valid"] = True
        state["document_type"] = "purchase_agreement"
        state["metadata"] = metadata
        state["errors"] = []
        return state


class SimpleOCRAgent:
    """Simple OCR agent for testing"""
    def __init__(self):
        if EASYOCR_AVAILABLE:
            logger.info("Initializing EasyOCR...")
            self.reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR ready")
    
    async def execute(self, state):
        logger.info("Executing OCRAgent")
        file_path = state.get("file_path")
        
        doc = fitz.open(file_path)
        page_texts = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            
            if len(text.strip()) < 50 and page.get_images() and EASYOCR_AVAILABLE:
                logger.info(f"Running OCR on page {page_num + 1}")
                images = page.get_images()
                if images:
                    img = images[0]
                    xref = img[0]
                    base_image = page.parent.extract_image(xref)
                    image_bytes = base_image["image"]
                    image = Image.open(BytesIO(image_bytes))
                    
                    result = self.reader.readtext(image, detail=0)
                    text = "\n".join(result)
            
            page_texts.append({
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text)
            })
        
        doc.close()
        
        ocr_text = "\n\n".join([f"[Page {p['page_number']}]\n{p['text']}" for p in page_texts])
        
        entities = {
            "dates": re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', ocr_text)[:10],
            "amounts": re.findall(r'[\$£€]\s*[\d,]+\.?\d*', ocr_text)[:10],
            "emails": re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', ocr_text)[:10],
            "potential_names": re.findall(r'\b(?:Mr|Mrs|Ms|Dr)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', ocr_text)[:10]
        }
        
        state["ocr_text"] = ocr_text
        state["page_texts"] = page_texts
        state["text_length"] = len(ocr_text)
        state["has_text"] = len(ocr_text.strip()) > 100
        state["extracted_entities"] = entities
        
        return state


async def test_full_workflow_with_risk(pdf_path: str):
    """Run full 7-agent workflow on real PDF (includes Background Check)"""
    
    print("=" * 80)
    print("🧪 FULL WORKFLOW TEST - 9 Agents + Risk Assessment")
    print("=" * 80)
    print(f"\n📄 PDF: {pdf_path}")
    print(f"📁 Size: {Path(pdf_path).stat().st_size / 1024:.2f} KB\n")
    
    # Initialize LLM Service (Groq by default, or switch provider via config)
    try:
        llm_service = LLMService(provider="groq")  # Can be "openai", "anthropic", or "groq"
        print(f"✅ LLM initialized: {llm_service.provider.value} - {llm_service.model}\n")
    except Exception as e:
        print(f"⚠️  LLM not available: {e}\n")
        llm_service = None
    
    state = {
        "file_path": pdf_path,
        "document_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "document": {"document_type": "purchase_agreement"},
        "errors": []
    }
    
    # Agent 1: Document Intake
    print("=" * 80)
    print("1️⃣  DOCUMENT INTAKE")
    print("=" * 80)
    intake = SimpleDocumentIntakeAgent()
    state = await intake.execute(state)
    print(f"✅ Valid: {state['file_valid']}")
    print(f"📄 Type: {state['document_type']}")
    print(f"📊 Pages: {state['metadata']['page_count']}\n")
    
    if not state['file_valid']:
        return
    
    # Agent 2: OCR
    print("=" * 80)
    print("2️⃣  OCR")
    print("=" * 80)
    ocr = SimpleOCRAgent()
    state = await ocr.execute(state)
    print(f"✅ Text Extracted: {state['has_text']}")
    print(f"📝 Length: {state['text_length']:,} chars\n")
    
    # Agent 3: Background Check (Dilisense API)
    print("=" * 80)
    print("3️⃣  BACKGROUND CHECK (Dilisense API)")
    print("=" * 80)
    background_agent = BackgroundCheckAgent()
    state = await background_agent.execute(state)
    print(f"✅ Entities Screened: {len(state.get('background_check_results', []))}")
    print(f"⚠️  PEP Found: {state.get('pep_found', False)}")
    print(f"⚠️  Sanctions Found: {state.get('sanctions_found', False)}")
    print(f"📊 Background Risk Score: {state.get('background_risk_score', 0)}/100\n")
    
    # Agent 4: Format Validation
    print("=" * 80)
    print("4️⃣  FORMAT VALIDATION")
    print("=" * 80)
    format_agent = FormatValidationAgent()
    state = await format_agent.execute(state)
    print(f"✅ Format Valid: {state['format_valid']}")
    print(f"📊 Completeness Score: {state['completeness_score']}/100")
    print(f"🔤 Spelling Errors: {state['spelling_errors']}\n")
    
    # Agent 5: NLP Validation
    print("=" * 80)
    print("5️⃣  NLP VALIDATION (LLM)")
    print("=" * 80)
    nlp_agent = NLPValidationAgent(llm_service=llm_service)
    state = await nlp_agent.execute(state)
    print(f"✅ NLP Valid: {state['nlp_valid']}")
    print(f"📊 Consistency Score: {state['consistency_score']}/100")
    print(f"⚠️  Contradictions: {len(state.get('contradictions', []))}\n")
    
    # Agent 6: PDF Forensics
    print("=" * 80)
    print("6️⃣  PDF FORENSICS")
    print("=" * 80)
    pdf_agent = PDFForensicsAgent()
    state = await pdf_agent.execute(state)
    print(f"✅ Integrity Score: {state['integrity_score']}/100")
    print(f"⚠️  Tampering Detected: {state['tampering_detected']}")
    print(f"🛡️  Software Trust: {state['software_trust_level']}\n")
    
    # Agent 7: Image Forensics (with LLM)
    print("=" * 80)
    print("7️⃣  IMAGE FORENSICS (AI Detection & Tampering)")
    print("=" * 80)
    image_agent = ImageForensicsAgent(llm_service=llm_service)
    state = await image_agent.execute(state)
    print(f"🖼️  Images Analyzed: {state.get('images_analyzed', 0)}")
    if state.get('images_analyzed', 0) > 0:
        print(f"🤖 AI-Generated Detected: {state.get('ai_generated_detected', False)}")
        if state.get('ai_generated_detected'):
            print(f"   Confidence: {state.get('ai_detection_confidence', 0)}%")
        print(f"✂️  Image Tampering Detected: {state.get('image_tampering_detected', False)}")
        print(f"📊 Image Forensics Score: {state.get('image_forensics_score', 100)}/100")
        if state.get('exif_issues'):
            print(f"⚠️  EXIF Issues: {len(state.get('exif_issues', []))}")
    print()
    
    # Agent 8: Cross Reference (with LLM)
    print("=" * 80)
    print("8️⃣  CROSS REFERENCE")
    print("=" * 80)
    cross_ref_agent = CrossReferenceAgent(llm_service=llm_service)
    state = await cross_ref_agent.execute(state)
    print(f"✅ Consistency with Profile: {state.get('consistency_with_profile', 'N/A')}")
    print(f"📊 Cross-Reference Score: {state.get('cross_reference_score', 0)}/100")
    print(f"⚠️  Discrepancies Found: {len(state.get('discrepancies', []))}\n")
    
    # Agent 9: Document Risk
    print("=" * 80)
    print("8️⃣  DOCUMENT RISK ASSESSMENT")
    print("=" * 80)
    risk_agent = DocumentRiskAgent()
    state = await risk_agent.execute(state)
    
    print()
    print("=" * 80)
    print("🎯 FINAL RISK ASSESSMENT")
    print("=" * 80)
    print(f"\n📊 Overall Risk Score: {state['overall_risk_score']}/100")
    print(f"🚨 Risk Band: {state['risk_band']}")
    print(f"👁️  Manual Review Required: {'YES' if state['requires_manual_review'] else 'NO'}")
    
    print(f"\n📊 Component Scores:")
    for component, score in sorted(state['component_scores'].items()):
        print(f"   - {component:20s}: {score:.0f}/100")
    
    if state['risk_factors']:
        print(f"\n🚨 Risk Factors ({len(state['risk_factors'])}):")
        for factor in state['risk_factors']:
            severity = factor.get('severity', 'unknown').upper()
            risk_type = factor.get('type', 'unknown')
            description = factor.get('description', 'No description')
            print(f"   • [{severity}] {risk_type}: {description}")
    
    if state['recommendations']:
        print(f"\n💡 Recommendations ({len(state['recommendations'])}):")
        for rec in state['recommendations']:
            action = rec.get('action', 'unknown')
            description = rec.get('description', 'No description')
            print(f"   ✓ {action}: {description}")
    
    # Summary
    print()
    print("=" * 80)
    print("📊 WORKFLOW SUMMARY")
    print("=" * 80)
    print(f"\n✅ Agents Executed: 9/9")
    print(f"   1. DocumentIntake: {'✅ Pass' if state.get('file_valid') else '❌ Fail'}")
    print(f"   2. OCR: {'✅ Pass' if state.get('has_text') else '⚠️ Limited'}")
    print(f"   3. BackgroundCheck: {'✅ Pass' if not state.get('pep_found') and not state.get('sanctions_found') else '❌ Fail'}")
    print(f"   4. FormatValidation: {'✅ Pass' if state.get('format_valid') else '❌ Fail'}")
    print(f"   5. NLPValidation: {'✅ Pass' if state.get('nlp_valid') else '❌ Fail'}")
    print(f"   6. PDFForensics: {'✅ Pass' if state.get('integrity_score', 0) >= 70 else '❌ Fail'}")
    print(f"   7. ImageForensics: {'✅ Pass' if state.get('image_forensics_score', 100) >= 70 else '❌ Fail'}")
    print(f"   8. CrossReference: {'✅ Pass' if state.get('cross_reference_score', 100) >= 70 else '❌ Fail'}")
    print(f"   9. DocumentRisk: {state['risk_band']}")
    
    # Final verdict - considers both risk band AND manual review flag
    print()
    requires_review = state.get('requires_manual_review', False)
    
    if state['risk_band'] == "CRITICAL":
        print("🔴 VERDICT: ❌ REJECT - Critical risk detected")
    elif state['risk_band'] == "HIGH":
        print("🚨 VERDICT: ⛔ HOLD - Enhanced due diligence required")
    elif state['risk_band'] == "MEDIUM" or (state['risk_band'] == "LOW" and requires_review):
        print("⚠️  VERDICT: 📋 REVIEW REQUIRED - Manual verification needed")
    elif state['risk_band'] == "LOW" and not requires_review:
        print("🎉 VERDICT: ✅ ACCEPT - Document passes all checks")
    else:
        print("❓ VERDICT: ⚠️  UNKNOWN - Unable to determine risk")
    
    print()
    print("=" * 80)
    print("✅ WORKFLOW TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_full_workflow_risk.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    asyncio.run(test_full_workflow_with_risk(pdf_path))
