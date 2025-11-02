"""
Alert-related Pydantic schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    """Response schema for alert."""

    alert_id: str
    title: str
    description: str
    severity: str = Field(..., description="critical, high, medium, low")
    role: str = Field(..., description="front, compliance, legal")
    status: str = Field(..., description="pending, acknowledged, escalated, resolved")
    source_type: str = Field(..., description="transaction, document")
    source_id: str
    remediation_workflow: Optional[str] = None
    sla_deadline: datetime
    metadata: Dict[str, Any]
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    escalated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    sla_breached: bool = Field(..., description="Whether SLA deadline has passed")

    class Config:
        json_schema_extra = {
            "example": {
                "alert_id": "ALT-001",
                "title": "Missing EDD Documentation",
                "description": "Transaction flagged for missing Enhanced Due Diligence documentation",
                "severity": "high",
                "role": "compliance",
                "status": "pending",
                "source_type": "transaction",
                "source_id": "TXN-2024-001",
                "remediation_workflow": "Request additional documentation from customer",
                "sla_deadline": "2024-11-03T10:30:00Z",
                "metadata": {
                    "transaction_amount": 100000.00,
                    "jurisdiction": "HK",
                },
                "created_at": "2024-11-01T10:30:00Z",
                "acknowledged_at": None,
                "acknowledged_by": None,
                "escalated_at": None,
                "resolved_at": None,
                "resolved_by": None,
                "sla_breached": False,
            }
        }


class AlertListResponse(BaseModel):
    """Response schema for list of alerts."""

    total: int
    alerts: List[AlertResponse]
    page: int = 1
    page_size: int = 100
    filters: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "total": 15,
                "alerts": [],  # List of AlertResponse objects
                "page": 1,
                "page_size": 100,
                "filters": {
                    "role": "compliance",
                    "status": "pending",
                    "severity": "high",
                },
            }
        }


class AlertAcknowledgeRequest(BaseModel):
    """Request to acknowledge an alert."""

    acknowledged_by: str = Field(..., description="User ID of acknowledger")
    notes: Optional[str] = Field(None, description="Optional acknowledgment notes")

    class Config:
        json_schema_extra = {
            "example": {
                "acknowledged_by": "compliance_officer_123",
                "notes": "Reviewing documentation now",
            }
        }


class AlertDashboardResponse(BaseModel):
    """Dashboard statistics for alerts."""

    total: int
    by_status: Dict[str, int] = Field(..., description="Count by status")
    by_severity: Dict[str, int] = Field(..., description="Count by severity")
    by_role: Dict[str, int] = Field(..., description="Count by role")
    sla_breached: int
    pending_critical: int
    pending_high: int
    
    # Time-based metrics
    avg_resolution_time_hours: Optional[float] = None
    avg_acknowledgment_time_hours: Optional[float] = None
    
    # Recent alerts
    recent_critical: List[AlertResponse]
    recent_high: List[AlertResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "total": 45,
                "by_status": {
                    "pending": 20,
                    "acknowledged": 15,
                    "escalated": 3,
                    "resolved": 7,
                },
                "by_severity": {
                    "critical": 2,
                    "high": 10,
                    "medium": 20,
                    "low": 13,
                },
                "by_role": {
                    "front": 15,
                    "compliance": 25,
                    "legal": 5,
                },
                "sla_breached": 3,
                "pending_critical": 2,
                "pending_high": 8,
                "avg_resolution_time_hours": 24.5,
                "avg_acknowledgment_time_hours": 2.3,
                "recent_critical": [],
                "recent_high": [],
            }
        }
