"""
Monetary Authority of Singapore (MAS) Regulatory Crawler

Scrapes MAS notices and guidelines for AML/CFT regulations.
Uses BeautifulSoup for HTML parsing, Selenium for JavaScript handling, and PyPDF2 for PDF extraction.
"""

import logging
import os
import json
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
    
    def __init__(self, use_cached_html: bool = False, max_pages: int = 10):
        # Updated URL for regulations and guidance page with circulars filter
        self.base_url_template = "https://www.mas.gov.sg/regulation/regulations-and-guidance?content_type=Circulars&page={page}&entity_type=Banking"
        # Alternative URL (old): "https://www.mas.gov.sg/regulation/notices"
        self.source = "MAS"
        self.jurisdiction = "SG"
        self.use_cached_html = use_cached_html
        self.max_pages = max_pages
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def crawl(self) -> List[Dict]:
        """Crawl MAS site: find PDF links and parse PDFs across multiple pages."""
        logger.info(f"Starting MAS crawler (up to {self.max_pages} pages)")

        if PdfReader is None:
            msg = "PyPDF2 not available. Install pypdf2 to proceed."
            logger.error(msg)
            raise RuntimeError(msg)

        all_pdf_links = []
        
        if self.use_cached_html:
            # Single cached file mode
            html_path = Path("mas.html")
            if not html_path.exists():
                raise FileNotFoundError(f"Cached HTML file not found: {html_path}")
            html_content = html_path.read_text(encoding="utf-8")
            logger.info("Using cached HTML file")
            pdf_links = self._discover_pdf_links(html_content)
            all_pdf_links.extend(pdf_links)
        else:
            # Crawl multiple pages
            for page_num in range(1, self.max_pages + 1):
                url = self.base_url_template.format(page=page_num)
                logger.info(f"Fetching page {page_num}: {url}")
                
                try:
                    # Use Selenium to handle JavaScript-rendered content
                    html_content = self._fetch_with_selenium(url)
                    
                    # Parse HTML and extract PDF links
                    pdf_links = self._discover_pdf_links(html_content)
                    logger.info(f"Page {page_num}: discovered {len(pdf_links)} PDF links")
                    
                    if not pdf_links:
                        logger.info(f"No results on page {page_num}, stopping pagination")
                        break
                    
                    all_pdf_links.extend(pdf_links)
                    
                except Exception as e:
                    logger.error(f"Failed to fetch page {page_num}: {e}")
                    break

        logger.info(f"MAS discovered {len(all_pdf_links)} total PDF links across all pages")

        # Parse each PDF
        notices: List[Dict] = []
        for i, link in enumerate(all_pdf_links, 1):
            try:
                logger.info(f"Parsing PDF {i}/{len(all_pdf_links)}: {link.get('title', 'Unknown')[:60]}...")
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
                    "rule_type": "circular",
                })
            except Exception as e:
                logger.error(f"MAS PDF parse failed for {link.get('url')}: {e}")
                continue

        logger.info(f"MAS crawler produced {len(notices)} circulars")
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
            
            # Make absolute URL (use page 1 as base for relative URLs)
            base_url = "https://www.mas.gov.sg/regulation/regulations-and-guidance"
            abs_url = urljoin(base_url, href)
            
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

    def _fetch_with_selenium(self, url: str) -> str:
        """Fetch page using Selenium to handle JavaScript rendering."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            driver.get(url)
            
            # Wait for content to load - look for circular links or result cards
            try:
                WebDriverWait(driver, 15).until(
                    lambda d: len(d.find_elements(By.TAG_NAME, "a")) > 20
                )
                # Give extra time for dynamic content
                time.sleep(3)
            except Exception as e:
                logger.warning(f"Wait condition not met, proceeding anyway: {e}")
            
            html_content = driver.page_source
            logger.info(f"Selenium fetched {len(html_content)} bytes")
            
            return html_content
            
        finally:
            driver.quit()

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
        Save crawled circulars to PostgreSQL + Pinecone vector database.
        Uses Pinecone's built-in inference API (no OpenAI needed).
        
        Follows external_rules_ingestion.py pattern:
        1. Check for duplicates (by URL)
        2. Chunk large documents (2000 words max, 200 words overlap)
        3. Prepare text with context prefix
        4. Store in PostgreSQL + Pinecone (Pinecone generates embeddings)
        
        Args:
            notices: List of circular dictionaries from crawler
            db_session: Database session
        """
        from db.models import ExternalRule
        from pinecone import Pinecone
        from config import settings
        from uuid import uuid4
        import hashlib
        
        # Initialize Pinecone client
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(host=settings.pinecone_external_index_host)
        namespace = "__default__"
        
        saved_count = 0
        records_batch = []  # Batch for Pinecone upsert_records
        
        for notice in notices:
            try:
                # Validate content
                content = notice.get("content", "").strip()
                if not content or len(content) < 100:
                    logger.warning(f"Skipping circular with insufficient content: {notice.get('title', 'Unknown')[:50]}")
                    continue
                
                title = notice.get("title", "")
                url = notice.get("url", "")
                
                # Check for duplicates by URL
                existing = db_session.query(ExternalRule).filter(
                    ExternalRule.source_url == url
                ).first()
                
                if existing:
                    logger.debug(f"Circular already exists (URL match): {title[:50]}")
                    continue
                
                # Generate rule_id (REGULATOR-HASH format)
                hash_input = f"{title}{url}".encode('utf-8')
                hash_hex = hashlib.md5(hash_input).hexdigest()[:12]
                rule_id = f"{self.source}-{hash_hex}"
                
                # Chunk content if needed (2000 words max, 200 overlap)
                chunks = self._chunk_text(content, max_words=2000, overlap_words=200)
                logger.info(f"Processing circular: {title[:60]} ({len(chunks)} chunks, {len(content.split())} words)")
                
                # Process each chunk
                for chunk_idx, chunk_content in enumerate(chunks):
                    try:
                        # Prepare text with context for embedding
                        text_for_embedding = self._prepare_text_for_embedding(
                            {**notice, "content": chunk_content},
                            chunk_index=chunk_idx if len(chunks) > 1 else None
                        )
                        
                        # Generate unique ID for this chunk
                        vector_id = str(uuid4())
                        chunk_rule_id = f"{rule_id}-{chunk_idx}" if len(chunks) > 1 else rule_id
                        
                        # Create database record
                        db_rule = ExternalRule(
                            rule_id=chunk_rule_id,
                            regulator=self.source,
                            jurisdiction=self.jurisdiction,
                            rule_title=title,
                            rule_text=chunk_content,
                            source_url=url,
                            document_title=title,
                            section_path="",
                            published_date=notice.get("date"),
                            effective_date=notice.get("effective_date", notice.get("date")),
                            vector_id=vector_id,
                            chunk_index=chunk_idx if len(chunks) > 1 else None,
                            meta={
                                "crawled_at": datetime.utcnow().isoformat(),
                                "rule_type": notice.get("rule_type", "circular"),
                                "total_chunks": len(chunks),
                                "word_count": len(chunk_content.split()),
                                "full_word_count": len(content.split()),
                            },
                            scraped_at=datetime.utcnow(),
                        )
                        
                        db_session.add(db_rule)
                        db_session.flush()  # Get the ID without committing
                        
                        # Prepare Pinecone record (flat structure for inference API)
                        record = {
                            "_id": vector_id,
                            "text": text_for_embedding,  # Full text with context for embedding
                            # Metadata fields at top level
                            "rule_id": chunk_rule_id,
                            "regulator": self.source,
                            "jurisdiction": self.jurisdiction,
                            "title": title[:500],  # Truncate for metadata
                            "passage_text": chunk_content[:512],  # Preview text
                            "url": url[:500],
                            "chunk_index": chunk_idx if len(chunks) > 1 else 0,
                            "total_chunks": len(chunks),
                            "published_date": notice.get("date").isoformat() if notice.get("date") else None,
                            "rule_type": notice.get("rule_type", "circular"),
                            "word_count": len(chunk_content.split()),
                            "is_active": True,
                            "ingestion_date": datetime.utcnow().isoformat(),
                        }
                        
                        # Add to batch
                        records_batch.append(record)
                        
                        # Batch upsert every 96 records (Pinecone inference API recommended batch size)
                        if len(records_batch) >= 96:
                            try:
                                index.upsert_records(namespace=namespace, records=records_batch)
                                db_session.commit()
                                saved_count += len(records_batch)
                                logger.info(f"✅ Upserted batch of {len(records_batch)} records to Pinecone")
                            except Exception as batch_err:
                                logger.warning(f"⚠️ Batch upsert failed, trying per-record: {batch_err}")
                                # Try per-record upsert
                                for rec in records_batch:
                                    try:
                                        index.upsert_records(namespace=namespace, records=[rec])
                                        saved_count += 1
                                    except Exception as rec_err:
                                        logger.error(f"❌ Failed to upsert record {rec.get('_id')}: {rec_err}")
                                        db_session.rollback()
                            
                            # Clear batch
                            records_batch = []
                    
                    except Exception as e:
                        logger.error(f"Error processing chunk {chunk_idx} of {title[:50]}: {str(e)}")
                        db_session.rollback()
                        continue
            
            except Exception as e:
                logger.error(f"Error saving circular {notice.get('title', 'Unknown')[:50]}: {str(e)}")
                db_session.rollback()
                continue
        
        # Upsert remaining records
        if records_batch:
            try:
                index.upsert_records(namespace=namespace, records=records_batch)
                db_session.commit()
                saved_count += len(records_batch)
                logger.info(f"✅ Upserted final batch of {len(records_batch)} records to Pinecone")
            except Exception as batch_err:
                logger.warning(f"⚠️ Final batch upsert failed, trying per-record: {batch_err}")
                for rec in records_batch:
                    try:
                        index.upsert_records(namespace=namespace, records=[rec])
                        saved_count += 1
                    except Exception as rec_err:
                        logger.error(f"❌ Failed to upsert record {rec.get('_id')}: {rec_err}")
                        db_session.rollback()
        
        logger.info(f"💾 Saved {saved_count} circular chunks to PostgreSQL + Pinecone")
        return saved_count
    
    def _chunk_text(self, text: str, max_words: int = 2000, overlap_words: int = 200) -> List[str]:
        """Split text into overlapping chunks based on word count."""
        words = text.split()
        
        if len(words) <= max_words:
            return [text]
        
        chunks = []
        start_idx = 0
        
        while start_idx < len(words):
            end_idx = start_idx + max_words
            chunk_words = words[start_idx:end_idx]
            chunks.append(" ".join(chunk_words))
            
            # Move start index forward, accounting for overlap
            start_idx += (max_words - overlap_words)
            
            # Break if we're at the end
            if end_idx >= len(words):
                break
        
        return chunks
    
    def _prepare_text_for_embedding(self, rule: Dict, chunk_index: Optional[int] = None) -> str:
        """Prepare text for embedding with context prefix."""
        source = rule.get("source", self.source)
        jurisdiction = rule.get("jurisdiction", self.jurisdiction)
        title = rule.get("title", "")
        content = rule.get("content", "")
        
        # Build context prefix: "MAS SG - Title [Chunk X]: Content"
        prefix_parts = [f"{source} {jurisdiction}"]
        if title:
            prefix_parts.append(f"- {title}")
        if chunk_index is not None:
            prefix_parts.append(f"[Chunk {chunk_index}]")
        
        prefix = " ".join(prefix_parts) + ": "
        
        return prefix + content


def main():
    """Test the crawler"""
    print("=== Testing MAS Crawler with Selenium (Multi-page) ===\n")
    crawler = MASCrawler(use_cached_html=False, max_pages=5)  # Test first 5 pages
    notices = crawler.crawl()
    print(f"\n✅ Found {len(notices)} MAS circulars\n")
    print("Sample notices:")
    for i, notice in enumerate(notices[:10], 1):
        print(f"\n{i}. {notice['title'][:80]}...")
        print(f"   Date: {notice['date']}")
        print(f"   Content: {len(notice['content'])} chars")
        print(f"   URL: {notice['url'][:80]}...")
    
    if len(notices) > 10:
        print(f"\n... and {len(notices) - 10} more circulars")
    
    print(f"\n📊 Summary:")
    print(f"   Total circulars: {len(notices)}")
    if notices:
        print(f"   Date range: {min(n['date'] for n in notices).strftime('%Y-%m-%d')} to {max(n['date'] for n in notices).strftime('%Y-%m-%d')}")
        print(f"   Total content: {sum(len(n['content']) for n in notices):,} characters")
    else:
        print("   No circulars found")


if __name__ == "__main__":
    main()
