"""
Test script to execute the Part 1 Transaction Monitoring Workflow with detailed logging.

This script:
1. Loads environment variables from .env file
2. Sets up comprehensive logging to see intermediate steps
3. Creates mock/real services (Groq LLM, Pinecone)
4. Executes the workflow with a sample transaction
5. Displays detailed output at each agent step
6. Saves results to a JSON file for inspection

Usage:
    python scripts/test_workflow_execution.py
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables FIRST (before importing services)
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
else:
    print(f"⚠️  .env file not found at {env_path}")

from sqlalchemy.orm import Session

from db.database import SessionLocal, init_db
from services.llm import LLMService
from services.pinecone_db import PineconeService
from workflows.transaction_workflow import execute_transaction_workflow


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_detailed_logging():
    """Set up detailed logging to console and file."""
    
    # Create logs directory if it doesn't exist
    log_dir = project_root / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Log filename with timestamp
    log_file = log_dir / f"workflow_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Console handler (INFO level, simple format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (DEBUG level, detailed format)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Set specific loggers to DEBUG for our modules
    for module in [
        'workflows.transaction_workflow',
        'agents.part1',
        'services.llm',
        'services.pinecone_db',
    ]:
        logging.getLogger(module).setLevel(logging.DEBUG)
    
    print(f"\n{'='*80}")
    print(f"Logging configured:")
    print(f"  Console: INFO level")
    print(f"  File: {log_file}")
    print(f"  File level: DEBUG")
    print(f"{'='*80}\n")
    
    return log_file


# ============================================================================
# SAMPLE TRANSACTION DATA
# ============================================================================

def create_sample_transaction(scenario: str = "high_risk") -> dict:
    """
    Create sample transaction data for testing.
    
    Args:
        scenario: Type of scenario - "high_risk", "medium_risk", "low_risk", "structuring"
    
    Returns:
        Transaction dictionary
    """
    base_transaction = {
        "transaction_id": f"TXN_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_id": "CUST_12345",
        "customer_name": "John Doe",
        "customer_risk_rating": "medium",
        "transaction_type": "wire_transfer",
        "currency": "USD",
    }
    
    scenarios = {
        "high_risk": {
            "amount": 250000,  # High value
            "originator_country": "HK",
            "beneficiary_country": "SG",
            "beneficiary_name": "Offshore Trading Co Ltd",
            "customer_risk_rating": "high",
            "purpose": "Investment",
        },
        "medium_risk": {
            "amount": 50000,
            "originator_country": "US",
            "beneficiary_country": "UK",
            "beneficiary_name": "ABC Manufacturing Ltd",
            "customer_risk_rating": "medium",
            "purpose": "Business payment",
        },
        "low_risk": {
            "amount": 5000,
            "originator_country": "US",
            "beneficiary_country": "US",
            "beneficiary_name": "Jane Smith",
            "customer_risk_rating": "low",
            "purpose": "Personal transfer",
        },
        "structuring": {
            "amount": 9500,  # Just below reporting threshold
            "originator_country": "US",
            "beneficiary_country": "MX",
            "beneficiary_name": "Cash Exchange Service",
            "customer_risk_rating": "medium",
            "purpose": "Cash deposit",
            "notes": "Multiple similar transactions in past 24h",
        },
    }
    
    return {**base_transaction, **scenarios.get(scenario, scenarios["medium_risk"])}


# ============================================================================
# WORKFLOW EXECUTION
# ============================================================================

async def run_workflow_with_logging(
    transaction: dict,
    db_session: Session,
    llm_service: LLMService,
    pinecone_internal: PineconeService,
    pinecone_external: PineconeService,
) -> dict:
    """
    Execute workflow and log each step.
    
    Returns:
        Final workflow state
    """
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info("STARTING TRANSACTION WORKFLOW EXECUTION")
    logger.info("="*80)
    logger.info(f"Transaction ID: {transaction['transaction_id']}")
    logger.info(f"Amount: {transaction['currency']} {transaction['amount']:,.2f}")
    logger.info(f"Route: {transaction['originator_country']} → {transaction['beneficiary_country']}")
    logger.info(f"Customer Risk: {transaction['customer_risk_rating']}")
    logger.info("="*80)
    
    try:
        # Execute workflow
        result = await execute_transaction_workflow(
            transaction=transaction,
            db_session=db_session,
            llm_service=llm_service,
            pinecone_internal=pinecone_internal,
            pinecone_external=pinecone_external,
        )
        
        logger.info("="*80)
        logger.info("WORKFLOW EXECUTION COMPLETED")
        logger.info("="*80)
        
        # Log key results
        if result.get("errors"):
            logger.error(f"Errors encountered: {result['errors']}")
        
        if result.get("risk_score") is not None:
            logger.info(f"Final Risk Score: {result['risk_score']}")
        
        if result.get("risk_band"):
            logger.info(f"Risk Band: {result['risk_band']}")
        
        if result.get("applicable_rules"):
            logger.info(f"Applicable Rules: {len(result['applicable_rules'])}")
        
        if result.get("alerts"):
            logger.info(f"Alerts Generated: {len(result['alerts'])}")
        
        processing_time = result.get('processing_end_time', 0) - result.get('processing_start_time', 0)
        logger.info(f"Processing Time: {processing_time:.2f}s")
        
        logger.info("="*80)
        
        return result
        
    except Exception as e:
        logger.error(f"WORKFLOW EXECUTION FAILED: {e}", exc_info=True)
        raise


def save_results(result: dict, log_file: Path):
    """Save workflow results to JSON file."""
    
    # Create results directory
    results_dir = project_root / "data" / "workflow_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Save to JSON (same timestamp as log file)
    timestamp = log_file.stem.replace("workflow_execution_", "")
    result_file = results_dir / f"workflow_result_{timestamp}.json"
    
    # Convert any non-serializable objects
    def json_serializer(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return str(obj)
    
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2, default=json_serializer)
    
    print(f"\n{'='*80}")
    print(f"Results saved to: {result_file}")
    print(f"{'='*80}\n")


def print_summary(result: dict):
    """Print a human-readable summary of the workflow results."""
    
    print("\n" + "="*80)
    print("WORKFLOW EXECUTION SUMMARY")
    print("="*80)
    
    # Transaction Info
    print("\n📊 Transaction:")
    print(f"  ID: {result.get('transaction_id')}")
    print(f"  Amount: {result.get('transaction', {}).get('currency')} {result.get('transaction', {}).get('amount', 0):,.2f}")
    
    # Risk Assessment
    print("\n⚠️  Risk Assessment:")
    print(f"  Risk Score: {result.get('risk_score', 'N/A')}")
    print(f"  Risk Band: {result.get('risk_band', 'N/A')}")
    
    # Rules Analysis
    print("\n📋 Rules Analysis:")
    print(f"  Retrieved Rules: {len(result.get('retrieved_rules', []))}")
    print(f"  Applicable Rules: {len(result.get('applicable_rules', []))}")
    
    # Control Tests
    control_results = result.get('control_results', [])
    if control_results:
        print(f"\n🔍 Control Tests: {len(control_results)}")
        passed = sum(1 for c in control_results if c.get('status') == 'pass')
        failed = sum(1 for c in control_results if c.get('status') == 'fail')
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
    
    # Features
    features = result.get('features', {})
    if features:
        print(f"\n🔢 Features Extracted: {len(features)}")
        print(f"  High Value: {features.get('is_high_value', 'N/A')}")
        print(f"  Cross-Border: {features.get('is_cross_border', 'N/A')}")
    
    # Patterns
    patterns = result.get('detected_patterns', [])
    if patterns:
        print(f"\n🎯 Patterns Detected: {len(patterns)}")
        for pattern in patterns[:3]:  # Show first 3
            print(f"  - {pattern.get('pattern_type', 'Unknown')}: {pattern.get('description', '')}")
    
    # Alerts
    alerts = result.get('alerts', [])
    if alerts:
        print(f"\n🚨 Alerts Generated: {len(alerts)}")
        for alert in alerts[:3]:  # Show first 3
            print(f"  - {alert.get('severity', 'N/A')}: {alert.get('title', 'Alert')}")
    
    # Compliance Analysis
    analysis = result.get('compliance_analysis', '')
    if analysis:
        print(f"\n📝 Compliance Analysis:")
        print(f"  {analysis[:200]}..." if len(analysis) > 200 else f"  {analysis}")
    
    # Remediation
    remediation = result.get('remediation_actions', [])
    if remediation:
        print(f"\n🔧 Remediation Actions: {len(remediation)}")
        for action in remediation[:3]:  # Show first 3
            print(f"  - {action.get('action_type', 'Unknown')}: {action.get('description', '')}")
    
    # Errors
    errors = result.get('errors', [])
    if errors:
        print(f"\n❌ Errors: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    
    # Performance
    processing_time = result.get('processing_end_time', 0) - result.get('processing_start_time', 0)
    print(f"\n⏱️  Performance:")
    print(f"  Processing Time: {processing_time:.2f}s")
    
    print("\n" + "="*80 + "\n")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function."""
    
    # Check environment variables
    print("\n" + "="*80)
    print("ENVIRONMENT VARIABLES CHECK")
    print("="*80)
    required_vars = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY"),
        "PINECONE_INTERNAL_INDEX_HOST": os.getenv("PINECONE_INTERNAL_INDEX_HOST"),
        "PINECONE_EXTERNAL_INDEX_HOST": os.getenv("PINECONE_EXTERNAL_INDEX_HOST"),
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            masked_value = var_value[:8] + "..." if len(var_value) > 8 else "***"
            print(f"✅ {var_name}: {masked_value}")
        else:
            print(f"❌ {var_name}: NOT SET")
            all_set = False
    
    print("="*80 + "\n")
    
    if not all_set:
        print("⚠️  Some required environment variables are missing!")
        print("Please check your .env file and ensure all required variables are set.\n")
        return None
    
    # Setup logging
    log_file = setup_detailed_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        # init_db()  # Uncomment if you need to create tables
        
        # Create database session
        db_session = SessionLocal()
        
        # Initialize services
        logger.info("Initializing services...")
        logger.info("  - LLM Service (Groq)")
        llm_service = LLMService()
        
        logger.info("  - Pinecone Internal Index")
        pinecone_internal = PineconeService(index_type="internal")
        
        logger.info("  - Pinecone External Index")
        pinecone_external = PineconeService(index_type="external")
        
        # Create sample transaction
        logger.info("\nCreating sample transaction...")
        
        # You can change the scenario here: "high_risk", "medium_risk", "low_risk", "structuring"
        transaction = create_sample_transaction(scenario="high_risk")
        
        logger.info(f"Created transaction: {transaction['transaction_id']}")
        
        # Execute workflow
        logger.info("\nExecuting workflow...\n")
        
        result = await run_workflow_with_logging(
            transaction=transaction,
            db_session=db_session,
            llm_service=llm_service,
            pinecone_internal=pinecone_internal,
            pinecone_external=pinecone_external,
        )
        
        # Save results
        save_results(result, log_file)
        
        # Print summary
        print_summary(result)
        
        # Close database session
        db_session.close()
        
        logger.info("Execution completed successfully!")
        
        return result
        
    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
