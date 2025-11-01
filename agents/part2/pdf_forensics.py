"""
PDFForensicsAgent - Extracts PDF metadata, detects simple tampering signs,
and assesses document integrity. Designed to be resilient if optional
libraries are unavailable.
"""

import hashlib
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import Part2Agent

logger = logging.getLogger(__name__)


class PDFForensicsAgent(Part2Agent):
    """Agent: PDF forensics - metadata, tampering detection, integrity analysis"""

    # Common software buckets used to infer trust level
    TRUSTED_SOFTWARE = {
        'adobe', 'acrobat', 'adobe pdf library', 'foxit', 'nitro',
        'microsoft', 'quartz', 'ghostscript', 'pdflib', 'itext', 'reportlab',
        'pdf-xchange', 'bluebeam', 'chrome', 'chromium'
    }

    SUSPICIOUS_SOFTWARE = {
        'pdf24', 'pdfescape', 'sejda', 'smallpdf', 'ilovepdf', 'soda pdf',
        'wondershare', 'online pdf', 'converter', 'modify', 'editor'
    }

    IMAGE_EDITING_SOFTWARE = {
        'photoshop', 'adobe photoshop', 'gimp', 'paint.net', 'pixlr',
        'affinity photo', 'corel', 'paintshop', 'photoscape'
    }

    WORD_PROCESSORS = {
        'microsoft word', 'ms word', 'libreoffice', 'openoffice', 'pages',
        'google docs', 'wordperfect'
    }

    def __init__(self) -> None:
        super().__init__("pdf_forensics")

        # Optional dependency: PyMuPDF
        self.pymupdf_available = False
        self.fitz = None
        try:
            import fitz  # type: ignore
            self.fitz = fitz
            self.pymupdf_available = True
            logger.info("PyMuPDF available for PDF analysis")
        except Exception:
            logger.warning("PyMuPDF not available - PDF forensics limited")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute PDF forensics analysis.

        Expects in state:
          - file_path: Path to PDF file
          - metadata: Optional pre-known metadata

        Adds to state:
          - pdf_metadata, tampering_detected, tampering_indicators,
            software_trust_level, integrity_score, forensics_issues,
            document_hash
        """
        self.logger.info("Executing PDFForensicsAgent")

        file_path = state.get("file_path", "")
        errors: List[str] = state.get("errors", [])

        pdf_metadata: Dict[str, Any] = {}
        tampering_detected = False
        tampering_indicators: List[Dict[str, Any]] = []
        forensics_issues: List[Dict[str, Any]] = []
        integrity_score = 100
        software_trust_level = "unknown"
        document_hash: Optional[str] = None

        try:
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"PDF not found: {file_path}")

            # Hash first – cheap and deterministic
            self.logger.info("🔒 Calculating document hash...")
            document_hash = self._calculate_hash(file_path)
            self.logger.info(f"   Hash: {document_hash[:16]}...")

            # Metadata (best-effort if PyMuPDF is not available)
            if self.pymupdf_available:
                self.logger.info("📊 Extracting PDF metadata...")
                pdf_metadata = self._extract_pdf_metadata(file_path)
                self.logger.info(f"   Creator: {pdf_metadata.get('creator', 'N/A')}")
                self.logger.info(f"   Producer: {pdf_metadata.get('producer', 'N/A')}")
                self.logger.info(f"   Creation Date: {pdf_metadata.get('creation_date', 'N/A')}")
                self.logger.info(f"   Modification Date: {pdf_metadata.get('mod_date', 'N/A')}")
                self.logger.info(f"   Pages: {pdf_metadata.get('page_count', 'N/A')}")
                self.logger.info(f"   Encrypted: {pdf_metadata.get('is_encrypted', 'N/A')}")
                self.logger.info(f"   Uniform Pages: {pdf_metadata.get('uniform_page_sizes', 'N/A')}")
            else:
                forensics_issues.append({
                    "type": "analysis_limited",
                    "severity": "medium",
                    "description": "PyMuPDF not available - forensics analysis limited"
                })
                integrity_score = 50
                # Minimal fallback metadata
                stat = os.stat(file_path)
                pdf_metadata = {
                    "title": None,
                    "author": None,
                    "creator": None,
                    "producer": None,
                    "creation_date": None,
                    "mod_date": None,
                    "page_count": None,
                    "file_size": stat.st_size,
                    "is_encrypted": None,
                    "uniform_page_sizes": None,
                }

            # Consistency checks
            self.logger.info("🔍 Checking metadata consistency...")
            consistency_issues = self._check_metadata_consistency(pdf_metadata)
            forensics_issues.extend(consistency_issues)
            if consistency_issues:
                self.logger.info(f"   Found {len(consistency_issues)} consistency issue(s)")
                for issue in consistency_issues:
                    self.logger.info(f"   - [{issue['severity'].upper()}] {issue['type']}: {issue['description']}")
                integrity_score -= min(30, len(consistency_issues) * 10)
            else:
                self.logger.info("   ✅ Metadata is consistent")

            # Tampering detection
            self.logger.info("🕵️  Detecting tampering indicators...")
            tampering = self._detect_tampering(file_path, pdf_metadata)
            tampering_indicators = tampering["indicators"]
            if tampering["detected"]:
                tampering_detected = True
                self.logger.info(f"   ⚠️  TAMPERING DETECTED! Found {len(tampering_indicators)} indicator(s)")
                for indicator in tampering_indicators:
                    self.logger.info(f"   - [{indicator['severity'].upper()}] {indicator['type']}: {indicator['description']}")
                integrity_score -= 30
            else:
                self.logger.info("   ✅ No tampering detected")

            # Software analysis
            self.logger.info("🛠️  Analyzing creation software...")
            sw = self._analyze_software(pdf_metadata)
            software_trust_level = sw["trust_level"]
            self.logger.info(f"   Software: {sw['software'] or 'unknown'}")
            self.logger.info(f"   Trust Level: {software_trust_level.upper()}")
            if sw["issues"]:
                self.logger.info(f"   Found {len(sw['issues'])} software-related issue(s)")
                for issue in sw["issues"]:
                    self.logger.info(f"   - [{issue['severity'].upper()}] {issue['type']}: {issue['description']}")
            else:
                self.logger.info("   ✅ Software appears legitimate")
            forensics_issues.extend(sw["issues"])

            # Quality checks
            self.logger.info("📐 Assessing document quality...")
            quality = self._assess_document_quality(file_path, pdf_metadata)
            forensics_issues.extend(quality)
            if quality:
                self.logger.info(f"   Found {len(quality)} quality issue(s)")
                for issue in quality:
                    self.logger.info(f"   - [{issue['severity'].upper()}] {issue['type']}: {issue['description']}")
                integrity_score -= min(20, len(quality) * 5)
            else:
                self.logger.info("   ✅ Document quality is good")

            # Clamp score
            integrity_score = max(0, min(100, integrity_score))
            
            self.logger.info(f"")
            self.logger.info(f"📊 FINAL INTEGRITY SCORE: {integrity_score}/100")
            self.logger.info(f"   - Tampering: {'YES' if tampering_detected else 'NO'}")
            self.logger.info(f"   - Software Trust: {software_trust_level.upper()}")
            self.logger.info(f"   - Total Issues: {len(forensics_issues)}")
            self.logger.info(f"   - Tampering Indicators: {len(tampering_indicators)}")

        except Exception as e:
            self.logger.error(f"PDF forensics error: {e}")
            errors.append(f"pdf_forensics_error: {str(e)}")

        # Update state
        state["pdf_metadata"] = pdf_metadata
        state["tampering_detected"] = tampering_detected
        state["tampering_indicators"] = tampering_indicators
        state["software_trust_level"] = software_trust_level
        state["integrity_score"] = integrity_score
        state["forensics_issues"] = forensics_issues
        state["document_hash"] = document_hash
        state["errors"] = errors
        state["pdf_forensics_executed"] = True

        return state

    # ----- Helpers -----
    def _calculate_hash(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        assert self.fitz is not None
        meta: Dict[str, Any] = {}
        with self.fitz.open(file_path) as doc:  # type: ignore[attr-defined]
            info = doc.metadata or {}
            # Normalize keys to snake_case
            meta = {
                "title": info.get("title") or info.get("Title"),
                "author": info.get("author") or info.get("Author"),
                "creator": info.get("creator") or info.get("Creator"),
                "producer": info.get("producer") or info.get("Producer"),
                "creation_date": info.get("creationDate") or info.get("CreationDate"),
                "mod_date": info.get("modDate") or info.get("ModDate"),
                "page_count": doc.page_count,
                "file_size": os.path.getsize(file_path),
                "is_encrypted": doc.is_encrypted,
                "uniform_page_sizes": self._check_uniform_page_sizes(doc),
            }
        return meta

    def _check_uniform_page_sizes(self, doc: Any) -> Optional[bool]:
        try:
            sizes = []
            for i in range(min(20, getattr(doc, "page_count", 0))):
                page = doc.load_page(i)
                r = page.rect
                sizes.append((round(r.width, 3), round(r.height, 3)))
            return len(set(sizes)) == 1 if sizes else None
        except Exception:
            return None

    def _check_metadata_consistency(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        creation = metadata.get("creation_date")
        mod = metadata.get("mod_date")
        if not creation and not mod:
            issues.append({
                "type": "missing_dates",
                "severity": "low",
                "description": "Creation/modification dates missing"
            })
            return issues

        cdt = self._parse_pdf_date(creation) if creation else None
        mdt = self._parse_pdf_date(mod) if mod else None

        if cdt and mdt:
            if mdt < cdt:
                issues.append({
                    "type": "mod_before_creation",
                    "severity": "high",
                    "description": "Modification date precedes creation date"
                })
        return issues

    def _analyze_software(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        creator = (metadata.get("creator") or "").lower()
        producer = (metadata.get("producer") or "").lower()
        software = creator or producer

        trust = "unknown"
        # Trusted
        for t in self.TRUSTED_SOFTWARE:
            if t in creator or t in producer:
                trust = "trusted"
                break
        # Suspicious/editor
        for s in self.SUSPICIOUS_SOFTWARE:
            if s in creator or s in producer:
                trust = "suspicious"
                issues.append({
                    "type": "suspicious_software",
                    "severity": "high",
                    "description": f"Document created with suspicious tool: {software or 'unknown'}"
                })
                break
        for e in self.IMAGE_EDITING_SOFTWARE:
            if e in creator or e in producer:
                trust = "image_editor"
                issues.append({
                    "type": "image_editing_software",
                    "severity": "critical",
                    "description": f"Image editor detected in metadata: {software or 'unknown'}"
                })
                break
        for w in self.WORD_PROCESSORS:
            if w in creator:
                issues.append({
                    "type": "word_processor_origin",
                    "severity": "medium",
                    "description": f"Document originated from word processor: {creator}"
                })
                break

        return {"trust_level": trust, "software": software, "issues": issues}

    def _detect_tampering(self, pdf_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        indicators: List[Dict[str, Any]] = []
        # Structural checks
        indicators.extend(self._detect_structural_tampering(pdf_path))

        detected = any(ind.get("severity") in {"high", "critical"} for ind in indicators)
        return {"detected": detected, "indicators": indicators}

    def _detect_structural_tampering(self, pdf_path: str) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        try:
            with open(pdf_path, "rb") as f:
                content = f.read()
            xref = content.count(b"xref")
            self.logger.debug(f"   Structural check: {xref} xref table(s) found")
            if xref > 1:
                issues.append({
                    "type": "multiple_xref_tables",
                    "severity": "critical",
                    "description": f"Multiple xref tables detected ({xref})"
                })
            eof = content.count(b"%%EOF")
            self.logger.debug(f"   Structural check: {eof} EOF marker(s) found")
            if eof > 1:
                issues.append({
                    "type": "multiple_eof_markers",
                    "severity": "high",
                    "description": f"Multiple EOF markers detected ({eof})"
                })
            linearized = b"/Linearized" in content
            self.logger.debug(f"   Structural check: Linearized={linearized}")
            if not linearized and xref > 1:
                issues.append({
                    "type": "non_linearized_updates",
                    "severity": "medium",
                    "description": "Non-linearized PDF with incremental updates"
                })
        except Exception as e:
            self.logger.debug(f"Structural tampering check failed: {e}")
        return issues

    def _assess_document_quality(self, pdf_path: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        if metadata.get("uniform_page_sizes") is False:
            issues.append({
                "type": "non_uniform_pages",
                "severity": "low",
                "description": "Page sizes are not uniform"
            })
        if metadata.get("page_count") == 1:
            issues.append({
                "type": "single_page",
                "severity": "low",
                "description": "Single-page document"
            })
        if metadata.get("is_encrypted"):
            issues.append({
                "type": "encrypted_document",
                "severity": "medium",
                "description": "Document is encrypted (limits forensic analysis)"
            })
        return issues

    def _parse_pdf_date(self, pdf_date_str: Optional[str]) -> Optional[datetime]:
        if not pdf_date_str:
            return None
        try:
            s = pdf_date_str
            if s.startswith("D:"):
                s = s[2:]
            s = s.split("+")[0].split("-")[0].split("Z")[0]
            if len(s) >= 14:
                return datetime.strptime(s[:14], "%Y%m%d%H%M%S")
            if len(s) >= 8:
                return datetime.strptime(s[:8], "%Y%m%d")
        except Exception:
            return None
        return None

