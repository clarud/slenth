"""
Document-related Pydantic schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document (synchronous processing)."""

    document_id: str
    filename: str
    file_size: int
    file_type: str
    status: str = Field(default="processing", description="Processing status")
    transaction_id: Optional[str] = Field(None, description="Linked transaction ID from Part 1")
    uploaded_at: datetime
    
    # Processing results (available immediately since Part 2 is synchronous)
    risk_score: Optional[float] = Field(None, description="Document risk score (0-100)")
    risk_level: Optional[str] = Field(None, description="Low, Medium, High, Critical")
    processing_completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    
    # Findings summary
    total_findings: Optional[int] = Field(None, description="Total number of findings")
    findings_summary: Optional[Dict[str, int]] = Field(None, description="Findings breakdown by type")
    report_path: Optional[str] = Field(None, description="Path to generated PDF report")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "DOC-2024-001",
                "filename": "purchase_agreement.pdf",
                "file_size": 2048576,
                "file_type": "pdf",
                "status": "completed",
                "transaction_id": "TXN-20241101-001",
                "uploaded_at": "2024-11-01T10:30:00Z",
                "risk_score": 45.0,
                "risk_level": "Medium",
                "processing_completed_at": "2024-11-01T10:30:15Z",
                "processing_time_seconds": 15.2,
                "total_findings": 8,
                "findings_summary": {
                    "format": 2,
                    "content": 3,
                    "image_forensics": 1,
                    "background_check": 1,
                    "cross_reference": 1
                },
                "report_path": "/uploads/reports/DOC-2024-001_report.pdf"
            }
        }


class DocumentRiskResponse(BaseModel):
    """Document risk assessment results."""

    document_id: str
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., description="Low, Medium, High, Critical")
    
    # Breakdown by category
    format_risk: float
    content_risk: float
    image_risk: float
    background_check_risk: float
    
    # Summary
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    
    # Evidence
    key_issues: List[str]
    recommendations: List[str]
    
    # Metadata
    assessed_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "DOC-2024-001",
                "risk_score": 45.0,
                "risk_level": "Medium",
                "format_risk": 20.0,
                "content_risk": 35.0,
                "image_risk": 15.0,
                "background_check_risk": 30.0,
                "total_findings": 8,
                "critical_findings": 0,
                "high_findings": 2,
                "medium_findings": 4,
                "low_findings": 2,
                "key_issues": [
                    "Formatting inconsistencies detected",
                    "Potential match found in background check",
                ],
                "recommendations": [
                    "Manual review of background check results",
                    "Verify document authenticity",
                ],
                "assessed_at": "2024-11-01T10:30:15Z",
            }
        }


class FindingDetail(BaseModel):
    """Individual finding detail."""

    finding_type: str
    severity: str
    description: str
    evidence: Optional[Dict[str, Any]] = None
    page_number: Optional[int] = None
    confidence: Optional[float] = None


class DocumentFindingsResponse(BaseModel):
    """Detailed findings from document processing."""

    document_id: str
    filename: Optional[str] = None
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    processing_completed_at: Optional[str] = None
    workflow_metadata: Optional[Dict[str, Any]] = None
    
    # OCR results
    ocr_text: str
    ocr_confidence: float
    pages_processed: int
    
    # Format validation findings
    format_findings: List[FindingDetail]
    
    # Content validation findings
    content_findings: List[FindingDetail]
    
    # Image forensics findings
    image_findings: List[FindingDetail]
    
    # Background check findings
    background_check_findings: List[FindingDetail]
    
    # Cross-reference findings
    cross_reference_findings: List[FindingDetail]
    
    # Extracted entities
    extracted_entities: Dict[str, List[str]]
    
    # Report URL
    report_url: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "DOC-2024-001",
                "ocr_text": "Swiss Home Purchase Agreement...",
                "ocr_confidence": 0.95,
                "pages_processed": 5,
                "format_findings": [
                    {
                        "finding_type": "spacing_error",
                        "severity": "low",
                        "description": "Double spacing detected on page 2",
                        "page_number": 2,
                        "confidence": 0.85,
                    }
                ],
                "content_findings": [
                    {
                        "finding_type": "missing_section",
                        "severity": "high",
                        "description": "Required annex section missing",
                        "evidence": {"expected_section": "Annex A"},
                    }
                ],
                "image_findings": [],
                "background_check_findings": [
                    {
                        "finding_type": "potential_match",
                        "severity": "medium",
                        "description": "Potential PEP match for entity name",
                        "evidence": {
                            "match_name": "John Doe",
                            "match_strength": 75,
                            "category": "PEP",
                        },
                    }
                ],
                "cross_reference_findings": [],
                "extracted_entities": {
                    "persons": ["John Doe", "Jane Smith"],
                    "organizations": ["ABC Corp"],
                    "locations": ["Zurich, Switzerland"],
                    "dates": ["2024-11-01"],
                    "amounts": ["500000 CHF"],
                },
                "report_url": "/documents/DOC-2024-001/report",
            }
        }


class DocumentAcknowledgeRequest(BaseModel):
    """Request to acknowledge document review."""

    reviewed_by: str = Field(..., description="User ID of reviewer")
    review_notes: Optional[str] = Field(None, description="Optional review notes")
    approved: bool = Field(..., description="Whether document is approved")

    class Config:
        json_schema_extra = {
            "example": {
                "reviewed_by": "compliance_officer_123",
                "review_notes": "Document verified, no issues found",
                "approved": True,
            }
        }
