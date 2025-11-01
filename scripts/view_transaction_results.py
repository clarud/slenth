#!/usr/bin/env python3
"""
View Transaction Processing Results

This script displays the results of transactions processed by the Part 1 workflow.
Shows data from transactions, compliance_analysis, and alerts tables.

Usage:
    python scripts/view_transaction_results.py [transaction_id]
    
    # View all recent transactions
    python scripts/view_transaction_results.py
    
    # View specific transaction details
    python scripts/view_transaction_results.py ad66338d-b17f-47fc-a966-1b4395351b41
"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import desc, func
from db.database import SessionLocal
from db.models import Transaction, ComplianceAnalysis, Alert


def format_datetime(dt):
    """Format datetime for display"""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_json_length(json_data):
    """Get length of JSON array"""
    if json_data is None:
        return 0
    if isinstance(json_data, list):
        return len(json_data)
    return 0


def view_all_recent_transactions(db, limit=10):
    """View recent transactions summary"""
    print("\n" + "="*100)
    print("🔍 RECENT TRANSACTIONS")
    print("="*100)
    
    transactions = db.query(Transaction).order_by(desc(Transaction.created_at)).limit(limit).all()
    
    if not transactions:
        print("❌ No transactions found")
        return
    
    print(f"\nFound {len(transactions)} recent transactions:\n")
    
    for i, txn in enumerate(transactions, 1):
        # Get related compliance analysis
        analysis = db.query(ComplianceAnalysis).filter(
            ComplianceAnalysis.transaction_id == txn.id
        ).first()
        
        # Get related alerts
        alerts_count = db.query(func.count(Alert.id)).filter(
            Alert.transaction_id == txn.id
        ).scalar()
        
        print(f"{i}. Transaction: {txn.transaction_id}")
        print(f"   Jurisdiction: {txn.booking_jurisdiction} | Regulator: {txn.regulator}")
        print(f"   Amount: {txn.currency} {txn.amount:,.2f}")
        print(f"   Status: {txn.status}")
        print(f"   Created: {format_datetime(txn.created_at)}")
        
        if txn.processing_started_at:
            print(f"   Processing Started: {format_datetime(txn.processing_started_at)}")
        if txn.processing_completed_at:
            print(f"   Processing Completed: {format_datetime(txn.processing_completed_at)}")
        
        if analysis:
            print(f"   Risk Band: {analysis.risk_band} | Score: {analysis.compliance_score}")
            print(f"   Processing Time: {analysis.processing_time_seconds:.2f}s")
            print(f"   Applicable Rules: {format_json_length(analysis.applicable_rules)}")
            print(f"   Control Tests: {format_json_length(analysis.control_test_results)}")
        
        if alerts_count > 0:
            print(f"   ⚠️  Alerts Generated: {alerts_count}")
        
        print()


def view_transaction_detail(db, transaction_id):
    """View detailed information for a specific transaction"""
    print("\n" + "="*100)
    print(f"🔍 TRANSACTION DETAILS: {transaction_id}")
    print("="*100)
    
    # Get transaction
    txn = db.query(Transaction).filter(
        Transaction.transaction_id == transaction_id
    ).first()
    
    if not txn:
        print(f"❌ Transaction {transaction_id} not found")
        return
    
    # Transaction Details
    print("\n📋 TRANSACTION INFORMATION")
    print("-" * 100)
    print(f"Transaction ID: {txn.transaction_id}")
    print(f"Booking Jurisdiction: {txn.booking_jurisdiction}")
    print(f"Regulator: {txn.regulator}")
    print(f"Amount: {txn.currency} {txn.amount:,.2f}")
    print(f"Channel: {txn.channel}")
    print(f"Product Type: {txn.product_type}")
    print(f"Status: {txn.status}")
    print(f"\nOriginator: {txn.originator_name} ({txn.originator_country})")
    print(f"  Account: {txn.originator_account}")
    print(f"Beneficiary: {txn.beneficiary_name} ({txn.beneficiary_country})")
    print(f"  Account: {txn.beneficiary_account}")
    print(f"\nCustomer ID: {txn.customer_id}")
    print(f"Customer Type: {txn.customer_segment}")
    print(f"Customer Risk Rating: {txn.customer_risk_rating}")
    print(f"\nCreated: {format_datetime(txn.created_at)}")
    print(f"Processing Started: {format_datetime(txn.processing_started_at)}")
    print(f"Processing Completed: {format_datetime(txn.processing_completed_at)}")
    
    # Compliance Analysis
    analysis = db.query(ComplianceAnalysis).filter(
        ComplianceAnalysis.transaction_id == txn.id
    ).first()
    
    if analysis:
        print("\n📊 COMPLIANCE ANALYSIS")
        print("-" * 100)
        print(f"Risk Band: {analysis.risk_band}")
        print(f"Compliance Score: {analysis.compliance_score}")
        print(f"Bayesian Posterior: {analysis.bayesian_posterior}")
        print(f"Processing Time: {analysis.processing_time_seconds:.2f} seconds")
        print(f"Analysis Created: {format_datetime(analysis.created_at)}")
        
        # Applicable Rules
        if analysis.applicable_rules:
            print(f"\n📜 APPLICABLE RULES ({len(analysis.applicable_rules)} rules)")
            for i, rule in enumerate(analysis.applicable_rules[:5], 1):  # Show first 5
                print(f"  {i}. {rule.get('title', 'N/A')}")
                print(f"     Jurisdiction: {rule.get('jurisdiction', 'N/A')}")
                print(f"     Source: {rule.get('source', 'N/A')}")
        
        # Control Test Results
        if analysis.control_test_results:
            print(f"\n🧪 CONTROL TEST RESULTS ({len(analysis.control_test_results)} tests)")
            for i, test in enumerate(analysis.control_test_results[:5], 1):  # Show first 5
                status_icon = "✅" if test.get('status') == 'pass' else "❌"
                print(f"  {status_icon} {i}. {test.get('rule_title', 'N/A')}")
                print(f"     Status: {test.get('status', 'N/A')} | Severity: {test.get('severity', 'N/A')}")
                if test.get('rationale'):
                    print(f"     Rationale: {test.get('rationale', '')[:100]}...")
        
        # Pattern Detections
        if analysis.pattern_detections:
            print(f"\n🔍 PATTERN DETECTIONS")
            for pattern_type, details in analysis.pattern_detections.items():
                print(f"  • {pattern_type}: {details}")
        
        # Analyst Notes
        if analysis.analyst_notes:
            print(f"\n📝 ANALYST NOTES")
            print(f"  {analysis.analyst_notes[:500]}...")
    
    # Alerts
    alerts = db.query(Alert).filter(Alert.transaction_id == txn.id).all()
    
    if alerts:
        print(f"\n⚠️  ALERTS ({len(alerts)} alerts)")
        print("-" * 100)
        for i, alert in enumerate(alerts, 1):
            severity_icons = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢"
            }
            role_icons = {
                "front": "🧭",
                "compliance": "🕵️‍♀️",
                "legal": "⚖️"
            }
            icon = severity_icons.get(alert.severity, "⚪")
            role_icon = role_icons.get(alert.role, "👤")
            
            print(f"{icon} {role_icon} {i}. {alert.title}")
            print(f"   Alert ID: {alert.alert_id}")
            print(f"   Assigned To: {alert.role.upper()} TEAM | Severity: {alert.severity} | Type: {alert.alert_type}")
            print(f"   Status: {alert.status}")
            print(f"   Description: {alert.description[:200]}...")
            
            if alert.remediation_workflow:
                print(f"\n   📋 REMEDIATION WORKFLOW:")
                workflow_lines = alert.remediation_workflow.split('\n')
                for line in workflow_lines[:8]:  # Show first 8 steps
                    if line.strip():
                        print(f"      {line}")
                if len(workflow_lines) > 8:
                    print(f"      ... ({len(workflow_lines) - 8} more steps)")
            
            print(f"\n   Created: {format_datetime(alert.created_at)}")
            if alert.sla_deadline:
                print(f"   SLA Deadline: {format_datetime(alert.sla_deadline)}")
            print()
    else:
        print("\n✅ No alerts generated for this transaction")
    
    print("="*100)


def main():
    """Main function"""
    db = SessionLocal()
    
    try:
        if len(sys.argv) > 1:
            # View specific transaction
            transaction_id = sys.argv[1]
            view_transaction_detail(db, transaction_id)
        else:
            # View all recent transactions
            view_all_recent_transactions(db, limit=20)
            
            print("\n💡 TIP: To view details of a specific transaction, run:")
            print("   python scripts/view_transaction_results.py <transaction_id>")
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
