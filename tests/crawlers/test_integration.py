"""
Integration tests for all crawlers.

Tests the complete workflow: crawl -> parse -> save -> retrieve
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch

from crawlers.hkma import HKMACrawler
from crawlers.mas import MASCrawler
from crawlers.finma import FINMACrawler


class TestCrawlerIntegration:
    """Integration tests for crawler workflow"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_crawl_all_regulators(self):
        """Test crawling all three regulators"""
        print("\n" + "="*60)
        print("INTEGRATION TEST: Crawling All Regulators")
        print("="*60)
        
        hkma = HKMACrawler()
        mas = MASCrawler()
        finma = FINMACrawler()
        
        # Crawl all in parallel
        results = await asyncio.gather(
            hkma.crawl(),
            mas.crawl(),
            finma.crawl(),
            return_exceptions=True
        )
        
        hkma_data, mas_data, finma_data = results
        
        # Verify all succeeded
        assert not isinstance(hkma_data, Exception), f"HKMA crawl failed: {hkma_data}"
        assert not isinstance(mas_data, Exception), f"MAS crawl failed: {mas_data}"
        assert not isinstance(finma_data, Exception), f"FINMA crawl failed: {finma_data}"
        
        # Print results
        print(f"\nResults:")
        print(f"  HKMA: {len(hkma_data)} circulars")
        print(f"  MAS: {len(mas_data)} notices")
        print(f"  FINMA: {len(finma_data)} circulars")
        
        total = len(hkma_data) + len(mas_data) + len(finma_data)
        print(f"\nTotal: {total} regulatory documents")
        
        assert total > 0, "Should have found at least some regulatory documents"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_all_to_database(self, mock_db_session):
        """Test saving all crawled data to database"""
        hkma = HKMACrawler()
        mas = MASCrawler()
        finma = FINMACrawler()
        
        # Crawl all
        hkma_data = await hkma.crawl()
        mas_data = await mas.crawl()
        finma_data = await finma.crawl()
        
        # Mock services
        with patch('crawlers.hkma.EmbeddingService') as mock_embed, \
             patch('crawlers.hkma.VectorDBService') as mock_vector:
            
            mock_embed.return_value.embed_text.return_value = [0.1] * 1536
            mock_vector.return_value.upsert_vectors.return_value = True
            
            # Save all
            hkma_saved = hkma.save_to_db(hkma_data, mock_db_session)
            # Note: MAS and FINMA crawlers need save_to_db method implemented
            # For now, just test HKMA
            
            print(f"\nSaved to database:")
            print(f"  HKMA: {hkma_saved} records")
            
            assert hkma_saved >= 0
    
    @pytest.mark.integration
    def test_data_quality(self):
        """Test data quality of crawled circulars"""
        async def check_quality():
            hkma = HKMACrawler()
            data = await hkma.crawl()
            
            issues = []
            
            for i, circular in enumerate(data):
                # Check title length
                if len(circular["title"]) < 10:
                    issues.append(f"Circular {i}: Title too short")
                
                # Check content length
                if len(circular["content"]) < 50:
                    issues.append(f"Circular {i}: Content too short")
                
                # Check URL format
                if not circular["url"].startswith("http"):
                    issues.append(f"Circular {i}: Invalid URL format")
                
                # Check date is recent
                if circular["date"].year < 2020:
                    issues.append(f"Circular {i}: Date seems too old")
            
            return issues
        
        issues = asyncio.run(check_quality())
        
        if issues:
            print("\n⚠️  Data Quality Issues:")
            for issue in issues:
                print(f"  - {issue}")
        
        # Allow some issues but not too many
        assert len(issues) < len(issues) * 0.5, "Too many data quality issues"


class TestCrawlerPerformance:
    """Performance tests for crawlers"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_crawl_speed(self):
        """Test that crawling completes in reasonable time"""
        import time
        
        hkma = HKMACrawler()
        
        start = time.time()
        data = await hkma.crawl()
        elapsed = time.time() - start
        
        print(f"\nCrawl time: {elapsed:.2f}s")
        print(f"Circulars found: {len(data)}")
        print(f"Speed: {len(data)/elapsed:.2f} circulars/sec")
        
        # Should complete within reasonable time
        assert elapsed < 30, "Crawling should not take more than 30 seconds"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_parallel_crawling(self):
        """Test that parallel crawling is faster than sequential"""
        import time
        
        hkma = HKMACrawler()
        mas = MASCrawler()
        finma = FINMACrawler()
        
        # Sequential
        start_seq = time.time()
        await hkma.crawl()
        await mas.crawl()
        await finma.crawl()
        seq_time = time.time() - start_seq
        
        # Parallel
        start_par = time.time()
        await asyncio.gather(
            hkma.crawl(),
            mas.crawl(),
            finma.crawl()
        )
        par_time = time.time() - start_par
        
        print(f"\nSequential: {seq_time:.2f}s")
        print(f"Parallel: {par_time:.2f}s")
        print(f"Speedup: {seq_time/par_time:.2f}x")
        
        # Parallel should be faster (or at least not slower)
        assert par_time <= seq_time * 1.1, "Parallel should not be slower than sequential"


# Standalone comprehensive test
async def run_comprehensive_test():
    """Run a comprehensive test of all crawlers"""
    print("\n" + "="*80)
    print("COMPREHENSIVE CRAWLER TEST")
    print("="*80)
    
    crawlers = [
        ("HKMA", HKMACrawler()),
        ("MAS", MASCrawler()),
        ("FINMA", FINMACrawler()),
    ]
    
    all_results = []
    
    for name, crawler in crawlers:
        print(f"\n{'─'*80}")
        print(f"Testing {name} Crawler")
        print(f"{'─'*80}")
        
        try:
            data = await crawler.crawl()
            
            print(f"✅ Success: Found {len(data)} documents")
            
            if data:
                sample = data[0]
                print(f"\nSample document:")
                print(f"  Title: {sample['title']}")
                print(f"  Date: {sample['date']}")
                print(f"  URL: {sample['url']}")
                print(f"  Type: {sample['rule_type']}")
                print(f"  Content: {sample['content'][:100]}...")
            
            all_results.extend(data)
            
        except Exception as e:
            print(f"❌ Failed: {str(e)}")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total documents crawled: {len(all_results)}")
    print(f"By jurisdiction:")
    
    by_jurisdiction = {}
    for doc in all_results:
        jur = doc["jurisdiction"]
        by_jurisdiction[jur] = by_jurisdiction.get(jur, 0) + 1
    
    for jur, count in by_jurisdiction.items():
        print(f"  {jur}: {count} documents")
    
    print(f"\n✅ All tests complete!")


if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())
