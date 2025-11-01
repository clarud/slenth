"""
Check alerts in database - debugging script
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Alert, Transaction, ComplianceAnalysis
from sqlalchemy import desc

def check_alerts():
    """Check what's in the alerts table."""
    db = SessionLocal()
    
    try:
        # Check recent transactions
        print("\n" + "="*80)
        print("RECENT TRANSACTIONS")
        print("="*80)
        transactions = db.query(Transaction).order_by(desc(Transaction.created_at)).limit(5).all()
        
        for txn in transactions:
            print(f"\nTransaction: {txn.transaction_id}")
            print(f"  Status: {txn.status}")
            print(f"  Created: {txn.created_at}")
            
            # Check if it has compliance analysis
            analysis = db.query(ComplianceAnalysis).filter(
                ComplianceAnalysis.transaction_id == txn.id
            ).first()
            
            if analysis:
                print(f"  ✅ Has ComplianceAnalysis:")
                print(f"     Risk Score: {analysis.compliance_score}")
                print(f"     Risk Band: {analysis.risk_band}")
            else:
                print(f"  ❌ No ComplianceAnalysis found")
            
            # Check if it has alerts
            alerts = db.query(Alert).filter(Alert.transaction_id == txn.id).all()
            if alerts:
                print(f"  ✅ Has {len(alerts)} Alert(s):")
                for alert in alerts:
                    print(f"     - {alert.alert_id}: {alert.role} / {alert.severity} / {alert.alert_type}")
            else:
                print(f"  ❌ No Alerts found")
        
        # Check total counts
        print("\n" + "="*80)
        print("DATABASE COUNTS")
        print("="*80)
        
        total_txns = db.query(Transaction).count()
        total_analysis = db.query(ComplianceAnalysis).count()
        total_alerts = db.query(Alert).count()
        
        print(f"Total Transactions: {total_txns}")
        print(f"Total ComplianceAnalysis: {total_analysis}")
        print(f"Total Alerts: {total_alerts}")
        
        # Check if there are any compliance analyses with risk >= 30 but no alerts
        print("\n" + "="*80)
        print("COMPLIANCE ANALYSES WITH RISK >= 30")
        print("="*80)
        
        high_risk_analyses = db.query(ComplianceAnalysis).filter(
            ComplianceAnalysis.compliance_score >= 30
        ).order_by(desc(ComplianceAnalysis.created_at)).limit(10).all()
        
        print(f"Found {len(high_risk_analyses)} analyses with risk >= 30")
        
        for analysis in high_risk_analyses:
            txn = db.query(Transaction).filter(Transaction.id == analysis.transaction_id).first()
            alerts = db.query(Alert).filter(Alert.transaction_id == analysis.transaction_id).all()
            
            print(f"\nTransaction: {txn.transaction_id if txn else 'Unknown'}")
            print(f"  Risk Score: {analysis.compliance_score}")
            print(f"  Risk Band: {analysis.risk_band}")
            print(f"  Alerts: {len(alerts)} alert(s)")
            if not alerts:
                print(f"  ⚠️  WARNING: Should have alert but none found!")
        
    finally:
        db.close()


if __name__ == "__main__":
    check_alerts()
