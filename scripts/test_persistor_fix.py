#!/usr/bin/env python3
"""
Test PersistorAgent Fix - Verify transaction status updates

This script simulates what the PersistorAgent should do and verifies it works.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from sqlalchemy import desc
from db.database import SessionLocal
from db.models import Transaction, ComplianceAnalysis, TransactionStatus

def test_transaction_update():
    """Test updating transaction status"""
    db = SessionLocal()
    
    try:
        # Get a pending transaction
        txn = db.query(Transaction).filter(
            Transaction.status == TransactionStatus.PENDING
        ).order_by(desc(Transaction.created_at)).first()
        
        if not txn:
            print("❌ No pending transactions found")
            return False
        
        print(f"✅ Found pending transaction: {txn.transaction_id}")
        print(f"   Current status: {txn.status.value}")
        print(f"   processing_started_at: {txn.processing_started_at}")
        print(f"   processing_completed_at: {txn.processing_completed_at}")
        
        # Try to update it
        print("\n🔄 Updating transaction...")
        txn.status = TransactionStatus.COMPLETED
        txn.processing_completed_at = datetime.utcnow()
        db.commit()
        
        # Refresh and verify
        db.refresh(txn)
        print(f"✅ Updated status: {txn.status.value}")
        print(f"   processing_completed_at: {txn.processing_completed_at}")
        
        # Rollback the test change
        print("\n⏪ Rolling back test change...")
        txn.status = TransactionStatus.PENDING
        txn.processing_completed_at = None
        db.commit()
        
        print("✅ Test passed! PersistorAgent should be able to update transaction status")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_transaction_update()
    sys.exit(0 if success else 1)
