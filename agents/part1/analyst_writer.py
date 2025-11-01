"""
AnalystWriterAgent - Generate concise compliance analysis summary

Logic:

1. Summarize key findings from all agents
2. Include rule IDs and violations
3. Reference evidence
4. Provide rationale
5. Generate human-readable summary


Output:
compliance_summary: str, recommendations: List[str]
"""

import logging
from typing import Any, Dict

from agents import Part1Agent
from services.llm import LLMService

logger = logging.getLogger(__name__)


class AnalystWriterAgent(Part1Agent):
    """Agent: Generate concise compliance analysis summary"""

    def __init__(self, llm_service: LLMService = None):
        super().__init__("analyst_writer")
        self.llm = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute analyst_writer agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with analyst report
        """
        self.logger.info("Executing AnalystWriterAgent")

        try:
            transaction = state.get("transaction", {})
            control_results = state.get("control_results", [])
            risk_score = state.get("risk_score", 0.0)
            risk_band = state.get("risk_band", "Low")
            pattern_scores = state.get("pattern_scores", {})

            # Build comprehensive prompt for analyst report
            failed_controls = [r for r in control_results if r.get("status") == "fail"]
            partial_controls = [r for r in control_results if r.get("status") == "partial"]

            prompt = f"""You are a senior AML compliance analyst. Write a concise compliance analysis report for this transaction.

TRANSACTION DETAILS:
- Transaction ID: {transaction.get('transaction_id')}
- Type: {transaction.get('transaction_type')}
- Amount: {transaction.get('amount')} {transaction.get('currency')}
- Sender: {transaction.get('sender_account')} ({transaction.get('sender_country')})
- Receiver: {transaction.get('receiver_account')} ({transaction.get('receiver_country')})

RISK ASSESSMENT:
- Overall Risk Score: {risk_score}/100
- Risk Band: {risk_band}

CONTROL TEST RESULTS:
- Total Controls Tested: {len(control_results)}
- Failed: {len(failed_controls)}
- Partial Pass: {len(partial_controls)}
- Passed: {len([r for r in control_results if r.get('status') == 'pass'])}

FAILED CONTROLS:
{chr(10).join([f"- {r.get('rule_title')}: {r.get('rationale')}" for r in failed_controls[:5]]) if failed_controls else "None"}

PATTERN DETECTION:
{chr(10).join([f"- {k}: {v:.1f}" for k, v in pattern_scores.items() if v > 50]) if pattern_scores else "No significant patterns detected"}

Write a professional compliance report (300-500 words) that includes:
1. Executive Summary
2. Key Findings
3. Regulatory Concerns
4. Recommendations

Format as plain text with clear sections."""

            try:
                report = await self.llm.generate(
                    prompt=prompt,
                    max_tokens=800,
                    temperature=0.3,
                )

                state["analyst_report"] = report
                state["compliance_summary"] = report[:500]  # Short version

                # Generate recommendations
                recommendations = []
                if risk_score >= 80:
                    recommendations.append("URGENT: Escalate to senior compliance officer immediately")
                    recommendations.append("Freeze transaction pending further investigation")
                if risk_score >= 60:
                    recommendations.append("Request additional documentation from customer")
                    recommendations.append("Enhanced due diligence required")
                if failed_controls:
                    recommendations.append(f"Address {len(failed_controls)} failed compliance controls")
                if pattern_scores.get("structuring", 0) > 70:
                    recommendations.append("Investigate for potential structuring activity")

                state["recommendations"] = recommendations

                self.logger.info(f"Generated analyst report ({len(report)} chars, {len(recommendations)} recommendations)")

            except Exception as e:
                self.logger.error(f"Error generating report: {e}")
                state["analyst_report"] = f"Transaction {transaction.get('transaction_id')} assessed with {risk_band} risk (score: {risk_score}). {len(failed_controls)} controls failed."
                state["compliance_summary"] = state["analyst_report"]
                state["recommendations"] = []

            state["analyst_writer_completed"] = True

        except Exception as e:
            self.logger.error(f"Error in AnalystWriterAgent: {str(e)}", exc_info=True)
            state["analyst_report"] = "Error generating compliance report"
            state["compliance_summary"] = "Error generating summary"
            state["recommendations"] = []
            state["errors"] = state.get("errors", []) + [f"AnalystWriterAgent: {str(e)}"]

        return state
