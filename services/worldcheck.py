"""
World-Check One API Service - LSEG screening integration.

Provides methods for:
- Screening individuals and entities
- PEP database checks
- Sanctions list screening
- Adverse media checks
- Risk assessment
"""

import logging
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings

logger = logging.getLogger(__name__)


class MatchStatus(str, Enum):
    """Match status for screening results."""
    CLEAR = "clear"
    POTENTIAL_MATCH = "potential_match"
    CONFIRMED_MATCH = "confirmed_match"


class RiskLevel(str, Enum):
    """Risk level for screening results."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorldCheckService:
    """Service for LSEG World-Check One API integration."""

    def __init__(self):
        """Initialize World-Check One client."""
        self.api_key = settings.worldcheck_api_key
        self.api_secret = settings.worldcheck_api_secret
        self.base_url = settings.worldcheck_base_url
        self.enabled = settings.worldcheck_enabled

        if not self.enabled:
            logger.warning("World-Check One integration is DISABLED")
        else:
            logger.info("Initialized World-Check One service")

    @retry(
        retry=retry_if_exception_type(httpx.TimeoutException),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
    )
    async def screen_individual(
        self,
        name: str,
        date_of_birth: Optional[str] = None,
        country: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Screen an individual against World-Check One databases.

        Args:
            name: Full name of individual
            date_of_birth: Date of birth (YYYY-MM-DD)
            country: Country code (ISO 3166-1 alpha-2)
            additional_info: Additional screening parameters

        Returns:
            Screening results with match status and details
        """
        if not self.enabled:
            logger.warning("World-Check screening disabled, returning mock result")
            return self._mock_screening_result(name, "individual")

        try:
            async with httpx.AsyncClient() as client:
                # Build screening request
                request_data = {
                    "name": name,
                    "entity_type": "INDIVIDUAL",
                }

                if date_of_birth:
                    request_data["date_of_birth"] = date_of_birth
                if country:
                    request_data["country"] = country
                if additional_info:
                    request_data.update(additional_info)

                # Call World-Check One API
                response = await client.post(
                    f"{self.base_url}/cases/screeningRequest",
                    json=request_data,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )

                response.raise_for_status()
                result = response.json()

                # Parse and format results
                formatted_result = self._parse_screening_result(result)

                logger.info(
                    f"Screened individual '{name}': {formatted_result['match_status']}"
                )
                return formatted_result

        except httpx.HTTPStatusError as e:
            logger.error(f"World-Check API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error screening individual: {e}")
            raise

    @retry(
        retry=retry_if_exception_type(httpx.TimeoutException),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
    )
    async def screen_entity(
        self,
        name: str,
        country: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Screen an entity/organization against World-Check One databases.

        Args:
            name: Name of entity/organization
            country: Country code
            additional_info: Additional screening parameters

        Returns:
            Screening results with match status and details
        """
        if not self.enabled:
            logger.warning("World-Check screening disabled, returning mock result")
            return self._mock_screening_result(name, "entity")

        try:
            async with httpx.AsyncClient() as client:
                request_data = {
                    "name": name,
                    "entity_type": "ORGANISATION",
                }

                if country:
                    request_data["country"] = country
                if additional_info:
                    request_data.update(additional_info)

                response = await client.post(
                    f"{self.base_url}/cases/screeningRequest",
                    json=request_data,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )

                response.raise_for_status()
                result = response.json()

                formatted_result = self._parse_screening_result(result)

                logger.info(
                    f"Screened entity '{name}': {formatted_result['match_status']}"
                )
                return formatted_result

        except httpx.HTTPStatusError as e:
            logger.error(f"World-Check API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error screening entity: {e}")
            raise

    def _parse_screening_result(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse World-Check One API response into standardized format.

        Args:
            api_result: Raw API response

        Returns:
            Formatted screening result
        """
        # Extract matches
        matches = api_result.get("results", [])

        if not matches:
            return {
                "match_status": MatchStatus.CLEAR,
                "risk_level": RiskLevel.LOW,
                "match_details": [],
                "total_matches": 0,
                "screening_date": api_result.get("screening_date"),
            }

        # Categorize matches
        match_details = []
        max_risk = RiskLevel.LOW

        for match in matches:
            categories = match.get("categories", [])
            match_strength = match.get("match_strength", 0)

            # Determine match type
            is_pep = any("PEP" in cat for cat in categories)
            is_sanctions = any("Sanctions" in cat or "Watchlist" in cat for cat in categories)
            is_adverse_media = any("Adverse Media" in cat for cat in categories)

            match_detail = {
                "name": match.get("primary_name"),
                "match_strength": match_strength,
                "is_pep": is_pep,
                "is_sanctions": is_sanctions,
                "is_adverse_media": is_adverse_media,
                "categories": categories,
                "countries": match.get("countries", []),
            }

            match_details.append(match_detail)

            # Update risk level
            if is_sanctions:
                max_risk = RiskLevel.CRITICAL
            elif is_pep and max_risk != RiskLevel.CRITICAL:
                max_risk = RiskLevel.HIGH
            elif is_adverse_media and max_risk not in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                max_risk = RiskLevel.MEDIUM

        # Determine overall match status
        high_strength_matches = [m for m in match_details if m["match_strength"] >= 80]

        if high_strength_matches:
            match_status = MatchStatus.CONFIRMED_MATCH
        elif match_details:
            match_status = MatchStatus.POTENTIAL_MATCH
        else:
            match_status = MatchStatus.CLEAR

        return {
            "match_status": match_status,
            "risk_level": max_risk,
            "match_details": match_details,
            "total_matches": len(matches),
            "screening_date": api_result.get("screening_date"),
        }

    def _mock_screening_result(
        self, name: str, entity_type: str
    ) -> Dict[str, Any]:
        """
        Generate mock screening result for testing.

        Args:
            name: Name being screened
            entity_type: Type of entity

        Returns:
            Mock screening result
        """
        # Mock result for hackathon demo
        return {
            "match_status": MatchStatus.CLEAR,
            "risk_level": RiskLevel.LOW,
            "match_details": [],
            "total_matches": 0,
            "screening_date": "2024-11-01T00:00:00Z",
            "note": "World-Check One integration disabled - mock result",
        }

    async def batch_screen(
        self, names: List[str], entity_type: str = "individual"
    ) -> List[Dict[str, Any]]:
        """
        Screen multiple names in batch.

        Args:
            names: List of names to screen
            entity_type: Type of entities (individual/entity)

        Returns:
            List of screening results
        """
        results = []

        for name in names:
            if entity_type == "individual":
                result = await self.screen_individual(name)
            else:
                result = await self.screen_entity(name)

            results.append({"name": name, "result": result})

        logger.info(f"Batch screened {len(names)} {entity_type}s")
        return results
