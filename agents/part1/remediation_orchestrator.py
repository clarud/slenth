"""
RemediationOrchestratorAgent - Suggest remediation actions with owners and SLAs

Logic:

1. Map findings to remediation playbooks
2. Assign action owners (Front/Compliance/Legal)
3. Set SLA deadlines
4. Create cases if needed
5. Link alerts to cases


Output:
remediation_actions: List[Dict] with action, owner, sla
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService

logger = logging.getLogger(__name__)


class RemediationOrchestratorAgent(Part1Agent):
    """Agent: Suggest remediation actions with owners and SLAs"""

    def __init__(self, llm_service: LLMService = None):
        super().__init__("remediation_orchestrator")
        self.llm = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute remediation_orchestrator agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with remediation actions
        """
        self.logger.info("Executing RemediationOrchestratorAgent")

        try:
            transaction = state.get("transaction", {})
            risk_score = state.get("risk_score", 0.0)
            risk_band = state.get("risk_band", "Low")
            control_results = state.get("control_results", [])
            alerts_generated = state.get("alerts_generated", [])
            
            remediation_actions = []
            
            # Only generate remediation actions if there are alerts (risk >= 30)
            if not alerts_generated:
                self.logger.info("No alerts generated, skipping remediation")
                state["remediation_actions"] = []
                state["remediation_orchestrator_executed"] = True
                return state
            
            failed_controls = [r for r in control_results if r.get("status") == "fail"]
            partial_controls = [r for r in control_results if r.get("status") == "partial"]
            
            from datetime import datetime, timedelta
            
            # 1. Map findings to remediation playbooks
            
            # Action 1: Investigation for Medium+ risk
            if risk_score >= 30:
                action = {
                    "action_type": "INVESTIGATE",
                    "title": "Investigate Transaction",
                    "description": (
                        f"Conduct enhanced investigation of transaction {transaction.get('transaction_id')} "
                        f"due to {risk_band} risk rating."
                    ),
                    "owner": "COMPLIANCE",
                    "priority": risk_band,
                    "sla_hours": 48 if risk_band == "Medium" else 24,
                    "sla_deadline": (datetime.utcnow() + timedelta(
                        hours=48 if risk_band == "Medium" else 24
                    )).isoformat(),
                    "details": {
                        "risk_score": risk_score,
                        "failed_controls": len(failed_controls),
                        "investigation_areas": [
                            "Source of funds verification",
                            "Beneficiary identity confirmation",
                            "Transaction purpose documentation"
                        ]
                    }
                }
                remediation_actions.append(action)
            
            # Action 2: Enhanced Due Diligence for High+ risk
            if risk_score >= 60:
                action = {
                    "action_type": "ENHANCED_DD",
                    "title": "Enhanced Due Diligence Required",
                    "description": (
                        f"Perform Enhanced Due Diligence (EDD) on customer "
                        f"{transaction.get('customer_id')} due to High/Critical risk transaction."
                    ),
                    "owner": "COMPLIANCE",
                    "priority": "HIGH",
                    "sla_hours": 24,
                    "sla_deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                    "details": {
                        "customer_id": transaction.get("customer_id"),
                        "edd_requirements": [
                            "Update KYC documentation",
                            "Verify source of wealth",
                            "Review transaction history",
                            "Assess PEP status"
                        ]
                    }
                }
                remediation_actions.append(action)
            
            # Action 3: Collect Missing Documentation
            if failed_controls:
                missing_info = []
                for control in failed_controls:
                    rationale = control.get("rationale", "").lower()
                    if "missing" in rationale or "lacks" in rationale:
                        # Extract what's missing from rationale
                        if "purpose" in rationale:
                            missing_info.append("Transaction purpose documentation")
                        if "sender" in rationale or "originator" in rationale:
                            missing_info.append("Sender identification documents")
                        if "receiver" in rationale or "beneficiary" in rationale:
                            missing_info.append("Beneficiary details and purpose")
                        if "kyc" in rationale:
                            missing_info.append("Updated KYC documents")
                
                if missing_info:
                    action = {
                        "action_type": "COLLECT_DOCUMENTS",
                        "title": "Collect Missing Documentation",
                        "description": (
                            f"Request and collect missing documentation for transaction "
                            f"{transaction.get('transaction_id')}."
                        ),
                        "owner": "FRONT_OFFICE",
                        "priority": "MEDIUM",
                        "sla_hours": 48,
                        "sla_deadline": (datetime.utcnow() + timedelta(hours=48)).isoformat(),
                        "details": {
                            "missing_documents": list(set(missing_info)),
                            "contact": transaction.get("customer_id"),
                        }
                    }
                    remediation_actions.append(action)
            
            # Action 4: SAR Filing for Critical risk
            if risk_score >= 80:
                action = {
                    "action_type": "FILE_SAR",
                    "title": "File Suspicious Activity Report",
                    "description": (
                        f"Prepare and file SAR for transaction {transaction.get('transaction_id')} "
                        f"due to Critical risk indicators."
                    ),
                    "owner": "LEGAL",
                    "priority": "CRITICAL",
                    "sla_hours": 12,
                    "sla_deadline": (datetime.utcnow() + timedelta(hours=12)).isoformat(),
                    "details": {
                        "transaction_id": transaction.get("transaction_id"),
                        "customer_id": transaction.get("customer_id"),
                        "amount": transaction.get("amount"),
                        "currency": transaction.get("currency"),
                        "red_flags": [
                            f"Risk score: {risk_score}/100",
                            f"Failed {len(failed_controls)} AML controls",
                            f"Risk band: {risk_band}"
                        ]
                    }
                }
                remediation_actions.append(action)
            
            # Action 5: Review Partial Passes
            if partial_controls and risk_score >= 40:
                action = {
                    "action_type": "REVIEW",
                    "title": "Review Partial Control Passes",
                    "description": (
                        f"Review {len(partial_controls)} controls that partially passed "
                        f"to determine if additional action needed."
                    ),
                    "owner": "COMPLIANCE",
                    "priority": "LOW",
                    "sla_hours": 72,
                    "sla_deadline": (datetime.utcnow() + timedelta(hours=72)).isoformat(),
                    "details": {
                        "partial_controls": [
                            {
                                "rule_id": c.get("rule_id"),
                                "rule_title": c.get("rule_title"),
                                "rationale": c.get("rationale")
                            }
                            for c in partial_controls[:3]
                        ]
                    }
                }
                remediation_actions.append(action)
            
            # 5. Link remediation actions to alerts
            for action in remediation_actions:
                action["linked_alerts"] = [
                    alert.get("transaction_id") for alert in alerts_generated
                ]
            
            state["remediation_actions"] = remediation_actions
            state["remediation_orchestrator_executed"] = True
            
            self.logger.info(
                f"Generated {len(remediation_actions)} remediation actions for {risk_band} risk"
            )

        except Exception as e:
            self.logger.error(f"Error in RemediationOrchestratorAgent: {str(e)}", exc_info=True)
            state["remediation_actions"] = []
            state["errors"] = state.get("errors", []) + [f"RemediationOrchestratorAgent: {str(e)}"]

        return state
