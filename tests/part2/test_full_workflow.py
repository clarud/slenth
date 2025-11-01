"""
Full Workflow Test - Real PDF Document
Tests: DocumentIntake → OCR → FormatValidation → NLPValidation (with Groq LLM)
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from io import BytesIO

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    loaded = load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed")

# Set required env vars
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5432/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test')
os.environ.setdefault('MAX_UPLOAD_SIZE_MB', '50')
os.environ.setdefault('OCR_OUTPUT_DIR', 'data/ocr_output')

import logging
import fitz
import re

try:
    from PIL import Image
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import agents and services using direct imports
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load GroqLLMService
groq_module = load_module("groq_llm", project_root / "services" / "groq_llm.py")
GroqLLMService = groq_module.GroqLLMService

# Load FormatValidationAgent
format_module = load_module("format_validation", project_root / "agents" / "part2" / "format_validation.py")
FormatValidationAgent = format_module.FormatValidationAgent

# Load NLPValidationAgent
nlp_module = load_module("nlp_validation", project_root / "agents" / "part2" / "nlp_validation.py")
NLPValidationAgent = nlp_module.NLPValidationAgent


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
                    logger.info(f"OCR extracted {len(text)} characters")
            
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


async def test_full_workflow(pdf_path: str):
    """Run full workflow on real PDF with all 4 agents"""
    
    print("=" * 80)
    print("🧪 FULL WORKFLOW TEST - Real PDF with Groq LLM")
    print("=" * 80)
    print(f"\n📄 PDF: {pdf_path}")
    print(f"📁 Size: {Path(pdf_path).stat().st_size / 1024:.2f} KB\n")
    
    # Initialize Groq LLM
    try:
        groq_service = GroqLLMService()
        print(f"✅ Groq LLM initialized: {groq_service.default_model}\n")
    except Exception as e:
        print(f"❌ Failed to initialize Groq: {e}")
        print("   Continuing without LLM...\n")
        groq_service = None
    
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
    print(f"📊 Pages: {state['metadata']['page_count']}")
    print(f"📦 Has Images: {state['metadata']['has_images']}")
    print()
    
    if not state['file_valid']:
        return
    
    # Agent 2: OCR
    print("=" * 80)
    print("2️⃣  OCR")
    print("=" * 80)
    ocr = SimpleOCRAgent()
    state = await ocr.execute(state)
    
    print(f"✅ Text Extracted: {state['has_text']}")
    print(f"📝 Length: {state['text_length']:,} chars")
    print(f"📄 Pages: {len(state['page_texts'])}")
    
    if state['ocr_text']:
        print(f"\n📖 Preview (first 300 chars):")
        print("-" * 80)
        print(state['ocr_text'][:300])
        print("..." if len(state['ocr_text']) > 300 else "")
        print("-" * 80)
    
    entities = state['extracted_entities']
    print(f"\n🔍 Extracted Entities:")
    print(f"  Dates: {len(entities['dates'])}")
    print(f"  Amounts: {len(entities['amounts'])}")
    print(f"  Names: {len(entities['potential_names'])}")
    print()
    
    # Agent 3: Format Validation
    print("=" * 80)
    print("3️⃣  FORMAT VALIDATION")
    print("=" * 80)
    format_agent = FormatValidationAgent()
    state = await format_agent.execute(state)
    
    print(f"✅ Format Valid: {state['format_valid']}")
    print(f"📊 Completeness Score: {state['completeness_score']}/100")
    print(f"🔤 Spelling Errors: {state['spelling_errors']}")
    print(f"📊 Spelling Error Rate: {state.get('spelling_error_rate', 0):.1f}%")
    
    misspelled = state.get('misspelled_words', [])
    if misspelled:
        print(f"\n❌ Typos Found: {len(misspelled)}")
        print(f"   Examples: {', '.join(misspelled[:10])}")
    
    print(f"\n❌ Missing Sections ({len(state['missing_sections'])}):")
    for section in state['missing_sections'][:5]:
        print(f"   - {section}")
    
    print(f"\n📋 Format Issues ({len(state['format_issues'])}):")
    for i, issue in enumerate(state['format_issues'][:5], 1):
        print(f"   {i}. [{issue['severity'].upper()}] {issue['type']}: {issue['details'][:60]}...")
    if len(state['format_issues']) > 5:
        print(f"   ... and {len(state['format_issues']) - 5} more")
    print()
    
    # Agent 4: NLP Validation with Groq LLM
    print("=" * 80)
    print("4️⃣  NLP VALIDATION (Groq LLM)")
    print("=" * 80)
    
    nlp_agent = NLPValidationAgent(llm_service=groq_service)
    state = await nlp_agent.execute(state)
    
    print(f"✅ NLP Valid: {state['nlp_valid']}")
    print(f"📊 Consistency Score: {state['consistency_score']}/100")
    print(f"⚠️  Contradictions: {len(state.get('contradictions', []))}")
    print(f"📅 Timeline Issues: {len(state.get('timeline_issues', []))}")
    print(f"📋 Semantic Issues: {len(state.get('semantic_issues', []))}")
    
    if state.get('contradictions'):
        print(f"\n🚨 Contradictions Detected:")
        for i, contradiction in enumerate(state['contradictions'][:5], 1):
            if isinstance(contradiction, dict):
                print(f"   {i}. [{contradiction.get('severity', 'N/A')}] {contradiction.get('type', 'N/A')}")
                print(f"      {contradiction.get('description', 'N/A')[:80]}...")
            else:
                print(f"   {i}. {contradiction}")
    
    if state.get('timeline_issues'):
        print(f"\n📅 Timeline Issues:")
        for issue in state['timeline_issues'][:3]:
            if isinstance(issue, dict):
                print(f"   - {issue.get('description', issue)[:80]}...")
            else:
                print(f"   - {issue}")
    
    if state.get('semantic_issues') and not state.get('contradictions'):
        print(f"\n📋 Other Semantic Issues:")
        for issue in state['semantic_issues'][:3]:
            if isinstance(issue, dict):
                print(f"   - [{issue.get('severity', 'N/A')}] {issue.get('description', issue)[:80]}...")
            else:
                print(f"   - {issue}")
    
    print()
    
    # Summary
    print("=" * 80)
    print("📊 WORKFLOW SUMMARY")
    print("=" * 80)
    print()
    print(f"✅ Agents Executed: 4/4")
    print(f"   1. DocumentIntake: {'✅ Pass' if state.get('file_valid') else '❌ Fail'}")
    print(f"   2. OCR: {'✅ Pass' if state.get('has_text') else '⚠️ Limited'}")
    print(f"   3. FormatValidation: {'✅ Pass' if state.get('format_valid') else '❌ Fail'}")
    print(f"   4. NLPValidation: {'✅ Pass' if state.get('nlp_valid') else '❌ Fail'}")
    print()
    
    print(f"📈 Quality Metrics:")
    print(f"   - Format Completeness: {state.get('completeness_score', 0)}/100")
    print(f"   - Semantic Consistency: {state.get('consistency_score', 0)}/100")
    print(f"   - Spelling Quality: {100 - state.get('spelling_error_rate', 0):.1f}%")
    print(f"   - Total Format Issues: {len(state.get('format_issues', []))}")
    print(f"   - Total Semantic Issues: {len(state.get('semantic_issues', []))}")
    print(f"   - Contradictions: {len(state.get('contradictions', []))}")
    print()
    
    # Overall Assessment
    overall_pass = (
        state.get('file_valid', False) and
        state.get('has_text', False) and
        state.get('format_valid', False) and
        state.get('nlp_valid', False)
    )
    
    print(f"🎯 Overall Assessment: {'✅ PASS' if overall_pass else '❌ FAIL'}")
    
    if not overall_pass:
        print(f"\n⚠️  Document Quality Issues Detected:")
        if not state.get('format_valid'):
            print(f"   - Format validation failed (score: {state.get('completeness_score', 0)}/100)")
        if not state.get('nlp_valid'):
            print(f"   - Semantic validation failed (score: {state.get('consistency_score', 0)}/100)")
        if state.get('contradictions'):
            print(f"   - {len(state.get('contradictions', []))} contradictions found")
    
    if state.get('errors'):
        print(f"\n⚠️  Errors: {len(state['errors'])}")
        for error in state['errors']:
            print(f"   - {error}")
    
    print()
    print("=" * 80)
    print("✅ WORKFLOW TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_full_workflow.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    asyncio.run(test_full_workflow(pdf_path))
