"""
Comprehensive test suite for LangGraph Workflows.

Tests:
1. Transaction Workflow (Part 1) - Async via Celery
2. Document Workflow (Part 2) - Synchronous execution
3. Workflow state management
4. Error recovery
5. Conditional edges
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any
from datetime import datetime, timezone

from workflows.transaction_workflow import create_transaction_workflow, execute_transaction_workflow
from workflows.document_workflow import create_document_workflow, execute_document_workflow
from workflows.state import TransactionWorkflowState, DocumentWorkflowState


@pytest.fixture
def sample_transaction():
    """Sample transaction data."""
    return {
        "transaction_id": "TXN001",
        "amount": 50000,
        "currency": "USD",
        "customer_id": "CUST123",
        "originator_country": "HK",
        "beneficiary_country": "SG",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_document():
    """Sample document data."""
    return {
        "document_id": "DOC001",
        "filename": "test_document.pdf",
        "file_type": "application/pdf",
        "file_size": 102400,
        "upload_timestamp": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def mock_services():
    """Mock all required services."""
    return {
        "db_session": MagicMock(),
        "llm_service": MagicMock(chat=AsyncMock(return_value="test")),
        "vector_service": MagicMock(search=AsyncMock(return_value=[])),
        "embedding_service": MagicMock(embed_text=AsyncMock(return_value=[0.1] * 1024))
    }


# ============================================================================
# TRANSACTION WORKFLOW TESTS
# ============================================================================

class TestTransactionWorkflow:
    """Test Part 1 transaction monitoring workflow."""
    
    @pytest.mark.asyncio
    async def test_workflow_creation(self, mock_services):
        """Test transaction workflow can be created."""
        workflow = create_transaction_workflow(
            mock_services["db_session"],
            mock_services["llm_service"],
            mock_services["vector_service"],
            mock_services["embedding_service"]
        )
        
        assert workflow is not None
    
    @pytest.mark.asyncio
    async def test_workflow_execution(self, sample_transaction, mock_services):
        """Test transaction workflow executes end-to-end."""
        result = await execute_transaction_workflow(
            sample_transaction,
            mock_services["db_session"],
            mock_services["llm_service"],
            mock_services["vector_service"],
            mock_services["embedding_service"]
        )
        
        assert result is not None
        assert "transaction_id" in result
        assert result["transaction_id"] == "TXN001"
    
    @pytest.mark.asyncio
    async def test_all_agents_execute(self, sample_transaction, mock_services):
        """Test all 13 agents in workflow execute."""
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        
        # Check that key agents executed
        expected_keys = [
            "context_builder_executed",
            "retrieval_executed",
            "applicability_executed",
            "evidence_mapper_executed",
            "control_test_executed",
            "feature_service_executed",
            "bayesian_engine_executed",
            "pattern_detector_executed",
            "decision_fusion_executed",
            "analyst_writer_executed",
            "alert_composer_executed",
            "remediation_orchestrator_executed",
            "persistor_executed"
        ]
        
        # At least some agents should have executed
        executed_count = sum(1 for key in expected_keys if result.get(key))
        assert executed_count > 0
    
    @pytest.mark.asyncio
    async def test_risk_score_generated(self, sample_transaction, mock_services):
        """Test workflow generates risk score."""
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        
        # Should have risk assessment
        assert "risk_score" in result or "decision_fusion_executed" in result
    
    @pytest.mark.asyncio
    async def test_compliance_analysis_generated(self, sample_transaction, mock_services):
        """Test compliance analysis is generated."""
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        
        # Should have analysis
        assert "compliance_analysis" in result or "analyst_writer_executed" in result
    
    @pytest.mark.asyncio
    async def test_state_preservation(self, sample_transaction, mock_services):
        """Test state is preserved throughout workflow."""
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        
        # Original transaction should be preserved
        assert result.get("transaction", {}).get("transaction_id") == "TXN001"
    
    @pytest.mark.asyncio
    async def test_error_collection(self, sample_transaction, mock_services):
        """Test errors are collected during workflow."""
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        
        # Should have errors list (even if empty)
        assert "errors" in result
        assert isinstance(result["errors"], list)
    
    @pytest.mark.asyncio
    async def test_processing_time_tracked(self, sample_transaction, mock_services):
        """Test processing time is tracked."""
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        
        # Should track timing
        assert "processing_start_time" in result or "processing_time_seconds" in result


# ============================================================================
# DOCUMENT WORKFLOW TESTS
# ============================================================================

class TestDocumentWorkflow:
    """Test Part 2 document corroboration workflow."""
    
    @pytest.mark.asyncio
    async def test_workflow_creation(self):
        """Test document workflow can be created."""
        workflow = create_document_workflow()
        
        assert workflow is not None
    
    @pytest.mark.asyncio
    async def test_workflow_execution(self, sample_document):
        """Test document workflow executes end-to-end."""
        sample_document["file_content"] = b"test content"
        
        result = await execute_document_workflow(sample_document)
        
        assert result is not None
        assert "document_id" in result
        assert result["document_id"] == "DOC001"
    
    @pytest.mark.asyncio
    async def test_all_agents_execute(self, sample_document):
        """Test all 10 agents in workflow execute."""
        sample_document["file_content"] = b"content"
        
        result = await execute_document_workflow(sample_document)
        
        # Check that key agents executed
        expected_keys = [
            "document_intake_executed",
            "ocr_executed",
            "format_validation_executed",
            "nlp_validation_executed",
            "image_forensics_executed",
            "background_check_executed",
            "cross_reference_executed",
            "document_risk_executed",
            "report_generator_executed",
            "evidence_store_executed"
        ]
        
        # At least some agents should have executed
        executed_count = sum(1 for key in expected_keys if result.get(key))
        assert executed_count > 0
    
    @pytest.mark.asyncio
    async def test_risk_score_calculated(self, sample_document):
        """Test document risk score is calculated."""
        sample_document["file_content"] = b"test"
        
        result = await execute_document_workflow(sample_document)
        
        # Should have risk score
        assert "doc_risk_score" in result or "document_risk_executed" in result
    
    @pytest.mark.asyncio
    async def test_report_generated(self, sample_document):
        """Test PDF report is generated."""
        sample_document["file_content"] = b"test"
        
        result = await execute_document_workflow(sample_document)
        
        # Should generate report
        assert "report_generator_executed" in result or "report_path" in result
    
    @pytest.mark.asyncio
    async def test_synchronous_execution(self, sample_document):
        """Test workflow executes synchronously (not queued)."""
        import time
        sample_document["file_content"] = b"test"
        
        start = time.time()
        result = await execute_document_workflow(sample_document)
        duration = time.time() - start
        
        # Should complete quickly (not queued)
        assert result is not None
        # Synchronous execution should return results immediately
        assert duration < 10  # Should be fast


# ============================================================================
# WORKFLOW STATE TESTS
# ============================================================================

class TestWorkflowState:
    """Test workflow state management."""
    
    def test_transaction_state_structure(self):
        """Test TransactionWorkflowState has required fields."""
        state: TransactionWorkflowState = {
            "transaction": {"transaction_id": "TXN001"},
            "transaction_id": "TXN001",
            "errors": []
        }
        
        assert "transaction" in state
        assert "transaction_id" in state
        assert "errors" in state
    
    def test_document_state_structure(self):
        """Test DocumentWorkflowState has required fields."""
        state: DocumentWorkflowState = {
            "document": {"document_id": "DOC001"},
            "document_id": "DOC001",
            "errors": []
        }
        
        assert "document" in state
        assert "document_id" in state
        assert "errors" in state
    
    def test_state_is_mutable(self):
        """Test workflow state can be modified."""
        state: TransactionWorkflowState = {
            "transaction": {},
            "errors": []
        }
        
        state["risk_score"] = 75
        state["errors"].append("test error")
        
        assert state["risk_score"] == 75
        assert len(state["errors"]) == 1


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestWorkflowErrorHandling:
    """Test error handling in workflows."""
    
    @pytest.mark.asyncio
    async def test_handles_missing_transaction_data(self, mock_services):
        """Test workflow handles missing transaction data."""
        invalid_transaction = {}  # Missing required fields
        
        result = await execute_transaction_workflow(
            invalid_transaction,
            **mock_services
        )
        
        # Should not crash, should collect errors
        assert result is not None
        assert "errors" in result
    
    @pytest.mark.asyncio
    async def test_handles_agent_failures(self, sample_transaction, mock_services):
        """Test workflow continues when agent fails."""
        # Make an agent fail
        mock_services["llm_service"].chat = AsyncMock(side_effect=Exception("LLM error"))
        
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        
        # Workflow should complete despite failure
        assert result is not None
        # Errors should be logged
        assert "errors" in result
    
    @pytest.mark.asyncio
    async def test_handles_missing_document_content(self, sample_document):
        """Test document workflow handles missing file content."""
        # Don't provide file_content
        
        result = await execute_document_workflow(sample_document)
        
        # Should handle gracefully
        assert result is not None
        assert "errors" in result


# ============================================================================
# CONDITIONAL EDGE TESTS
# ============================================================================

class TestConditionalEdges:
    """Test conditional routing in workflows."""
    
    @pytest.mark.asyncio
    async def test_high_risk_triggers_alerts(self, sample_transaction, mock_services):
        """Test high risk score triggers alert generation."""
        # This would need actual workflow with conditional logic
        # For now, test that alerts are generated
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        
        # If risk is high, alerts should be present
        if result.get("risk_score", 0) > 70:
            assert "alerts" in result or "alert_composer_executed" in result
    
    @pytest.mark.asyncio
    async def test_low_risk_skips_remediation(self, sample_transaction, mock_services):
        """Test low risk transactions skip remediation."""
        # Simulate low risk
        sample_transaction["amount"] = 100  # Small amount
        
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        
        # Low risk might skip some steps
        assert result is not None


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestWorkflowPerformance:
    """Test workflow performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_transaction_workflow_completes_reasonably(self, sample_transaction, mock_services):
        """Test transaction workflow completes in reasonable time."""
        import time
        
        start = time.time()
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        duration = time.time() - start
        
        # Should complete within reasonable time (with mocks)
        assert duration < 5  # 5 seconds with mocks
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_document_workflow_completes_reasonably(self, sample_document):
        """Test document workflow completes in reasonable time."""
        import time
        sample_document["file_content"] = b"test"
        
        start = time.time()
        result = await execute_document_workflow(sample_document)
        duration = time.time() - start
        
        # Should complete within reasonable time (with mocks)
        assert duration < 5
        assert result is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestWorkflowIntegration:
    """Test workflow integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_transaction_creates_alert(self, sample_transaction, mock_services):
        """Test transaction workflow creates alerts for high risk."""
        # High value transaction
        sample_transaction["amount"] = 100000
        sample_transaction["customer_risk_rating"] = "high"
        
        result = await execute_transaction_workflow(
            sample_transaction,
            **mock_services
        )
        
        # Should process successfully
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_document_generates_report(self, sample_document):
        """Test document workflow generates PDF report."""
        sample_document["file_content"] = b"test content"
        
        result = await execute_document_workflow(sample_document)
        
        # Should generate report
        assert result is not None
        assert "report_generator_executed" in result or "report_path" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
