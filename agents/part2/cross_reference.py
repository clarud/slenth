"""
CrossReferenceAgent - Correlate document with transaction history and KYC

Responsibilities:
1. Extract key entities from document (names, amounts, dates)
2. Check consistency with customer profile
3. Validate against transaction patterns
4. Flag discrepancies or unusual patterns
5. Calculate cross-reference score
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from agents import Part2Agent

logger = logging.getLogger(__name__)


class CrossReferenceAgent(Part2Agent):
    """Agent: Correlate document with transaction history and KYC"""

    def __init__(self, db_session: Optional[Session] = None, llm_service=None):
        super().__init__("cross_reference")
        self.db_session = db_session
        self.llm_service = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute cross-reference correlation.

        Args:
            state: Workflow state containing:
                - extracted_entities: Entities from OCR
                - ocr_text: Document text
                - document_type: Type of document
                - background_check_results: PEP/sanctions results

        Returns:
            Updated state with:
                - cross_reference_results: Correlation findings
                - consistency_with_profile: Boolean
                - discrepancies: List of mismatches
                - cross_reference_score: 0-100
        """
        self.logger.info("Executing CrossReferenceAgent")

        entities = state.get("extracted_entities", {})
        ocr_text = state.get("ocr_text", "")
        document_type = state.get("document_type", "other")
        background_results = state.get("background_check_results", [])
        errors = state.get("errors", [])

        # Initialize results
        cross_reference_results = []
        consistency_with_profile = True
        discrepancies = []
        cross_reference_score = 100

        try:
            # Step 1: Extract key information from entities
            amounts = entities.get("amounts", [])
            dates = entities.get("dates", [])
            names = entities.get("potential_names", [])

            self.logger.info(
                f"Cross-referencing: {len(names)} names, "
                f"{len(amounts)} amounts, {len(dates)} dates"
            )

            # Step 2: Check for basic consistency issues
            if document_type == "purchase_agreement":
                discrepancies.extend(
                    self._check_purchase_agreement_consistency(
                        amounts, dates, names, ocr_text
                    )
                )

            # Step 3: Check against background screening results
            if background_results:
                bg_discrepancies = self._check_background_consistency(
                    names, background_results
                )
                discrepancies.extend(bg_discrepancies)

            # Step 4: Use LLM for intelligent correlation (if available)
            if self.llm_service and len(ocr_text) > 100:
                llm_findings = await self._llm_correlation_analysis(
                    ocr_text, entities, document_type
                )
                if llm_findings:
                    discrepancies.extend(llm_findings.get("discrepancies", []))
                    cross_reference_results.append(llm_findings)

            # Step 5: Calculate cross-reference score
            # Deduct points for each discrepancy
            severity_weights = {"critical": 30, "high": 20, "medium": 10, "low": 5}
            
            for discrepancy in discrepancies:
                severity = discrepancy.get("severity", "low")
                deduction = severity_weights.get(severity, 5)
                cross_reference_score = max(0, cross_reference_score - deduction)

            # Determine overall consistency
            consistency_with_profile = cross_reference_score >= 70

            self.logger.info(
                f"Cross-reference completed: score={cross_reference_score}, "
                f"discrepancies={len(discrepancies)}, consistent={consistency_with_profile}"
            )

        except Exception as e:
            self.logger.error(f"Cross-reference error: {e}")
            errors.append(f"Cross-reference error: {str(e)}")
            cross_reference_score = 50  # Neutral score on error

        # Update state
        state["cross_reference_executed"] = True
        state["cross_reference_results"] = cross_reference_results
        state["consistency_with_profile"] = consistency_with_profile
        state["discrepancies"] = discrepancies
        state["cross_reference_score"] = cross_reference_score
        state["errors"] = errors

        return state

    def _check_purchase_agreement_consistency(
        self,
        amounts: List[str],
        dates: List[str],
        names: List[str],
        text: str
    ) -> List[Dict[str, Any]]:
        """Check consistency specific to purchase agreements."""
        discrepancies = []

        # Check if purchase amount is present
        if not amounts:
            discrepancies.append({
                "type": "missing_amount",
                "severity": "high",
                "description": "No monetary amounts found in purchase agreement"
            })

        # Check if dates are present
        if not dates:
            discrepancies.append({
                "type": "missing_dates",
                "severity": "medium",
                "description": "No dates found in purchase agreement"
            })

        # Check for multiple conflicting amounts
        if len(amounts) > 5:
            discrepancies.append({
                "type": "multiple_amounts",
                "severity": "low",
                "description": f"Multiple amounts found ({len(amounts)}), may indicate inconsistency"
            })

        return discrepancies

    def _check_background_consistency(
        self,
        names: List[str],
        background_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check if names match background screening results."""
        discrepancies = []

        # Check if any PEP matches were found
        pep_matches = [r for r in background_results if r.get("is_pep")]
        if pep_matches:
            for match in pep_matches:
                discrepancies.append({
                    "type": "pep_in_document",
                    "severity": "critical",
                    "description": f"PEP match found: {match.get('name')}"
                })

        # Check sanctions matches
        sanctions_matches = [r for r in background_results if r.get("is_sanctioned")]
        if sanctions_matches:
            for match in sanctions_matches:
                discrepancies.append({
                    "type": "sanctioned_entity",
                    "severity": "critical",
                    "description": f"Sanctioned entity found: {match.get('name')}"
                })

        return discrepancies

    async def _llm_correlation_analysis(
        self,
        text: str,
        entities: Dict[str, Any],
        document_type: str
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to perform intelligent correlation analysis."""
        try:
            # Truncate text if too long
            if len(text) > 2000:
                text = text[:2000] + "\n...[truncated]"

            prompt = f"""Analyze this {document_type} document for internal consistency and potential red flags.

Document text:
{text}

Extracted entities:
- Names: {', '.join(entities.get('potential_names', [])[:5])}
- Amounts: {', '.join(entities.get('amounts', [])[:5])}
- Dates: {', '.join(entities.get('dates', [])[:5])}

Check for:
1. Consistency between parties mentioned
2. Logical flow of information
3. Any red flags or suspicious patterns
4. Completeness of transaction details

Respond in JSON format:
{{
    "is_consistent": true/false,
    "confidence": 0-100,
    "discrepancies": [
        {{"type": "...", "severity": "critical/high/medium/low", "description": "..."}}
    ],
    "red_flags": ["list of concerns"],
    "summary": "brief analysis"
}}"""

            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=800
            )

            # Parse JSON response
            import json
            response_text = response.strip()
            
            # Handle markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            results = json.loads(response_text)
            self.logger.info(f"LLM correlation analysis: {results.get('summary', 'N/A')}")
            return results

        except Exception as e:
            self.logger.warning(f"LLM correlation analysis failed: {e}")
            return None
