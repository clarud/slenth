# Quick Reference: Groq + Pinecone Integration

## Environment Setup

```bash
# Required in .env
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=your_groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1

PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INTERNAL_INDEX_HOST=https://your-internal-index.pinecone.io
PINECONE_EXTERNAL_INDEX_HOST=https://your-external-index.pinecone.io
```

## Usage Examples

### 1. LLM Service (Groq with LangChain)

```python
from services.llm import LLMService

# Initialize (uses Groq by default from config)
llm = LLMService()

# Simple text generation using LCEL pattern
response = await llm.generate(
    prompt="Analyze this transaction for AML risks...",
    temperature=0.3,
    max_tokens=500
)

# Chat completions using LangChain's invoke pattern
response = llm.chat_completion(
    messages=[
        {"role": "system", "content": "You are a compliance analyst"},
        {"role": "user", "content": "Evaluate this transaction..."}
    ],
    temperature=0.3,
    max_tokens=500
)

# Streaming responses
for chunk in llm.chat_completion_stream(
    messages=[{"role": "user", "content": "Analyze this..."}]
):
    print(chunk, end="")
```

**Direct LangChain + Groq Usage:**
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

### 2. Pinecone Service

```python
from services.pinecone_db import PineconeService

# Initialize for internal rules
pinecone = PineconeService(index_type="internal")

# Search using text (Pinecone generates embeddings automatically)
results = pinecone.search_by_text(
    query_text="Hong Kong AML transaction monitoring requirements",
    top_k=10,
    filters={
        "jurisdiction": "HK",
        "is_active": True
    },
    namespace="internal-rules"
)

# Upsert records (Pinecone generates embeddings automatically)
pinecone.upsert_records(
    records=[
        {
            "_id": "rule-001",
            "text": "All transactions over 10,000 require EDD...",
            "metadata": {
                "rule_id": "rule-001",
                "jurisdiction": "HK",
                "severity": "high",
                "is_active": True
            }
        }
    ],
    namespace="internal-rules"
)
```

### 3. Workflow Execution

```python
from workflows.transaction_workflow import execute_transaction_workflow
from services.llm import LLMService
from services.pinecone_db import PineconeService
from db.database import get_db

# Initialize services
llm = LLMService()
pinecone_internal = PineconeService(index_type="internal")
pinecone_external = PineconeService(index_type="external")

# Execute workflow
result = await execute_transaction_workflow(
    transaction={
        "transaction_id": "TXN-12345",
        "amount": 50000,
        "currency": "USD",
        # ... other fields
    },
    db_session=next(get_db()),
    llm_service=llm,
    pinecone_internal=pinecone_internal,
    pinecone_external=pinecone_external
)

# Access results
print(f"Risk Score: {result['risk_score']}")
print(f"Risk Band: {result['risk_band']}")
print(f"Compliance Summary: {result['compliance_summary']}")
```

### 4. Agent Integration

```python
from agents.part1.retrieval import RetrievalAgent
from agents.part1.applicability import ApplicabilityAgent

# Retrieval Agent (uses Pinecone)
retrieval = RetrievalAgent(
    llm_service=llm,
    pinecone_internal=pinecone_internal,
    pinecone_external=pinecone_external
)

state = await retrieval.execute(state)
# state["applicable_rules"] populated

# Applicability Agent (uses Groq LLM)
applicability = ApplicabilityAgent(llm_service=llm)

state = await applicability.execute(state)
# state["applicable_rules_filtered"] populated
```

## Key Differences from Old Implementation

### Before (OpenAI + Separate Embeddings)
```python
# Had to generate embeddings separately
embedding_service = EmbeddingService()
embedding = embedding_service.embed_text(query)

# Then search with vector
results = await vector_db.similarity_search(
    query_vector=embedding,
    top_k=10
)
```

### After (Pinecone Integrated Embeddings)
```python
# Pinecone generates embeddings automatically
results = pinecone.search_by_text(
    query_text=query,
    top_k=10,
    namespace="internal-rules"
)
```

## Testing

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_llm():
    llm = Mock(spec=LLMService)
    llm.generate = AsyncMock(return_value='{"risk": "high"}')
    return llm

@pytest.fixture
def mock_pinecone():
    pc = Mock(spec=PineconeService)
    pc.search_by_text = Mock(return_value=[
        {"rule_id": "R1", "score": 0.95, "text": "..."}
    ])
    return pc

async def test_retrieval(mock_llm, mock_pinecone):
    agent = RetrievalAgent(
        llm_service=mock_llm,
        pinecone_internal=mock_pinecone,
        pinecone_external=mock_pinecone
    )
    
    state = {"query_strings": ["AML requirements"]}
    result = await agent.execute(state)
    
    assert "applicable_rules" in result
    assert len(result["applicable_rules"]) > 0
```

## Performance Tips

### 1. Batch Queries
```python
# Good: Combine related queries
query = "Hong Kong AML requirements for high-value cross-border transactions"

# Avoid: Multiple similar queries
queries = [
    "Hong Kong AML requirements",
    "high-value transactions",
    "cross-border monitoring"
]
```

### 2. Use Appropriate top_k
```python
# For initial search
results = pinecone.search_by_text(query, top_k=10)

# For detailed analysis
results = pinecone.search_by_text(query, top_k=20)

# Avoid excessive results
# results = pinecone.search_by_text(query, top_k=100)  # Too many
```

### 3. Leverage Metadata Filters
```python
# Efficient: Filter at query time
results = pinecone.search_by_text(
    query_text=query,
    top_k=10,
    filters={
        "jurisdiction": "HK",
        "is_active": True,
        "severity": "high"
    }
)

# Less efficient: Filter after retrieval
# results = [r for r in all_results if r["jurisdiction"] == "HK"]
```

### 4. Cache LLM Responses
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_rule_applicability(rule_id: str, transaction_id: str) -> dict:
    # Cache expensive LLM calls
    return llm.generate(prompt)
```

## Troubleshooting

### Groq API Issues
```python
# Check API key
import os
print(f"GROQ_API_KEY set: {bool(os.getenv('GROQ_API_KEY'))}")

# Test connection
from services.llm import LLMService
llm = LLMService()
response = llm.generate("Hello", max_tokens=10)
print(response)  # Should return greeting
```

### Pinecone Connection Issues
```python
# Check API key and hosts
import os
print(f"PINECONE_API_KEY: {bool(os.getenv('PINECONE_API_KEY'))}")
print(f"Internal host: {os.getenv('PINECONE_INTERNAL_INDEX_HOST')}")
print(f"External host: {os.getenv('PINECONE_EXTERNAL_INDEX_HOST')}")

# Test connection
from services.pinecone_db import PineconeService
pc = PineconeService(index_type="internal")
stats = pc.get_index_stats()
print(f"Index stats: {stats}")
```

### Search Returns No Results
```python
# Check if data exists in namespace
stats = pinecone.get_index_stats()
print(f"Namespaces: {stats.get('namespaces')}")

# Try without filters
results = pinecone.search_by_text(
    query_text="test",
    top_k=5,
    namespace="internal-rules"
)
print(f"Results: {len(results)}")
```

## Configuration Reference

### LLM Models (Groq)
- `openai/gpt-oss-20b` (default) - Fast, cost-effective
- `llama-3.1-70b` - Alternative for complex reasoning
- `mixtral-8x7b` - Good balance of speed and quality

### Pinecone Namespaces
- `internal-rules` - Internal compliance rules
- `external-rules` - Regulatory documents (HKMA, MAS, FINMA)

### Response Formats
- `response_format="json"` - For structured outputs
- `response_format=None` - For free-form text

## Best Practices

1. **Always use Pinecone's integrated embeddings** - Don't try to generate embeddings separately
2. **Set appropriate temperature** - 0.0-0.3 for factual tasks, 0.7+ for creative tasks
3. **Use metadata filters** - Reduce search space and improve relevance
4. **Handle errors gracefully** - Both Groq and Pinecone can have transient failures
5. **Monitor token usage** - Track costs with `llm.get_token_stats()`
6. **Validate JSON responses** - LLM may not always return valid JSON

---

**Quick Start:** Copy the environment variables, initialize services, and you're ready to go!
