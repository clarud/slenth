#!/usr/bin/env python3
"""
Test script to verify compliance analysis persistence guarantee.

This script tests all the layers of the persistence guarantee system.
"""

import asyncio
import sys
from datetime import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, "/Users/chenxiangrui/Projects/slenth")

from db.database import SessionLocal
from db.models import Transaction, ComplianceAnalysis, TransactionStatus
from services.persistence_monitor import get_persistence_monitor


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_monitoring_service(db: Session):
    """Test the persistence monitoring service"""
    print_section("TEST 1: Persistence Monitoring Service")
    
    monitor = get_persistence_monitor(db)
    
    # Test 1: Health check
    print("1. Testing health check...")
    health = monitor.get_health_status()
    print(f"   Status: {health['status']}")
    print(f"   ✅ Health check working\n")
    
    # Test 2: Integrity check
    print("2. Testing integrity check (last 24 hours)...")
    integrity = monitor.check_persistence_integrity(lookback_hours=24)
    print(f"   Status: {integrity['status']}")
    print(f"   Total completed: {integrity['total_completed']}")
    print(f"   With compliance: {integrity['with_compliance_analysis']}")
    print(f"   Violations: {integrity['violations']}")
    print(f"   Integrity rate: {integrity['integrity_rate_percent']}%")
    
    if integrity['violations'] > 0:
        print(f"   ⚠️  WARNING: Found {integrity['violations']} violations!")
        if 'violation_details' in integrity:
            for v in integrity['violation_details'][:5]:
                print(f"      - {v['transaction_id']}: {v['status']}")
    else:
        print(f"   ✅ No violations found\n")
    
    # Test 3: Statistics
    print("3. Testing statistics (last 24 hours)...")
    stats = monitor.get_persistence_stats(lookback_hours=24)
    print(f"   Total transactions: {stats['total_transactions']}")
    print(f"   Compliance analyses: {stats['compliance_analyses_created']}")
    print(f"   Persistence rate: {stats['persistence_rate_percent']}%")
    print(f"   Avg processing time: {stats['average_processing_time_seconds']:.2f}s")
    print(f"   ✅ Statistics working\n")
    
    return integrity['status'] == 'healthy'


def test_database_integrity(db: Session):
    """Test database integrity directly"""
    print_section("TEST 2: Database Integrity Check")
    
    # Query for violations
    violations = db.query(Transaction).outerjoin(
        ComplianceAnalysis,
        Transaction.id == ComplianceAnalysis.transaction_id
    ).filter(
        Transaction.status == TransactionStatus.COMPLETED,
        ComplianceAnalysis.id == None
    ).all()
    
    print(f"Querying for COMPLETED transactions without ComplianceAnalysis...")
    print(f"Found: {len(violations)} violations\n")
    
    if violations:
        print("⚠️  WARNING: Violations detected!")
        for v in violations[:5]:
            print(f"   - {v.transaction_id}: status={v.status.value}, "
                  f"completed_at={v.processing_completed_at}")
        return False
    else:
        print("✅ No violations found - all COMPLETED transactions have ComplianceAnalysis\n")
        return True


def test_specific_transaction(db: Session, transaction_id: str = None):
    """Test verification of a specific transaction"""
    print_section("TEST 3: Specific Transaction Verification")
    
    if not transaction_id:
        # Get the most recent completed transaction
        recent = db.query(Transaction).filter(
            Transaction.status == TransactionStatus.COMPLETED
        ).order_by(Transaction.processing_completed_at.desc()).first()
        
        if not recent:
            print("No completed transactions found to test")
            return True
        
        transaction_id = recent.transaction_id
    
    print(f"Testing transaction: {transaction_id}\n")
    
    monitor = get_persistence_monitor(db)
    verification = monitor.verify_transaction_compliance(transaction_id)
    
    print(f"Transaction Status: {verification['transaction_status']}")
    print(f"Has ComplianceAnalysis: {verification['has_compliance_analysis']}")
    print(f"Should Have Compliance: {verification['should_have_compliance']}")
    print(f"Verification Status: {verification['verification_status']}")
    
    if verification['has_compliance_analysis']:
        print(f"ComplianceAnalysis ID: {verification['compliance_analysis_id']}")
        print(f"Risk Score: {verification['risk_score']}")
        print(f"Risk Band: {verification['risk_band']}")
        print(f"Processing Time: {verification['processing_time_seconds']}s")
    
    if verification['verification_status'] == 'ok':
        print(f"\n✅ Transaction verification passed\n")
        return True
    elif verification['verification_status'] == 'violation':
        print(f"\n⚠️  Transaction verification FAILED - violation detected\n")
        return False
    else:
        print(f"\n⚠️  Transaction in {verification['verification_status']} state\n")
        return True


def test_statistics_summary(db: Session):
    """Print summary statistics"""
    print_section("TEST 4: Summary Statistics")
    
    # Count by status
    from sqlalchemy import func
    
    status_counts = {}
    for status in TransactionStatus:
        count = db.query(Transaction).filter(
            Transaction.status == status
        ).count()
        status_counts[status.value] = count
    
    total_completed = status_counts.get('completed', 0)
    total_failed = status_counts.get('failed', 0)
    total_processing = status_counts.get('processing', 0)
    
    # Count compliance analyses
    total_analyses = db.query(ComplianceAnalysis).count()
    
    print("Transaction Status Summary:")
    for status, count in status_counts.items():
        print(f"   {status.upper()}: {count}")
    
    print(f"\nCompliance Analysis Summary:")
    print(f"   Total analyses: {total_analyses}")
    print(f"   Expected (completed): {total_completed}")
    print(f"   Match: {total_analyses == total_completed}")
    
    if total_analyses == total_completed:
        print(f"\n✅ All {total_completed} COMPLETED transactions have ComplianceAnalysis\n")
        return True
    else:
        diff = total_completed - total_analyses
        print(f"\n⚠️  MISMATCH: {diff} COMPLETED transactions missing ComplianceAnalysis\n")
        return False


def main():
    """Run all tests"""
    print(f"\n{'#'*80}")
    print(f"  COMPLIANCE ANALYSIS PERSISTENCE GUARANTEE - TEST SUITE")
    print(f"  Started at: {datetime.utcnow().isoformat()}")
    print(f"{'#'*80}")
    
    db = SessionLocal()
    all_passed = True
    
    try:
        # Test 1: Monitoring service
        passed_1 = test_monitoring_service(db)
        all_passed = all_passed and passed_1
        
        # Test 2: Database integrity
        passed_2 = test_database_integrity(db)
        all_passed = all_passed and passed_2
        
        # Test 3: Specific transaction
        passed_3 = test_specific_transaction(db)
        all_passed = all_passed and passed_3
        
        # Test 4: Summary statistics
        passed_4 = test_statistics_summary(db)
        all_passed = all_passed and passed_4
        
        # Final result
        print_section("FINAL RESULT")
        
        if all_passed:
            print("🎉 ALL TESTS PASSED 🎉")
            print("\n✅ Compliance analysis persistence guarantee is working correctly!")
            print("✅ All COMPLETED transactions have ComplianceAnalysis records")
            print("✅ Monitoring system is operational")
            print("✅ Database integrity verified")
            return 0
        else:
            print("⚠️  SOME TESTS FAILED")
            print("\n❌ Review the violations above and investigate")
            print("❌ Check logs for more details")
            print("❌ Run database migration if needed")
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
