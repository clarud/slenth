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
        for link in pdf_links[:25]:  # Limit to 25 for performance
            try:
                doc = self._parse_pdf(link["url"])
                title = link.get("title") or doc.get("title") or "FINMA Circular"
                date = self._parse_date(link.get("date_text")) or datetime.now()
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
                # For testing/fallback we can use cached HTML
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
            
            # Find all PDF links with FINMA circular pattern
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '.pdf' not in href.lower():
                    continue
                
                # Build absolute URL
                abs_url = urljoin(url, href)
                
                # Filter for rundschreiben/circulars
                if '/rundschreiben/' not in abs_url.lower() and '/circulars/' not in abs_url.lower():
                    continue
                
                # Prefer English PDFs (sc_lang=en) or PDFs without language specified
                if '?sc_lang=' in abs_url and 'sc_lang=en' not in abs_url:
                    continue
                
                if abs_url in seen:
                    continue
                
                # Get link text
                link_text = a_tag.get_text(strip=True)
                
                # Skip if link_text is just language codes or empty
                if not link_text or link_text in ['DE', 'FR', 'IT', 'EN'] or len(link_text) < 5:
                    continue
                
                seen.add(abs_url)
                
                # Extract title and date
                title = link_text
                date_text = ""
                
                # Look for the parent container that has the circular information
                parent = a_tag.find_parent(['div', 'li', 'article', 'p'])
                if parent:
                    # Extract date from "Updated: DD.MM.YYYY" pattern
                    updated_match = re.search(r'Updated:\s*(\d{1,2}\.\d{1,2}\.\d{4})', parent.get_text())
                    if updated_match:
                        date_text = updated_match.group(1)
                
                # Clean up title - remove metadata patterns
                title = re.sub(r'Updated:.*?Language\(s\):', '', title, flags=re.DOTALL).strip()
                title = re.sub(r'Updated:.*?Size:.*?MB', '', title, flags=re.DOTALL).strip()
                title = title.replace('Language(s):', '').strip()
                title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
                
                if not title or len(title) < 5:
                    continue
                
                links.append({
                    "url": abs_url,
                    "title": title,
                    "date_text": date_text,
                })
            
            logger.info(f"FINMA found {len(links)} circular PDF links")
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
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",  # Swiss format DD.MM.YYYY
            r"(\d{4})-(\d{2})-(\d{2})",  # ISO format YYYY-MM-DD
            r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",  # DD Month YYYY
        ]
        months = {
            m.lower(): i for i, m in enumerate([
                "january", "february", "march", "april", "may", "june",
                "july", "august", "september", "october", "november", "december"
            ], 1)
        }
        for pat in patterns:
            m = re.search(pat, text)
            if not m:
                continue
            try:
                if pat == patterns[0]:  # DD.MM.YYYY
                    d, mm, y = m.groups()
                    return datetime(int(y), int(mm), int(d))
                elif pat == patterns[1]:  # YYYY-MM-DD
                    y, mm, dd = m.groups()
                    return datetime(int(y), int(mm), int(dd))
                elif pat == patterns[2]:  # DD Month YYYY
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
                        "metadata": {"crawled_at": datetime.now().isoformat()},
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
                            "crawled_at": datetime.now().isoformat(),
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
    # Use live mode to fetch from website
    import logging
    logging.basicConfig(level=logging.INFO)
    
    crawler = FINMACrawler(use_cached_html=False)
    circulars = crawler.crawl()
    print(f"\nFound {len(circulars)} FINMA circulars")
    for c in circulars[:5]:
        print(f"\n- {c['title']}")
        print(f"  URL: {c['url']}")
        print(f"  Date: {c['date']}")
        print(f"  Content: {len(c['content'])} chars")
