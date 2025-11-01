"""
ApplicabilityAgent - Determine if each retrieved rule applies to transaction

Logic:

1. For each rule from Retrieval agent
2. Use LLM to determine applicability
3. Provide rationale and confidence score
4. Filter to only applicable rules


Output:
applicable_rules_filtered: List with applies=True, rationale, confidence
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService

logger = logging.getLogger(__name__)


class ApplicabilityAgent(Part1Agent):
    """Agent: Determine if each retrieved rule applies to transaction"""

    def __init__(self, llm_service: LLMService = None):
        super().__init__("applicability")
        self.llm = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute applicability agent logic using LLM.

        Args:
            state: Workflow state

        Returns:
            Updated state with filtered applicable rules
        """
        self.logger.info("Executing ApplicabilityAgent")

        try:
            applicable_rules = state.get("applicable_rules", [])
            transaction = state.get("transaction", {})
            
            if not applicable_rules:
                self.logger.warning("No rules to check applicability")
                state["applicable_rules_filtered"] = []
                return state

            filtered_rules = []

            # Process each rule
            for rule in applicable_rules[:10]:  # Limit to top 10 for efficiency
                rule_id = rule.get("rule_id")
                rule_text = f"{rule.get('title', '')}: {rule.get('description', '')}"

                # Build prompt for LLM
                prompt = f"""You are a compliance expert. Determine if the following rule applies to this transaction.

RULE:
{rule_text}

TRANSACTION:
- Type: {transaction.get('transaction_type')}
- Amount: {transaction.get('amount')} {transaction.get('currency')}
- From: {transaction.get('sender_account')} ({transaction.get('sender_country')})
- To: {transaction.get('receiver_account')} ({transaction.get('receiver_country')})
- Purpose: {transaction.get('purpose', 'N/A')}

Respond in JSON format:
{{
    "applies": true/false,
    "rationale": "brief explanation",
    "confidence": 0.0-1.0
}}"""

                try:
                    response = await self.llm.generate(
                        prompt=prompt,
                        response_format="json",
                        max_tokens=300,
                    )

                    import json
                    result = json.loads(response)
                    
                    if result.get("applies", False):
                        filtered_rules.append({
                            **rule,
                            "applies": True,
                            "rationale": result.get("rationale", ""),
                            "confidence": result.get("confidence", 0.5),
                        })
                        self.logger.info(f"Rule {rule_id} applies (confidence: {result.get('confidence')})")

                except Exception as e:
                    self.logger.error(f"Error checking applicability for rule {rule_id}: {e}")
                    # Include with low confidence if error
                    filtered_rules.append({
                        **rule,
                        "applies": True,
                        "rationale": "Error in applicability check, included for review",
                        "confidence": 0.3,
                    })

            self.logger.info(f"Filtered {len(filtered_rules)} applicable rules from {len(applicable_rules)}")
            state["applicable_rules_filtered"] = filtered_rules
            state["applicability_completed"] = True

        except Exception as e:
            self.logger.error(f"Error in ApplicabilityAgent: {str(e)}", exc_info=True)
            state["applicable_rules_filtered"] = state.get("applicable_rules", [])
            state["errors"] = state.get("errors", []) + [f"ApplicabilityAgent: {str(e)}"]

        return state
