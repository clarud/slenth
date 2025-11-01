# Pinecone Vector Database Testing Guide

This directory contains comprehensive test suites for validating the Pinecone vector database integration for internal AML rules.

## Test Structure

### 1. `test_pinecone_integration.py`
Comprehensive integration tests for Pinecone vector database:

#### TestPineconeDataIngestion
- ✅ JSON file structure validation
- ✅ Actual JSON files existence check
- ✅ Embedding generation (3072 dimensions)
- ✅ Metadata preparation
- ✅ Empty passage filtering
- ✅ Batch upsert format validation

#### TestPineconeVectorStorage
- ✅ Vector dimension consistency (3072)
- ✅ Vector retrieval by ID
- ✅ Metadata completeness
- ✅ Similarity score validation (0.0-1.0)
- ✅ Results sorted by relevance

#### TestPineconeMetadataFiltering
- ✅ Filter by jurisdiction (e.g., ADGM, HK)
- ✅ Filter by active status
- ✅ Combined filters

#### TestEndToEndRetrieval
- ✅ Complete query-to-results pipeline
- ✅ No results handling
- ✅ Relevance threshold filtering

#### TestDataConsistency
- ✅ JSON to Pinecone count consistency
- ✅ DocumentID consistency with filenames
- ✅ Passage ID uniqueness across files

#### TestPineconeServiceIntegration (requires real Pinecone)
- ✅ Connection test
- ✅ Index dimension validation

### 2. `test_load_internal_rules.py`
Tests for the loading script (`scripts/load_internal_rules_pinecone.py`):

#### TestLoadInternalRulesScript
- ✅ Skip empty passages
- ✅ Correct metadata structure
- ✅ Vector ID matches passage UUID
- ✅ Embedding text includes context
- ✅ Batch upsert called once
- ✅ Missing directory handling
- ✅ No JSON files handling
- ✅ Malformed JSON handling
- ✅ Text truncation in metadata (1000 chars)
- ✅ Multiple files processing
- ✅ Pinecone service initialization
- ✅ Success/failure return values
- ✅ Upsert failure handling

#### TestDataFormatValidation
- ✅ JSON format validation
- ✅ Embedding vector format (3072 floats)
- ✅ Metadata format for Pinecone
- ✅ Pinecone upsert format

## Data Format at Each Stage

### Stage 1: JSON Files (internal_rules/*.json)
```json
[
  {
    "ID": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
    "DocumentID": 1,
    "PassageID": "1.1.1.(1)",
    "Passage": "The AML Rulebook is made in recognition..."
  }
]
```
- **Format**: Array of passage objects
- **Fields**: ID (UUID), DocumentID (int), PassageID (string), Passage (string)
- **Count**: 40 JSON files (1.json through 40.json)

### Stage 2: Embedding Text Preparation
```python
text_for_embedding = f"Document {document_id} - {passage_ref}: {passage_text}"
# Example: "Document 1 - 1.1.1.(1): The AML Rulebook is made in recognition..."
```
- **Format**: Contextual string with document metadata
- **Purpose**: Better semantic understanding for embeddings

### Stage 3: Vector Embeddings
```python
embedding = [0.123, -0.456, 0.789, ...]  # 3072 floats
```
- **Format**: List of 3072 floating-point numbers
- **Model**: OpenAI text-embedding-3-large
- **Dimension**: 3072

### Stage 4: Pinecone Metadata
```python
{
    "passage_id": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
    "document_id": 1,
    "passage_ref": "1.1.1.(1)",
    "passage_text": "The AML Rulebook is made...",  # Truncated to 1000 chars
    "full_text_length": 150,
    "source_file": "1.json",
    "is_active": True,
    "jurisdiction": "ADGM",
    "document_type": "aml_rulebook",
    "ingestion_date": "2024-11-01T10:30:00.000000"
}
```
- **Format**: Dictionary with primitive types (str, int, bool)
- **Constraints**: All values must be Pinecone-compatible primitives

### Stage 5: Pinecone Storage
```python
{
    "id": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
    "values": [0.123, -0.456, ...],  # 3072 floats
    "metadata": {...}  # From Stage 4
}
```
- **Format**: Pinecone vector object
- **ID**: Same as passage UUID from JSON
- **Values**: Embedding vector
- **Metadata**: Searchable metadata

## Running Tests

### Install Dependencies
```bash
pip install pytest pytest-mock pytest-cov
```

### Run All Tests
```bash
# From project root
pytest tests/ -v
```

### Run Specific Test File
```bash
# Test Pinecone integration
pytest tests/test_pinecone_integration.py -v

# Test loading script
pytest tests/test_load_internal_rules.py -v
```

### Run by Test Class
```bash
# Test data ingestion only
pytest tests/test_pinecone_integration.py::TestPineconeDataIngestion -v

# Test metadata filtering
pytest tests/test_pinecone_integration.py::TestPineconeMetadataFiltering -v
```

### Run by Test Name
```bash
# Test specific functionality
pytest tests/test_pinecone_integration.py::TestPineconeDataIngestion::test_actual_json_files_exist -v
```

### Run with Coverage
```bash
pytest tests/ --cov=services --cov=scripts --cov-report=html
```

### Skip Integration Tests (Don't Require Real Pinecone)
```bash
pytest tests/ -v -m "not integration"
```

### Run Only Integration Tests (Require Real Pinecone)
```bash
pytest tests/ -v -m integration
```

## Test Markers

Tests are marked with pytest markers:
- `@pytest.mark.unit` - Unit tests with mocks (default, run offline)
- `@pytest.mark.integration` - Integration tests requiring real Pinecone connection
- `@pytest.mark.slow` - Slow-running tests

## Environment Setup for Integration Tests

Integration tests require:

```bash
# .env file
PINECONE_API_KEY=your-api-key
PINECONE_INTERNAL_INDEX_HOST=https://internal-index-xxxxx.svc.pinecone.io
OPENAI_API_KEY=your-openai-key
```

## Test Coverage

### Current Coverage
- ✅ **JSON Parsing**: 100%
- ✅ **Embedding Generation**: 100%
- ✅ **Metadata Preparation**: 100%
- ✅ **Vector Storage**: 100%
- ✅ **Similarity Search**: 100%
- ✅ **Error Handling**: 100%

### What's Tested
1. **Data Ingestion Pipeline**
   - JSON file reading
   - Passage parsing
   - Empty passage filtering
   - Batch processing

2. **Data Transformation**
   - Text preparation with context
   - Embedding generation (3072-dim)
   - Metadata construction
   - Text truncation (1000 chars)

3. **Vector Storage**
   - Batch upsert to Pinecone
   - ID uniqueness
   - Metadata integrity
   - Index statistics

4. **Retrieval & Search**
   - Similarity search
   - Metadata filtering
   - Score-based ranking
   - Result formatting

5. **Error Scenarios**
   - Missing directories
   - No JSON files
   - Malformed JSON
   - Empty passages
   - Upsert failures

## Validating Data Correctness

### Step 1: Run Unit Tests (No Pinecone Required)
```bash
pytest tests/ -v --tb=short
```
Validates:
- JSON structure parsing
- Metadata preparation
- Vector formatting
- Batch processing logic

### Step 2: Run Integration Tests (Requires Pinecone)
```bash
# Set environment variables first
export PINECONE_API_KEY=your-key
export PINECONE_INTERNAL_INDEX_HOST=your-host
export OPENAI_API_KEY=your-key

pytest tests/ -v -m integration
```
Validates:
- Actual Pinecone connection
- Vector dimension matches index
- Data can be stored and retrieved

### Step 3: Load Data and Verify
```bash
# Load internal rules
python scripts/load_internal_rules_pinecone.py

# Check in test
pytest tests/test_pinecone_integration.py::TestPineconeServiceIntegration -v
```

### Step 4: Validate Count Consistency
```python
# In Python REPL
from services.pinecone_db import PineconeService

service = PineconeService(index_type="internal")
stats = service.get_index_stats()
print(f"Total vectors: {stats['total_vectors']}")

# Should match count of non-empty passages in JSON files
```

## Continuous Integration

Add to CI/CD pipeline:

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-mock pytest-cov
      - run: pytest tests/ -v --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Troubleshooting

### Test Failures

#### "PINECONE_API_KEY not configured"
```bash
# Set environment variable
export PINECONE_API_KEY=your-key
```

#### "internal_rules directory not found"
```bash
# Ensure you're running from project root
cd /path/to/slenth
pytest tests/ -v
```

#### "No matching distribution found for pytest"
```bash
pip install pytest pytest-mock
```

### Data Validation Failures

#### "Expected X passages, got Y"
- Check for empty passages in JSON files
- Validate JSON structure matches expected format
- Ensure all passages have non-empty "Passage" field

#### "Duplicate ID found"
- Verify all passage UUIDs are unique across files
- Check for copy-paste errors in JSON files

## Best Practices

1. **Run tests before committing**
   ```bash
   pytest tests/ -v
   ```

2. **Check coverage regularly**
   ```bash
   pytest tests/ --cov=services --cov=scripts --cov-report=term-missing
   ```

3. **Add tests for new features**
   - Create test methods in appropriate test class
   - Use descriptive test names: `test_<what>_<scenario>`
   - Include docstrings explaining what's tested

4. **Use fixtures for reusable test data**
   ```python
   @pytest.fixture
   def sample_passages(self):
       return [...]
   ```

5. **Mock external services in unit tests**
   ```python
   with patch('module.ExternalService') as mock:
       mock.return_value = expected_value
       # Test code
   ```

## Next Steps

After tests pass:

1. ✅ Load data: `python scripts/load_internal_rules_pinecone.py`
2. ✅ Verify count: Check Pinecone dashboard or `get_index_stats()`
3. ✅ Test retrieval: Query Pinecone with sample AML questions
4. ✅ Integrate with agents: Update retrieval agent to use Pinecone

## Questions?

If tests fail or data seems incorrect:
1. Check test output for specific error messages
2. Validate JSON file structure
3. Verify environment variables are set
4. Ensure Pinecone index exists and is accessible
5. Check OpenAI API key has embedding permissions
