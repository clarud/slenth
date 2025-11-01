# Complete Ingestion Workflow Guide
## Internal Rules → Pinecone Vector Database

---

## 🎯 Overview

This guide explains the complete workflow for ingesting internal AML compliance rules from JSON files into Pinecone vector database for semantic search and retrieval.

---

## 📊 Data Flow Pipeline

```
internal_rules/*.json
    ↓
Parse JSON Array of Passages
    ↓
Filter Empty Passages
    ↓
Prepare Contextual Text
    ↓
Generate OpenAI Embeddings (3072-dim)
    ↓
Build Metadata
    ↓
Batch Collection
    ↓
Pinecone Upsert
    ↓
Vector Storage (Indexed & Searchable)
```

---

## 📁 Source Data Format

**Location**: `internal_rules/1.json` through `internal_rules/40.json`

**Structure**: Array of passage objects
```json
[
    {
        "ID": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
        "DocumentID": 1,
        "PassageID": "1.1.1.(1)",
        "Passage": "The AML Rulebook is made in recognition..."
    },
    {
        "ID": "e563ad09-df80-435c-a497-eeec420efbc4",
        "DocumentID": 1,
        "PassageID": "1.2",
        "Passage": "Customer Due Diligence must be performed..."
    }
]
```

**Key Fields**:
- `ID`: UUID for the passage (used as Pinecone vector ID)
- `DocumentID`: Integer matching filename (1.json → DocumentID: 1)
- `PassageID`: Hierarchical reference like "1.1.1.(1)"
- `Passage`: The actual rule text (can be empty)

---

## 🔄 Transformation Stages

### Stage 1: JSON Parsing
The script reads each JSON file and parses it into a Python list of dictionaries.

```python
with open('internal_rules/1.json', 'r') as f:
    passages = json.load(f)  # Returns: List[Dict]
```

### Stage 2: Empty Passage Filtering
Passages with empty text are automatically skipped:

```python
passage_text = passage_obj.get('Passage', '').strip()
if not passage_text:
    continue  # Skip this passage
```

**Why?** Empty passages have no semantic meaning and would pollute search results.

### Stage 3: Text Preparation
Contextual information is added to improve embedding quality:

```python
text_for_embedding = f"Document {document_id} - {passage_ref}: {passage_text}"
```

**Example**:
```
"Document 1 - 1.1.1.(1): The AML Rulebook is made in recognition of the application..."
```

**Why add context?**
- Document ID helps group related passages
- Passage reference helps identify hierarchical structure
- Improves semantic search accuracy

### Stage 4: Embedding Generation
OpenAI API converts text to 3072-dimensional vector:

```python
embedding = embedding_service.embed_text(text_for_embedding)
# Returns: [0.0123, -0.0234, 0.0345, ..., -0.0456]  # 3072 floats
```

**Model**: `text-embedding-3-large`  
**Dimension**: 3072  
**Output**: List of normalized floats in range [-1, 1]

### Stage 5: Metadata Construction
Rich metadata is attached for filtering and retrieval:

```python
metadata = {
    "passage_id": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
    "document_id": 1,
    "passage_ref": "1.1.1.(1)",
    "passage_text": passage_text[:1000],  # Truncated to 1000 chars
    "full_text_length": len(passage_text),
    "source_file": "1.json",
    "is_active": True,
    "jurisdiction": "ADGM",
    "document_type": "aml_rulebook",
    "ingestion_date": "2024-11-01T10:30:00.000000"
}
```

**Truncation**: Pinecone has metadata size limits, so text is truncated to 1000 characters. Full length is tracked in `full_text_length`.

### Stage 6: Batch Collection
Vectors are collected into batches for efficient upserting:

```python
vectors_to_upsert.append(embedding)
metadata_to_upsert.append(metadata)
ids_to_upsert.append(passage_id)
```

All passages from all files are collected into single batches.

### Stage 7: Pinecone Upsert
All vectors are upserted in one operation:

```python
success = pinecone_service.upsert_vectors(
    vectors=vectors_to_upsert,      # List of 3072-dim vectors
    metadata_list=metadata_to_upsert,  # List of metadata dicts
    ids=ids_to_upsert               # List of UUIDs
)
```

**Batch Size**: PineconeService automatically batches in groups of 100 for optimal performance.

### Stage 8: Final Storage
Data is stored in Pinecone with structure:

```python
{
    "id": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
    "values": [0.0123, -0.0234, ...],  # 3072 floats
    "metadata": {
        "passage_id": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
        "document_id": 1,
        "passage_ref": "1.1.1.(1)",
        "passage_text": "The AML Rulebook...",
        "full_text_length": 150,
        "source_file": "1.json",
        "is_active": True,
        "jurisdiction": "ADGM",
        "document_type": "aml_rulebook",
        "ingestion_date": "2024-11-01T10:30:00.000000"
    }
}
```

---

## 🚀 Running the Ingestion

### Prerequisites

1. **Environment Variables**:
```bash
export PINECONE_API_KEY="your-pinecone-api-key"
export PINECONE_INTERNAL_INDEX_HOST="https://your-index-abc123.svc.pinecone.io"
export OPENAI_API_KEY="your-openai-api-key"
```

2. **Dependencies**:
```bash
pip install -r requirements.txt
```

3. **JSON Files**: Ensure `internal_rules/*.json` files exist

### Run the Script

```bash
# From project root
python scripts/load_internal_rules_pinecone.py
```

### Expected Output

```
🚀 Loading internal rules to Pinecone vector database...
📁 Found 40 rule files in /path/to/internal_rules
🔧 Initializing services...
📦 Using Pinecone internal index: https://your-index-abc123.svc.pinecone.io
📄 Processing: 1.json
   ✅ Prepared 150 passages from 1.json
📄 Processing: 2.json
   ✅ Prepared 120 passages from 2.json
...
📄 Processing: 40.json
   ✅ Prepared 85 passages from 40.json
🚀 Upserting 3500 vectors to Pinecone...
💾 Successfully upserted 3500 rules to Pinecone
======================================================================
📊 SUMMARY
======================================================================
✅ Loaded to Pinecone: 3500 rules
📦 Total in Pinecone index: 3500 vectors
======================================================================
🎉 Internal rules loading complete!
   Pinecone: ✅
======================================================================
```

### Monitoring Progress

The script logs:
- **Each file processed**: Shows filename
- **Passages per file**: Count of non-empty passages
- **Batch upsert**: Single operation for all vectors
- **Final stats**: Total vectors in Pinecone index

---

## 🧪 Running Tests

### 1. Install Test Dependencies

```bash
pip install pytest pytest-mock pytest-cov
```

### 2. Run All Tests

```bash
# From project root
pytest tests/ -v
```

### 3. Run Specific Test Suites

**Test Pinecone Integration** (requires mocking):
```bash
pytest tests/test_pinecone_integration.py -v
```

**Test Loading Script**:
```bash
pytest tests/test_load_internal_rules.py -v
```

### 4. Run Unit Tests Only (No Pinecone Required)

```bash
pytest tests/ -v -m "unit"
```

### 5. Run with Coverage

```bash
pytest tests/ --cov=services --cov=scripts --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```

### 6. Quick Test Script

Use the provided test runner:
```bash
chmod +x run_tests.sh
./run_tests.sh
```

### Expected Test Output

```
================================================
Internal Rules Testing - Quick Start
================================================

Running unit tests...

tests/test_pinecone_integration.py::TestPineconeDataIngestion::test_json_file_structure_validation PASSED
tests/test_pinecone_integration.py::TestPineconeDataIngestion::test_actual_json_files_exist PASSED
tests/test_pinecone_integration.py::TestPineconeDataIngestion::test_embedding_generation PASSED
...
tests/test_load_internal_rules.py::TestLoadInternalRulesScript::test_skip_empty_passages PASSED
tests/test_load_internal_rules.py::TestDataFormatValidation::test_json_format PASSED
...

================================================
20 passed in 5.2s
================================================
```

---

## 🔍 Verifying the Data

### Method 1: Check Index Stats

```python
from services.pinecone_db import PineconeService

pinecone = PineconeService(index_type="internal")
stats = pinecone.get_index_stats()
print(f"Total vectors: {stats['total_vectors']}")
```

### Method 2: Test Similarity Search

```python
from services.pinecone_db import PineconeService
from services.embeddings import EmbeddingService

# Initialize services
embedding_service = EmbeddingService()
pinecone_service = PineconeService(index_type="internal")

# Create query embedding
query = "What are the customer due diligence requirements?"
query_embedding = embedding_service.embed_text(query)

# Search
results = pinecone_service.similarity_search(
    query_vector=query_embedding,
    top_k=5,
    filter_dict={"is_active": True}
)

# Display results
for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Ref: {result['metadata']['passage_ref']}")
    print(f"Text: {result['metadata']['passage_text'][:100]}...")
    print("-" * 80)
```

### Method 3: Run Integration Tests

```bash
pytest tests/test_pinecone_integration.py::TestPineconeServiceIntegration -v
```

**Note**: This requires real Pinecone credentials and data to be loaded.

---

## 📈 Performance Metrics

### Expected Processing Times

| Operation | Time | Notes |
|-----------|------|-------|
| Read 1 JSON file | 10-50ms | Depends on file size |
| Generate 1 embedding | 50-200ms | OpenAI API latency |
| Upsert 100 vectors | 100-500ms | Pinecone batch operation |
| Total for 40 files (~3500 passages) | 3-10 minutes | Depends on network |

### Optimization Tips

1. **Parallel Processing**: Process multiple files concurrently
2. **Batch Size**: Increase to 200-500 for faster upserts
3. **Caching**: Cache embeddings if reprocessing same data
4. **Error Handling**: Continue on single file failures

---

## ❌ Troubleshooting

### Issue: "Rules directory not found"

**Cause**: `internal_rules/` directory doesn't exist or script run from wrong location

**Solution**:
```bash
# Ensure you're in project root
cd /path/to/slenth

# Check directory exists
ls -la internal_rules/

# Run script
python scripts/load_internal_rules_pinecone.py
```

### Issue: "No JSON files found"

**Cause**: `internal_rules/` is empty

**Solution**:
```bash
# Check files exist
ls internal_rules/*.json

# Should see: 1.json, 2.json, ..., 40.json
```

### Issue: "OpenAI API error"

**Cause**: Invalid API key or quota exceeded

**Solution**:
```bash
# Check API key is set
echo $OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Issue: "Pinecone connection error"

**Cause**: Invalid API key or index host

**Solution**:
```bash
# Check environment variables
echo $PINECONE_API_KEY
echo $PINECONE_INTERNAL_INDEX_HOST

# Verify index host format
# Should be: https://your-index-abc123.svc.pinecone.io
```

### Issue: "Empty passages logged"

**Cause**: Some passages in JSON have empty `Passage` field

**Solution**: This is expected behavior. Empty passages are automatically skipped. No action needed.

### Issue: "Dimension mismatch"

**Cause**: Pinecone index dimension doesn't match embedding dimension (3072)

**Solution**:
```python
# Check index dimension
from services.pinecone_db import PineconeService
pinecone = PineconeService(index_type="internal")
stats = pinecone.get_index_stats()
print(f"Index dimension: {stats.get('dimension')}")

# Should be: 3072 for text-embedding-3-large
```

---

## 🔄 Re-running Ingestion

### Upsert Behavior

Pinecone **upserts** vectors, meaning:
- If vector ID exists → **Update** (overwrite)
- If vector ID is new → **Insert** (add)

### Safe to Re-run

You can safely re-run the script multiple times:
```bash
python scripts/load_internal_rules_pinecone.py
```

The script will:
1. Read all JSON files again
2. Generate embeddings again
3. Upsert to Pinecone (overwrite existing vectors with same ID)

### Incremental Updates

To update only specific files:
```python
# Modify script to process specific files
json_files = [rules_dir / "1.json", rules_dir / "2.json"]
```

---

## 📚 Related Documentation

- **Data Formats**: `DATA_FORMAT_REFERENCE.md` - Quick reference for all data formats
- **Testing Guide**: `tests/README_TESTING.md` - Comprehensive testing documentation
- **Workflow Details**: `INTERNAL_RULES_WORKFLOW.md` - Detailed workflow explanation
- **Implementation Summary**: `TESTING_IMPLEMENTATION_SUMMARY.md` - What's been built

---

## 🎓 Key Concepts

### Why Embeddings?

Embeddings convert text to vectors that capture semantic meaning. Similar texts have similar vectors, enabling semantic search:

```
"Customer due diligence" → [0.1, -0.2, 0.3, ...]
"KYC requirements"       → [0.1, -0.2, 0.3, ...]  ← Similar vector!
"Transaction monitoring" → [0.8, 0.5, -0.1, ...]  ← Different vector
```

### Why Pinecone?

Pinecone is optimized for:
- **Fast similarity search**: Find nearest neighbors in milliseconds
- **Scale**: Millions of vectors with low latency
- **Filtering**: Combine semantic search with metadata filters
- **Managed service**: No infrastructure management

### Why Metadata?

Metadata enables:
- **Filtering**: "Find rules for ADGM jurisdiction only"
- **Context**: Return passage reference for citations
- **Debugging**: Track source file and ingestion date
- **Business logic**: Filter by `is_active` status

---

## ✅ Success Criteria

After successful ingestion, you should have:

1. ✅ All non-empty passages from `internal_rules/*.json` in Pinecone
2. ✅ Vector count matches total non-empty passages
3. ✅ Metadata attached to every vector
4. ✅ Similarity search returns relevant results
5. ✅ All tests passing

**Quick Check**:
```bash
# Run tests
pytest tests/ -v

# Should see: "X passed" (all green)
```

---

## 🚦 Next Steps

After ingestion is complete:

1. **Test Retrieval Agent**:
```bash
pytest tests/test_retrieval_agent.py -v
```

2. **Test End-to-End Workflow**:
```bash
# Submit a test transaction through API
# Verify internal rules are retrieved correctly
```

3. **Monitor Performance**:
```bash
# Check Pinecone dashboard for query latency
# Optimize filters if needed
```

4. **Production Readiness**:
   - Add monitoring and alerting
   - Set up scheduled re-ingestion (if rules update)
   - Configure backup and disaster recovery

---

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review test failures for specific error messages
3. Check Pinecone and OpenAI service status
4. Verify all environment variables are set correctly

---

**Last Updated**: November 1, 2025  
**Version**: 1.0
