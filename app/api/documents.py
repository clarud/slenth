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

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Form
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
    transaction_id: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Upload and process a document SYNCHRONOUSLY (PDF, JPEG, PNG).

    Two modes:
    1. WITH transaction_id: Links document to Part 1 transaction, stores results in DB
    2. WITHOUT transaction_id: Standalone analysis, returns results only (no DB storage of findings)

    Args:
        file: Uploaded file (PDF, JPEG, PNG)
        transaction_id: Optional transaction ID to link document to Part 1
        document_type: Optional document type hint (purchase_agreement, id_document, etc.)
        db: Database session

    Returns:
        Complete processing results including risk assessment and findings
    """
    filename = file.filename
    file_size = 0
    
    # Validate file type
    file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
    if file_extension not in ['pdf', 'jpg', 'jpeg', 'png']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file_extension}. Supported: pdf, jpg, jpeg, png"
        )

    logger.info(f"Uploading document: {filename}, transaction_id: {transaction_id or 'standalone'}, type: {document_type or 'auto-detect'}")

    try:
        # Validate transaction exists if provided
        if transaction_id:
            from db.models import Transaction
            transaction = db.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).first()
            
            if not transaction:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Transaction {transaction_id} not found"
                )
            
            logger.info(f"Linking document to transaction: {transaction_id}")

        # Save uploaded file
        upload_dir = settings.upload_dir
        os.makedirs(upload_dir, exist_ok=True)

        document_id = f"DOC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')[:20]}"
        file_path = os.path.join(upload_dir, f"{document_id}_{filename}")

        # Write file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            file_size = len(content)

        # Create document record
        from db.models import DocumentStatus
        db_document = Document(
            document_id=document_id,
            filename=filename,
            file_type=file_extension,
            mime_type=file.content_type or "application/octet-stream",
            file_size_bytes=file_size,
            file_path=file_path,
            status=DocumentStatus.PROCESSING,
            transaction_id=transaction_id,  # Link to Part 1 transaction (or None for standalone)
            document_type=document_type,  # Optional type hint
            processing_started_at=datetime.utcnow(),
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
            "transaction_id": transaction_id,  # Pass transaction_id to workflow
            "filename": filename,
            "file_type": file_extension,
            "file_size": file_size,
            "document_type": document_type,
        }

        # Run Part 2 workflow - this blocks until complete
        final_state = await execute_document_workflow(
            document=document_data,
            file_path=file_path,
            db_session=db,
            llm_service=llm_service,
        )

        processing_time = (
            final_state.get("processing_end_time", 0)
            - final_state.get("processing_start_time", 0)
        )

        # Calculate total findings
        total_findings = (
            len(final_state.get("format_findings", []))
            + len(final_state.get("content_findings", []))
            + len(final_state.get("image_findings", []))
            + len(final_state.get("background_check_findings", []))
            + len(final_state.get("cross_reference_findings", []))
        )

        # Update document record with results
        db_document.status = DocumentStatus.COMPLETED
        db_document.risk_score = final_state.get("overall_risk_score")  # Fixed: agent outputs "overall_risk_score"
        db_document.risk_band = final_state.get("risk_band")
        db_document.processing_completed_at = datetime.utcnow()
        db_document.workflow_metadata = {
            "ocr_text_length": len(final_state.get("ocr_text", "")),
            "pages_processed": final_state.get("metadata", {}).get("page_count", 1),
            "total_findings": total_findings,
            "processing_time_seconds": processing_time,
            "workflow_state": {
                "format_findings": final_state.get("format_findings", []),
                "content_findings": final_state.get("content_findings", []),
                "image_findings": final_state.get("image_findings", []),
                "background_check_findings": final_state.get("background_check_findings", []),
                "cross_reference_findings": final_state.get("cross_reference_findings", []),
                "risk_factors": final_state.get("risk_factors", []),
                "overall_risk_score": final_state.get("overall_risk_score"),
                "risk_band": final_state.get("risk_band"),
                "report_path": final_state.get("report_path"),
            }
        }

        # If transaction_id provided, store detailed findings in DB
        if transaction_id:
            from db.models import DocumentFinding
            
            # Store all findings in document_findings table
            all_findings = []
            
            # Format findings
            for finding in final_state.get("format_findings", []):
                all_findings.append(DocumentFinding(
                    document_id=db_document.id,
                    finding_type="format",
                    finding_category=finding.get("category", "unknown"),
                    finding_severity=finding.get("severity", "low"),
                    finding_description=finding.get("description", ""),
                    finding_details=finding,
                    detected_at=datetime.utcnow()
                ))
            
            # Content/NLP findings
            for finding in final_state.get("content_findings", []):
                all_findings.append(DocumentFinding(
                    document_id=db_document.id,
                    finding_type="nlp",
                    finding_category=finding.get("category", "unknown"),
                    finding_severity=finding.get("severity", "low"),
                    finding_description=finding.get("description", ""),
                    finding_details=finding,
                    detected_at=datetime.utcnow()
                ))
            
            # Image forensics findings
            for finding in final_state.get("image_findings", []):
                all_findings.append(DocumentFinding(
                    document_id=db_document.id,
                    finding_type="image_forensics",
                    finding_category=finding.get("category", "unknown"),
                    finding_severity=finding.get("severity", "low"),
                    finding_description=finding.get("description", ""),
                    finding_details=finding,
                    detected_at=datetime.utcnow()
                ))
            
            # Background check findings
            for finding in final_state.get("background_check_findings", []):
                all_findings.append(DocumentFinding(
                    document_id=db_document.id,
                    finding_type="background_check",
                    finding_category=finding.get("category", "unknown"),
                    finding_severity=finding.get("severity", "low"),
                    finding_description=finding.get("description", ""),
                    finding_details=finding,
                    detected_at=datetime.utcnow()
                ))
            
            # Cross-reference findings
            for finding in final_state.get("cross_reference_findings", []):
                all_findings.append(DocumentFinding(
                    document_id=db_document.id,
                    finding_type="cross_reference",
                    finding_category=finding.get("category", "unknown"),
                    finding_severity=finding.get("severity", "low"),
                    finding_description=finding.get("description", ""),
                    finding_details=finding,
                    detected_at=datetime.utcnow()
                ))
            
            # Bulk insert findings
            if all_findings:
                db.bulk_save_objects(all_findings)
                logger.info(f"Stored {len(all_findings)} findings for document {document_id} linked to transaction {transaction_id}")
        
        db.commit()
        db.refresh(db_document)

        logger.info(
            f"Document {document_id} processed successfully in {processing_time:.2f}s "
            f"(transaction_id: {transaction_id or 'standalone'})"
        )

        # Return complete results
        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            file_size=file_size,
            file_type=file_extension,
            status="completed",
            transaction_id=transaction_id,
            uploaded_at=db_document.created_at,
            risk_score=final_state.get("risk_score"),
            risk_level=final_state.get("risk_band"),
            processing_completed_at=datetime.utcnow(),
            processing_time_seconds=processing_time,
            total_findings=total_findings,
            findings_summary={
                "format": len(final_state.get("format_findings", [])),
                "content": len(final_state.get("content_findings", [])),
                "image_forensics": len(final_state.get("image_findings", [])),
                "background_check": len(final_state.get("background_check_findings", [])),
                "cross_reference": len(final_state.get("cross_reference_findings", [])),
            },
            report_path=final_state.get("report_path"),
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
    # For simplicity, using workflow_metadata
    workflow_meta = document.workflow_metadata or {}
    findings = workflow_meta.get("findings", {})

    return DocumentRiskResponse(
        document_id=document_id,
        risk_score=document.risk_score or 0.0,
        risk_level=document.risk_band or "Unknown",
        format_risk=findings.get("format_risk", 0.0),
        content_risk=findings.get("content_risk", 0.0),
        image_risk=findings.get("image_risk", 0.0),
        background_check_risk=findings.get("background_check_risk", 0.0),
        total_findings=workflow_meta.get("total_findings", 0),
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

    workflow_meta = document.workflow_metadata or {}
    report_path = workflow_meta.get("report_path")

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
        Detailed findings including full workflow metadata
    """
    document = db.query(Document).filter(Document.document_id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Return full document data including workflow_metadata
    return DocumentFindingsResponse(
        document_id=document_id,
        filename=document.filename,
        risk_level=document.risk_band,
        risk_score=document.risk_score,
        processing_completed_at=document.processing_completed_at.isoformat() if document.processing_completed_at else None,
        workflow_metadata=document.workflow_metadata or {},
        ocr_text="",  # Not needed in response
        ocr_confidence=0.0,
        pages_processed=document.workflow_metadata.get("pages_processed", 0) if document.workflow_metadata else 0,
        format_findings=[],
        content_findings=[],
        image_findings=[],
        background_check_findings=[],
        cross_reference_findings=[],
        extracted_entities={},
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
    workflow_meta = document.workflow_metadata or {}
    workflow_meta["reviewed_by"] = request.reviewed_by
    workflow_meta["review_notes"] = request.review_notes
    workflow_meta["approved"] = request.approved
    workflow_meta["reviewed_at"] = datetime.utcnow().isoformat()
    document.workflow_metadata = workflow_meta

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
