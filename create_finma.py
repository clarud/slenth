import os

finma_code = '''"""
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
    
    def __init__(self):
        self.base_url = "https://www.finma.ch/en/documentation/finma-circulars/"
        self.source = "FINMA"
        self.jurisdiction = "CH"
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
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            links: List[Dict] = []
            seen = set()
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if not href.lower().endswith('.pdf'):
                    continue
                abs_url = urljoin(url, href)
                if '/rundschreiben/' not in abs_url.lower():
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
            logger.info(f"FINMA discovered {len(links)} circular PDF links")
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
            text = "\\n\\n".join(text_parts)
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
            r"(\\d{1,2})\\.(\\d{1,2})\\.(\\d{4})",
            r"(\\d{4})-(\\d{2})-(\\d{2})",
            r"(\\d{1,2})\\s+([A-Za-z]+)\\s+(\\d{4})",
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


if __name__ == "__main__":
    crawler = FINMACrawler()
    circulars = crawler.crawl()
    print(f"Found {len(circulars)} FINMA circulars")
    for c in circulars[:3]:
        print(f"- {c['title'][:70]}")
        print(f"  Date: {c['date']}")
        print(f"  Content: {len(c['content'])} chars")
'''

# Write the file
with open(r"C:\Users\clare\OneDrive\Desktop\slenth\crawlers\finma.py", "w", encoding="utf-8") as f:
    f.write(finma_code)

print("Created finma.py")
