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
    async def test_crawl_returns_notices(self):
        """Test that crawl method returns list of notices"""
        crawler = MASCrawler()
        
        notices = await crawler.crawl()
        
        assert isinstance(notices, list)
        assert len(notices) > 0
    
    @pytest.mark.asyncio
    async def test_notice_structure(self):
        """Test that each notice has required fields"""
        crawler = MASCrawler()
        
        notices = await crawler.crawl()
        
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
    
    @pytest.mark.asyncio
    async def test_crawl_with_mock_html(self, sample_mas_html):
        """Test crawling with mocked HTML response"""
        crawler = MASCrawler()
        
        with patch('crawlers.mas.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_result = Mock()
            mock_result.html = sample_mas_html
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            # Test with placeholder data
            notices = await crawler.crawl()
            
            assert len(notices) >= 2
            assert any("Money Laundering" in n["title"] for n in notices)
    
    @pytest.mark.asyncio
    async def test_specific_notice_types(self):
        """Test that different notice types are handled correctly"""
        crawler = MASCrawler()
        
        notices = await crawler.crawl()
        
        # Check for different rule types
        rule_types = [n["rule_type"] for n in notices]
        assert "notice" in rule_types or "guideline" in rule_types
    
    @pytest.mark.asyncio
    async def test_crawl_error_handling(self):
        """Test that crawler handles errors gracefully"""
        crawler = MASCrawler()
        
        with patch('crawlers.mas.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(side_effect=Exception("Connection timeout"))
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            # Should not raise exception
            notices = await crawler.crawl()
            
            assert isinstance(notices, list)
    
    @pytest.mark.asyncio
    async def test_date_parsing(self):
        """Test that dates are parsed correctly"""
        crawler = MASCrawler()
        
        notices = await crawler.crawl()
        
        for notice in notices:
            date = notice["date"]
            assert isinstance(date, datetime)
            # Check date is reasonable (not in future, not too old)
            assert date.year >= 2020
            assert date.year <= 2025


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
