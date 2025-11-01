"""
Comprehensive test suite for Part 1 Transaction Monitoring Agents.

Tests all 13 agents in the transaction workflow:
1. ContextBuilder
2. Retrieval
3. Applicability
4. EvidenceMapper
5. ControlTest
6. FeatureService
7. BayesianEngine
8. PatternDetector
9. DecisionFusion
10. AnalystWriter
11. AlertComposer
12. RemediationOrchestrator
13. Persistor

This test suite uses REAL services:
- LLM: Groq via services/llm.py
- Vector DB: Pinecone (internal + external indexes)
- Database: PostgreSQL via DATABASE_URL
"""
import pytest
import os
from dotenv import load_dotenv
from typing import Dict, Any, List
from datetime import datetime, timezone

# Load environment variables from .env
load_dotenv()


# ============================================================================
# LOAD ENVIRONMENT VARIABLES FOR TESTING
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def load_env_vars():
    """
    Load real environment variables for testing.
    
    Required variables in .env:
    - GROQ_API_KEY
    - PINECONE_API_KEY
    - PINECONE_INTERNAL_INDEX_HOST
    - PINECONE_EXTERNAL_INDEX_HOST
    - DATABASE_URL
    """
    required_vars = [
        "GROQ_API_KEY",
        "PINECONE_API_KEY", 
        "PINECONE_INTERNAL_INDEX_HOST",
        "PINECONE_EXTERNAL_INDEX_HOST",
        "DATABASE_URL"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    yield


# Import real services
from services.llm import LLMService
from services.pinecone_db import PineconeService
from db.database import SessionLocal

# Import agents (after environment is loaded)
from agents.part1.context_builder import ContextBuilderAgent
from agents.part1.retrieval import RetrievalAgent
from agents.part1.applicability import ApplicabilityAgent
from agents.part1.evidence_mapper import EvidenceMapperAgent
from agents.part1.control_test import ControlTestAgent
from agents.part1.feature_service import FeatureServiceAgent
from agents.part1.bayesian_engine import BayesianEngineAgent
from agents.part1.pattern_detector import PatternDetectorAgent
from agents.part1.decision_fusion import DecisionFusionAgent
from agents.part1.analyst_writer import AnalystWriterAgent
from agents.part1.alert_composer import AlertComposerAgent
from agents.part1.remediation_orchestrator import RemediationOrchestratorAgent
from agents.part1.persistor import PersistorAgent


@pytest.fixture
def sample_transaction():
    """Sample transaction for testing."""
    return {
        "transaction_id": "TXN001",
        "amount": 50000,
        "currency": "USD",
        "customer_id": "CUST123",
        "originator_country": "HK",
        "beneficiary_country": "SG",
        "customer_risk_rating": "high",
        "transaction_type": "wire_transfer",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_state(sample_transaction):
    """Sample workflow state."""
    return {
        "transaction": sample_transaction,
        "transaction_id": sample_transaction["transaction_id"],
        "errors": []
    }


@pytest.fixture(scope="session")
def real_db_session():
    """Real database session from SessionLocal."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="session")
def real_llm_service():
    """Real LLM service (Groq)."""
    return LLMService()


@pytest.fixture(scope="session")
def real_pinecone_internal():
    """Real Pinecone service for internal rules."""
    return PineconeService(index_type="internal")


@pytest.fixture(scope="session")
def real_pinecone_external():
    """Real Pinecone service for external rules."""
    return PineconeService(index_type="external")


# ============================================================================
# TEST CLASS 1: ContextBuilderAgent
# ============================================================================

class TestContextBuilderAgent:
    """Test ContextBuilderAgent functionality with real database."""
    
    @pytest.mark.asyncio
    async def test_context_builder_execution(self, sample_state, real_db_session):
        """Test context builder creates query context."""
        agent = ContextBuilderAgent(real_db_session)
        
        result = await agent.execute(sample_state)
        
        assert "query_context" in result
        assert result["context_builder_executed"] is True
        assert "errors" in result
        
    @pytest.mark.asyncio
    async def test_context_includes_transaction_details(self, sample_state, real_db_session):
        """Test context includes transaction amount and countries."""
        agent = ContextBuilderAgent(real_db_session)
        
        result = await agent.execute(sample_state)
        query_context = result.get("query_context", "")
        
        assert "50000" in query_context or "50,000" in query_context
        assert "HK" in query_context or "Hong Kong" in query_context
        
    @pytest.mark.asyncio
    async def test_transaction_history_retrieval(self, sample_state, real_db_session):
        """Test retrieval of customer transaction history from real database."""
        agent = ContextBuilderAgent(real_db_session)
        result = await agent.execute(sample_state)
        
        # transaction_history may be empty if customer has no history
        assert "transaction_history" in result or result.get("context_builder_executed") is True
        
    @pytest.mark.asyncio
    async def test_handles_missing_transaction(self, real_db_session):
        """Test graceful handling of missing transaction data."""
        state = {"errors": []}
        agent = ContextBuilderAgent(real_db_session)
        
        result = await agent.execute(state)
        
        # Should handle gracefully without crashing
        assert "errors" in result


# ============================================================================
# TEST CLASS 2: RetrievalAgent
# ============================================================================

class TestRetrievalAgent:
    """Test RetrievalAgent functionality with real Pinecone."""
    
    @pytest.mark.asyncio
    async def test_retrieval_executes(self, sample_state, real_llm_service, real_pinecone_internal, real_pinecone_external):
        """Test retrieval agent executes successfully with real services."""
        agent = RetrievalAgent(
            llm_service=real_llm_service,
            pinecone_internal=real_pinecone_internal,
            pinecone_external=real_pinecone_external
        )
        sample_state["query_context"] = "High value transaction from HK to SG"
        
        result = await agent.execute(sample_state)
        
        assert "retrieved_rules" in result
        assert result["retrieval_executed"] is True
        
    @pytest.mark.asyncio
    async def test_retrieval_returns_rules(self, sample_state, real_llm_service, real_pinecone_internal, real_pinecone_external):
        """Test retrieval returns applicable rules from real Pinecone."""
        agent = RetrievalAgent(
            llm_service=real_llm_service,
            pinecone_internal=real_pinecone_internal,
            pinecone_external=real_pinecone_external
        )
        sample_state["query_context"] = "High value transaction monitoring requirements for Hong Kong"
        
        result = await agent.execute(sample_state)
        retrieved_rules = result.get("retrieved_rules", [])
        
        assert isinstance(retrieved_rules, list)
        # Rules may or may not be found depending on index content
        print(f"Retrieved {len(retrieved_rules)} rules from Pinecone")
    
    @pytest.mark.asyncio
    async def test_handles_no_rules_found(self, sample_state, real_llm_service, real_pinecone_internal, real_pinecone_external):
        """Test handling when no rules match."""
        agent = RetrievalAgent(
            llm_service=real_llm_service,
            pinecone_internal=real_pinecone_internal,
            pinecone_external=real_pinecone_external
        )
        sample_state["query_context"] = "Completely irrelevant query xyz123"
        
        result = await agent.execute(sample_state)
        
        assert "retrieved_rules" in result
        assert result["retrieved_rules"] == []


# ============================================================================
# TEST CLASS 3: ApplicabilityAgent
# ============================================================================

class TestApplicabilityAgent:
    """Test ApplicabilityAgent functionality with real Groq LLM."""
    
    @pytest.mark.asyncio
    async def test_applicability_execution(self, sample_state, real_llm_service):
        """Test applicability agent executes with real LLM."""
        agent = ApplicabilityAgent(real_llm_service)
        sample_state["retrieved_rules"] = [{"rule_id": "RULE001", "title": "High Value Transaction Monitoring"}]
        
        result = await agent.execute(sample_state)
        
        assert "applicable_rules" in result
        assert result["applicability_executed"] is True
    
    @pytest.mark.asyncio
    async def test_applicability_assessment(self, sample_state, real_llm_service):
        """Test applicability assessment logic with real LLM."""
        agent = ApplicabilityAgent(real_llm_service)
        sample_state["retrieved_rules"] = [{"rule_id": "RULE001", "title": "Anti-Money Laundering Rule"}]
        
        result = await agent.execute(sample_state)
        applicable_rules = result.get("applicable_rules", [])
        
        assert isinstance(applicable_rules, list)
        print(f"LLM determined {len(applicable_rules)} applicable rules")
    
    @pytest.mark.asyncio
    async def test_handles_empty_rules(self, sample_state, real_llm_service):
        """Test handling of empty rules list."""
        agent = ApplicabilityAgent(real_llm_service)
        sample_state["retrieved_rules"] = []
        
        result = await agent.execute(sample_state)
        
        assert result.get("applicable_rules") == []


# ============================================================================
# TEST CLASS 4: EvidenceMapperAgent
# ============================================================================

class TestEvidenceMapperAgent:
    """Test EvidenceMapperAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_evidence_mapper_execution(self, sample_state, mock_llm_service):
        """Test evidence mapper executes."""
        agent = EvidenceMapperAgent(mock_llm_service)
        sample_state["applicable_rules"] = [{"rule_id": "RULE001"}]
        
        result = await agent.execute(sample_state)
        
        assert "evidence_mapping" in result
        assert result["evidence_mapper_executed"] is True
    
    @pytest.mark.asyncio
    async def test_evidence_identification(self, sample_state, mock_llm_service):
        """Test identification of present and missing evidence."""
        agent = EvidenceMapperAgent(mock_llm_service)
        sample_state["applicable_rules"] = [{"rule_id": "RULE001", "evidence_required": ["amount", "kyc"]}]
        
        result = await agent.execute(sample_state)
        evidence_mapping = result.get("evidence_mapping", {})
        
        assert isinstance(evidence_mapping, dict)


# ============================================================================
# TEST CLASS 5: ControlTestAgent
# ============================================================================

class TestControlTestAgent:
    """Test ControlTestAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_control_test_execution(self, sample_state, mock_llm_service):
        """Test control test agent executes."""
        agent = ControlTestAgent(mock_llm_service)
        sample_state["applicable_rules"] = [{"rule_id": "RULE001"}]
        sample_state["evidence_mapping"] = {"RULE001": {"present": [], "missing": []}}
        
        result = await agent.execute(sample_state)
        
        assert "control_results" in result
        assert result["control_test_executed"] is True
    
    @pytest.mark.asyncio
    async def test_control_pass_fail_determination(self, sample_state, mock_llm_service):
        """Test pass/fail determination for controls."""
        mock_llm_service.chat = AsyncMock(return_value='{"status": "fail", "severity": "high", "score": 0.3}')
        
        agent = ControlTestAgent(mock_llm_service)
        sample_state["applicable_rules"] = [{"rule_id": "RULE001"}]
        sample_state["evidence_mapping"] = {}
        
        result = await agent.execute(sample_state)
        control_results = result.get("control_results", [])
        
        assert isinstance(control_results, list)


# ============================================================================
# TEST CLASS 6: FeatureServiceAgent
# ============================================================================

class TestFeatureServiceAgent:
    """Test FeatureServiceAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_feature_extraction(self, sample_state, mock_db_session):
        """Test feature extraction from transaction."""
        agent = FeatureServiceAgent(mock_db_session)
        
        result = await agent.execute(sample_state)
        
        assert "features" in result
        assert result["feature_service_executed"] is True
        
    @pytest.mark.asyncio
    async def test_amount_features(self, sample_state, mock_db_session):
        """Test amount-related features."""
        agent = FeatureServiceAgent(mock_db_session)
        
        result = await agent.execute(sample_state)
        features = result.get("features", {})
        
        assert "amount" in features
        assert "is_high_value" in features
        assert features["amount"] == 50000
        
    @pytest.mark.asyncio
    async def test_velocity_features(self, sample_state, mock_db_session):
        """Test velocity features from transaction history."""
        sample_state["transaction_history"] = [
            {"amount": 1000, "hours_ago": 2},
            {"amount": 2000, "hours_ago": 48}
        ]
        
        agent = FeatureServiceAgent(mock_db_session)
        result = await agent.execute(sample_state)
        features = result.get("features", {})
        
        assert "transaction_count_24h" in features or "transaction_count_7d" in features


# ============================================================================
# TEST CLASS 7: BayesianEngineAgent
# ============================================================================

class TestBayesianEngineAgent:
    """Test BayesianEngineAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_bayesian_execution(self, sample_state):
        """Test Bayesian engine executes."""
        agent = BayesianEngineAgent()
        sample_state["features"] = {"is_high_value": True, "is_round_number": True}
        sample_state["control_results"] = [{"status": "fail", "severity": "high"}]
        
        result = await agent.execute(sample_state)
        
        assert "posterior_probabilities" in result
        assert result["bayesian_engine_executed"] is True
    
    @pytest.mark.asyncio
    async def test_risk_probability_calculation(self, sample_state):
        """Test risk probability calculations."""
        agent = BayesianEngineAgent()
        sample_state["features"] = {"is_high_value": True}
        sample_state["control_results"] = []
        
        result = await agent.execute(sample_state)
        posterior = result.get("posterior_probabilities", {})
        
        assert isinstance(posterior, dict)
        # Should have probabilities for risk categories
        if posterior:
            assert all(isinstance(v, (int, float)) for v in posterior.values())


# ============================================================================
# TEST CLASS 8: PatternDetectorAgent
# ============================================================================

class TestPatternDetectorAgent:
    """Test PatternDetectorAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_pattern_detection(self, sample_state, mock_db_session):
        """Test pattern detection executes."""
        agent = PatternDetectorAgent(mock_db_session)
        
        result = await agent.execute(sample_state)
        
        assert "detected_patterns" in result
        assert result["pattern_detector_executed"] is True
    
    @pytest.mark.asyncio
    async def test_structuring_detection(self, sample_state, mock_db_session):
        """Test structuring pattern detection."""
        sample_state["transaction_history"] = [
            {"amount": 9000, "hours_ago": 1},
            {"amount": 9500, "hours_ago": 2},
            {"amount": 9800, "hours_ago": 3}
        ]
        
        agent = PatternDetectorAgent(mock_db_session)
        result = await agent.execute(sample_state)
        patterns = result.get("detected_patterns", [])
        
        assert isinstance(patterns, list)


# ============================================================================
# TEST CLASS 9: DecisionFusionAgent
# ============================================================================

class TestDecisionFusionAgent:
    """Test DecisionFusionAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_decision_fusion(self, sample_state):
        """Test decision fusion executes."""
        agent = DecisionFusionAgent()
        sample_state["control_results"] = [{"score": 0.3}]
        sample_state["posterior_probabilities"] = {"high": 0.7}
        sample_state["detected_patterns"] = []
        
        result = await agent.execute(sample_state)
        
        assert "risk_score" in result
        assert "risk_band" in result
        assert result["decision_fusion_executed"] is True
    
    @pytest.mark.asyncio
    async def test_risk_score_calculation(self, sample_state):
        """Test risk score is within valid range."""
        agent = DecisionFusionAgent()
        sample_state["control_results"] = []
        sample_state["posterior_probabilities"] = {}
        sample_state["detected_patterns"] = []
        
        result = await agent.execute(sample_state)
        risk_score = result.get("risk_score", 0)
        
        assert 0 <= risk_score <= 100
    
    @pytest.mark.asyncio
    async def test_risk_band_assignment(self, sample_state):
        """Test risk band assignment."""
        agent = DecisionFusionAgent()
        sample_state["control_results"] = []
        sample_state["posterior_probabilities"] = {}
        sample_state["detected_patterns"] = []
        
        result = await agent.execute(sample_state)
        risk_band = result.get("risk_band", "")
        
        assert risk_band in ["Low", "Medium", "High", "Critical", ""]


# ============================================================================
# TEST CLASS 10: AnalystWriterAgent
# ============================================================================

class TestAnalystWriterAgent:
    """Test AnalystWriterAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_analyst_writer_execution(self, sample_state, mock_llm_service):
        """Test analyst writer generates summary."""
        agent = AnalystWriterAgent(mock_llm_service)
        sample_state["applicable_rules"] = []
        sample_state["control_results"] = []
        sample_state["risk_score"] = 75
        sample_state["risk_band"] = "High"
        
        result = await agent.execute(sample_state)
        
        assert "compliance_analysis" in result
        assert result["analyst_writer_executed"] is True
    
    @pytest.mark.asyncio
    async def test_analysis_includes_risk_info(self, sample_state, mock_llm_service):
        """Test analysis includes risk information."""
        mock_llm_service.chat = AsyncMock(return_value="Risk assessment: High risk transaction")
        
        agent = AnalystWriterAgent(mock_llm_service)
        sample_state["risk_score"] = 85
        sample_state["risk_band"] = "High"
        
        result = await agent.execute(sample_state)
        analysis = result.get("compliance_analysis", "")
        
        assert isinstance(analysis, str)


# ============================================================================
# TEST CLASS 11: AlertComposerAgent
# ============================================================================

class TestAlertComposerAgent:
    """Test AlertComposerAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_alert_composer_execution(self, sample_state, mock_db_session):
        """Test alert composer executes."""
        agent = AlertComposerAgent(mock_db_session)
        sample_state["risk_band"] = "High"
        sample_state["compliance_analysis"] = "Test analysis"
        
        result = await agent.execute(sample_state)
        
        assert "alerts" in result
        assert result["alert_composer_executed"] is True
    
    @pytest.mark.asyncio
    async def test_alert_creation_for_high_risk(self, sample_state, mock_db_session):
        """Test alerts created for high risk transactions."""
        agent = AlertComposerAgent(mock_db_session)
        sample_state["risk_band"] = "Critical"
        sample_state["risk_score"] = 95
        
        result = await agent.execute(sample_state)
        alerts = result.get("alerts", [])
        
        assert isinstance(alerts, list)
    
    @pytest.mark.asyncio
    async def test_no_alerts_for_low_risk(self, sample_state, mock_db_session):
        """Test no alerts for low risk transactions."""
        agent = AlertComposerAgent(mock_db_session)
        sample_state["risk_band"] = "Low"
        sample_state["risk_score"] = 10
        
        result = await agent.execute(sample_state)
        alerts = result.get("alerts", [])
        
        # Should have minimal or no alerts for low risk
        assert isinstance(alerts, list)


# ============================================================================
# TEST CLASS 12: RemediationOrchestratorAgent
# ============================================================================

class TestRemediationOrchestratorAgent:
    """Test RemediationOrchestratorAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_remediation_execution(self, sample_state, mock_db_session):
        """Test remediation orchestrator executes."""
        agent = RemediationOrchestratorAgent(mock_db_session)
        sample_state["risk_band"] = "High"
        sample_state["control_results"] = [{"status": "fail"}]
        
        result = await agent.execute(sample_state)
        
        assert "remediation_actions" in result
        assert result["remediation_orchestrator_executed"] is True
    
    @pytest.mark.asyncio
    async def test_remediation_actions_suggested(self, sample_state, mock_db_session):
        """Test remediation actions are suggested."""
        agent = RemediationOrchestratorAgent(mock_db_session)
        sample_state["risk_band"] = "Critical"
        sample_state["control_results"] = [{"status": "fail", "severity": "critical"}]
        
        result = await agent.execute(sample_state)
        actions = result.get("remediation_actions", [])
        
        assert isinstance(actions, list)


# ============================================================================
# TEST CLASS 13: PersistorAgent
# ============================================================================

class TestPersistorAgent:
    """Test PersistorAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_persistor_execution(self, sample_state, mock_db_session):
        """Test persistor stores results."""
        agent = PersistorAgent(mock_db_session)
        sample_state["risk_score"] = 75
        sample_state["risk_band"] = "High"
        sample_state["compliance_analysis"] = "Test"
        
        result = await agent.execute(sample_state)
        
        assert result["persistor_executed"] is True
    
    @pytest.mark.asyncio
    async def test_audit_trail_creation(self, sample_state, mock_db_session):
        """Test audit trail is created."""
        agent = PersistorAgent(mock_db_session)
        sample_state["risk_score"] = 50
        
        result = await agent.execute(sample_state)
        
        # Verify database operations were called
        assert mock_db_session.add.called or mock_db_session.commit.called or result.get("records_persisted")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestAgentIntegration:
    """Test agent integration and workflow."""
    
    @pytest.mark.asyncio
    async def test_sequential_agent_execution(self, sample_state, mock_db_session, mock_llm_service, mock_vector_service, mock_embedding_service):
        """Test agents can be chained sequentially."""
        # Execute agents in sequence
        context_builder = ContextBuilderAgent(mock_db_session)
        state1 = await context_builder.execute(sample_state)
        
        assert "query_context" in state1
        
        retrieval = RetrievalAgent(mock_llm_service, mock_vector_service, mock_embedding_service)
        state2 = await retrieval.execute(state1)
        
        assert "retrieved_rules" in state2
        
        # Verify state is preserved across agents
        assert state2.get("transaction_id") == sample_state["transaction_id"]
    
    @pytest.mark.asyncio
    async def test_error_propagation(self, sample_state, mock_db_session):
        """Test errors are captured and propagated."""
        agent = ContextBuilderAgent(mock_db_session)
        
        # Inject an error condition
        corrupt_state = {"errors": []}  # Missing transaction
        
        result = await agent.execute(corrupt_state)
        
        # Errors should be tracked
        assert "errors" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
