"""
Part 1: Transaction Monitoring Workflow

LangGraph-based workflow that orchestrates 13 agents for real-time AML transaction monitoring.

Workflow DAG:
ContextBuilder → Retrieval → Applicability → EvidenceMapper → ControlTest
                                                                    ↓
                                                              FeatureService
                                                                    ↓
                                                              BayesianEngine
                                                                    ↓
                                                             PatternDetector
                                                                    ↓
                                                             DecisionFusion
                                                                    ↓
                                                              AnalystWriter
                                                                    ↓
                                                              AlertComposer
                                                                    ↓
                                                        RemediationOrchestrator
                                                                    ↓
                                                                Persistor
"""

import logging
import time
from typing import Any, Dict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from agents.part1 import (
    AlertComposerAgent,
    AnalystWriterAgent,
    ApplicabilityAgent,
    BayesianEngineAgent,
    ContextBuilderAgent,
    ControlTestAgent,
    DecisionFusionAgent,
    EvidenceMapperAgent,
    FeatureServiceAgent,
    PatternDetectorAgent,
    PersistorAgent,
    RemediationOrchestratorAgent,
    RetrievalAgent,
)
from services.llm import LLMService
from services.pinecone_db import PineconeService
from workflows.state import TransactionWorkflowState

logger = logging.getLogger(__name__)


def create_transaction_workflow(
    db_session: Session,
    llm_service: LLMService,
    pinecone_internal: PineconeService,
    pinecone_external: PineconeService,
):
    """
    Create and compile the Part 1 transaction monitoring workflow.

    Args:
        db_session: Database session
        llm_service: LLM service instance (Groq)
        pinecone_internal: Pinecone service for internal rules
        pinecone_external: Pinecone service for external rules

    Returns:
        Compiled LangGraph workflow
    """
    # Initialize agents
    context_builder = ContextBuilderAgent(db_session)
    retrieval = RetrievalAgent(
        llm_service=llm_service,
        pinecone_internal=pinecone_internal,
        pinecone_external=pinecone_external
    )
    applicability = ApplicabilityAgent(llm_service)
    evidence_mapper = EvidenceMapperAgent(llm_service)
    control_test = ControlTestAgent(llm_service)
    feature_service = FeatureServiceAgent(db_session)
    bayesian_engine = BayesianEngineAgent()
    pattern_detector = PatternDetectorAgent(db_session)
    decision_fusion = DecisionFusionAgent()
    analyst_writer = AnalystWriterAgent(llm_service)
    alert_composer = AlertComposerAgent(db_session)
    remediation = RemediationOrchestratorAgent(db_session)
    persistor = PersistorAgent(db_session=db_session)

    # Define workflow graph
    workflow = StateGraph(TransactionWorkflowState)

    # Add nodes (agents)
    workflow.add_node("context_builder", context_builder.execute)
    workflow.add_node("retrieval", retrieval.execute)
    workflow.add_node("applicability", applicability.execute)
    workflow.add_node("evidence_mapper", evidence_mapper.execute)
    workflow.add_node("control_test", control_test.execute)
    workflow.add_node("feature_service", feature_service.execute)
    workflow.add_node("bayesian_engine", bayesian_engine.execute)
    workflow.add_node("pattern_detector", pattern_detector.execute)
    workflow.add_node("decision_fusion", decision_fusion.execute)
    workflow.add_node("analyst_writer", analyst_writer.execute)
    workflow.add_node("alert_composer", alert_composer.execute)
    workflow.add_node("remediation", remediation.execute)
    workflow.add_node("persistor", persistor.execute)

    # Define edges (workflow flow)
    workflow.set_entry_point("context_builder")

    # Linear flow
    workflow.add_edge("context_builder", "retrieval")
    workflow.add_edge("retrieval", "applicability")
    workflow.add_edge("applicability", "evidence_mapper")
    workflow.add_edge("evidence_mapper", "control_test")

    # Parallel processing branches (in practice, sequential due to dependencies)
    workflow.add_edge("control_test", "feature_service")
    workflow.add_edge("feature_service", "bayesian_engine")
    workflow.add_edge("bayesian_engine", "pattern_detector")

    # Fusion and downstream
    workflow.add_edge("pattern_detector", "decision_fusion")
    workflow.add_edge("decision_fusion", "analyst_writer")
    workflow.add_edge("analyst_writer", "alert_composer")
    workflow.add_edge("alert_composer", "remediation")
    workflow.add_edge("remediation", "persistor")

    # End workflow
    workflow.add_edge("persistor", END)

    # Compile workflow
    app = workflow.compile()

    logger.info("Transaction workflow compiled successfully")

    return app


async def execute_transaction_workflow(
    transaction: Dict[str, Any],
    db_session: Session,
    llm_service: LLMService,
    pinecone_internal: PineconeService,
    pinecone_external: PineconeService,
) -> Dict[str, Any]:
    """
    Execute the transaction monitoring workflow for a single transaction.

    Args:
        transaction: Transaction data (dict)
        db_session: Database session
        llm_service: LLM service (Groq)
        pinecone_internal: Pinecone service for internal rules
        pinecone_external: Pinecone service for external rules

    Returns:
        Final workflow state with all results
    """
    from datetime import datetime, timezone
    from db.models import Transaction as TransactionModel, TransactionStatus
    
    start_time = datetime.now(timezone.utc)
    transaction_id = transaction.get("transaction_id")
    
    # 1. ALWAYS persist incoming transaction to database first
    # This ensures PersistorAgent can find and update it later
    # Whether it's a new transaction or re-processing an existing one
    try:
        # Check if transaction already exists
        existing = db_session.query(TransactionModel).filter(
            TransactionModel.transaction_id == transaction_id
        ).first()
        
        if existing:
            # Update existing transaction to PROCESSING status
            existing.status = TransactionStatus.PROCESSING
            existing.processing_started_at = datetime.now(timezone.utc)
            # Update transaction data in case anything changed
            existing.amount = transaction.get("amount", existing.amount)
            existing.currency = transaction.get("currency", existing.currency)
            existing.customer_risk_rating = transaction.get("customer_risk_rating", existing.customer_risk_rating)
            existing.raw_data = transaction
            db_session.commit()
            logger.info(f"Updated existing transaction {transaction_id} to PROCESSING status")
        else:
            # Create new transaction record
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
        logger.error(f"❌ Failed to persist transaction to database: {e}", exc_info=True)
        # Don't fail the workflow, but log the error
        db_session.rollback()
        # Re-raise to prevent workflow from running if transaction can't be persisted
        raise RuntimeError(f"Cannot persist transaction {transaction_id}: {e}")

    # 2. Create workflow
    app = create_transaction_workflow(
        db_session, llm_service, pinecone_internal, pinecone_external
    )

    # 3. Initialize state
    initial_state: TransactionWorkflowState = {
        "transaction": transaction,
        "transaction_id": transaction.get("transaction_id"),
        "processing_start_time": start_time,
        "errors": [],
    }

    try:
        # 4. Execute workflow
        final_state = await app.ainvoke(initial_state)

        # Add processing time
        end_time = datetime.now(timezone.utc)
        final_state["processing_end_time"] = end_time
        processing_duration = (end_time - start_time).total_seconds()

        # POST-WORKFLOW VERIFICATION: Ensure ComplianceAnalysis was created
        if final_state.get("persistor_completed"):
            from db.models import ComplianceAnalysis
            
            txn_record = db_session.query(TransactionModel).filter(
                TransactionModel.transaction_id == transaction_id
            ).first()
            
            if txn_record:
                compliance_check = db_session.query(ComplianceAnalysis).filter(
                    ComplianceAnalysis.transaction_id == txn_record.id
                ).first()
                
                if not compliance_check:
                    error_msg = (
                        f"CRITICAL INTEGRITY ERROR: Workflow completed but no ComplianceAnalysis found "
                        f"for transaction {transaction_id}. This violates the persistence guarantee."
                    )
                    logger.error(error_msg)
                    
                    # Mark transaction as FAILED
                    txn_record.status = TransactionStatus.FAILED
                    db_session.commit()
                    
                    raise RuntimeError(error_msg)
                else:
                    logger.info(
                        f"✅ POST-WORKFLOW VERIFICATION PASSED: ComplianceAnalysis {compliance_check.id} "
                        f"confirmed for transaction {transaction_id}"
                    )
            else:
                logger.warning(f"Transaction record not found during verification: {transaction_id}")

        logger.info(
            f"Transaction workflow completed for {transaction.get('transaction_id')} "
            f"in {processing_duration:.2f}s"
        )

        return final_state

    except Exception as e:
        logger.error(f"Error in transaction workflow: {e}", exc_info=True)
        
        # Mark transaction as FAILED in database
        try:
            failed_txn = db_session.query(TransactionModel).filter(
                TransactionModel.transaction_id == transaction_id
            ).first()
            if failed_txn:
                failed_txn.status = TransactionStatus.FAILED
                failed_txn.processing_completed_at = datetime.now(timezone.utc)
                db_session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update transaction status to FAILED: {db_error}")
            db_session.rollback()
        
        return {
            **initial_state,
            "errors": [str(e)],
            "processing_end_time": datetime.now(timezone.utc),
        }
