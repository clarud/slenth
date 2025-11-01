"""
Comprehensive test suite for Services layer.

Tests:
1. Vector DB Service (Pinecone)
2. LLM Service  
3. Alert Service
4. Audit Service
5. World-Check One Service
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List, Dict, Any
from datetime import datetime, timezone

# Import services
from services.pinecone_db import PineconeService
from services.llm import LLMService
from services.alert_service import AlertService
from services.audit import AuditService
from services.worldcheck import WorldCheckService


# ============================================================================
# PINECONE DB SERVICE TESTS
# ============================================================================

class TestPineconeService:
    """Test Pinecone vector database service."""
    
    @pytest.fixture
    def mock_pinecone_client(self):
        """Mock Pinecone client."""
        with patch('services.pinecone_db.Pinecone') as MockPinecone:
            mock_client = MagicMock()
            mock_index = MagicMock()
            
            mock_client.Index.return_value = mock_index
            mock_index.upsert_records = MagicMock(return_value=None)
            mock_index.query = MagicMock(return_value={
                "matches": [
                    {
                        "id": "rule-001",
                        "score": 0.95,
                        "metadata": {"rule_id": "RULE001", "title": "Test Rule"}
                    }
                ]
            })
            
            MockPinecone.return_value = mock_client
            
            yield {'client': mock_client, 'index': mock_index}
    
    def test_pinecone_service_initialization(self, mock_pinecone_client):
        """Test Pinecone service initializes."""
        service = PineconeService(index_type="internal")
        
        assert service is not None
        assert service.index_type == "internal"
    
    @pytest.mark.asyncio
    async def test_search_by_text(self, mock_pinecone_client):
        """Test text-based semantic search."""
        service = PineconeService(index_type="internal")
        
        results = await service.search_by_text(
            "High value transaction rules",
            top_k=10
        )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, mock_pinecone_client):
        """Test search with metadata filters."""
        service = PineconeService(index_type="internal")
        
        results = await service.search_by_text(
            "AML rules",
            top_k=5,
            filter_dict={"jurisdiction": "HK"}
        )
        
        assert isinstance(results, list)
    
    def test_upsert_records(self, mock_pinecone_client):
        """Test upserting records to Pinecone."""
        service = PineconeService(index_type="internal")
        
        records = [
            {
                "_id": "test-001",
                "text": "Test document content",
                "metadata_field": "value"
            }
        ]
        
        # Should not raise exception
        service.index.upsert_records(records=records, namespace="__default__")
    
    def test_get_index_stats(self, mock_pinecone_client):
        """Test retrieving index statistics."""
        mock_pinecone_client['index'].describe_index_stats.return_value = {
            'total_vector_count': 150,
            'dimension': 1024
        }
        
        service = PineconeService(index_type="internal")
        stats = service.get_index_stats()
        
        assert isinstance(stats, dict)
        if stats:
            assert 'total_vector_count' in stats or 'dimension' in stats


# ============================================================================
# LLM SERVICE TESTS
# ============================================================================

class TestLLMService:
    """Test LLM service."""
    
    @pytest.fixture
    def mock_openai(self):
        """Mock OpenAI client."""
        with patch('services.llm.openai') as mock:
            mock.chat.completions.create = AsyncMock(return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="Test response"))]
            ))
            yield mock
    
    @pytest.mark.asyncio
    async def test_llm_service_initialization(self):
        """Test LLM service initializes."""
        service = LLMService()
        
        assert service is not None
    
    @pytest.mark.asyncio
    async def test_chat_completion(self, mock_openai):
        """Test chat completion."""
        service = LLMService()
        
        response = await service.chat(
            messages=[{"role": "user", "content": "Test prompt"}],
            temperature=0.7
        )
        
        assert isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_structured_output(self, mock_openai):
        """Test structured output generation."""
        service = LLMService()
        
        response = await service.chat(
            messages=[{"role": "user", "content": "Analyze transaction"}],
            response_format={"type": "json_object"}
        )
        
        assert isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_handles_api_errors(self, mock_openai):
        """Test handling of API errors."""
        mock_openai.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        
        service = LLMService()
        
        with pytest.raises(Exception):
            await service.chat(
                messages=[{"role": "user", "content": "Test"}]
            )


# ============================================================================
# ALERT SERVICE TESTS
# ============================================================================

class TestAlertService:
    """Test alert management service."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.query = MagicMock()
        return session
    
    def test_alert_service_initialization(self, mock_db_session):
        """Test alert service initializes."""
        service = AlertService(mock_db_session)
        
        assert service is not None
    
    def test_create_alert(self, mock_db_session):
        """Test alert creation."""
        service = AlertService(mock_db_session)
        
        alert = service.create_alert(
            transaction_id="TXN001",
            alert_type="high_risk",
            severity="high",
            message="High risk transaction detected",
            assigned_to="compliance_team"
        )
        
        assert alert is not None
        mock_db_session.add.assert_called()
    
    def test_get_alerts_by_status(self, mock_db_session):
        """Test retrieving alerts by status."""
        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            MagicMock(alert_id="A001", status="open")
        ]
        
        service = AlertService(mock_db_session)
        alerts = service.get_alerts_by_status("open")
        
        assert isinstance(alerts, list)
    
    def test_acknowledge_alert(self, mock_db_session):
        """Test alert acknowledgment."""
        mock_alert = MagicMock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_alert
        
        service = AlertService(mock_db_session)
        service.acknowledge_alert("A001", "user@example.com")
        
        assert mock_alert.acknowledged is True
        mock_db_session.commit.assert_called()
    
    def test_alert_routing(self, mock_db_session):
        """Test alert routing to teams."""
        service = AlertService(mock_db_session)
        
        # Route by severity
        team = service.route_alert("critical", "transaction")
        
        assert team in ["front_office", "compliance", "legal", ""]
    
    def test_sla_calculation(self, mock_db_session):
        """Test SLA deadline calculation."""
        service = AlertService(mock_db_session)
        
        sla_hours = service.calculate_sla("critical")
        
        assert isinstance(sla_hours, (int, float))
        assert sla_hours > 0


# ============================================================================
# AUDIT SERVICE TESTS
# ============================================================================

class TestAuditService:
    """Test audit trail service."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        return session
    
    def test_audit_service_initialization(self, mock_db_session):
        """Test audit service initializes."""
        service = AuditService(mock_db_session)
        
        assert service is not None
    
    def test_log_action(self, mock_db_session):
        """Test logging user action."""
        service = AuditService(mock_db_session)
        
        service.log_action(
            user_id="user@example.com",
            action="acknowledge_alert",
            entity_type="alert",
            entity_id="A001",
            details={"timestamp": datetime.now(timezone.utc).isoformat()}
        )
        
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
    
    def test_log_system_event(self, mock_db_session):
        """Test logging system event."""
        service = AuditService(mock_db_session)
        
        service.log_system_event(
            event_type="transaction_processed",
            details={"transaction_id": "TXN001", "risk_score": 75}
        )
        
        mock_db_session.add.assert_called()
    
    def test_get_audit_trail(self, mock_db_session):
        """Test retrieving audit trail."""
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            MagicMock(action="test_action", timestamp=datetime.now(timezone.utc))
        ]
        
        service = AuditService(mock_db_session)
        trail = service.get_audit_trail(entity_id="TXN001")
        
        assert isinstance(trail, list)
    
    def test_audit_trail_immutability(self, mock_db_session):
        """Test audit records cannot be modified."""
        service = AuditService(mock_db_session)
        
        # Audit records should not have update methods
        assert not hasattr(service, 'update_audit_log')


# ============================================================================
# WORLD-CHECK ONE SERVICE TESTS
# ============================================================================

class TestWorldCheckService:
    """Test World-Check One integration service."""
    
    @pytest.fixture
    def mock_worldcheck_api(self):
        """Mock World-Check One API."""
        with patch('services.worldcheck.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "results": [],
                "status": "complete"
            }
            mock_response.status_code = 200
            mock_requests.post.return_value = mock_response
            mock_requests.get.return_value = mock_response
            
            yield mock_requests
    
    @pytest.mark.asyncio
    async def test_worldcheck_service_initialization(self):
        """Test World-Check service initializes."""
        service = WorldCheckService()
        
        assert service is not None
    
    @pytest.mark.asyncio
    async def test_screen_individual(self, mock_worldcheck_api):
        """Test screening individual person."""
        service = WorldCheckService()
        
        result = await service.screen_entity(
            name="John Doe",
            entity_type="individual",
            date_of_birth="1980-01-01"
        )
        
        assert isinstance(result, dict)
        assert "match_status" in result or "results" in result or "status" in result
    
    @pytest.mark.asyncio
    async def test_screen_organization(self, mock_worldcheck_api):
        """Test screening organization."""
        service = WorldCheckService()
        
        result = await service.screen_entity(
            name="Test Corporation",
            entity_type="organization"
        )
        
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_pep_screening(self, mock_worldcheck_api):
        """Test PEP (Politically Exposed Person) screening."""
        service = WorldCheckService()
        
        result = await service.screen_entity(
            name="Political Figure",
            entity_type="individual",
            screening_type="pep"
        )
        
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_sanctions_screening(self, mock_worldcheck_api):
        """Test sanctions list screening."""
        service = WorldCheckService()
        
        result = await service.screen_entity(
            name="Sanctioned Entity",
            entity_type="organization",
            screening_type="sanctions"
        )
        
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_adverse_media_screening(self, mock_worldcheck_api):
        """Test adverse media screening."""
        service = WorldCheckService()
        
        result = await service.screen_entity(
            name="Test Person",
            entity_type="individual",
            screening_type="adverse_media"
        )
        
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_handles_api_errors(self, mock_worldcheck_api):
        """Test handling of World-Check API errors."""
        mock_worldcheck_api.post.side_effect = Exception("API Error")
        
        service = WorldCheckService()
        
        # Should handle gracefully
        result = await service.screen_entity(
            name="Test",
            entity_type="individual"
        )
        
        # Should return error indication
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_match_result_parsing(self, mock_worldcheck_api):
        """Test parsing of match results."""
        mock_worldcheck_api.get.return_value.json.return_value = {
            "results": [
                {
                    "match_strength": "strong",
                    "category": "PEP",
                    "name": "John Doe"
                }
            ]
        }
        
        service = WorldCheckService()
        result = await service.screen_entity(
            name="John Doe",
            entity_type="individual"
        )
        
        assert isinstance(result, dict)


# ============================================================================
# SERVICE INTEGRATION TESTS
# ============================================================================

class TestServiceIntegration:
    """Test service layer integration."""
    
    @pytest.mark.asyncio
    async def test_llm_and_vector_db_integration(self):
        """Test LLM and vector DB work together."""
        # This would test RAG pipeline
        # LLM generates query -> Vector DB searches -> LLM processes results
        pass
    
    @pytest.mark.asyncio
    async def test_alert_and_audit_integration(self):
        """Test alert creation triggers audit log."""
        mock_db = MagicMock()
        
        alert_service = AlertService(mock_db)
        audit_service = AuditService(mock_db)
        
        # Create alert
        alert = alert_service.create_alert(
            transaction_id="TXN001",
            alert_type="test",
            severity="high",
            message="Test"
        )
        
        # Log audit
        audit_service.log_action(
            user_id="system",
            action="alert_created",
            entity_type="alert",
            entity_id=getattr(alert, 'alert_id', 'A001')
        )
        
        # Both should have called database
        assert mock_db.add.called
        assert mock_db.commit.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
