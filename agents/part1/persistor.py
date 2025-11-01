"""
PersistorAgent - Persist all results and maintain audit trail

Logic:

1. Store ComplianceAnalysis to database
2. Update Transaction record
3. Create Alert records
4. Create Case records if needed
5. Log to AuditLog
6. Store hashes and versions


Output:
persisted: bool, records_created: List[str]
"""

import logging
from typing import Any, Dict
from datetime import datetime

from agents import Part1Agent
from services.llm import LLMService
from services.vector_db import VectorDBService
from services.audit import AuditService
from services.alert_service import AlertService

logger = logging.getLogger(__name__)


class PersistorAgent(Part1Agent):
    """Agent: Persist all results and maintain audit trail"""

    def __init__(
        self,
        llm_service: LLMService = None,
        vector_service: VectorDBService = None,
        audit_service: AuditService = None,
        alert_service: AlertService = None,
        db_session = None
    ):
        super().__init__("persistor")
        self.llm = llm_service
        self.vector_db = vector_service
        self.audit = audit_service
        self.alert_service = alert_service
        self.db = db_session

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute persistor agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with persistence confirmation
        """
        self.logger.info("Executing PersistorAgent")

        records_created = []

        try:
            transaction_id = state.get("transaction_id")
            if not transaction_id:
                raise ValueError("No transaction_id in state")

            # Get DB session from state if not provided
            db = self.db or state.get("db_session")
            if not db:
                raise ValueError("No database session available")

            # Import models here to avoid circular imports
            from db.models import Transaction, ComplianceAnalysis, Alert, Case, AuditLog

            # 1. Update Transaction record
            transaction = db.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).first()

            if transaction:
                transaction.risk_score = state.get("risk_score", 0.0)
                transaction.risk_band = state.get("risk_band", "Low")
                transaction.processing_status = "completed"
                transaction.processed_at = datetime.utcnow()
                db.commit()
                records_created.append(f"transaction:{transaction_id}")
                self.logger.info(f"Updated transaction {transaction_id}")

            # 2. Create ComplianceAnalysis record
            compliance_analysis = ComplianceAnalysis(
                transaction_id=transaction_id,
                risk_score=state.get("risk_score", 0.0),
                risk_band=state.get("risk_band", "Low"),
                applicable_rules=state.get("applicable_rules", []),
                evidence_summary=state.get("evidence_summary", {}),
                control_results=state.get("control_results", []),
                pattern_scores=state.get("pattern_scores", {}),
                analyst_report=state.get("analyst_report", ""),
                score_breakdown=state.get("score_breakdown", {}),
                metadata={
                    "bayesian_posterior": state.get("bayesian_posterior", {}),
                    "features": state.get("features", {}),
                    "workflow_version": "1.0",
                }
            )
            db.add(compliance_analysis)
            db.commit()
            records_created.append(f"compliance_analysis:{compliance_analysis.analysis_id}")
            self.logger.info(f"Created compliance analysis")

            # 3. Create Alert records if risk is significant
            risk_score = state.get("risk_score", 0.0)
            risk_band = state.get("risk_band", "Low")
            
            if risk_score >= 30:  # Medium or higher
                alert_data = state.get("alerts", [])
                
                if not alert_data and self.alert_service:
                    # Create default alert if none provided
                    from db.models import AlertSeverity, AlertRole
                    
                    severity = AlertSeverity.HIGH if risk_score >= 60 else AlertSeverity.MEDIUM
                    
                    alert = await self.alert_service.create_alert(
                        title=f"Transaction Risk Alert: {risk_band}",
                        description=f"Transaction {transaction_id} flagged with {risk_band} risk (score: {risk_score})",
                        severity=severity,
                        role=AlertRole.COMPLIANCE,
                        source_type="transaction",
                        source_id=transaction_id,
                        metadata={
                            "risk_score": risk_score,
                            "risk_band": risk_band,
                            "applicable_rules_count": len(state.get("applicable_rules", [])),
                        }
                    )
                    records_created.append(f"alert:{alert.alert_id}")
                    self.logger.info(f"Created alert {alert.alert_id}")

            # 4. Create Case if risk is Critical
            if risk_score >= 80:
                case = Case(
                    title=f"Critical Risk - Transaction {transaction_id}",
                    description=f"Automated case created for critical risk transaction",
                    case_type="transaction_review",
                    priority="critical",
                    source_type="transaction",
                    source_id=transaction_id,
                    status="open",
                    metadata={
                        "risk_score": risk_score,
                        "risk_band": risk_band,
                        "auto_created": True,
                    }
                )
                db.add(case)
                db.commit()
                records_created.append(f"case:{case.case_id}")
                self.logger.info(f"Created case {case.case_id}")

            # 5. Log to AuditLog
            if self.audit:
                await self.audit.log_event(
                    event_type="transaction_processing_complete",
                    entity_type="transaction",
                    entity_id=transaction_id,
                    action="workflow_complete",
                    actor_type="system",
                    actor_id="workflow_engine",
                    details={
                        "risk_score": risk_score,
                        "risk_band": risk_band,
                        "records_created": records_created,
                        "applicable_rules_count": len(state.get("applicable_rules", [])),
                    }
                )

            state["persisted"] = True
            state["records_created"] = records_created
            state["persistor_completed"] = True

            self.logger.info(f"Persistence complete: {len(records_created)} records created")

        except Exception as e:
            self.logger.error(f"Error in PersistorAgent: {str(e)}", exc_info=True)
            state["persisted"] = False
            state["records_created"] = records_created
            state["errors"] = state.get("errors", []) + [f"PersistorAgent: {str(e)}"]

        return state
