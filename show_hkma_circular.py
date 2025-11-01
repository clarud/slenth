"""
Test HKMA crawler and show one circular's full content
"""
import sys
sys.path.insert(0, 'c:\\Users\\clare\\OneDrive\\Desktop\\slenth')

from crawlers.hkma import HKMACrawler

# Initialize crawler with cached HTML
crawler = HKMACrawler(use_cached_html=True)

# Crawl
circulars = crawler.crawl()

print(f"Found {len(circulars)} circulars\n")

if circulars:
    # Show first circular
    first = circulars[0]
    print(f"Title: {first['title']}")
    print(f"URL: {first['url']}")
    print(f"Date: {first['date']}")
    print(f"Content length: {len(first['content'])} characters")
    print(f"\nFirst 500 characters of content:")
    print(first['content'][:500])
    print(f"\n...\n\nLast 500 characters of content:")
    print(first['content'][-500:])
