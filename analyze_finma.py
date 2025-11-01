import json

with open('tests/crawlers/output/finma.jsonl', encoding='utf-8') as f:
    lines = f.readlines()

circulars = [json.loads(line) for line in lines]

print("=" * 80)
print("FINMA CRAWLER TEST RESULTS")
print("=" * 80)

print(f"\n✅ Total circulars extracted: {len(circulars)}")
print(f"📊 Average content length: {sum(len(c['content']) for c in circulars) // len(circulars):,} characters")
print(f"📅 Date range: {min(c['date'] for c in circulars)} to {max(c['date'] for c in circulars)}")

print("\n📄 Top 5 circulars by content length:")
for i, c in enumerate(sorted(circulars, key=lambda x: len(x['content']), reverse=True)[:5], 1):
    print(f"  {i}. {c['title'][:70]}...")
    print(f"     Length: {len(c['content']):,} chars | Date: {c['date']} | URL: {c['url'][:80]}...")

print("\n📋 Sample of extracted circular content (first 500 chars):")
sample = circulars[8]  # A good regulatory circular
print(f"Title: {sample['title'][:80]}")
print(f"Date: {sample['date']}")
print(f"Content preview:\n{sample['content'][:500]}...")

print("\n✅ All circulars have:")
print(f"  - Title: {all('title' in c for c in circulars)}")
print(f"  - URL: {all('url' in c for c in circulars)}")
print(f"  - Date: {all('date' in c for c in circulars)}")
print(f"  - Content: {all('content' in c for c in circulars)}")
print(f"  - Source = FINMA: {all(c['source'] == 'FINMA' for c in circulars)}")
print(f"  - Jurisdiction = CH: {all(c['jurisdiction'] == 'CH' for c in circulars)}")
print(f"  - Non-empty content: {all(len(c['content']) > 50 for c in circulars)}")

print("=" * 80)
