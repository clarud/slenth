"""
PatternDetectorAgent - Detect temporal and network AML patterns

Logic:

1. Structuring: multiple transactions below threshold
2. Layering: complex transaction chains
3. Circular transfers: round-trip funds
4. Rapid movement: quick in-and-out
5. Velocity: unusual transaction frequency


Output:
patterns_detected: List[Dict] with pattern_type, confidence, description
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService

logger = logging.getLogger(__name__)


class PatternDetectorAgent(Part1Agent):
    """Agent: Detect temporal and network AML patterns"""

    def __init__(self, llm_service: LLMService = None):
        super().__init__("pattern_detector")
        self.llm = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute pattern_detector agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with pattern scores
        """
        self.logger.info("Executing PatternDetectorAgent")

        try:
            transaction = state.get("transaction", {})
            features = state.get("features", {})
            transaction_history = state.get("transaction_history", [])
            
            pattern_scores = {}
            
            # 1. Structuring: multiple transactions below threshold
            amount = features.get("amount", 0)
            count_24h = features.get("transaction_count_24h", 0)
            count_7d = features.get("transaction_count_7d", 0)
            
            structuring_score = 0.0
            if 9000 <= amount <= 10000:  # Just below reporting threshold
                structuring_score += 40.0
            if count_24h >= 3:
                structuring_score += 30.0
            if count_7d >= 10:
                structuring_score += 30.0
            pattern_scores["structuring"] = min(structuring_score, 100.0)
            
            # 2. Layering: complex transaction chains (requires network data)
            # Simplified: check for rapid succession of transactions
            layering_score = 0.0
            if count_24h >= 5:
                layering_score = 50.0
            if count_7d >= 20:
                layering_score = 70.0
            pattern_scores["layering"] = layering_score
            
            # 3. Circular transfers: round-trip funds (sender == previous receiver)
            circular_score = 0.0
            sender_account = transaction.get("sender_account", "")
            receiver_account = transaction.get("receiver_account", "")
            
            if transaction_history:
                # Check if current sender was a receiver in recent history
                for hist_txn in transaction_history[:5]:  # Check last 5 transactions
                    if hist_txn.get("receiver_account") == sender_account:
                        circular_score = 60.0
                        break
                    # Check for exact round-trip
                    if (hist_txn.get("sender_account") == receiver_account and 
                        hist_txn.get("receiver_account") == sender_account):
                        circular_score = 90.0
                        break
            pattern_scores["circular"] = circular_score
            
            # 4. Rapid movement: quick in-and-out (same-day transactions)
            rapid_score = 0.0
            same_day_count = sum(1 for t in transaction_history if t.get("hours_ago", 999) < 24)
            if same_day_count >= 5:
                rapid_score = 70.0
            elif same_day_count >= 3:
                rapid_score = 50.0
            pattern_scores["rapid_movement"] = rapid_score
            
            # 5. Velocity: unusual transaction frequency
            velocity_score = 0.0
            avg_7d = features.get("avg_amount_7d", 0)
            
            if count_24h >= 10:
                velocity_score = 80.0
            elif count_24h >= 5:
                velocity_score = 60.0
            elif count_24h >= 3:
                velocity_score = 40.0
            
            # Check for volume spike
            if avg_7d > 0 and amount > avg_7d * 3:
                velocity_score = max(velocity_score, 50.0)
            
            pattern_scores["velocity"] = velocity_score
            
            # Store results
            state["pattern_scores"] = pattern_scores
            state["pattern_detector_executed"] = True
            
            # Log detected patterns
            detected = [k for k, v in pattern_scores.items() if v > 40]
            if detected:
                self.logger.info(f"Patterns detected: {', '.join(detected)}")
            else:
                self.logger.info("No significant patterns detected")

        except Exception as e:
            self.logger.error(f"Error in PatternDetectorAgent: {str(e)}", exc_info=True)
            state["pattern_scores"] = {}
            state["errors"] = state.get("errors", []) + [f"PatternDetectorAgent: {str(e)}"]

        return state
