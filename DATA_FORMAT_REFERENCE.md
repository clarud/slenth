# Quick Reference: Internal Rules Data Formats

## JSON Source Format
**Location**: `internal_rules/1.json` through `internal_rules/40.json`

```json
[
    {
        "ID": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
        "DocumentID": 1,
        "PassageID": "1.1.1.(1)",
        "Passage": "The AML Rulebook is made in recognition of the application..."
    }
]
```

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| ID | string (UUID) | `"bd35fb2d-..."` | Unique identifier |
| DocumentID | integer | `1` | Matches filename (1.json → 1) |
| PassageID | string | `"1.1.1.(1)"` | Hierarchical reference |
| Passage | string | `"The AML..."` | Rule text (may be empty) |

---

## Embedding Text Format
**Context**: Prepared for OpenAI API

```python
f"Document {document_id} - {passage_ref}: {passage_text}"
```

**Example**:
```
"Document 1 - 1.1.1.(1): The AML Rulebook is made in recognition of the application..."
```

---

## Vector Format
**Model**: `text-embedding-3-large`  
**Dimension**: 3072

```python
[0.0123456789, -0.0234567890, 0.0345678901, ..., -0.0456789012]
```

| Property | Value |
|----------|-------|
| Type | List of floats |
| Length | 3072 |
| Range | Typically [-1.0, 1.0] |
| Normalized | Yes (by OpenAI) |

---

## Metadata Format
**Storage**: Pinecone metadata

```python
{
    "passage_id": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
    "document_id": 1,
    "passage_ref": "1.1.1.(1)",
    "passage_text": "The AML Rulebook is made...",  # Max 1000 chars
    "full_text_length": 150,
    "source_file": "1.json",
    "is_active": True,
    "jurisdiction": "ADGM",
    "document_type": "aml_rulebook",
    "ingestion_date": "2024-11-01T10:30:00.000000"
}
```

| Field | Type | Purpose |
|-------|------|---------|
| passage_id | string | Original UUID from JSON |
| document_id | integer | Document number for grouping |
| passage_ref | string | Hierarchical reference for citation |
| passage_text | string | Truncated text (max 1000 chars) |
| full_text_length | integer | Original text length |
| source_file | string | Source JSON filename |
| is_active | boolean | Rule status (for filtering) |
| jurisdiction | string | Applicable jurisdiction |
| document_type | string | Document category |
| ingestion_date | string | ISO 8601 timestamp |

**Constraints**:
- All values must be primitives (string, int, float, bool)
- No nested objects or arrays
- Text truncated to fit Pinecone limits

---

## Pinecone Storage Format
**Final format** in Pinecone index:

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

## Query Result Format
**Returned** by similarity search:

```python
[
    {
        "id": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
        "score": 0.92,  # Cosine similarity (0-1, higher = more similar)
        "metadata": {
            "passage_id": "bd35fb2d-4de6-48fb-ab3c-baead722854f",
            "document_id": 1,
            "passage_ref": "1.1.1.(1)",
            "passage_text": "The AML Rulebook...",
            "jurisdiction": "ADGM",
            ...
        }
    },
    {
        "id": "e563ad09-df80-435c-a497-eeec420efbc4",
        "score": 0.87,
        "metadata": {...}
    }
]
```

**Sorted by**: `score` descending (most relevant first)

---

## Batch Upsert Format
**Sent to PineconeService**:

```python
vectors = [
    [0.123, -0.456, ...],  # 3072 floats
    [0.234, -0.567, ...],  # 3072 floats
]

metadata_list = [
    {"passage_id": "uuid-1", "document_id": 1, ...},
    {"passage_id": "uuid-2", "document_id": 1, ...},
]

ids = [
    "bd35fb2d-4de6-48fb-ab3c-baead722854f",
    "e563ad09-df80-435c-a497-eeec420efbc4",
]

pinecone_service.upsert_vectors(
    vectors=vectors,
    metadata_list=metadata_list,
    ids=ids
)
```

**Requirements**:
- All three lists must have same length
- Each vector must be exactly 3072 dimensions
- IDs must be unique strings
- Metadata values must be primitives

---

## Filter Dictionary Format
**For metadata filtering**:

```python
# Simple filter
filter_dict = {"is_active": True}

# Multiple filters (AND logic)
filter_dict = {
    "is_active": True,
    "jurisdiction": "ADGM",
    "document_id": 1
}

# Usage
results = pinecone_service.similarity_search(
    query_vector=vector,
    top_k=10,
    filter_dict=filter_dict
)
```

**Supported operators**:
- Exact match: `{"field": "value"}`
- Numeric: `{"field": {"$gte": 10}}`
- In list: `{"field": {"$in": ["A", "B"]}}`

---

## Quick Examples

### Load Data
```bash
python scripts/load_internal_rules_pinecone.py
```

### Query by Similarity
```python
from services.embeddings import EmbeddingService
from services.pinecone_db import PineconeService

# Generate query embedding
embedding_service = EmbeddingService()
query_vector = embedding_service.embed_text("Enhanced Due Diligence requirements")

# Search
pinecone_service = PineconeService(index_type="internal")
results = pinecone_service.similarity_search(
    query_vector=query_vector,
    top_k=5,
    filter_dict={"is_active": True}
)
```

### Filter Results
```python
# Active ADGM rules only
results = pinecone_service.similarity_search(
    query_vector=vector,
    top_k=10,
    filter_dict={
        "is_active": True,
        "jurisdiction": "ADGM"
    }
)
```

### Check Stats
```python
from services.pinecone_db import PineconeService

service = PineconeService(index_type="internal")
stats = service.get_index_stats()
print(f"Total vectors: {stats['total_vectors']}")
print(f"Dimension: {stats.get('dimension', 'N/A')}")
```

---

## Common Values

### Jurisdictions
- `"ADGM"` (Abu Dhabi Global Market)
- `"HK"` (Hong Kong)
- `"SG"` (Singapore)
- `"CH"` (Switzerland)

### Document Types
- `"aml_rulebook"` (Internal AML rules)
- `"regulatory_circular"` (External regulatory updates)
- `"policy_manual"` (Internal policies)

### Document IDs
- `1` through `40` (corresponding to 1.json through 40.json)

---

## Data Transformation Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ Stage 1: JSON Files                                             │
│ [{ID, DocumentID, PassageID, Passage}, ...]                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 2: Text Preparation                                       │
│ "Document X - Y: Z"                                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 3: Embedding Generation (OpenAI API)                      │
│ [0.123, -0.456, ...] (3072 floats)                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 4: Metadata Construction                                  │
│ {passage_id, document_id, passage_ref, passage_text, ...}      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 5: Batch Collection                                       │
│ vectors=[[...]], metadata=[{...}], ids=["uuid", ...]           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 6: Pinecone Upsert (Batches of 100)                       │
│ POST /vectors/upsert                                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 7: Vector Storage                                         │
│ Pinecone Index: internal-rules                                  │
│ {id, values, metadata}                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Validation Checklist

- [ ] JSON files exist in `internal_rules/`
- [ ] All passages have valid UUID in `ID` field
- [ ] `DocumentID` matches filename (1.json → 1)
- [ ] Empty passages are skipped
- [ ] Embeddings are 3072-dimensional
- [ ] Metadata text truncated to 1000 chars
- [ ] All metadata values are primitives
- [ ] Vector IDs match passage UUIDs
- [ ] Batch sizes appropriate (100 per upsert)
- [ ] Total vectors in Pinecone matches non-empty passages in JSON
