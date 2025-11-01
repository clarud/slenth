"""
EvidenceStorekeeperAgent

Skeleton agent that aggregates evidence produced by other Part 2 agents and
prepares it for storage and frontend display. No database integration is
performed here; a placeholder storage_id is returned.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from agents import Part2Agent

logger = logging.getLogger(__name__)


class EvidenceStorekeeperAgent(Part2Agent):
    """Agent: Manage storage for docs, extracted text, embeddings"""

    def __init__(self, db_session: Optional[Session] = None) -> None:
        super().__init__("evidence_storekeeper")
        self.db_session = db_session
        self.logger.info("Evidence Storekeeper Agent initialized (SKELETON)")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute evidence collection and presentation preparation.

        Inputs (best-effort): document_id, file_path, file_format, metadata,
        OCR results, background check, validation, forensics, risk results.

        Outputs: evidence_collected, evidence_items_count, evidence_storage_id,
        evidence_display_data, audit_entries, evidence_storekeeper_executed.
        """
        self.logger.info("Executing EvidenceStorekeeperAgent")

        document_id = state.get("document_id") or state.get("document", {}).get("document_id")
        errors: List[str] = state.get("errors", [])

        try:
            evidence = self._collect_evidence(state)
            structured = self._structure_evidence(evidence)
            audit_entries = self._create_audit_trail(state, evidence)
            display = self._prepare_display_data(state, evidence)
            storage_result = self._store_evidence(document_id, structured, audit_entries)

            state.update({
                "evidence_collected": True,
                "evidence_items_count": len(structured.get("items", [])),
                "evidence_storage_id": storage_result.get("storage_id"),
                "evidence_display_data": display,
                "audit_entries": audit_entries,
                "errors": errors,
                "evidence_storekeeper_executed": True,
            })

            self.logger.info(
                f"Evidence collected for {document_id}: {state['evidence_items_count']} items"
            )

        except Exception as e:
            self.logger.error(f"EvidenceStorekeeper error: {e}")
            errors.append(f"evidence_storekeeper_error: {str(e)}")
            state["errors"] = errors
            state["evidence_storekeeper_executed"] = True

        return state

    # ----- internals -----
    def _collect_evidence(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Collect evidence snapshots from the workflow state."""
        return {
            "document": {
                "id": state.get("document_id") or state.get("document", {}).get("document_id"),
                "path": state.get("file_path"),
                "format": state.get("file_format") or state.get("document", {}).get("document_type", "pdf"),
                "metadata": state.get("metadata", {}),
            },
            "ocr": {
                "has_text": state.get("has_text"),
                "text_length": state.get("text_length"),
                "text": state.get("ocr_text"),
                "page_texts": state.get("page_texts"),
                "entities": state.get("extracted_entities", {}),
            },
            "background": {
                "screened_entities": state.get("screened_entities", []),
                "pep_found": state.get("pep_found"),
                "sanctions_found": state.get("sanctions_found"),
                "risk_score": state.get("background_risk_score"),
                "results": state.get("background_check_results", []),
            },
            "validation": {
                "format_valid": state.get("format_valid"),
                "completeness_score": state.get("completeness_score"),
                "spelling_errors": state.get("spelling_errors"),
                "nlp_valid": state.get("nlp_valid"),
                "consistency_score": state.get("consistency_score"),
                "contradictions": state.get("contradictions", []),
            },
            "forensics": {
                "pdf": {
                    "tampering_detected": state.get("tampering_detected"),
                    "integrity_score": state.get("integrity_score"),
                    "software_trust_level": state.get("software_trust_level"),
                    "tampering_indicators": state.get("tampering_indicators", []),
                },
                "image": {
                    "images_analyzed": state.get("images_analyzed"),
                    "ai_generated_detected": state.get("ai_generated_detected"),
                    "image_tampering_detected": state.get("image_tampering_detected"),
                    "image_forensics_score": state.get("image_forensics_score"),
                    "exif_issues": state.get("exif_issues", []),
                },
            },
            "risk_assessment": {
                "overall_score": state.get("overall_risk_score"),
                "band": state.get("risk_band"),
                "requires_manual_review": state.get("requires_manual_review"),
                "factors": state.get("risk_factors", []),
                "recommendations": state.get("recommendations", []),
            },
        }

    def _structure_evidence(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Create a flattened list of evidence items with categories and timestamps."""
        now = datetime.utcnow().isoformat()
        items: List[Dict[str, Any]] = []

        # Document
        items.append({
            "category": "document",
            "type": "metadata",
            "data": evidence["document"],
            "timestamp": now,
        })

        # OCR
        if evidence["ocr"].get("text") is not None:
            items.append({
                "category": "ocr",
                "type": "text",
                "data": {
                    "length": evidence["ocr"].get("text_length"),
                    "has_text": evidence["ocr"].get("has_text"),
                },
                "timestamp": now,
            })
        if evidence["ocr"].get("entities"):
            items.append({
                "category": "ocr",
                "type": "entities",
                "data": evidence["ocr"].get("entities"),
                "timestamp": now,
            })

        # Background
        if evidence["background"]["results"] is not None:
            items.append({
                "category": "background_check",
                "type": "results",
                "data": evidence["background"],
                "severity": "critical" if evidence["background"].get("sanctions_found") else (
                    "high" if evidence["background"].get("pep_found") else "low"
                ),
                "timestamp": now,
            })

        # Validation
        items.append({
            "category": "validation",
            "type": "format_and_nlp",
            "data": evidence["validation"],
            "timestamp": now,
        })

        # Forensics
        items.append({
            "category": "forensics",
            "type": "pdf",
            "data": evidence["forensics"]["pdf"],
            "severity": "high" if evidence["forensics"]["pdf"].get("tampering_detected") else "low",
            "timestamp": now,
        })
        items.append({
            "category": "forensics",
            "type": "image",
            "data": evidence["forensics"]["image"],
            "severity": "high" if evidence["forensics"]["image"].get("image_tampering_detected") else "low",
            "timestamp": now,
        })

        # Risk Assessment
        items.append({
            "category": "risk_assessment",
            "type": "overall",
            "data": evidence["risk_assessment"],
            "severity": self._map_risk_to_severity(evidence["risk_assessment"].get("band")),
            "timestamp": now,
        })

        return {"items": items}

    def _create_audit_trail(self, state: Dict[str, Any], evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
        now = datetime.utcnow().isoformat()
        entries: List[Dict[str, Any]] = []
        def add(event: str, details: Dict[str, Any]):
            entries.append({
                "timestamp": now,
                "event": event,
                "details": details,
            })

        add("evidence_collected", {"document_id": evidence["document"].get("id")})
        add("ocr_processed", {"has_text": evidence["ocr"].get("has_text"), "length": evidence["ocr"].get("text_length")})
        add("background_checked", {
            "pep_found": evidence["background"].get("pep_found"),
            "sanctions_found": evidence["background"].get("sanctions_found"),
        })
        add("validation_summarized", {
            "format_valid": evidence["validation"].get("format_valid"),
            "nlp_valid": evidence["validation"].get("nlp_valid"),
        })
        add("forensics_summarized", {
            "pdf_tampering": evidence["forensics"]["pdf"].get("tampering_detected"),
            "image_tampering": evidence["forensics"]["image"].get("image_tampering_detected"),
        })
        add("risk_assessed", {
            "score": evidence["risk_assessment"].get("overall_score"),
            "band": evidence["risk_assessment"].get("band"),
        })

        return entries

    def _prepare_display_data(self, state: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "document_info": {
                "id": evidence["document"].get("id"),
                "format": evidence["document"].get("format"),
                "pages": evidence["document"].get("metadata", {}).get("page_count"),
                "size": evidence["document"].get("metadata", {}).get("file_size"),
            },
            "key_findings": {
                "pep_found": evidence["background"].get("pep_found", False),
                "sanctions_found": evidence["background"].get("sanctions_found", False),
                "pdf_tampering": evidence["forensics"]["pdf"].get("tampering_detected", False),
            },
            "risk_summary": {
                "score": evidence["risk_assessment"].get("overall_score", 0),
                "band": evidence["risk_assessment"].get("band", "UNKNOWN"),
                "requires_manual_review": evidence["risk_assessment"].get("requires_manual_review", False),
            },
        }

    def _store_evidence(self, document_id: Any, structured: Dict[str, Any], audit_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Placeholder storage; return a deterministic id without persisting."""
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        storage_id = f"local-{document_id or 'unknown'}-{ts}"
        return {"storage_id": storage_id}

    def _map_risk_to_severity(self, band: Any) -> str:
        band = (band or "").upper()
        if band in ("CRITICAL",):
            return "critical"
        if band in ("HIGH",):
            return "high"
        if band in ("MEDIUM",):
            return "medium"
        return "low"

