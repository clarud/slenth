"""
DecisionFusionAgent - Fuse rule-based, ML, and pattern scores into final risk

Logic:

1. Collect scores from control_test, bayesian_engine, pattern_detector
2. Apply weighted fusion
3. Compute final risk_score (0-100)
4. Determine risk_band (Low/Medium/High/Critical)


Output:
risk_score: float, risk_band: str
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService

logger = logging.getLogger(__name__)


class DecisionFusionAgent(Part1Agent):
    """Agent: Fuse rule-based, ML, and pattern scores into final risk"""

    def __init__(self, llm_service: LLMService = None):
        super().__init__("decision_fusion")
        self.llm = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute decision_fusion agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with risk_score and risk_band
        """
        self.logger.info("Executing DecisionFusionAgent")

        try:
            # Collect scores from previous agents
            control_results = state.get("control_results", [])
            bayesian_posterior = state.get("bayesian_posterior", {})
            pattern_scores = state.get("pattern_scores", {})

            # Calculate rule-based risk (from control tests)
            rule_based_score = 0.0
            if control_results:
                # Weight by severity
                severity_weights = {
                    "critical": 1.0,
                    "high": 0.7,
                    "medium": 0.4,
                    "low": 0.2,
                }
                
                total_weight = 0.0
                weighted_sum = 0.0
                
                for result in control_results:
                    status = result.get("status", "pass")
                    severity = result.get("severity", "medium")
                    weight = severity_weights.get(severity, 0.4)
                    
                    if status == "fail":
                        score = 100.0
                    elif status == "partial":
                        score = 50.0
                    else:
                        score = 0.0
                    
                    weighted_sum += score * weight
                    total_weight += weight
                
                if total_weight > 0:
                    rule_based_score = weighted_sum / total_weight

            # Calculate ML-based risk (from Bayesian engine)
            ml_score = 0.0
            if bayesian_posterior:
                # Convert posterior probabilities to risk score
                prob_low = bayesian_posterior.get("low", 0.0)
                prob_medium = bayesian_posterior.get("medium", 0.0)
                prob_high = bayesian_posterior.get("high", 0.0)
                prob_critical = bayesian_posterior.get("critical", 0.0)
                
                ml_score = (
                    prob_low * 10.0 +
                    prob_medium * 40.0 +
                    prob_high * 70.0 +
                    prob_critical * 95.0
                )

            # Calculate pattern-based risk
            pattern_score = 0.0
            if pattern_scores:
                structuring_score = pattern_scores.get("structuring", 0.0)
                layering_score = pattern_scores.get("layering", 0.0)
                circular_score = pattern_scores.get("circular", 0.0)
                velocity_score = pattern_scores.get("velocity", 0.0)
                
                pattern_score = max(
                    structuring_score,
                    layering_score,
                    circular_score,
                    velocity_score
                )

            # Weighted fusion (Rule: 40%, ML: 30%, Pattern: 30%)
            final_score = (
                rule_based_score * 0.40 +
                ml_score * 0.30 +
                pattern_score * 0.30
            )

            # Determine risk band
            if final_score >= 80:
                risk_band = "Critical"
            elif final_score >= 60:
                risk_band = "High"
            elif final_score >= 30:
                risk_band = "Medium"
            else:
                risk_band = "Low"

            self.logger.info(
                f"Decision fusion: score={final_score:.2f}, band={risk_band} "
                f"(rule={rule_based_score:.1f}, ml={ml_score:.1f}, pattern={pattern_score:.1f})"
            )

            state["risk_score"] = round(final_score, 2)
            state["risk_band"] = risk_band
            state["score_breakdown"] = {
                "rule_based": round(rule_based_score, 2),
                "ml_based": round(ml_score, 2),
                "pattern_based": round(pattern_score, 2),
            }
            state["decision_fusion_completed"] = True

        except Exception as e:
            self.logger.error(f"Error in DecisionFusionAgent: {str(e)}", exc_info=True)
            state["risk_score"] = 0.0
            state["risk_band"] = "Low"
            state["errors"] = state.get("errors", []) + [f"DecisionFusionAgent: {str(e)}"]

        return state
