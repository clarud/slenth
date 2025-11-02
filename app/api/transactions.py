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
from fastapi.encoders import jsonable_encoder
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


@router.get("", response_model=list)
async def list_transactions(
    skip: int = 0,
    limit: int = 50,
    status_filter: str = None,
    db: Session = Depends(get_db),
):
    """
    List transactions with optional filtering.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return (max 100)
        status_filter: Filter by status (pending, processing, completed, failed)
        db: Database session
    
    Returns:
        List of transactions
    """
    from db.models import TransactionStatus
    
    # Limit the maximum to prevent overload
    limit = min(limit, 100)
    
    query = db.query(Transaction)
    
    # Apply status filter if provided
    if status_filter:
        try:
            status_enum = TransactionStatus[status_filter.upper()]
            query = query.filter(Transaction.status == status_enum)
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status filter. Valid values: {[s.value for s in TransactionStatus]}"
            )
    
    # Order by most recent first
    query = query.order_by(Transaction.created_at.desc())
    
    # Apply pagination
    transactions = query.offset(skip).limit(limit).all()
    
    # Convert to response format
    result = []
    for txn in transactions:
        # Get risk_band from compliance analysis if available
        risk_band = None
        if txn.compliance_analysis:
            risk_band = txn.compliance_analysis.risk_band.value if txn.compliance_analysis.risk_band else None
        
        result.append({
            "transaction_id": txn.transaction_id,
            "status": txn.status.value if txn.status else "unknown",
            "amount": float(txn.amount) if txn.amount else 0.0,
            "currency": txn.currency,
            "originator_country": txn.originator_country,
            "beneficiary_country": txn.beneficiary_country,
            "created_at": txn.created_at.isoformat() if txn.created_at else None,
            "processing_completed_at": txn.processing_completed_at.isoformat() if txn.processing_completed_at else None,
            "risk_band": risk_band,
        })
    
    return result


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

            # If the prior record is missing a task_id (from older runs), enqueue now and backfill.
            if not existing_task_id:
                try:
                    encoded_request = jsonable_encoder(transaction)
                    task = process_transaction.delay(encoded_request)
                    data = existing.raw_data or {}
                    data["task_id"] = task.id
                    existing.raw_data = data
                    db.add(existing)
                    db.commit()
                    existing_task_id = task.id
                except Exception:
                    db.rollback()

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

        # Encode request body into JSON-serializable form (convert datetimes, etc.)
        encoded_request = jsonable_encoder(transaction)

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
            raw_data=encoded_request,
        )
        db.add(db_transaction)
        db.flush()  # get PK without committing

        # Enqueue task to Celery
        task = process_transaction.delay(encoded_request)

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
    # Get transaction record first (to join and get transaction_id string)
    from db.models import Transaction
    
    transaction_record = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )
    
    if not transaction_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )
    
    # Get compliance analysis from database using the transaction's UUID
    analysis = (
        db.query(ComplianceAnalysis)
        .filter(ComplianceAnalysis.transaction_id == transaction_record.id)
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance analysis not found for transaction {transaction_id}",
        )

    # Extract data from actual columns (not metadata)
    applicable_rules = analysis.applicable_rules or []
    control_test_results = analysis.control_test_results or []
    pattern_detections = analysis.pattern_detections or {}
    
    # Count rules evaluated and violated
    rules_evaluated = len(applicable_rules)
    rules_violated = len([r for r in control_test_results if r.get("violated", False)])
    
    # Convert bayesian_posterior (stored as float 0-1) back to distribution format for display
    bayesian_risk_value = analysis.bayesian_posterior or 0.0
    # Create a distribution representation (all values as floats for schema compliance)
    bayesian_distribution = {
        "risk_value": float(bayesian_risk_value),
        "low": 1.0 - bayesian_risk_value if bayesian_risk_value < 0.1 else 0.0,
        "medium": bayesian_risk_value if 0.1 <= bayesian_risk_value < 0.4 else 0.0,
        "high": bayesian_risk_value if 0.4 <= bayesian_risk_value < 0.7 else 0.0,
        "critical": bayesian_risk_value if bayesian_risk_value >= 0.7 else 0.0,
    }
    
    # Format patterns for display
    patterns_detected_list = [
        {"pattern_type": k, "score": v}
        for k, v in pattern_detections.items()
    ] if isinstance(pattern_detections, dict) else []
    
    # Format response with data from actual database columns
    return ComplianceAnalysisResponse(
        transaction_id=transaction_id,
        risk_band=analysis.risk_band.value if hasattr(analysis.risk_band, 'value') else str(analysis.risk_band),
        risk_score=analysis.compliance_score,
        rules_evaluated=rules_evaluated,
        rules_violated=rules_violated,
        applicable_rules=applicable_rules,
        patterns_detected=patterns_detected_list,
        bayesian_posterior=bayesian_distribution,
        compliance_summary=analysis.compliance_summary or "",
        recommendations=[],  # Not stored separately, could extract from summary
        alerts_generated=[],  # Would need to query Alert table separately
        remediation_actions=[],  # Would need to query from related tables
        processed_at=analysis.created_at,
        processing_time_seconds=analysis.processing_time_seconds or 0.0,
    )


@router.get("/{transaction_id}/compliance/detailed")
async def get_detailed_compliance_analysis(
    transaction_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get detailed compliance analysis with all fields including control tests and evidence.
    
    This endpoint returns comprehensive compliance data including:
    - compliance_score and risk_band
    - applicable_rules (full list)
    - control_test_results (detailed test outcomes)
    - pattern_detections (all detected patterns)
    - bayesian_posterior (risk probability)
    - evidence_map (evidence mapping results)
    - compliance_summary (analyst report)
    - processing_time_seconds
    
    Args:
        transaction_id: Transaction ID
        db: Database session
        
    Returns:
        Detailed compliance analysis with all available fields
    """
    from db.models import Transaction, Alert
    
    # Get transaction record
    transaction_record = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )
    
    if not transaction_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )
    
    # Get compliance analysis
    analysis = (
        db.query(ComplianceAnalysis)
        .filter(ComplianceAnalysis.transaction_id == transaction_record.id)
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance analysis not found for transaction {transaction_id}",
        )
    
    # Get related alerts
    alerts = db.query(Alert).filter(
        Alert.transaction_id == transaction_record.id
    ).all()
    
    alerts_list = [
        {
            "alert_id": alert.alert_id,
            "severity": alert.severity.value if hasattr(alert.severity, 'value') else str(alert.severity),
            "role": alert.role.value if hasattr(alert.role, 'value') else str(alert.role),
            "status": alert.status.value if hasattr(alert.status, 'value') else str(alert.status),
            "title": alert.title,
            "alert_type": alert.alert_type,
            "sla_deadline": alert.sla_deadline.isoformat() if alert.sla_deadline else None,
        }
        for alert in alerts
    ]
    
    # Return all fields from ComplianceAnalysis
    return {
        "transaction_id": transaction_id,
        
        # Core risk assessment
        "compliance_score": analysis.compliance_score,
        "risk_band": analysis.risk_band.value if hasattr(analysis.risk_band, 'value') else str(analysis.risk_band),
        
        # Detailed analysis results (from JSONB columns)
        "applicable_rules": analysis.applicable_rules or [],
        "control_test_results": analysis.control_test_results or [],
        "pattern_detections": analysis.pattern_detections or {},
        "evidence_map": analysis.evidence_map or {},
        
        # Bayesian analysis
        "bayesian_posterior": analysis.bayesian_posterior or 0.0,
        "bayesian_interpretation": (
            "critical" if (analysis.bayesian_posterior or 0.0) >= 0.7 else
            "high" if (analysis.bayesian_posterior or 0.0) >= 0.4 else
            "medium" if (analysis.bayesian_posterior or 0.0) >= 0.1 else
            "low"
        ),
        
        # Summary and notes
        "compliance_summary": analysis.compliance_summary or "",
        "analyst_notes": analysis.analyst_notes or "",
        
        # Related alerts
        "alerts": alerts_list,
        
        # Metadata
        "processing_time_seconds": analysis.processing_time_seconds or 0.0,
        "analyzed_at": analysis.created_at.isoformat() if analysis.created_at else None,
        
        # Transaction metadata
        "transaction_status": transaction_record.status.value if hasattr(transaction_record.status, 'value') else str(transaction_record.status),
        "transaction_completed_at": transaction_record.processing_completed_at.isoformat() if transaction_record.processing_completed_at else None,
    }
