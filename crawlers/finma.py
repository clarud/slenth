"""
Swiss Financial Market Supervisory Authority (FINMA) Regulatory Crawler

Scrapes FINMA circulars and guidelines for AML regulations.
Uses Crawl4AI to discover PDF links and extract PDF content without LLMs.
"""

import logging
import os
import json
import re
from urllib.parse import urljoin
from datetime import datetime
from typing import List, Dict, Optional
import asyncio

logger = logging.getLogger(__name__)

# Crawl4AI imports (guarded)
try:  # pragma: no cover
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, JsonCssExtractionStrategy  # type: ignore
    from crawl4ai.async_configs import BrowserConfig  # type: ignore
    from crawl4ai.processors.pdf import PDFCrawlerStrategy, PDFContentScrapingStrategy  # type: ignore
except Exception:  # pragma: no cover
    AsyncWebCrawler = None  # type: ignore
    CrawlerRunConfig = None  # type: ignore
    CacheMode = None  # type: ignore
    JsonCssExtractionStrategy = None  # type: ignore
    BrowserConfig = None  # type: ignore
    PDFCrawlerStrategy = None  # type: ignore
    PDFContentScrapingStrategy = None  # type: ignore

# Online-only toggle (default True)
ONLINE_ONLY = os.getenv("CRAWLER_ONLINE_ONLY", "true").lower() in {"1", "true", "yes"}


class FINMACrawler:
    """Crawler for FINMA regulatory circulars"""
    
    def __init__(self):
        self.base_url = "https://www.finma.ch/en/documentation/finma-circulars/"
        self.source = "FINMA"
        self.jurisdiction = "CH"
    
    async def crawl(self) -> List[Dict]:
        """Crawl FINMA site: find PDF links and parse PDFs."""
        logger.info(f"Starting FINMA crawler from {self.base_url}")

        if AsyncWebCrawler is None or JsonCssExtractionStrategy is None:
            msg = "Crawl4AI not available; online-only mode is enforced. Install crawl4ai to proceed."
            logger.error(msg)
            raise RuntimeError(msg)

        # Optional download mode: click all PDF anchors and parse local files
        use_downloads = os.getenv("CRAWLER_USE_DOWNLOADS", "false").lower() in {"1", "true", "yes"}
        downloads_dir = os.getenv("CRAWLER_DOWNLOADS_DIR")

        if use_downloads and BrowserConfig is not None:
            downloaded = await self._download_pdfs_from_page(self.base_url, downloads_dir)
            logger.info(f"FINMA downloaded {len(downloaded)} files")
            circulars: List[Dict] = []
            for path in downloaded[:50]:  # safety cap
                try:
                    local_path = os.path.abspath(path)
                    doc = await self._parse_pdf(local_path)
                    title = doc.get("title") or os.path.basename(local_path)
                    content = doc.get("text", "")
                    # FINMA links page didn't provide date text in this branch
                    date = datetime.utcnow()
                    circulars.append(
                        {
                            "title": title,
                            "url": local_path,
                            "date": date,
                            "content": content,
                            "source": self.source,
                            "jurisdiction": self.jurisdiction,
                            "rule_type": "circular",
                        }
                    )
                except Exception as e:
                    logger.error(f"FINMA local PDF parse failed for {path}: {e}")
                    continue
            logger.info(f"FINMA crawler produced {len(circulars)} circulars from downloads")
            return circulars
        else:
            pdf_links = await self._discover_pdf_links(self.base_url)
            logger.info(f"FINMA discovered {len(pdf_links)} PDF links")

            circulars: List[Dict] = []
            for link in pdf_links[:25]:
                try:
                    doc = await self._parse_pdf(link["url"])
                    title = link.get("title") or doc.get("title") or "FINMA Circular"
                    date = self._parse_date(link.get("date_text")) or datetime.utcnow()
                    content = doc.get("text", "")
                    circulars.append(
                        {
                            "title": title,
                            "url": link["url"],
                            "date": date,
                            "content": content,
                            "source": self.source,
                            "jurisdiction": self.jurisdiction,
                            "rule_type": "circular",
                        }
                    )
                except Exception as e:
                    logger.error(f"FINMA PDF parse failed for {link.get('url')}: {e}")
                    continue

            logger.info(f"FINMA crawler produced {len(circulars)} circulars")
            return circulars

    async def _discover_pdf_links(self, url: str) -> List[Dict]:
        schema = {
            "name": "pdf_links",
            "baseSelector": "a",
            "fields": [
                {"name": "href", "type": "attribute", "attribute": "href"},
                {"name": "text", "type": "text"},
            ],
        }
        extraction = JsonCssExtractionStrategy(schema, verbose=False)
        config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, extraction_strategy=extraction)
        links: List[Dict] = []
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url, config=config)
            if not getattr(result, "success", False):
                return links
            try:
                items = json.loads(result.extracted_content) if result.extracted_content else []
            except Exception:
                items = []

        for it in items or []:
            href = (it.get("href") or "").strip()
            if not href:
                continue
            if href.lower().endswith(".pdf"):
                abs_url = urljoin(url, href)
                links.append({
                    "url": abs_url,
                    "title": (it.get("text") or "").strip(),
                    "date_text": (it.get("text") or "").strip(),
                })
        return links

    async def _parse_pdf(self, pdf_url: str) -> Dict:
        pdf_scraper = PDFContentScrapingStrategy(extract_images=False, save_images_locally=False)
        run_cfg = CrawlerRunConfig(scraping_strategy=pdf_scraper)
        async with AsyncWebCrawler(crawler_strategy=PDFCrawlerStrategy(), verbose=False) as crawler:
            result = await crawler.arun(url=pdf_url, config=run_cfg)
            if not getattr(result, "success", False):
                raise RuntimeError(getattr(result, "error_message", "PDF crawl failed"))
            text = ""
            md = getattr(result, "markdown", None)
            if md is not None and hasattr(md, "raw_markdown"):
                text = md.raw_markdown or ""
            meta = getattr(result, "metadata", {}) or {}
            title = meta.get("title") or ""
            return {"text": text, "title": title, "metadata": meta}

    def _parse_date(self, text: Optional[str]) -> Optional[datetime]:
        if not text:
            return None
        patterns = [
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",
            r"(\d{4})-(\d{2})-(\d{2})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if not m:
                continue
            try:
                if pat == patterns[0]:
                    d, mm, y = m.groups()
                    return datetime(int(y), int(mm), int(d))
                if pat == patterns[1]:
                    y, mm, dd = m.groups()
                    return datetime(int(y), int(mm), int(dd))
            except Exception:
                continue
        return None

    async def _download_pdfs_from_page(self, url: str, download_dir: str | None) -> List[str]:
        """Use BrowserConfig to click .pdf links and collect downloaded file paths."""
        if BrowserConfig is None:
            return []
        target_dir = download_dir or os.path.join(os.getcwd(), "crawler_downloads")
        os.makedirs(target_dir, exist_ok=True)

        browser_cfg = BrowserConfig(accept_downloads=True, downloads_path=target_dir)
        # Click all anchors ending with .pdf, with a small delay between clicks
        run_cfg = CrawlerRunConfig(
            js_code="""
                const links = Array.from(document.querySelectorAll('a[href$=".pdf"]'));
                for (const [i, link] of links.entries()) {
                    link.click();
                    await new Promise(r => setTimeout(r, 400));
                }
            """,
            wait_for=8,
        )
        files: List[str] = []
        async with AsyncWebCrawler(config=browser_cfg, verbose=False) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
            dl = getattr(result, "downloaded_files", None)
            if dl:
                files.extend([str(p) for p in dl])
        return files


if __name__ == "__main__":
    async def main():
        crawler = FINMACrawler()
        circulars = await crawler.crawl()
        print(f"Found {len(circulars)} FINMA circulars")
        for c in circulars[:3]:
            print("-", c["title"], c["date"], c["url"]) 
    
    asyncio.run(main())
