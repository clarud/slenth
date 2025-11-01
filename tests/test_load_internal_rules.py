"""
Test suite for the internal rules loading script.

Tests the complete workflow of:
1. Reading JSON files from internal_rules/
2. Parsing passages correctly
3. Generating embeddings
4. Upserting to Pinecone with proper metadata
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path setup
from scripts.load_internal_rules_pinecone import load_internal_rules


class TestLoadInternalRulesScript:
    """Test the load_internal_rules_pinecone.py script."""
    
    @pytest.fixture
    def sample_json_data(self):
        """Sample JSON data matching internal_rules structure."""
        return [
            {
                "ID": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
                "DocumentID": 1,
                "PassageID": "1.",
                "Passage": "INTRODUCTION"
            },
            {
                "ID": "e563ad09-df80-435c-a497-eeec420efbc4",
                "DocumentID": 1,
                "PassageID": "1.1",
                "Passage": "Jurisdiction"
            },
            {
                "ID": "1389d0fa-5346-4953-8d52-45d7fd96c5e8",
                "DocumentID": 1,
                "PassageID": "1.1.1.(1)",
                "Passage": "The AML Rulebook is made in recognition of the application of the Federal AML Legislation in the Abu Dhabi Global Market (\"ADGM\")."
            },
            {
                "ID": "8edbc54b-4d98-4417-a4b7-3531b6f80f8c",
                "DocumentID": 1,
                "PassageID": "1.1.2",
                "Passage": ""  # Empty passage should be skipped
            }
        ]
    
    @pytest.fixture
    def mock_services(self):
        """Mock both EmbeddingService and PineconeService."""
        with patch('scripts.load_internal_rules_pinecone.EmbeddingService') as MockEmbed, \
             patch('scripts.load_internal_rules_pinecone.PineconeService') as MockPinecone:
            
            # Setup embedding service mock
            embed_instance = MagicMock()
            embed_instance.embed_text.return_value = [0.1] * 3072
            MockEmbed.return_value = embed_instance
            
            # Setup Pinecone service mock
            pinecone_instance = MagicMock()
            pinecone_instance.upsert_vectors.return_value = True
            pinecone_instance.get_index_stats.return_value = {
                'total_vectors': 150,
                'total_vector_count': 150
            }
            MockPinecone.return_value = pinecone_instance
            
            yield {
                'embedding_class': MockEmbed,
                'embedding_instance': embed_instance,
                'pinecone_class': MockPinecone,
                'pinecone_instance': pinecone_instance
            }
    
    def test_skip_empty_passages(self, sample_json_data, mock_services):
        """Test that empty passages are skipped during processing."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            # Setup path mocking
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            # Run the loading function
            result = load_internal_rules()
            
            # Should call embed_text 3 times (skipping the empty passage)
            embed_calls = mock_services['embedding_instance'].embed_text.call_count
            assert embed_calls == 3, f"Expected 3 embed calls, got {embed_calls}"
    
    def test_correct_metadata_structure(self, sample_json_data, mock_services):
        """Test that metadata is structured correctly for Pinecone."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            load_internal_rules()
            
            # Check that upsert_vectors was called
            assert mock_services['pinecone_instance'].upsert_vectors.called
            
            # Get the call arguments
            call_args = mock_services['pinecone_instance'].upsert_vectors.call_args
            metadata_list = call_args[1]['metadata_list']  # keyword arg
            
            # Validate metadata structure
            for metadata in metadata_list:
                assert 'passage_id' in metadata
                assert 'document_id' in metadata
                assert 'passage_ref' in metadata
                assert 'passage_text' in metadata
                assert 'source_file' in metadata
                assert 'jurisdiction' in metadata
                assert 'is_active' in metadata
                
                # Check specific values
                assert metadata['is_active'] is True
                assert metadata['jurisdiction'] == 'ADGM'
                assert metadata['document_type'] == 'aml_rulebook'
    
    def test_vector_id_matches_passage_id(self, sample_json_data, mock_services):
        """Test that vector IDs match the passage UUIDs from JSON."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            load_internal_rules()
            
            # Get the upsert call arguments
            call_args = mock_services['pinecone_instance'].upsert_vectors.call_args
            ids = call_args[1]['ids']
            
            # IDs should match the UUIDs from JSON (excluding empty passage)
            expected_ids = [
                "bd35fb2d-4de6-48fb-ab3c-baead722854f",
                "e563ad09-df80-435c-a497-eeec420efbc4",
                "1389d0fa-5346-4953-8d52-45d7fd96c5e8"
            ]
            
            assert ids == expected_ids, f"Expected {expected_ids}, got {ids}"
    
    def test_embedding_text_includes_context(self, sample_json_data, mock_services):
        """Test that embedding text includes document context."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            load_internal_rules()
            
            # Check embed_text was called with context
            embed_calls = mock_services['embedding_instance'].embed_text.call_args_list
            
            for call in embed_calls:
                text = call[0][0]  # First positional argument
                # Should include "Document X - PassageID: Passage text"
                assert "Document" in text
                assert "-" in text
                assert ":" in text
    
    def test_batch_upsert_called_once(self, sample_json_data, mock_services):
        """Test that upsert_vectors is called once with all vectors."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            load_internal_rules()
            
            # Should call upsert_vectors exactly once
            assert mock_services['pinecone_instance'].upsert_vectors.call_count == 1
            
            # Should upsert 3 vectors (excluding empty passage)
            call_args = mock_services['pinecone_instance'].upsert_vectors.call_args
            vectors = call_args[1]['vectors']
            assert len(vectors) == 3
    
    def test_handles_missing_rules_directory(self, mock_services):
        """Test graceful handling when internal_rules/ doesn't exist."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath:
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = False
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            result = load_internal_rules()
            
            assert result is False, "Should return False when directory missing"
    
    def test_handles_no_json_files(self, mock_services):
        """Test graceful handling when no JSON files found."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath:
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = []  # No JSON files
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            result = load_internal_rules()
            
            assert result is False, "Should return False when no JSON files"
    
    def test_handles_malformed_json(self, mock_services):
        """Test error handling for malformed JSON."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data="{ invalid json")):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("bad.json")]
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            # Should not raise exception, but handle gracefully
            result = load_internal_rules()
            
            # Should still attempt to process, but may return False or True
            # depending on whether other files succeed
            assert isinstance(result, bool)
    
    def test_text_truncation_in_metadata(self, mock_services):
        """Test that long passage text is truncated in metadata."""
        long_passage_data = [
            {
                "ID": "test-long",
                "DocumentID": 1,
                "PassageID": "1.1",
                "Passage": "A" * 2000  # Very long text
            }
        ]
        
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(long_passage_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            load_internal_rules()
            
            # Check metadata
            call_args = mock_services['pinecone_instance'].upsert_vectors.call_args
            metadata_list = call_args[1]['metadata_list']
            
            for metadata in metadata_list:
                # passage_text should be truncated to 1000 chars
                assert len(metadata['passage_text']) <= 1000
                # But full_text_length should record the actual length
                assert metadata['full_text_length'] == 2000
    
    def test_multiple_files_processing(self, sample_json_data, mock_services):
        """Test processing multiple JSON files."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            # Simulate 3 JSON files
            mock_rules_dir.glob.return_value = [
                Path("1.json"),
                Path("2.json"),
                Path("3.json")
            ]
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            load_internal_rules()
            
            # Should call embed_text multiple times (3 files * 3 passages each)
            embed_calls = mock_services['embedding_instance'].embed_text.call_count
            assert embed_calls == 9, f"Expected 9 embed calls (3 files * 3 passages), got {embed_calls}"
    
    def test_pinecone_service_initialized_with_internal_index(self, mock_services):
        """Test that PineconeService is initialized with 'internal' index type."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data='[]')):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            load_internal_rules()
            
            # Check PineconeService was initialized with index_type="internal"
            mock_services['pinecone_class'].assert_called_once_with(index_type="internal")
    
    def test_success_return_value(self, sample_json_data, mock_services):
        """Test that function returns True on successful load."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            result = load_internal_rules()
            
            assert result is True, "Should return True on successful load"
    
    def test_upsert_failure_handling(self, sample_json_data, mock_services):
        """Test handling when Pinecone upsert fails."""
        # Make upsert return False (failure)
        mock_services['pinecone_instance'].upsert_vectors.return_value = False
        
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            MockPath.return_value.parent.parent.__truediv__.return_value = mock_rules_dir
            
            result = load_internal_rules()
            
            assert result is False, "Should return False when upsert fails"


class TestDataFormatValidation:
    """Test data format at each stage of the pipeline."""
    
    def test_json_format_validation(self):
        """Test that JSON files have correct structure."""
        sample = {
            "ID": "uuid-string",
            "DocumentID": 1,
            "PassageID": "1.1",
            "Passage": "Some text"
        }
        
        # Validate required fields
        required_fields = ["ID", "DocumentID", "PassageID", "Passage"]
        for field in required_fields:
            assert field in sample, f"Missing required field: {field}"
        
        # Validate types
        assert isinstance(sample["ID"], str)
        assert isinstance(sample["DocumentID"], int)
        assert isinstance(sample["PassageID"], str)
        assert isinstance(sample["Passage"], str)
    
    def test_embedding_vector_format(self):
        """Test embedding vector format."""
        vector = [0.1] * 3072
        
        assert isinstance(vector, list)
        assert len(vector) == 3072
        assert all(isinstance(x, (int, float)) for x in vector)
    
    def test_metadata_format_for_pinecone(self):
        """Test metadata format expected by Pinecone."""
        metadata = {
            "passage_id": "uuid-123",
            "document_id": 1,
            "passage_ref": "1.1.1",
            "passage_text": "Sample text",
            "full_text_length": 100,
            "source_file": "1.json",
            "is_active": True,
            "jurisdiction": "ADGM",
            "document_type": "aml_rulebook",
            "ingestion_date": "2024-01-01T00:00:00"
        }
        
        # All values should be primitive types (Pinecone requirement)
        for key, value in metadata.items():
            assert isinstance(value, (str, int, float, bool)), \
                f"Metadata value for {key} must be primitive type, got {type(value)}"
    
    def test_pinecone_upsert_format(self):
        """Test the format expected by Pinecone upsert."""
        vectors = [[0.1] * 3072, [0.2] * 3072]
        ids = ["uuid-1", "uuid-2"]
        metadata_list = [
            {"passage_id": "uuid-1", "document_id": 1},
            {"passage_id": "uuid-2", "document_id": 1}
        ]
        
        # Validate format
        assert len(vectors) == len(ids) == len(metadata_list)
        assert all(len(v) == 3072 for v in vectors)
        assert all(isinstance(id, str) for id in ids)
        assert all(isinstance(m, dict) for m in metadata_list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
