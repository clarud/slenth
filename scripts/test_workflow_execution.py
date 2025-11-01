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
# DETAILED AGENT OUTPUT DISPLAY
# ============================================================================

def display_agent_output(agent_name: str, state: dict):
    """Display detailed output from each agent."""
    
    if agent_name == "context_builder":
        query_strings = state.get("query_strings", [])
        if query_strings:
            print(f"\n   📝 Query Strings Generated ({len(query_strings)}):")
            for i, query in enumerate(query_strings, 1):
                print(f"      {i}. \"{query}\"")
        
        tx_history = state.get("transaction_history", [])
        print(f"\n   📊 Historical Transactions: {len(tx_history)}")
        if tx_history:
            print(f"      • Most recent: {tx_history[0].get('transaction_id', 'N/A')}")
            print(f"      • Date range: Last {len(tx_history)} transactions")
    
    elif agent_name == "retrieval":
        retrieved = state.get("applicable_rules", [])  # Fixed: was "retrieved_rules"
        print(f"\n   📚 Rules Retrieved: {len(retrieved)}")
        
        internal = [r for r in retrieved if r.get('source') == 'internal']
        external = [r for r in retrieved if r.get('source') == 'external']
        
        if internal:
            print(f"\n   🏢 Internal Rules ({len(internal)}):")
            for i, rule in enumerate(internal[:3], 1):
                print(f"      {i}. {rule.get('rule_id', 'N/A')}: {rule.get('title', 'N/A')[:60]}")
        
        if external:
            print(f"\n   🌐 External Rules ({len(external)}):")
            for i, rule in enumerate(external[:3], 1):
                print(f"      {i}. {rule.get('rule_id', 'N/A')}: {rule.get('title', 'N/A')[:60]}")
        
        if not retrieved:
            print(f"      ⚠️  No rules found (Vector DB may be empty)")
    
    elif agent_name == "applicability":
        # Get both the full list and filtered list
        all_rules = state.get("applicable_rules", [])
        filtered_rules = state.get("applicable_rules_filtered", [])
        
        print(f"\n   ✓ Applicable Rules: {len(all_rules)}")
        print(f"   ✓ Filtered (Truly Applicable): {len(filtered_rules)}")
        
        if filtered_rules:
            print(f"\n   📋 Rule Applicability:")
            for i, rule in enumerate(filtered_rules[:5], 1):
                rule_title = rule.get('title', 'N/A')[:50]
                rationale = rule.get('rationale', 'N/A')
                confidence = rule.get('confidence', 0.0)
                print(f"      {i}. {rule_title}")
                print(f"         Rule ID: {rule.get('rule_id', 'N/A')[:36]}")
                print(f"         Confidence: {confidence:.2f}")
                print(f"         Reason: {rationale[:100]}")
    
    elif agent_name == "evidence_mapper":
        # evidence_summary is the old name, evidence_map is the correct field
        evidence = state.get("evidence_map", {}) or state.get("evidence_summary", {})
        print(f"\n   🗺️  Evidence Mapping: {len(evidence)} rules mapped")
        
        if evidence:
            for rule_id, ev_data in list(evidence.items())[:3]:
                print(f"\n      Rule: {rule_id}")
                if isinstance(ev_data, dict):
                    print(f"      • Evidence Count: {len(ev_data.get('evidence', []))}")
                else:
                    print(f"      • Evidence: {str(ev_data)[:100]}")
    
    elif agent_name == "control_test":
        control_results = state.get("control_results", [])
        print(f"\n   🧪 Control Tests: {len(control_results)}")
        
        if control_results:
            passed = sum(1 for c in control_results if c.get('status') == 'pass')
            failed = sum(1 for c in control_results if c.get('status') == 'fail')
            partial = sum(1 for c in control_results if c.get('status') == 'partial')
            print(f"      • Passed: {passed}")
            print(f"      • Failed: {failed}")
            print(f"      • Partial: {partial}")
            
            print(f"\n   📋 Control Test Results:")
            for i, test in enumerate(control_results[:3], 1):
                rule_title = test.get('rule_title', 'N/A')[:50]
                status = test.get('status', 'N/A')
                score = test.get('compliance_score', 0)
                rationale = test.get('rationale', 'N/A')[:80]
                
                status_emoji = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
                print(f"      {i}. {status_emoji} {rule_title}")
                print(f"         Status: {status.upper()} (Score: {score}/100)")
                print(f"         Rationale: {rationale}...")
    
    elif agent_name == "feature_service":
        features = state.get("features", {})
        print(f"\n   🔢 Features Extracted: {len(features)}")
        
        if features:
            print(f"\n   📊 Feature Details:")
            for key, value in features.items():
                # Format the key
                formatted_key = key.replace('_', ' ').title()
                # Format the value
                if isinstance(value, bool):
                    icon = "✓" if value else "✗"
                    print(f"      {icon} {formatted_key}: {value}")
                elif isinstance(value, (int, float)):
                    print(f"      • {formatted_key}: {value:,.2f}" if isinstance(value, float) else f"      • {formatted_key}: {value}")
                else:
                    print(f"      • {formatted_key}: {value}")
    
    elif agent_name == "bayesian_engine":
        bayesian = state.get("bayesian_posterior", {})
        print(f"\n   📊 Bayesian Analysis:")
        if bayesian:
            print(f"      • Prior: {bayesian.get('prior_suspicious', 0):.4f}")
            print(f"      • Posterior: {bayesian.get('posterior_suspicious', 0):.4f}")
            print(f"      • Evidence Strength: {bayesian.get('evidence_strength', 'N/A')}")
    
    elif agent_name == "pattern_detector":
        patterns = state.get("detected_patterns", [])
        print(f"\n   🎯 Patterns Detected: {len(patterns)}")
        
        if patterns:
            print(f"\n   📋 Pattern Details:")
            for i, pattern in enumerate(patterns, 1):
                print(f"      {i}. {pattern.get('pattern_type', 'N/A')}")
                print(f"         Confidence: {pattern.get('confidence', 0):.2%}")
                print(f"         Description: {pattern.get('description', 'N/A')[:60]}")
    
    elif agent_name == "decision_fusion":
        print(f"\n   ⚖️  Risk Assessment:")
        print(f"      • Risk Score: {state.get('risk_score', 0):.2f}")
        print(f"      • Risk Band: {state.get('risk_band', 'N/A')}")
        
        breakdown = state.get("score_breakdown", {})
        if breakdown:
            print(f"\n   📊 Score Breakdown:")
            print(f"      • Rule Score: {breakdown.get('rule_score', 0):.2f}")
            print(f"      • ML Score: {breakdown.get('ml_score', 0):.2f}")
            print(f"      • Pattern Score: {breakdown.get('pattern_score', 0):.2f}")
    
    elif agent_name == "analyst_writer":
        # Try multiple possible field names
        report = state.get("analyst_report", "") or state.get("compliance_summary", "")
        recommendations = state.get("recommendations", [])
        
        print(f"\n   📝 Analyst Report:")
        print(f"      • Length: {len(report)} characters")
        print(f"      • Recommendations: {len(recommendations)}")
        
        if report and len(report) > 0:
            # Show first few lines
            lines = report.split('\n')[:5]
            print(f"\n      Preview:")
            for line in lines:
                if line.strip():
                    print(f"      {line[:80]}")
        
        if recommendations:
            print(f"\n      Recommendations:")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"      {i}. {rec[:80]}")
    
    elif agent_name == "alert_composer":
        alerts = state.get("alerts", [])
        print(f"\n   🚨 Alerts: {len(alerts)}")
        
        if alerts:
            print(f"\n   📋 Alert Details:")
            for i, alert in enumerate(alerts, 1):
                print(f"      {i}. [{alert.get('severity', 'N/A')}] {alert.get('title', 'N/A')}")
                print(f"         Role: {alert.get('role', 'N/A')}")
    
    elif agent_name == "remediation":
        actions = state.get("remediation_actions", [])
        print(f"\n   🔧 Remediation Actions: {len(actions)}")
        
        if actions:
            print(f"\n   📋 Action Details:")
            for i, action in enumerate(actions, 1):
                print(f"      {i}. {action.get('action_type', 'N/A')}")
                print(f"         Owner: {action.get('owner', 'N/A')}")
                print(f"         SLA: {action.get('sla_hours', 'N/A')} hours")
    
    elif agent_name == "persistor":
        records = state.get("records_created", [])
        print(f"\n   💾 Records Persisted: {len(records)}")
        
        if records:
            print(f"\n   📋 Created Records:")
            for record in records:
                print(f"      • {record}")


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
    Execute workflow with comprehensive agent-by-agent logging.
    
    This function uses execute_transaction_workflow() which handles transaction
    persistence, but captures streaming output for detailed logging.
    
    Returns:
        Final workflow state
    """
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 80)
    print("🚀  TRANSACTION WORKFLOW EXECUTION")
    print("=" * 80)
    print(f"📍 Transaction ID: {transaction['transaction_id']}")
    print(f"💰 Amount: {transaction['currency']} {transaction['amount']:,.2f}")
    print(f"🌍 Route: {transaction.get('originator_country', 'N/A')} → {transaction.get('beneficiary_country', 'N/A')}")
    print(f"⚠️  Customer Risk: {transaction['customer_risk_rating']}")
    print(f"👤 Customer ID: {transaction['customer_id']}")
    print("=" * 80)
    
    # Import the workflow execution function
    # This handles transaction persistence properly
    from workflows.transaction_workflow import execute_transaction_workflow
    
    # For comprehensive logging, we need to intercept the workflow execution
    # We'll use a custom approach: persist transaction, then stream the workflow
    from datetime import datetime, timezone
    from db.models import Transaction as TransactionModel, TransactionStatus
    import time
    
    start_time = time.time()
    transaction_id = transaction.get("transaction_id")
    
    # 1. Persist transaction (same logic as execute_transaction_workflow)
    try:
        existing = db_session.query(TransactionModel).filter(
            TransactionModel.transaction_id == transaction_id
        ).first()
        
        if existing:
            existing.status = TransactionStatus.PROCESSING
            existing.processing_started_at = datetime.now(timezone.utc)
            existing.amount = transaction.get("amount", existing.amount)
            existing.currency = transaction.get("currency", existing.currency)
            existing.customer_risk_rating = transaction.get("customer_risk_rating", existing.customer_risk_rating)
            existing.raw_data = transaction
            db_session.commit()
            logger.info(f"✅ Updated existing transaction {transaction_id} to PROCESSING")
        else:
            db_transaction = TransactionModel(
                transaction_id=transaction_id,
                booking_jurisdiction=transaction.get("booking_jurisdiction", "HK"),
                regulator=transaction.get("regulator", "HKMA"),
                booking_datetime=datetime.now(timezone.utc),
                value_date=transaction.get("value_date"),
                amount=transaction.get("amount"),
                currency=transaction.get("currency", "USD"),
                channel=transaction.get("channel"),
                product_type=transaction.get("product_type"),
                originator_name=transaction.get("originator_name"),
                originator_account=transaction.get("originator_account"),
                originator_country=transaction.get("originator_country"),
                beneficiary_name=transaction.get("beneficiary_name"),
                beneficiary_account=transaction.get("beneficiary_account"),
                beneficiary_country=transaction.get("beneficiary_country"),
                customer_id=transaction.get("customer_id"),
                customer_segment=transaction.get("customer_segment"),
                customer_risk_rating=transaction.get("customer_risk_rating"),
                customer_kyc_date=transaction.get("customer_kyc_date"),
                swift_mt=transaction.get("swift_mt"),
                ordering_institution_bic=transaction.get("ordering_institution_bic"),
                beneficiary_institution_bic=transaction.get("beneficiary_institution_bic"),
                swift_f50_present=transaction.get("swift_f50_present"),
                swift_f59_present=transaction.get("swift_f59_present"),
                swift_f70_purpose=transaction.get("swift_f70_purpose"),
                swift_f71_charges=transaction.get("swift_f71_charges"),
                pep_indicator=transaction.get("pep_indicator"),
                sanctions_hit=transaction.get("sanctions_hit"),
                high_risk_country=transaction.get("high_risk_country"),
                structuring_flag=transaction.get("structuring_flag"),
                status=TransactionStatus.PROCESSING,
                processing_started_at=datetime.now(timezone.utc),
                raw_data=transaction,
            )
            db_session.add(db_transaction)
            db_session.commit()
            logger.info(f"✅ Persisted NEW transaction {transaction_id} to database")
    except Exception as e:
        logger.error(f"❌ Failed to persist transaction: {e}", exc_info=True)
        db_session.rollback()
        raise RuntimeError(f"Cannot persist transaction {transaction_id}: {e}")
    
    # 2. Create workflow and stream for detailed logging
    from workflows.transaction_workflow import create_transaction_workflow
    
    app = create_transaction_workflow(
        db_session, llm_service, pinecone_internal, pinecone_external
    )
    
    agent_emojis = {
        "context_builder": "📋",
        "retrieval": "🔍",
        "applicability": "✅",
        "evidence_mapper": "🗺️",
        "control_test": "🧪",
        "feature_service": "🔢",
        "bayesian_engine": "📊",
        "pattern_detector": "🎯",
        "decision_fusion": "⚖️",
        "analyst_writer": "📝",
        "alert_composer": "🚨",
        "remediation": "🔧",
        "persistor": "💾",
    }
    
    # Execute using stream to capture each node's output
    from datetime import datetime, timezone
    start_time = datetime.now(timezone.utc)
    initial_state = {
        "transaction": transaction,
        "transaction_id": transaction.get("transaction_id"),
        "processing_start_time": start_time,
        "errors": [],
    }
    
    try:
        result = None
        async for event in app.astream(initial_state):
            # event is a dict with node_name: state
            for node_name, state in event.items():
                emoji = agent_emojis.get(node_name, "▶️")
                print(f"\n{'─' * 80}")
                print(f"{emoji}  {node_name.replace('_', ' ').upper()} AGENT")
                print(f"{'─' * 80}")
                display_agent_output(node_name, state)
                result = state
        
        if result:
            # processing_end_time already set by persistor agent
            pass
        
        # Final summary - calculate processing time from datetime objects
        start_time_dt = result.get('processing_start_time')
        end_time_dt = result.get('processing_end_time')
        if start_time_dt and end_time_dt:
            processing_time = (end_time_dt - start_time_dt).total_seconds()
        else:
            processing_time = 0.0
        
        print("\n" + "=" * 80)
        print("✅  WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\n⏱️  PERFORMANCE:")
        print(f"   • Total Processing Time: {processing_time:.2f}s")
        
        # Errors
        errors = result.get('errors', [])
        if errors:
            print(f"\n❌ ERRORS:")
            for error in errors:
                print(f"   • {error}")
        
        print(f"\n⏱️  PERFORMANCE:")
        print(f"   • Total Processing Time: {processing_time:.2f}s")
        
        errors = result.get('errors', [])
        if errors:
            print(f"\n❌ ERRORS:")
            for error in errors:
                print(f"   • {error}")
        
        print("\n" + "=" * 80 + "\n")
        
        return result
        
    except Exception as e:
        print(f"\n{'=' * 80}")
        print(f"❌  WORKFLOW EXECUTION FAILED")
        print(f"{'=' * 80}")
        print(f"Error: {str(e)}")
        print(f"{'=' * 80}\n")
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
    """Print a concise summary of the workflow results."""
    
    print("\n" + "="*80)
    print("📋 QUICK SUMMARY")
    print("="*80)
    
    # Key metrics only
    print(f"\n� Transaction: {result.get('transaction_id')}")
    print(f"💰 Amount: {result.get('transaction', {}).get('currency')} {result.get('transaction', {}).get('amount', 0):,.2f}")
    print(f"⚖️  Risk: {result.get('risk_score', 0):.2f} ({result.get('risk_band', 'N/A')})")
    print(f"📚 Rules: {len(result.get('applicable_rules', []))} applicable")
    
    # Errors
    # Errors
    errors = result.get('errors', [])
    if errors:
        print(f"❌ Errors: {len(errors)}")
    else:
        print(f"✅ Status: Completed successfully")
    
    # Performance - calculate from datetime objects
    start_time_dt = result.get('processing_start_time')
    end_time_dt = result.get('processing_end_time')
    if start_time_dt and end_time_dt:
        processing_time = (end_time_dt - start_time_dt).total_seconds()
        print(f"⏱️  Time: {processing_time:.2f}s")
    
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
        transaction_data = create_sample_transaction(scenario="high_risk")
        
        logger.info(f"Created transaction: {transaction_data['transaction_id']}")
        
        # Note: The workflow now handles persisting the transaction to the database
        # No need to manually save it here
        
        # Execute workflow
        logger.info("\nExecuting workflow...\n")
        
        result = await run_workflow_with_logging(
            transaction=transaction_data,
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
