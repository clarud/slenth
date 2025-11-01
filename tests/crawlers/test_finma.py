"""
Tests for FINMA crawler.

Tests the Swiss Financial Market Supervisory Authority circular scraper.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from crawlers.finma import FINMACrawler


class TestFINMACrawler:
    """Test suite for FINMA crawler"""
    
    def test_crawler_initialization(self):
        """Test crawler initializes with correct configuration"""
        crawler = FINMACrawler()
        
        assert crawler.source == "FINMA"
        assert crawler.jurisdiction == "CH"
        assert "finma.ch" in crawler.base_url
    
    @pytest.mark.asyncio
    async def test_crawl_returns_circulars(self, clean_output_files, file_saver):
        """Test that crawl method returns list of circulars and saves to output"""
        crawler = FINMACrawler()
        
        circulars = await crawler.crawl()
        
        assert isinstance(circulars, list)
        assert len(circulars) > 0
        
        # Save to output file for inspection
        saved = file_saver.save(circulars, "finma.jsonl")
        print(f"\n✅ Saved {saved} FINMA circulars to tests/crawlers/output/finma.jsonl")
        
        # Print summary
        print(f"\n📊 FINMA Crawl Summary:")
        print(f"   Total circulars: {len(circulars)}")
        print(f"   Saved to file: {saved}")
        if circulars:
            print(f"\n📄 Sample circular:")
            sample = circulars[0]
            print(f"   Title: {sample['title'][:80]}...")
            print(f"   URL: {sample['url']}")
            print(f"   Date: {sample['date']}")
            print(f"   Content length: {len(sample['content'])} chars")
    
    @pytest.mark.asyncio
    async def test_circular_structure(self):
        """Test that each circular has required fields"""
        crawler = FINMACrawler()
        
        circulars = await crawler.crawl()
        
        assert len(circulars) > 0, "Should crawl at least one circular"
        
        for circular in circulars:
            assert "title" in circular
            assert "url" in circular
            assert "date" in circular
            assert "content" in circular
            assert "source" in circular
            assert "jurisdiction" in circular
            assert "rule_type" in circular
            
            # Verify data types
            assert isinstance(circular["title"], str)
            assert isinstance(circular["url"], str)
            assert isinstance(circular["date"], datetime)
            assert isinstance(circular["content"], str)
            assert circular["source"] == "FINMA"
            assert circular["jurisdiction"] == "CH"
            
            # Verify content is not empty
            assert len(circular["title"]) > 0, "Title should not be empty"
            assert len(circular["content"]) > 0, "Content should not be empty"
    
    
    @pytest.mark.asyncio
    async def test_pdf_content_extraction(self):
        """Test that PDFs are properly extracted with actual content"""
        crawler = FINMACrawler()
        
        circulars = await crawler.crawl()
        
        assert len(circulars) > 0, "Should extract at least one circular"
        
        # Check that we have actual PDF content, not just links
        for circular in circulars[:3]:  # Check first 3
            content = circular["content"]
            assert len(content) > 100, f"PDF content too short for {circular['title']}"
            # PDF content should have some common regulatory terms
            content_lower = content.lower()
            has_regulatory_content = any(term in content_lower for term in [
                'aml', 'money laundering', 'financial', 'regulation', 
                'compliance', 'requirement', 'circular', 'finma'
            ])
            assert has_regulatory_content, f"Content doesn't seem like a regulatory document: {circular['title']}"
    
    @pytest.mark.asyncio
    async def test_swiss_date_format(self):
        """Test that Swiss date formats are handled correctly"""
        crawler = FINMACrawler()
        
        circulars = await crawler.crawl()
        
        assert len(circulars) > 0
        
        for circular in circulars:
            date = circular["date"]
            assert isinstance(date, datetime)
            # Swiss dates often in DD.MM.YYYY format
            assert date.year >= 2020
            assert date.year <= 2026
    
    @pytest.mark.asyncio
    async def test_multilingual_content(self):
        """Test handling of multilingual content (German/English/French)"""
        crawler = FINMACrawler()
        
        circulars = await crawler.crawl()
        
        assert len(circulars) > 0
        
        # FINMA circulars may be in multiple languages
        # Just verify content exists and is substantial
        for circular in circulars:
            assert len(circular["content"]) > 50, "Content should be substantial"
    
    


class TestAllCrawlers:
    """Test all three crawlers together"""
    
    @pytest.mark.asyncio
    async def test_all_crawlers_consistent_format(self):
        """Test that all crawlers return consistent format"""
        from crawlers.hkma import HKMACrawler
        from crawlers.mas import MASCrawler
        
        hkma = HKMACrawler()
        mas = MASCrawler()
        finma = FINMACrawler()
        
        hkma_data = await hkma.crawl()
        mas_data = await mas.crawl()
        finma_data = await finma.crawl()
        
        # All should return lists
        assert isinstance(hkma_data, list)
        assert isinstance(mas_data, list)
        assert isinstance(finma_data, list)
        
        # All should have data
        assert len(hkma_data) > 0
        assert len(mas_data) > 0
        assert len(finma_data) > 0
        
        # Check keys are consistent
        if hkma_data and mas_data and finma_data:
            hkma_keys = set(hkma_data[0].keys())
            mas_keys = set(mas_data[0].keys())
            finma_keys = set(finma_data[0].keys())
            
            assert hkma_keys == mas_keys == finma_keys
    
    @pytest.mark.asyncio
    async def test_all_crawlers_unique_jurisdictions(self):
        """Test that each crawler has correct jurisdiction"""
        from crawlers.hkma import HKMACrawler
        from crawlers.mas import MASCrawler
        
        hkma = HKMACrawler()
        mas = MASCrawler()
        finma = FINMACrawler()
        
        hkma_data = await hkma.crawl()
        mas_data = await mas.crawl()
        finma_data = await finma.crawl()
        
        # Check jurisdictions
        assert all(c["jurisdiction"] == "HK" for c in hkma_data)
        assert all(n["jurisdiction"] == "SG" for n in mas_data)
        assert all(c["jurisdiction"] == "CH" for c in finma_data)
    
    @pytest.mark.asyncio
    async def test_all_crawlers_unique_sources(self):
        """Test that each crawler has correct source"""
        from crawlers.hkma import HKMACrawler
        from crawlers.mas import MASCrawler
        
        hkma = HKMACrawler()
        mas = MASCrawler()
        finma = FINMACrawler()
        
        hkma_data = await hkma.crawl()
        mas_data = await mas.crawl()
        finma_data = await finma.crawl()
        
        # Check sources
        assert all(c["source"] == "HKMA" for c in hkma_data)
        assert all(n["source"] == "MAS" for n in mas_data)
        assert all(c["source"] == "FINMA" for c in finma_data)


# Standalone test function for manual testing
@pytest.mark.asyncio
async def test_finma_crawler_manual():
    """Manual test - can be run directly"""
    print("\n" + "="*60)
    print("FINMA Crawler Manual Test")
    print("="*60)
    
    crawler = FINMACrawler()
    circulars = await crawler.crawl()
    
    print(f"\nFound {len(circulars)} circulars:")
    for i, circular in enumerate(circulars, 1):
        print(f"\n{i}. {circular['title']}")
        print(f"   Date: {circular['date']}")
        print(f"   URL: {circular['url']}")
        print(f"   Type: {circular['rule_type']}")
        print(f"   Jurisdiction: {circular['jurisdiction']}")
        print(f"   Content preview: {circular['content'][:100]}...")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(test_finma_crawler_manual())
