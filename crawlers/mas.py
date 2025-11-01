"""
Monetary Authority of Singapore (MAS) Regulatory Crawler

Scrapes MAS notices and guidelines for AML/CFT regulations.
Uses BeautifulSoup for HTML parsing and PyPDF2 for PDF extraction.
"""

import logging
import os
import json
import re
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime
from typing import List, Dict, Optional
from io import BytesIO

# BeautifulSoup imports
from bs4 import BeautifulSoup
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# PyPDF2 import
try:
    from PyPDF2 import PdfReader
except ImportError:
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None

logger = logging.getLogger(__name__)


class MASCrawler:
    """Crawler for MAS regulatory notices"""
    
    def __init__(self, use_cached_html: bool = False):
        self.base_url = "https://www.mas.gov.sg/regulation/notices"
        self.source = "MAS"
        self.jurisdiction = "SG"
        self.use_cached_html = use_cached_html
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def crawl(self) -> List[Dict]:
        """Crawl MAS site: find PDF links and parse PDFs."""
        logger.info(f"Starting MAS crawler from {self.base_url}")

        if PdfReader is None:
            msg = "PyPDF2 not available. Install pypdf2 to proceed."
            logger.error(msg)
            raise RuntimeError(msg)

        # Get HTML content
        if self.use_cached_html:
            html_path = Path("mas.html")
            if not html_path.exists():
                raise FileNotFoundError(f"Cached HTML file not found: {html_path}")
            html_content = html_path.read_text(encoding="utf-8")
            logger.info("Using cached HTML file")
        else:
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            html_content = response.text
            logger.info("Fetched HTML from live URL")

        # Parse HTML and extract PDF links
        pdf_links = self._discover_pdf_links(html_content)
        logger.info(f"MAS discovered {len(pdf_links)} PDF links")

        # Parse each PDF
        notices: List[Dict] = []
        for link in pdf_links[:25]:  # limit for safety
            try:
                content = self._parse_pdf(link["url"])
                title = link.get("title") or "MAS Notice"
                date = self._parse_date(link.get("date_text")) or datetime.utcnow()

                notices.append({
                    "title": title,
                    "url": link["url"],
                    "date": date,
                    "content": content,
                    "source": self.source,
                    "jurisdiction": self.jurisdiction,
                    "rule_type": "notice",
                })
            except Exception as e:
                logger.error(f"MAS PDF parse failed for {link.get('url')}: {e}")
                continue

        logger.info(f"MAS crawler produced {len(notices)} notices")
        return notices

    def _discover_pdf_links(self, html_content: str) -> List[Dict]:
        """Extract PDF links from HTML using BeautifulSoup."""
        soup = BeautifulSoup(html_content, 'lxml')
        links: List[Dict] = []
        
        # Find all search result cards
        cards = soup.select("article.mas-search-card")
        logger.info(f"Found {len(cards)} search cards")
        
        for card in cards:
            # Find the main link
            main_link = card.select_one("a.ola-link.mas-link")
            if not main_link:
                continue
                
            href = main_link.get("href", "").strip()
            if not href:
                continue
            
            # Make absolute URL
            abs_url = urljoin(self.base_url, href)
            
            # Extract title
            title = main_link.get_text(strip=True)
            
            # Extract date from ancillaries
            date_elem = card.select_one(".mas-ancillaries")
            date_text = date_elem.get_text(strip=True) if date_elem else ""
            
            # Check if this links to a PDF directly or to a detail page
            if ".pdf" in href.lower():
                # Direct PDF link
                links.append({
                    "url": abs_url,
                    "title": title,
                    "date_text": date_text,
                })
            else:
                # Detail page - need to fetch and find PDF links
                try:
                    detail_pdfs = self._find_pdfs_on_page(abs_url)
                    for pdf_url in detail_pdfs:
                        links.append({
                            "url": pdf_url,
                            "title": title,
                            "date_text": date_text,
                        })
                except Exception as e:
                    logger.warning(f"Failed to extract PDFs from detail page {abs_url}: {e}")
        
        return links

    def _find_pdfs_on_page(self, url: str) -> List[str]:
        """Find PDF links on a detail page."""
        try:
            response = requests.get(url, headers=self.headers, timeout=30, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            
            pdf_urls = []
            # Find all links that point to PDFs
            for link in soup.select("a[href]"):
                href = link.get("href", "").strip()
                if ".pdf" in href.lower():
                    abs_url = urljoin(url, href)
                    pdf_urls.append(abs_url)
            
            return pdf_urls
        except Exception as e:
            logger.error(f"Failed to fetch detail page {url}: {e}")
            return []

    def _parse_pdf(self, pdf_url: str) -> str:
        """Download and parse a PDF into text using PyPDF2."""
        try:
            # Download PDF
            response = requests.get(pdf_url, headers=self.headers, timeout=30, verify=False)
            response.raise_for_status()
            
            # Parse PDF with PyPDF2
            pdf_file = BytesIO(response.content)
            reader = PdfReader(pdf_file)
            
            # Extract text from ALL pages
            text_parts = []
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num} from {pdf_url}: {e}")
                    continue
            
            text = "\n\n".join(text_parts)
            return text
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {pdf_url}: {e}")
            raise

    def _parse_date(self, text: Optional[str]) -> Optional[datetime]:
        """Parse date from text."""
        if not text:
            return None
        
        # Try patterns like '20 January 2024', '2024-01-20'
        patterns = [
            r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
            r"(\d{4})-(\d{2})-(\d{2})",
        ]
        months = {
            m.lower(): i
            for i, m in enumerate(
                [
                    "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December",
                ],
                1,
            )
        }
        for pat in patterns:
            m = re.search(pat, text)
            if not m:
                continue
            try:
                if pat == patterns[0]:
                    d = int(m.group(1))
                    mon = months.get(m.group(2).lower(), 1)
                    y = int(m.group(3))
                    return datetime(y, mon, d)
                if pat == patterns[1]:
                    y, mm, dd = m.groups()
                    return datetime(int(y), int(mm), int(dd))
            except Exception:
                continue
        return None

    def save_to_db(self, notices: List[Dict], db_session):
        """
        Save crawled notices to external_rules table.
        
        Args:
            notices: List of notice dictionaries
            db_session: Database session
        """
        from db.models import ExternalRule
        from services.embeddings import EmbeddingService
        from services.vector_db import VectorDBService
        
        embedding_service = EmbeddingService()
        vector_db = VectorDBService()
        
        saved_count = 0
        
        # Optional file-saving mode for tests
        save_path = os.getenv("CRAWLER_SAVE_TO_FILE")

        for notice in notices:
            try:
                # Generate embedding
                embedding = embedding_service.embed_text(notice["content"])

                if save_path:
                    # File-saving mode
                    out = Path(save_path)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    payload = {
                        **notice,
                        "metadata": {"crawled_at": datetime.utcnow().isoformat()},
                    }
                    out.write_text((out.read_text(encoding="utf-8") if out.exists() else "") +
                                    (json.dumps(payload, default=str) + "\n"), encoding="utf-8")

                    vector_db.upsert_vectors(
                        collection_name="external_rules",
                        texts=[notice["content"]],
                        vectors=[embedding],
                        metadata=[{
                            "title": notice["title"],
                            "source": notice["source"],
                            "jurisdiction": notice["jurisdiction"],
                            "rule_type": notice["rule_type"],
                        }],
                    )

                    saved_count += 1
                    logger.info(f"Saved notice to file: {notice['title']}")
                else:
                    # Database mode
                    existing = db_session.query(ExternalRule).filter(
                        ExternalRule.source == notice["source"],
                        ExternalRule.title == notice["title"]
                    ).first()

                    if existing:
                        logger.info(f"Notice already exists: {notice['title']}")
                        continue

                    rule = ExternalRule(
                        meta={
                            "crawled_at": datetime.utcnow().isoformat(),
                        }
                    )
                    db_session.add(rule)
                    db_session.commit()

                    vector_db.upsert_vectors(
                        collection_name="external_rules",
                        texts=[notice["content"]],
                        vectors=[embedding],
                        metadata=[{
                            "rule_id": rule.rule_id,
                            "title": rule.title,
                            "description": rule.description,
                            "source": rule.source,
                            "jurisdiction": rule.jurisdiction,
                            "rule_type": rule.rule_type,
                        }],
                    )

                    saved_count += 1
                    logger.info(f"Saved notice: {notice['title']}")
                
            except Exception as e:
                logger.error(f"Error saving notice {notice.get('title')}: {str(e)}")
                if not save_path:
                    db_session.rollback()
        
        logger.info(f"MAS crawler saved {saved_count}/{len(notices)} new notices")
        return saved_count


def main():
    """Test the crawler"""
    crawler = MASCrawler(use_cached_html=True)
    notices = crawler.crawl()
    print(f"Found {len(notices)} MAS notices")
    for notice in notices[:3]:
        print(f"- {notice['title']} ({notice['date']})")


if __name__ == "__main__":
    main()
