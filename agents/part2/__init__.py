"""
Part 2 Agents - Document Corroboration

Contains 10 agents for document validation and risk assessment:
1. DocumentIntake - Accept uploads and normalize
2. OCR - Perform OCR on scanned documents
3. FormatValidation - Detect formatting errors
4. NLPValidation - Extract fields and validate
5. ImageForensics - Image analysis and tampering detection
6. BackgroundCheck - World-Check One screening
7. CrossReference - Correlate with transaction history
8. DocumentRisk - Calculate document risk score
9. ReportGenerator - Generate PDF report
10. EvidenceStorekeeper - Manage evidence storage
"""

from .document_intake import DocumentIntakeAgent
from .ocr import OCRAgent
from .format_validation import FormatValidationAgent
from .nlp_validation import NLPValidationAgent
from .image_forensics import ImageForensicsAgent
from .background_check import BackgroundCheckAgent
from .cross_reference import CrossReferenceAgent
from .document_risk import DocumentRiskAgent
from .report_generator import ReportGeneratorAgent
from .evidence_storekeeper import EvidenceStorekeeperAgent

__all__ = [
    "DocumentIntakeAgent",
    "OCRAgent",
    "FormatValidationAgent",
    "NLPValidationAgent",
    "ImageForensicsAgent",
    "BackgroundCheckAgent",
    "CrossReferenceAgent",
    "DocumentRiskAgent",
    "ReportGeneratorAgent",
    "EvidenceStorekeeperAgent",
]
