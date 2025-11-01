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
from services.embeddings import EmbeddingService
from services.llm import LLMService
from services.vector_db import VectorDBService
from workflows.state import TransactionWorkflowState

logger = logging.getLogger(__name__)


def create_transaction_workflow(
    db_session: Session,
    llm_service: LLMService,
    vector_service: VectorDBService,
    embedding_service: EmbeddingService,
):
    """
    Create and compile the Part 1 transaction monitoring workflow.

    Args:
        db_session: Database session
        llm_service: LLM service instance
        vector_service: Vector DB service instance
        embedding_service: Embedding service instance

    Returns:
        Compiled LangGraph workflow
    """
    # Initialize agents
    context_builder = ContextBuilderAgent(db_session)
    retrieval = RetrievalAgent(llm_service, vector_service, embedding_service)
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
    persistor = PersistorAgent(db_session)

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
    vector_service: VectorDBService,
    embedding_service: EmbeddingService,
) -> Dict[str, Any]:
    """
    Execute the transaction monitoring workflow for a single transaction.

    Args:
        transaction: Transaction data
        db_session: Database session
        llm_service: LLM service
        vector_service: Vector DB service
        embedding_service: Embedding service

    Returns:
        Final workflow state with all results
    """
    start_time = time.time()

    # Create workflow
    app = create_transaction_workflow(
        db_session, llm_service, vector_service, embedding_service
    )

    # Initialize state
    initial_state: TransactionWorkflowState = {
        "transaction": transaction,
        "transaction_id": transaction.get("transaction_id"),
        "processing_start_time": start_time,
        "errors": [],
    }

    try:
        # Execute workflow
        final_state = await app.ainvoke(initial_state)

        # Add processing time
        final_state["processing_end_time"] = time.time()

        logger.info(
            f"Transaction workflow completed for {transaction.get('transaction_id')} "
            f"in {final_state['processing_end_time'] - start_time:.2f}s"
        )

        return final_state

    except Exception as e:
        logger.error(f"Error in transaction workflow: {e}", exc_info=True)
        return {
            **initial_state,
            "errors": [str(e)],
            "processing_end_time": time.time(),
        }
