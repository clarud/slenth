"""
DocumentRiskAgent - Aggregate findings and calculate overall document risk score.
"""

import logging
from typing import Any, Dict, List

from agents import Part2Agent

logger = logging.getLogger(__name__)


class DocumentRiskAgent(Part2Agent):
    """Agent: Aggregate findings and calculate doc risk score"""

    # Risk band thresholds
    RISK_BANDS = {
        "LOW": (0, 30),
        "MEDIUM": (31, 60),
        "HIGH": (61, 85),
        "CRITICAL": (86, 100),
    }

    # Component weights for risk calculation (quality scores, 0-100)
    DEFAULT_WEIGHTS = {
        "format_validation": 0.20,
        "nlp_validation": 0.20,
        "pdf_forensics": 0.30,
        "background_check": 0.25,
        "ocr_quality": 0.05,
    }

    def __init__(self) -> None:
        super().__init__("document_risk")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute risk aggregation and assessment.

        Inputs in state (if available):
          - completeness_score, consistency_score, integrity_score,
            background_risk_score, text_length/has_text, pep_found, sanctions_found

        Outputs in state:
          - overall_risk_score, risk_band, component_scores, risk_factors,
            recommendations, requires_manual_review
        """
        self.logger.info("Executing DocumentRiskAgent")

        errors: List[str] = state.get("errors", [])

        # Initialize results
        component_scores: Dict[str, float] = {}
        risk_factors: List[Dict[str, Any]] = []
        recommendations: List[Dict[str, str]] = []
        overall_risk_score = 0.0
        risk_band = "UNKNOWN"
        requires_manual_review = False

        try:
            component_scores = self._collect_component_scores(state)
            overall_risk_score = self._calculate_weighted_risk(component_scores)
            risk_band = self._determine_risk_band(overall_risk_score)
            risk_factors = self._extract_risk_factors(state, component_scores)
            recommendations = self._generate_recommendations(risk_band, risk_factors)
            requires_manual_review = (
                risk_band in {"HIGH", "CRITICAL"}
                or any(f.get("severity") in {"high", "critical"} for f in risk_factors)
            )
        except Exception as e:
            self.logger.error(f"Document risk assessment error: {e}")
            errors.append(f"document_risk_error: {str(e)}")
            overall_risk_score = 100.0
            risk_band = "CRITICAL"
            requires_manual_review = True

        # Update state
        state["overall_risk_score"] = overall_risk_score
        state["risk_band"] = risk_band
        state["component_scores"] = component_scores
        state["risk_factors"] = risk_factors
        state["recommendations"] = recommendations
        state["requires_manual_review"] = requires_manual_review
        state["errors"] = errors
        state["document_risk_executed"] = True

        return state

    def _collect_component_scores(self, state: Dict[str, Any]) -> Dict[str, float]:
        scores: Dict[str, float] = {}

        if state.get("format_valid") is not None:
            scores["format_validation"] = float(state.get("completeness_score", 0))

        if state.get("nlp_valid") is not None:
            scores["nlp_validation"] = float(state.get("consistency_score", 0))

        if state.get("pdf_forensics_executed"):
            scores["pdf_forensics"] = float(state.get("integrity_score", 0))

        if state.get("background_check_results") is not None:
            bg_score = float(state.get("background_risk_score", 0))
            if state.get("pep_found") or state.get("sanctions_found"):
                bg_score = min(100.0, bg_score + 50.0)
            scores["background_check"] = bg_score

        if state.get("has_text") is not None:
            text_length = int(state.get("text_length", 0))
            if text_length < 100:
                scores["ocr_quality"] = 0.0
            elif text_length < 500:
                scores["ocr_quality"] = 50.0
            else:
                scores["ocr_quality"] = 100.0

        return scores

    def _calculate_weighted_risk(self, component_scores: Dict[str, float]) -> float:
        if not component_scores:
            return 100.0

        total_weighted_risk = 0.0
        total_weight = 0.0
        for component, score in component_scores.items():
            weight = self.DEFAULT_WEIGHTS.get(component, 0.0)
            if weight <= 0:
                continue
            risk = 100.0 - float(score)  # quality -> risk
            total_weighted_risk += risk * weight
            total_weight += weight

        if total_weight <= 0:
            return 100.0
        overall = total_weighted_risk / total_weight
        return round(min(100.0, max(0.0, overall)), 1)

    def _determine_risk_band(self, risk_score: float) -> str:
        for band, (low, high) in self.RISK_BANDS.items():
            if low <= risk_score <= high:
                return band
        return "UNKNOWN"

    def _extract_risk_factors(self, state: Dict[str, Any], component_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        factors: List[Dict[str, Any]] = []

        if state.get("tampering_detected"):
            factors.append({
                "type": "pdf_tampering",
                "severity": "critical",
                "description": "PDF shows signs of tampering",
            })

        st = state.get("software_trust_level")
        if st in {"suspicious", "image_editor"}:
            factors.append({
                "type": "suspicious_software",
                "severity": "high",
                "description": f"Creation software flagged: {st}",
            })

        if component_scores.get("pdf_forensics", 100.0) < 70.0:
            factors.append({
                "type": "low_integrity",
                "severity": "high",
                "description": f"Low integrity score: {component_scores.get('pdf_forensics', 0)}",
            })

        if component_scores.get("format_validation", 100.0) < 60.0:
            factors.append({
                "type": "incomplete_document",
                "severity": "medium",
                "description": "Document completeness below threshold",
            })

        if component_scores.get("nlp_validation", 100.0) < 60.0:
            factors.append({
                "type": "nlp_inconsistencies",
                "severity": "medium",
                "description": "Content inconsistencies detected",
            })

        if state.get("pep_found"):
            factors.append({
                "type": "pep_detected",
                "severity": "high",
                "description": "Politically Exposed Person matched",
            })
        if state.get("sanctions_found"):
            factors.append({
                "type": "sanctions_match",
                "severity": "critical",
                "description": "Sanctions list match detected",
            })

        return factors

    def _generate_recommendations(self, risk_band: str, factors: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        recs: List[Dict[str, str]] = []

        if risk_band in {"HIGH", "CRITICAL"}:
            recs.append({"action": "manual_review", "description": "Conduct manual review and verify sources"})
        elif risk_band == "MEDIUM":
            recs.append({"action": "additional_checks", "description": "Request supporting documents and cross-check"})
        else:
            recs.append({"action": "proceed", "description": "Proceed with standard controls"})

        for f in factors:
            t = f.get("type")
            if t == "pdf_tampering":
                recs.append({"action": "request_original", "description": "Request original/certified PDF copy"})
            elif t == "suspicious_software":
                recs.append({"action": "confirm_generation_process", "description": "Confirm how the document was generated"})
            elif t == "pep_detected":
                recs.append({"action": "enhanced_due_diligence", "description": "Perform EDD, seek senior approval"})
            elif t == "sanctions_match":
                recs.append({"action": "block_and_escalate", "description": "Block processing and escalate to compliance"})

        return recs

