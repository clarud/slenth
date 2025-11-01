"""
ControlTestAgent - Test each control/rule: pass/fail/partial

Logic:

1. For each applicable rule
2. Test control based on evidence
3. Assign severity (critical/high/medium/low)
4. Compute per-rule compliance score


Output:
control_results: List[Dict] with rule_id, status, severity, score
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService

logger = logging.getLogger(__name__)


class ControlTestAgent(Part1Agent):
    """Agent: Test each control/rule: pass/fail/partial"""

    def __init__(self, llm_service: LLMService = None):
        super().__init__("control_test")
        self.llm = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute control_test agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with control test results
        """
        self.logger.info("Executing ControlTestAgent")

        try:
            applicable_rules = state.get("applicable_rules_filtered", [])
            transaction = state.get("transaction", {})
            evidence_map = state.get("evidence_map", {})

            if not applicable_rules:
                self.logger.warning("No applicable rules to test")
                state["control_results"] = []
                return state

            control_results = []

            for rule in applicable_rules:
                rule_id = rule.get("rule_id")
                rule_severity = rule.get("severity", "medium")

                # Build prompt for LLM to test control
                prompt = f"""You are a compliance analyst testing if this transaction passes regulatory controls.

RULE: {rule.get('title')}
Description: {rule.get('description')}
Severity: {rule_severity}

TRANSACTION:
- Type: {transaction.get('transaction_type')}
- Amount: {transaction.get('amount')} {transaction.get('currency')}
- Sender: {transaction.get('sender_account')} ({transaction.get('sender_country')})
- Receiver: {transaction.get('receiver_account')} ({transaction.get('receiver_country')})
- Purpose: {transaction.get('purpose', 'N/A')}

EVIDENCE AVAILABLE:
{evidence_map.get(rule_id, 'No specific evidence mapped')}

Determine if the transaction passes this control. Respond in JSON:
{{
    "status": "pass" | "fail" | "partial",
    "rationale": "brief explanation",
    "compliance_score": 0-100
}}"""

                try:
                    response = await self.llm.generate(
                        prompt=prompt,
                        response_format="json",
                        max_tokens=400,
                    )

                    import json
                    import re
                    
                    # Validate response is not empty
                    if not response or not response.strip():
                        self.logger.warning(f"Empty response from LLM for rule {rule_id}")
                        result = {
                            "status": "partial",
                            "rationale": "No LLM response received",
                            "compliance_score": 50
                        }
                    else:
                        try:
                            result = json.loads(response)
                        except json.JSONDecodeError as je:
                            self.logger.error(f"JSON parse error for rule {rule_id}: {je}")
                            self.logger.debug(f"Raw response (first 200 chars): {response[:200]}")
                            
                            # Try to extract JSON from mixed text response
                            json_match = re.search(r'\{.*\}', response, re.DOTALL)
                            if json_match:
                                try:
                                    result = json.loads(json_match.group())
                                    self.logger.info(f"Successfully extracted JSON from mixed response")
                                except:
                                    # Give up and use default
                                    result = {
                                        "status": "partial",
                                        "rationale": f"Parse error: {str(je)[:100]}",
                                        "compliance_score": 50
                                    }
                            else:
                                result = {
                                    "status": "partial",
                                    "rationale": f"No valid JSON found in response",
                                    "compliance_score": 50
                                }

                    control_results.append({
                        "rule_id": rule_id,
                        "rule_title": rule.get("title", ""),
                        "status": result.get("status", "partial"),
                        "severity": rule_severity,
                        "compliance_score": result.get("compliance_score", 50),
                        "rationale": result.get("rationale", ""),
                    })

                    self.logger.info(
                        f"Control test for {rule_id}: {result.get('status')} "
                        f"(score: {result.get('compliance_score')})"
                    )

                except Exception as e:
                    self.logger.error(f"Unexpected error testing control for rule {rule_id}: {e}")
                    control_results.append({
                        "rule_id": rule_id,
                        "rule_title": rule.get("title", ""),
                        "status": "partial",
                        "severity": rule_severity,
                        "compliance_score": 50,
                        "rationale": f"Error in control test: {str(e)}",
                    })

            state["control_results"] = control_results
            state["control_test_completed"] = True

            self.logger.info(f"Completed control tests for {len(control_results)} rules")

        except Exception as e:
            self.logger.error(f"Error in ControlTestAgent: {str(e)}", exc_info=True)
            state["control_results"] = []
            state["errors"] = state.get("errors", []) + [f"ControlTestAgent: {str(e)}"]

        return state
