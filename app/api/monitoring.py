"""
Persistence Monitoring API Endpoints

Provides endpoints to monitor and verify compliance analysis persistence guarantee.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from services.persistence_monitor import get_persistence_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/persistence/health")
async def get_persistence_health(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get overall health status of compliance analysis persistence system.
    
    Returns:
        Health status report including integrity checks and statistics
    """
    try:
        monitor = get_persistence_monitor(db)
        health = monitor.get_health_status()
        return health
    except Exception as e:
        logger.error(f"Error getting persistence health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/persistence/integrity")
async def check_persistence_integrity(
    lookback_hours: int = Query(24, ge=1, le=168, description="Hours to look back (1-168)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check integrity of compliance analysis persistence.
    
    Verifies that all COMPLETED transactions have ComplianceAnalysis records.
    
    Args:
        lookback_hours: How many hours back to check (default 24, max 168)
        
    Returns:
        Integrity report with violation details if any
    """
    try:
        monitor = get_persistence_monitor(db)
        report = monitor.check_persistence_integrity(lookback_hours=lookback_hours)
        return report
    except Exception as e:
        logger.error(f"Error checking persistence integrity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/persistence/stats")
async def get_persistence_statistics(
    lookback_hours: int = Query(24, ge=1, le=168, description="Hours to analyze (1-168)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed persistence statistics.
    
    Args:
        lookback_hours: How many hours back to analyze (default 24, max 168)
        
    Returns:
        Detailed statistics about transaction processing and persistence
    """
    try:
        monitor = get_persistence_monitor(db)
        stats = monitor.get_persistence_stats(lookback_hours=lookback_hours)
        return stats
    except Exception as e:
        logger.error(f"Error getting persistence stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/persistence/verify/{transaction_id}")
async def verify_transaction_persistence(
    transaction_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verify a specific transaction has compliance analysis.
    
    Args:
        transaction_id: Transaction ID to verify
        
    Returns:
        Verification report for the transaction
    """
    try:
        monitor = get_persistence_monitor(db)
        verification = monitor.verify_transaction_compliance(transaction_id)
        
        if verification["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return verification
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying transaction persistence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
