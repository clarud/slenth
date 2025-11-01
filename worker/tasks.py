"""
Celery Tasks for Part 1 Transaction Processing.

Tasks defined here are executed asynchronously by Celery workers.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from db.database import SessionLocal
from services.llm import LLMService
from services.pinecone_db import PineconeService
from worker.celery_app import celery_app
from workflows.transaction_workflow import execute_transaction_workflow

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_transaction")
def process_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single transaction through the Part 1 workflow.

    This task is executed asynchronously by Celery workers.

    Args:
        transaction: Transaction data dict

    Returns:
        Processing results
    """
    task_id = self.request.id
    transaction_id = transaction.get("transaction_id")

    logger.info(
        f"Task {task_id}: Processing transaction {transaction_id}"
    )

    # Update task state
    self.update_state(
        state="PROCESSING",
        meta={"transaction_id": transaction_id, "progress": 0},
    )

    # Create database session
    db: Session = SessionLocal()

    try:
        # Initialize services
        llm_service = LLMService()  # Uses Groq by default from config
        pinecone_internal = PineconeService(index_type="internal")
        pinecone_external = PineconeService(index_type="external")

        # Execute workflow
        import asyncio
        final_state = asyncio.run(
            execute_transaction_workflow(
                transaction=transaction,
                db_session=db,
                llm_service=llm_service,
                pinecone_internal=pinecone_internal,
                pinecone_external=pinecone_external,
            )
        )

        # Extract results
        # Calculate processing time in seconds (JSON-serializable)
        start_time = final_state.get("processing_start_time")
        end_time = final_state.get("processing_end_time")
        if start_time and end_time:
            processing_time_seconds = (end_time - start_time).total_seconds()
        else:
            processing_time_seconds = 0.0
        
        results = {
            "transaction_id": transaction_id,
            "task_id": task_id,
            "status": "completed",
            "risk_score": final_state.get("risk_score"),
            "risk_band": final_state.get("risk_band"),
            "compliance_summary": final_state.get("compliance_summary"),
            "alerts_generated": final_state.get("alerts_generated", []),
            "processing_time": processing_time_seconds,  # Now a float, JSON-serializable
            "errors": final_state.get("errors", []),
        }

        logger.info(
            f"Task {task_id}: Completed transaction {transaction_id} "
            f"with risk_band={results['risk_band']}"
        )

        return results

    except Exception as e:
        logger.error(
            f"Task {task_id}: Error processing transaction {transaction_id}: {e}",
            exc_info=True,
        )

        # Update task state to FAILURE
        self.update_state(
            state="FAILURE",
            meta={
                "transaction_id": transaction_id,
                "error": str(e),
            },
        )

        # Re-raise to mark task as failed
        raise

    finally:
        db.close()


@celery_app.task(name="healthcheck")
def healthcheck() -> Dict[str, str]:
    """
    Celery worker health check task.

    Returns:
        Status dict
    """
    return {"status": "healthy", "service": "celery_worker"}
