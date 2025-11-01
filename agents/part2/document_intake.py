"""
DocumentIntakeAgent - Accept uploads and normalize to internal format

Responsibilities:
1. Validate file type (PDF only)
2. Check file size limits
3. Detect document type from metadata/filename
4. Extract basic document metadata
5. Normalize file path and store location
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    import PyMuPDF as fitz

from agents import Part2Agent
from config import settings

logger = logging.getLogger(__name__)


class DocumentIntakeAgent(Part2Agent):
    """Agent: Accept uploads and normalize to internal format"""

    # Supported document types and their indicators
    DOCUMENT_TYPES = {
        "purchase_agreement": ["purchase", "agreement", "sale", "buy"],
        "proof_of_address": ["address", "utility", "bill", "statement"],
        "id_document": ["passport", "id", "identity", "license"],
        "bank_statement": ["bank", "statement", "account"],
        "contract": ["contract", "terms", "conditions"],
        "invoice": ["invoice", "receipt", "payment"],
        "other": []
    }

    def __init__(self):
        super().__init__("document_intake")
        self.max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
        self.allowed_types = settings.document_allowed_types

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute document intake: validate, classify, and normalize document.

        Args:
            state: Workflow state containing:
                - file_path: Path to uploaded document
                - document: Document metadata dict
                - document_id: Unique document ID

        Returns:
            Updated state with:
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

        try:
            # Step 1: Validate file exists
            if not file_path or not os.path.exists(file_path):
                errors.append("File does not exist")
                state["errors"] = errors
                state["file_valid"] = False
                return state

            # Step 2: Validate file type (PDF only)
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            if file_extension not in self.allowed_types:
                errors.append(
                    f"Invalid file type: {file_extension}. "
                    f"Allowed types: {', '.join(self.allowed_types)}"
                )
                state["errors"] = errors
                state["file_valid"] = False
                return state

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

            # Step 4: Extract PDF metadata
            metadata = self._extract_pdf_metadata(file_path)

            # Step 5: Detect document type
            document_type = self._detect_document_type(
                file_path=file_path,
                metadata=metadata,
                provided_type=document.get("document_type")
            )

            # Step 6: Validate PDF is not corrupted
            if not self._validate_pdf(file_path):
                errors.append("PDF file is corrupted or cannot be opened")
                state["errors"] = errors
                state["file_valid"] = False
                return state

            # Success - file is valid
            file_valid = True
            self.logger.info(
                f"Document intake successful: {document_id}, "
                f"type={document_type}, pages={metadata.get('page_count')}"
            )

        except Exception as e:
            self.logger.error(f"Error in document intake: {e}")
            errors.append(f"Document intake error: {str(e)}")
            file_valid = False

        # Update state
        state["file_valid"] = file_valid
        state["document_type"] = document_type
        state["metadata"] = metadata
        state["errors"] = errors
        state["document_intake_executed"] = True

        return state

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
            doc = fitz.open(file_path)
            
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
            doc = fitz.open(file_path)
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
