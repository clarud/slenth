import json

with open('tests/crawlers/output/finma.jsonl', encoding='utf-8') as f:
    circulars = [json.loads(line) for line in f]

# Check a regulatory circular (index 8)
circ = circulars[8]

print("=" * 80)
print("DETAILED PDF EXTRACTION CHECK")
print("=" * 80)

print(f"\nCircular: {circ['title']}")
print(f"URL: {circ['url']}")
print(f"Date: {circ['date']}")
print(f"\n📄 FULL CONTENT LENGTH: {len(circ['content']):,} characters")

print(f"\n📖 Content preview (first 2000 characters):")
print("-" * 80)
print(circ['content'][:2000])
print("-" * 80)

# Check if it looks like a full PDF extraction
if len(circ['content']) > 5000:
    print("\n✅ GOOD: Content is substantial (>5000 chars) - likely full PDF extracted")
else:
    print("\n⚠️  WARNING: Content seems short - may only be first page")

# Check all circulars
print(f"\n📊 Content length statistics for all {len(circulars)} circulars:")
lengths = [len(c['content']) for c in circulars]
print(f"   Min: {min(lengths):,} chars")
print(f"   Max: {max(lengths):,} chars")
print(f"   Average: {sum(lengths)//len(lengths):,} chars")

# Find the longest one
longest = max(circulars, key=lambda x: len(x['content']))
print(f"\n📄 Longest circular:")
print(f"   Title: {longest['title'][:80]}")
print(f"   Length: {len(longest['content']):,} chars")
print(f"   Preview: {longest['content'][:500]}")
