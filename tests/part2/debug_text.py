"""
Debug script to show extracted text and spell checking details
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault('OCR_OUTPUT_DIR', 'data/ocr_output')

try:
    from PIL import Image
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

import fitz
from io import BytesIO
import re

async def debug_text_extraction(pdf_path):
    """Extract and show text details"""
    
    print("=" * 80)
    print("🔍 TEXT EXTRACTION DEBUG")
    print("=" * 80)
    print()
    
    # Initialize EasyOCR
    print("Initializing EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=False)
    print("✅ EasyOCR ready\n")
    
    # Extract text
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Get native text
    native_text = page.get_text("text")
    print(f"📄 Native PDF text: {len(native_text)} chars")
    if native_text.strip():
        print(f"Preview: {native_text[:200]}")
    print()
    
    # Get images and run OCR
    images = page.get_images()
    print(f"🖼️  Images found: {len(images)}")
    print()
    
    if images:
        img = images[0]
        xref = img[0]
        base_image = page.parent.extract_image(xref)  # page.parent is the document
        image_bytes = base_image["image"]
        image = Image.open(BytesIO(image_bytes))
        
        print("Running EasyOCR...")
        result = reader.readtext(image, detail=0)
        ocr_text = "\n".join(result)
        
        print(f"✅ OCR extracted: {len(ocr_text)} chars")
        print()
        print("=" * 80)
        print("FULL EXTRACTED TEXT:")
        print("=" * 80)
        print(ocr_text)
        print("=" * 80)
        print()
        
        # Now analyze spelling
        print("=" * 80)
        print("🔤 SPELLING ANALYSIS")
        print("=" * 80)
        print()
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', ocr_text.lower())
        print(f"📊 Total words extracted: {len(words)}")
        print(f"📊 Unique words: {len(set(words))}")
        print()
        
        # Show first 50 words
        print("First 50 words extracted:")
        print("-" * 80)
        for i in range(0, min(50, len(words)), 10):
            print(" ".join(words[i:i+10]))
        print("-" * 80)
        print()
        
        # Check with spell checker
        try:
            from spellchecker import SpellChecker
            spell = SpellChecker()
            
            print("Running spell checker...")
            misspelled = spell.unknown(words)
            
            print(f"❌ Misspelled words: {len(misspelled)}")
            print(f"📊 Error rate: {len(misspelled)/len(words)*100:.1f}%")
            print()
            
            if misspelled:
                print("Examples of misspelled words (first 30):")
                print("-" * 80)
                misspelled_list = list(misspelled)[:30]
                for i in range(0, len(misspelled_list), 5):
                    print(" | ".join(misspelled_list[i:i+5]))
                print("-" * 80)
                print()
                
                # Show corrections for first 10
                print("Suggested corrections (first 10):")
                print("-" * 80)
                for word in list(misspelled)[:10]:
                    corrections = spell.candidates(word)
                    if corrections:
                        print(f"  '{word}' → {list(corrections)[:3]}")
                    else:
                        print(f"  '{word}' → No suggestions")
                print("-" * 80)
        
        except ImportError:
            print("⚠️  pyspellchecker not available")
    
    doc.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_text.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    asyncio.run(debug_text_extraction(pdf_path))
