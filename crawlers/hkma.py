"""
Hong Kong Monetary Authority (HKMA) Regulatory Crawler

Scrapes HKMA circulars and guidelines for AML/CFT regulations.
Uses BeautifulSoup for HTML parsing, Selenium for JavaScript handling, and PyPDF2 for PDF extraction.
"""

import logging
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime
from typing import List, Dict, Optional
from io import BytesIO

# BeautifulSoup imports
from bs4 import BeautifulSoup
import requests
import urllib3

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# PDF parsing imports
try:
    from PyPDF2 import PdfReader
except ImportError:
    try:
        from pypdf import PdfReader  # Alternative package name
    except ImportError:
        PdfReader = None

# Try PyMuPDF (fitz) as alternative - more robust
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

logger = logging.getLogger(__name__)


class HKMACrawler:
    """Crawler for HKMA regulatory circulars"""
    
    def __init__(self, use_cached_html: bool = False):
        self.base_url = "https://www.hkma.gov.hk/eng/key-functions/banking/anti-money-laundering-and-counter-financing-of-terrorism/guidance-papers-circulars/"
        self.source = "HKMA"
        self.jurisdiction = "HK"
        self.use_cached_html = use_cached_html
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def crawl(self) -> List[Dict]:
        """Crawl HKMA site: find PDF links and parse PDFs."""
        logger.info(f"Starting HKMA crawler from {self.base_url}")

        if PdfReader is None:
            msg = "PyPDF2 not available. Install pypdf2 to proceed."
            logger.error(msg)
            raise RuntimeError(msg)

        # Get HTML content
        if self.use_cached_html:
            html_path = Path("hkma_test.html")  # Updated to use test file
            if not html_path.exists():
                raise FileNotFoundError(f"Cached HTML file not found: {html_path}")
            html_content = html_path.read_text(encoding="utf-8")
            logger.info("Using cached HTML file")
        else:
            response = requests.get(self.base_url, headers=self.headers, timeout=30, verify=False)
            response.raise_for_status()
            html_content = response.text
            logger.info("Fetched HTML from live URL")

        # Parse HTML and extract PDF links
        pdf_links = self._discover_pdf_links(html_content)
        logger.info(f"HKMA discovered {len(pdf_links)} PDF links")

        # Parse each PDF (process more, but keep reasonable limit)
        circulars: List[Dict] = []
        max_docs = 50  # Increased from 25 to capture more documents
        
        for i, link in enumerate(pdf_links[:max_docs]):
            try:
                logger.info(f"Processing {i+1}/{min(len(pdf_links), max_docs)}: {link['title'][:60]}...")
                
                content = self._parse_pdf(link["url"], link.get("is_brdr", False))
                title = link.get("title") or "HKMA Circular"
                date = self._parse_date(link.get("date_text")) or datetime.utcnow()

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
                logger.error(f"HKMA PDF parse failed for {link.get('url')}: {e}")
                continue

        logger.info(f"HKMA crawler produced {len(circulars)} circulars")
        return circulars

    def _discover_pdf_links(self, html_content: str) -> List[Dict]:
        """Extract PDF links from HTML using BeautifulSoup."""
        soup = BeautifulSoup(html_content, 'lxml')
        links: List[Dict] = []
        
        # Find all PDF links in the page
        # Pattern 1: Links in table rows with .filter-head .active a
        rows = soup.select("div.template-table tbody tr")
        logger.info(f"Found {len(rows)} table rows")
        
        for row in rows:
            # Find PDF link in the row - inside .filter-head .active a OR .filter a
            pdf_links = row.select(".filter-head .active a, .filter a")
            
            # Extract date from the second column
            date_cell = row.select_one("td[width='140px']")
            date_text = date_cell.get_text(strip=True) if date_cell else ""
            
            for pdf_link in pdf_links:
                href = pdf_link.get("href", "").strip()
                if not href:
                    continue
                
                # Accept both .pdf files and brdr.hkma.gov.hk links (which redirect to PDFs)
                is_pdf = ".pdf" in href.lower()
                is_brdr = "brdr.hkma.gov.hk" in href
                
                if not (is_pdf or is_brdr):
                    continue
                
                # Make absolute URL
                abs_url = urljoin(self.base_url, href)
                
                # Extract title
                title = pdf_link.get_text(strip=True)
                
                # Skip empty titles
                if not title or title.strip() == "":
                    continue
                
                links.append({
                    "url": abs_url,
                    "title": title,
                    "date_text": date_text,
                    "is_brdr": is_brdr,
                })
        
        # Also find standalone PDF links not in rows (annexes, enclosures)
        all_pdf_links = soup.select("a[href*='.pdf'], a[href*='brdr.hkma.gov.hk']")
        logger.info(f"Found {len(all_pdf_links)} total PDF/BRDR links in page")
        
        # Add links not already captured
        existing_urls = {link["url"] for link in links}
        for pdf_link in all_pdf_links:
            href = pdf_link.get("href", "").strip()
            if not href:
                continue
                
            abs_url = urljoin(self.base_url, href)
            
            # Skip if already added
            if abs_url in existing_urls:
                continue
            
            title = pdf_link.get_text(strip=True)
            if not title:
                continue
            
            is_brdr = "brdr.hkma.gov.hk" in href
            
            links.append({
                "url": abs_url,
                "title": title,
                "date_text": "",
                "is_brdr": is_brdr,
            })
        
        logger.info(f"Total unique PDF/BRDR links found: {len(links)}")
        return links

    def _parse_pdf(self, pdf_url: str, is_brdr: bool = False) -> str:
        """Fetch PDF using Selenium to handle redirects, then parse with PyPDF2."""
        driver = None
        try:
            # Set up Chrome options for headless operation
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Initialize Chrome driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # First try direct download to see if it's a real PDF
            try:
                logger.info(f"Attempting direct PDF download: {pdf_url[:80]}...")
                response = requests.get(pdf_url, headers=self.headers, timeout=15, verify=False, allow_redirects=True)
                
                # Check if we got an actual PDF
                if response.status_code == 200 and response.content[:4] == b'%PDF':
                    logger.info(f"✅ Got direct PDF ({len(response.content)} bytes)")
                else:
                    # Not a PDF - it's an HTML landing page, need Selenium
                    logger.info(f"⚠️ Not a direct PDF (Content-Type: {response.headers.get('Content-Type')}), using Selenium...")
                    raise Exception("Need Selenium")
                    
            except Exception:
                # BRDR link or landing page - needs Selenium processing
                # Navigate to URL (may redirect to landing page)
                driver.get(pdf_url)
                
                # Wait for page to load
                time.sleep(3)
                
                # Get the final URL after redirects
                final_url = driver.current_url
                logger.info(f"Redirected from {pdf_url} to {final_url}")
                
                # Parse the landing page to find the actual PDF download link
                soup = BeautifulSoup(driver.page_source, 'lxml')
                
                # Look for PDF download links
                actual_pdf_url = None
                
                # Method 1: Look for links with .pdf extension
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '.pdf' in href.lower():
                        # Make absolute URL
                        if href.startswith('http'):
                            actual_pdf_url = href
                        elif href.startswith('/'):
                            # Relative to domain
                            base = final_url.split('/')[0] + '//' + final_url.split('/')[2]
                            actual_pdf_url = base + href
                        else:
                            actual_pdf_url = urljoin(final_url, href)
                        logger.info(f"Found PDF link: {actual_pdf_url}")
                        break
                
                # Method 2: Try clicking download button if no direct link found
                if not actual_pdf_url:
                    try:
                        download_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Download')] | //a[contains(text(), 'Download')]")
                        onclick = download_btn.get_attribute('onclick')
                        href = download_btn.get_attribute('href')
                        if href:
                            actual_pdf_url = href if href.startswith('http') else urljoin(final_url, href)
                            logger.info(f"Found PDF from download button href: {actual_pdf_url}")
                    except:
                        pass
                
                # If we found the actual PDF URL, download it
                if actual_pdf_url:
                    response = requests.get(actual_pdf_url, headers=self.headers, timeout=30, verify=False)
                else:
                    # Fallback: try the final URL directly
                    logger.warning(f"Could not find PDF link on landing page, trying final URL: {final_url}")
                    response = requests.get(final_url, headers=self.headers, timeout=30, verify=False)
                
                response.raise_for_status()

            # Try PyMuPDF first (more robust), then fall back to PyPDF2
            pdf_content = response.content
            text = ""
            
            # Method 1: Try PyMuPDF (fitz) if available
            if HAS_PYMUPDF:
                try:
                    doc = fitz.open(stream=pdf_content, filetype="pdf")
                    text_parts = []
                    for page_num in range(len(doc)):
                        try:
                            page = doc[page_num]
                            page_text = page.get_text()
                            if page_text:
                                text_parts.append(page_text)
                        except Exception as e:
                            logger.warning(f"PyMuPDF failed on page {page_num}: {e}")
                            continue
                    doc.close()
                    text = "\n\n".join(text_parts)
                    if text.strip():
                        logger.info(f"✅ Extracted {len(text)} chars using PyMuPDF")
                        return text
                except Exception as e:
                    logger.warning(f"PyMuPDF failed: {e}, falling back to PyPDF2")
            
            # Method 2: Fall back to PyPDF2
            if not text.strip() and PdfReader is not None:
                pdf_file = BytesIO(pdf_content)
                try:
                    reader = PdfReader(pdf_file)
                except Exception as e:
                    # Try with strict=False for problematic PDFs
                    logger.warning(f"PyPDF2 standard read failed, trying strict=False: {e}")
                    pdf_file.seek(0)
                    try:
                        reader = PdfReader(pdf_file, strict=False)
                    except Exception as e2:
                        logger.error(f"PyPDF2 failed even with strict=False: {e2}")
                        return ""
                
                # Extract text from ALL pages
                text_parts = []
                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num}: {e}")
                        continue
                
                text = "\n\n".join(text_parts)
                if text.strip():
                    logger.info(f"✅ Extracted {len(text)} chars using PyPDF2")
            
            # Log if no text was extracted
            if not text.strip():
                logger.warning(f"⚠️ No text extracted from PDF: {pdf_url}")
            
            return text
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {pdf_url}: {e}")
            raise
        finally:
            if driver:
                driver.quit()

    def _parse_date(self, text: Optional[str]) -> Optional[datetime]:
        if not text:
            return None
        # Try patterns like '20 January 2024', '2024-01-20', '20.01.2024'
        patterns = [
            r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
            r"(\d{4})-(\d{2})-(\d{2})",
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",
        ]
        months = {
            m.lower(): i
            for i, m in enumerate(
                [
                    "January",
                    "February",
                    "March",
                    "April",
                    "May",
                    "June",
                    "July",
                    "August",
                    "September",
                    "October",
                    "November",
                    "December",
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
                if pat == patterns[2]:
                    d, mm, y = m.groups()
                    return datetime(int(y), int(mm), int(d))
            except Exception:
                continue
        return None
    
    def save_to_db(self, circulars: List[Dict], db_session):
        """
        Save crawled circulars to external_rules table with chunking and Pinecone inference API.
        
        Args:
            circulars: List of circular dictionaries with title, date, content, url
            db_session: Database session
        """
        from db.models import ExternalRule
        from config import settings
        from pinecone.grpc import PineconeGRPC as Pinecone
        from pinecone import ServerlessSpec
        import hashlib
        
        # Initialize Pinecone client
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(
            host=settings.PINECONE_INFERENCE_HOST,
            name="external"
        )
        
        saved_count = 0
        total_chunks = 0
        batch_records = []
        
        for circular in circulars:
            try:
                # Check for duplicates by source URL
                existing = db_session.query(ExternalRule).filter(
                    ExternalRule.source_url == circular["url"]
                ).first()
                
                if existing:
                    logger.info(f"Circular already exists: {circular['title']}")
                    continue
                
                # Generate rule ID
                hash_source = f"{circular['title']}-{circular['url']}"
                rule_hash = hashlib.md5(hash_source.encode()).hexdigest()[:12]
                base_rule_id = f"HKMA-{rule_hash}"
                
                # Chunk the content
                content = circular.get("content", "")
                chunks = self._chunk_text(content, max_words=2000, overlap_words=200)
                
                logger.info(f"Processing: {circular['title']} ({len(chunks)} chunks)")
                
                # Process each chunk
                for chunk_index, chunk_text in enumerate(chunks):
                    # Generate unique rule_id and vector_id for this chunk
                    if len(chunks) > 1:
                        rule_id = f"{base_rule_id}:{chunk_index}"
                    else:
                        rule_id = base_rule_id
                    
                    vector_id = str(uuid.uuid4())
                    
                    # Create database record
                    rule = ExternalRule(
                        rule_id=rule_id,
                        regulator="HKMA",
                        jurisdiction="HK",
                        rule_title=circular["title"],
                        rule_text=chunk_text,
                        source_url=circular["url"],
                        document_title=circular["title"],
                        published_date=circular.get("date"),
                        vector_id=vector_id,
                        chunk_index=chunk_index if len(chunks) > 1 else None,
                        meta={
                            "crawled_at": datetime.utcnow().isoformat(),
                            "rule_type": "circular",
                            "total_chunks": len(chunks),
                            "word_count": len(chunk_text.split()),
                            "full_word_count": len(content.split())
                        }
                    )
                    
                    db_session.add(rule)
                    
                    # Prepare text for embedding with context prefix
                    embedding_text = self._prepare_text_for_embedding(rule, chunk_index)
                    
                    # Add to batch for Pinecone
                    batch_records.append({
                        "_id": vector_id,
                        "text": embedding_text,
                        "metadata": {
                            "rule_id": rule_id,
                            "regulator": "HKMA",
                            "jurisdiction": "HK",
                            "title": circular["title"],
                            "source_url": circular["url"],
                            "published_date": circular.get("date").isoformat() if circular.get("date") else None,
                            "chunk_index": chunk_index if len(chunks) > 1 else None,
                            "total_chunks": len(chunks)
                        }
                    })
                    
                    total_chunks += 1
                    
                    # Batch upsert to Pinecone (96 records at a time)
                    if len(batch_records) >= 96:
                        index.upsert_records(
                            namespace="__default__",
                            records=batch_records
                        )
                        logger.info(f"Upserted batch of {len(batch_records)} records to Pinecone")
                        batch_records = []
                
                # Commit this circular's chunks
                db_session.commit()
                saved_count += 1
                logger.info(f"Saved {len(chunks)} chunk(s) for: {circular['title']}")
                
            except Exception as e:
                logger.error(f"Error saving circular {circular.get('title')}: {str(e)}")
                db_session.rollback()
        
        # Upsert remaining records
        if batch_records:
            index.upsert_records(
                namespace="__default__",
                records=batch_records
            )
            logger.info(f"Upserted final batch of {len(batch_records)} records to Pinecone")
        
        logger.info(f"HKMA crawler: saved {saved_count} circulars ({total_chunks} total chunks)")
        return saved_count
    
    def _chunk_text(self, text: str, max_words: int = 2000, overlap_words: int = 200) -> List[str]:
        """
        Split text into overlapping chunks based on word count.
        
        Args:
            text: Text to chunk
            max_words: Maximum words per chunk
            overlap_words: Number of overlapping words between chunks
            
        Returns:
            List of text chunks
        """
        words = text.split()
        
        if len(words) <= max_words:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(words):
            end = start + max_words
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))
            
            if end >= len(words):
                break
                
            start = end - overlap_words
        
        return chunks
    
    def _prepare_text_for_embedding(self, rule: 'ExternalRule', chunk_index: int) -> str:
        """
        Prepare text for embedding with context prefix.
        
        Args:
            rule: ExternalRule database model
            chunk_index: Index of this chunk
            
        Returns:
            Text with context prefix
        """
        total_chunks = rule.meta.get("total_chunks", 1)
        
        if total_chunks > 1:
            prefix = f"HKMA HK - {rule.rule_title} [Chunk {chunk_index + 1} of {total_chunks}]: "
        else:
            prefix = f"HKMA HK - {rule.rule_title}: "
        
        return prefix + rule.rule_text


def main():
    """Test the crawler"""
    crawler = HKMACrawler(use_cached_html=True)
    circulars = crawler.crawl()
    print(f"Found {len(circulars)} circulars")
    for circular in circulars:
        print(f"- {circular['title']} ({circular['date']})")


if __name__ == "__main__":
    main()
