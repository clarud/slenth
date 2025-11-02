"""
BackgroundCheckAgent - Dilisense API screening for PEP/sanctions

Responsibilities:
1. Extract person/entity names from OCR text
2. Screen individuals against Dilisense databases
3. Check for PEP (Politically Exposed Persons)
4. Check for sanctions list matches
5. Screen entities/organizations
6. Aggregate and score findings
"""

import logging
import re
from typing import Any, Dict, List, Tuple

from agents import Part2Agent
from config import settings
from services.dilisense import DilisenseService, MatchStatus, RiskLevel

logger = logging.getLogger(__name__)


class BackgroundCheckAgent(Part2Agent):
    """Agent: Dilisense API screening for PEP/sanctions"""

    def __init__(self):
        super().__init__("background_check")
        self.dilisense = DilisenseService()
        self.enabled = settings.enable_background_check

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute background check: screen entities against Dilisense.

        Args:
            state: Workflow state containing:
                - ocr_text: Extracted text from document
                - extracted_entities: Pre-extracted entities
                - document_id: Unique document ID

        Returns:
            Updated state with:
                - background_check_results: List of screening results
                - pep_found: Boolean if PEP detected
                - sanctions_found: Boolean if sanctioned entity found
                - background_risk_score: Risk score (0-100)
                - screened_entities: List of entities screened
        """
        self.logger.info("Executing BackgroundCheckAgent")

        errors = state.get("errors", [])
        
        if not self.enabled:
            self.logger.warning("Background check disabled")
            state["background_check_executed"] = True
            state["background_check_skipped"] = True
            return state

        ocr_text = state.get("ocr_text", "")
        extracted_entities = state.get("extracted_entities", {})
        document_id = state.get("document_id")

        # Initialize results
        background_check_results = []
        pep_found = False
        sanctions_found = False
        background_risk_score = 0
        screened_entities = []

        try:
            # Step 1: Extract names from OCR text and entities
            potential_names = self._extract_names_from_text(
                ocr_text,
                extracted_entities.get("potential_names", [])
            )

            self.logger.info(
                f"Found {len(potential_names)} potential entities to screen"
            )

            # Step 2: Screen each entity against Dilisense
            for name in potential_names[:10]:  # Limit to 10 to conserve API calls
                try:
                    result = await self.dilisense.screen_individual(
                        name=name,
                        date_of_birth=None,  # Could extract from text if available
                        country=None
                    )

                    # Store result
                    background_check_results.append(result)
                    screened_entities.append(name)

                    # Check for PEP
                    if result.get("is_pep"):
                        pep_found = True
                        self.logger.warning(
                            f"PEP detected in {document_id}: {name}"
                        )

                    # Check for sanctions
                    if result.get("is_sanctioned"):
                        sanctions_found = True
                        self.logger.warning(
                            f"Sanctioned entity detected in {document_id}: {name}"
                        )

                except Exception as e:
                    self.logger.error(f"Error screening {name}: {e}")
                    errors.append(f"Screening error for {name}: {str(e)}")

            # Step 3: Calculate risk score
            background_risk_score = self._calculate_risk_score(
                background_check_results,
                pep_found,
                sanctions_found
            )

            self.logger.info(
                f"Background check completed: {document_id}, "
                f"screened={len(screened_entities)}, "
                f"PEP={pep_found}, sanctions={sanctions_found}, "
                f"risk={background_risk_score}"
            )

        except Exception as e:
            self.logger.error(f"Error in background check: {e}")
            errors.append(f"Background check error: {str(e)}")

        # Update state
        state["background_check_results"] = background_check_results
        state["pep_found"] = pep_found
        state["sanctions_found"] = sanctions_found
        state["background_risk_score"] = background_risk_score
        state["screened_entities"] = screened_entities
        
        # NEW: Add findings to background_check_findings list for workflow state
        # Convert results to findings format
        background_findings = []
        for result in background_check_results:
            if result.get("is_pep") or result.get("is_sanctioned") or result.get("matches"):
                finding = {
                    "type": "background_check",
                    "severity": "critical" if result.get("is_sanctioned") else "high" if result.get("is_pep") else "medium",
                    "entity": result.get("name"),
                    "is_pep": result.get("is_pep", False),
                    "is_sanctioned": result.get("is_sanctioned", False),
                    "matches": result.get("matches", []),
                    "sources": result.get("sources", [])
                }
                background_findings.append(finding)
        state["background_check_findings"] = background_findings
        
        state["errors"] = errors
        state["background_check_executed"] = True

        return state

    def _extract_names_from_text(
        self,
        text: str,
        pre_extracted_names: List[str]
    ) -> List[str]:
        """
        Extract person and entity names from text.

        Args:
            text: OCR extracted text
            pre_extracted_names: Names already extracted

        Returns:
            List of potential names to screen
        """
        names = set(pre_extracted_names)

        try:
            # Pattern 1: Title + Name (Mr. John Doe, Dr. Jane Smith)
            title_pattern = r'\b(?:Mr|Mrs|Ms|Dr|Prof|Sir|Dame|Lord|Lady)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
            matches = re.findall(title_pattern, text)
            names.update(matches)

            # Pattern 2: Capitalized full names (at least 2 words)
            name_pattern = r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
            matches = re.findall(name_pattern, text)
            # Filter out common false positives
            filtered_matches = [
                name for name in matches
                if not any(word in name for word in [
                    'Agreement', 'Contract', 'Date', 'Page', 'Annex',
                    'Clause', 'Section', 'Article', 'Bank', 'Company'
                ])
            ]
            names.update(filtered_matches)

            # Pattern 3: "Name:" or "Buyer:" labels
            labeled_pattern = r'(?:Name|Buyer|Seller|Owner|Tenant|Landlord|Party):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})'
            matches = re.findall(labeled_pattern, text, re.IGNORECASE)
            names.update(matches)

        except Exception as e:
            self.logger.error(f"Error extracting names: {e}")

        # Clean and deduplicate
        names = [name.strip() for name in names if len(name.strip()) > 5]
        names = list(set(names))

        return names[:20]  # Limit to 20 names

    def _calculate_risk_score(
        self,
        results: List[Dict[str, Any]],
        pep_found: bool,
        sanctions_found: bool
    ) -> int:
        """
        Calculate overall background check risk score.

        Args:
            results: List of screening results
            pep_found: Whether PEP was found
            sanctions_found: Whether sanctioned entity was found

        Returns:
            Risk score (0-100)
        """
        risk_score = 0

        # Base risk from number of matches
        if results:
            total_hits = sum(r.get("total_hits", 0) for r in results)
            risk_score += min(total_hits * 5, 20)  # Max 20 points

        # PEP findings
        if pep_found:
            risk_score += 40  # High risk

        # Sanctions findings
        if sanctions_found:
            risk_score += 60  # Critical risk

        # Risk level from individual results
        for result in results:
            risk_level = result.get("risk_level", RiskLevel.LOW)
            if risk_level == RiskLevel.CRITICAL:
                risk_score += 20
            elif risk_level == RiskLevel.HIGH:
                risk_score += 15
            elif risk_level == RiskLevel.MEDIUM:
                risk_score += 10

        # Cap at 100
        return min(risk_score, 100)
