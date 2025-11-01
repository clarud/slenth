# Internal Rules Ingestion Workflow

## Complete Data Flow: JSON → Pinecone Vector Database

This document explains the complete workflow for ingesting internal AML rules from JSON files into the Pinecone vector database.

---

## Overview

**Source**: `internal_rules/*.json` (40 JSON files containing AML rulebook passages)  
**Destination**: Pinecone vector database (internal index)  
**Purpose**: Enable semantic similarity search for rule retrieval during transaction analysis

---

## Data Format at Each Stage

### Stage 1: Source JSON Files
**Location**: `internal_rules/1.json` through `internal_rules/40.json`

**Structure**:
```json
[
    {
        "ID": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
        "DocumentID": 1,
        "PassageID": "1.1.1.(1)",
        "Passage": "The AML Rulebook is made in recognition of the application of the Federal AML Legislation in the Abu Dhabi Global Market (\"ADGM\")."
    },
    {
        "ID": "e563ad09-df80-435c-a497-eeec420efbc4",
        "DocumentID": 1,
        "PassageID": "1.1.1.(2)",
        "Passage": "Nothing in the AML Rulebook affects the operation of Federal AML Legislation."
    }
]
```

**Format Details**:
- **Type**: JSON array of passage objects
- **Fields**:
  - `ID` (string): UUID uniquely identifying the passage
  - `DocumentID` (integer): Document number (matches filename)
  - `PassageID` (string): Hierarchical reference (e.g., "1.1.1.(1)")
  - `Passage` (string): The actual rule text content
- **Notes**:
  - Some passages have empty `Passage` fields (these are skipped)
  - DocumentID=1 corresponds to `1.json`, DocumentID=2 to `2.json`, etc.

---

### Stage 2: Text Preparation
**Process**: Concatenate metadata with passage text for better semantic understanding

**Format**:
```python
text_for_embedding = f"Document {document_id} - {passage_ref}: {passage_text}"
```

**Example**:
```
"Document 1 - 1.1.1.(1): The AML Rulebook is made in recognition of the application of the Federal AML Legislation in the Abu Dhabi Global Market (\"ADGM\")."
```

**Rationale**:
- Including document ID and passage reference provides context
- Helps embeddings capture hierarchical structure
- Improves semantic search accuracy

---

### Stage 3: Embedding Generation
**Service**: OpenAI Embeddings API  
**Model**: `text-embedding-3-large`  
**API Call**:
```python
from services.embeddings import EmbeddingService

embedding_service = EmbeddingService()
vector = embedding_service.embed_text(text_for_embedding)
```

**Output Format**:
```python
# List of 3072 floating-point numbers
[
    0.0123456789,
    -0.0234567890,
    0.0345678901,
    # ... 3069 more values ...
    -0.0456789012
]
```

**Format Details**:
- **Type**: Python list of floats
- **Dimension**: 3072 (fixed by model)
- **Value Range**: Typically [-1.0, 1.0], normalized
- **Properties**: Dense vector representation capturing semantic meaning

---

### Stage 4: Metadata Construction
**Process**: Create metadata dictionary for Pinecone storage

**Format**:
```python
metadata = {
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

**Field Descriptions**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `passage_id` | string | Original UUID from JSON | `"bd35fb2d..."` |
| `document_id` | integer | Document number | `1` |
| `passage_ref` | string | Hierarchical reference | `"1.1.1.(1)"` |
| `passage_text` | string | Truncated text (max 1000 chars) | `"The AML Rulebook..."` |
| `full_text_length` | integer | Original text length | `150` |
| `source_file` | string | Source JSON filename | `"1.json"` |
| `is_active` | boolean | Rule active status | `true` |
| `jurisdiction` | string | Applicable jurisdiction | `"ADGM"` |
| `document_type` | string | Document category | `"aml_rulebook"` |
| `ingestion_date` | string | ISO 8601 timestamp | `"2024-11-01T10:30:00"` |

**Constraints**:
- All values must be Pinecone-compatible primitives (string, int, float, bool)
- `passage_text` truncated to 1000 characters (Pinecone metadata limit)
- Full text preserved in vector embedding for search

---

### Stage 5: Batch Collection
**Process**: Accumulate vectors before upserting to Pinecone

**Format**:
```python
vectors_to_upsert = [
    [0.123, -0.456, ...],  # 3072 floats
    [0.234, -0.567, ...],  # 3072 floats
    # ... more vectors
]

metadata_to_upsert = [
    {"passage_id": "uuid-1", "document_id": 1, ...},
    {"passage_id": "uuid-2", "document_id": 1, ...},
    # ... more metadata
]

ids_to_upsert = [
    "bd35fb2d-4de6-48fb-ab3c-baead722854f",
    "e563ad09-df80-435c-a497-eeec420efbc4",
    # ... more UUIDs
]
```

**Batch Size**: 100 vectors per upsert (configurable in PineconeService)

**Rationale**:
- Batch processing reduces API calls
- Improves ingestion performance
- All three lists must have same length (validated)

---

### Stage 6: Pinecone Upsert
**Service**: Pinecone Vector Database  
**API Call**:
```python
from services.pinecone_db import PineconeService

pinecone_service = PineconeService(index_type="internal")
success = pinecone_service.upsert_vectors(
    vectors=vectors_to_upsert,
    metadata_list=metadata_to_upsert,
    ids=ids_to_upsert
)
```

**Internal Format** (sent to Pinecone):
```python
[
    {
        "id": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
        "values": [0.123, -0.456, ...],  # 3072 floats
        "metadata": {
            "passage_id": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
            "document_id": 1,
            "passage_ref": "1.1.1.(1)",
            # ... rest of metadata
        }
    },
    # ... more vectors
]
```

**Batch Processing**:
- Internally splits into batches of 100
- Retries on transient failures
- Returns `True` if all batches succeed

---

### Stage 7: Pinecone Storage (Final)
**Storage Format** (in Pinecone index):

```
Index: internal-rules (PINECONE_INTERNAL_INDEX_HOST)
├── Vector: bd35fb2d-4de6-48fb-ab3c-baead722854f
│   ├── Dimensions: 3072
│   ├── Values: [0.123, -0.456, ...]
│   └── Metadata: {...}
├── Vector: e563ad09-df80-435c-a497-eeec420efbc4
│   ├── Dimensions: 3072
│   ├── Values: [0.234, -0.567, ...]
│   └── Metadata: {...}
└── ... (all passages from all 40 JSON files)
```

**Index Properties**:
- **Index Name**: Retrieved from `PINECONE_INTERNAL_INDEX_HOST` environment variable
- **Dimension**: 3072 (matches embedding model)
- **Metric**: Cosine similarity (default for semantic search)
- **Total Vectors**: ~3,000-5,000 (depending on non-empty passages)

---

## Complete Workflow Script

### Prerequisites
```bash
# 1. Set environment variables
export PINECONE_API_KEY=your-pinecone-api-key
export PINECONE_INTERNAL_INDEX_HOST=https://internal-xxxxx.svc.pinecone.io
export OPENAI_API_KEY=your-openai-api-key

# 2. Ensure Pinecone index exists (3072 dimensions, cosine metric)
```

### Execution
```bash
# Run the loading script
python scripts/load_internal_rules_pinecone.py
```

### Script Flow

```
START
  │
  ├─► 1. Locate internal_rules/ directory
  │      └─► Find all *.json files (1.json through 40.json)
  │
  ├─► 2. Initialize Services
  │      ├─► EmbeddingService (OpenAI client)
  │      └─► PineconeService(index_type="internal")
  │
  ├─► 3. For each JSON file:
  │      │
  │      ├─► Load JSON array
  │      │
  │      ├─► For each passage object:
  │      │      │
  │      │      ├─► Skip if Passage is empty
  │      │      │
  │      │      ├─► Extract: ID, DocumentID, PassageID, Passage
  │      │      │
  │      │      ├─► Prepare text: "Document X - Y: Z"
  │      │      │
  │      │      ├─► Generate embedding (3072-dim vector)
  │      │      │
  │      │      ├─► Construct metadata dict
  │      │      │
  │      │      └─► Add to batch (vectors, metadata, ids)
  │      │
  │      └─► Log progress
  │
  ├─► 4. Batch Upsert to Pinecone
  │      ├─► Split into batches of 100
  │      ├─► Upsert each batch with retry logic
  │      └─► Return success/failure
  │
  ├─► 5. Get Index Stats
  │      └─► Query Pinecone for total vector count
  │
  ├─► 6. Print Summary
  │      ├─► Total passages processed
  │      ├─► Total vectors in index
  │      └─► Success status
  │
  └─► END
```

### Expected Output
```
🚀 Loading internal rules to Pinecone vector database...
📁 Found 40 rule files in /path/to/internal_rules
🔧 Initializing services...
📦 Using Pinecone internal index: https://internal-xxxxx.svc.pinecone.io
📄 Processing: 1.json
   ✅ Prepared 150 passages from 1.json
📄 Processing: 2.json
   ✅ Prepared 120 passages from 2.json
...
📄 Processing: 40.json
   ✅ Prepared 95 passages from 40.json
🚀 Upserting 3847 vectors to Pinecone...
💾 Successfully upserted 3847 rules to Pinecone
======================================================================
📊 SUMMARY
======================================================================
✅ Loaded to Pinecone: 3847 rules
📦 Total in Pinecone index: 3847 vectors
======================================================================
🎉 Internal rules loading complete!
   Pinecone: ✅
======================================================================
```

---

## Retrieval Workflow (After Ingestion)

### Query Processing
```python
from services.embeddings import EmbeddingService
from services.pinecone_db import PineconeService

# 1. User query
query = "What are the Enhanced Due Diligence requirements?"

# 2. Generate query embedding
embedding_service = EmbeddingService()
query_vector = embedding_service.embed_text(query)  # 3072-dim vector

# 3. Search Pinecone
pinecone_service = PineconeService(index_type="internal")
results = pinecone_service.similarity_search(
    query_vector=query_vector,
    top_k=10,
    filter_dict={"is_active": True, "jurisdiction": "ADGM"}
)

# 4. Results format
# [
#     {
#         'id': 'uuid-123',
#         'score': 0.92,  # Similarity score (0-1)
#         'metadata': {
#             'passage_id': 'uuid-123',
#             'passage_ref': '8.4.1',
#             'passage_text': 'Enhanced CDD must be performed for...',
#             'document_id': 8,
#             ...
#         }
#     },
#     ...
# ]
```

---

## Data Validation

### Verify Ingestion Success

```python
from services.pinecone_db import PineconeService

# Check index stats
service = PineconeService(index_type="internal")
stats = service.get_index_stats()

print(f"Total vectors: {stats['total_vectors']}")
print(f"Dimension: {stats.get('dimension', 'N/A')}")
```

### Count Source Passages

```python
import json
from pathlib import Path

total = 0
rules_dir = Path("internal_rules")

for json_file in rules_dir.glob("*.json"):
    with open(json_file) as f:
        passages = json.load(f)
    non_empty = len([p for p in passages if p['Passage'].strip()])
    total += non_empty

print(f"Total non-empty passages in JSON: {total}")
```

### Compare Counts
```python
# Should match (or be very close)
assert abs(pinecone_count - json_count) < 10
```

---

## Error Handling

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No JSON files found | Wrong directory | Ensure running from project root |
| Empty passages skipped | Normal behavior | Empty passages are intentionally excluded |
| Embedding API error | OpenAI rate limit | Retry with backoff (handled automatically) |
| Pinecone upsert failure | Network/auth issue | Check API key and index host |
| Dimension mismatch | Wrong embedding model | Use text-embedding-3-large (3072-dim) |

### Script Failure Recovery

```bash
# Check what was already loaded
python -c "
from services.pinecone_db import PineconeService
s = PineconeService(index_type='internal')
print(s.get_index_stats())
"

# Re-run the script (safe - upsert is idempotent)
python scripts/load_internal_rules_pinecone.py
```

---

## Performance Metrics

### Expected Timing
- **JSON Loading**: ~1-2 seconds (40 files)
- **Embedding Generation**: ~30-60 seconds (3,847 passages, ~15 req/sec)
- **Pinecone Upsert**: ~10-20 seconds (batches of 100)
- **Total Time**: ~1-2 minutes for complete ingestion

### Optimization
- Batch size: 100 vectors per upsert (tunable in PineconeService)
- Parallel embedding generation: Possible with asyncio (future enhancement)
- Incremental updates: Only process changed files (future enhancement)

---

## Testing

See `tests/README_TESTING.md` for comprehensive test suite documentation.

**Quick Test**:
```bash
# Run all tests
pytest tests/test_pinecone_integration.py -v
pytest tests/test_load_internal_rules.py -v
```

---

## Summary

**Data Flow**:
```
JSON Files → Text Preparation → Embedding Generation → Metadata Construction → Batch Collection → Pinecone Upsert → Vector Storage
```

**Key Points**:
- ✅ 40 JSON files with ~3,800 passages
- ✅ 3072-dimensional embeddings (OpenAI text-embedding-3-large)
- ✅ Rich metadata for filtering (jurisdiction, document_id, is_active)
- ✅ UUID-based vector IDs for consistency
- ✅ Batch processing for efficiency
- ✅ Idempotent upserts (safe to re-run)
- ✅ Empty passages automatically skipped
- ✅ Full text truncated in metadata, preserved in embedding

**Next Steps**:
1. ✅ Run ingestion script
2. ✅ Verify vector count
3. ✅ Test similarity search
4. ✅ Integrate with retrieval agent
