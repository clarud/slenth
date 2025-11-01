from crawlers.finma import FINMACrawler

print("Extracting FINMA circulars...")
crawler = FINMACrawler(use_cached_html=True)
circulars = crawler.crawl()

# Show the Nature-related financial risks circular (a substantial one)
circ = circulars[8]

print("=" * 80)
print("COMPLETE FINMA CIRCULAR EXTRACTION EXAMPLE")
print("=" * 80)

print(f"\n📄 Title: {circ['title']}")
print(f"\n🔗 URL: {circ['url']}")
print(f"\n📅 Date: {circ['date']}")
print(f"\n🏛️  Source: {circ['source']}")
print(f"🌍 Jurisdiction: {circ['jurisdiction']}")
print(f"📋 Rule Type: {circ['rule_type']}")
print(f"\n📊 Content Length: {len(circ['content']):,} characters")

print(f"\n{'=' * 80}")
print("FULL PDF CONTENT (ALL PAGES EXTRACTED):")
print("=" * 80)
print()
print(circ['content'])
print()
print("=" * 80)
print(f"✅ Successfully extracted {len(circ['content']):,} characters from PDF")
print("=" * 80)
