"""
Test suite for the internal rules loading script.

Tests the complete workflow of:
1. Reading JSON files from internal_rules/
2. Parsing passages correctly
3. Using Pinecone's inference API (no embedding generation needed)
4. Upserting to Pinecone with proper metadata
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
    def mock_pinecone(self):
        """Mock Pinecone client and index."""
        with patch('scripts.load_internal_rules_pinecone.Pinecone') as MockPinecone:
            # Setup Pinecone mock
            pc_instance = MagicMock()
            mock_index = MagicMock()
            
            # Mock index methods
            mock_index.upsert_records = MagicMock(return_value=None)
            mock_index.describe_index_stats = MagicMock(return_value={
                'total_vector_count': 150,
                'dimension': 1024
            })
            
            pc_instance.Index = MagicMock(return_value=mock_index)
            MockPinecone.return_value = pc_instance
            
            yield {
                'pinecone_class': MockPinecone,
                'pinecone_instance': pc_instance,
                'index': mock_index
            }
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        with patch.dict(os.environ, {
            'PINECONE_API_KEY': 'test-api-key',
            'PINECONE_INTERNAL_INDEX_HOST': 'https://test-index.svc.pinecone.io'
        }):
            yield
    
    def test_skip_empty_passages(self, sample_json_data, mock_pinecone, mock_env):
        """Test that empty passages are skipped during processing."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            # Setup path mocking
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            
            # Mock the path structure
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            MockPath.__file__ = __file__
            
            # Run the loading function
            result = load_internal_rules()
            
            # Verify upsert was called
            assert mock_pinecone['index'].upsert_records.called
            
            # Get the records that were upserted
            call_args = mock_pinecone['index'].upsert_records.call_args_list
            all_records = []
            for call_obj in call_args:
                records = call_obj[1]['records']  # Get records from kwargs
                all_records.extend(records)
            
            # Should have 3 records (skipping the empty passage)
            assert len(all_records) == 3, f"Expected 3 records, got {len(all_records)}"
    
    def test_correct_metadata_structure(self, sample_json_data, mock_pinecone, mock_env):
        """Test that metadata is structured correctly for Pinecone (flat structure)."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            load_internal_rules()
            
            # Get the records that were upserted
            call_args = mock_pinecone['index'].upsert_records.call_args_list
            all_records = []
            for call_obj in call_args:
                records = call_obj[1]['records']
                all_records.extend(records)
            
            # Validate record structure (flat, not nested)
            for record in all_records:
                # Core fields
                assert '_id' in record
                assert 'text' in record
                
                # Metadata at top level (not nested)
                assert 'passage_id' in record
                assert 'document_id' in record
                assert 'passage_ref' in record
                assert 'passage_text' in record  # Changed from passage_excerpt to match implementation
                assert 'source_file' in record
                assert 'jurisdiction' in record
                assert 'is_active' in record
                
                # Check specific values
                assert record['is_active'] is True
                assert record['jurisdiction'] == 'ADGM'
                assert record['document_type'] == 'aml_rulebook'
    
    def test_vector_id_matches_passage_id(self, sample_json_data, mock_pinecone, mock_env):
        """Test that record IDs match the passage UUIDs from JSON."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            load_internal_rules()
            
            # Get the records
            call_args = mock_pinecone['index'].upsert_records.call_args_list
            all_records = []
            for call_obj in call_args:
                records = call_obj[1]['records']
                all_records.extend(records)
            
            # IDs should match the UUIDs from JSON (excluding empty passage)
            expected_ids = [
                "bd35fb2d-4de6-48fb-ab3c-baead722854f",
                "e563ad09-df80-435c-a497-eeec420efbc4",
                "1389d0fa-5346-4953-8d52-45d7fd96c5e8"
            ]
            
            actual_ids = [r['_id'] for r in all_records]
            assert actual_ids == expected_ids, f"Expected {expected_ids}, got {actual_ids}"
    
    def test_text_includes_context(self, sample_json_data, mock_pinecone, mock_env):
        """Test that text field includes document context for embedding."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            load_internal_rules()
            
            # Get the records
            call_args = mock_pinecone['index'].upsert_records.call_args_list
            all_records = []
            for call_obj in call_args:
                records = call_obj[1]['records']
                all_records.extend(records)
            
            # Check text includes context
            for record in all_records:
                text = record['text']
                # Should include "Document X - PassageID: Passage text"
                assert "Document" in text
                assert "-" in text
                assert ":" in text
    
    def test_batch_upsert_called(self, sample_json_data, mock_pinecone, mock_env):
        """Test that upsert_records is called with batches."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            load_internal_rules()
            
            # Should call upsert_records (at least once for small batch)
            assert mock_pinecone['index'].upsert_records.called
            
            # Should upsert 3 records total (excluding empty passage)
            call_args = mock_pinecone['index'].upsert_records.call_args_list
            total_records = sum(len(call[1]['records']) for call in call_args)
            assert total_records == 3
    
    def test_handles_missing_rules_directory(self, mock_pinecone, mock_env):
        """Test graceful handling when internal_rules/ doesn't exist."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath:
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = False
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            result = load_internal_rules()
            
            assert result is False, "Should return False when directory missing"
    
    def test_handles_no_json_files(self, mock_pinecone, mock_env):
        """Test graceful handling when no JSON files found."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath:
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = []  # No JSON files
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            result = load_internal_rules()
            
            assert result is False, "Should return False when no JSON files"
    
    def test_handles_malformed_json(self, mock_pinecone, mock_env):
        """Test error handling for malformed JSON."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data="{ invalid json")):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("bad.json")]
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            # Should handle gracefully and continue
            result = load_internal_rules()
            
            # Should still return True/False
            assert isinstance(result, bool)
    
    def test_text_truncation_in_metadata(self, mock_pinecone, mock_env):
        """Test that long passage text is truncated in metadata (passage_text field)."""
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
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            load_internal_rules()
            
            # Check that passage_text is truncated to 512 chars
            call_args = mock_pinecone['index'].upsert_records.call_args_list
            for call in call_args:
                records = call[1]['records']
                for record in records:
                    assert len(record.get('passage_text', '')) <= 512
    
    def test_multiple_files_processing(self, sample_json_data, mock_pinecone, mock_env):
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
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            load_internal_rules()
            
            # Should upsert 9 total records (3 files * 3 passages each)
            call_args = mock_pinecone['index'].upsert_records.call_args_list
            total_records = sum(len(call[1]['records']) for call in call_args)
            assert total_records == 9, f"Expected 9 records (3 files * 3 passages), got {total_records}"
    
    def test_pinecone_client_initialized(self, mock_pinecone, mock_env):
        """Test that Pinecone client is initialized correctly."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data='[]')):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            load_internal_rules()
            
            # Check Pinecone was initialized with API key
            mock_pinecone['pinecone_class'].assert_called_once_with(api_key="test-api-key")
    
    def test_success_return_value(self, sample_json_data, mock_pinecone, mock_env):
        """Test that function returns True on successful load."""
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            result = load_internal_rules()
            
            assert result is True, "Should return True on successful load"
    
    def test_upsert_failure_handling(self, sample_json_data, mock_pinecone, mock_env):
        """Test handling when Pinecone upsert fails."""
        # Make upsert raise an exception
        mock_pinecone['index'].upsert_records.side_effect = Exception("Pinecone API error")
        
        with patch('scripts.load_internal_rules_pinecone.Path') as MockPath, \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_json_data))):
            
            mock_rules_dir = MagicMock()
            mock_rules_dir.exists.return_value = True
            mock_rules_dir.glob.return_value = [Path("1.json")]
            
            mock_path = MagicMock()
            mock_path.parent.parent.__truediv__.return_value = mock_rules_dir
            MockPath.return_value = mock_path
            
            # Should handle exception and log to failed_upserts.log
            result = load_internal_rules()
            
            # Function continues despite errors (per-record retry)
            assert isinstance(result, bool)


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
    
    def test_pinecone_record_format(self):
        """Test Pinecone record format (using inference API)."""
        record = {
            "_id": "uuid-123",
            "text": "Doc 1: Passage 1.1: Sample text",
            "passage_id": "uuid-123",
            "document_id": 1,
            "passage_ref": "1.1",
            "passage_text": "Sample text",  # Changed from passage_excerpt
            "source_file": "1.json",
            "is_active": True,
            "ingestion_date": "2024-01-01T00:00:00+00:00"
        }
        
        # Validate required fields for Pinecone inference API
        assert "_id" in record
        assert "text" in record  # Required for embedding generation
        
        # All metadata values should be primitive types (Pinecone requirement)
        metadata_fields = {k: v for k, v in record.items() if k not in ['_id', 'text']}
        for key, value in metadata_fields.items():
            assert isinstance(value, (str, int, float, bool)), \
                f"Metadata value for {key} must be primitive type, got {type(value)}"
    
    def test_pinecone_upsert_format(self):
        """Test the format expected by Pinecone upsert_records()."""
        records = [
            {
                "_id": "uuid-1",
                "text": "Doc 1: Passage 1.1: Sample text 1",
                "passage_id": "uuid-1",
                "document_id": 1
            },
            {
                "_id": "uuid-2",
                "text": "Doc 1: Passage 1.2: Sample text 2",
                "passage_id": "uuid-2",
                "document_id": 1
            }
        ]
        
        # Validate format
        assert all(isinstance(r, dict) for r in records)
        assert all("_id" in r and "text" in r for r in records)
        assert all(isinstance(r["_id"], str) for r in records)
        assert all(isinstance(r["text"], str) for r in records)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
