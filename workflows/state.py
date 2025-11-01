"""
Workflow State Definitions for LangGraph

Defines state structures for Part 1 (transaction) and Part 2 (document) workflows.
"""

from typing import Any, Dict, List, Optional, TypedDict


class TransactionWorkflowState(TypedDict, total=False):
    """
    State for Part 1 transaction monitoring workflow.

    This state is passed between agents in the LangGraph workflow.
    """

    # Input
    transaction: Dict[str, Any]  # Original transaction data
    transaction_id: str

    # ContextBuilder outputs
    query_strings: List[str]
    transaction_history: List[Dict[str, Any]]
    context_summary: str

    # Retrieval outputs
    applicable_rules: List[Dict[str, Any]]

    # Applicability outputs
    applicable_rules_filtered: List[Dict[str, Any]]

    # EvidenceMapper outputs
    evidence_mapping: Dict[str, Dict[str, Any]]

    # ControlTest outputs
    control_results: List[Dict[str, Any]]

    # FeatureService outputs
    features: Dict[str, Any]

    # BayesianEngine outputs
    bayesian_posterior: Dict[str, float]

    # PatternDetector outputs
    patterns_detected: List[Dict[str, Any]]

    # DecisionFusion outputs
    risk_score: float
    risk_band: str

    # AnalystWriter outputs
    compliance_summary: str
    recommendations: List[str]

    # AlertComposer outputs
    alerts_generated: List[Dict[str, Any]]

    # RemediationOrchestrator outputs
    remediation_actions: List[Dict[str, Any]]

    # Persistor outputs
    persisted: bool
    records_created: List[str]

    # Metadata
    processing_start_time: float
    processing_end_time: Optional[float]
    errors: List[str]


class DocumentWorkflowState(TypedDict, total=False):
    """
    State for Part 2 document corroboration workflow.

    This state is passed between agents in the LangGraph workflow.
    """

    # Input
    document: Dict[str, Any]  # Document metadata
    document_id: str
    file_path: str
    file_type: str

    # DocumentIntake outputs
    normalized_document: Dict[str, Any]

    # OCR outputs
    ocr_text: str
    ocr_confidence: float
    ocr_regions: List[Dict[str, Any]]
    pages_processed: int

    # FormatValidation outputs
    format_findings: List[Dict[str, Any]]

    # NLPValidation outputs
    content_findings: List[Dict[str, Any]]
    extracted_entities: Dict[str, List[str]]

    # ImageForensics outputs
    image_findings: List[Dict[str, Any]]

    # BackgroundCheck outputs
    background_check_findings: List[Dict[str, Any]]
    screening_results: Dict[str, Any]

    # CrossReference outputs
    cross_reference_findings: List[Dict[str, Any]]

    # DocumentRisk outputs
    risk_score: float
    risk_level: str
    format_risk: float
    content_risk: float
    image_risk: float
    background_check_risk: float

    # ReportGenerator outputs
    report_path: str
    report_url: str

    # EvidenceStorekeeper outputs
    evidence_stored: bool
    evidence_paths: Dict[str, str]

    # Metadata
    processing_start_time: float
    processing_end_time: Optional[float]
    errors: List[str]
