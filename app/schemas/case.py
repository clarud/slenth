"""
Case management-related Pydantic schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    """Schema for creating a new case."""

    title: str = Field(..., description="Case title")
    description: str = Field(..., description="Detailed case description")
    case_type: str = Field(..., description="Type of case: AML, KYC, Fraud, Other")
    priority: str = Field(..., description="Priority: critical, high, medium, low")
    assigned_to: Optional[str] = Field(None, description="User ID of assignee")
    source_type: Optional[str] = Field(None, description="Source type: transaction, document, alert")
    source_id: Optional[str] = Field(None, description="ID of source entity")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional case metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Suspicious Transaction Pattern - Customer CUST-001",
                "description": "Multiple transactions detected showing structuring behavior",
                "case_type": "AML",
                "priority": "high",
                "assigned_to": "compliance_officer_123",
                "source_type": "transaction",
                "source_id": "TXN-2024-001",
                "metadata": {
                    "customer_id": "CUST-001",
                    "total_amount": 500000.00,
                    "transaction_count": 15,
                },
            }
        }


class CaseUpdate(BaseModel):
    """Schema for updating a case."""

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, description="open, in_progress, resolved, closed")
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "in_progress",
                "assigned_to": "senior_compliance_456",
                "resolution_notes": "Investigating transaction history",
            }
        }


class CaseResponse(BaseModel):
    """Response schema for case."""

    case_id: str
    title: str
    description: str
    case_type: str
    status: str
    priority: str
    assigned_to: Optional[str]
    source_type: Optional[str]
    source_id: Optional[str]
    metadata: Dict[str, Any]
    
    # Linked entities
    alert_count: int = Field(..., description="Number of linked alerts")
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Resolution
    resolution_notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "case_id": "CASE-001",
                "title": "Suspicious Transaction Pattern - Customer CUST-001",
                "description": "Multiple transactions detected showing structuring behavior",
                "case_type": "AML",
                "status": "in_progress",
                "priority": "high",
                "assigned_to": "compliance_officer_123",
                "source_type": "transaction",
                "source_id": "TXN-2024-001",
                "metadata": {
                    "customer_id": "CUST-001",
                },
                "alert_count": 3,
                "created_at": "2024-11-01T10:30:00Z",
                "updated_at": "2024-11-01T14:20:00Z",
                "resolved_at": None,
                "closed_at": None,
                "resolution_notes": None,
            }
        }


class CaseListResponse(BaseModel):
    """Response schema for list of cases."""

    total: int
    cases: List[CaseResponse]
    page: int = 1
    page_size: int = 100
    filters: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "total": 8,
                "cases": [],  # List of CaseResponse objects
                "page": 1,
                "page_size": 100,
                "filters": {
                    "status": "open",
                    "case_type": "AML",
                },
            }
        }
