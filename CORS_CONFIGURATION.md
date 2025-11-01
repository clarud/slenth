# CORS Configuration - Frontend & Backend

**Date**: 2025-11-02  
**Status**: ✅ CONFIGURED

---

## Overview

This document describes the CORS (Cross-Origin Resource Sharing) configuration between the frontend and backend services.

---

## Configuration Summary

### Frontend
- **Framework**: React + Vite
- **Dev Server URL**: `http://localhost:8080`
- **API Base URL**: `http://localhost:8000`
- **Configuration File**: `frontend/vite.config.ts`

### Backend
- **Framework**: FastAPI
- **API Server URL**: `http://localhost:8000`
- **CORS Origins Allowed**: 
  - `http://localhost:3000` (legacy/alternative frontend port)
  - `http://localhost:8000` (backend self)
  - `http://localhost:8080` (frontend Vite dev server) ✅ **NEW**
- **Configuration File**: `config.py`

---

## Frontend Configuration

### Vite Config (`frontend/vite.config.ts`)
```typescript
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,  // Frontend runs on port 8080
  },
  // ... other config
}));
```

### API Configuration (`frontend/src/config.ts`)
```typescript
export const API = {
  BASE_URL: "http://localhost:8000",  // Points to FastAPI backend
  
  // Endpoints
  LIST_TRANSACTIONS_PATH: "/transactions",
  TRANSACTION_STATUS_PATH: (id: string) => `/transactions/${id}/status`,
  TRANSACTION_COMPLIANCE_PATH: (id: string) => `/transactions/${id}/compliance`,
  DOCUMENT_UPLOAD_PATH: "/documents/upload",
  RULES_ALL_PATH: "/rules/all",
  RULES_EXTERNAL_PATH: "/rules/external",
  RULES_INTERNAL_PATH: "/rules/internal",
  INTERNAL_RULES_TEXT_PATH: "/internal_rules",
  INTERNAL_RULES_UPLOAD_PATH: "/internal_rules/upload",
} as const;
```

---

## Backend Configuration

### CORS Settings (`config.py`)
```python
class Settings(BaseSettings):
    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_reload: bool = Field(default=True)
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",      # Legacy/alternative frontend
            "http://localhost:8000",      # Backend self (for testing)
            "http://localhost:8080",      # Frontend Vite dev server ✅
        ]
    )
```

### CORS Middleware (`app/main.py`)
```python
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## How It Works

1. **Frontend Makes Request**
   ```typescript
   // In frontend code
   fetch("http://localhost:8000/transactions")
   ```

2. **Browser Checks CORS**
   - Browser sees request is cross-origin (8080 → 8000)
   - Browser sends preflight OPTIONS request (for POST/PUT/DELETE)
   - Browser includes `Origin: http://localhost:8080` header

3. **Backend Responds with CORS Headers**
   ```
   Access-Control-Allow-Origin: http://localhost:8080
   Access-Control-Allow-Credentials: true
   Access-Control-Allow-Methods: *
   Access-Control-Allow-Headers: *
   ```

4. **Browser Allows Request**
   - If origin matches allowed list, request proceeds
   - If not, browser blocks and shows CORS error

---

## Testing CORS Configuration

### Test 1: Frontend Can Access Backend
```bash
# Start backend
cd /Users/chenxiangrui/Projects/slenth
uvicorn app.main:app --reload --port 8000

# Start frontend (in another terminal)
cd frontend
npm run dev
# Opens at http://localhost:8080

# Test in browser console (at http://localhost:8080)
fetch("http://localhost:8000/health")
  .then(r => r.json())
  .then(console.log)
```

**Expected**: ✅ Request succeeds, no CORS errors

### Test 2: Preflight Request
```bash
# Simulate OPTIONS preflight request
curl -X OPTIONS http://localhost:8000/transactions \
  -H "Origin: http://localhost:8080" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -v
```

**Expected Output**:
```
< HTTP/1.1 200 OK
< access-control-allow-origin: http://localhost:8080
< access-control-allow-credentials: true
< access-control-allow-methods: *
< access-control-allow-headers: *
```

### Test 3: Actual Request from Frontend
```bash
# From http://localhost:8080 browser console
fetch("http://localhost:8000/transactions", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  credentials: "include",
  body: JSON.stringify({
    transaction_id: "test-123",
    amount: 1000.00,
    currency: "USD",
    originator_country: "US",
    beneficiary_country: "UK"
  })
})
.then(r => r.json())
.then(console.log)
.catch(console.error)
```

**Expected**: ✅ Transaction accepted, no CORS errors

---

## Common CORS Errors and Solutions

### Error: "has been blocked by CORS policy"
**Symptom**:
```
Access to fetch at 'http://localhost:8000/transactions' from origin 'http://localhost:8080' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
```

**Solution**:
1. ✅ Verify `http://localhost:8080` is in `cors_origins` list
2. ✅ Restart backend server after config change
3. ✅ Clear browser cache and reload

### Error: "credentials mode 'include'"
**Symptom**:
```
Credentials flag is 'true', but the 'Access-Control-Allow-Credentials' header is ''
```

**Solution**:
1. ✅ Ensure `allow_credentials=True` in CORS middleware (already set)
2. ✅ Use `credentials: "include"` in frontend fetch

### Error: Preflight request doesn't pass
**Symptom**: OPTIONS request returns 403 or missing headers

**Solution**:
1. ✅ Ensure `allow_methods=["*"]` in CORS middleware (already set)
2. ✅ Ensure `allow_headers=["*"]` in CORS middleware (already set)

---

## Production Configuration

For production deployment, update CORS origins:

```python
# config.py - Production
cors_origins: List[str] = Field(
    default=[
        "https://yourdomain.com",
        "https://app.yourdomain.com",
        "http://localhost:8080",  # Keep for local development
    ]
)
```

Or use environment variable:
```bash
export CORS_ORIGINS='["https://yourdomain.com","https://app.yourdomain.com"]'
```

---

## Security Considerations

1. **Wildcard Origins**: Never use `allow_origins=["*"]` with `allow_credentials=True`
2. **HTTPS in Production**: Always use HTTPS for production origins
3. **Specific Origins**: List specific allowed origins, not wildcards
4. **Credentials**: Only enable credentials if needed for authentication

---

## Verification Checklist

- ✅ Frontend runs on `http://localhost:8080`
- ✅ Frontend API config points to `http://localhost:8000`
- ✅ Backend CORS allows `http://localhost:8080`
- ✅ CORS middleware configured with credentials, methods, headers
- ✅ Both servers can be started simultaneously
- ⏳ **TODO**: Test end-to-end request from frontend to backend

---

## Related Documentation

- See `ENV_VARS_INTEGRATION.md` for environment configuration
- See `TRANSACTION_API_FIX.md` for transaction endpoints
- See FastAPI CORS docs: https://fastapi.tiangolo.com/tutorial/cors/

---

## Status: READY FOR TESTING ✅

CORS is now properly configured. Start both servers and test the integration:

```bash
# Terminal 1: Backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Then open `http://localhost:8080` and verify API calls work without CORS errors.
