#!/usr/bin/env python3
"""
Service Health Checker

Checks if all required services are running for the transaction flow:
- FastAPI Server
- Redis
- Celery Worker
- PostgreSQL
- Pinecone

Usage:
    python scripts/check_services.py
"""

import sys
import logging
import requests
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def check_fastapi(url: str = "http://localhost:8000") -> bool:
    """Check if FastAPI server is running"""
    try:
        response = requests.get(f"{url}/health", timeout=3)
        if response.status_code == 200:
            logger.info("✅ FastAPI Server - Running")
            return True
        else:
            logger.error(f"❌ FastAPI Server - Unhealthy (status: {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ FastAPI Server - Not running")
        logger.info("   Start with: python -m uvicorn app.main:app --reload")
        return False
    except Exception as e:
        logger.error(f"❌ FastAPI Server - Error: {e}")
        return False


def check_redis() -> bool:
    """Check if Redis is running"""
    try:
        result = subprocess.run(
            ["redis-cli", "ping"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0 and "PONG" in result.stdout:
            logger.info("✅ Redis - Running")
            return True
        else:
            logger.error("❌ Redis - Not responding")
            return False
    except FileNotFoundError:
        logger.error("❌ Redis - redis-cli not found")
        logger.info("   Install with: brew install redis")
        return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Redis - Timeout")
        return False
    except Exception as e:
        logger.error(f"❌ Redis - Error: {e}")
        return False


def check_celery() -> bool:
    """Check if Celery worker is running"""
    try:
        # Check via API health endpoint
        response = requests.get("http://localhost:8000/health", timeout=3)
        data = response.json()
        
        # Try to inspect Celery
        result = subprocess.run(
            ["celery", "-A", "worker.celery_app", "inspect", "ping"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(project_root)
        )
        
        if result.returncode == 0 and "pong" in result.stdout.lower():
            logger.info("✅ Celery Worker - Running")
            return True
        else:
            logger.error("❌ Celery Worker - Not running")
            logger.info("   Start with: celery -A worker.celery_app worker --loglevel=info")
            return False
            
    except FileNotFoundError:
        logger.error("❌ Celery - Not installed")
        logger.info("   Install with: pip install celery[redis]")
        return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Celery Worker - Timeout")
        logger.info("   Start with: celery -A worker.celery_app worker --loglevel=info")
        return False
    except Exception as e:
        logger.error(f"❌ Celery Worker - Error: {e}")
        logger.info("   Start with: celery -A worker.celery_app worker --loglevel=info")
        return False


def check_postgresql() -> bool:
    """Check if PostgreSQL database is accessible"""
    try:
        from db.database import SessionLocal
        db = SessionLocal()
        
        # Try a simple query
        result = db.execute("SELECT 1").fetchone()
        db.close()
        
        if result:
            logger.info("✅ PostgreSQL - Connected")
            return True
        else:
            logger.error("❌ PostgreSQL - Query failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ PostgreSQL - Error: {e}")
        logger.info("   Check DATABASE_URL in .env file")
        return False


def check_pinecone() -> bool:
    """Check if Pinecone is accessible"""
    try:
        from services.pinecone_db import PineconeService
        
        # Try to initialize Pinecone service
        pinecone_internal = PineconeService(index_type="internal")
        
        # Try a simple query
        results = pinecone_internal.query_text(
            query_text="test",
            top_k=1
        )
        
        logger.info("✅ Pinecone - Connected")
        return True
        
    except Exception as e:
        logger.error(f"❌ Pinecone - Error: {e}")
        logger.info("   Check PINECONE_API_KEY and PINECONE_INTERNAL_INDEX_HOST in .env")
        return False


def main():
    """Run all health checks"""
    logger.info("\n" + "="*70)
    logger.info("🔧 SERVICE HEALTH CHECK")
    logger.info("="*70 + "\n")
    
    checks = {
        "FastAPI Server": check_fastapi(),
        "Redis": check_redis(),
        "Celery Worker": check_celery(),
        "PostgreSQL": check_postgresql(),
        "Pinecone": check_pinecone(),
    }
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("📊 SUMMARY")
    logger.info("="*70)
    
    passed = sum(checks.values())
    total = len(checks)
    
    for service, status in checks.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"   {status_icon} {service}")
    
    logger.info(f"\n   {passed}/{total} services running")
    
    if passed == total:
        logger.info("\n✅ All services are healthy! Ready to process transactions.")
        logger.info("="*70 + "\n")
        return 0
    else:
        logger.warning(f"\n⚠️  {total - passed} service(s) need attention.")
        logger.info("="*70 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
