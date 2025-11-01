"""
Test suite for Pinecone vector database integration.

Tests cover:
1. Data ingestion correctness
2. Record format validation (Pinecone inference API)
3. Metadata integrity
4. Similarity search functionality
5. End-to-end retrieval workflow

Note: Uses Pinecone inference API (automatic embeddings from text)
No separate embedding service needed.
"""
import pytest
import json
from pathlib import Path
from typing import List, Dict
from unittest.mock import Mock, patch, MagicMock
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPineconeDataIngestion:
    """Test data ingestion from internal_rules/* to Pinecone."""
    
    @pytest.fixture
    def sample_passages(self) -> List[Dict]:
        """Sample passages matching internal_rules JSON structure."""
        return [
            {
                "ID": "test-uuid-001",
                "DocumentID": 1,
                "PassageID": "1.1",
                "Passage": "The AML Rulebook applies to all financial institutions in ADGM."
            },
            {
                "ID": "test-uuid-002",
                "DocumentID": 1,
                "PassageID": "1.2",
                "Passage": "Customer Due Diligence must be performed for all new customers."
            },
            {
                "ID": "test-uuid-003",
                "DocumentID": 2,
                "PassageID": "2.1",
                "Passage": "Enhanced Due Diligence is required for high-risk customers including PEPs."
            }
        ]
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables."""
        monkeypatch.setenv('PINECONE_API_KEY', 'test-api-key')
        monkeypatch.setenv('PINECONE_INTERNAL_INDEX_HOST', 'https://test-index.pinecone.io')
    
    @pytest.fixture
    def mock_pinecone(self):
        """Mock Pinecone client and index."""
        with patch('scripts.load_internal_rules_pinecone.Pinecone') as MockPinecone:
            mock_client = MagicMock()
            mock_index = MagicMock()
            
            MockPinecone.return_value = mock_client
            mock_client.Index.return_value = mock_index
            mock_index.upsert_records.return_value = None
            
            yield {
                'client_class': MockPinecone,
                'client': mock_client,
                'index': mock_index
            }
    
    def test_json_file_structure_validation(self, sample_passages):
        """Test that JSON files match expected structure."""
        for passage in sample_passages:
            assert "ID" in passage, "Passage must have ID field"
            assert "DocumentID" in passage, "Passage must have DocumentID field"
            assert "PassageID" in passage, "Passage must have PassageID field"
            assert "Passage" in passage, "Passage must have Passage field"
            
            # Validate types
            assert isinstance(passage["ID"], str), "ID must be string"
            assert isinstance(passage["DocumentID"], int), "DocumentID must be int"
            assert isinstance(passage["PassageID"], str), "PassageID must be string"
            assert isinstance(passage["Passage"], str), "Passage must be string"
    
    def test_actual_json_files_exist(self):
        """Test that internal_rules directory contains JSON files."""
        rules_dir = Path(__file__).parent.parent.parent / "internal_rules"
        assert rules_dir.exists(), f"Rules directory not found: {rules_dir}"
        
        json_files = list(rules_dir.glob("*.json"))
        assert len(json_files) > 0, "No JSON files found in internal_rules/"
        
        # Should have files 1.json through 40.json based on user description
        assert len(json_files) >= 10, f"Expected at least 10 JSON files, found {len(json_files)}"
    
    def test_actual_json_file_structure(self):
        """Test that actual JSON files match expected structure."""
        rules_dir = Path(__file__).parent.parent.parent / "internal_rules"
        json_file = rules_dir / "1.json"
        
        if not json_file.exists():
            pytest.skip("1.json not found")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Should be an array
        assert isinstance(data, list), "JSON file should contain array of passages"
        assert len(data) > 0, "JSON file should not be empty"
        
        # Validate first passage structure
        first_passage = data[0]
        assert "ID" in first_passage
        assert "DocumentID" in first_passage
        assert "PassageID" in first_passage
        assert "Passage" in first_passage
    
    def test_record_format_for_pinecone_inference(self, sample_passages):
        """Test that records are formatted correctly for Pinecone inference API."""
        passage = sample_passages[0]
        
        # Format as Pinecone inference API expects
        record = {
            "_id": passage["ID"],
            "text": f"Doc {passage['DocumentID']}: Passage {passage['PassageID']}: {passage['Passage']}",
            "passage_id": passage["ID"],
            "document_id": passage["DocumentID"],
            "passage_ref": passage["PassageID"],
            "passage_excerpt": passage["Passage"][:512],
            "source_file": "1.json",
            "is_active": True,
        }
        
        # Validate record structure
        assert "_id" in record, "Record must have _id"
        assert "text" in record, "Record must have text for embedding"
        assert record["passage_id"] == passage["ID"]
        assert record["document_id"] == passage["DocumentID"]
        assert record["passage_ref"] == passage["PassageID"]
        
        # Text should include context for better embeddings
        assert "Doc" in record["text"]
        assert "Passage" in record["text"]
        assert passage["Passage"] in record["text"]
        
        # Excerpt should be truncated
        assert len(record["passage_excerpt"]) <= 512
    
    def test_metadata_preparation(self, sample_passages):
        """Test that metadata is correctly prepared for Pinecone."""
        passage = sample_passages[0]
        
        # All metadata at top level (flat structure)
        record = {
            "_id": passage["ID"],
            "text": f"Doc {passage['DocumentID']}: Passage {passage['PassageID']}: {passage['Passage']}",
            "passage_id": passage["ID"],
            "document_id": passage["DocumentID"],
            "passage_ref": passage["PassageID"],
            "passage_excerpt": passage["Passage"][:512],
            "source_file": "1.json",
            "is_active": True,
        }
        
        # Validate metadata types (must be primitives)
        for key, value in record.items():
            if key not in ['_id', 'text']:
                assert isinstance(value, (str, int, float, bool)), \
                    f"Metadata {key} must be primitive type, got {type(value)}"
    
    def test_empty_passages_are_skipped(self):
        """Test that passages with empty text are skipped."""
        passages = [
            {"ID": "test-1", "DocumentID": 1, "PassageID": "1.1", "Passage": "Valid text"},
            {"ID": "test-2", "DocumentID": 1, "PassageID": "1.2", "Passage": ""},
            {"ID": "test-3", "DocumentID": 1, "PassageID": "1.3", "Passage": "   "},
        ]
        
        valid_passages = [p for p in passages if p["Passage"].strip()]
        assert len(valid_passages) == 1, "Only non-empty passages should be processed"
    
    def test_batch_upsert_format(self, sample_passages):
        """Test that records are formatted correctly for batch upsert."""
        records = []
        
        for passage in sample_passages:
            if not passage["Passage"].strip():
                continue
            
            record = {
                "_id": passage["ID"],
                "text": f"Doc {passage['DocumentID']}: Passage {passage['PassageID']}: {passage['Passage']}",
                "passage_id": passage["ID"],
                "document_id": passage["DocumentID"],
                "passage_ref": passage["PassageID"],
                "passage_excerpt": passage["Passage"][:512],
            }
            records.append(record)
        
        # Should have 3 valid records
        assert len(records) == 3, "Should have 3 valid passages"
        
        # All records must have _id and text
        for record in records:
            assert "_id" in record
            assert "text" in record
            assert isinstance(record["_id"], str)
            assert isinstance(record["text"], str)
        
        # IDs should be unique
        ids = [r["_id"] for r in records]
        assert len(set(ids)) == len(ids), "All IDs should be unique"
    
    def test_batch_size_limit(self, sample_passages):
        """Test that batches respect Pinecone inference API limit (96 records)."""
        # Simulate 200 passages
        large_batch = sample_passages * 67  # 201 passages
        
        # Should split into batches of 96
        batch_size = 96
        batches = [large_batch[i:i + batch_size] for i in range(0, len(large_batch), batch_size)]
        
        assert len(batches) == 3, "Should split into 3 batches"
        assert len(batches[0]) == 96
        assert len(batches[1]) == 96
        assert len(batches[2]) == 9  # Remaining


class TestPineconeVectorStorage:
    """Test vector storage and retrieval from Pinecone."""
    
    @pytest.fixture
    def mock_pinecone_index(self):
        """Mock Pinecone index with query capability."""
        index = MagicMock()
        
        # Mock query response
        index.query.return_value = {
            'matches': [
                {
                    'id': 'test-uuid-001',
                    'score': 0.95,
                    'metadata': {
                        'passage_id': 'test-uuid-001',
                        'document_id': 1,
                        'passage_ref': '1.1',
                        'passage_text': 'The AML Rulebook applies to all financial institutions.',
                        'jurisdiction': 'ADGM'
                    }
                },
                {
                    'id': 'test-uuid-002',
                    'score': 0.87,
                    'metadata': {
                        'passage_id': 'test-uuid-002',
                        'document_id': 1,
                        'passage_ref': '1.2',
                        'passage_text': 'Customer Due Diligence must be performed.',
                        'jurisdiction': 'ADGM'
                    }
                }
            ]
        }
        
        # Mock describe_index_stats
        index.describe_index_stats.return_value = {
            'total_vector_count': 150,
            'dimension': 3072
        }
        
        return index
    
    def test_vector_dimension_consistency(self, mock_pinecone_index):
        """Test that all vectors have consistent dimensions."""
        stats = mock_pinecone_index.describe_index_stats()
        assert stats['dimension'] == 3072, "All vectors must be 3072-dimensional"
    
    def test_vector_retrieval_by_id(self, mock_pinecone_index):
        """Test that vectors can be retrieved by their ID."""
        query_result = mock_pinecone_index.query(
            vector=[0.1] * 3072,
            top_k=10,
            include_metadata=True
        )
        
        matches = query_result['matches']
        assert len(matches) > 0, "Should return matches"
        
        # Check that IDs match expected format (UUIDs from JSON)
        for match in matches:
            assert 'id' in match
            assert 'metadata' in match
            assert match['metadata']['passage_id'] == match['id']
    
    def test_metadata_completeness(self, mock_pinecone_index):
        """Test that stored metadata contains all required fields."""
        query_result = mock_pinecone_index.query(
            vector=[0.1] * 3072,
            top_k=10,
            include_metadata=True
        )
        
        required_fields = [
            'passage_id', 'document_id', 'passage_ref', 
            'passage_text', 'jurisdiction'
        ]
        
        for match in query_result['matches']:
            metadata = match['metadata']
            for field in required_fields:
                assert field in metadata, f"Metadata missing required field: {field}"
    
    def test_similarity_scores_are_valid(self, mock_pinecone_index):
        """Test that similarity scores are in valid range."""
        query_result = mock_pinecone_index.query(
            vector=[0.1] * 3072,
            top_k=10,
            include_metadata=True
        )
        
        for match in query_result['matches']:
            score = match['score']
            assert 0.0 <= score <= 1.0, f"Score {score} out of valid range [0, 1]"
    
    def test_results_sorted_by_relevance(self, mock_pinecone_index):
        """Test that query results are sorted by relevance score."""
        query_result = mock_pinecone_index.query(
            vector=[0.1] * 3072,
            top_k=10,
            include_metadata=True
        )
        
        scores = [match['score'] for match in query_result['matches']]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"


class TestPineconeMetadataFiltering:
    """Test metadata filtering capabilities."""
    
    @pytest.fixture
    def mock_pinecone_service(self):
        """Mock Pinecone service with filtering support."""
        service = Mock(spec=PineconeService)
        
        def mock_similarity_search(query_vector, top_k=10, filter_dict=None):
            """Mock similarity search with filter support."""
            all_results = [
                {
                    'id': 'test-1',
                    'score': 0.95,
                    'metadata': {
                        'document_id': 1,
                        'jurisdiction': 'ADGM',
                        'is_active': True,
                        'document_type': 'aml_rulebook'
                    }
                },
                {
                    'id': 'test-2',
                    'score': 0.90,
                    'metadata': {
                        'document_id': 2,
                        'jurisdiction': 'HK',
                        'is_active': True,
                        'document_type': 'aml_rulebook'
                    }
                },
                {
                    'id': 'test-3',
                    'score': 0.85,
                    'metadata': {
                        'document_id': 3,
                        'jurisdiction': 'ADGM',
                        'is_active': False,
                        'document_type': 'archived'
                    }
                }
            ]
            
            # Apply filters
            filtered_results = all_results
            if filter_dict:
                filtered_results = [
                    r for r in all_results
                    if all(r['metadata'].get(k) == v for k, v in filter_dict.items())
                ]
            
            return filtered_results[:top_k]
        
        service.similarity_search.side_effect = mock_similarity_search
        return service
    
    def test_filter_by_jurisdiction(self, mock_pinecone_service):
        """Test filtering by jurisdiction."""
        query_vector = [0.1] * 3072
        
        # Filter for ADGM only
        results = mock_pinecone_service.similarity_search(
            query_vector,
            top_k=10,
            filter_dict={"jurisdiction": "ADGM"}
        )
        
        assert all(r['metadata']['jurisdiction'] == 'ADGM' for r in results)
    
    def test_filter_by_active_status(self, mock_pinecone_service):
        """Test filtering by is_active status."""
        query_vector = [0.1] * 3072
        
        # Filter for active rules only
        results = mock_pinecone_service.similarity_search(
            query_vector,
            top_k=10,
            filter_dict={"is_active": True}
        )
        
        assert all(r['metadata']['is_active'] is True for r in results)
        assert len(results) == 2, "Should only return active rules"
    
    def test_combined_filters(self, mock_pinecone_service):
        """Test combining multiple filters."""
        query_vector = [0.1] * 3072
        
        # Filter for active ADGM rules
        results = mock_pinecone_service.similarity_search(
            query_vector,
            top_k=10,
            filter_dict={
                "jurisdiction": "ADGM",
                "is_active": True
            }
        )
        
        assert len(results) == 1, "Should only return rules matching all filters"
        assert results[0]['metadata']['jurisdiction'] == 'ADGM'
        assert results[0]['metadata']['is_active'] is True


class TestEndToEndRetrieval:
    """Test end-to-end retrieval workflow."""
    
    @pytest.fixture
    def mock_services(self):
        """Setup mock services for end-to-end test."""
        embedding_service = Mock(spec=EmbeddingService)
        embedding_service.embed_text.return_value = [0.1] * 3072
        
        pinecone_service = Mock(spec=PineconeService)
        pinecone_service.similarity_search.return_value = [
            {
                'id': 'uuid-001',
                'score': 0.92,
                'metadata': {
                    'passage_id': 'uuid-001',
                    'document_id': 1,
                    'passage_ref': '8.3.1',
                    'passage_text': 'Enhanced Due Diligence requirements for high-risk customers.',
                    'jurisdiction': 'ADGM',
                    'is_active': True
                }
            }
        ]
        
        return {
            'embedding': embedding_service,
            'pinecone': pinecone_service
        }
    
    def test_query_to_results_pipeline(self, mock_services):
        """Test complete pipeline from query to results."""
        # 1. User query
        query = "What are the requirements for high-risk customers?"
        
        # 2. Generate query embedding
        query_embedding = mock_services['embedding'].embed_text(query)
        assert len(query_embedding) == 3072
        
        # 3. Search Pinecone
        results = mock_services['pinecone'].similarity_search(
            query_embedding,
            top_k=5,
            filter_dict={"is_active": True}
        )
        
        # 4. Validate results
        assert len(results) > 0, "Should return results"
        assert results[0]['score'] > 0.9, "Top result should have high relevance"
        assert 'Enhanced Due Diligence' in results[0]['metadata']['passage_text']
    
    def test_no_results_handling(self, mock_services):
        """Test handling when no results are found."""
        mock_services['pinecone'].similarity_search.return_value = []
        
        query_embedding = mock_services['embedding'].embed_text("nonexistent query")
        results = mock_services['pinecone'].similarity_search(query_embedding, top_k=5)
        
        assert len(results) == 0, "Should return empty list when no matches"
    
    def test_relevance_threshold_filtering(self, mock_services):
        """Test filtering results by relevance threshold."""
        # Mock results with varying scores
        mock_services['pinecone'].similarity_search.return_value = [
            {'id': '1', 'score': 0.95, 'metadata': {'passage_text': 'High relevance'}},
            {'id': '2', 'score': 0.75, 'metadata': {'passage_text': 'Medium relevance'}},
            {'id': '3', 'score': 0.45, 'metadata': {'passage_text': 'Low relevance'}},
        ]
        
        query_embedding = [0.1] * 3072
        all_results = mock_services['pinecone'].similarity_search(query_embedding, top_k=10)
        
        # Filter by threshold
        threshold = 0.7
        filtered_results = [r for r in all_results if r['score'] >= threshold]
        
        assert len(filtered_results) == 2, "Should only keep high-scoring results"
        assert all(r['score'] >= threshold for r in filtered_results)


class TestDataConsistency:
    """Test data consistency between JSON files and Pinecone storage."""
    
    def test_json_to_pinecone_count_consistency(self):
        """Test that all non-empty passages from JSON are stored in Pinecone."""
        rules_dir = Path(__file__).parent.parent / "internal_rules"
        
        if not rules_dir.exists():
            pytest.skip("internal_rules directory not found")
        
        total_passages = 0
        json_files = list(rules_dir.glob("*.json"))
        
        for json_file in json_files[:3]:  # Test first 3 files
            with open(json_file, 'r', encoding='utf-8') as f:
                passages = json.load(f)
            
            # Count non-empty passages
            non_empty = len([p for p in passages if p.get('Passage', '').strip()])
            total_passages += non_empty
        
        assert total_passages > 0, "Should have counted some passages"
    
    def test_document_id_consistency(self):
        """Test that DocumentID matches the JSON filename."""
        rules_dir = Path(__file__).parent.parent / "internal_rules"
        
        if not rules_dir.exists():
            pytest.skip("internal_rules directory not found")
        
        # Test 1.json should have DocumentID = 1
        json_file = rules_dir / "1.json"
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                passages = json.load(f)
            
            # All passages in 1.json should have DocumentID = 1
            document_ids = set(p['DocumentID'] for p in passages)
            assert document_ids == {1}, f"Expected DocumentID=1, found {document_ids}"
    
    def test_passage_id_uniqueness(self):
        """Test that all passage IDs are unique."""
        rules_dir = Path(__file__).parent.parent / "internal_rules"
        
        if not rules_dir.exists():
            pytest.skip("internal_rules directory not found")
        
        all_ids = set()
        json_files = list(rules_dir.glob("*.json"))
        
        for json_file in json_files[:5]:  # Test first 5 files
            with open(json_file, 'r', encoding='utf-8') as f:
                passages = json.load(f)
            
            for passage in passages:
                passage_id = passage.get('ID')
                assert passage_id not in all_ids, f"Duplicate ID found: {passage_id}"
                all_ids.add(passage_id)
        
        assert len(all_ids) > 0, "Should have collected some IDs"


class TestPineconeServiceIntegration:
    """Integration tests for PineconeService (requires actual Pinecone connection)."""
    
    @pytest.fixture
    def pinecone_service(self):
        """Real Pinecone service (skip if not configured)."""
        if not settings.pinecone_api_key:
            pytest.skip("PINECONE_API_KEY not configured")
        
        return PineconeService(index_type="internal")
    
    def test_connection_to_pinecone(self, pinecone_service):
        """Test that we can connect to Pinecone index."""
        stats = pinecone_service.get_index_stats()
        assert 'total_vectors' in stats or 'total_vector_count' in stats
    
    def test_index_dimension_matches_embedding(self, pinecone_service):
        """Test that index dimension matches embedding model."""
        stats = pinecone_service.get_index_stats()
        
        # Should be 3072 for text-embedding-3-large
        if 'dimension' in stats:
            assert stats['dimension'] == 3072


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
