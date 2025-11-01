# Quick Setup Guide - Internal Rules Ingestion

## 🚀 Simplified Standalone Script

The loading script (`scripts/load_internal_rules_pinecone.py`) is now **completely standalone** and doesn't require the full SLENTH config.

---

## 📋 Prerequisites

### 1. Environment Variables (Required)

Set these two environment variables:

```bash
export PINECONE_API_KEY="pcsk_your-api-key-here"
export PINECONE_INTERNAL_INDEX_HOST="https://your-index-xxxxx.svc.pinecone.io"
```

### 2. JSON Files (Already Present)

Ensure `internal_rules/*.json` files exist (you already have these)

### 3. Dependencies

```bash
pip install pinecone-client
```

---

## ✅ Run the Ingestion

### Option 1: Export Variables Then Run

```bash
# Set environment variables
export PINECONE_API_KEY="pcsk_your-key"
export PINECONE_INTERNAL_INDEX_HOST="https://your-host.svc.pinecone.io"

# Run ingestion
python scripts/load_internal_rules_pinecone.py
```

### Option 2: One-Liner

```bash
PINECONE_API_KEY="your-key" \
PINECONE_INTERNAL_INDEX_HOST="https://your-host" \
python scripts/load_internal_rules_pinecone.py
```

### Option 3: Use the Setup Script

```bash
# Edit scripts/setup_and_run.sh with your credentials
nano scripts/setup_and_run.sh

# Make it executable
chmod +x scripts/setup_and_run.sh

# Run it
./scripts/setup_and_run.sh
```

---

## 📊 Expected Output

```
2025-11-01 15:48:34,612 - INFO - 🚀 Loading internal rules to Pinecone vector database...
2025-11-01 15:48:34,650 - INFO - 📁 Found 40 rule files in /path/to/internal_rules
2025-11-01 15:48:34,700 - INFO - 🔧 Initializing Pinecone service...
2025-11-01 15:48:35,100 - INFO - 📦 Using Pinecone internal index: https://your-host
2025-11-01 15:48:35,100 - INFO - 📝 Using Pinecone's built-in embedding model (no OpenAI required)
2025-11-01 15:48:35,200 - INFO - 📄 Processing: 1.json
2025-11-01 15:48:35,250 - INFO -    ✅ Prepared 150 passages from 1.json
...
2025-11-01 15:50:45,800 - INFO - 🚀 Upserting 3500 records to Pinecone...
2025-11-01 15:50:45,800 - INFO -    Pinecone will generate embeddings using its inference API
2025-11-01 15:51:10,500 - INFO -    ✅ Upserted batch 1/35
2025-11-01 15:51:12,300 - INFO -    ✅ Upserted batch 2/35
...
2025-11-01 15:53:20,100 - INFO - 💾 Successfully upserted 3500 rules to Pinecone
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

## 🔍 What the Script Does

1. **Reads** JSON files from `internal_rules/` directory
2. **Parses** each passage object `{ID, DocumentID, PassageID, Passage}`
3. **Filters** empty passages automatically
4. **Prepares** text with context: `"Document X - PassageID: Text"`
5. **Creates** records with `{_id, text, metadata}`
6. **Upserts** to Pinecone (Pinecone generates embeddings automatically)
7. **Reports** summary statistics

---

## 🎯 Key Features

✅ **No OpenAI needed** - Pinecone generates embeddings  
✅ **No config.py dependency** - Standalone script  
✅ **Simple setup** - Just 2 environment variables  
✅ **Batch processing** - Efficient 100-record batches  
✅ **Progress logging** - See what's happening  
✅ **Error handling** - Clear error messages  

---

## ❓ Troubleshooting

### Error: "PINECONE_API_KEY environment variable not set"

```bash
# Make sure to export the variable
export PINECONE_API_KEY="your-key"

# Verify it's set
echo $PINECONE_API_KEY
```

### Error: "PINECONE_INTERNAL_INDEX_HOST environment variable not set"

```bash
# Set the host URL (get from Pinecone dashboard)
export PINECONE_INTERNAL_INDEX_HOST="https://your-index-abc123.svc.pinecone.io"

# Verify it's set
echo $PINECONE_INTERNAL_INDEX_HOST
```

### Error: "Rules directory not found"

```bash
# Make sure you're running from project root
cd /Users/chenxiangrui/Projects/slenth

# Check directory exists
ls -la internal_rules/
```

### Error: "No JSON files found"

```bash
# Check files exist
ls internal_rules/*.json

# Should see: 1.json, 2.json, ..., 40.json
```

---

## 🔐 Security Note

**Never commit API keys to git!**

Use environment variables or a `.env` file (add to `.gitignore`):

```bash
# Create .env file
cat > .env.internal_rules << EOF
PINECONE_API_KEY=your-key
PINECONE_INTERNAL_INDEX_HOST=your-host
EOF

# Load variables
source .env.internal_rules

# Run script
python scripts/load_internal_rules_pinecone.py
```

---

## 📚 Next Steps

After successful ingestion:

1. **Test search**:
   ```python
   from pinecone import Pinecone
   import os
   
   pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
   index = pc.Index(host=os.getenv("PINECONE_INTERNAL_INDEX_HOST"))
   
   results = index.search(
       namespace="",
       query={"inputs": {"text": "customer due diligence"}, "top_k": 3},
       fields=["*"]
   )
   
   for match in results['matches']:
       print(f"Score: {match['score']:.3f}")
       print(f"Ref: {match['metadata']['passage_ref']}")
       print(f"Text: {match['metadata']['passage_text'][:100]}...")
       print("-" * 70)
   ```

2. **Update retrieval agent** to use `search_by_text()`

3. **Run end-to-end tests** with the full system

---

## 💡 Pro Tips

1. **Check index stats** before running to see current count
2. **Safe to re-run** - upserts will update existing records
3. **Monitor Pinecone dashboard** for usage and performance
4. **Use batching** - already built-in (100 per batch)

---

**Ready to go!** Just set your environment variables and run the script. 🚀
