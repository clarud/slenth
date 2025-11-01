"""
Integration tests for all crawlers.

Tests all three crawlers together and saves results to output directory.
"""

import pytest
from datetime import datetime
import asyncio

from crawlers.finma import FINMACrawler
from crawlers.hkma import HKMACrawler
from crawlers.mas import MASCrawler


class TestAllCrawlers:
    """Test all three crawlers together"""
    
    @pytest.mark.asyncio
    async def test_all_crawlers_consistent_format(self):
        """Test that all crawlers return consistent format"""
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
            
            assert hkma_keys == mas_keys == finma_keys, "All crawlers should return same structure"
    
    @pytest.mark.asyncio
    async def test_all_crawlers_unique_jurisdictions(self):
        """Test that each crawler has correct jurisdiction"""
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
    
    @pytest.mark.asyncio
    async def test_all_crawlers_save_output(self, clean_output_files, file_saver):
        """Test that all crawlers save their output correctly"""
        hkma = HKMACrawler()
        mas = MASCrawler()
        finma = FINMACrawler()
        
        print("\n" + "="*80)
        print("🚀 Running All Crawlers - Integration Test")
        print("="*80)
        
        # Crawl all sources
        print("\n📥 Crawling FINMA...")
        finma_data = await finma.crawl()
        finma_saved = file_saver.save(finma_data, "finma.jsonl")
        print(f"   ✅ FINMA: {len(finma_data)} circulars found, {finma_saved} saved")
        
        print("\n📥 Crawling HKMA...")
        hkma_data = await hkma.crawl()
        hkma_saved = file_saver.save(hkma_data, "hkma.jsonl")
        print(f"   ✅ HKMA: {len(hkma_data)} circulars found, {hkma_saved} saved")
        
        print("\n📥 Crawling MAS...")
        mas_data = await mas.crawl()
        mas_saved = file_saver.save(mas_data, "mas.jsonl")
        print(f"   ✅ MAS: {len(mas_data)} notices found, {mas_saved} saved")
        
        # Summary
        total_docs = len(finma_data) + len(hkma_data) + len(mas_data)
        total_saved = finma_saved + hkma_saved + mas_saved
        
        print("\n" + "="*80)
        print(f"📊 Total Summary:")
        print(f"   Total documents crawled: {total_docs}")
        print(f"   Total documents saved: {total_saved}")
        print(f"   Output location: tests/crawlers/output/")
        print("="*80 + "\n")
        
        # Assertions
        assert len(finma_data) > 0, "FINMA should return data"
        assert len(hkma_data) > 0, "HKMA should return data"
        assert len(mas_data) > 0, "MAS should return data"
        assert finma_saved > 0, "FINMA should save data"
        assert hkma_saved > 0, "HKMA should save data"
        assert mas_saved > 0, "MAS should save data"
    
    @pytest.mark.asyncio
    async def test_all_crawlers_pdf_content_quality(self):
        """Test that all crawlers extract quality PDF content"""
        hkma = HKMACrawler()
        mas = MASCrawler()
        finma = FINMACrawler()
        
        hkma_data = await hkma.crawl()
        mas_data = await mas.crawl()
        finma_data = await finma.crawl()
        
        # Check FINMA content quality
        for item in finma_data[:3]:
            assert len(item["content"]) > 100, f"FINMA content too short: {item['title']}"
            assert len(item["title"]) > 0, "FINMA title empty"
        
        # Check HKMA content quality
        for item in hkma_data[:3]:
            assert len(item["content"]) > 100, f"HKMA content too short: {item['title']}"
            assert len(item["title"]) > 0, "HKMA title empty"
        
        # Check MAS content quality
        for item in mas_data[:3]:
            assert len(item["content"]) > 100, f"MAS content too short: {item['title']}"
            assert len(item["title"]) > 0, "MAS title empty"


class TestCrawlerPerformance:
    """Test crawler performance and efficiency"""
    
    @pytest.mark.asyncio
    async def test_crawl_speed(self):
        """Test that crawlers complete in reasonable time"""
        import time
        
        finma = FINMACrawler()
        
        start = time.time()
        data = await finma.crawl()
        duration = time.time() - start
        
        assert len(data) > 0
        # Should complete within 5 minutes for reasonable number of documents
        assert duration < 300, f"Crawl took too long: {duration:.1f}s"
        
        print(f"\n⏱️  FINMA crawl completed in {duration:.1f}s ({len(data)} documents)")


# Standalone test function for manual testing
@pytest.mark.asyncio
async def test_all_crawlers_manual():
    """Manual test - can be run directly"""
    print("\n" + "="*80)
    print("🌐 All Crawlers Manual Test")
    print("="*80)
    
    finma = FINMACrawler()
    hkma = HKMACrawler()
    mas = MASCrawler()
    
    print("\n📥 Crawling FINMA...")
    finma_data = await finma.crawl()
    print(f"✅ Found {len(finma_data)} FINMA circulars")
    
    print("\n📥 Crawling HKMA...")
    hkma_data = await hkma.crawl()
    print(f"✅ Found {len(hkma_data)} HKMA circulars")
    
    print("\n📥 Crawling MAS...")
    mas_data = await mas.crawl()
    print(f"✅ Found {len(mas_data)} MAS notices")
    
    print("\n" + "="*80)
    print(f"📊 Total: {len(finma_data) + len(hkma_data) + len(mas_data)} documents")
    print("="*80 + "\n")
    
    # Show samples
    if finma_data:
        print(f"\n📄 Sample FINMA: {finma_data[0]['title'][:60]}...")
    if hkma_data:
        print(f"📄 Sample HKMA: {hkma_data[0]['title'][:60]}...")
    if mas_data:
        print(f"📄 Sample MAS: {mas_data[0]['title'][:60]}...")


if __name__ == "__main__":
    asyncio.run(test_all_crawlers_manual())
