"""
Dilisense API Service - Background screening integration.

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


class DilisenseService:
    """Service for Dilisense API integration."""

    def __init__(self):
        """Initialize Dilisense client."""
        self.api_key = settings.dilisense_api_key
        self.base_url = settings.dilisense_base_url
        self.enabled = settings.dilisense_enabled
        self.timeout = settings.dilisense_timeout
        self.max_retries = settings.dilisense_max_retries

        if not self.enabled:
            logger.warning("Dilisense integration is DISABLED")
        else:
            logger.info("Initialized Dilisense service")

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
        Screen an individual against Dilisense databases.

        Args:
            name: Full name of individual
            date_of_birth: Date of birth (YYYY-MM-DD)
            country: Country code (ISO 3166-1 alpha-2)
            additional_info: Additional screening parameters

        Returns:
            Screening results with match status and details
        """
        if not self.enabled:
            logger.warning("Dilisense screening disabled, returning mock result")
            return self._mock_screening_result(name, "individual")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Build query parameters (Dilisense uses GET requests)
                params = {
                    "names": name,
                    "fuzzy_search": "1",  # Enable fuzzy matching
                }

                if date_of_birth:
                    # Convert to dd/mm/yyyy format if needed
                    params["dob"] = date_of_birth
                if country:
                    # Can be used in 'includes' parameter
                    pass
                if additional_info:
                    params.update(additional_info)

                # Call Dilisense API (GET request with x-api-key header)
                response = await client.get(
                    f"{self.base_url}/checkIndividual",
                    params=params,
                    headers={
                        "x-api-key": self.api_key,
                    },
                )
                response.raise_for_status()

                # Parse response
                api_response = response.json()
                found_records = api_response.get("found_records", [])
                result = found_records[0] if found_records else {}
                
                # Determine match status and risk
                total_hits = api_response.get("total_hits", 0)
                if total_hits == 0:
                    match_status = MatchStatus.CLEAR
                    risk_level = RiskLevel.LOW
                else:
                    match_status = MatchStatus.CONFIRMED_MATCH
                    # Determine risk based on source type
                    source_type = result.get("source_type", "")
                    if source_type == "SANCTION":
                        risk_level = RiskLevel.CRITICAL
                    elif source_type == "PEP":
                        risk_level = RiskLevel.HIGH
                    elif source_type == "CRIMINAL":
                        risk_level = RiskLevel.HIGH
                    else:
                        risk_level = RiskLevel.MEDIUM
                
                return {
                    "name": name,
                    "entity_type": "individual",
                    "match_status": match_status,
                    "risk_level": risk_level,
                    "matches": found_records,
                    "total_hits": total_hits,
                    "is_pep": result.get("source_type") == "PEP",
                    "is_sanctioned": result.get("source_type") == "SANCTION",
                    "pep_type": result.get("pep_type"),
                    "date_of_birth": result.get("date_of_birth", []),
                    "citizenship": result.get("citizenship", []),
                    "positions": result.get("positions", []),
                    "sanction_details": result.get("sanction_details", []),
                    "screening_date": api_response.get("timestamp"),
                    "raw_response": api_response,
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Dilisense API error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.TimeoutException:
            logger.error(f"Dilisense API timeout for {name}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Dilisense screening: {e}")
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
        registration_number: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Screen an entity/organization against Dilisense databases.

        Args:
            name: Entity/organization name
            country: Country code (ISO 3166-1 alpha-2)
            registration_number: Business registration number
            additional_info: Additional screening parameters

        Returns:
            Screening results with match status and details
        """
        if not self.enabled:
            logger.warning("Dilisense screening disabled, returning mock result")
            return self._mock_screening_result(name, "entity")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Build query parameters (Dilisense uses GET requests)
                params = {
                    "names": name,
                    "fuzzy_search": "1",  # Enable fuzzy matching
                }

                if country:
                    # Can be used in 'includes' parameter to filter by country lists
                    pass
                if registration_number:
                    # Can add to search query
                    params["names"] = f"{name} {registration_number}"
                if additional_info:
                    params.update(additional_info)

                # Call Dilisense API (GET request with x-api-key header)
                response = await client.get(
                    f"{self.base_url}/checkEntity",
                    params=params,
                    headers={
                        "x-api-key": self.api_key,
                    },
                )
                response.raise_for_status()

                # Parse response
                api_response = response.json()
                found_records = api_response.get("found_records", [])
                result = found_records[0] if found_records else {}
                
                # Determine match status and risk
                total_hits = api_response.get("total_hits", 0)
                if total_hits == 0:
                    match_status = MatchStatus.CLEAR
                    risk_level = RiskLevel.LOW
                else:
                    match_status = MatchStatus.CONFIRMED_MATCH
                    source_type = result.get("source_type", "")
                    if source_type == "SANCTION":
                        risk_level = RiskLevel.CRITICAL
                    elif source_type == "PEP":
                        risk_level = RiskLevel.HIGH
                    else:
                        risk_level = RiskLevel.MEDIUM
                
                return {
                    "name": name,
                    "entity_type": "entity",
                    "match_status": match_status,
                    "risk_level": risk_level,
                    "matches": found_records,
                    "total_hits": total_hits,
                    "is_sanctioned": result.get("source_type") == "SANCTION",
                    "sanction_details": result.get("sanction_details", []),
                    "jurisdiction": result.get("jurisdiction", []),
                    "company_number": result.get("company_number", []),
                    "screening_date": api_response.get("timestamp"),
                    "raw_response": api_response,
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Dilisense API error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.TimeoutException:
            logger.error(f"Dilisense API timeout for {name}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Dilisense screening: {e}")
            raise

    async def batch_screen(
        self,
        entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Screen multiple entities in batch.

        Args:
            entities: List of entities to screen, each with 'name', 'type', etc.

        Returns:
            List of screening results
        """
        results = []
        
        for entity in entities:
            entity_type = entity.get("type", "individual")
            name = entity.get("name")
            
            if not name:
                logger.warning(f"Skipping entity with no name: {entity}")
                continue
            
            try:
                if entity_type.lower() == "individual":
                    result = await self.screen_individual(
                        name=name,
                        date_of_birth=entity.get("date_of_birth"),
                        country=entity.get("country"),
                        additional_info=entity.get("additional_info"),
                    )
                else:
                    result = await self.screen_entity(
                        name=name,
                        country=entity.get("country"),
                        registration_number=entity.get("registration_number"),
                        additional_info=entity.get("additional_info"),
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error screening {name}: {e}")
                results.append({
                    "name": name,
                    "entity_type": entity_type,
                    "error": str(e),
                    "match_status": MatchStatus.CLEAR,
                    "risk_level": RiskLevel.LOW,
                })
        
        return results

    def _mock_screening_result(self, name: str, entity_type: str) -> Dict[str, Any]:
        """
        Generate mock screening result for testing.

        Args:
            name: Entity name
            entity_type: Type of entity ('individual' or 'entity')

        Returns:
            Mock screening result
        """
        # Simple logic: flag if name contains certain keywords
        suspicious_keywords = ["suspect", "criminal", "fraud", "sanction"]
        is_suspicious = any(keyword in name.lower() for keyword in suspicious_keywords)

        if is_suspicious:
            match_status = MatchStatus.POTENTIAL_MATCH
            risk_level = RiskLevel.HIGH
            matches = [{
                "name": name,
                "match_score": 0.85,
                "reason": "Adverse media mention",
                "source": "Mock Database"
            }]
        else:
            match_status = MatchStatus.CLEAR
            risk_level = RiskLevel.LOW
            matches = []

        return {
            "name": name,
            "entity_type": entity_type,
            "match_status": match_status,
            "risk_level": risk_level,
            "matches": matches,
            "is_pep": False,
            "is_sanctioned": is_suspicious,
            "adverse_media": matches,
            "screening_date": "2025-11-01T00:00:00Z",
            "mock": True,
        }

    async def get_entity_details(self, entity_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific entity.

        Args:
            entity_id: Dilisense entity ID

        Returns:
            Detailed entity information
        """
        if not self.enabled:
            logger.warning("Dilisense service disabled")
            return {}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/entities/{entity_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                    },
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error fetching entity details for {entity_id}: {e}")
            raise
