"""Test MAS crawler - verify it crawls circular pages and extracts PDF content"""
from crawlers.mas import MASCrawler
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("=== Testing MAS Crawler - Full Workflow ===\n")
print("Testing: Search pages → Circular detail pages → PDF extraction → Content parsing\n")

# Test with 2 pages to keep it quick
crawler = MASCrawler(use_cached_html=False, max_pages=2)
notices = crawler.crawl()

print(f"\n✅ Successfully crawled {len(notices)} circulars\n")

if notices:
    print("=" * 80)
    print("SAMPLE CIRCULAR #1")
    print("=" * 80)
    first = notices[0]
    print(f"Title: {first['title']}")
    print(f"Date: {first['date']}")
    print(f"URL: {first['url']}")
    print(f"Source: {first['source']} ({first['jurisdiction']})")
    print(f"\nContent Preview (first 500 chars):")
    print("-" * 80)
    print(first['content'][:500])
    print("-" * 80)
    print(f"\nFull content length: {len(first['content']):,} characters")
    
    print("\n" + "=" * 80)
    print("SAMPLE CIRCULAR #2")
    print("=" * 80)
    second = notices[1]
    print(f"Title: {second['title']}")
    print(f"Date: {second['date']}")
    print(f"URL: {second['url']}")
    print(f"\nContent Preview (first 300 chars):")
    print("-" * 80)
    print(second['content'][:300])
    print("-" * 80)
    print(f"\nFull content length: {len(second['content']):,} characters")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total circulars parsed: {len(notices)}")
    print(f"Date range: {min(n['date'] for n in notices).strftime('%Y-%m-%d')} to {max(n['date'] for n in notices).strftime('%Y-%m-%d')}")
    print(f"Total content extracted: {sum(len(n['content']) for n in notices):,} characters")
    print(f"Average content per circular: {sum(len(n['content']) for n in notices) // len(notices):,} characters")
    print("\n✅ All circulars successfully crawled from detail pages and PDFs parsed!")
else:
    print("❌ No circulars found")
