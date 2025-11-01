"""
FeatureServiceAgent - Generate deterministic features from transaction + history

Logic:

1. Velocity features: transaction frequency, amount patterns
2. Structuring indicators: amounts just below thresholds
3. Round-trip patterns: circular transfers
4. Geographic risk: high-risk jurisdictions
5. Customer behavior: deviations from profile


Output:
features: Dict with feature vectors and flags
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService

logger = logging.getLogger(__name__)


class FeatureServiceAgent(Part1Agent):
    """Agent: Generate deterministic features from transaction + history"""

    def __init__(self, llm_service: LLMService = None):
        super().__init__("feature_service")
        self.llm = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute feature_service agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with extracted features
        """
        self.logger.info("Executing FeatureServiceAgent")

        try:
            transaction = state.get("transaction", {})
            transaction_history = state.get("transaction_history", [])
            
            features = {}
            
            # Basic transaction features
            features["amount"] = float(transaction.get("amount", 0))
            features["is_high_value"] = features["amount"] > 10000
            features["is_round_number"] = features["amount"] % 1000 == 0
            
            # Velocity features from history
            if transaction_history:
                features["transaction_count_24h"] = len([t for t in transaction_history if t.get("hours_ago", 999) < 24])
                features["transaction_count_7d"] = len(transaction_history)
                total_amount = sum([float(t.get("amount", 0)) for t in transaction_history])
                features["total_volume_7d"] = total_amount
                features["avg_amount_7d"] = total_amount / len(transaction_history) if transaction_history else 0
            else:
                features["transaction_count_24h"] = 0
                features["transaction_count_7d"] = 0
                features["total_volume_7d"] = 0
                features["avg_amount_7d"] = 0
            
            # Geographic features
            originator_country = transaction.get("originator_country", "")
            beneficiary_country = transaction.get("beneficiary_country", "")
            
            features["is_cross_border"] = originator_country != beneficiary_country
            
            # High-risk countries (FATF grey/black lists and common AML concern countries)
            high_risk_countries = {
                "AF", "AL", "BB", "BF", "KH", "KY", "CI", "HT", "IR", "IQ", "JM", "JO", 
                "KP", "LB", "LY", "ML", "MM", "NI", "PK", "PA", "PH", "RU", "SN", "SO",
                "SS", "SD", "SY", "TT", "TR", "UG", "AE", "VE", "YE", "ZW"
            }
            features["is_high_risk_country"] = (
                beneficiary_country in high_risk_countries or 
                originator_country in high_risk_countries
            )
            
            # Structuring indicators
            features["potential_structuring"] = (
                features["is_high_value"] and 
                features["is_round_number"] and 
                features["transaction_count_24h"] > 3
            )
            
            state["features"] = features
            state["feature_service_completed"] = True
            self.logger.info(f"Extracted {len(features)} features")

        except Exception as e:
            self.logger.error(f"Error in FeatureServiceAgent: {str(e)}", exc_info=True)
            state["features"] = {}
            state["errors"] = state.get("errors", []) + [f"FeatureServiceAgent: {str(e)}"]

        return state
