"""
Part 2: Document Corroboration Workflow

LangGraph-based workflow that orchestrates 10 agents for document validation and risk assessment.
This workflow executes SYNCHRONOUSLY (no Celery/Redis).

Workflow DAG:
DocumentIntake → OCR → FormatValidation → NLPValidation → ImageForensics
                                                               ↓
                                                         BackgroundCheck
                                                               ↓
                                                         CrossReference
                                                               ↓
                                                          DocumentRisk
                                                               ↓
                                                        ReportGenerator
                                                               ↓
                                                     EvidenceStorekeeper
"""

import logging
import time
from typing import Any, Dict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from agents.part2 import (
    BackgroundCheckAgent,
    CrossReferenceAgent,
    DocumentIntakeAgent,
    DocumentRiskAgent,
    EvidenceStorekeeperAgent,
    FormatValidationAgent,
    ImageForensicsAgent,
    NLPValidationAgent,
    OCRAgent,
    ReportGeneratorAgent,
)
from services.llm import LLMService
from workflows.state import DocumentWorkflowState

logger = logging.getLogger(__name__)


def create_document_workflow(
    db_session: Session,
    llm_service: LLMService,
    skip_background_check: bool = False,
):
    """
    Create and compile the Part 2 document corroboration workflow.

    Args:
        db_session: Database session
        llm_service: LLM service instance
        skip_background_check: If True, skip BackgroundCheck agent (no Dilisense API call)

    Returns:
        Compiled LangGraph workflow
    """
    # Initialize agents
    document_intake = DocumentIntakeAgent()
    ocr = OCRAgent()
    format_validation = FormatValidationAgent()
    nlp_validation = NLPValidationAgent(llm_service=llm_service)
    image_forensics = ImageForensicsAgent()
    background_check = BackgroundCheckAgent()
    cross_reference = CrossReferenceAgent(db_session)
    document_risk = DocumentRiskAgent()
    report_generator = ReportGeneratorAgent()
    evidence_storekeeper = EvidenceStorekeeperAgent(db_session)

    # Define workflow graph
    workflow = StateGraph(DocumentWorkflowState)

    # Add nodes (agents)
    workflow.add_node("document_intake", document_intake.execute)
    workflow.add_node("ocr", ocr.execute)
    workflow.add_node("format_validation", format_validation.execute)
    workflow.add_node("nlp_validation", nlp_validation.execute)
    workflow.add_node("image_forensics", image_forensics.execute)
    
    if not skip_background_check:
        workflow.add_node("background_check", background_check.execute)
    
    workflow.add_node("cross_reference", cross_reference.execute)
    # DocumentRisk removed - not compatible with Part2 state structure
    # ReportGenerator will calculate risk from findings instead
    workflow.add_node("report_generator", report_generator.execute)
    workflow.add_node("evidence_storekeeper", evidence_storekeeper.execute)

    # Define edges (workflow flow)
    workflow.set_entry_point("document_intake")

    # Sequential flow
    workflow.add_edge("document_intake", "ocr")
    workflow.add_edge("ocr", "format_validation")
    workflow.add_edge("format_validation", "nlp_validation")
    workflow.add_edge("nlp_validation", "image_forensics")
    
    if skip_background_check:
        # Skip BackgroundCheck - go directly to CrossReference
        workflow.add_edge("image_forensics", "cross_reference")
    else:
        # Include BackgroundCheck in the flow
        workflow.add_edge("image_forensics", "background_check")
        workflow.add_edge("background_check", "cross_reference")
    
    # Go directly from CrossReference to ReportGenerator (skip DocumentRisk)
    workflow.add_edge("cross_reference", "report_generator")
    workflow.add_edge("report_generator", "evidence_storekeeper")

    # End workflow
    workflow.add_edge("evidence_storekeeper", END)

    # Compile workflow
    app = workflow.compile()

    logger.info("Document workflow compiled successfully")

    return app


async def execute_document_workflow(
    document: Dict[str, Any],
    file_path: str,
    db_session: Session,
    llm_service: LLMService,
    skip_background_check: bool = False,
) -> Dict[str, Any]:
    """
    Execute the document corroboration workflow for a single document.
    
    This executes SYNCHRONOUSLY and returns complete results immediately.

    Args:
        document: Document metadata
        file_path: Path to uploaded file
        db_session: Database session
        llm_service: LLM service
        skip_background_check: If True, skip BackgroundCheck agent (no Dilisense API call)

    Returns:
        Final workflow state with all results
    """
    start_time = time.time()

    # Create workflow with optional BackgroundCheck skip
    app = create_document_workflow(db_session, llm_service, skip_background_check)

    # Initialize state
    initial_state: DocumentWorkflowState = {
        "document": document,
        "document_id": document.get("document_id"),
        "file_path": file_path,
        "file_type": document.get("file_type"),
        "processing_start_time": start_time,
        "errors": [],
    }

    try:
        # Execute workflow SYNCHRONOUSLY
        final_state = await app.ainvoke(initial_state)

        # Add processing time
        final_state["processing_end_time"] = time.time()

        logger.info(
            f"Document workflow completed for {document.get('document_id')} "
            f"in {final_state['processing_end_time'] - start_time:.2f}s"
        )

        return final_state

    except Exception as e:
        logger.error(f"Error in document workflow: {e}", exc_info=True)
        return {
            **initial_state,
            "errors": [str(e)],
            "processing_end_time": time.time(),
        }
