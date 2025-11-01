"""
Test REAL agents with the actual PDF through full workflow
Tests: DocumentIntake -> OCR -> FormatValidation (with spell checking!)
(Skipping BackgroundCheck to save API tokens)
"""
import asyncio
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from io import BytesIO

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set minimal env vars before importing anything that needs config
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5432/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-key')
os.environ.setdefault('MAX_UPLOAD_SIZE_MB', '50')
os.environ.setdefault('OCR_OUTPUT_DIR', 'data/ocr_output')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import libraries
import fitz
try:
    from PIL import Image
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("EasyOCR not available")

# Import agents without config dependency
import re
from typing import Dict, Any

# Simple Document Intake (no config needed)
class TestDocumentIntakeAgent:
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
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

# Simple OCR Agent
class TestOCRAgent:
    def __init__(self):
        if EASYOCR_AVAILABLE:
            logger.info("Initializing EasyOCR...")
            self.reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR ready")
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Executing OCRAgent")
        file_path = state.get("file_path")
        
        doc = fitz.open(file_path)
        page_texts = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            
            # If minimal text and has images, try OCR
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
        
        # Extract entities
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

# Import REAL FormatValidationAgent directly (bypass __init__.py)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "format_validation",
    str(project_root / "agents" / "part2" / "format_validation.py")
)
format_validation_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(format_validation_module)
FormatValidationAgent = format_validation_module.FormatValidationAgent

async def test_full_workflow(pdf_path: str):
    """Run full workflow on real PDF"""
    
    print("=" * 80)
    print("🧪 REAL AGENTS TEST - Full Workflow with Spell Checking")
    print("=" * 80)
    print(f"\n📄 PDF: {pdf_path}")
    print(f"📁 Size: {Path(pdf_path).stat().st_size / 1024:.2f} KB\n")
    
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
    intake = TestDocumentIntakeAgent()
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
    ocr = TestOCRAgent()
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
    
    # Agent 3: REAL Format Validation
    print("=" * 80)
    print("3️⃣  FORMAT VALIDATION (REAL AGENT WITH SPELL CHECKING)")
    print("=" * 80)
    format_agent = FormatValidationAgent()
    state = await format_agent.execute(state)
    
    print(f"✅ Format Valid: {state['format_valid']}")
    print(f"📊 Completeness Score: {state['completeness_score']}/100")
    print(f"🔤 Spelling Errors: {state['spelling_errors']}")
    print(f"📊 Spelling Error Rate: {state.get('spelling_error_rate', 0):.1f}%")
    print()
    
    # Show misspelled words (TYPOS)
    misspelled = state.get('misspelled_words', [])
    if misspelled:
        print(f"❌ ACTUAL TYPOS DETECTED ({len(misspelled)}):")
        print("   (Filtered: proper nouns, foreign words, banking terms, codes)")
        print("=" * 80)
        # Group into rows of 5
        for i in range(0, len(misspelled), 5):
            row = misspelled[i:i+5]
            print("   " + " | ".join(f"{word:15}" for word in row))
        print("=" * 80)
        print()
        
        # Show some examples of what would be the corrections
        if len(misspelled) > 0:
            print("📝 Likely Corrections (examples):")
            corrections = {
                'confrm': 'confirm',
                'adress': 'address',
                'occured': 'occurred',
                'evidense': 'evidence',
                'assesment': 'assessment',
                'ransaction': 'transaction',
                'resoluton': 'resolution',
                'agreemment': 'agreement',
                'knowlege': 'knowledge',
                'seperately': 'separately',
                'constiute': 'constitute',
                'voucherls': 'vouchers',
                'annexture': 'annexure'
            }
            found_corrections = {k: v for k, v in corrections.items() if k in misspelled}
            if found_corrections:
                for typo, correction in list(found_corrections.items())[:10]:
                    print(f"   • '{typo}' → '{correction}'")
                print()
    else:
        print("✅ No typos detected (after filtering)")
        print()
    
    if state.get('fraud_indicators'):
        print(f"🚨 Fraud Indicators ({len(state['fraud_indicators'])}):")
        for indicator in state['fraud_indicators']:
            print(f"   ⚠️  {indicator}")
        print()
    
    print(f"❌ Missing Sections ({len(state['missing_sections'])}):")
    for section in state['missing_sections']:
        print(f"   - {section}")
    print()
    
    print(f"📋 Format Issues ({len(state['format_issues'])}):")
    for i, issue in enumerate(state['format_issues'][:15], 1):
        print(f"   {i}. [{issue['severity'].upper()}] {issue['type']}")
        print(f"      → {issue['details']}")
    if len(state['format_issues']) > 15:
        print(f"   ... and {len(state['format_issues']) - 15} more issues")
    print()
    
    # Summary
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"\n✅ Agents Executed: 3/3")
    print(f"   1. DocumentIntake: {'✅ Pass' if state.get('file_valid') else '❌ Fail'}")
    print(f"   2. OCR: {'✅ Pass' if state.get('has_text') else '⚠️ Limited'}")
    print(f"   3. FormatValidation: {'✅ Pass' if state.get('format_valid') else '❌ Fail'}")
    print()
    
    print(f"📈 Quality Metrics:")
    print(f"   - Completeness: {state.get('completeness_score', 0)}/100")
    print(f"   - Spelling Quality: {100 - state.get('spelling_error_rate', 0):.1f}%")
    print(f"   - Misspelled Words: {len(misspelled)}")
    print(f"   - Total Issues: {len(state.get('format_issues', []))}")
    print(f"   - Fraud Indicators: {len(state.get('fraud_indicators', []))}")
    print()
    
    if state.get('errors'):
        print(f"⚠️  Errors: {len(state['errors'])}")
        for error in state['errors']:
            print(f"   - {error}")
    else:
        print("✅ No errors")
    
    print()
    print("=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_real_format_validation.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    asyncio.run(test_full_workflow(pdf_path))
