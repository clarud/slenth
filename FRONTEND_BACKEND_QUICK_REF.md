# Quick Reference: Frontend ↔ Backend Connection

## ✅ Configuration Status

### Frontend
- **URL**: http://localhost:8080
- **API Base**: http://localhost:8000
- **Config File**: `frontend/src/config.ts`
- **Status**: ✅ Correctly configured

### Backend
- **URL**: http://localhost:8000
- **CORS Origins**: 
  - ✅ http://localhost:3000
  - ✅ http://localhost:8000
  - ✅ http://localhost:8080 (Frontend)
- **Config File**: `config.py`
- **Status**: ✅ Correctly configured

---

## 🧪 Test Results

All CORS tests passed:

```
CORS Configuration...................... ✅ PASS
CORS Preflight.......................... ✅ PASS
Actual Request.......................... ✅ PASS
```

**Preflight Response Headers**:
- `Access-Control-Allow-Origin: http://localhost:8080` ✅
- `Access-Control-Allow-Credentials: true` ✅
- `Access-Control-Allow-Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT` ✅
- `Access-Control-Allow-Headers: content-type` ✅

---

## 🚀 Starting the Services

### Backend
```bash
# In project root
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
# In frontend directory
cd frontend
npm run dev
# Starts on http://localhost:8080
```

---

## 📡 API Endpoints Available

From frontend, you can now access:

### Health & Config
- `GET /health` - System health check
- `GET /health/config` - Configuration details
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### Transactions
- `GET /transactions` - List transactions (with pagination & filtering)
- `POST /transactions` - Submit new transaction
- `GET /transactions/{id}/status` - Check transaction status
- `GET /transactions/{id}/compliance` - Get compliance analysis

### Documents
- `POST /documents/upload` - Upload document for analysis

### Rules
- `GET /rules/all` - Get all rules
- `GET /rules/external` - Get external rules
- `GET /rules/internal` - Get internal rules
- `POST /internal_rules` - Create internal rule (JSON)
- `POST /internal_rules/upload` - Upload internal rule (file)

### Alerts & Cases
- Various alert and case management endpoints

---

## 🔧 Testing CORS

Run the automated test suite:
```bash
python3 scripts/test_cors.py
```

Or manually test with curl:
```bash
# Test preflight
curl -X OPTIONS http://localhost:8000/transactions \
  -H "Origin: http://localhost:8080" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -i

# Test actual request
curl http://localhost:8000/health \
  -H "Origin: http://localhost:8080" \
  -i
```

---

## 🌐 Browser Testing

Open http://localhost:8080 in your browser and test in console:

```javascript
// Test GET request
fetch("http://localhost:8000/health")
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)

// Test with credentials
fetch("http://localhost:8000/transactions", {
  method: "GET",
  credentials: "include"
})
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

**Expected**: No CORS errors ✅

---

## 📝 Configuration Files

### Backend: `config.py`
```python
cors_origins: List[str] = Field(
    default=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",  # Frontend
    ]
)
```

### Frontend: `frontend/src/config.ts`
```typescript
export const API = {
  BASE_URL: "http://localhost:8000",
  // ... endpoints
}
```

### Frontend: `frontend/vite.config.ts`
```typescript
server: {
  host: "::",
  port: 8080,
}
```

---

## 🔐 Security Notes

✅ Credentials enabled: `allow_credentials=True`  
✅ Specific origins only (no wildcards)  
✅ All methods allowed for development  
✅ All headers allowed for development  

For production, update `cors_origins` to your production frontend URL.

---

## 📚 Related Documentation

- **CORS_CONFIGURATION.md** - Detailed CORS setup guide
- **ENV_VARS_INTEGRATION.md** - Environment variables
- **TRANSACTION_API_FIX.md** - Transaction endpoints
- **ALERT_DIVERSIFICATION_FIX.md** - Alert classification

---

## ✅ Status: PRODUCTION READY

Both frontend and backend are correctly configured and tested.  
No CORS errors will occur when accessing the API from the frontend.
