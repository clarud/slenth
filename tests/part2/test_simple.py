"""
Simplified test script for Part 2 agents without full config
Tests: Document Intake, OCR, Background Check (Dilisense)
"""

import asyncio
import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set minimal environment variables for testing
os.environ.setdefault('MAX_UPLOAD_SIZE_MB', '50')
os.environ.setdefault('OCR_OUTPUT_DIR', 'data/ocr_output')
os.environ.setdefault('DOCUMENT_ALLOWED_TYPES', 'pdf')
os.environ.setdefault('ENABLE_BACKGROUND_CHECK', 'true')
os.environ.setdefault('DILISENSE_API_KEY', 'sF8e01BcNQ2pz5Wfs3hcp5L2TME4qwkC1vIb5DdK')
os.environ.setdefault('DILISENSE_BASE_URL', 'https://api.dilisense.com/v1')
os.environ.setdefault('DILISENSE_TIMEOUT', '30')
os.environ.setdefault('DILISENSE_MAX_RETRIES', '3')
os.environ.setdefault('DILISENSE_ENABLED', 'true')

# Import agents directly without full config
import logging
import fitz  # PyMuPDF
import re
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from io import BytesIO

try:
    from PIL import Image
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

if not TESSERACT_AVAILABLE and not EASYOCR_AVAILABLE:
    print("⚠️  Warning: No OCR available - text extraction from scanned PDFs will be limited")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SimpleDocumentIntakeAgent:
    """Simplified Document Intake Agent"""
    
    def __init__(self):
        self.max_size_bytes = int(os.getenv('MAX_UPLOAD_SIZE_MB', '50')) * 1024 * 1024
        self.allowed_types = [os.getenv('DOCUMENT_ALLOWED_TYPES', 'pdf')]
    
    async def execute(self, state):
        """Execute document intake"""
        logger.info("Executing DocumentIntakeAgent")
        
        file_path = state.get("file_path")
        errors = []
        
        # Validate file
        if not os.path.exists(file_path):
            errors.append("File does not exist")
            state["file_valid"] = False
            return state
        
        # Check file type
        file_ext = Path(file_path).suffix.lower().lstrip('.')
        if file_ext not in self.allowed_types:
            errors.append(f"Invalid file type: {file_ext}")
            state["file_valid"] = False
            return state
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.max_size_bytes:
            errors.append(f"File too large: {file_size / (1024*1024):.2f}MB")
            state["file_valid"] = False
            return state
        
        # Extract metadata
        metadata = {}
        try:
            doc = fitz.open(file_path)
            metadata["file_name"] = Path(file_path).name
            metadata["file_size"] = file_size
            metadata["page_count"] = len(doc)
            metadata["is_encrypted"] = doc.is_encrypted
            
            pdf_meta = doc.metadata
            if pdf_meta:
                metadata["title"] = pdf_meta.get("title", "")
                metadata["author"] = pdf_meta.get("author", "")
            
            has_images = any(doc[i].get_images() for i in range(len(doc)))
            metadata["has_images"] = has_images
            
            doc.close()
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
        
        state["file_valid"] = True
        state["document_type"] = "purchase_agreement"
        state["metadata"] = metadata
        state["errors"] = errors
        
        return state


class SimpleOCRAgent:
    """Simplified OCR Agent"""
    
    def __init__(self):
        self.output_dir = os.getenv('OCR_OUTPUT_DIR', 'data/ocr_output')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize EasyOCR reader if available
        self.easyocr_reader = None
        if EASYOCR_AVAILABLE:
            try:
                logger.info("Initializing EasyOCR reader...")
                self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
                logger.info("EasyOCR ready!")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR: {e}")
    
    async def execute(self, state):
        """Execute OCR"""
        logger.info("Executing OCRAgent")
        
        file_path = state.get("file_path")
        document_id = state.get("document_id")
        
        try:
            doc = fitz.open(file_path)
            page_texts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Try to extract text from PDF layer first
                text = page.get_text("text")
                
                # If minimal text and has images, try OCR
                if len(text.strip()) < 50 and page.get_images():
                    if self.easyocr_reader or TESSERACT_AVAILABLE:
                        logger.info(f"Page {page_num + 1} has minimal text, attempting OCR")
                        ocr_text = self._ocr_page(page, page_num)
                        if ocr_text:
                            text = ocr_text
                
                page_texts.append({
                    "page_number": page_num + 1,
                    "text": text,
                    "char_count": len(text)
                })
            
            doc.close()
            
            # Combine text
            ocr_text = "\n\n".join([
                f"[Page {p['page_number']}]\n{p['text']}" 
                for p in page_texts
            ])
            
            # Save output
            output_path = os.path.join(self.output_dir, f"{document_id}_ocr.txt")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ocr_text)
            
            # Extract entities
            entities = self._extract_entities(ocr_text)
            
            state["ocr_text"] = ocr_text
            state["page_texts"] = page_texts
            state["ocr_output_path"] = output_path
            state["text_length"] = len(ocr_text)
            state["has_text"] = len(ocr_text.strip()) > 100
            state["extracted_entities"] = entities
            
        except Exception as e:
            logger.error(f"OCR error: {e}")
            state["errors"].append(f"OCR error: {str(e)}")
        
        return state
    
    def _ocr_page(self, page, page_num):
        """Perform OCR on page images"""
        ocr_text = []
        
        try:
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    # Extract image
                    xref = img[0]
                    base_image = page.parent.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Try EasyOCR first (better accuracy, no external dependencies)
                    if self.easyocr_reader:
                        logger.info(f"Running EasyOCR on page {page_num + 1}, image {img_index + 1}")
                        
                        # Convert bytes to PIL Image for EasyOCR
                        image = Image.open(BytesIO(image_bytes))
                        
                        # Run EasyOCR
                        result = self.easyocr_reader.readtext(image, detail=0)
                        text = "\n".join(result)
                        
                        if text.strip():
                            ocr_text.append(text)
                            logger.info(f"EasyOCR extracted {len(text)} characters")
                    
                    # Fallback to Tesseract if available
                    elif TESSERACT_AVAILABLE:
                        logger.info(f"Running Tesseract on page {page_num + 1}, image {img_index + 1}")
                        image = Image.open(BytesIO(image_bytes))
                        text = pytesseract.image_to_string(image, lang='eng')
                        
                        if text.strip():
                            ocr_text.append(text)
                            logger.info(f"Tesseract extracted {len(text)} characters")
                    
                except Exception as e:
                    logger.error(f"Error OCRing image: {e}")
        
        except Exception as e:
            logger.error(f"Error in OCR: {e}")
        
        return "\n\n".join(ocr_text)
    
    def _extract_entities(self, text):
        """Extract basic entities"""
        entities = {
            "dates": [],
            "amounts": [],
            "emails": [],
            "phone_numbers": [],
            "potential_names": []
        }
        
        # Dates
        entities["dates"] = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)[:10]
        
        # Amounts
        entities["amounts"] = re.findall(r'[\$£€]\s*[\d,]+\.?\d*', text)[:10]
        
        # Emails
        entities["emails"] = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)[:10]
        
        # Names
        entities["potential_names"] = re.findall(
            r'\b(?:Mr|Mrs|Ms|Dr)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
            text
        )[:10]
        
        return entities


class SimpleBackgroundCheckAgent:
    """Simplified Background Check Agent with Dilisense"""
    
    def __init__(self):
        self.api_key = os.getenv('DILISENSE_API_KEY')
        self.base_url = os.getenv('DILISENSE_BASE_URL')
        self.enabled = os.getenv('DILISENSE_ENABLED', 'true').lower() == 'true'
    
    async def execute(self, state):
        """Execute background check"""
        logger.info("Executing BackgroundCheckAgent")
        
        if not self.enabled:
            state["background_check_skipped"] = True
            return state
        
        ocr_text = state.get("ocr_text", "")
        entities = state.get("extracted_entities", {})
        
        # Extract names
        names = self._extract_names(ocr_text, entities.get("potential_names", []))
        
        results = []
        screened = []
        pep_found = False
        sanctions_found = False
        
        # Screen each name
        for name in names[:5]:  # Limit to 5
            try:
                result = await self._screen_individual(name)
                results.append(result)
                screened.append(name)
                
                if result.get("is_pep"):
                    pep_found = True
                if result.get("is_sanctioned"):
                    sanctions_found = True
                    
            except Exception as e:
                logger.error(f"Error screening {name}: {e}")
        
        # Calculate risk score
        risk_score = 0
        if pep_found:
            risk_score += 40
        if sanctions_found:
            risk_score += 60
        
        state["background_check_results"] = results
        state["pep_found"] = pep_found
        state["sanctions_found"] = sanctions_found
        state["background_risk_score"] = min(risk_score, 100)
        state["screened_entities"] = screened
        
        return state
    
    def _extract_names(self, text, pre_extracted):
        """Extract names from text"""
        names = set(pre_extracted)
        
        # Title + Name pattern
        matches = re.findall(
            r'\b(?:Mr|Mrs|Ms|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b',
            text
        )
        names.update(matches)
        
        return list(names)[:10]
    
    async def _screen_individual(self, name):
        """Screen individual against Dilisense"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/checkIndividual",
                params={"names": name, "fuzzy_search": "1"},
                headers={"x-api-key": self.api_key}
            )
            response.raise_for_status()
            
            data = response.json()
            records = data.get("found_records", [])
            first_record = records[0] if records else {}
            
            return {
                "name": name,
                "total_hits": data.get("total_hits", 0),
                "is_pep": first_record.get("source_type") == "PEP",
                "is_sanctioned": first_record.get("source_type") == "SANCTION",
                "risk_level": "high" if data.get("total_hits", 0) > 0 else "low",
                "matches": records
            }


async def test_agents(pdf_path):
    """Test all 3 agents"""
    print("=" * 80)
    print("🧪 TESTING PART 2 AGENTS (Simplified)")
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
    agent1 = SimpleDocumentIntakeAgent()
    state = await agent1.execute(state)
    
    print(f"✅ Valid: {state['file_valid']}")
    print(f"📄 Type: {state['document_type']}")
    metadata = state['metadata']
    print(f"📊 Pages: {metadata.get('page_count')}")
    print(f"📦 Has Images: {metadata.get('has_images')}")
    if metadata.get('title'):
        print(f"📝 Title: {metadata['title']}")
    print()
    
    if not state['file_valid']:
        return
    
    # Agent 2: OCR
    print("=" * 80)
    print("2️⃣  OCR")
    print("=" * 80)
    agent2 = SimpleOCRAgent()
    state = await agent2.execute(state)
    
    print(f"✅ Text Extracted: {state['has_text']}")
    print(f"📝 Length: {state['text_length']:,} chars")
    print(f"📄 Pages: {len(state['page_texts'])}")
    
    # Show preview
    if state['ocr_text']:
        print(f"\n📖 Preview (first 500 chars):")
        print("-" * 80)
        print(state['ocr_text'][:500])
        print("..." if len(state['ocr_text']) > 500 else "")
        print("-" * 80)
    
    # Show entities
    entities = state['extracted_entities']
    print(f"\n🔍 Extracted:")
    print(f"  Dates: {len(entities['dates'])}")
    print(f"  Amounts: {len(entities['amounts'])}")
    print(f"  Names: {len(entities['potential_names'])}")
    if entities['potential_names']:
        print(f"  Examples: {', '.join(entities['potential_names'][:3])}")
    print()
    
    # Agent 3: Background Check
    print("=" * 80)
    print("3️⃣  BACKGROUND CHECK (Dilisense)")
    print("=" * 80)
    agent3 = SimpleBackgroundCheckAgent()
    state = await agent3.execute(state)
    
    print(f"✅ Screened: {len(state['screened_entities'])} entities")
    if state['screened_entities']:
        print(f"   Names: {', '.join(state['screened_entities'])}")
    
    print(f"\n🚨 Findings:")
    print(f"  PEP: {'⚠️  YES' if state['pep_found'] else '✅ No'}")
    print(f"  Sanctions: {'🚨 YES' if state['sanctions_found'] else '✅ No'}")
    print(f"  Risk Score: {state['background_risk_score']}/100")
    
    # Show results
    if state['background_check_results']:
        print(f"\n📊 Screening Results:")
        for i, result in enumerate(state['background_check_results'], 1):
            print(f"\n  {i}. {result['name']}")
            print(f"     Hits: {result['total_hits']}")
            print(f"     PEP: {result['is_pep']}")
            print(f"     Sanctioned: {result['is_sanctioned']}")
    
    print()
    print("=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)
    
    # Save results
    output_file = f"test_output_{state['document_id']}.json"
    with open(output_file, 'w') as f:
        json_state = {k: v for k, v in state.items() if k not in ['ocr_text', 'page_texts']}
        json_state['ocr_text_length'] = len(state.get('ocr_text', ''))
        json.dump(json_state, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_simple.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    asyncio.run(test_agents(pdf_path))
