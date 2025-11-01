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
from services.audit import AuditService
from services.alert_service import AlertService

logger = logging.getLogger(__name__)


class PersistorAgent(Part1Agent):
    """Agent: Persist all results and maintain audit trail"""

    def __init__(
        self,
        llm_service: LLMService = None,
        audit_service: AuditService = None,
        alert_service: AlertService = None,
        db_session = None
    ):
        super().__init__("persistor")
        self.llm = llm_service
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
        from datetime import datetime, timezone
        
        self.logger.info("Executing PersistorAgent")
        
        # Set end time NOW (persistor is the last agent to run)
        if "processing_end_time" not in state:
            state["processing_end_time"] = datetime.now(timezone.utc)
            self.logger.debug("Set processing_end_time in persistor agent")

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

            if not transaction:
                raise ValueError(f"Transaction {transaction_id} not found in database")

            # Update transaction with final results
            transaction.status = "completed"
            transaction.processing_completed_at = datetime.utcnow()
            db.commit()
            records_created.append(f"transaction:{transaction_id}")
            self.logger.info(f"Updated transaction {transaction_id}")

            # 2. Create ComplianceAnalysis record
            # Map state fields to ComplianceAnalysis model fields
            from db.models import RiskBand
            
            risk_band_str = state.get("risk_band", "Low").lower()
            risk_band_enum = RiskBand[risk_band_str.upper()] if risk_band_str else RiskBand.LOW
            
            # Calculate processing time correctly
            start_time = state.get("processing_start_time")
            end_time = state.get("processing_end_time")
            
            self.logger.info(f"⏱️  TIMESTAMP DEBUG:")
            self.logger.info(f"   Start time: {start_time}")
            self.logger.info(f"   Start type: {type(start_time)}")
            self.logger.info(f"   End time: {end_time}")
            self.logger.info(f"   End type: {type(end_time)}")
            
            if start_time and end_time:
                # Both are datetime objects, calculate difference in seconds
                try:
                    processing_time = (end_time - start_time).total_seconds()
                    self.logger.info(f"   ✅ Calculated: {processing_time:.2f}s")
                except Exception as e:
                    self.logger.warning(f"   ❌ Error calculating: {e}")
                    processing_time = 0.0
            else:
                self.logger.warning(f"   ⚠️  Missing timestamps!")
                processing_time = 0.0
            
            self.logger.info(f"   💾 Storing processing_time: {processing_time}s")
            
            compliance_analysis = ComplianceAnalysis(
                transaction_id=transaction.id,  # Use Transaction UUID, not string ID
                compliance_score=state.get("risk_score", 0.0),
                risk_band=risk_band_enum,
                applicable_rules=state.get("applicable_rules", []),
                evidence_map=state.get("evidence_summary", {}),
                control_test_results=state.get("control_results", []),
                pattern_detections=state.get("pattern_scores", {}),
                bayesian_posterior=state.get("bayesian_posterior", {}).get("posterior_suspicious", 0.0) if isinstance(state.get("bayesian_posterior"), dict) else state.get("bayesian_posterior", 0.0),
                compliance_summary=state.get("analyst_report", ""),
                analyst_notes=state.get("analyst_notes", ""),
                processing_time_seconds=processing_time
            )
            db.add(compliance_analysis)
            db.commit()
            records_created.append(f"compliance_analysis:{compliance_analysis.id}")
            self.logger.info(f"Created compliance analysis")

            # 3. Create Alert records if risk is significant
            risk_score = state.get("risk_score", 0.0)
            risk_band_str = state.get("risk_band", "Low")
            
            if risk_score >= 30:  # Medium or higher
                from db.models import AlertSeverity, AlertRole, AlertStatus
                from datetime import timedelta
                
                # Map risk band to alert severity
                severity_map = {
                    "Low": AlertSeverity.LOW,
                    "Medium": AlertSeverity.MEDIUM,
                    "High": AlertSeverity.HIGH,
                    "Critical": AlertSeverity.CRITICAL
                }
                severity = severity_map.get(risk_band_str, AlertSeverity.MEDIUM)
                
                # Calculate SLA deadline based on severity
                sla_hours = {
                    AlertSeverity.LOW: 72,
                    AlertSeverity.MEDIUM: 48,
                    AlertSeverity.HIGH: 24,
                    AlertSeverity.CRITICAL: 12
                }
                sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours.get(severity, 48))
                
                # Create alert
                alert = Alert(
                    alert_id=f"ALR_{transaction_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    source_type="transaction",
                    transaction_id=transaction.id,  # Use Transaction UUID
                    role=AlertRole.COMPLIANCE,
                    severity=severity,
                    alert_type="transaction_risk",
                    title=f"Transaction Risk Alert: {risk_band_str}",
                    description=f"Transaction {transaction_id} flagged with {risk_band_str} risk (score: {risk_score:.2f})",
                    context={
                        "risk_score": risk_score,
                        "risk_band": risk_band_str,
                        "applicable_rules_count": len(state.get("applicable_rules", [])),
                        "features": state.get("features", {}),
                    },
                    evidence={
                        "patterns": state.get("pattern_scores", {}),
                        "controls": state.get("control_results", []),
                    },
                    status=AlertStatus.PENDING,
                    sla_deadline=sla_deadline,
                )
                db.add(alert)
                db.commit()
                records_created.append(f"alert:{alert.alert_id}")
                self.logger.info(f"Created alert {alert.alert_id}")

            # 4. Create Case if risk is Critical
            if risk_score >= 80:
                from db.models import CaseStatus
                
                case = Case(
                    case_id=f"CASE_{transaction_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    case_title=f"Critical Risk - Transaction {transaction_id}",
                    case_description=f"Automated case created for critical risk transaction (score: {risk_score:.2f})",
                    case_type="transaction_aml",
                    severity=AlertSeverity.CRITICAL,
                    status=CaseStatus.OPEN,
                    customer_id=state.get("transaction", {}).get("customer_id"),
                    entity_name=state.get("transaction", {}).get("customer_name"),
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
                        "risk_band": risk_band_str,
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
