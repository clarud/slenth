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
    async def test_crawl_returns_circulars(self):
        """Test that crawl method returns list of circulars"""
        crawler = FINMACrawler()
        
        circulars = await crawler.crawl()
        
        assert isinstance(circulars, list)
        assert len(circulars) > 0
    
    @pytest.mark.asyncio
    async def test_circular_structure(self):
        """Test that each circular has required fields"""
        crawler = FINMACrawler()
        
        circulars = await crawler.crawl()
        
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
    
    @pytest.mark.asyncio
    async def test_crawl_with_mock_html(self, sample_finma_html):
        """Test crawling with mocked HTML response"""
        crawler = FINMACrawler()
        
        with patch('crawlers.finma.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_result = Mock()
            mock_result.html = sample_finma_html
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            # Test with placeholder data
            circulars = await crawler.crawl()
            
            assert len(circulars) >= 1
            assert any("Anti-Money Laundering" in c["title"] for c in circulars)
    
    @pytest.mark.asyncio
    async def test_swiss_date_format(self):
        """Test that Swiss date formats are handled correctly"""
        crawler = FINMACrawler()
        
        circulars = await crawler.crawl()
        
        for circular in circulars:
            date = circular["date"]
            assert isinstance(date, datetime)
            # Swiss dates often in DD.MM.YYYY format
            assert date.year >= 2020
            assert date.year <= 2025
    
    @pytest.mark.asyncio
    async def test_multilingual_content(self):
        """Test handling of multilingual content (German/English/French)"""
        crawler = FINMACrawler()
        
        circulars = await crawler.crawl()
        
        # FINMA circulars may be in multiple languages
        # Just verify content exists
        for circular in circulars:
            assert len(circular["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_crawl_error_handling(self):
        """Test that crawler handles errors gracefully"""
        crawler = FINMACrawler()
        
        with patch('crawlers.finma.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(side_effect=Exception("SSL Error"))
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            # Should not raise exception
            circulars = await crawler.crawl()
            
            assert isinstance(circulars, list)


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
