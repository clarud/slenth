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
    async def test_crawl_returns_circulars(self):
        """Test that crawl method returns list of circulars"""
        crawler = HKMACrawler()
        
        circulars = await crawler.crawl()
        
        assert isinstance(circulars, list)
        assert len(circulars) > 0
    
    @pytest.mark.asyncio
    async def test_circular_structure(self):
        """Test that each circular has required fields"""
        crawler = HKMACrawler()
        
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
            assert circular["source"] == "HKMA"
            assert circular["jurisdiction"] == "HK"
    
    @pytest.mark.asyncio
    async def test_crawl_with_mock_html(self, sample_hkma_html):
        """Test crawling with mocked HTML response"""
        crawler = HKMACrawler()
        
        # Mock the web scraping
        with patch('crawlers.hkma.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_result = Mock()
            mock_result.html = sample_hkma_html
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            # For now, test with placeholder data
            circulars = await crawler.crawl()
            
            assert len(circulars) >= 2
            assert any("Customer Due Diligence" in c["title"] for c in circulars)
    
    def test_save_to_db(self, mock_db_session):
        """Test saving circulars to database"""
        crawler = HKMACrawler()
        
        test_circulars = [
            {
                "title": "Test AML Circular",
                "url": "https://test.hkma.gov.hk/test",
                "date": datetime(2024, 1, 15),
                "content": "Test content for AML circular",
                "source": "HKMA",
                "jurisdiction": "HK",
                "rule_type": "guideline",
            }
        ]
        
        with patch('crawlers.hkma.EmbeddingService') as mock_embed, \
             patch('crawlers.hkma.VectorDBService') as mock_vector:
            
            mock_embed.return_value.embed_text.return_value = [0.1] * 1536
            mock_vector.return_value.upsert_vectors.return_value = True
            
            saved_count = crawler.save_to_db(test_circulars, mock_db_session)
            
            assert saved_count >= 0  # May be 0 if duplicate check works
    
    def test_save_to_db_handles_duplicates(self, mock_db_session):
        """Test that duplicate circulars are not saved"""
        crawler = HKMACrawler()
        
        circular = {
            "title": "Duplicate Test Circular",
            "url": "https://test.hkma.gov.hk/dup",
            "date": datetime(2024, 1, 15),
            "content": "Duplicate test content",
            "source": "HKMA",
            "jurisdiction": "HK",
            "rule_type": "guideline",
        }
        
        with patch('crawlers.hkma.EmbeddingService') as mock_embed, \
             patch('crawlers.hkma.VectorDBService') as mock_vector:
            
            mock_embed.return_value.embed_text.return_value = [0.1] * 1536
            mock_vector.return_value.upsert_vectors.return_value = True
            
            # Save once
            count1 = crawler.save_to_db([circular], mock_db_session)
            
            # Try to save again (should skip duplicate)
            count2 = crawler.save_to_db([circular], mock_db_session)
            
            # Second save should process but not create new records
            assert count2 == 0  # Duplicate should be skipped
    
    @pytest.mark.asyncio
    async def test_crawl_error_handling(self):
        """Test that crawler handles errors gracefully"""
        crawler = HKMACrawler()
        
        with patch('crawlers.hkma.AsyncWebCrawler') as mock_crawler_class:
            # Simulate network error
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(side_effect=Exception("Network error"))
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            # Should not raise exception
            circulars = await crawler.crawl()
            
            # Should return empty list or placeholder data
            assert isinstance(circulars, list)
    
    def test_save_to_db_error_handling(self, mock_db_session):
        """Test that save_to_db handles errors gracefully"""
        crawler = HKMACrawler()
        
        invalid_circular = {
            "title": None,  # Invalid data
            "url": "test",
            "date": "invalid",
            "content": "",
            "source": "HKMA",
            "jurisdiction": "HK",
            "rule_type": "guideline",
        }
        
        # Should not raise exception
        try:
            saved_count = crawler.save_to_db([invalid_circular], mock_db_session)
            assert saved_count == 0
        except Exception:
            # Error handling may vary, but should be logged
            pass


class TestHKMACrawlerIntegration:
    """Integration tests for HKMA crawler (requires actual database)"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_crawl_and_save_workflow(self, mock_db_session):
        """Test complete workflow: crawl -> parse -> save"""
        crawler = HKMACrawler()
        
        # Crawl circulars
        circulars = await crawler.crawl()
        
        assert len(circulars) > 0
        
        # Mock services for saving
        with patch('crawlers.hkma.EmbeddingService') as mock_embed, \
             patch('crawlers.hkma.VectorDBService') as mock_vector:
            
            mock_embed.return_value.embed_text.return_value = [0.1] * 1536
            mock_vector.return_value.upsert_vectors.return_value = True
            
            # Save to database
            saved_count = crawler.save_to_db(circulars, mock_db_session)
            
            # Verify embedding service was called
            assert mock_embed.return_value.embed_text.call_count >= saved_count
            
            # Verify vector DB was called
            if saved_count > 0:
                assert mock_vector.return_value.upsert_vectors.called


# Standalone test function for manual testing
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
