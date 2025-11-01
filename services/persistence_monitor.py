"""
Persistence Monitoring Service

Tracks and monitors compliance analysis persistence to ensure the guarantee is maintained.
Provides metrics, alerts, and health checks for the persistence layer.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class PersistenceMonitor:
    """Monitor compliance analysis persistence and track guarantee compliance"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def check_persistence_integrity(
        self,
        lookback_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Check if all completed transactions have compliance analysis.
        
        Args:
            lookback_hours: How far back to check (default 24 hours)
            
        Returns:
            Report with integrity status and any violations
        """
        from db.models import Transaction, ComplianceAnalysis, TransactionStatus
        
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        # Count completed transactions
        completed_count = self.db.query(Transaction).filter(
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.processing_completed_at >= cutoff_time
        ).count()
        
        # Count completed transactions WITHOUT compliance analysis
        violations = self.db.query(Transaction).outerjoin(
            ComplianceAnalysis,
            Transaction.id == ComplianceAnalysis.transaction_id
        ).filter(
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.processing_completed_at >= cutoff_time,
            ComplianceAnalysis.id == None  # NULL check
        ).all()
        
        violation_count = len(violations)
        
        # Calculate metrics
        integrity_rate = (
            ((completed_count - violation_count) / completed_count * 100)
            if completed_count > 0
            else 100.0
        )
        
        report = {
            "status": "healthy" if violation_count == 0 else "violated",
            "lookback_hours": lookback_hours,
            "total_completed": completed_count,
            "with_compliance_analysis": completed_count - violation_count,
            "violations": violation_count,
            "integrity_rate_percent": round(integrity_rate, 2),
            "checked_at": datetime.utcnow().isoformat(),
        }
        
        if violations:
            report["violation_details"] = [
                {
                    "transaction_id": v.transaction_id,
                    "completed_at": v.processing_completed_at.isoformat() if v.processing_completed_at else None,
                    "status": v.status.value if hasattr(v.status, 'value') else str(v.status)
                }
                for v in violations[:10]  # Limit to first 10
            ]
            
            logger.error(
                f"⚠️  PERSISTENCE GUARANTEE VIOLATED: {violation_count} completed transactions "
                f"missing ComplianceAnalysis in last {lookback_hours} hours"
            )
        else:
            logger.info(
                f"✅ Persistence integrity check PASSED: All {completed_count} completed transactions "
                f"have ComplianceAnalysis (last {lookback_hours} hours)"
            )
        
        return report

    def get_persistence_stats(
        self,
        lookback_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get detailed persistence statistics.
        
        Args:
            lookback_hours: How far back to analyze
            
        Returns:
            Detailed statistics report
        """
        from db.models import Transaction, ComplianceAnalysis, TransactionStatus
        
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        # Query transaction counts by status
        status_counts = {}
        for status in TransactionStatus:
            count = self.db.query(Transaction).filter(
                Transaction.status == status,
                Transaction.created_at >= cutoff_time
            ).count()
            status_counts[status.value] = count
        
        # Count compliance analyses created
        analysis_count = self.db.query(ComplianceAnalysis).join(
            Transaction,
            ComplianceAnalysis.transaction_id == Transaction.id
        ).filter(
            Transaction.created_at >= cutoff_time
        ).count()
        
        # Calculate average processing time
        avg_processing_time = self.db.query(
            func.avg(ComplianceAnalysis.processing_time_seconds)
        ).join(
            Transaction,
            ComplianceAnalysis.transaction_id == Transaction.id
        ).filter(
            Transaction.created_at >= cutoff_time
        ).scalar() or 0.0
        
        # Failed transactions (should have no compliance analysis)
        failed_count = status_counts.get("failed", 0)
        
        return {
            "lookback_hours": lookback_hours,
            "transactions_by_status": status_counts,
            "total_transactions": sum(status_counts.values()),
            "compliance_analyses_created": analysis_count,
            "average_processing_time_seconds": round(avg_processing_time, 2),
            "expected_analyses": status_counts.get("completed", 0),
            "persistence_rate_percent": round(
                (analysis_count / status_counts.get("completed", 1)) * 100, 2
            ) if status_counts.get("completed", 0) > 0 else 0.0,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def verify_transaction_compliance(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:
        """
        Verify a specific transaction has compliance analysis.
        
        Args:
            transaction_id: Transaction ID to check
            
        Returns:
            Verification report
        """
        from db.models import Transaction, ComplianceAnalysis, TransactionStatus
        
        transaction = self.db.query(Transaction).filter(
            Transaction.transaction_id == transaction_id
        ).first()
        
        if not transaction:
            return {
                "transaction_id": transaction_id,
                "status": "not_found",
                "message": "Transaction not found in database"
            }
        
        compliance = self.db.query(ComplianceAnalysis).filter(
            ComplianceAnalysis.transaction_id == transaction.id
        ).first()
        
        has_compliance = compliance is not None
        
        # Check if it should have compliance
        should_have_compliance = transaction.status == TransactionStatus.COMPLETED
        
        status = "ok"
        if should_have_compliance and not has_compliance:
            status = "violation"
        elif not should_have_compliance:
            status = "pending" if transaction.status == TransactionStatus.PROCESSING else "expected"
        
        return {
            "transaction_id": transaction_id,
            "transaction_status": transaction.status.value if hasattr(transaction.status, 'value') else str(transaction.status),
            "has_compliance_analysis": has_compliance,
            "compliance_analysis_id": str(compliance.id) if compliance else None,
            "should_have_compliance": should_have_compliance,
            "verification_status": status,
            "risk_score": compliance.compliance_score if compliance else None,
            "risk_band": compliance.risk_band.value if compliance and hasattr(compliance.risk_band, 'value') else None,
            "processing_time_seconds": compliance.processing_time_seconds if compliance else None,
            "checked_at": datetime.utcnow().isoformat(),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of persistence system.
        
        Returns:
            Health status report
        """
        try:
            # Check last hour for quick health status
            integrity = self.check_persistence_integrity(lookback_hours=1)
            stats = self.get_persistence_stats(lookback_hours=1)
            
            is_healthy = (
                integrity["status"] == "healthy" and
                stats["persistence_rate_percent"] >= 99.0  # Allow 1% error margin
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "integrity_check": integrity,
                "statistics": stats,
                "checked_at": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error checking persistence health: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat(),
            }


# Singleton instance (optional, for convenience)
_monitor_instance: Optional[PersistenceMonitor] = None


def get_persistence_monitor(db_session: Session) -> PersistenceMonitor:
    """Get or create persistence monitor instance"""
    return PersistenceMonitor(db_session)
