# Part 2 Testing Guide

## Quick Start

### Test 1: Direct Agent Testing (No Server Required) ⚡
Tests agents directly without API layer.

```powershell
cd tests\part2
$env:PYTHONIOENCODING="utf-8"
..\..\..\.venv312\Scripts\python.exe test_case_1_pdf.py
```

**Pros:** Fast, no server setup  
**Cons:** Doesn't test API endpoints  
**Time:** ~15 seconds

---

### Test 2: Mock API Workflow Testing (No Server Required) 🎭
Tests complete API flow logic without running server.

```powershell
cd tests\part2
$env:PYTHONIOENCODING="utf-8"
..\..\..\.venv312\Scripts\python.exe test_mock_api_workflow.py
```

**Pros:** Tests API flow without server/database setup  
**Cons:** Doesn't test actual HTTP endpoints  
**Time:** ~15 seconds  
**Use Case:** Validate API logic before server deployment

---

### Test 3: API Endpoint Testing (Requires Server) 🌐
Tests complete production API flow via HTTP.

#### Step 1: Start API Server (Terminal 1)
```powershell
cd slenth
..\.venv312\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Wait for:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

#### Step 2: Run API Test (Terminal 2)
```powershell
cd tests\part2
$env:PYTHONIOENCODING="utf-8"
..\..\..\.venv312\Scripts\python.exe test_api_endpoints.py
```

**Pros:** Tests full production stack  
**Cons:** Requires server + database running  
**Time:** ~20 seconds

---

## Test Comparison

| Feature | Direct Agent | Mock API | Real API |
|---------|--------------|----------|----------|
| **Speed** | Fast (~15s) | Fast (~15s) | Slower (~20s) |
| **Setup** | None | None | Server + DB |
| **Coverage** | Agents only | API logic | Full HTTP stack |
| **Use Case** | Development | Pre-deployment | Production validation |
| **Database** | ❌ Not needed | ❌ Not needed | ✅ Required |
| **Server** | ❌ Not needed | ❌ Not needed | ✅ Required |

---

## Recommended Testing Order

1. **Start with Direct Agent Test** → Verify agents work
2. **Run Mock API Test** → Validate API flow logic
3. **Finally Real API Test** → Confirm HTTP endpoints (after server setup)

---

## Expected Results

Both tests should:
- ✅ Extract text via OCR
- ✅ Detect format issues
- ✅ Find semantic contradictions
- ✅ Detect PDF tampering
- ✅ Identify image tampering
- ✅ Calculate risk score: ~39.1/100 (MEDIUM)
- ✅ Recommend manual review

---

## Troubleshooting

### API Test: "Cannot connect to API server"

**Problem:** Server not running

**Solution:**
```powershell
# Start server first
cd slenth
..\.venv312\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### Test: "ModuleNotFoundError: No module named 'httpx'"

**Problem:** Missing httpx for API tests

**Solution:**
```powershell
..\.venv312\Scripts\python.exe -m pip install httpx
```

### Test: "GROQ_API_KEY not set"

**Problem:** Missing API key in .env

**Solution:** Add to `.env` file:
```
GROQ_API_KEY=your_key_here
```

---

## Next Steps

1. ✅ Run both tests to validate implementation
2. 🔍 Compare results to ensure consistency
3. 📊 Review risk assessment accuracy
4. 🚀 Deploy to production if tests pass
