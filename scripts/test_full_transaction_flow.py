#!/usr/bin/env python3
"""
Test Full Transaction Flow

This script tests the complete end-to-end transaction processing flow:
1. Create a test transaction
2. Submit to API endpoint (queues to Redis via Celery)
3. Monitor Celery task status
4. Check workflow execution results
5. Verify database persistence

Prerequisites:
- FastAPI server running (python -m uvicorn app.main:app --reload)
- Redis server running
- Celery worker running (celery -A worker.celery_app worker --loglevel=info)
- PostgreSQL database accessible
- Pinecone indices configured

Usage:
    python scripts/test_full_transaction_flow.py
    
    # Or with custom API URL
    python scripts/test_full_transaction_flow.py --api-url http://localhost:8000
"""

import sys
import time
import logging
import requests
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Transaction, ComplianceAnalysis, Alert

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TransactionFlowTester:
    """Tests the full transaction processing flow"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.submit_endpoint = f"{api_base_url}/transactions"
        self.db = SessionLocal()
    
    def create_test_transaction(self) -> Dict[str, Any]:
        """Create a test transaction payload"""
        timestamp = datetime.now(timezone.utc).isoformat()
        transaction_id = f"TEST_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        transaction = {
            "transaction_id": transaction_id,
            "booking_jurisdiction": "HK",
            "regulator": "HKMA",
            "booking_datetime": timestamp,
            "amount": 250000.0,
            "currency": "USD",
            "channel": "SWIFT",
            "product_type": "wire_transfer",
            "originator_name": "Test Corp Ltd",
            "originator_account": "1234567890",
            "originator_country": "HK",
            "beneficiary_name": "Offshore Trading Co Ltd",
            "beneficiary_account": "9876543210",
            "beneficiary_country": "SG",
            "customer_id": "CUST_TEST_001",
            "customer_risk_rating": "high",
            "swift_mt": "MT103",
            "swift_f70_purpose": "Investment",
            "pep_indicator": False,
            "sanctions_hit": False,
        }
        
        logger.info(f"✅ Created test transaction: {transaction_id}")
        return transaction
    
    def submit_transaction(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Submit transaction to API endpoint"""
        try:
            logger.info(f"\n{'='*70}")
            logger.info("📤 STEP 1: Submitting transaction to API")
            logger.info(f"{'='*70}")
            logger.info(f"   Endpoint: {self.submit_endpoint}")
            logger.info(f"   Transaction ID: {transaction['transaction_id']}")
            logger.info(f"   Amount: {transaction['currency']} {transaction['amount']:,.2f}")
            
            response = requests.post(
                self.submit_endpoint,
                json=transaction,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            task_id = result.get("task_id")
            
            logger.info(f"   ✅ Transaction queued successfully!")
            logger.info(f"   Task ID: {task_id}")
            logger.info(f"   Status: {result.get('status')}")
            logger.info(f"   Message: {result.get('message')}")
            
            return result
            
        except requests.exceptions.ConnectionError:
            logger.error("   ❌ Cannot connect to API server!")
            logger.error("   Make sure FastAPI server is running:")
            logger.error("   → python -m uvicorn app.main:app --reload")
            return None
        except Exception as e:
            logger.error(f"   ❌ Error submitting transaction: {e}")
            return None
    
    def monitor_task(self, task_id: str, transaction_id: str, max_wait: int = 60) -> bool:
        """Monitor Celery task status"""
        logger.info(f"\n{'='*70}")
        logger.info("⏳ STEP 2: Monitoring Celery task execution")
        logger.info(f"{'='*70}")
        logger.info(f"   Task ID: {task_id}")
        logger.info(f"   Max wait time: {max_wait}s")
        
        status_endpoint = f"{self.api_base_url}/transactions/{transaction_id}/status"
        
        start_time = time.time()
        dots = 0
        
        while (time.time() - start_time) < max_wait:
            try:
                response = requests.get(status_endpoint, timeout=5)
                response.raise_for_status()
                
                status_data = response.json()
                task_status = status_data.get("task_status", "UNKNOWN")
                
                # Print progress
                elapsed = int(time.time() - start_time)
                dots = (dots + 1) % 4
                print(f"\r   Status: {task_status:<15} | Elapsed: {elapsed:>3}s {'.' * dots}   ", end='', flush=True)
                
                if task_status == "SUCCESS":
                    print()  # New line
                    logger.info(f"   ✅ Task completed successfully!")
                    logger.info(f"   Processing time: {elapsed}s")
                    return True
                elif task_status == "FAILURE":
                    print()  # New line
                    logger.error(f"   ❌ Task failed!")
                    logger.error(f"   Error: {status_data.get('error')}")
                    return False
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"\n   ⚠️  Error checking status: {e}")
                time.sleep(2)
        
        print()  # New line
        logger.warning(f"   ⏰ Task did not complete within {max_wait}s")
        return False
    
    def verify_database_records(self, transaction_id: str) -> Dict[str, Any]:
        """Verify records were created in database"""
        logger.info(f"\n{'='*70}")
        logger.info("🔍 STEP 3: Verifying database persistence")
        logger.info(f"{'='*70}")
        
        results = {
            "transaction": None,
            "compliance_analysis": None,
            "alerts": [],
        }
        
        try:
            # Check Transaction record
            transaction = self.db.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).first()
            
            if transaction:
                logger.info(f"   ✅ Transaction record found")
                logger.info(f"      Status: {transaction.status}")
                logger.info(f"      Amount: {transaction.currency} {transaction.amount:,.2f}")
                results["transaction"] = transaction
            else:
                logger.error(f"   ❌ Transaction record NOT found")
                return results
            
            # Check ComplianceAnalysis record
            compliance = self.db.query(ComplianceAnalysis).filter(
                ComplianceAnalysis.transaction_id == transaction.id
            ).first()
            
            if compliance:
                logger.info(f"   ✅ Compliance analysis found")
                logger.info(f"      Risk Score: {compliance.compliance_score}")
                logger.info(f"      Risk Band: {compliance.risk_band}")
                logger.info(f"      Processing Time: {compliance.processing_time_seconds:.2f}s")
                logger.info(f"      Applicable Rules: {len(compliance.applicable_rules or [])}")
                logger.info(f"      Control Tests: {len(compliance.control_test_results or [])}")
                results["compliance_analysis"] = compliance
            else:
                logger.warning(f"   ⚠️  Compliance analysis NOT found")
            
            # Check Alerts
            alerts = self.db.query(Alert).filter(
                Alert.transaction_id == transaction.id
            ).all()
            
            if alerts:
                logger.info(f"   ✅ Found {len(alerts)} alert(s)")
                for alert in alerts:
                    logger.info(f"      • {alert.severity}: {alert.title}")
                    logger.info(f"        Alert ID: {alert.alert_id}")
                results["alerts"] = alerts
            else:
                logger.warning(f"   ⚠️  No alerts found")
            
            return results
            
        except Exception as e:
            logger.error(f"   ❌ Database error: {e}")
            return results
    
    def display_detailed_results(self, results: Dict[str, Any]):
        """Display detailed analysis results"""
        logger.info(f"\n{'='*70}")
        logger.info("📊 DETAILED RESULTS")
        logger.info(f"{'='*70}")
        
        compliance = results.get("compliance_analysis")
        if not compliance:
            logger.warning("No compliance analysis data available")
            return
        
        # Control Test Results
        control_tests = compliance.control_test_results or []
        if control_tests:
            logger.info(f"\n📋 Control Test Results ({len(control_tests)} tests):")
            for i, test in enumerate(control_tests, 1):
                status_emoji = "✅" if test.get("status") == "pass" else "❌"
                logger.info(f"   {i}. {status_emoji} {test.get('rule_title', 'N/A')}")
                logger.info(f"      Status: {test.get('status', 'N/A').upper()}")
                logger.info(f"      Score: {test.get('compliance_score', 0)}/100")
                rationale = test.get('rationale', '')
                if rationale:
                    logger.info(f"      Rationale: {rationale[:100]}...")
        
        # Pattern Detections
        patterns = compliance.pattern_detections or {}
        if patterns:
            logger.info(f"\n🔍 Pattern Detections:")
            for pattern, data in patterns.items():
                logger.info(f"   • {pattern}: {data}")
        
        # Analyst Notes
        if compliance.analyst_notes:
            logger.info(f"\n📝 Analyst Notes:")
            logger.info(f"   {compliance.analyst_notes[:200]}...")
    
    def run_full_test(self, transaction: Optional[Dict[str, Any]] = None) -> bool:
        """Run complete end-to-end test"""
        logger.info("\n" + "="*70)
        logger.info("🚀 STARTING FULL TRANSACTION FLOW TEST")
        logger.info("="*70)
        
        # Create or use provided transaction
        if not transaction:
            transaction = self.create_test_transaction()
        
        transaction_id = transaction["transaction_id"]
        
        # Step 1: Submit transaction
        submission_result = self.submit_transaction(transaction)
        if not submission_result:
            logger.error("\n❌ TEST FAILED: Could not submit transaction")
            return False
        
        task_id = submission_result.get("task_id")
        if not task_id:
            logger.error("\n❌ TEST FAILED: No task ID returned")
            return False
        
        # Step 2: Monitor task execution
        task_completed = self.monitor_task(task_id, transaction_id, max_wait=60)
        if not task_completed:
            logger.error("\n❌ TEST FAILED: Task did not complete successfully")
            return False
        
        # Step 3: Verify database records
        results = self.verify_database_records(transaction_id)
        if not results["transaction"]:
            logger.error("\n❌ TEST FAILED: Transaction not found in database")
            return False
        
        # Step 4: Display detailed results
        self.display_detailed_results(results)
        
        # Final summary
        logger.info(f"\n{'='*70}")
        logger.info("✅ TEST COMPLETED SUCCESSFULLY!")
        logger.info(f"{'='*70}")
        logger.info(f"   Transaction ID: {transaction_id}")
        logger.info(f"   Task ID: {task_id}")
        logger.info(f"   Risk Score: {results['compliance_analysis'].compliance_score if results['compliance_analysis'] else 'N/A'}")
        logger.info(f"   Risk Band: {results['compliance_analysis'].risk_band if results['compliance_analysis'] else 'N/A'}")
        logger.info(f"   Alerts Generated: {len(results['alerts'])}")
        logger.info(f"{'='*70}\n")
        
        return True
    
    def cleanup(self):
        """Close database connection"""
        self.db.close()


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(
        description="Test full transaction processing flow"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="FastAPI server URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    # Pre-flight checks
    logger.info("\n🔧 Pre-flight Checks:")
    logger.info("   Please ensure the following services are running:")
    logger.info("   1. ✓ FastAPI Server: python -m uvicorn app.main:app --reload")
    logger.info("   2. ✓ Redis Server: redis-server")
    logger.info("   3. ✓ Celery Worker: celery -A worker.celery_app worker --loglevel=info")
    logger.info("   4. ✓ PostgreSQL Database")
    logger.info("   5. ✓ Pinecone Vector Database\n")
    
    input("Press Enter to continue...")
    
    # Run test
    tester = TransactionFlowTester(api_base_url=args.api_url)
    
    try:
        success = tester.run_full_test()
        sys.exit(0 if success else 1)
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
