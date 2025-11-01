"""
EvidenceMapperAgent - Map expected evidence from rules to transaction fields

Logic:

1. For each applicable rule
2. Extract expected_evidence fields
3. Map to concrete transaction fields
4. Identify present, missing, contradictory evidence


Output:
evidence_mapping: Dict[rule_id] -> {present, missing, contradictory}
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService

logger = logging.getLogger(__name__)


class EvidenceMapperAgent(Part1Agent):
    """Agent: Map expected evidence from rules to transaction fields"""

    def __init__(self, llm_service: LLMService = None):
        super().__init__("evidence_mapper")
        self.llm = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute evidence_mapper agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with evidence mappings
        """
        self.logger.info("Executing EvidenceMapperAgent")

        try:
            applicable_rules = state.get("applicable_rules_filtered", [])
            transaction = state.get("transaction", {})
            
            evidence_map = {}
            
            for rule in applicable_rules:
                rule_id = rule.get("rule_id")
                
                # Map transaction fields to evidence requirements
                evidence_map[rule_id] = {
                    "present": [
                        f"transaction_type: {transaction.get('transaction_type')}",
                        f"amount: {transaction.get('amount')} {transaction.get('currency')}",
                        f"sender_country: {transaction.get('sender_country')}",
                        f"receiver_country: {transaction.get('receiver_country')}",
                    ],
                    "missing": [],
                    "contradictory": [],
                }
                
                # Check for missing documentation based on amount thresholds
                if transaction.get("amount", 0) > 10000:
                    if not transaction.get("purpose"):
                        evidence_map[rule_id]["missing"].append("transaction_purpose")
                    if not transaction.get("documentation"):
                        evidence_map[rule_id]["missing"].append("supporting_documentation")
            
            state["evidence_map"] = evidence_map
            state["evidence_mapper_completed"] = True
            self.logger.info(f"Mapped evidence for {len(evidence_map)} rules")

        except Exception as e:
            self.logger.error(f"Error in EvidenceMapperAgent: {str(e)}", exc_info=True)
            state["evidence_map"] = {}
            state["errors"] = state.get("errors", []) + [f"EvidenceMapperAgent: {str(e)}"]

        return state
