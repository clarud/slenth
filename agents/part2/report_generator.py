"""
ReportGeneratorAgent - Generate comprehensive PDF report with findings and calculate risk score
"""

import logging
from typing import Any, Dict

from agents import Part2Agent

logger = logging.getLogger(__name__)


class ReportGeneratorAgent(Part2Agent):
    """Agent: Generate comprehensive PDF report with findings and calculate risk score"""

    def __init__(self):
        super().__init__("report_generator")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute report_generator agent logic and calculate risk score.

        Args:
            state: Workflow state

        Returns:
            Updated state with risk assessment
        """
        self.logger.info(f"📝 === EXECUTING ReportGeneratorAgent ===")

        # Calculate risk score from all findings
        self.logger.info(f"DEBUG: Calculating risk score from findings...")
        risk_score, risk_band, risk_factors = self._calculate_risk_score(state)
        
        self.logger.info(f"DEBUG: Calculated risk_score={risk_score}, risk_band={risk_band}")
        self.logger.info(f"DEBUG: risk_factors={risk_factors}")
        
        # Set risk values in state
        state["overall_risk_score"] = risk_score
        state["risk_band"] = risk_band
        state["risk_factors"] = risk_factors
        state["report_generator_executed"] = True

        self.logger.info(f"✅ ReportGenerator complete - Score: {risk_score}, Band: {risk_band}")

        return state

    def _calculate_risk_score(self, state: Dict[str, Any]) -> tuple[float, str, list]:
        """
        Calculate overall risk score based on all findings.
        
        Returns:
            (risk_score, risk_band, risk_factors)
        """
        risk_score = 0.0
        risk_factors = []
        
        # Get findings
        format_findings = state.get("format_findings", [])
        content_findings = state.get("content_findings", [])
        image_findings = state.get("image_findings", [])
        background_findings = state.get("background_check_findings", [])
        cross_ref_findings = state.get("cross_reference_findings", [])
        
        # Count findings by severity
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        
        all_findings = (
            format_findings + content_findings + image_findings + 
            background_findings + cross_ref_findings
        )
        
        for finding in all_findings:
            # Skip if finding is not a dict (could be a string)
            if not isinstance(finding, dict):
                continue
                
            severity = finding.get("severity", "low")
            if isinstance(severity, str):
                severity = severity.lower()
            else:
                severity = "low"
                
            if severity == "critical":
                critical_count += 1
                risk_score += 25
                risk_factors.append(f"Critical: {finding.get('type', 'Unknown')}")
            elif severity == "high":
                high_count += 1
                risk_score += 15
                risk_factors.append(f"High: {finding.get('type', 'Unknown')}")
            elif severity == "medium":
                medium_count += 1
                risk_score += 8
            elif severity == "low":
                low_count += 1
                risk_score += 3
        
        # Check for PEP/Sanctions
        pep_found = state.get("pep_found", False)
        sanctions_found = state.get("sanctions_found", False)
        
        if sanctions_found:
            risk_score += 40
            risk_factors.append("Sanctioned entity detected")
        elif pep_found:
            risk_score += 25
            risk_factors.append("PEP (Politically Exposed Person) detected")
        
        # Check NLP validation
        nlp_valid = state.get("nlp_valid", True)
        if not nlp_valid:
            risk_score += 15
            risk_factors.append("Semantic inconsistencies detected")
        
        # Cap at 100
        risk_score = min(risk_score, 100.0)
        
        # Determine risk band
        if risk_score >= 75:
            risk_band = "CRITICAL"
        elif risk_score >= 50:
            risk_band = "HIGH"
        elif risk_score >= 25:
            risk_band = "MEDIUM"
        else:
            risk_band = "LOW"
        
        return risk_score, risk_band, risk_factors
