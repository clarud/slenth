"""
Internal rule-related Pydantic schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InternalRuleCreate(BaseModel):
    """Schema for creating a new internal rule."""

    title: str = Field(..., description="Rule title")
    description: str = Field(..., description="Detailed rule description")
    text: str = Field(..., description="Full rule text content")
    section: Optional[str] = Field(None, description="Rule section/category")
    obligation_type: Optional[str] = Field(None, description="Type of obligation")
    conditions: Optional[List[str]] = Field(None, description="Applicability conditions")
    expected_evidence: Optional[List[str]] = Field(None, description="Required evidence")
    penalty_level: Optional[str] = Field(None, description="Penalty severity")
    effective_date: str = Field(..., description="Effective date (YYYY-MM-DD)")
    sunset_date: Optional[str] = Field(None, description="Expiration date (YYYY-MM-DD)")
    version: str = Field(default="v1.0", description="Rule version")
    source: str = Field(default="internal_policy_manual", description="Rule source")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "EDD Required for High-Risk Jurisdictions",
                "description": "Enhanced Due Diligence must be performed for transactions involving high-risk jurisdictions",
                "text": "For all transactions with counterparties in high-risk jurisdictions as defined by FATF, Enhanced Due Diligence procedures must be completed within 48 hours...",
                "section": "KYC/EDD",
                "obligation_type": "mandatory",
                "conditions": ["high_risk_jurisdiction", "transaction_amount > 10000"],
                "expected_evidence": ["edd_report", "source_of_funds_verification"],
                "penalty_level": "high",
                "effective_date": "2024-01-01",
                "version": "v1.0",
                "source": "internal_policy_manual",
            }
        }


class InternalRuleUpdate(BaseModel):
    """Schema for updating an internal rule (creates new version)."""

    title: Optional[str] = None
    description: Optional[str] = None
    text: Optional[str] = None
    section: Optional[str] = None
    obligation_type: Optional[str] = None
    conditions: Optional[List[str]] = None
    expected_evidence: Optional[List[str] ] = None
    penalty_level: Optional[str] = None
    effective_date: Optional[str] = None
    sunset_date: Optional[str] = None
    version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Updated rule text with revised thresholds...",
                "version": "v1.1",
                "effective_date": "2024-06-01",
            }
        }


class InternalRuleResponse(BaseModel):
    """Response schema for internal rule."""

    rule_id: str
    title: str
    description: str
    text: str
    section: Optional[str]
    obligation_type: Optional[str]
    conditions: Optional[List[str]]
    expected_evidence: Optional[List[str]]
    penalty_level: Optional[str]
    effective_date: str
    sunset_date: Optional[str]
    version: str
    source: str
    is_active: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "rule_id": "RULE-001",
                "title": "EDD Required for High-Risk Jurisdictions",
                "description": "Enhanced Due Diligence must be performed...",
                "text": "For all transactions with counterparties...",
                "section": "KYC/EDD",
                "obligation_type": "mandatory",
                "conditions": ["high_risk_jurisdiction"],
                "expected_evidence": ["edd_report"],
                "penalty_level": "high",
                "effective_date": "2024-01-01",
                "sunset_date": None,
                "version": "v1.0",
                "source": "internal_policy_manual",
                "is_active": True,
                "metadata": {},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


class InternalRuleListResponse(BaseModel):
    """Response schema for list of internal rules."""

    total: int
    rules: List[InternalRuleResponse]
    page: int = 1
    page_size: int = 100

    class Config:
        json_schema_extra = {
            "example": {
                "total": 42,
                "rules": [],  # List of InternalRuleResponse objects
                "page": 1,
                "page_size": 100,
            }
        }
