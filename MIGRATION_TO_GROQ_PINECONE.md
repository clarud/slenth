# Migration to Groq and Pinecone with Integrated Embeddings

## Overview
This document summarizes the migration of the Part 1 agentic workflow from using separate embedding services and multiple vector databases to using **Groq** as the LLM provider and **Pinecone** with integrated embeddings as the sole vector database.

## Key Changes

### 1. LLM Provider: Migrated to Groq

#### Configuration (`config.py`)
- Added `LLM_PROVIDER` configuration (default: `groq`)
- Added `GROQ_API_KEY` environment variable
- Added `GROQ_BASE_URL` (https://api.groq.com/openai/v1)
- Added `GROQ_MODEL` (default: `openai/gpt-oss-20b`)

#### LLM Service (`services/llm.py`)
- Added `LLMProvider.GROQ` enum value
- Updated `__init__` to support Groq provider
- Groq uses OpenAI-compatible API via `openai.OpenAI` client with custom base URL
- Updated `chat_completion()` to handle Groq responses
- Updated `chat_completion_stream()` for Groq streaming
- Added cost estimation for Groq usage
- Added `generate()` helper method for simplified text generation

**Example Groq Usage with LangChain:**
```python
from langchain_openai import ChatOpenAI
import os

# Configure ChatOpenAI to point at Groq
llm = ChatOpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
    model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
    temperature=0.2,
)

# Use LCEL invoke pattern
response = llm.invoke([
    {"role": "system", "content": "You are a concise AI assistant."},
    {"role": "user", "content": "Explain the importance of fast language models"}
])

# response.content contains the model's reply
print(response.content)
```

### 2. Vector Database: Pinecone with Integrated Embeddings

#### Key Concept
Pinecone now provides integrated embeddings through its inference API, eliminating the need for separate embedding services (like OpenAI embeddings). When you search or upsert, Pinecone automatically generates embeddings.

#### Pinecone Service (`services/pinecone_db.py`)
Already implemented with:
- `search_by_text()` - Semantic search using Pinecone's integrated embeddings
- `upsert_records()` - Upsert with automatic embedding generation
- Dual-index support (internal and external)

**Example Pinecone Search:**
```python
from pinecone import Pinecone

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(host=os.getenv("PINECONE_INTERNAL_INDEX_HOST"))

results = index.search(
    namespace="internal-rules",
    query={
        "inputs": {"text": query_text},
        "top_k": 10
    },
    fields=["text", "rule_id", "jurisdiction", "severity"]
)
```

### 3. Removed Dependencies

#### Deprecated Services
- `EmbeddingService` - No longer needed (Pinecone handles embeddings)
- `VectorDBService` - Replaced by `PineconeService`

#### Files Modified

**`workflows/transaction_workflow.py`**
- Removed `EmbeddingService` import
- Removed `VectorDBService` import
- Added `PineconeService` import
- Updated `create_transaction_workflow()` signature:
  - ❌ `vector_service: VectorDBService`
  - ❌ `embedding_service: EmbeddingService`
  - ✅ `pinecone_internal: PineconeService`
  - ✅ `pinecone_external: PineconeService`

**`agents/part1/retrieval.py`**
- Removed `VectorDBService` import
- Removed `EmbeddingService` import
- Updated `RetrievalAgent.__init__()` to only accept Pinecone services
- Changed from `similarity_search()` with pre-computed embeddings to `search_by_text()` with integrated embeddings
- Removed manual embedding generation step

**Before:**
```python
query_embedding = self.embeddings.embed_text(query)
results = await self.pinecone.similarity_search(
    query_vector=query_embedding,
    top_k=10
)
```

**After:**
```python
results = self.pinecone.search_by_text(
    query_text=query,
    top_k=10,
    namespace="internal-rules"
)
```

**`worker/tasks.py`**
- Removed `EmbeddingService` import
- Removed `VectorDBService` import
- Added `PineconeService` import
- Updated `process_transaction()` to initialize Pinecone services:
```python
llm_service = LLMService()  # Uses Groq by default
pinecone_internal = PineconeService(index_type="internal")
pinecone_external = PineconeService(index_type="external")
```

**`app/api/internal_rules.py`**
- Removed `EmbeddingService` import
- Removed `VectorDBService` import
- Added `PineconeService` import
- Updated rule creation to use Pinecone's `upsert_records()`:
```python
pinecone_service.upsert_records(
    records=[{
        "_id": rule_id,
        "text": rule_text,
        "metadata": {...}
    }],
    namespace="internal-rules"
)
```

### 4. Environment Variables

Required environment variables in `.env`:

```bash
# LLM Configuration (Groq)
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=your_groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INTERNAL_INDEX_HOST=https://your-internal-index.pinecone.io
PINECONE_EXTERNAL_INDEX_HOST=https://your-external-index.pinecone.io
```

### 5. Agent Updates

All agents that use LLM now automatically use Groq:
- **ApplicabilityAgent** - LLM-based rule applicability determination
- **ControlTestAgent** - LLM-based control testing
- **AnalystWriterAgent** - LLM-based report generation

All agents use the simplified `LLMService.generate()` method:
```python
response = await self.llm.generate(
    prompt=prompt,
    response_format="json",
    max_tokens=300,
    temperature=0.3
)
```

### 6. Workflow Execution Flow

**Updated Flow:**
```
1. ContextBuilder → Builds query strings
2. RetrievalAgent → Pinecone semantic search (integrated embeddings)
3. ApplicabilityAgent → Groq LLM determines applicability
4. FeatureService → Feature extraction
5. PatternDetector → Pattern detection
6. BayesianEngine → Risk probability calculation
7. EvidenceMapper → Evidence mapping
8. ControlTest → Groq LLM tests controls
9. DecisionFusion → Risk score aggregation
10. AlertComposer → Alert generation
11. AnalystWriter → Groq LLM generates report
12. Persistor → Data persistence
13. RemediationOrchestrator → Remediation planning
```

## Benefits

### Performance
- ✅ **Faster retrieval** - No separate embedding API calls
- ✅ **Reduced latency** - Pinecone generates embeddings server-side
- ✅ **Fewer API dependencies** - Only Groq and Pinecone

### Cost
- ✅ **Lower embedding costs** - No separate OpenAI embedding charges
- ✅ **Competitive LLM pricing** - Groq offers cost-effective inference
- ✅ **Simplified billing** - Two services instead of three+

### Simplicity
- ✅ **Fewer services to manage** - No embedding service maintenance
- ✅ **Single vector database** - Pinecone for both internal and external rules
- ✅ **Cleaner architecture** - Reduced service dependencies

### Reliability
- ✅ **Integrated embeddings** - No embedding service failures
- ✅ **Fast inference** - Groq optimized for speed
- ✅ **Consistent embedding model** - Pinecone manages embedding model

## Migration Checklist

- [x] Update `config.py` with Groq configuration
- [x] Update `services/llm.py` to support Groq
- [x] Add `generate()` helper method to LLM service
- [x] Update `workflows/transaction_workflow.py` to remove embedding service
- [x] Update `agents/part1/retrieval.py` to use Pinecone's integrated embeddings
- [x] Update `worker/tasks.py` to use Pinecone services
- [x] Update `app/api/internal_rules.py` to use Pinecone's upsert_records
- [x] Update `.env` with required environment variables
- [x] Update `PART1_AGENTS_DOCUMENTATION.md` with new architecture
- [ ] Test end-to-end workflow with real transaction data
- [ ] Verify Pinecone indexes are properly configured
- [ ] Monitor Groq API rate limits and performance
- [ ] Update deployment scripts if needed

## Testing

### Unit Tests
Update test files to mock Pinecone and Groq services:
```python
@pytest.fixture
def mock_pinecone():
    return Mock(spec=PineconeService)

@pytest.fixture
def mock_llm():
    return Mock(spec=LLMService)
```

### Integration Tests
Test the full workflow:
```python
async def test_transaction_workflow():
    llm = LLMService()  # Uses Groq
    pinecone_internal = PineconeService(index_type="internal")
    pinecone_external = PineconeService(index_type="external")
    
    result = await execute_transaction_workflow(
        transaction=sample_transaction,
        db_session=db,
        llm_service=llm,
        pinecone_internal=pinecone_internal,
        pinecone_external=pinecone_external
    )
    
    assert result["risk_score"] is not None
    assert result["risk_band"] in ["Low", "Medium", "High", "Critical"]
```

## Troubleshooting

### Common Issues

**1. Groq API Errors**
- Check `GROQ_API_KEY` is valid
- Verify model name is `openai/gpt-oss-20b`
- Check rate limits

**2. Pinecone Search Failures**
- Verify `PINECONE_INTERNAL_INDEX_HOST` and `PINECONE_EXTERNAL_INDEX_HOST` are correct
- Ensure indexes are properly configured with inference enabled
- Check namespace names match ("internal-rules", "external-rules")

**3. Missing Embeddings**
- Pinecone generates embeddings automatically - no action needed
- If search returns no results, check if data is properly upserted

## Rollback Plan

If issues arise, rollback by:
1. Revert to OpenAI for LLM: `LLM_PROVIDER=openai`
2. Re-enable `EmbeddingService` if needed
3. Git revert to previous commit

## Next Steps

1. Monitor production performance metrics
2. Optimize Pinecone index configurations
3. Fine-tune Groq model parameters for better results
4. Consider adding caching layer for frequent queries
5. Implement retry logic for API failures

---

**Migration Date:** November 2025  
**Status:** ✅ Complete  
**Version:** 1.1.0
