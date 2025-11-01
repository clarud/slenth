"""
AlertComposerAgent - Compose actionable alerts with role assignment and remediation workflows

Logic:

1. Analyze transaction risk, control failures, and patterns
2. Determine appropriate alert category and team assignment
3. Generate specific, actionable alert descriptions
4. Assign role (Front, Compliance, Legal)
5. Create unique remediation workflow tied to alert type


Output:
alerts_generated: List[Dict] with alert details, role, and remediation workflow
"""

import logging
from typing import Any, Dict, List

from agents import Part1Agent
from services.llm import LLMService

logger = logging.getLogger(__name__)


class AlertComposerAgent(Part1Agent):
    """Agent: Compose actionable alerts with role assignment and remediation workflows"""

    def __init__(self, llm_service: LLMService = None):
        super().__init__("alert_composer")
        self.llm = llm_service
        
        # Alert categorization rules based on detection logic
        self.alert_rules = self._initialize_alert_rules()

    def _initialize_alert_rules(self) -> List[Dict]:
        """Initialize alert categorization rules with role assignment and remediation workflows."""
        return [
            # FRONT TEAM ALERTS - Client-facing red flags
            {
                "category": "unusual_transaction_behavior",
                "role": "FRONT",
                "alert_templates": {
                    "transaction_exceeds_normal": {
                        "title": "Transaction Exceeds Client's Normal Activity",
                        "description_template": "Transaction amount {amount} {currency} exceeds client's historical average. Customer ID: {customer_id}, Risk Score: {risk_score}/100",
                        "remediation_workflow": "1. Contact client via secure channel within 24 hours\n2. Request explanation and justification for transaction\n3. Document client response in CRM system\n4. If explanation unsatisfactory, escalate to Compliance\n5. Update client risk profile if pattern continues"
                    },
                    "high_risk_jurisdiction": {
                        "title": "Transaction to/from High-Risk Jurisdiction",
                        "description_template": "Transaction involves {country} (high-risk jurisdiction). Amount: {amount} {currency}, Beneficiary: {beneficiary_name}",
                        "remediation_workflow": "1. Immediately suspend transaction processing\n2. Escalate to Compliance Team within 2 hours\n3. Request additional KYC documentation\n4. Perform enhanced screening on beneficiary\n5. Transaction requires Compliance Officer approval"
                    },
                },
            },
            # COMPLIANCE TEAM ALERTS - AML monitoring and investigation
            {
                "category": "high_risk_patterns",
                "role": "COMPLIANCE",
                "alert_templates": {
                    "structuring_detected": {
                        "title": "Structuring Pattern Detected (Smurfing)",
                        "description_template": "Multiple transactions below threshold detected. Total: {total_amount} {currency}, Count: {transaction_count}, Window: {time_window}h",
                        "remediation_workflow": "1. Assign to Senior AML Analyst for investigation\n2. Pull complete transaction history (90 days)\n3. Analyze patterns, timing, beneficiaries\n4. Prepare preliminary SAR documentation\n5. Escalate to Legal if pattern confirmed\n6. Consider account restrictions"
                    },
                    "layering_detected": {
                        "title": "Rapid Movement of Funds (Layering)",
                        "description_template": "Multiple rapid transfers detected. {transaction_count} transactions totaling {total_amount} {currency} within {time_window} hours",
                        "remediation_workflow": "1. Freeze all involved accounts immediately\n2. Map complete transaction flow\n3. Identify all intermediary accounts\n4. Check beneficial owner connections\n5. Prepare investigation report\n6. Escalate to Legal for SAR filing"
                    },
                    "regulatory_breach": {
                        "title": "Regulatory Rule Breach",
                        "description_template": "Transaction violates {rule_name}. Amount: {amount} {currency}, Rule: {rule_id}",
                        "remediation_workflow": "1. Review specific regulatory requirement\n2. Determine if transaction can be restructured\n3. If not compliant: reject and notify client\n4. Document decision with regulation citation\n5. Update controls to prevent similar violations\n6. Report to Compliance Manager"
                    },
                },
            },
            # LEGAL TEAM ALERTS - Regulatory reporting and enforcement
            {
                "category": "regulatory_reporting",
                "role": "LEGAL",
                "alert_templates": {
                    "sar_filing_required": {
                        "title": "Suspicious Activity Report (SAR) Filing Required",
                        "description_template": "SAR prepared for transaction. Customer: {customer_id}, Suspicion: {suspicion_level}, Amount: {amount} {currency}",
                        "remediation_workflow": "1. Legal Counsel to review SAR within 24 hours\n2. Verify all required fields completed\n3. Obtain MLRO approval signature\n4. File with regulator within 30 days\n5. Retain documentation for 5 years\n6. Do NOT notify customer (tipping off)\n7. Add to enhanced monitoring list"
                    },
                    "sanctions_breach": {
                        "title": "Potential Sanctions Breach",
                        "description_template": "CRITICAL: Sanctioned entity match. Entity: {entity_name}, Confidence: {match_score}%, Amount: {amount} {currency}",
                        "remediation_workflow": "1. IMMEDIATELY freeze transaction and accounts\n2. Escalate to GC and CCO within 1 hour\n3. Verify match details (DOB, passport, address)\n4. If confirmed: file OFAC blocking report\n5. Prepare for regulatory inquiry\n6. Report to Board\n7. Engage external counsel if needed"
                    },
                },
            },
        ]

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute alert_composer agent logic.
        
        Args:
            state: Workflow state

        Returns:
            Updated state with alerts
        """
        self.logger.info("Executing AlertComposerAgent")

        try:
            transaction = state.get("transaction", {})
            risk_score = state.get("risk_score", 0.0)
            risk_band = state.get("risk_band", "Low")
            control_results = state.get("control_results", [])
            pattern_scores = state.get("pattern_scores", {})
            
            alerts_generated = []
            
            # 1. Determine if alert should be generated
            # Generate alerts for Medium risk and above (score >= 30)
            if risk_score < 30:
                self.logger.info(f"No alerts generated for Low risk (score={risk_score})")
                state["alerts_generated"] = []
                state["alert_composer_executed"] = True
                return state
            
            # 2. Determine alert severity from risk_band
            severity_map = {
                "Low": "LOW",
                "Medium": "MEDIUM",
                "High": "HIGH",
                "Critical": "CRITICAL"
            }
            alert_severity = severity_map.get(risk_band, "MEDIUM")
            
            # 3. Determine roles to notify based on risk level and findings
            roles_to_alert = []
            
            if risk_band == "Critical":
                roles_to_alert = ["COMPLIANCE", "LEGAL"]  # Critical: both compliance and legal
            elif risk_band == "High":
                roles_to_alert = ["COMPLIANCE"]
            elif risk_band == "Medium":
                roles_to_alert = ["COMPLIANCE"]
            
            # Add FRONT_OFFICE role if specific patterns detected
            significant_patterns = [k for k, v in pattern_scores.items() if v > 60]
            if significant_patterns:
                if "FRONT_OFFICE" not in roles_to_alert:
                    roles_to_alert.append("FRONT_OFFICE")
            
            # 4. Set SLA deadlines based on severity
            from datetime import datetime, timedelta
            
            sla_hours_map = {
                "LOW": 72,      # 3 days
                "MEDIUM": 48,   # 2 days
                "HIGH": 24,     # 1 day
                "CRITICAL": 12  # 12 hours
            }
            sla_hours = sla_hours_map.get(alert_severity, 48)
            sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours)
            
            # 5. Build alert context
            failed_controls = [r for r in control_results if r.get("status") == "fail"]
            
            context = {
                "risk_score": risk_score,
                "risk_band": risk_band,
                "failed_controls_count": len(failed_controls),
                "failed_rules": [r.get("rule_title") for r in failed_controls[:5]],
                "significant_patterns": significant_patterns,
                "transaction_amount": transaction.get("amount"),
                "transaction_currency": transaction.get("currency"),
                "sender_country": transaction.get("sender_country"),
                "receiver_country": transaction.get("receiver_country"),
            }
            
            # 6. Build evidence summary
            evidence = {
                "control_failures": [
                    {
                        "rule_id": r.get("rule_id"),
                        "rule_title": r.get("rule_title"),
                        "severity": r.get("severity"),
                        "rationale": r.get("rationale")
                    }
                    for r in failed_controls[:5]  # Top 5 failures
                ],
                "pattern_scores": {k: v for k, v in pattern_scores.items() if v > 40},
            }
            
            # 7. Create alerts for each role (deduplicated by role)
            transaction_id = transaction.get("transaction_id")
            
            for role in roles_to_alert:
                alert = {
                    "transaction_id": transaction_id,
                    "role": role,
                    "severity": alert_severity,
                    "alert_type": "transaction_risk",
                    "title": f"Transaction Risk Alert: {risk_band}",
                    "description": (
                        f"Transaction {transaction_id} flagged with {risk_band} risk "
                        f"(score: {risk_score:.2f}). "
                        f"{len(failed_controls)} control failures detected."
                    ),
                    "context": context,
                    "evidence": evidence,
                    "sla_deadline": sla_deadline.isoformat(),
                    "sla_hours": sla_hours,
                }
                alerts_generated.append(alert)
            
            state["alerts_generated"] = alerts_generated
            state["alert_composer_executed"] = True
            
            self.logger.info(
                f"Generated {len(alerts_generated)} alerts: "
                f"severity={alert_severity}, roles={roles_to_alert}"
            )

        except Exception as e:
            self.logger.error(f"Error in AlertComposerAgent: {str(e)}", exc_info=True)
            state["alerts_generated"] = []
            state["errors"] = state.get("errors", []) + [f"AlertComposerAgent: {str(e)}"]

        return state
