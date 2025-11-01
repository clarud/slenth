# Quick Start Guide
## Internal Rules Ingestion & Testing

---

## 🚀 Quick Setup (3 Steps)

### 1. Set Environment Variables
```bash
export PINECONE_API_KEY="pcsk_xxxxx"
export PINECONE_INTERNAL_INDEX_HOST="https://your-index-xxxxx.svc.pinecone.io"
export OPENAI_API_KEY="sk-xxxxx"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Ingestion
```bash
python scripts/load_internal_rules_pinecone.py
```

**Done!** Your internal rules are now in Pinecone.

---

## 🧪 Quick Test

```bash
# Run all tests
pytest tests/ -v

# Or use the quick test script
chmod +x run_tests.sh
./run_tests.sh
```

---

## 📊 Verify Data

```python
from services.pinecone_db import PineconeService

pinecone = PineconeService(index_type="internal")
stats = pinecone.get_index_stats()
print(f"✅ Total vectors: {stats['total_vectors']}")
```

---

## 🔍 Test Search

```python
from services.pinecone_db import PineconeService
from services.embeddings import EmbeddingService

# Setup
embedding_service = EmbeddingService()
pinecone_service = PineconeService(index_type="internal")

# Query
query = "What are the customer due diligence requirements?"
query_embedding = embedding_service.embed_text(query)
results = pinecone_service.similarity_search(query_embedding, top_k=3)

# Results
for r in results:
    print(f"Score: {r['score']:.3f} | {r['metadata']['passage_ref']}")
    print(f"Text: {r['metadata']['passage_text'][:100]}...")
    print("-" * 70)
```

---

## 📁 File Structure

```
slenth/
├── internal_rules/          # JSON files (1.json - 40.json)
├── scripts/
│   └── load_internal_rules_pinecone.py  # Main ingestion script
├── services/
│   ├── pinecone_db.py      # Pinecone service
│   └── embeddings.py       # OpenAI embeddings
├── tests/
│   ├── test_pinecone_integration.py    # Integration tests
│   └── test_load_internal_rules.py     # Script tests
└── config.py               # Configuration
```

---

## 🎯 Common Commands

### Run Specific Tests
```bash
# Pinecone integration tests
pytest tests/test_pinecone_integration.py -v

# Loading script tests
pytest tests/test_load_internal_rules.py -v

# Specific test class
pytest tests/test_pinecone_integration.py::TestPineconeDataIngestion -v

# Unit tests only (no Pinecone)
pytest tests/ -v -m "unit"
```

### Run with Coverage
```bash
pytest tests/ --cov=services --cov=scripts --cov-report=html
open htmlcov/index.html
```

### Re-run Ingestion
```bash
# Safe to run multiple times (upserts existing vectors)
python scripts/load_internal_rules_pinecone.py
```

---

## 🔧 Troubleshooting

### "Rules directory not found"
```bash
# Check you're in project root
pwd  # Should be: /path/to/slenth
ls internal_rules/  # Should show: 1.json, 2.json, ...
```

### "OpenAI API error"
```bash
# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### "Pinecone connection error"
```bash
# Check environment variables
echo $PINECONE_API_KEY
echo $PINECONE_INTERNAL_INDEX_HOST
```

### Tests failing
```bash
# Install test dependencies
pip install pytest pytest-mock pytest-cov

# Run with verbose output
pytest tests/ -v -s
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `INGESTION_WORKFLOW_GUIDE.md` | Complete workflow explanation |
| `DATA_FORMAT_REFERENCE.md` | Quick reference for data formats |
| `tests/README_TESTING.md` | Comprehensive testing guide |
| `TESTING_IMPLEMENTATION_SUMMARY.md` | Implementation summary |
| `INTERNAL_RULES_WORKFLOW.md` | Detailed workflow documentation |

---

## ✅ Success Checklist

- [ ] Environment variables set (`PINECONE_API_KEY`, `PINECONE_INTERNAL_INDEX_HOST`, `OPENAI_API_KEY`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Internal rules JSON files exist (`internal_rules/*.json`)
- [ ] Ingestion script runs successfully
- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Can query Pinecone and get results

---

## 🎓 What Happens During Ingestion?

```
JSON Files → Parse → Filter Empty → Add Context → Generate Embeddings
    ↓
[0.01, -0.02, ...]  (3072-dim vectors)
    ↓
+ Metadata (passage_ref, document_id, jurisdiction, etc.)
    ↓
Pinecone Upsert (batch of 100)
    ↓
✅ Indexed & Searchable
```

---

## 📊 Expected Output

```
🚀 Loading internal rules to Pinecone vector database...
📁 Found 40 rule files in /path/to/internal_rules
🔧 Initializing services...
📦 Using Pinecone internal index: https://...
📄 Processing: 1.json
   ✅ Prepared 150 passages from 1.json
...
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

---

## ⏱️ Expected Time

- **40 files, ~3500 passages**: 3-10 minutes
- **Per passage**: ~50-200ms (embedding generation)
- **Upsert**: ~100-500ms per 100 vectors

---

## 🔄 Re-running

**Safe to re-run**: The script upserts (updates existing, inserts new) so running multiple times is safe.

```bash
# Run again to update all vectors
python scripts/load_internal_rules_pinecone.py
```

---

## 🚦 Next Steps

1. ✅ Ingest internal rules
2. ✅ Run tests to verify
3. 🔜 Test retrieval agent
4. 🔜 End-to-end transaction processing
5. 🔜 Production deployment

---

**Need Help?** Check `INGESTION_WORKFLOW_GUIDE.md` for detailed explanations.
