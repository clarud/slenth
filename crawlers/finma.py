"""
Swiss Financial Market Supervisory Authority (FINMA) Regulatory Crawler
Scrapes FINMA circulars using BeautifulSoup and PyPDF2.
"""
import logging
import os
import re
import io
from urllib.parse import urljoin
from datetime import datetime
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


class FINMACrawler:
    """Crawler for FINMA regulatory circulars"""
    
    def __init__(self, use_cached_html: bool = False):
        self.base_url = "https://www.finma.ch/en/documentation/circulars/"
        self.source = "FINMA"
        self.jurisdiction = "CH"
        self.use_cached_html = use_cached_html
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def crawl(self) -> List[Dict]:
        """Crawl FINMA site: find PDF links and parse PDFs."""
        logger.info(f"Starting FINMA crawler from {self.base_url}")
        pdf_links = self._discover_pdf_links(self.base_url)
        logger.info(f"FINMA discovered {len(pdf_links)} PDF links")
        
        circulars: List[Dict] = []
        for link in pdf_links[:25]:
            try:
                doc = self._parse_pdf(link["url"])
                title = link.get("title") or doc.get("title") or "FINMA Circular"
                date = self._parse_date(link.get("date_text")) or datetime.utcnow()
                content = doc.get("text", "")
                circulars.append({
                    "title": title,
                    "url": link["url"],
                    "date": date,
                    "content": content,
                    "source": self.source,
                    "jurisdiction": self.jurisdiction,
                    "rule_type": "circular",
                })
            except Exception as e:
                logger.error(f"FINMA PDF parse failed for {link.get('url')}: {e}")
                continue
        logger.info(f"FINMA crawler produced {len(circulars)} circulars")
        return circulars
    
    def _discover_pdf_links(self, url: str) -> List[Dict]:
        """Discover PDF links from FINMA circulars page using BeautifulSoup."""
        try:
            if self.use_cached_html:
                # FINMA uses AJAX, so for testing/fallback we can use cached HTML
                cached_path = os.path.join(os.path.dirname(__file__), '..', 'finma.html')
                with open(cached_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                soup = BeautifulSoup(html_content, 'lxml')
            else:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'lxml')
            links: List[Dict] = []
            seen = set()
            all_pdf_links = 0
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '.pdf' not in href.lower():
                    continue
                all_pdf_links += 1
                abs_url = urljoin(url, href)
                if '/rundschreiben/' not in abs_url.lower() and '/circulars/' not in abs_url.lower():
                    continue
                if abs_url in seen:
                    continue
                seen.add(abs_url)
                title = a_tag.get_text(strip=True)
                if not title or len(title) < 5:
                    parent = a_tag.find_parent(['div', 'td', 'li'])
                    if parent:
                        title = parent.get_text(strip=True)[:200]
                date_text = ""
                if a_tag.parent:
                    date_spans = a_tag.parent.find_all(['span', 'time'], class_=re.compile(r'date|update', re.I))
                    if date_spans:
                        date_text = date_spans[0].get_text(strip=True)
                links.append({
                    "url": abs_url,
                    "title": title or os.path.basename(abs_url),
                    "date_text": date_text,
                })
            logger.info(f"FINMA found {all_pdf_links} total PDFs, {len(links)} circular PDF links")
            return links
        except Exception as e:
            logger.error(f"Failed to discover PDF links from {url}: {e}")
            return []
    
    def _parse_pdf(self, pdf_url: str) -> Dict:
        """Download and parse a PDF into text using PyPDF2."""
        try:
            response = self.session.get(pdf_url, timeout=60)
            response.raise_for_status()
            pdf_file = io.BytesIO(response.content)
            reader = PdfReader(pdf_file)
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
            title = ""
            if reader.metadata:
                title = reader.metadata.get('/Title', '')
            return {
                "text": text,
                "title": title,
                "metadata": {"pages": len(reader.pages)}
            }
        except Exception as e:
            logger.error(f"Failed to parse PDF {pdf_url}: {e}")
            raise
    
    def _parse_date(self, text: Optional[str]) -> Optional[datetime]:
        """Parse date from text in various formats."""
        if not text:
            return None
        patterns = [
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",
            r"(\d{4})-(\d{2})-(\d{2})",
            r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
        ]
        months = {
            m.lower(): i for i, m in enumerate([
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ], 1)
        }
        for pat in patterns:
            m = re.search(pat, text)
            if not m:
                continue
            try:
                if pat == patterns[0]:
                    d, mm, y = m.groups()
                    return datetime(int(y), int(mm), int(d))
                elif pat == patterns[1]:
                    y, mm, dd = m.groups()
                    return datetime(int(y), int(mm), int(dd))
                elif pat == patterns[2]:
                    d = int(m.group(1))
                    mon = months.get(m.group(2).lower(), 1)
                    y = int(m.group(3))
                    return datetime(y, mon, d)
            except Exception:
                continue
        return None
    
    def save_to_db(self, circulars: List[Dict], db_session):
        """
        Save crawled circulars to external_rules table.
        
        Args:
            circulars: List of circular dictionaries
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
        
        for circular in circulars:
            try:
                # Generate embedding
                content = circular.get("content", "")
                if not content:
                    logger.warning(f"Skipping circular with no content: {circular.get('title')}")
                    continue
                    
                embedding = embedding_service.embed_text(content)
                
                if save_path:
                    # File-saving mode
                    from pathlib import Path
                    import json
                    out = Path(save_path)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    payload = {
                        **circular,
                        "metadata": {"crawled_at": datetime.utcnow().isoformat()},
                    }
                    out.write_text((out.read_text(encoding="utf-8") if out.exists() else "") +
                                    (json.dumps(payload, default=str) + "\n"), encoding="utf-8")
                    
                    vector_db.upsert_vectors(
                        collection_name="external_rules",
                        texts=[content],
                        vectors=[embedding],
                        metadata=[{
                            "title": circular["title"],
                            "source": circular["source"],
                            "jurisdiction": circular["jurisdiction"],
                            "rule_type": circular["rule_type"],
                        }],
                    )
                    
                    saved_count += 1
                    logger.info(f"Saved circular to file: {circular['title']}")
                else:
                    # Database mode
                    existing = db_session.query(ExternalRule).filter(
                        ExternalRule.source == circular["source"],
                        ExternalRule.title == circular["title"]
                    ).first()
                    
                    if existing:
                        logger.info(f"Circular already exists: {circular['title']}")
                        continue
                    
                    rule = ExternalRule(
                        title=circular["title"],
                        description=content[:500],  # First 500 chars
                        source=circular["source"],
                        jurisdiction=circular["jurisdiction"],
                        rule_type=circular["rule_type"],
                        meta={
                            "crawled_at": datetime.utcnow().isoformat(),
                            "url": circular["url"],
                            "date": circular["date"].isoformat() if circular.get("date") else None,
                        }
                    )
                    db_session.add(rule)
                    db_session.commit()
                    
                    vector_db.upsert_vectors(
                        collection_name="external_rules",
                        texts=[content],
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
                    logger.info(f"Saved circular: {circular['title']}")
            
            except Exception as e:
                logger.error(f"Error saving circular {circular.get('title')}: {str(e)}")
                if not save_path:
                    db_session.rollback()
        
        logger.info(f"FINMA crawler saved {saved_count}/{len(circulars)} new circulars")
        return saved_count


if __name__ == "__main__":
    # Use cached HTML since FINMA uses AJAX
    crawler = FINMACrawler(use_cached_html=True)
    circulars = crawler.crawl()
    print(f"Found {len(circulars)} FINMA circulars")
    for c in circulars[:3]:
        print(f"- {c['title'][:70]}")
        print(f"  Date: {c['date']}")
        print(f"  Content: {len(c['content'])} chars")
