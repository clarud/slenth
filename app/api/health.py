"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
from db.database import get_db
from config import settings

router = APIRouter()


def _mask_sensitive_value(value: str) -> str:
    """Mask sensitive configuration values."""
    if not value:
        return "not_set"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _mask_url(url: str) -> str:
    """Mask credentials in URLs."""
    try:
        url_str = str(url)
        if "@" in url_str and "://" in url_str:
            scheme, rest = url_str.split("://", 1)
            if "@" in rest:
                creds, host = rest.split("@", 1)
                return f"{scheme}://***:***@{host}"
        return url_str
    except Exception:
        return str(url)


@router.get("")
async def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check for all system components.
    
    Returns:
        Health status of database, Redis, Pinecone, Celery, and overall system
    """
    health_status = {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.app_env,
        "components": {}
    }
    
    # Check PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["postgres"] = {
            "status": "healthy",
            "url": _mask_url(settings.database_url)
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["postgres"] = {
            "status": "unhealthy",
            "error": str(e),
            "url": _mask_url(settings.database_url)
        }
    
    # Check Redis
    try:
        r = redis.from_url(str(settings.redis_url))
        r.ping()
        health_status["components"]["redis"] = {
            "status": "healthy",
            "url": _mask_url(settings.redis_url)
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
            "url": _mask_url(settings.redis_url)
        }
    
    # Check Celery Broker
    try:
        r = redis.from_url(str(settings.celery_broker_url))
        r.ping()
        health_status["components"]["celery_broker"] = {
            "status": "healthy",
            "url": _mask_url(settings.celery_broker_url)
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["celery_broker"] = {
            "status": "unhealthy",
            "error": str(e),
            "url": _mask_url(settings.celery_broker_url)
        }
    
    # Check Pinecone Configuration
    pinecone_status = {
        "api_key": _mask_sensitive_value(settings.pinecone_api_key),
        "internal_index_host": settings.pinecone_internal_index_host,
        "external_index_host": settings.pinecone_external_index_host,
        "provider": settings.vector_db_provider
    }
    
    # Verify Pinecone connectivity (basic check)
    try:
        from services.pinecone_db import PineconeService
        pinecone_service = PineconeService()
        # If initialization doesn't throw, consider it healthy
        pinecone_status["status"] = "healthy"
        health_status["components"]["pinecone"] = pinecone_status
    except Exception as e:
        pinecone_status["status"] = "unhealthy"
        pinecone_status["error"] = str(e)
        health_status["components"]["pinecone"] = pinecone_status
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe for Kubernetes/orchestration.
    
    Returns:
        200 if ready, 503 if not ready
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/live")
async def liveness_check():
    """
    Liveness probe for Kubernetes/orchestration.
    
    Returns:
        200 if alive
    """
    return {"status": "alive"}


@router.get("/config")
async def config_info():
    """
    Get application configuration information (with sensitive data masked).
    
    Returns:
        Configuration details for database, Redis, Pinecone, Celery, and other services
    """
    return {
        "environment": settings.app_env,
        "version": settings.app_version,
        "debug": settings.debug,
        "database": {
            "url": _mask_url(settings.database_url),
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow
        },
        "redis": {
            "url": _mask_url(settings.redis_url),
            "max_connections": settings.redis_max_connections
        },
        "celery": {
            "broker_url": _mask_url(settings.celery_broker_url),
            "result_backend": _mask_url(settings.celery_result_backend),
            "worker_concurrency": settings.celery_worker_concurrency
        },
        "pinecone": {
            "api_key": _mask_sensitive_value(settings.pinecone_api_key),
            "internal_index_host": settings.pinecone_internal_index_host,
            "external_index_host": settings.pinecone_external_index_host,
            "provider": settings.vector_db_provider
        },
        "llm": {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "groq_api_key": _mask_sensitive_value(settings.groq_api_key) if settings.groq_api_key else "not_set",
            "openai_api_key": _mask_sensitive_value(settings.openai_api_key) if settings.openai_api_key else "not_set"
        },
        "embeddings": {
            "provider": settings.embeddings_provider,
            "model": settings.embedding_model,
            "dimension": settings.embedding_dimension
        },
        "api": {
            "host": settings.api_host,
            "port": settings.api_port,
            "cors_origins": settings.cors_origins
        },
        "features": {
            "background_check": settings.enable_background_check,
            "image_forensics": settings.enable_image_forensics,
            "ai_detection": settings.enable_ai_detection,
            "metrics": settings.enable_metrics,
            "tracing": settings.enable_tracing
        }
    }
