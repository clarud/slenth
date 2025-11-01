"""Test MAS crawler with database ingestion"""
from crawlers.mas import MASCrawler
from db.database import SessionLocal
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("=" * 80)
print("MAS CRAWLER - DATABASE INGESTION TEST")
print("=" * 80)

# Test with 1 page to keep it quick
print("\n1️⃣ Crawling MAS circulars (1 page)...")
crawler = MASCrawler(use_cached_html=False, max_pages=1)
circulars = crawler.crawl()

print(f"\n✅ Crawled {len(circulars)} circulars")
print(f"📊 Total content: {sum(len(c['content']) for c in circulars):,} characters")

# Test database ingestion
print("\n2️⃣ Ingesting to PostgreSQL + Pinecone...")
db = SessionLocal()
try:
    saved_count = crawler.save_to_db(circulars, db)
    print(f"\n✅ Successfully saved {saved_count} chunks to database!")
    
    # Query to verify
    from db.models import ExternalRule
    total_mas = db.query(ExternalRule).filter(
        ExternalRule.regulator == "MAS"
    ).count()
    
    print(f"\n📊 VERIFICATION:")
    print(f"   Total MAS rules in database: {total_mas}")
    print(f"   Newly added: {saved_count}")
    
    # Show sample
    latest = db.query(ExternalRule).filter(
        ExternalRule.regulator == "MAS"
    ).order_by(ExternalRule.scraped_at.desc()).first()
    
    if latest:
        print(f"\n📄 LATEST ENTRY:")
        print(f"   Rule ID: {latest.rule_id}")
        print(f"   Title: {latest.rule_title[:80]}")
        print(f"   Published: {latest.published_date}")
        print(f"   Chunk: {latest.chunk_index}/{latest.meta.get('total_chunks', 1)}")
        print(f"   Words: {latest.meta.get('word_count', 0)}")
        print(f"   Vector ID: {latest.vector_id}")
        print(f"\n   Content preview:")
        print(f"   {latest.rule_text[:300]}...")
    
    print("\n✅ MAS crawler database ingestion test PASSED!")
    
finally:
    db.close()
