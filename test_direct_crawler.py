from crawlers.finma import FINMACrawler

print("Testing FINMA crawler directly...")
crawler = FINMACrawler(use_cached_html=True)
circulars = crawler.crawl()

print(f"\nExtracted {len(circulars)} circulars\n")
print("Content length check:")
for i, circ in enumerate(circulars[:10], 1):
    print(f"{i:2}. {len(circ['content']):6,} chars - {circ['title'][:70]}")

# Check the first full circular
print(f"\n{'='*80}")
print("FIRST CIRCULAR FULL CONTENT:")
print(f"{'='*80}")
print(f"Title: {circulars[0]['title']}")
print(f"URL: {circulars[0]['url']}")
print(f"Content length: {len(circulars[0]['content']):,} characters")
print(f"\nFull content:\n{circulars[0]['content']}")
