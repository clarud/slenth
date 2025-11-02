"""
SQLAlchemy ORM models for SLENTH AML Monitoring System.
"""
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    JSON, ForeignKey, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
import enum

from db.database import Base


# Enums
class AlertRole(str, enum.Enum):
    """Alert recipient roles."""
    FRONT = "front"
    COMPLIANCE = "compliance"
    LEGAL = "legal"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    """Alert processing status."""
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class TransactionStatus(str, enum.Enum):
    """Transaction processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStatus(str, enum.Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    OCR_COMPLETE = "ocr_complete"
    VALIDATION_COMPLETE = "validation_complete"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskBand(str, enum.Enum):
    """Risk classification bands."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseStatus(str, enum.Enum):
    """Case management status."""
    OPEN = "open"
    IN_INVESTIGATION = "in_investigation"
    PENDING_APPROVAL = "pending_approval"
    CLOSED = "closed"
    ESCALATED = "escalated"


# Models

class Transaction(Base):
    """Transaction records for Part 1 AML monitoring."""
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Jurisdictional Info
    booking_jurisdiction = Column(String(10), nullable=False, index=True)
    regulator = Column(String(50), nullable=False)
    booking_datetime = Column(DateTime, nullable=False, index=True)
    value_date = Column(DateTime)
    
    # Financial Details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    channel = Column(String(50))
    product_type = Column(String(100))
    
    # Originator
    originator_name = Column(String(255))
    originator_account = Column(String(100))
    originator_country = Column(String(3), index=True)
    
    # Beneficiary
    beneficiary_name = Column(String(255))
    beneficiary_account = Column(String(100))
    beneficiary_country = Column(String(3), index=True)
    
    # Customer
    customer_id = Column(String(100), index=True)
    customer_segment = Column(String(50))
    customer_risk_rating = Column(String(20))
    customer_kyc_date = Column(DateTime)
    
    # SWIFT Details
    swift_mt = Column(String(10))
    ordering_institution_bic = Column(String(20))
    beneficiary_institution_bic = Column(String(20))
    swift_f50_present = Column(Boolean)
    swift_f59_present = Column(Boolean)
    swift_f70_purpose = Column(Text)
    swift_f71_charges = Column(String(10))
    
    # Risk Indicators
    pep_indicator = Column(Boolean)
    sanctions_hit = Column(Boolean)
    high_risk_country = Column(Boolean)
    structuring_flag = Column(Boolean)
    
    # Processing Status
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, index=True)
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    
    # Metadata
    raw_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    compliance_analysis = relationship("ComplianceAnalysis", back_populates="transaction", uselist=False)
    alerts = relationship("Alert", back_populates="transaction")
    
    __table_args__ = (
        Index('idx_transaction_booking_date', 'booking_datetime'),
        Index('idx_transaction_amount', 'amount'),
        Index('idx_transaction_customer', 'customer_id'),
    )


class ComplianceAnalysis(Base):
    """Compliance analysis results for transactions."""
    __tablename__ = "compliance_analysis"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey('transactions.id'), unique=True, nullable=False)
    
    # Risk Scoring
    compliance_score = Column(Float, nullable=False)  # 0-100
    risk_band = Column(SQLEnum(RiskBand), nullable=False, index=True)
    
    # Analysis Results
    applicable_rules = Column(JSONB)  # List of applicable rules
    evidence_map = Column(JSONB)  # Evidence mapping results
    control_test_results = Column(JSONB)  # Control test outcomes
    pattern_detections = Column(JSONB)  # Detected patterns
    bayesian_posterior = Column(Float)  # Bayesian probability
    
    # Summary
    compliance_summary = Column(Text)  # Markdown summary
    analyst_notes = Column(Text)
    
    # Metadata
    processing_time_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="compliance_analysis")


class Document(Base):
    """Document records for Part 2 document corroboration."""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # File Info
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer)
    file_type = Column(String(50))  # PDF, image, text
    mime_type = Column(String(100))
    
    # Document Type
    document_type = Column(String(100))  # e.g., purchase_agreement, ID, etc.
    
    # Processing Status
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.UPLOADED, index=True)
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    
    # Risk Assessment
    risk_score = Column(Float)  # 0-100
    risk_band = Column(SQLEnum(RiskBand), index=True)
    
    # Metadata
    uploaded_by = Column(String(100))
    customer_id = Column(String(100), index=True)
    transaction_id = Column(String(255), ForeignKey('transactions.transaction_id'), nullable=True, index=True)  # Link to Part 1 transaction
    workflow_metadata = Column(JSONB)  # Store workflow results and findings (renamed from metadata to avoid SQLAlchemy conflict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    findings = relationship("DocumentFinding", back_populates="document")
    alerts = relationship("Alert", back_populates="document")
    transaction = relationship("Transaction", backref="documents")


class DocumentFinding(Base):
    """Detailed findings from document analysis."""
    __tablename__ = "document_findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False)
    
    # Finding Type
    finding_type = Column(String(50), nullable=False)  # format, nlp, image_forensics, background_check
    
    # Finding Details
    finding_category = Column(String(100))
    finding_severity = Column(SQLEnum(AlertSeverity))
    finding_description = Column(Text)
    finding_data = Column(JSONB)  # Detailed finding data (legacy)
    finding_details = Column(JSONB)  # Complete finding object from workflow
    
    # Evidence
    evidence_location = Column(String(500))  # File path or coordinates
    confidence_score = Column(Float)
    
    # Metadata
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="findings")
    
    __table_args__ = (
        Index('idx_finding_type', 'finding_type'),
        Index('idx_finding_severity', 'finding_severity'),
    )


class Alert(Base):
    """Unified alerts for transactions and documents."""
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Alert Source
    source_type = Column(String(20), nullable=False)  # transaction or document
    transaction_id = Column(UUID(as_uuid=True), ForeignKey('transactions.id'), index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), index=True)
    
    # Alert Details
    role = Column(SQLEnum(AlertRole), nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, index=True)
    alert_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    remediation_workflow = Column(Text)  # Specific remediation workflow for this alert
    
    # Context
    context = Column(JSONB)  # Additional context data
    evidence = Column(JSONB)  # Supporting evidence
    
    # Status and Assignment
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.PENDING, index=True)
    assigned_to = Column(String(100))
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime)
    resolved_by = Column(String(100))
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    # SLA
    sla_deadline = Column(DateTime, nullable=False, index=True)
    sla_breached = Column(Boolean, default=False, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="alerts")
    document = relationship("Document", back_populates="alerts")
    case = relationship("Case", secondary="case_alerts", back_populates="alerts")
    
    __table_args__ = (
        Index('idx_alert_role_status', 'role', 'status'),
        Index('idx_alert_severity_status', 'severity', 'status'),
        Index('idx_alert_sla', 'sla_deadline', 'sla_breached'),
    )


class Case(Base):
    """Case management for high-severity alerts."""
    __tablename__ = "cases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Case Details
    case_title = Column(String(255), nullable=False)
    case_description = Column(Text)
    case_type = Column(String(100))  # AML, Sanctions, Fraud, etc.
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    status = Column(SQLEnum(CaseStatus), default=CaseStatus.OPEN, index=True)
    
    # Assignment
    assigned_to = Column(String(100))
    investigator = Column(String(100))
    supervisor = Column(String(100))
    
    # Dates
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime)
    due_date = Column(DateTime)
    
    # Customer/Entity
    customer_id = Column(String(100), index=True)
    entity_name = Column(String(255))
    
    # Resolution
    resolution_summary = Column(Text)
    action_taken = Column(String(100))  # SAR_filed, escalated, closed_no_action
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    alerts = relationship("Alert", secondary="case_alerts", back_populates="case")
    remediation_actions = relationship("RemediationAction", back_populates="case")
    
    __table_args__ = (
        Index('idx_case_status', 'status'),
        Index('idx_case_severity', 'severity'),
    )


class CaseAlert(Base):
    """Association table for cases and alerts."""
    __tablename__ = "case_alerts"
    
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), primary_key=True)
    alert_id = Column(UUID(as_uuid=True), ForeignKey('alerts.id'), primary_key=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RemediationAction(Base):
    """Remediation actions and playbooks."""
    __tablename__ = "remediation_actions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Association
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), index=True)
    alert_id = Column(UUID(as_uuid=True), ForeignKey('alerts.id'), index=True)
    
    # Action Details
    action_type = Column(String(100), nullable=False)  # edd, freeze_account, sar_filing, etc.
    action_title = Column(String(255), nullable=False)
    action_description = Column(Text)
    playbook_reference = Column(String(100))
    
    # Status
    status = Column(String(50), default="pending")  # pending, in_progress, completed, cancelled
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    
    # Assignment
    assigned_to = Column(String(100))
    completed_by = Column(String(100))
    
    # Dates
    scheduled_date = Column(DateTime)
    completed_at = Column(DateTime)
    due_date = Column(DateTime)
    
    # Results
    outcome = Column(Text)
    evidence_collected = Column(JSONB)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="remediation_actions")


class ExternalRule(Base):
    """External regulatory rules from HKMA, MAS, FINMA."""
    __tablename__ = "external_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Rule Info
    regulator = Column(String(50), nullable=False, index=True)  # HKMA, MAS, FINMA
    jurisdiction = Column(String(10), nullable=False, index=True)  # HK, SG, CH
    rule_title = Column(String(500))
    rule_text = Column(Text, nullable=False)
    
    # Source
    source_url = Column(String(1000))
    document_title = Column(String(500))
    section_path = Column(String(500))
    published_date = Column(DateTime, index=True)
    effective_date = Column(DateTime, index=True)
    
    # Vector DB
    vector_id = Column(String(100))  # ID in Qdrant
    
    # Metadata
    chunk_index = Column(Integer)  # If rule is chunked
    # 'metadata' attribute name is reserved by SQLAlchemy's Declarative API.
    # Use a different attribute name while keeping the DB column name as 'metadata'.
    meta = Column('metadata', JSONB)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_external_rule_regulator', 'regulator'),
        Index('idx_external_rule_dates', 'published_date', 'effective_date'),
    )


class InternalRule(Base):
    """Internal compliance rules and policies."""
    __tablename__ = "internal_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Rule Info
    rule_text = Column(Text, nullable=False)
    rule_category = Column(String(100))  # AML, KYC, Sanctions, etc.
    rule_priority = Column(String(20))  # high, medium, low
    
    # Versioning
    version = Column(String(50), nullable=False)
    effective_date = Column(DateTime, nullable=False, index=True)
    sunset_date = Column(DateTime)
    is_active = Column(Boolean, default=True, index=True)
    
    # Source
    source = Column(String(100))  # internal_policy_manual, board_directive, etc.
    policy_reference = Column(String(100))
    
    # Vector DB
    vector_id = Column(String(100))  # ID in Qdrant
    
    # Metadata
    # reserved attribute name fix
    meta = Column('metadata', JSONB)
    created_by = Column(String(100))
    approved_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_internal_rule_active', 'is_active', 'effective_date'),
        UniqueConstraint('rule_id', 'version', name='uq_rule_version'),
    )


class AuditLog(Base):
    """Audit trail for all system actions."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Action Info
    action_type = Column(String(100), nullable=False, index=True)
    action_description = Column(Text)
    actor = Column(String(100), nullable=False, index=True)  # User or system component
    
    # Target
    target_type = Column(String(50))  # transaction, document, alert, case, rule
    target_id = Column(String(100), index=True)
    
    # Context
    context_data = Column(JSONB)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_actor_type', 'actor', 'action_type'),
    )
