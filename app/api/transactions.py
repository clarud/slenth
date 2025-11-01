"""
Transaction API Endpoints - Part 1 Transaction Monitoring

Endpoints:
- POST /transactions - Submit transaction for async processing
- GET /transactions/{transaction_id}/status - Check processing status
- GET /transactions/{transaction_id}/compliance - Get compliance analysis results
"""

import logging
from typing import Any, Dict

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.transaction import (
    ComplianceAnalysisResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionStatusResponse,
)
from db.database import get_db
from db.models import Transaction, ComplianceAnalysis, AuditLog
from services.audit import AuditService
from worker.tasks import process_transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """
    Submit a transaction for async processing via Celery.

    This endpoint queues the transaction for processing and returns immediately
    with a task ID for tracking.

    Args:
        transaction: Transaction data
        db: Database session

    Returns:
        Response with task ID for tracking
    """
    transaction_id = transaction.transaction_id

    logger.info(f"Submitting transaction {transaction_id} for processing")

    try:
        # Idempotency: if this transaction_id already exists, return its task info
        existing = (
            db.query(Transaction)
            .filter(Transaction.transaction_id == transaction_id)
            .first()
        )
        if existing:
            existing_task_id = (existing.raw_data or {}).get("task_id")
            return TransactionResponse(
                transaction_id=transaction_id,
                task_id=existing_task_id or "unknown",
                status="queued" if existing_task_id else "unknown",
                message="Transaction already exists",
                submitted_at=existing.created_at,
            )

        # Map request schema to DB model fields only (avoid invalid kwargs)
        # Derivations:
        # - pep_indicator from customer_is_pep
        # - sanctions_hit from sanctions_screening string
        # - customer_segment from customer_type
        sanctions_str = (transaction.sanctions_screening or "").strip().lower() if hasattr(transaction, "sanctions_screening") else ""
        sanctions_hit = sanctions_str in {"hit", "positive", "match", "true", "yes"}

        db_transaction = Transaction(
            transaction_id=transaction_id,
            booking_jurisdiction=transaction.booking_jurisdiction,
            regulator=transaction.regulator,
            booking_datetime=transaction.booking_datetime,
            value_date=transaction.value_date,
            amount=transaction.amount,
            currency=transaction.currency,
            channel=transaction.channel,
            product_type=transaction.product_type,
            originator_name=transaction.originator_name,
            originator_account=transaction.originator_account,
            originator_country=transaction.originator_country,
            beneficiary_name=transaction.beneficiary_name,
            beneficiary_account=transaction.beneficiary_account,
            beneficiary_country=transaction.beneficiary_country,
            swift_mt=transaction.swift_mt,
            ordering_institution_bic=getattr(transaction, "ordering_institution_bic", None),
            beneficiary_institution_bic=getattr(transaction, "beneficiary_institution_bic", None),
            swift_f50_present=getattr(transaction, "swift_f50_present", False),
            swift_f59_present=getattr(transaction, "swift_f59_present", False),
            swift_f70_purpose=getattr(transaction, "swift_f70_purpose", None),
            swift_f71_charges=getattr(transaction, "swift_f71_charges", None),
            pep_indicator=getattr(transaction, "customer_is_pep", False),
            sanctions_hit=sanctions_hit,
            customer_id=transaction.customer_id,
            customer_segment=getattr(transaction, "customer_type", None),
            customer_risk_rating=transaction.customer_risk_rating,
            raw_data=transaction.dict(),
        )
        db.add(db_transaction)
        db.flush()  # get PK without committing

        # Enqueue task to Celery
        task = process_transaction.delay(transaction.dict())

        # Persist task_id into the same transaction before commit
        data = db_transaction.raw_data or {}
        data["task_id"] = task.id
        db_transaction.raw_data = data
        db.commit()

        # Log audit trail
        audit_service = AuditService(db)
        audit_service.log_action(
            action_type="SUBMIT_TRANSACTION",
            entity_type="transaction",
            entity_id=transaction_id,
            user_id="system",
            details={"task_id": task.id},
        )

        logger.info(f"Transaction {transaction_id} queued with task_id={task.id}")

        return TransactionResponse(
            transaction_id=transaction_id,
            task_id=task.id,
            status="queued",
            message="Transaction queued for processing",
            submitted_at=db_transaction.created_at,
        )

    except Exception as e:
        logger.error(f"Error submitting transaction {transaction_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting transaction: {str(e)}",
        )


@router.get("/{transaction_id}/status", response_model=TransactionStatusResponse)
async def get_transaction_status(
    transaction_id: str,
    db: Session = Depends(get_db),
) -> TransactionStatusResponse:
    """
    Get processing status of a transaction.

    Args:
        transaction_id: Transaction ID
        db: Database session

    Returns:
        Status information
    """
    # Get transaction from database
    transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    # Get task ID from audit log or transaction metadata
    # For simplicity, we'll need to track task_id in transaction record
    # This is a simplified version
    # task_id is stored inside Transaction.raw_data
    task_id = (transaction.raw_data or {}).get("task_id")

    if not task_id:
        # Fallback: retrieve task_id from audit logs if raw_data missing it
        audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.action_type == "SUBMIT_TRANSACTION",
                AuditLog.target_type == "transaction",
                AuditLog.target_id == transaction_id,
            )
            .order_by(AuditLog.timestamp.desc())
            .first()
        )
        if audit and audit.context_data and audit.context_data.get("task_id"):
            task_id = audit.context_data.get("task_id")
            # Backfill into transaction.raw_data for future lookups
            try:
                data = transaction.raw_data or {}
                data["task_id"] = task_id
                transaction.raw_data = data
                db.add(transaction)
                db.commit()
            except Exception:
                db.rollback()

    if not task_id:
        return TransactionStatusResponse(
            transaction_id=transaction_id,
            task_id="unknown",
            status="unknown",
            progress=None,
        )

    # Check Celery task status
    task_result = AsyncResult(task_id)

    status_map = {
        "PENDING": "queued",
        "STARTED": "processing",
        "PROCESSING": "processing",
        "SUCCESS": "completed",
        "FAILURE": "failed",
        "RETRY": "processing",
    }

    celery_status = task_result.state
    mapped_status = status_map.get(celery_status, "unknown")

    # Get progress if available
    progress = None
    current_step = None
    error = None

    if celery_status == "PROCESSING" and task_result.info:
        progress = task_result.info.get("progress")
        current_step = task_result.info.get("current_step")
    elif celery_status == "FAILURE":
        error = str(task_result.info) if task_result.info else "Unknown error"

    return TransactionStatusResponse(
        transaction_id=transaction_id,
        task_id=task_id,
        status=mapped_status,
        progress=progress,
        current_step=current_step,
        error=error,
        completed_at=None,  # Would need to track completion time
    )


@router.get("/{transaction_id}/compliance", response_model=ComplianceAnalysisResponse)
async def get_compliance_analysis(
    transaction_id: str,
    db: Session = Depends(get_db),
) -> ComplianceAnalysisResponse:
    """
    Get compliance analysis results for a transaction.

    This endpoint returns the full compliance analysis after processing is complete.

    Args:
        transaction_id: Transaction ID
        db: Database session

    Returns:
        Compliance analysis results
    """
    # Get compliance analysis from database
    analysis = (
        db.query(ComplianceAnalysis)
        .filter(ComplianceAnalysis.transaction_id == transaction_id)
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance analysis not found for transaction {transaction_id}",
        )

    # Format response
    return ComplianceAnalysisResponse(
        transaction_id=transaction_id,
        risk_band=analysis.risk_band,
        risk_score=analysis.risk_score,
        rules_evaluated=len(analysis.metadata.get("applicable_rules", [])),
        rules_violated=len(
            [r for r in analysis.metadata.get("control_results", []) if r.get("violated")]
        ),
        applicable_rules=analysis.metadata.get("applicable_rules", []),
        patterns_detected=analysis.metadata.get("patterns_detected", []),
        bayesian_posterior=analysis.metadata.get("bayesian_posterior", {}),
        compliance_summary=analysis.summary,
        recommendations=analysis.metadata.get("recommendations", []),
        alerts_generated=analysis.metadata.get("alerts_generated", []),
        remediation_actions=analysis.metadata.get("remediation_actions", []),
        processed_at=analysis.created_at,
        processing_time_seconds=analysis.metadata.get("processing_time", 0),
    )
