"""
DocumentIntakeAgent - Accept uploads and normalize to internal format

Responsibilities:
1. Validate file type (PDF, JPG, PNG, DOCX, etc.)
2. Check file size limits
3. Detect document type from metadata/filename
4. Extract basic document metadata
5. Normalize file path and store location
6. Support multi-format document processing
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents import Part2Agent
from config import settings

logger = logging.getLogger(__name__)


class DocumentIntakeAgent(Part2Agent):
    """Agent: Accept uploads and normalize to internal format (multi-format support)"""

    # Supported document types and their indicators
    DOCUMENT_TYPES = {
        "purchase_agreement": ["purchase", "agreement", "sale", "buy"],
        "proof_of_address": ["address", "utility", "bill", "statement"],
        "id_document": ["passport", "id", "identity", "license", "driver"],
        "bank_statement": ["bank", "statement", "account"],
        "contract": ["contract", "terms", "conditions"],
        "invoice": ["invoice", "receipt", "payment"],
        "other": []
    }

    # Supported file formats
    SUPPORTED_FORMATS = {
        # Documents
        "pdf": {"category": "document", "mime": "application/pdf"},
        
        # Images
        "jpg": {"category": "image", "mime": "image/jpeg"},
        "jpeg": {"category": "image", "mime": "image/jpeg"},
        "png": {"category": "image", "mime": "image/png"},
        "tiff": {"category": "image", "mime": "image/tiff"},
        "tif": {"category": "image", "mime": "image/tiff"},
        "bmp": {"category": "image", "mime": "image/bmp"},
        "webp": {"category": "image", "mime": "image/webp"},
        
        # Office Documents
        "docx": {"category": "document", "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        "doc": {"category": "document", "mime": "application/msword"},
        "xlsx": {"category": "document", "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        "xls": {"category": "document", "mime": "application/vnd.ms-excel"},
    }

    def __init__(self):
        super().__init__("document_intake")
        self.max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
        
        # Initialize optional dependencies
        self._init_dependencies()

    def _init_dependencies(self):
        """Initialize optional document processing libraries"""
        # PyMuPDF for PDF
        self.fitz_available = False
        try:
            import fitz
            self.fitz = fitz
            self.fitz_available = True
            logger.info("PyMuPDF available for PDF processing")
        except ImportError:
            logger.warning("PyMuPDF not available - PDF processing limited")

        # PIL for images
        self.pil_available = False
        try:
            from PIL import Image
            self.Image = Image
            self.pil_available = True
            logger.info("PIL/Pillow available for image processing")
        except ImportError:
            logger.warning("PIL/Pillow not available - image processing limited")

        # python-docx for DOCX
        self.docx_available = False
        try:
            import docx
            self.docx = docx
            self.docx_available = True
            logger.info("python-docx available for DOCX processing")
        except ImportError:
            logger.warning("python-docx not available - DOCX processing limited")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute document intake: validate, classify, and normalize document.

        Args:
            state: Workflow state containing:
                - file_path: Path to uploaded document (PDF/JPG/PNG)
                - document: Document metadata dict
                - document_id: Unique document ID

        Returns:
            Updated state with:
                - file_format: Detected format (pdf/jpg/png)
                - document_type: Classified document type
                - file_valid: Boolean validation result
                - metadata: Extracted document metadata
                - errors: List of validation errors
        """
        self.logger.info("Executing DocumentIntakeAgent")

        file_path = state.get("file_path")
        document = state.get("document", {})
        document_id = state.get("document_id")

        # Initialize results
        errors = []
        metadata = {}
        file_valid = False
        document_type = "other"
        file_format = "unknown"

        try:
            # Step 1: Validate file exists
            if not file_path or not os.path.exists(file_path):
                errors.append("File does not exist")
                state["errors"] = errors
                state["file_valid"] = False
                return state

            # Step 2: Detect and validate file format
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            
            # Map extension to format
            if file_extension == "pdf":
                file_format = "pdf"
            elif file_extension in ["jpg", "jpeg"]:
                file_format = "jpg"
            elif file_extension == "png":
                file_format = "png"
            else:
                errors.append(
                    f"Invalid file type: {file_extension}. "
                    f"Supported: pdf, jpg, jpeg, png"
                )
                state["errors"] = errors
                state["file_valid"] = False
                return state

            self.logger.info(f"Detected file format: {file_format}")

            # Step 3: Validate file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_size_bytes:
                errors.append(
                    f"File size {file_size / (1024*1024):.2f}MB exceeds "
                    f"maximum {settings.max_upload_size_mb}MB"
                )
                state["errors"] = errors
                state["file_valid"] = False
                return state

            # Step 4: Extract metadata based on format
            if file_format == "pdf":
                metadata = self._extract_pdf_metadata(file_path)
                
                # Validate PDF is not corrupted
                if not self._validate_pdf(file_path):
                    errors.append("PDF file is corrupted or cannot be opened")
                    state["errors"] = errors
                    state["file_valid"] = False
                    return state
                    
            elif file_format in ["jpg", "png"]:
                metadata = self._extract_image_metadata(file_path)
                
                # Validate image is readable
                if not self._validate_image(file_path):
                    errors.append("Image file is corrupted or cannot be opened")
                    state["errors"] = errors
                    state["file_valid"] = False
                    return state

            # Step 5: Detect document type
            document_type = self._detect_document_type(
                file_path=file_path,
                metadata=metadata,
                provided_type=document.get("document_type")
            )

            # Success - file is valid
            file_valid = True
            self.logger.info(
                f"Document intake successful: {document_id}, "
                f"format={file_format}, type={document_type}"
            )

        except Exception as e:
            self.logger.error(f"Error in document intake: {e}")
            errors.append(f"Document intake error: {str(e)}")
            file_valid = False

        # Update state
        state["file_valid"] = file_valid
        state["file_format"] = file_format  # Add format to state
        state["document_type"] = document_type
        state["metadata"] = metadata
        state["errors"] = errors
        state["document_intake_executed"] = True

        return state
    
    def _extract_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from image file (JPG/PNG).

        Args:
            file_path: Path to image file

        Returns:
            Dictionary with metadata
        """
        metadata = {
            "file_name": Path(file_path).name,
            "file_size": os.path.getsize(file_path),
            "file_size_mb": os.path.getsize(file_path) / (1024 * 1024),
            "file_extension": Path(file_path).suffix.lower(),
            "upload_timestamp": datetime.utcnow().isoformat(),
            "page_count": 1,  # Images are single "page"
        }

        try:
            if self.pil_available:
                from PIL import Image
                with Image.open(file_path) as img:
                    metadata["width"] = img.width
                    metadata["height"] = img.height
                    metadata["format"] = img.format
                    metadata["mode"] = img.mode  # RGB, RGBA, L, etc.
                    
                    # Check for images
                    metadata["has_images"] = True
                    
                    # Extract EXIF if available
                    exif = img.getexif()
                    if exif:
                        metadata["has_exif"] = True
                        # Common EXIF tags
                        if 271 in exif:  # Make
                            metadata["camera_make"] = exif[271]
                        if 272 in exif:  # Model
                            metadata["camera_model"] = exif[272]
                        if 306 in exif:  # DateTime
                            metadata["creation_date"] = exif[306]
                    else:
                        metadata["has_exif"] = False
            
            self.logger.info(f"Image metadata extracted: {metadata.get('width')}x{metadata.get('height')}")
            
        except Exception as e:
            self.logger.warning(f"Could not extract image metadata: {e}")
        
        return metadata

    def _validate_image(self, file_path: str) -> bool:
        """
        Validate that image file can be opened and is not corrupted.

        Args:
            file_path: Path to image file

        Returns:
            True if image is valid, False otherwise
        """
        try:
            if self.pil_available:
                from PIL import Image
                with Image.open(file_path) as img:
                    # Try to load the image data
                    img.verify()
                    
                # Reopen to actually load (verify closes the file)
                with Image.open(file_path) as img:
                    img.load()
                    
                return True
            else:
                self.logger.warning("PIL not available, skipping image validation")
                return True  # Assume valid if can't check
                
        except Exception as e:
            self.logger.error(f"Image validation failed: {e}")
            return False

    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary with metadata
        """
        metadata = {
            "file_name": Path(file_path).name,
            "file_size": os.path.getsize(file_path),
            "file_extension": Path(file_path).suffix.lower(),
            "upload_timestamp": datetime.utcnow().isoformat(),
        }

        try:
            if not self.fitz_available:
                self.logger.warning("PyMuPDF not available for PDF metadata extraction")
                return metadata
                
            doc = self.fitz.open(file_path)
            
            # Basic document info
            metadata["page_count"] = len(doc)
            metadata["is_encrypted"] = doc.is_encrypted
            metadata["is_pdf"] = doc.is_pdf
            
            # PDF metadata
            pdf_metadata = doc.metadata
            if pdf_metadata:
                metadata["title"] = pdf_metadata.get("title", "")
                metadata["author"] = pdf_metadata.get("author", "")
                metadata["subject"] = pdf_metadata.get("subject", "")
                metadata["creator"] = pdf_metadata.get("creator", "")
                metadata["producer"] = pdf_metadata.get("producer", "")
                metadata["creation_date"] = pdf_metadata.get("creationDate", "")
                metadata["modification_date"] = pdf_metadata.get("modDate", "")
            
            # Check if document has images
            has_images = False
            for page_num in range(len(doc)):
                page = doc[page_num]
                if page.get_images():
                    has_images = True
                    break
            metadata["has_images"] = has_images
            
            doc.close()

        except Exception as e:
            self.logger.error(f"Error extracting PDF metadata: {e}")
            metadata["extraction_error"] = str(e)

        return metadata

    def _detect_document_type(
        self,
        file_path: str,
        metadata: Dict[str, Any],
        provided_type: Optional[str] = None
    ) -> str:
        """
        Detect document type from filename, metadata, and content.

        Args:
            file_path: Path to document
            metadata: Extracted metadata
            provided_type: User-provided document type

        Returns:
            Detected document type
        """
        # If user provided valid type, use it
        if provided_type and provided_type in self.DOCUMENT_TYPES:
            return provided_type

        # Check filename and metadata for keywords
        search_text = " ".join([
            Path(file_path).stem.lower(),
            metadata.get("title", "").lower(),
            metadata.get("subject", "").lower(),
        ])

        # Find best matching document type
        for doc_type, keywords in self.DOCUMENT_TYPES.items():
            if doc_type == "other":
                continue
            for keyword in keywords:
                if keyword in search_text:
                    self.logger.info(
                        f"Detected document type: {doc_type} "
                        f"(matched keyword: {keyword})"
                    )
                    return doc_type

        # Default to "other" if no match
        return "other"

    def _validate_pdf(self, file_path: str) -> bool:
        """
        Validate that PDF can be opened and read.

        Args:
            file_path: Path to PDF file

        Returns:
            True if valid, False otherwise
        """
        try:
            if not self.fitz_available:
                self.logger.warning("PyMuPDF not available for PDF validation")
                return True  # Assume valid if can't check
                
            doc = self.fitz.open(file_path)
            # Try to access first page
            if len(doc) > 0:
                page = doc[0]
                # Try to get page text
                _ = page.get_text()
            doc.close()
            return True
        except Exception as e:
            self.logger.error(f"PDF validation failed: {e}")
            return False
