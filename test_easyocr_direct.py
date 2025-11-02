"""
Direct test of EasyOCR on the Swiss PDF
"""
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.part2.ocr import OCRAgent

def test_easyocr_extraction():
    """Test EasyOCR directly on the Swiss PDF"""
    pdf_path = "Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        return
    
    print("="*80)
    print("TESTING EASYOCR TEXT EXTRACTION")
    print("="*80)
    print(f"\n📄 Testing with: {pdf_path}")
    print(f"   File size: {Path(pdf_path).stat().st_size / 1024:.2f} KB\n")
    
    # Initialize OCR agent
    print("🔧 Initializing OCR agent...")
    ocr_agent = OCRAgent()
    
    # Create minimal state
    state = {
        "file_path": pdf_path,
        "file_format": "pdf",
        "document_id": "test-doc-001",
        "errors": []
    }
    
    print("🚀 Starting OCR extraction...")
    print("   Note: First run will download EasyOCR models (~100MB)")
    print("   This may take 30-60 seconds...\n")
    
    start_time = time.time()
    
    # Run OCR
    import asyncio
    result = asyncio.run(ocr_agent.execute(state))
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    ocr_text = result.get("ocr_text", "")
    pages_processed = result.get("pages_processed", 0)
    ocr_confidence = result.get("ocr_confidence", 0.0)
    has_text = result.get("has_text", False)
    extracted_entities = result.get("extracted_entities", {})
    errors = result.get("errors", [])
    
    print(f"\n⏱️  Processing time: {elapsed:.2f} seconds")
    print(f"📄 Pages processed: {pages_processed}")
    print(f"✅ Has text: {has_text}")
    print(f"📊 OCR confidence: {ocr_confidence * 100:.1f}%")
    print(f"📝 Text length: {len(ocr_text)} characters")
    
    if errors:
        print(f"\n⚠️  Errors:")
        for error in errors:
            print(f"   - {error}")
    
    if extracted_entities:
        print(f"\n🔍 Extracted Entities:")
        for entity_type, values in extracted_entities.items():
            if values:
                print(f"   {entity_type.title()}: {len(values)} found")
                for val in values[:3]:  # Show first 3
                    print(f"      - {val}")
                if len(values) > 3:
                    print(f"      ... and {len(values) - 3} more")
    
    if ocr_text:
        print(f"\n📖 Text Preview (first 500 characters):")
        print("-" * 80)
        print(ocr_text[:500])
        print("-" * 80)
        
        print(f"\n📖 Text Preview (middle 500 characters):")
        print("-" * 80)
        mid_point = len(ocr_text) // 2
        print(ocr_text[mid_point:mid_point+500])
        print("-" * 80)
        
        # Show some statistics
        words = ocr_text.split()
        print(f"\n📊 Text Statistics:")
        print(f"   Total words: {len(words)}")
        print(f"   Unique words: {len(set(words))}")
        print(f"   Average word length: {sum(len(w) for w in words) / len(words) if words else 0:.1f}")
    else:
        print(f"\n❌ No text extracted!")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_easyocr_extraction()
