"""
Tests for HKMA crawler.

Tests the Hong Kong Monetary Authority regulatory circular scraper.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from crawlers.hkma import HKMACrawler


class TestHKMACrawler:
    """Test suite for HKMA crawler"""
    
    def test_crawler_initialization(self):
        """Test crawler initializes with correct configuration"""
        crawler = HKMACrawler()
        
        assert crawler.source == "HKMA"
        assert crawler.jurisdiction == "HK"
        assert "hkma.gov.hk" in crawler.base_url
    
    @pytest.mark.asyncio
    async def test_crawl_returns_circulars(self, clean_output_files, file_saver):
        """Test that crawl method returns list of circulars and saves to output"""
        crawler = HKMACrawler()
        
        circulars = await crawler.crawl()
        
        assert isinstance(circulars, list)
        assert len(circulars) > 0
        
        # Save to output file for inspection
        saved = file_saver.save(circulars, "hkma.jsonl")
        print(f"\n✅ Saved {saved} HKMA circulars to tests/crawlers/output/hkma.jsonl")
        
        # Print summary
        print(f"\n📊 HKMA Crawl Summary:")
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
        crawler = HKMACrawler()
        
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
            assert circular["source"] == "HKMA"
            assert circular["jurisdiction"] == "HK"
            
            # Verify content is not empty
            assert len(circular["title"]) > 0, "Title should not be empty"
            assert len(circular["content"]) > 0, "Content should not be empty"
    
    @pytest.mark.asyncio
    async def test_two_layer_crawl(self):
        """Test that HKMA crawler properly crawls detail pages then PDFs"""
        crawler = HKMACrawler()
        
        # This should first find detail pages, then PDFs on those pages
        circulars = await crawler.crawl()
        
        assert len(circulars) > 0, "Should find circulars through two-layer crawl"
        
        # Check that we got actual PDF content
        for circular in circulars[:3]:
            content = circular["content"]
            assert len(content) > 100, f"PDF content too short for {circular['title']}"
    
    @pytest.mark.asyncio
    async def test_pdf_content_extraction(self):
        """Test that PDFs are properly extracted with actual content"""
        crawler = HKMACrawler()
        
        circulars = await crawler.crawl()
        
        assert len(circulars) > 0, "Should extract at least one circular"
        
        # Check that we have actual PDF content
        for circular in circulars[:3]:
            content = circular["content"]
            content_lower = content.lower()
            has_regulatory_content = any(term in content_lower for term in [
                'aml', 'cft', 'money laundering', 'financial', 'regulation',
                'hong kong', 'hkma', 'guideline', 'requirement'
            ])
            assert has_regulatory_content, f"Content doesn't seem regulatory: {circular['title']}"
    



# Standalone test function for manual testing
@pytest.mark.asyncio
async def test_hkma_crawler_manual():
    """Manual test - can be run directly"""
    print("\n" + "="*60)
    print("HKMA Crawler Manual Test")
    print("="*60)
    
    crawler = HKMACrawler()
    circulars = await crawler.crawl()
    
    print(f"\nFound {len(circulars)} circulars:")
    for i, circular in enumerate(circulars, 1):
        print(f"\n{i}. {circular['title']}")
        print(f"   Date: {circular['date']}")
        print(f"   URL: {circular['url']}")
        print(f"   Type: {circular['rule_type']}")
        print(f"   Content preview: {circular['content'][:100]}...")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Run manual test
    asyncio.run(test_hkma_crawler_manual())
