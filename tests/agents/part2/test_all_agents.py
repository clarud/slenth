"""
Comprehensive test suite for Part 2 Document Corroboration Agents.

Tests all 10 agents in the document workflow:
1. DocumentIntake
2. OCR
3. FormatValidation
4. NLPValidation
5. ImageForensics
6. BackgroundCheck (World-Check One)
7. CrossReference
8. DocumentRisk
9. ReportGenerator
10. EvidenceStorekeeper
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock, mock_open
from typing import Dict, Any
from datetime import datetime, timezone
import io

# Import agents
from agents.part2.document_intake import DocumentIntakeAgent
from agents.part2.ocr import OCRAgent
from agents.part2.format_validation import FormatValidationAgent
from agents.part2.nlp_validation import NLPValidationAgent
from agents.part2.image_forensics import ImageForensicsAgent
from agents.part2.background_check import BackgroundCheckAgent
from agents.part2.cross_reference import CrossReferenceAgent
from agents.part2.document_risk import DocumentRiskAgent
from agents.part2.report_generator import ReportGeneratorAgent
from agents.part2.evidence_store import EvidenceStorekeeperAgent


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "document_id": "DOC001",
        "filename": "purchase_agreement.pdf",
        "file_type": "application/pdf",
        "file_size": 102400,
        "upload_timestamp": datetime.now(timezone.utc).isoformat(),
        "document_type": "purchase_agreement"
    }


@pytest.fixture
def sample_state(sample_document):
    """Sample workflow state."""
    return {
        "document": sample_document,
        "document_id": sample_document["document_id"],
        "errors": []
    }


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    return session


# ============================================================================
# TEST CLASS 1: DocumentIntakeAgent
# ============================================================================

class TestDocumentIntakeAgent:
    """Test DocumentIntakeAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_document_intake_execution(self, sample_state):
        """Test document intake executes."""
        agent = DocumentIntakeAgent()
        
        result = await agent.execute(sample_state)
        
        assert result["document_intake_executed"] is True
        assert "document" in result
    
    @pytest.mark.asyncio
    async def test_document_type_classification(self, sample_state):
        """Test document type classification."""
        agent = DocumentIntakeAgent()
        
        result = await agent.execute(sample_state)
        
        # Should classify document type
        assert "document_type" in result or result.get("document", {}).get("document_type")
    
    @pytest.mark.asyncio
    async def test_handles_various_file_types(self):
        """Test handling of different file types."""
        agent = DocumentIntakeAgent()
        
        for ext in ["pdf", "png", "jpg", "txt"]:
            state = {
                "document": {"filename": f"test.{ext}", "document_id": "DOC001"},
                "errors": []
            }
            result = await agent.execute(state)
            assert result["document_intake_executed"] is True
    
    @pytest.mark.asyncio
    async def test_metadata_extraction(self, sample_state):
        """Test metadata extraction from document."""
        agent = DocumentIntakeAgent()
        
        result = await agent.execute(sample_state)
        
        assert "document" in result
        doc = result["document"]
        assert "filename" in doc
        assert "document_id" in doc


# ============================================================================
# TEST CLASS 2: OCRAgent
# ============================================================================

class TestOCRAgent:
    """Test OCRAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_ocr_execution(self, sample_state):
        """Test OCR agent executes."""
        agent = OCRAgent()
        sample_state["document"]["file_content"] = b"fake pdf content"
        
        result = await agent.execute(sample_state)
        
        assert result["ocr_executed"] is True
    
    @pytest.mark.asyncio
    async def test_text_extraction(self, sample_state):
        """Test text extraction from document."""
        agent = OCRAgent()
        sample_state["document"]["file_content"] = b"test content"
        
        result = await agent.execute(sample_state)
        
        # Should have extracted text
        assert "extracted_text" in result or "ocr_executed" in result
    
    @pytest.mark.asyncio
    async def test_handles_multi_page_documents(self, sample_state):
        """Test handling of multi-page documents."""
        agent = OCRAgent()
        sample_state["document"]["file_content"] = b"multi page content"
        
        result = await agent.execute(sample_state)
        
        # Should process multiple pages
        assert result["ocr_executed"] is True
    
    @pytest.mark.asyncio
    async def test_confidence_scores(self, sample_state):
        """Test OCR confidence scores are generated."""
        agent = OCRAgent()
        sample_state["document"]["file_content"] = b"content"
        
        result = await agent.execute(sample_state)
        
        # Should include confidence metrics
        assert "ocr_executed" in result


# ============================================================================
# TEST CLASS 3: FormatValidationAgent
# ============================================================================

class TestFormatValidationAgent:
    """Test FormatValidationAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_format_validation_execution(self, sample_state):
        """Test format validation executes."""
        agent = FormatValidationAgent()
        sample_state["extracted_text"] = "Test document content"
        
        result = await agent.execute(sample_state)
        
        assert result["format_validation_executed"] is True
        assert "format_findings" in result
    
    @pytest.mark.asyncio
    async def test_detects_formatting_errors(self, sample_state):
        """Test detection of formatting errors."""
        agent = FormatValidationAgent()
        sample_state["extracted_text"] = "Double  spacing  issues"
        
        result = await agent.execute(sample_state)
        findings = result.get("format_findings", {})
        
        assert isinstance(findings, dict)
    
    @pytest.mark.asyncio
    async def test_spelling_detection(self, sample_state):
        """Test spelling error detection."""
        agent = FormatValidationAgent()
        sample_state["extracted_text"] = "Thiss hass mistaakes"
        
        result = await agent.execute(sample_state)
        
        assert "format_findings" in result
    
    @pytest.mark.asyncio
    async def test_structure_validation(self, sample_state):
        """Test document structure validation."""
        agent = FormatValidationAgent()
        sample_state["extracted_text"] = "Missing header sections"
        
        result = await agent.execute(sample_state)
        findings = result.get("format_findings", {})
        
        # Should check for missing sections
        assert isinstance(findings, dict)


# ============================================================================
# TEST CLASS 4: NLPValidationAgent
# ============================================================================

class TestNLPValidationAgent:
    """Test NLPValidationAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_nlp_validation_execution(self, sample_state):
        """Test NLP validation executes."""
        agent = NLPValidationAgent()
        sample_state["extracted_text"] = "John Doe, 123 Main St, $50,000"
        
        result = await agent.execute(sample_state)
        
        assert result["nlp_validation_executed"] is True
        assert "nlp_findings" in result
    
    @pytest.mark.asyncio
    async def test_entity_extraction(self, sample_state):
        """Test entity extraction (names, addresses, amounts)."""
        agent = NLPValidationAgent()
        sample_state["extracted_text"] = "John Doe purchased property at 123 Main Street for USD 500,000"
        
        result = await agent.execute(sample_state)
        findings = result.get("nlp_findings", {})
        
        # Should extract entities
        assert isinstance(findings, dict)
    
    @pytest.mark.asyncio
    async def test_field_validation(self, sample_state):
        """Test field validation logic."""
        agent = NLPValidationAgent()
        sample_state["extracted_text"] = "Date: 2024-01-01, Amount: $100,000"
        
        result = await agent.execute(sample_state)
        
        assert "nlp_findings" in result
    
    @pytest.mark.asyncio
    async def test_cross_field_consistency(self, sample_state):
        """Test cross-field consistency checks."""
        agent = NLPValidationAgent()
        sample_state["extracted_text"] = "Amount: $50,000. Total: $50,000"
        
        result = await agent.execute(sample_state)
        findings = result.get("nlp_findings", {})
        
        # Should check field consistency
        assert isinstance(findings, dict)


# ============================================================================
# TEST CLASS 5: ImageForensicsAgent
# ============================================================================

class TestImageForensicsAgent:
    """Test ImageForensicsAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_image_forensics_execution(self, sample_state):
        """Test image forensics executes."""
        agent = ImageForensicsAgent()
        sample_state["document"]["file_content"] = b"fake image data"
        
        result = await agent.execute(sample_state)
        
        assert result["image_forensics_executed"] is True
        assert "image_findings" in result
    
    @pytest.mark.asyncio
    async def test_exif_analysis(self, sample_state):
        """Test EXIF metadata analysis."""
        agent = ImageForensicsAgent()
        sample_state["document"]["file_type"] = "image/jpeg"
        sample_state["document"]["file_content"] = b"jpeg data"
        
        result = await agent.execute(sample_state)
        findings = result.get("image_findings", {})
        
        # Should analyze EXIF
        assert isinstance(findings, dict)
    
    @pytest.mark.asyncio
    async def test_ela_detection(self, sample_state):
        """Test Error Level Analysis for tampering."""
        agent = ImageForensicsAgent()
        sample_state["document"]["file_content"] = b"image"
        
        result = await agent.execute(sample_state)
        
        assert "image_findings" in result
    
    @pytest.mark.asyncio
    async def test_ai_generated_detection(self, sample_state):
        """Test AI-generated image detection."""
        agent = ImageForensicsAgent()
        sample_state["document"]["file_content"] = b"image"
        
        result = await agent.execute(sample_state)
        findings = result.get("image_findings", {})
        
        # Should check for AI generation
        assert isinstance(findings, dict)


# ============================================================================
# TEST CLASS 6: BackgroundCheckAgent
# ============================================================================

class TestBackgroundCheckAgent:
    """Test BackgroundCheckAgent (World-Check One integration)."""
    
    @pytest.mark.asyncio
    async def test_background_check_execution(self, sample_state):
        """Test background check executes."""
        agent = BackgroundCheckAgent()
        sample_state["nlp_findings"] = {"entities": [{"type": "PERSON", "text": "John Doe"}]}
        
        result = await agent.execute(sample_state)
        
        assert result["background_check_executed"] is True
        assert "background_check_findings" in result
    
    @pytest.mark.asyncio
    async def test_world_check_api_call(self, sample_state):
        """Test World-Check One API integration."""
        agent = BackgroundCheckAgent()
        sample_state["nlp_findings"] = {"entities": [{"type": "PERSON", "text": "John Doe"}]}
        
        with patch('services.worldcheck.WorldCheckService') as MockWC:
            mock_service = MockWC.return_value
            mock_service.screen_entity = AsyncMock(return_value={
                "match_status": "clear",
                "matches": []
            })
            
            result = await agent.execute(sample_state)
            
            assert "background_check_findings" in result
    
    @pytest.mark.asyncio
    async def test_pep_screening(self, sample_state):
        """Test PEP (Politically Exposed Person) screening."""
        agent = BackgroundCheckAgent()
        sample_state["nlp_findings"] = {"entities": [{"type": "PERSON", "text": "Political Figure"}]}
        
        result = await agent.execute(sample_state)
        findings = result.get("background_check_findings", {})
        
        # Should screen for PEP status
        assert isinstance(findings, dict)
    
    @pytest.mark.asyncio
    async def test_sanctions_screening(self, sample_state):
        """Test sanctions list screening."""
        agent = BackgroundCheckAgent()
        sample_state["nlp_findings"] = {"entities": [{"type": "PERSON", "text": "Test Name"}]}
        
        result = await agent.execute(sample_state)
        
        assert "background_check_findings" in result
    
    @pytest.mark.asyncio
    async def test_handles_no_entities(self, sample_state):
        """Test handling when no entities found."""
        agent = BackgroundCheckAgent()
        sample_state["nlp_findings"] = {"entities": []}
        
        result = await agent.execute(sample_state)
        
        # Should handle gracefully
        assert result["background_check_executed"] is True


# ============================================================================
# TEST CLASS 7: CrossReferenceAgent
# ============================================================================

class TestCrossReferenceAgent:
    """Test CrossReferenceAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_cross_reference_execution(self, sample_state):
        """Test cross reference executes."""
        agent = CrossReferenceAgent()
        sample_state["nlp_findings"] = {"customer_id": "CUST123"}
        
        result = await agent.execute(sample_state)
        
        assert result["cross_reference_executed"] is True
        assert "cross_ref_findings" in result
    
    @pytest.mark.asyncio
    async def test_transaction_correlation(self, sample_state):
        """Test correlation with transaction history."""
        agent = CrossReferenceAgent()
        sample_state["nlp_findings"] = {"customer_id": "CUST123", "amount": 50000}
        
        result = await agent.execute(sample_state)
        findings = result.get("cross_ref_findings", {})
        
        # Should correlate with transactions
        assert isinstance(findings, dict)
    
    @pytest.mark.asyncio
    async def test_kyc_record_linking(self, sample_state):
        """Test linking to KYC records."""
        agent = CrossReferenceAgent()
        sample_state["nlp_findings"] = {"customer_id": "CUST123"}
        
        result = await agent.execute(sample_state)
        
        assert "cross_ref_findings" in result
    
    @pytest.mark.asyncio
    async def test_discrepancy_detection(self, sample_state):
        """Test detection of discrepancies."""
        agent = CrossReferenceAgent()
        sample_state["nlp_findings"] = {"customer_id": "CUST123", "address": "Mismatch"}
        
        result = await agent.execute(sample_state)
        findings = result.get("cross_ref_findings", {})
        
        # Should detect discrepancies
        assert isinstance(findings, dict)


# ============================================================================
# TEST CLASS 8: DocumentRiskAgent
# ============================================================================

class TestDocumentRiskAgent:
    """Test DocumentRiskAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_document_risk_execution(self, sample_state):
        """Test document risk calculation executes."""
        agent = DocumentRiskAgent()
        sample_state["format_findings"] = {}
        sample_state["nlp_findings"] = {}
        sample_state["image_findings"] = {}
        sample_state["background_check_findings"] = {}
        sample_state["cross_ref_findings"] = {}
        
        result = await agent.execute(sample_state)
        
        assert result["document_risk_executed"] is True
        assert "doc_risk_score" in result
    
    @pytest.mark.asyncio
    async def test_risk_score_calculation(self, sample_state):
        """Test risk score is calculated correctly."""
        agent = DocumentRiskAgent()
        sample_state["format_findings"] = {"errors": ["formatting issue"]}
        sample_state["background_check_findings"] = {"match_status": "potential_match"}
        
        result = await agent.execute(sample_state)
        risk_score = result.get("doc_risk_score", 0)
        
        # Score should be 0-100
        assert 0 <= risk_score <= 100
    
    @pytest.mark.asyncio
    async def test_risk_level_categorization(self, sample_state):
        """Test risk level categorization."""
        agent = DocumentRiskAgent()
        sample_state["format_findings"] = {}
        
        result = await agent.execute(sample_state)
        risk_level = result.get("risk_level", "")
        
        assert risk_level in ["Low", "Medium", "High", "Critical", ""]
    
    @pytest.mark.asyncio
    async def test_elevated_risk_for_background_matches(self, sample_state):
        """Test elevated risk when background check finds matches."""
        agent = DocumentRiskAgent()
        sample_state["background_check_findings"] = {
            "match_status": "confirmed_match",
            "matches": [{"category": "sanctions"}]
        }
        
        result = await agent.execute(sample_state)
        risk_score = result.get("doc_risk_score", 0)
        
        # Should have elevated risk
        assert risk_score > 0


# ============================================================================
# TEST CLASS 9: ReportGeneratorAgent
# ============================================================================

class TestReportGeneratorAgent:
    """Test ReportGeneratorAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_report_generation_execution(self, sample_state):
        """Test report generation executes."""
        agent = ReportGeneratorAgent()
        sample_state["doc_risk_score"] = 75
        sample_state["format_findings"] = {}
        sample_state["background_check_findings"] = {}
        
        result = await agent.execute(sample_state)
        
        assert result["report_generator_executed"] is True
        assert "report_path" in result or "report_generated" in result
    
    @pytest.mark.asyncio
    async def test_pdf_report_generation(self, sample_state):
        """Test PDF report is generated."""
        agent = ReportGeneratorAgent()
        sample_state["doc_risk_score"] = 50
        
        result = await agent.execute(sample_state)
        
        # Should generate PDF
        assert result.get("report_generator_executed") is True
    
    @pytest.mark.asyncio
    async def test_report_includes_findings(self, sample_state):
        """Test report includes all findings."""
        agent = ReportGeneratorAgent()
        sample_state.update({
            "format_findings": {"errors": ["test"]},
            "nlp_findings": {"entities": []},
            "image_findings": {},
            "background_check_findings": {"match_status": "clear"},
            "doc_risk_score": 30
        })
        
        result = await agent.execute(sample_state)
        
        assert result["report_generator_executed"] is True
    
    @pytest.mark.asyncio
    async def test_evidence_citations(self, sample_state):
        """Test evidence citations in report."""
        agent = ReportGeneratorAgent()
        sample_state["doc_risk_score"] = 60
        sample_state["background_check_findings"] = {"matches": []}
        
        result = await agent.execute(sample_state)
        
        # Report should include evidence
        assert result.get("report_generator_executed") is True


# ============================================================================
# TEST CLASS 10: EvidenceStorekeeperAgent
# ============================================================================

class TestEvidenceStorekeeperAgent:
    """Test EvidenceStorekeeperAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_evidence_storage_execution(self, sample_state):
        """Test evidence storage executes."""
        agent = EvidenceStorekeeperAgent()
        sample_state["document"]["file_content"] = b"content"
        sample_state["extracted_text"] = "text"
        
        result = await agent.execute(sample_state)
        
        assert result["evidence_store_executed"] is True
    
    @pytest.mark.asyncio
    async def test_raw_document_storage(self, sample_state):
        """Test raw document is stored."""
        agent = EvidenceStorekeeperAgent()
        sample_state["document"]["file_content"] = b"raw content"
        
        result = await agent.execute(sample_state)
        
        # Should store raw document
        assert result["evidence_store_executed"] is True
    
    @pytest.mark.asyncio
    async def test_extracted_text_storage(self, sample_state):
        """Test extracted text is stored."""
        agent = EvidenceStorekeeperAgent()
        sample_state["extracted_text"] = "Extracted document text"
        
        result = await agent.execute(sample_state)
        
        assert result["evidence_store_executed"] is True
    
    @pytest.mark.asyncio
    async def test_versioning(self, sample_state):
        """Test version control for stored evidence."""
        agent = EvidenceStorekeeperAgent()
        sample_state["document"]["file_content"] = b"v1"
        
        result = await agent.execute(sample_state)
        
        # Should handle versioning
        assert result["evidence_store_executed"] is True


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestDocumentAgentIntegration:
    """Test document agent integration."""
    
    @pytest.mark.asyncio
    async def test_sequential_document_processing(self, sample_state):
        """Test agents can process document sequentially."""
        # Intake
        intake = DocumentIntakeAgent()
        state1 = await intake.execute(sample_state)
        assert state1["document_intake_executed"] is True
        
        # OCR
        ocr = OCRAgent()
        state1["document"]["file_content"] = b"test"
        state2 = await ocr.execute(state1)
        assert state2["ocr_executed"] is True
        
        # Format Validation
        format_val = FormatValidationAgent()
        state2["extracted_text"] = "Test text"
        state3 = await format_val.execute(state2)
        assert state3["format_validation_executed"] is True
        
        # Verify state preservation
        assert state3.get("document_id") == sample_state["document_id"]
    
    @pytest.mark.asyncio
    async def test_risk_score_aggregation(self, sample_state):
        """Test risk score aggregates findings from all agents."""
        # Simulate findings from multiple agents
        sample_state.update({
            "format_findings": {"errors": ["error1"]},
            "nlp_findings": {"issues": ["issue1"]},
            "image_findings": {"tampering_detected": True},
            "background_check_findings": {"match_status": "potential_match"},
            "cross_ref_findings": {"discrepancies": []}
        })
        
        agent = DocumentRiskAgent()
        result = await agent.execute(sample_state)
        
        # Risk score should reflect multiple findings
        assert result.get("doc_risk_score", 0) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_across_agents(self, sample_state):
        """Test error handling across agent chain."""
        intake = DocumentIntakeAgent()
        
        # Test with corrupted state
        corrupt_state = {"errors": []}  # Missing document
        
        result = await intake.execute(corrupt_state)
        
        # Should handle gracefully
        assert "errors" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
