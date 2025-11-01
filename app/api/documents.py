"""
Document API Endpoints - Part 2 Document Corroboration

Endpoints:
- POST /documents/upload - Upload and process document (synchronous)
- GET /documents/{document_id}/risk - Get risk assessment
- GET /documents/{document_id}/report - Download PDF report
- GET /documents/{document_id}/findings - Get detailed findings
- POST /documents/{document_id}/acknowledge - Acknowledge document review
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.schemas.document import (
    DocumentAcknowledgeRequest,
    DocumentFindingsResponse,
    DocumentRiskResponse,
    DocumentUploadResponse,
    FindingDetail,
)
from db.database import get_db
from db.models import Document
from services.audit import AuditService
from services.llm import LLMService
from workflows.document_workflow import execute_document_workflow
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Upload and process a document SYNCHRONOUSLY.

    Unlike Part 1, this endpoint processes the document immediately and returns
    complete results in the response. No Celery/Redis queuing.

    Args:
        file: Uploaded file
        db: Database session

    Returns:
        Complete processing results
    """
    filename = file.filename
    file_size = 0

    logger.info(f"Uploading document: {filename}")

    try:
        # Save uploaded file
        upload_dir = settings.uploaded_docs_path
        os.makedirs(upload_dir, exist_ok=True)

        document_id = f"DOC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        file_path = os.path.join(upload_dir, f"{document_id}_{filename}")

        # Write file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            file_size = len(content)

        # Create document record
        db_document = Document(
            document_id=document_id,
            filename=filename,
            file_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            file_path=file_path,
            status="processing",
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        # Log audit trail
        audit_service = AuditService(db)
        audit_service.log_document_upload(
            document_id=document_id,
            user_id="system",
            filename=filename,
            file_size=file_size,
        )

        # Execute workflow SYNCHRONOUSLY
        llm_service = LLMService()

        document_data = {
            "document_id": document_id,
            "filename": filename,
            "file_type": file.content_type,
            "file_size": file_size,
        }

        # Run workflow - this blocks until complete
        import asyncio
        final_state = await execute_document_workflow(
            document=document_data,
            file_path=file_path,
            db_session=db,
            llm_service=llm_service,
        )

        # Update document record with results
        db_document.status = "completed"
        db_document.risk_score = final_state.get("risk_score")
        db_document.risk_level = final_state.get("risk_level")
        db_document.metadata = {
            "ocr_text_length": len(final_state.get("ocr_text", "")),
            "pages_processed": final_state.get("pages_processed", 0),
            "total_findings": (
                len(final_state.get("format_findings", []))
                + len(final_state.get("content_findings", []))
                + len(final_state.get("image_findings", []))
                + len(final_state.get("background_check_findings", []))
            ),
        }
        db.commit()
        db.refresh(db_document)

        processing_time = (
            final_state.get("processing_end_time", 0)
            - final_state.get("processing_start_time", 0)
        )

        logger.info(
            f"Document {document_id} processed successfully in {processing_time:.2f}s"
        )

        # Return complete results
        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            file_size=file_size,
            file_type=file.content_type or "application/octet-stream",
            status="completed",
            uploaded_at=db_document.created_at,
            risk_score=final_state.get("risk_score"),
            risk_level=final_state.get("risk_level"),
            processing_completed_at=datetime.utcnow(),
            processing_time_seconds=processing_time,
        )

    except Exception as e:
        logger.error(f"Error uploading/processing document: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}",
        )


@router.get("/{document_id}/risk", response_model=DocumentRiskResponse)
async def get_document_risk(
    document_id: str,
    db: Session = Depends(get_db),
) -> DocumentRiskResponse:
    """
    Get risk assessment for a document.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        Risk assessment details
    """
    document = db.query(Document).filter(Document.document_id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get findings from document_findings table
    # For simplicity, using metadata
    findings = document.metadata.get("findings", {})

    return DocumentRiskResponse(
        document_id=document_id,
        risk_score=document.risk_score or 0.0,
        risk_level=document.risk_level or "Unknown",
        format_risk=findings.get("format_risk", 0.0),
        content_risk=findings.get("content_risk", 0.0),
        image_risk=findings.get("image_risk", 0.0),
        background_check_risk=findings.get("background_check_risk", 0.0),
        total_findings=document.metadata.get("total_findings", 0),
        critical_findings=findings.get("critical_findings", 0),
        high_findings=findings.get("high_findings", 0),
        medium_findings=findings.get("medium_findings", 0),
        low_findings=findings.get("low_findings", 0),
        key_issues=findings.get("key_issues", []),
        recommendations=findings.get("recommendations", []),
        assessed_at=document.updated_at,
    )


@router.get("/{document_id}/report")
async def download_report(
    document_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """
    Download PDF report for a document.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        PDF file
    """
    document = db.query(Document).filter(Document.document_id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    report_path = document.metadata.get("report_path")

    if not report_path or not os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found for document {document_id}",
        )

    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=f"report_{document_id}.pdf",
    )


@router.get("/{document_id}/findings", response_model=DocumentFindingsResponse)
async def get_document_findings(
    document_id: str,
    db: Session = Depends(get_db),
) -> DocumentFindingsResponse:
    """
    Get detailed findings for a document.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        Detailed findings
    """
    document = db.query(Document).filter(Document.document_id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get findings from metadata (in production, would query document_findings table)
    findings = document.metadata.get("findings", {})

    return DocumentFindingsResponse(
        document_id=document_id,
        ocr_text=findings.get("ocr_text", "")[:1000],  # Truncate for API
        ocr_confidence=findings.get("ocr_confidence", 0.0),
        pages_processed=document.metadata.get("pages_processed", 0),
        format_findings=[],  # Would load from database
        content_findings=[],
        image_findings=[],
        background_check_findings=[],
        cross_reference_findings=[],
        extracted_entities=findings.get("extracted_entities", {}),
        report_url=f"/documents/{document_id}/report",
    )


@router.post("/{document_id}/acknowledge")
async def acknowledge_document(
    document_id: str,
    request: DocumentAcknowledgeRequest,
    db: Session = Depends(get_db),
) -> Dict:
    """
    Acknowledge document review.

    Args:
        document_id: Document ID
        request: Acknowledgment data
        db: Database session

    Returns:
        Success message
    """
    document = db.query(Document).filter(Document.document_id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Update document with review info
    document.metadata["reviewed_by"] = request.reviewed_by
    document.metadata["review_notes"] = request.review_notes
    document.metadata["approved"] = request.approved
    document.metadata["reviewed_at"] = datetime.utcnow().isoformat()

    if request.approved:
        document.status = "approved"
    else:
        document.status = "rejected"

    db.commit()

    # Log audit
    audit_service = AuditService(db)
    audit_service.log_action(
        action_type="ACKNOWLEDGE_DOCUMENT",
        entity_type="document",
        entity_id=document_id,
        user_id=request.reviewed_by,
        details={"approved": request.approved, "notes": request.review_notes},
    )

    return {
        "document_id": document_id,
        "status": "acknowledged",
        "approved": request.approved,
    }
