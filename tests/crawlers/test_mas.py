"""
Tests for MAS crawler.

Tests the Monetary Authority of Singapore regulatory notice scraper.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from crawlers.mas import MASCrawler


class TestMASCrawler:
    """Test suite for MAS crawler"""
    
    def test_crawler_initialization(self):
        """Test crawler initializes with correct configuration"""
        crawler = MASCrawler()
        
        assert crawler.source == "MAS"
        assert crawler.jurisdiction == "SG"
        assert "mas.gov.sg" in crawler.base_url
    
    @pytest.mark.asyncio
    async def test_crawl_returns_notices(self, clean_output_files, file_saver):
        """Test that crawl method returns list of notices and saves to output"""
        crawler = MASCrawler()
        
        notices = await crawler.crawl()
        
        assert isinstance(notices, list)
        assert len(notices) > 0
        
        # Save to output file for inspection
        saved = file_saver.save(notices, "mas.jsonl")
        print(f"\n✅ Saved {saved} MAS notices to tests/crawlers/output/mas.jsonl")
        
        # Print summary
        print(f"\n📊 MAS Crawl Summary:")
        print(f"   Total notices: {len(notices)}")
        print(f"   Saved to file: {saved}")
        if notices:
            print(f"\n📄 Sample notice:")
            sample = notices[0]
            print(f"   Title: {sample['title'][:80]}...")
            print(f"   URL: {sample['url']}")
            print(f"   Date: {sample['date']}")
            print(f"   Content length: {len(sample['content'])} chars")
    
    @pytest.mark.asyncio
    async def test_notice_structure(self):
        """Test that each notice has required fields"""
        crawler = MASCrawler()
        
        notices = await crawler.crawl()
        
        assert len(notices) > 0, "Should crawl at least one notice"
        
        for notice in notices:
            assert "title" in notice
            assert "url" in notice
            assert "date" in notice
            assert "content" in notice
            assert "source" in notice
            assert "jurisdiction" in notice
            assert "rule_type" in notice
            
            # Verify data types
            assert isinstance(notice["title"], str)
            assert isinstance(notice["url"], str)
            assert isinstance(notice["date"], datetime)
            assert isinstance(notice["content"], str)
            assert notice["source"] == "MAS"
            assert notice["jurisdiction"] == "SG"
            
            # Verify content is not empty
            assert len(notice["title"]) > 0, "Title should not be empty"
            assert len(notice["content"]) > 0, "Content should not be empty"
    
    @pytest.mark.asyncio
    async def test_two_layer_crawl(self):
        """Test that MAS crawler properly crawls detail pages then PDFs"""
        crawler = MASCrawler()
        
        # This should first find detail pages, then PDFs on those pages
        notices = await crawler.crawl()
        
        assert len(notices) > 0, "Should find notices through two-layer crawl"
        
        # Check that we got actual PDF content
        for notice in notices[:3]:
            content = notice["content"]
            assert len(content) > 100, f"PDF content too short for {notice['title']}"
    
    @pytest.mark.asyncio
    async def test_pdf_content_extraction(self):
        """Test that PDFs are properly extracted with actual content"""
        crawler = MASCrawler()
        
        notices = await crawler.crawl()
        
        assert len(notices) > 0, "Should extract at least one notice"
        
        # Check that we have actual PDF content
        for notice in notices[:3]:
            content = notice["content"]
            content_lower = content.lower()
            has_regulatory_content = any(term in content_lower for term in [
                'aml', 'cft', 'money laundering', 'financial', 'regulation',
                'singapore', 'mas', 'notice', 'requirement', 'monetary authority'
            ])
            assert has_regulatory_content, f"Content doesn't seem regulatory: {notice['title']}"
    
    
    @pytest.mark.asyncio
    async def test_date_parsing(self):
        """Test that dates are parsed correctly"""
        crawler = MASCrawler()
        
        notices = await crawler.crawl()
        
        assert len(notices) > 0
        
        for notice in notices:
            date = notice["date"]
            assert isinstance(date, datetime)
            # Check date is reasonable (not in future, not too old)
            assert date.year >= 2020
            assert date.year <= 2026


class TestMASCrawlerComparison:
    """Compare MAS crawler output with HKMA"""
    
    @pytest.mark.asyncio
    async def test_consistent_output_format(self):
        """Test that MAS crawler output matches HKMA format"""
        from crawlers.hkma import HKMACrawler
        
        mas_crawler = MASCrawler()
        hkma_crawler = HKMACrawler()
        
        mas_notices = await mas_crawler.crawl()
        hkma_circulars = await hkma_crawler.crawl()
        
        # Both should have same keys
        if mas_notices and hkma_circulars:
            mas_keys = set(mas_notices[0].keys())
            hkma_keys = set(hkma_circulars[0].keys())
            
            assert mas_keys == hkma_keys, "Output format should be consistent across crawlers"


# Standalone test function for manual testing
@pytest.mark.asyncio
async def test_mas_crawler_manual():
    """Manual test - can be run directly"""
    print("\n" + "="*60)
    print("MAS Crawler Manual Test")
    print("="*60)
    
    crawler = MASCrawler()
    notices = await crawler.crawl()
    
    print(f"\nFound {len(notices)} notices:")
    for i, notice in enumerate(notices, 1):
        print(f"\n{i}. {notice['title']}")
        print(f"   Date: {notice['date']}")
        print(f"   URL: {notice['url']}")
        print(f"   Type: {notice['rule_type']}")
        print(f"   Jurisdiction: {notice['jurisdiction']}")
        print(f"   Content preview: {notice['content'][:100]}...")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(test_mas_crawler_manual())
