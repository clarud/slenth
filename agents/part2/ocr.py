"""
OCRAgent - Extract text from PDF documents

Responsibilities:
1. Extract text from native PDF text layers
2. Perform OCR on scanned PDFs/images using Tesseract
3. Clean and normalize extracted text
4. Detect language
5. Save OCR output for downstream processing
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from io import BytesIO

try:
    import fitz  # PyMuPDF
except ImportError:
    import PyMuPDF as fitz

try:
    from PIL import Image
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("Tesseract/PIL not available - OCR for scanned documents will be limited")

from agents import Part2Agent
from config import settings

logger = logging.getLogger(__name__)


class OCRAgent(Part2Agent):
    """Agent: Extract text from PDF documents using PyMuPDF and Tesseract OCR"""

    def __init__(self):
        super().__init__("ocr")
        self.ocr_output_dir = settings.ocr_output_dir
        os.makedirs(self.ocr_output_dir, exist_ok=True)
        
        # Configure Tesseract if available
        if TESSERACT_AVAILABLE and hasattr(settings, 'tesseract_path'):
            tesseract_path = settings.tesseract_path
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute OCR: extract text from PDF document.

        Args:
            state: Workflow state containing:
                - file_path: Path to PDF document
                - document_id: Unique document ID
                - metadata: Document metadata

        Returns:
            Updated state with:
                - ocr_text: Extracted text content
                - ocr_output_path: Path to saved OCR output
                - page_texts: List of text per page
                - text_length: Total character count
                - has_text: Boolean if text was extracted
        """
        self.logger.info("Executing OCRAgent")

        file_path = state.get("file_path")
        document_id = state.get("document_id")
        metadata = state.get("metadata", {})

        # Initialize results
        ocr_text = ""
        page_texts = []
        has_text = False
        errors = state.get("errors", [])

        try:
            # Step 1: Open PDF document
            doc = fitz.open(file_path)
            
            self.logger.info(
                f"Processing {len(doc)} pages from {Path(file_path).name}"
            )

            # Step 2: Extract text from each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Try to extract text from PDF text layer first
                page_text = page.get_text("text")
                
                # If no text found and page has images, try OCR
                if len(page_text.strip()) < 50 and page.get_images():
                    self.logger.info(
                        f"Page {page_num + 1} has minimal text, attempting OCR on images"
                    )
                    ocr_text = self._ocr_page_images(page, page_num)
                    if ocr_text:
                        page_text = ocr_text
                
                # Clean the text
                page_text = self._clean_text(page_text)
                
                page_texts.append({
                    "page_number": page_num + 1,
                    "text": page_text,
                    "char_count": len(page_text)
                })

            doc.close()

            # Step 3: Combine all page texts
            ocr_text = "\n\n".join([
                f"[Page {p['page_number']}]\n{p['text']}" 
                for p in page_texts
            ])

            # Step 4: Check if meaningful text was extracted
            has_text = len(ocr_text.strip()) > 100  # At least 100 characters

            if not has_text:
                self.logger.warning(
                    f"Limited text extracted from {document_id}. "
                    f"Document may be scanned image or empty."
                )
                errors.append(
                    "Minimal text extracted - document may be scanned image"
                )

            # Step 5: Save OCR output to file
            ocr_output_path = os.path.join(
                self.ocr_output_dir,
                f"{document_id}_ocr.txt"
            )
            
            with open(ocr_output_path, 'w', encoding='utf-8') as f:
                f.write(ocr_text)

            self.logger.info(
                f"OCR completed: {document_id}, "
                f"{len(page_texts)} pages, "
                f"{len(ocr_text)} characters"
            )

            # Step 6: Extract structured information
            extracted_entities = self._extract_basic_entities(ocr_text)

        except Exception as e:
            self.logger.error(f"Error in OCR processing: {e}")
            errors.append(f"OCR error: {str(e)}")
            ocr_output_path = None
            extracted_entities = {}

        # Update state
        state["ocr_text"] = ocr_text
        state["page_texts"] = page_texts
        state["ocr_output_path"] = ocr_output_path
        state["text_length"] = len(ocr_text)
        state["has_text"] = has_text
        state["extracted_entities"] = extracted_entities
        state["errors"] = errors
        state["ocr_executed"] = True

        return state

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove multiple consecutive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def _extract_basic_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract basic entities from text (names, dates, amounts).

        Args:
            text: OCR extracted text

        Returns:
            Dictionary of extracted entities
        """
        entities = {
            "dates": [],
            "amounts": [],
            "emails": [],
            "phone_numbers": [],
            "potential_names": []
        }

        try:
            # Extract dates (various formats)
            date_patterns = [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # DD/MM/YYYY
                r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # YYYY-MM-DD
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'  # Month DD, YYYY
            ]
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities["dates"].extend(matches)

            # Extract monetary amounts
            amount_pattern = r'[\$£€¥]\s*[\d,]+\.?\d*|\b\d+[,\.\d]*\s*(?:USD|EUR|GBP|CHF|SGD|HKD)\b'
            entities["amounts"] = re.findall(amount_pattern, text, re.IGNORECASE)

            # Extract emails
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            entities["emails"] = re.findall(email_pattern, text)

            # Extract phone numbers
            phone_pattern = r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}'
            entities["phone_numbers"] = re.findall(phone_pattern, text)

            # Extract potential names (Title + Capitalized Words)
            name_pattern = r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
            entities["potential_names"] = re.findall(name_pattern, text)

            # Remove duplicates
            for key in entities:
                entities[key] = list(set(entities[key]))[:10]  # Limit to 10 per type

        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")

        return entities

    def _ocr_page_images(self, page, page_num: int) -> str:
        """
        Perform OCR on images within a PDF page using Tesseract.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)

        Returns:
            Extracted text from images
        """
        if not TESSERACT_AVAILABLE:
            self.logger.warning("Tesseract not available, cannot OCR images")
            return ""

        ocr_text = []

        try:
            # Get all images from the page
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    # Extract image
                    xref = img[0]
                    base_image = page.parent.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Convert to PIL Image
                    image = Image.open(BytesIO(image_bytes))
                    
                    # Perform OCR
                    self.logger.info(
                        f"Running Tesseract OCR on page {page_num + 1}, image {img_index + 1}"
                    )
                    text = pytesseract.image_to_string(image, lang='eng')
                    
                    if text.strip():
                        ocr_text.append(text)
                        self.logger.info(
                            f"Extracted {len(text)} characters from image {img_index + 1}"
                        )
                    
                except Exception as img_error:
                    self.logger.error(
                        f"Error OCRing image {img_index + 1} on page {page_num + 1}: {img_error}"
                    )
                    continue

        except Exception as e:
            self.logger.error(f"Error in OCR processing for page {page_num + 1}: {e}")

        return "\n\n".join(ocr_text)
