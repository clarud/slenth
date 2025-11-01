# External Rules Ingestion Workflow

## Complete Data Flow: Web Crawling → Pinecone Vector Database

This document explains the complete workflow for ingesting external AML regulatory rules from HKMA, MAS, and FINMA websites into the Pinecone vector database, following the same pattern as internal rules.

---

## Overview

**Sources**: 
- HKMA (Hong Kong): AML/CFT guidance papers and circulars
- MAS (Singapore): AML/CFT notices and regulations  
- FINMA (Switzerland): Regulatory circulars

**Destinations**: 
- PostgreSQL database (`external_rules` table)
- Pinecone vector database (external index)

**Purpose**: Enable semantic similarity search for regulatory rule retrieval during transaction analysis

---

## Data Format at Each Stage

### Stage 1: Web Crawling
**Process**: Automated crawlers fetch PDFs from regulatory websites

**HKMA Source**:
```
URL: https://www.hkma.gov.hk/eng/key-functions/banking/anti-money-laundering-and-counter-financing-of-terrorism/guidance-papers-circulars/

Example documents:
- "Use of Artificial Intelligence for Monitoring of Suspicious Transactions"
- "Enhanced CDD Measures for High-Risk Customers"
- "FATF Statements on High-Risk Jurisdictions"
```

**MAS Source**:
```
URL: https://www.mas.gov.sg/regulation/notices

Example documents:
- "AMLD 01/2022: Non-Face-to-Face Customer Due Diligence"
- "CMI 27/2018: Controls for Listed Securities"
- "MPI 02/2016: Margin Requirements for Derivatives"
```

**FINMA Source**:
```
URL: https://www.finma.ch/en/documentation/circulars/

Example documents:
- "FINMA Circular 2026/01: Nature-related Financial Risks"
- "Anti-Money Laundering Ordinance"
- "Market Conduct Rules"
```

**Crawler Output Format**:
```python
{
    "title": "Use of Artificial Intelligence for Monitoring...",
    "url": "https://www.hkma.gov.hk/media/eng/doc/key-information/...",
    "date": datetime(2024, 9, 15),
    "content": "1. Introduction\n\nThe Hong Kong Monetary Authority...",
    "source": "HKMA",
    "jurisdiction": "HK",
    "rule_type": "guidance",
}
```

---

### Stage 2: Content Extraction (PDF Parsing)
**Process**: PyPDF2 extracts text from downloaded PDFs

**Raw PDF Text**:
```
1. Introduction

The Hong Kong Monetary Authority (HKMA) recognizes that advances in 
artificial intelligence and machine learning technologies provide 
opportunities for authorized institutions to enhance their anti-money 
laundering and counter-financing of terrorism (AML/CFT) systems...

2. Key Principles

2.1 Risk-Based Approach
Authorized institutions should adopt a risk-based approach when 
implementing AI/ML solutions...
```

**Format Details**:
- Multi-page PDFs processed page-by-page
- Text extracted with layout preserved
- Handles various PDF formats (scanned OCR not yet implemented)
- Typical document: 500-5,000 words

---

### Stage 3: Content Chunking
**Process**: Large documents split into manageable chunks

**Configuration**:
```python
MAX_CHUNK_SIZE = 2000  # words per chunk
CHUNK_OVERLAP = 200    # words overlap between chunks
```

**Chunking Logic**:
```python
# Document with 4,500 words:
Chunk 0: Words 0-2000 (2000 words)
Chunk 1: Words 1800-3800 (2000 words, overlaps with Chunk 0)
Chunk 2: Words 3600-4500 (900 words, overlaps with Chunk 1)

# Result: 3 chunks stored separately
```

**Rationale**:
- Prevents exceeding embedding model context limits
- Overlap ensures context continuity
- Each chunk independently searchable
- Smaller chunks = more precise retrieval

---

### Stage 4: Text Preparation
**Process**: Add context metadata to each chunk for better semantic understanding

**Format**:
```python
text_for_embedding = f"{source} {jurisdiction} - {title} [Chunk {idx}]: {content}"
```

**Examples**:
```
"HKMA HK - Use of Artificial Intelligence for Monitoring of Suspicious Transactions [Chunk 0]: 1. Introduction The Hong Kong Monetary Authority..."

"MAS SG - AMLD 01/2022: Non-Face-to-Face Customer Due Diligence: 1. This circular sets out the requirements..."

"FINMA CH - Nature-related Financial Risks [Chunk 1]: 3. Risk Assessment Financial institutions must assess..."
```

**Rationale**:
- Source context helps embeddings capture jurisdiction-specific nuances
- Title provides topical context
- Chunk index aids in reconstructing full documents
- Similar to internal rules: "Document X - Y: Z" pattern

---

### Stage 5: Duplicate Detection
**Process**: Check PostgreSQL for existing rules before ingestion

**Query**:
```python
existing = db_session.query(ExternalRule).filter(
    ExternalRule.source_url == url
).first()

if existing:
    logger.debug(f"Rule already exists (URL match): {title}")
    continue
```

**Detection Method**:
- **Primary Key**: Source URL (unique per document)
- **Fallback**: Rule ID hash (regulator + title + URL)

**Behavior**:
- Existing documents skipped (idempotent ingestion)
- Safe to re-run daily without duplicates
- Updates require manual deletion first

---

### Stage 6: Embedding Generation
**Service**: OpenAI Embeddings API  
**Model**: `text-embedding-3-large` (same as internal rules)

**API Call**:
```python
from services.embeddings import EmbeddingService

embedding_service = EmbeddingService()
text_with_context = prepare_text_for_embedding(rule, chunk_index)
vector = embedding_service.embed_text(text_with_context)
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
- **Dimension**: 3072 (matches internal rules)
- **Model**: text-embedding-3-large
- **Cost**: ~$0.13 per 1M tokens

---

### Stage 7: Database Storage (PostgreSQL)
**Table**: `external_rules`

**Schema**:
```sql
CREATE TABLE external_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id VARCHAR(100) UNIQUE NOT NULL,  -- e.g., "HKMA-3f8a7b2c9d1e-0"
    
    -- Rule Info
    regulator VARCHAR(50) NOT NULL,  -- HKMA, MAS, FINMA
    jurisdiction VARCHAR(10) NOT NULL,  -- HK, SG, CH
    rule_title VARCHAR(500),
    rule_text TEXT NOT NULL,
    
    -- Source
    source_url VARCHAR(1000),
    document_title VARCHAR(500),
    section_path VARCHAR(500),
    published_date TIMESTAMP,
    effective_date TIMESTAMP,
    
    -- Vector DB
    vector_id VARCHAR(100),  -- UUID in Pinecone
    
    -- Chunking
    chunk_index INTEGER,  -- 0, 1, 2... (NULL for single-chunk docs)
    
    -- Metadata
    metadata JSONB,
    scraped_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_external_rule_regulator ON external_rules(regulator);
CREATE INDEX idx_external_rule_dates ON external_rules(published_date, effective_date);
```

**Example Record**:
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "rule_id": "HKMA-3f8a7b2c9d1e-0",
    "regulator": "HKMA",
    "jurisdiction": "HK",
    "rule_title": "Use of AI for Monitoring Suspicious Transactions",
    "rule_text": "1. Introduction\n\nThe Hong Kong Monetary Authority...",
    "source_url": "https://www.hkma.gov.hk/media/eng/doc/...",
    "document_title": "Use of AI for Monitoring Suspicious Transactions",
    "published_date": "2024-09-15T00:00:00",
    "vector_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "chunk_index": 0,
    "metadata": {
        "crawled_at": "2025-11-01T10:30:00",
        "rule_type": "guidance",
        "total_chunks": 3,
        "word_count": 2000,
        "full_word_count": 4500
    }
}
```

---

### Stage 8: Metadata Construction (for Pinecone)
**Process**: Create rich metadata for vector search filtering

**Format**:
```python
vector_metadata = {
    "rule_id": "HKMA-3f8a7b2c9d1e-0",
    "regulator": "HKMA",
    "jurisdiction": "HK",
    "title": "Use of AI for Monitoring...",  # Truncated to 500 chars
    "text": "1. Introduction\n\nThe Hong Kong...",  # First 1000 chars
    "url": "https://www.hkma.gov.hk/media/...",
    "chunk_index": 0,
    "total_chunks": 3,
    "published_date": "2024-09-15T00:00:00",
    "rule_type": "guidance",
    "word_count": 2000,
}
```

**Field Descriptions**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `rule_id` | string | Unique rule + chunk ID | `"HKMA-3f8a7b2c9d1e-0"` |
| `regulator` | string | Source regulator | `"HKMA"` |
| `jurisdiction` | string | Jurisdiction code | `"HK"` |
| `title` | string | Document title (truncated) | `"Use of AI..."` |
| `text` | string | Preview text (1000 chars) | `"1. Introduction..."` |
| `url` | string | Source PDF URL | `"https://..."` |
| `chunk_index` | integer | Chunk number (0-based) | `0` |
| `total_chunks` | integer | Total chunks in document | `3` |
| `published_date` | string | ISO 8601 date | `"2024-09-15T00:00:00"` |
| `rule_type` | string | Document type | `"guidance"` |
| `word_count` | integer | Words in this chunk | `2000` |

**Constraints**:
- All values must be Pinecone-compatible primitives
- `title` and `text` truncated for Pinecone metadata limits
- Full text preserved in vector embedding

---

### Stage 9: Batch Upsert to Pinecone
**Service**: Pinecone Vector Database  
**Index**: External rules index

**Batch Configuration**:
```python
BATCH_SIZE = 50  # Upsert 50 vectors at a time
```

**API Call**:
```python
vector_db.upsert_vectors(
    collection_name="external_rules",
    texts=texts_batch,  # List of 50 full texts
    vectors=vectors_batch,  # List of 50 embeddings (3072-dim each)
    metadata=metadata_batch,  # List of 50 metadata dicts
)
```

**Internal Format** (sent to Pinecone):
```python
[
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "values": [0.123, -0.456, ...],  # 3072 floats
        "metadata": {
            "rule_id": "HKMA-3f8a7b2c9d1e-0",
            "regulator": "HKMA",
            "jurisdiction": "HK",
            "title": "Use of AI...",
            "text": "1. Introduction...",
            # ... rest of metadata
        }
    },
    # ... 49 more vectors
]
```

**Batch Processing Rationale**:
- Reduces API calls (50x fewer than individual upserts)
- Improves throughput
- Handles transient failures with retry logic

---

### Stage 10: Pinecone Storage (Final)
**Storage Format** (in Pinecone index):

```
Index: external-rules (PINECONE_EXTERNAL_INDEX_HOST)
├── Vector: a1b2c3d4-e5f6-7890-abcd-ef1234567890
│   ├── Dimensions: 3072
│   ├── Values: [0.123, -0.456, ...]
│   └── Metadata: {...}
├── Vector: b2c3d4e5-f6a7-8901-bcde-f12345678901
│   ├── Dimensions: 3072
│   ├── Values: [0.234, -0.567, ...]
│   └── Metadata: {...}
└── ... (all chunks from all regulators)
```

**Index Properties**:
- **Index Name**: Retrieved from `PINECONE_EXTERNAL_INDEX_HOST` environment variable
- **Dimension**: 3072 (matches embedding model)
- **Metric**: Cosine similarity (default for semantic search)
- **Total Vectors**: ~150-300 (depending on crawl scope and chunking)

**Index Organization**:
```
HKMA (HK): ~100 documents → ~150 chunks
MAS (SG): ~20 documents → ~30 chunks
FINMA (CH): ~30 documents → ~50 chunks
────────────────────────────────────
Total: ~150 documents → ~230 chunks
```

---

## Complete Workflow Script

### Prerequisites
```bash
# 1. Set environment variables
export PINECONE_API_KEY=your-pinecone-api-key
export PINECONE_EXTERNAL_INDEX_HOST=https://external-xxxxx.svc.pinecone.io
export OPENAI_API_KEY=your-openai-api-key

# 2. Ensure Pinecone external index exists (3072 dimensions, cosine metric)

# 3. Ensure PostgreSQL external_rules table exists
python scripts/create_tables.py
```

### Execution
```bash
# Run the ingestion cron job
python cron/external_rules_ingestion.py
```

### Script Flow

```
START
  │
  ├─► 1. Initialize Services
  │      ├─► EmbeddingService (OpenAI client)
  │      ├─► VectorDBService (Pinecone client)
  │      └─► Database session (PostgreSQL)
  │
  ├─► 2. HKMA Crawler
  │      │
  │      ├─► Fetch HTML from HKMA website
  │      ├─► Discover PDF links (101 documents)
  │      ├─► Download first 50 PDFs
  │      ├─► Extract text with PyPDF2
  │      │
  │      └─► For each PDF:
  │            ├─► Check duplicate (by URL)
  │            ├─► Chunk if >2000 words
  │            ├─► Prepare text with context
  │            ├─► Generate embedding
  │            ├─► Create DB record
  │            ├─► Add to batch
  │            └─► Upsert batch every 50 vectors
  │
  ├─► 3. MAS Crawler
  │      │
  │      ├─► Fetch HTML from MAS website
  │      ├─► Discover PDF links
  │      ├─► Parse detail pages for PDF URLs
  │      ├─► Download and extract PDFs
  │      │
  │      └─► Process same as HKMA
  │
  ├─► 4. FINMA Crawler
  │      │
  │      ├─► Fetch HTML from FINMA website
  │      ├─► Filter circular PDFs
  │      ├─► Download and extract PDFs
  │      │
  │      └─► Process same as HKMA
  │
  ├─► 5. Final Batch Upsert
  │      └─► Upsert remaining vectors (<50)
  │
  ├─► 6. Database Commit
  │      └─► Commit all PostgreSQL records
  │
  ├─► 7. Print Summary
  │      ├─► Total rules/chunks saved
  │      ├─► Breakdown by regulator
  │      └─► Success status
  │
  └─► END
```

### Expected Output
```
================================================================================
🚀 EXTERNAL RULES INGESTION JOB - START
Timestamp: 2025-11-01T02:00:00.000000
================================================================================

================================================================================
[1/3] HKMA - Hong Kong Monetary Authority
================================================================================
Crawling: https://www.hkma.gov.hk/eng/key-functions/banking/anti-money-laundering...
✅ Crawled 50 circulars
Processing rule: Use of AI for Monitoring Suspicious Transactions (3 chunks, 4500 words)
Processing rule: Enhanced CDD Measures for High-Risk Customers (1 chunks, 1200 words)
...
Upserted batch of 50 vectors to Pinecone
Processing rule: FATF Statements on High-Risk Jurisdictions (2 chunks, 3000 words)
...
Upserted final batch of 25 vectors to Pinecone
💾 Ingested 75 rule chunks to PostgreSQL + Pinecone

================================================================================
[2/3] MAS - Monetary Authority of Singapore
================================================================================
Crawling: https://www.mas.gov.sg/regulation/notices
✅ Crawled 11 notices
Processing rule: AMLD 01/2022: Non-Face-to-Face Customer Due Diligence (2 chunks, 3259 words)
...
Upserted batch of 15 vectors to Pinecone
💾 Ingested 15 rule chunks to PostgreSQL + Pinecone

================================================================================
[3/3] FINMA - Swiss Financial Market Supervisory Authority
================================================================================
Crawling: https://www.finma.ch/en/documentation/circulars/
✅ Crawled 25 circulars
Processing rule: FINMA Circular 2026/01: Nature-related Financial Risks (2 chunks, 3288 words)
...
Upserted batch of 30 vectors to Pinecone
💾 Ingested 30 rule chunks to PostgreSQL + Pinecone

================================================================================
📊 INGESTION JOB SUMMARY
================================================================================
✅ Total rule chunks saved: 120
💾 Saved to: PostgreSQL (external_rules table) + Pinecone (external index)
⏰ Completed at: 2025-11-01T02:15:32.000000
================================================================================
🎉 External rules ingestion complete!
================================================================================
```

---

## Retrieval Workflow (After Ingestion)

### Query Processing
```python
from services.embeddings import EmbeddingService
from services.vector_db import VectorDBService

# 1. User query
query = "What are HKMA's guidance on using AI for transaction monitoring?"

# 2. Generate query embedding
embedding_service = EmbeddingService()
query_vector = embedding_service.embed_text(query)  # 3072-dim vector

# 3. Search Pinecone
vector_db = VectorDBService()
results = vector_db.hybrid_search(
    collection_name="external_rules",
    query_vector=query_vector,
    query_text=query,
    top_k=10,
    filters={
        "regulator": "HKMA",
        "jurisdiction": "HK",
    }
)

# 4. Results format
# [
#     {
#         'id': 'a1b2c3d4-...',
#         'score': 0.89,  # Similarity score (0-1)
#         'text': 'HKMA HK - Use of AI... 1. Introduction...',
#         'metadata': {
#             'rule_id': 'HKMA-3f8a7b2c9d1e-0',
#             'regulator': 'HKMA',
#             'jurisdiction': 'HK',
#             'title': 'Use of AI for Monitoring...',
#             'chunk_index': 0,
#             'total_chunks': 3,
#             ...
#         }
#     },
#     ...
# ]
```

### Filtering Options
```python
# Filter by regulator
filters = {"regulator": "HKMA"}

# Filter by jurisdiction
filters = {"jurisdiction": "SG"}

# Filter by date range
filters = {
    "published_date": {"gte": "2024-01-01T00:00:00"}
}

# Filter by rule type
filters = {"rule_type": "guidance"}

# Combine filters
filters = {
    "regulator": "FINMA",
    "jurisdiction": "CH",
    "published_date": {"gte": "2024-01-01T00:00:00"}
}
```

---

## Data Validation

### Verify Ingestion Success (PostgreSQL)

```sql
-- Count total rules
SELECT regulator, COUNT(*) as total_rules, COUNT(DISTINCT rule_id) as unique_docs
FROM external_rules
GROUP BY regulator;

-- Expected output:
-- regulator | total_rules | unique_docs
-- ----------+-------------+-------------
-- HKMA      |          75 |          50
-- MAS       |          15 |          11
-- FINMA     |          30 |          25

-- Check chunking
SELECT 
    regulator,
    AVG(CASE WHEN chunk_index IS NULL THEN 1 ELSE (metadata->>'total_chunks')::int END) as avg_chunks,
    MAX(CASE WHEN chunk_index IS NULL THEN 1 ELSE (metadata->>'total_chunks')::int END) as max_chunks
FROM external_rules
GROUP BY regulator;
```

### Verify Pinecone Storage

```python
from services.vector_db import VectorDBService

# Check index stats
vector_db = VectorDBService()
# Note: Pinecone stats API varies by SDK version
# Manual verification via Pinecone console recommended
```

### Compare Counts
```python
# PostgreSQL count
db_count = db_session.query(ExternalRule).count()

# Pinecone count (via console or API)
# Should match (or be very close)
assert abs(pinecone_count - db_count) < 10
```

---

## Comparison: Internal vs External Rules

| Aspect | Internal Rules | External Rules |
|--------|---------------|----------------|
| **Source** | 40 JSON files (static) | 3 websites (dynamic) |
| **Total Documents** | ~3,800 passages | ~150-200 documents |
| **Total Chunks** | ~3,800 (no chunking) | ~230 (with chunking) |
| **Update Frequency** | Manual | Daily (cron) |
| **Chunking** | No (passages already small) | Yes (>2000 words) |
| **Duplicate Detection** | UUID from JSON | URL-based |
| **Context Prefix** | `"Document X - Y: Z"` | `"Source Juris - Title: Z"` |
| **Pinecone Index** | Internal index | External index |
| **DB Table** | `internal_rules` | `external_rules` |
| **Jurisdiction** | ADGM only | HK, SG, CH |

---

## Error Handling

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Crawler timeout | Network/website slow | Retry with backoff (handled automatically) |
| PDF extraction failed | Scanned PDF / no text | Skip document (log warning) |
| Duplicate URL | Re-running cron | Skip (idempotent behavior) |
| Embedding API error | OpenAI rate limit | Retry with exponential backoff |
| Pinecone upsert failure | Network/auth issue | Check API key and index host |
| Database constraint violation | Duplicate rule_id | Check hash collision (rare) |

### Script Failure Recovery

```bash
# Check what was already loaded (PostgreSQL)
psql -d your_db -c "SELECT regulator, COUNT(*) FROM external_rules GROUP BY regulator;"

# Check Pinecone vectors (via console)
# https://app.pinecone.io/

# Re-run the script (safe - duplicate detection prevents re-ingestion)
python cron/external_rules_ingestion.py
```

---

## Performance Metrics

### Expected Timing (per regulator)
- **HTML Fetching**: ~2-5 seconds
- **PDF Discovery**: ~1-3 seconds
- **PDF Download**: ~10-30 seconds (50 PDFs)
- **PDF Extraction**: ~20-60 seconds
- **Embedding Generation**: ~30-90 seconds (~50 docs × 2 chunks avg)
- **Pinecone Upsert**: ~10-30 seconds (batched)
- **Total Time per Regulator**: ~2-5 minutes

### Total Job Time
- **All 3 Regulators**: ~8-15 minutes
- **Bottleneck**: PDF download and embedding generation

### Optimization
- Batch size: 50 vectors per upsert (tunable)
- Parallel crawling: Possible with asyncio (future)
- Incremental updates: Only crawl new documents (future)
- PDF caching: Cache downloaded PDFs locally (future)

---

## Cron Schedule

### Production Schedule
```bash
# Run daily at 2 AM UTC
0 2 * * * cd /path/to/slenth && python cron/external_rules_ingestion.py >> /var/log/slenth/external_rules.log 2>&1
```

### Testing Schedule
```bash
# Run every hour (for testing)
0 * * * * cd /path/to/slenth && python cron/external_rules_ingestion.py
```

---

## Testing

### Quick Test (Cached HTML)
```bash
# Test with cached HTML files (no live crawling)
# Ensure hkma_test.html, mas.html, finma.html exist
python test_all_crawlers.py
```

### Full Test (Live Crawling, Limited)
```bash
# Test with live URLs, limited to 3 documents per regulator
python test_all_crawlers.py --live
```

### Production Test (Live Crawling, Full)
```bash
# Full production run
python cron/external_rules_ingestion.py
```

---

## Summary

**Data Flow**:
```
Web Crawling → PDF Extraction → Duplicate Detection → Chunking → 
Text Preparation → Embedding Generation → Batch Collection → 
PostgreSQL Storage → Pinecone Upsert → Vector Storage
```

**Key Points**:
- ✅ 3 regulators: HKMA (HK), MAS (SG), FINMA (CH)
- ✅ ~150-200 documents → ~230 chunks (with overlap)
- ✅ 3072-dimensional embeddings (OpenAI text-embedding-3-large)
- ✅ Rich metadata for filtering (regulator, jurisdiction, date, type)
- ✅ URL-based duplicate detection (idempotent ingestion)
- ✅ Chunking for large documents (>2000 words)
- ✅ Context-aware embeddings (regulator + jurisdiction + title prefix)
- ✅ Batch processing for efficiency (50 vectors per upsert)
- ✅ Dual storage: PostgreSQL (searchable metadata) + Pinecone (semantic search)
- ✅ Safe to re-run (duplicates skipped)
- ✅ Scheduled daily via cron

**Next Steps**:
1. ✅ Run initial ingestion: `python cron/external_rules_ingestion.py`
2. ✅ Verify counts in PostgreSQL and Pinecone
3. ✅ Test semantic search with sample queries
4. ✅ Integrate with retrieval agent workflow
5. ⏳ Set up daily cron job
6. ⏳ Monitor logs for failures
7. ⏳ Implement incremental updates (future)
