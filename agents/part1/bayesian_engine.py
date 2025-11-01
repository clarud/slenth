"""
BayesianEngineAgent - Sequential Bayesian posterior update for entity risk

Logic:

1. Load prior risk distribution for customer
2. Update posterior based on transaction evidence
3. Consider rule violations, patterns, features
4. Output posterior probabilities for risk categories


Output:
bayesian_posterior: Dict[risk_category] -> probability
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService

logger = logging.getLogger(__name__)


class BayesianEngineAgent(Part1Agent):
    """Agent: Sequential Bayesian posterior update for entity risk"""

    def __init__(self, llm_service: LLMService = None):
        super().__init__("bayesian_engine")
        self.llm = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute bayesian_engine agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with Bayesian posterior probabilities
        """
        self.logger.info("Executing BayesianEngineAgent")

        try:
            transaction = state.get("transaction", {})
            control_results = state.get("control_results", [])
            features = state.get("features", {})
            
            # 1. Load prior risk distribution for customer
            customer_risk_rating = transaction.get("customer_risk_rating", "medium")
            
            # Map customer rating to prior probabilities
            prior_distribution = {
                "low": {"low": 0.70, "medium": 0.20, "high": 0.08, "critical": 0.02},
                "medium": {"low": 0.40, "medium": 0.35, "high": 0.20, "critical": 0.05},
                "high": {"low": 0.15, "medium": 0.30, "high": 0.40, "critical": 0.15},
                "critical": {"low": 0.05, "medium": 0.15, "high": 0.40, "critical": 0.40},
            }
            
            prior = prior_distribution.get(customer_risk_rating.lower(), prior_distribution["medium"])
            
            # 2. Calculate likelihood ratios based on evidence
            
            # Evidence from control test failures
            failed_controls = [r for r in control_results if r.get("status") == "fail"]
            critical_failures = [r for r in failed_controls if r.get("severity") == "critical"]
            high_failures = [r for r in failed_controls if r.get("severity") == "high"]
            
            # Likelihood multipliers (how much this evidence increases risk)
            lr_critical_failure = 5.0  # Critical failure strongly suggests high risk
            lr_high_failure = 3.0
            lr_med_failure = 1.5
            
            # Evidence from features
            is_high_value = features.get("is_high_value", False)
            is_cross_border = features.get("is_cross_border", False)
            is_high_risk_country = features.get("is_high_risk_country", False)
            potential_structuring = features.get("potential_structuring", False)
            
            lr_high_value = 1.5 if is_high_value else 1.0
            lr_cross_border = 1.3 if is_cross_border else 1.0
            lr_high_risk_country = 2.5 if is_high_risk_country else 1.0
            lr_structuring = 4.0 if potential_structuring else 1.0
            
            # 3. Update posterior using Bayes' theorem
            # For each risk category, multiply prior by likelihood ratios
            
            posterior = {
                "low": prior["low"],
                "medium": prior["medium"],
                "high": prior["high"],
                "critical": prior["critical"]
            }
            
            # Apply evidence from control failures
            if critical_failures:
                # Critical failures shift probability mass to high/critical
                posterior["critical"] *= lr_critical_failure * len(critical_failures)
                posterior["high"] *= lr_critical_failure * 0.5
                posterior["medium"] *= 0.5
                posterior["low"] *= 0.2
            
            if high_failures:
                posterior["critical"] *= lr_high_failure * 0.3
                posterior["high"] *= lr_high_failure * len(high_failures)
                posterior["medium"] *= 0.7
                posterior["low"] *= 0.3
            
            if len(failed_controls) > len(critical_failures) + len(high_failures):
                # Medium severity failures
                med_failures_count = len(failed_controls) - len(critical_failures) - len(high_failures)
                posterior["high"] *= lr_med_failure * 0.5
                posterior["medium"] *= lr_med_failure * med_failures_count
                posterior["low"] *= 0.7
            
            # Apply evidence from transaction features
            if is_high_value:
                posterior["high"] *= lr_high_value
                posterior["medium"] *= lr_high_value * 0.8
            
            if is_cross_border:
                posterior["medium"] *= lr_cross_border
                posterior["high"] *= lr_cross_border
            
            if is_high_risk_country:
                posterior["critical"] *= lr_high_risk_country
                posterior["high"] *= lr_high_risk_country
                posterior["medium"] *= lr_high_risk_country * 0.5
                posterior["low"] *= 0.3
            
            if potential_structuring:
                posterior["critical"] *= lr_structuring
                posterior["high"] *= lr_structuring * 0.8
                posterior["medium"] *= lr_structuring * 0.5
                posterior["low"] *= 0.2
            
            # 4. Normalize to ensure probabilities sum to 1.0
            total = sum(posterior.values())
            if total > 0:
                posterior = {k: v / total for k, v in posterior.items()}
            else:
                # Fallback to prior if something went wrong
                posterior = prior.copy()
            
            # Store results
            state["bayesian_posterior"] = posterior
            state["bayesian_prior"] = prior
            state["bayesian_engine_executed"] = True
            
            # Log results
            max_risk = max(posterior.items(), key=lambda x: x[1])
            self.logger.info(
                f"Bayesian analysis: {max_risk[0]} risk ({max_risk[1]:.2%} probability), "
                f"based on {len(failed_controls)} failures, customer_rating={customer_risk_rating}"
            )

        except Exception as e:
            self.logger.error(f"Error in BayesianEngineAgent: {str(e)}", exc_info=True)
            # Fallback to neutral posterior
            state["bayesian_posterior"] = {"low": 0.25, "medium": 0.50, "high": 0.20, "critical": 0.05}
            state["errors"] = state.get("errors", []) + [f"BayesianEngineAgent: {str(e)}"]

        return state
