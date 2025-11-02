"""
Alerts API Endpoints

Endpoints for managing and viewing alerts.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.schemas.alert import (
    AlertAcknowledgeRequest,
    AlertDashboardResponse,
    AlertListResponse,
    AlertResponse,
)
from db.database import get_db
from db.models import Alert, AlertRole, AlertSeverity, AlertStatus
from services.alert_service import AlertService
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    role: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> AlertListResponse:
    """List alerts with filtering."""
    query = db.query(Alert)

    if role:
        query = query.filter(Alert.role == role)
    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)

    total = query.count()
    alerts = query.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return AlertListResponse(
        total=total,
        alerts=[
            AlertResponse(
                alert_id=alert.alert_id,
                title=alert.title,
                description=alert.description,
                severity=alert.severity.value,
                role=alert.role.value,
                status=alert.status.value,
                source_type=alert.source_type,
                source_id=str(alert.transaction_id) if alert.transaction_id else str(alert.document_id),
                remediation_workflow=alert.remediation_workflow,
                sla_deadline=alert.sla_deadline,
                metadata=alert.context or {},
                created_at=alert.created_at,
                acknowledged_at=alert.acknowledged_at,
                acknowledged_by=alert.acknowledged_by,
                resolved_at=alert.resolved_at,
                resolved_by=alert.resolved_by,
                sla_breached=(alert.sla_deadline < datetime.utcnow() if alert.sla_deadline else False),
            )
            for alert in alerts
        ],
        page=page,
        page_size=page_size,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
) -> AlertResponse:
    """Get a specific alert."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    return AlertResponse(
        alert_id=alert.alert_id,
        title=alert.title,
        description=alert.description,
        severity=alert.severity.value,
        role=alert.role.value,
        status=alert.status.value,
        source_type=alert.source_type,
        source_id=str(alert.transaction_id) if alert.transaction_id else str(alert.document_id),
        remediation_workflow=alert.remediation_workflow,
        sla_deadline=alert.sla_deadline,
        metadata=alert.context or {},
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        resolved_at=alert.resolved_at,
        resolved_by=alert.resolved_by,
        sla_breached=(alert.sla_deadline < datetime.utcnow() if alert.sla_deadline else False),
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    request: AlertAcknowledgeRequest,
    db: Session = Depends(get_db),
) -> AlertResponse:
    """Acknowledge an alert."""
    alert_service = AlertService(db)

    try:
        alert = alert_service.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by=request.acknowledged_by,
        )

        return AlertResponse(
            alert_id=alert.alert_id,
            title=alert.title,
            description=alert.description,
            severity=alert.severity.value,
            role=alert.role.value,
            status=alert.status.value,
            source_type=alert.source_type,
            source_id=str(alert.transaction_id) if alert.transaction_id else str(alert.document_id),
            remediation_workflow=alert.remediation_workflow,
            sla_deadline=alert.sla_deadline,
            metadata=alert.context or {},
            created_at=alert.created_at,
            acknowledged_at=alert.acknowledged_at,
            acknowledged_by=alert.acknowledged_by,
            resolved_at=alert.resolved_at,
            resolved_by=alert.resolved_by,
            sla_breached=(alert.sla_deadline < datetime.utcnow()),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/dashboard/stats", response_model=AlertDashboardResponse)
async def get_dashboard_stats(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> AlertDashboardResponse:
    """Get dashboard statistics for alerts."""
    alert_service = AlertService(db)

    role_enum = AlertRole(role) if role else None
    stats = alert_service.get_dashboard_stats(role=role_enum)

    # Get recent critical and high alerts
    recent_critical = alert_service.get_alerts_by_role(
        role=role_enum or AlertRole.COMPLIANCE,
        severity=AlertSeverity.CRITICAL,
        limit=5,
    )

    recent_high = alert_service.get_alerts_by_role(
        role=role_enum or AlertRole.COMPLIANCE,
        severity=AlertSeverity.HIGH,
        limit=5,
    )

    return AlertDashboardResponse(
        total=stats["total"],
        by_status=stats["by_status"],
        by_severity=stats["by_severity"],
        by_role={"front": 0, "compliance": 0, "legal": 0},  # Simplified
        sla_breached=stats["sla_breached"],
        pending_critical=stats["by_severity"].get("critical", 0),
        pending_high=stats["by_severity"].get("high", 0),
        avg_resolution_time_hours=None,
        avg_acknowledgment_time_hours=None,
        recent_critical=[],
        recent_high=[],
    )


@router.get("/transaction/{transaction_id}", response_model=AlertListResponse)
async def get_transaction_alerts(
    transaction_id: str,
    db: Session = Depends(get_db),
) -> AlertListResponse:
    """Get all alerts for a specific transaction."""
    from db.models import Transaction
    
    # First get the transaction by transaction_id string
    transaction = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )
    
    # Get all alerts for this transaction using the UUID
    alerts = db.query(Alert).filter(Alert.transaction_id == transaction.id).order_by(Alert.created_at.desc()).all()
    
    return AlertListResponse(
        total=len(alerts),
        alerts=[
            AlertResponse(
                alert_id=alert.alert_id,
                title=alert.title,
                description=alert.description,
                severity=alert.severity.value,
                role=alert.role.value,
                status=alert.status.value,
                source_type=alert.source_type,
                source_id=str(alert.transaction_id) if alert.transaction_id else str(alert.document_id),
                remediation_workflow=alert.remediation_workflow,
                sla_deadline=alert.sla_deadline,
                metadata={
                    "context": alert.context,
                    "evidence": alert.evidence,
                },
                created_at=alert.created_at,
                acknowledged_at=alert.acknowledged_at,
                acknowledged_by=alert.acknowledged_by,
                resolved_at=alert.resolved_at,
                resolved_by=alert.resolved_by,
                sla_breached=(alert.sla_deadline < datetime.utcnow() if alert.sla_deadline else False),
            )
            for alert in alerts
        ],
        page=1,
        page_size=len(alerts),
    )


@router.post("/{alert_id}/remediation/trigger", response_model=dict)
async def trigger_remediation_workflow(
    alert_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Trigger remediation workflow for an alert (placeholder implementation)."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    
    # Placeholder: In production, this would trigger actual remediation workflow
    logger.info(f"Remediation workflow triggered for alert {alert_id}")
    
    return {
        "success": True,
        "message": f"Remediation workflow has been triggered for alert {alert_id}",
        "alert_id": alert_id,
        "workflow_status": "triggered"
    }


@router.post("/{alert_id}/remediation/reject", response_model=dict)
async def reject_remediation_workflow(
    alert_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Reject remediation workflow for an alert (placeholder implementation)."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    
    # Placeholder: In production, this would update alert status
    logger.info(f"Remediation workflow rejected for alert {alert_id}")
    
    return {
        "success": True,
        "message": f"Remediation workflow has been rejected for alert {alert_id}",
        "alert_id": alert_id,
        "workflow_status": "rejected"
    }
