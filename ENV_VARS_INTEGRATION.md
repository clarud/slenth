# Environment Variables Integration

## Overview

All environment variables are now properly linked to FastAPI routes through the centralized configuration system. The application uses Pydantic settings management for type-safe configuration.

## Configuration System

### Location
- **Config File**: `config.py`
- **Settings Class**: `Settings` (based on `pydantic_settings.BaseSettings`)
- **Global Instance**: `settings` (imported from `config.py`)

### Environment Variables Exposed

#### Core Infrastructure

1. **DATABASE_URL**
   - Type: `PostgresDsn`
   - Used by: Database connection, health checks
   - Exposed in: `/health`, `/health/config`
   - Format: `postgresql://user:pass@host:port/dbname`

2. **REDIS_URL**
   - Type: `RedisDsn`
   - Used by: Caching, session management
   - Exposed in: `/health`, `/health/config`
   - Format: `redis://user:pass@host:port/db`

3. **CELERY_BROKER_URL**
   - Type: `RedisDsn`
   - Used by: Celery task queue
   - Exposed in: `/health`, `/health/config`
   - Format: `redis://user:pass@host:port/db`

4. **CELERY_RESULT_BACKEND**
   - Type: `RedisDsn`
   - Used by: Celery result storage
   - Exposed in: `/health/config`
   - Format: `redis://user:pass@host:port/db`

#### Pinecone Vector Database

5. **PINECONE_API_KEY**
   - Type: `str`
   - Used by: PineconeService for authentication
   - Exposed in: `/health`, `/health/config` (masked)
   - Security: Always masked in API responses

6. **PINECONE_INTERNAL_INDEX_HOST**
   - Type: `str`
   - Used by: Internal rules vector index
   - Exposed in: `/health`, `/health/config`
   - Format: `https://your-index-host.pinecone.io`

7. **PINECONE_EXTERNAL_INDEX_HOST**
   - Type: `str`
   - Used by: External rules vector index
   - Exposed in: `/health`, `/health/config`
   - Format: `https://your-index-host.pinecone.io`

## API Endpoints

### Health Check Endpoints

#### 1. `/health` - Comprehensive Health Check
```json
GET /health

Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "components": {
    "postgres": {
      "status": "healthy",
      "url": "postgresql://***:***@host:5432/db"
    },
    "redis": {
      "status": "healthy",
      "url": "redis://***:***@host:6379/0"
    },
    "celery_broker": {
      "status": "healthy",
      "url": "redis://***:***@host:6379/0"
    },
    "pinecone": {
      "status": "healthy",
      "api_key": "sk-pr...key",
      "internal_index_host": "https://internal-host.pinecone.io",
      "external_index_host": "https://external-host.pinecone.io",
      "provider": "pinecone"
    }
  }
}
```

#### 2. `/health/ready` - Readiness Probe
```json
GET /health/ready

Response:
{
  "status": "ready"
}
```

#### 3. `/health/live` - Liveness Probe
```json
GET /health/live

Response:
{
  "status": "alive"
}
```

#### 4. `/health/config` - Configuration Information (NEW)
```json
GET /health/config

Response:
{
  "environment": "development",
  "version": "1.0.0",
  "debug": true,
  "database": {
    "url": "postgresql://***:***@host:5432/db",
    "pool_size": 20,
    "max_overflow": 10
  },
  "redis": {
    "url": "redis://***:***@host:6379/0",
    "max_connections": 50
  },
  "celery": {
    "broker_url": "redis://***:***@host:6379/0",
    "result_backend": "redis://***:***@host:6379/0",
    "worker_concurrency": 4
  },
  "pinecone": {
    "api_key": "sk-pr...key",
    "internal_index_host": "https://internal-host.pinecone.io",
    "external_index_host": "https://external-host.pinecone.io",
    "provider": "pinecone"
  },
  "llm": {
    "provider": "groq",
    "model": "llama3-70b-8192",
    "groq_api_key": "gsk_...key",
    "openai_api_key": "not_set"
  },
  "embeddings": {
    "provider": "openai",
    "model": "text-embedding-3-large",
    "dimension": 3072
  },
  "api": {
    "host": "0.0.0.0",
    "port": 8000,
    "cors_origins": ["http://localhost:3000", "http://localhost:8000"]
  },
  "features": {
    "background_check": true,
    "image_forensics": true,
    "ai_detection": true,
    "metrics": true,
    "tracing": false
  }
}
```

## Security Features

### Sensitive Data Masking

All sensitive configuration values are automatically masked in API responses:

1. **API Keys**: `sk-proj-abc123...xyz789` → `sk-pr...789`
2. **Database URLs**: `postgresql://user:pass@host/db` → `postgresql://***:***@host/db`
3. **Redis URLs**: `redis://user:pass@host/db` → `redis://***:***@host/db`

### Masking Functions

```python
def _mask_sensitive_value(value: str) -> str:
    """Mask sensitive configuration values."""
    if not value:
        return "not_set"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"

def _mask_url(url: str) -> str:
    """Mask credentials in URLs."""
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            creds, host = rest.split("@", 1)
            return f"{scheme}://***:***@{host}"
    return url
```

## Service Integration

### Services Using Configuration

1. **PineconeService** (`services/pinecone_db.py`)
   - Uses: `PINECONE_API_KEY`, `PINECONE_INTERNAL_INDEX_HOST`, `PINECONE_EXTERNAL_INDEX_HOST`
   - Purpose: Vector database operations for internal and external rules

2. **Database** (`db/database.py`)
   - Uses: `DATABASE_URL`, `database_pool_size`, `database_max_overflow`
   - Purpose: PostgreSQL connection management

3. **Celery** (`worker/celery_app.py`)
   - Uses: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
   - Purpose: Asynchronous task processing

4. **Redis** (various services)
   - Uses: `REDIS_URL`, `redis_max_connections`
   - Purpose: Caching and session storage

## Files Modified

### 1. `app/api/health.py`
- Added `/health/config` endpoint
- Enhanced `/health` endpoint with component details
- Added masking functions for sensitive data
- Added Pinecone connectivity check
- Added Celery broker health check

### 2. `config.py`
- Already configured with all environment variables
- Uses Pydantic settings for type safety
- Loads from `.env` file automatically

### 3. `app/main.py`
- Already imports and uses `settings` from config
- Exposes configuration through health endpoints

## Usage Examples

### Check Application Health
```bash
curl http://localhost:8000/health
```

### View Configuration
```bash
curl http://localhost:8000/health/config
```

### Test Pinecone Connectivity
```bash
curl http://localhost:8000/health | jq '.components.pinecone'
```

### Verify All Environment Variables
```python
from config import settings

print(f"Database: {settings.database_url}")
print(f"Redis: {settings.redis_url}")
print(f"Celery: {settings.celery_broker_url}")
print(f"Pinecone API: {settings.pinecone_api_key}")
print(f"Internal Index: {settings.pinecone_internal_index_host}")
print(f"External Index: {settings.pinecone_external_index_host}")
```

## Environment File Template

Create a `.env` file in the project root:

```bash
# Application
APP_ENV=development
APP_NAME="SLENTH AML Monitor"
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/slenth

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INTERNAL_INDEX_HOST=https://your-internal-index-host.pinecone.io
PINECONE_EXTERNAL_INDEX_HOST=https://your-external-index-host.pinecone.io

# LLM
GROQ_API_KEY=your-groq-api-key
OPENAI_API_KEY=your-openai-api-key

# API
API_HOST=0.0.0.0
API_PORT=8000
```

## Testing

### Test Configuration Loading
```python
import pytest
from config import settings

def test_database_url():
    assert settings.database_url is not None
    assert "postgresql://" in str(settings.database_url)

def test_pinecone_config():
    assert settings.pinecone_api_key is not None
    assert settings.pinecone_internal_index_host is not None
    assert settings.pinecone_external_index_host is not None
```

### Test Health Endpoint
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "components" in data
    assert "pinecone" in data["components"]

def test_config_endpoint():
    response = client.get("/health/config")
    assert response.status_code == 200
    data = response.json()
    assert "pinecone" in data
    assert "api_key" in data["pinecone"]
    # Verify masking
    assert "***" in data["pinecone"]["api_key"] or "not_set" in data["pinecone"]["api_key"]
```

## Benefits

1. **Centralized Configuration**: All environment variables in one place
2. **Type Safety**: Pydantic validates configuration at startup
3. **Security**: Sensitive data automatically masked in API responses
4. **Observability**: Health checks verify connectivity to all services
5. **Debugging**: `/health/config` endpoint helps diagnose configuration issues
6. **Production Ready**: Supports Kubernetes readiness/liveness probes

## Next Steps

1. Set up environment variables in your deployment environment
2. Test health endpoints to verify connectivity
3. Monitor `/health` endpoint for system status
4. Use `/health/config` for debugging configuration issues
5. Implement monitoring/alerting based on health check responses
