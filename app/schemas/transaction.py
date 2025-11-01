"""
Transaction-related Pydantic schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class TransactionCreate(BaseModel):
    """Schema for creating/submitting a transaction for processing."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    booking_jurisdiction: str = Field(..., description="Booking jurisdiction")
    regulator: str = Field(..., description="Regulatory authority")
    booking_datetime: datetime = Field(..., description="Booking timestamp")
    value_date: datetime = Field(..., description="Value date (date-only accepted)")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code")
    channel: str = Field(..., description="Transaction channel")
    product_type: str = Field(..., description="Product type")
    
    # Originator information
    originator_name: str
    originator_account: str
    originator_country: str
    
    # Beneficiary information
    beneficiary_name: str
    beneficiary_account: str
    beneficiary_country: str
    
    # SWIFT fields
    # Some transactions may not be SWIFT MT messages; allow missing
    swift_mt: Optional[str] = None
    ordering_institution_bic: Optional[str] = None
    beneficiary_institution_bic: Optional[str] = None
    swift_f50_present: bool = False
    swift_f59_present: bool = False
    swift_f70_purpose: Optional[str] = None
    swift_f71_charges: Optional[str] = None
    travel_rule_complete: bool = False
    
    # FX fields
    fx_indicator: bool = False
    fx_base_ccy: Optional[str] = None
    fx_quote_ccy: Optional[str] = None
    fx_applied_rate: Optional[float] = None
    fx_market_rate: Optional[float] = None
    fx_spread_bps: Optional[float] = None
    fx_counterparty: Optional[str] = None
    
    # Customer fields
    customer_id: str
    customer_type: str
    customer_risk_rating: str
    customer_is_pep: bool = False
    kyc_last_completed: Optional[str] = None
    kyc_due_date: Optional[str] = None
    edd_required: bool = False
    edd_performed: bool = False
    sow_documented: bool = False
    
    # Transaction details
    purpose_code: Optional[str] = None
    narrative: Optional[str] = None
    is_advised: bool = False
    product_complex: bool = False
    
    # Client risk assessment
    client_risk_profile: Optional[str] = None
    suitability_assessed: bool = False
    suitability_result: Optional[str] = None
    product_has_va_exposure: bool = False
    va_disclosure_provided: bool = False
    
    # Cash handling
    cash_id_verified: bool = False
    daily_cash_total_customer: Optional[float] = None
    daily_cash_txn_count: Optional[int] = None
    
    # Screening
    sanctions_screening: Optional[str] = None
    suspicion_determined_datetime: Optional[str] = None
    str_filed_datetime: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN-2024-001",
                "booking_jurisdiction": "HK",
                "regulator": "HKMA",
                "booking_datetime": "2024-11-01T10:30:00Z",
                "value_date": "2024-11-01",
                "amount": 100000.00,
                "currency": "USD",
                "channel": "SWIFT",
                "product_type": "Wire Transfer",
                "originator_name": "John Doe",
                "originator_account": "1234567890",
                "originator_country": "US",
                "beneficiary_name": "Jane Smith",
                "beneficiary_account": "0987654321",
                "beneficiary_country": "CH",
                "swift_mt": "MT103",
                "customer_id": "CUST-001",
                "customer_type": "Individual",
                "customer_risk_rating": "Medium",
            }
        }

    # Custom parsing for non-ISO date formats from CSV (e.g., "24/4/2024")
    @validator("value_date", pre=True)
    def _parse_value_date(cls, v):
        if v is None or v == "":
            return v
        if isinstance(v, datetime):
            return v
        s = str(v).strip()
        # Handle ISO-like with optional trailing Z
        try:
            ss = s[:-1] if s.endswith("Z") else s
            return datetime.fromisoformat(ss)
        except Exception:
            pass
        # Handle D/M/YYYY (or DD/MM/YYYY) with slashes
        if "/" in s:
            try:
                parts = s.split("/")
                if len(parts) == 3:
                    d, m, y = parts
                    return datetime(int(y), int(m), int(d), 0, 0, 0)
            except Exception:
                pass
        return s  # Let downstream validation surface a clear error

    @validator("booking_datetime", pre=True)
    def _parse_booking_datetime(cls, v):
        if v is None or v == "":
            return v
        if isinstance(v, datetime):
            return v
        s = str(v).strip()
        # Allow ISO8601 with optional trailing Z
        try:
            ss = s[:-1] if s.endswith("Z") else s
            return datetime.fromisoformat(ss)
        except Exception:
            pass
        # Fallback: if comes as D/M/YYYY, normalize to midnight
        if "/" in s:
            try:
                parts = s.split("/")
                if len(parts) == 3:
                    d, m, y = parts
                    return datetime(int(y), int(m), int(d), 0, 0, 0)
            except Exception:
                pass
        return s


class TransactionResponse(BaseModel):
    """Response after submitting transaction."""

    transaction_id: str
    task_id: str = Field(..., description="Celery task ID for tracking")
    status: str = Field(default="queued", description="Initial status")
    message: str = Field(default="Transaction queued for processing")
    submitted_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN-2024-001",
                "task_id": "abc-123-def-456",
                "status": "queued",
                "message": "Transaction queued for processing",
                "submitted_at": "2024-11-01T10:30:00Z",
            }
        }


class TransactionStatusResponse(BaseModel):
    """Response for transaction status check."""

    transaction_id: str
    task_id: str
    status: str = Field(..., description="Processing status: queued, processing, completed, failed")
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    current_step: Optional[str] = Field(None, description="Current processing step")
    error: Optional[str] = Field(None, description="Error message if failed")
    completed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN-2024-001",
                "task_id": "abc-123-def-456",
                "status": "processing",
                "progress": 65,
                "current_step": "BayesianEngine",
                "completed_at": None,
            }
        }


class ComplianceAnalysisResponse(BaseModel):
    """Complete compliance analysis results."""

    transaction_id: str
    risk_band: str = Field(..., description="Risk classification: Low, Medium, High, Critical")
    risk_score: float = Field(..., ge=0, le=100, description="Overall risk score")
    
    # Rule-based analysis
    rules_evaluated: int
    rules_violated: int
    applicable_rules: List[Dict[str, Any]]
    
    # Pattern detection
    patterns_detected: List[Dict[str, Any]]
    
    # Bayesian analysis
    bayesian_posterior: Dict[str, float]
    
    # Analyst summary
    compliance_summary: str
    recommendations: List[str]
    
    # Alerts generated
    alerts_generated: List[Dict[str, Any]]
    
    # Remediation
    remediation_actions: List[Dict[str, Any]]
    
    # Metadata
    processed_at: datetime
    processing_time_seconds: float

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN-2024-001",
                "risk_band": "Medium",
                "risk_score": 62.5,
                "rules_evaluated": 15,
                "rules_violated": 2,
                "applicable_rules": [
                    {
                        "rule_id": "RULE-001",
                        "title": "EDD Required for High-Risk Jurisdictions",
                        "applies": True,
                        "violated": True,
                        "severity": "high",
                    }
                ],
                "patterns_detected": [
                    {
                        "pattern_type": "structuring",
                        "confidence": 0.75,
                        "description": "Multiple transactions below reporting threshold",
                    }
                ],
                "bayesian_posterior": {
                    "low_risk": 0.2,
                    "medium_risk": 0.6,
                    "high_risk": 0.15,
                    "critical_risk": 0.05,
                },
                "compliance_summary": "Transaction flagged for missing EDD documentation...",
                "recommendations": [
                    "Complete Enhanced Due Diligence",
                    "Verify source of funds",
                ],
                "alerts_generated": [
                    {
                        "alert_id": "ALT-001",
                        "severity": "high",
                        "role": "compliance",
                        "title": "Missing EDD Documentation",
                    }
                ],
                "remediation_actions": [
                    {
                        "action": "Request EDD documentation",
                        "owner": "Compliance Team",
                        "sla_hours": 48,
                    }
                ],
                "processed_at": "2024-11-01T10:35:00Z",
                "processing_time_seconds": 4.5,
            }
        }
