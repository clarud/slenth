"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
from qdrant_client import QdrantClient

from db.database import get_db
from config import settings

router = APIRouter()


@router.get("")
async def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check for all system components.
    
    Returns:
        Health status of database, Redis, Qdrant, and overall system
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
        health_status["components"]["postgres"] = {"status": "healthy", "cloud": True}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["postgres"] = {"status": "unhealthy", "error": str(e)}
    
    # Check Redis
    try:
        r = redis.from_url(str(settings.redis_url))
        r.ping()
        health_status["components"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
    
    # Check Qdrant
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        collections = client.get_collections()
        health_status["components"]["qdrant"] = {
            "status": "healthy",
            "collections": len(collections.collections)
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["qdrant"] = {"status": "unhealthy", "error": str(e)}
    
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
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/live")
async def liveness_check():
    """
    Liveness probe for Kubernetes/orchestration.
    
    Returns:
        200 if alive
    """
    return {"status": "alive"}
