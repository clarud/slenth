"""
External Rules Ingestion Cron Job

Scheduled task to run regulatory crawlers and ingest external rules into:
1. PostgreSQL database (external_rules table)
2. Pinecone vector database (external index)

Workflow (similar to internal rules):
1. Crawl regulatory websites (HKMA, MAS, FINMA)
2. Extract PDF content and metadata
3. Chunk large documents (if needed)
4. Pinecone generates embeddings automatically (no OpenAI needed)
5. Store in PostgreSQL + Pinecone with rich metadata

Run daily via cron: 0 2 * * * python cron/external_rules_ingestion.py

Crawlers:
- HKMA (Hong Kong Monetary Authority): AML/CFT guidance papers and circulars
- MAS (Monetary Authority of Singapore): AML/CFT notices and regulations
- FINMA (Swiss Financial Market Supervisory Authority): Circulars
"""

import sys
import logging
import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from uuid import uuid4

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pinecone import Pinecone

from db.database import SessionLocal
from db.models import ExternalRule
from config import settings
from crawlers.hkma import HKMACrawler
from crawlers.mas import MASCrawler
from crawlers.finma import FINMACrawler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chunking configuration (similar to internal rules)
MAX_CHUNK_SIZE = 2000  # words per chunk
CHUNK_OVERLAP = 200  # words overlap between chunks


def chunk_text(text: str, max_words: int = MAX_CHUNK_SIZE, overlap_words: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks based on word count.
    Similar to internal rules processing.
    
    Args:
        text: Text to chunk
        max_words: Maximum words per chunk
        overlap_words: Words to overlap between chunks
        
    Returns:
        List of text chunks
    """
    words = text.split()
    
    if len(words) <= max_words:
        return [text]
    
    chunks = []
    start_idx = 0
    
    while start_idx < len(words):
        end_idx = start_idx + max_words
        chunk_words = words[start_idx:end_idx]
        chunks.append(" ".join(chunk_words))
        
        # Move start index forward, accounting for overlap
        start_idx += (max_words - overlap_words)
        
        # Break if we're at the end
        if end_idx >= len(words):
            break
    
    return chunks


def prepare_text_for_embedding(rule: Dict, chunk_index: Optional[int] = None) -> str:
    """
    Prepare text for embedding with context (similar to internal rules).
    Format: "Source Jurisdiction - Title [Chunk X]: Content"
    
    Args:
        rule: Rule dictionary with metadata
        chunk_index: Optional chunk index
        
    Returns:
        Formatted text string
    """
    source = rule.get("source", "Unknown")
    jurisdiction = rule.get("jurisdiction", "")
    title = rule.get("title", "")
    content = rule.get("content", "")
    
    # Build context prefix
    prefix_parts = [f"{source} {jurisdiction}"]
    if title:
        prefix_parts.append(f"- {title}")
    if chunk_index is not None:
        prefix_parts.append(f"[Chunk {chunk_index}]")
    
    prefix = " ".join(prefix_parts) + ": "
    
    return prefix + content


def generate_rule_id(regulator: str, title: str, url: str) -> str:
    """
    Generate unique rule_id from regulator + title + url hash.
    
    Args:
        regulator: Regulator code (HKMA, MAS, FINMA)
        title: Rule title
        url: Source URL
        
    Returns:
        Unique rule ID
    """
    import hashlib
    
    # Create hash of title + url for uniqueness
    hash_input = f"{title}{url}".encode('utf-8')
    hash_hex = hashlib.md5(hash_input).hexdigest()[:12]
    
    # Format: REGULATOR-HASH (e.g., HKMA-3f8a7b2c9d1e)
    return f"{regulator}-{hash_hex}"


def save_rules_to_db(rules: List[Dict], db_session, regulator: str, jurisdiction: str) -> int:
    """
    Save crawled rules to PostgreSQL + Pinecone vector database.
    Uses Pinecone's built-in inference API (no OpenAI needed).
    
    Follows the same pattern as internal rules ingestion:
    1. Check for duplicates (by URL)
    2. Chunk large documents
    3. Prepare text with context prefix
    4. Store in PostgreSQL + Pinecone (Pinecone generates embeddings)
    
    Args:
        rules: List of rule dictionaries from crawler
        db_session: Database session
        regulator: Regulator code (HKMA, MAS, FINMA)
        jurisdiction: Jurisdiction code (HK, SG, CH)
        
    Returns:
        Number of rules saved
    """
    # Initialize Pinecone client
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index(host=settings.pinecone_external_index_host)
    # Use "__default__" as namespace (same as test script that works)
    namespace = "__default__"
    
    saved_count = 0
    records_batch = []  # Batch for Pinecone upsert_records
    
    for rule in rules:
        try:
            # Validate content
            content = rule.get("content", "").strip()
            if not content or len(content) < 100:
                logger.warning(f"Skipping rule with insufficient content: {rule.get('title', 'Unknown')[:50]}")
                continue
            
            title = rule.get("title", "")
            url = rule.get("url", "")
            
            # Check for duplicates by URL
            existing = db_session.query(ExternalRule).filter(
                ExternalRule.source_url == url
            ).first()
            
            if existing:
                logger.debug(f"Rule already exists (URL match): {title[:50]}")
                continue
            
            # Generate rule_id
            rule_id = generate_rule_id(regulator, title, url)
            
            # Chunk content if needed
            chunks = chunk_text(content)
            logger.info(f"Processing rule: {title[:60]} ({len(chunks)} chunks, {len(content.split())} words)")
            
            # Process each chunk
            for chunk_idx, chunk_content in enumerate(chunks):
                try:
                    # Prepare text with context for embedding
                    text_for_embedding = prepare_text_for_embedding(
                        {**rule, "content": chunk_content},
                        chunk_index=chunk_idx if len(chunks) > 1 else None
                    )
                    
                    # Generate unique ID for this chunk
                    vector_id = str(uuid4())
                    chunk_rule_id = f"{rule_id}-{chunk_idx}" if len(chunks) > 1 else rule_id
                    
                    # Create database record
                    db_rule = ExternalRule(
                        rule_id=chunk_rule_id,
                        regulator=regulator,
                        jurisdiction=jurisdiction,
                        rule_title=title,
                        rule_text=chunk_content,
                        source_url=url,
                        document_title=title,
                        section_path=rule.get("section_path", ""),
                        published_date=rule.get("date"),
                        effective_date=rule.get("effective_date", rule.get("date")),
                        vector_id=vector_id,
                        chunk_index=chunk_idx if len(chunks) > 1 else None,
                        meta={
                            "crawled_at": datetime.utcnow().isoformat(),
                            "rule_type": rule.get("rule_type", "guidance"),
                            "total_chunks": len(chunks),
                            "word_count": len(chunk_content.split()),
                            "full_word_count": len(content.split()),
                        },
                        scraped_at=datetime.utcnow(),
                    )
                    
                    db_session.add(db_rule)
                    db_session.flush()  # Get the ID without committing
                    
                    # Prepare Pinecone record (flat structure for inference API)
                    # Pinecone will generate embeddings from the "text" field
                    record = {
                        "_id": vector_id,
                        "text": text_for_embedding,  # Full text with context for embedding
                        # Metadata fields at top level
                        "rule_id": chunk_rule_id,
                        "regulator": regulator,
                        "jurisdiction": jurisdiction,
                        "title": title[:500],  # Truncate for metadata
                        "passage_text": chunk_content[:512],  # Preview text
                        "url": url[:500],
                        "chunk_index": chunk_idx if len(chunks) > 1 else 0,
                        "total_chunks": len(chunks),
                        "published_date": rule.get("date").isoformat() if rule.get("date") else None,
                        "rule_type": rule.get("rule_type", "guidance"),
                        "word_count": len(chunk_content.split()),
                        "is_active": True,
                        "ingestion_date": datetime.utcnow().isoformat(),
                    }
                    
                    # Add to batch
                    records_batch.append(record)
                    
                    # Batch upsert every 96 records (Pinecone inference API recommended batch size)
                    if len(records_batch) >= 96:
                        try:
                            # Always pass namespace parameter (None or string value)
                            index.upsert_records(namespace=namespace, records=records_batch)
                            db_session.commit()
                            saved_count += len(records_batch)
                            logger.info(f"✅ Upserted batch of {len(records_batch)} records to Pinecone (embeddings auto-generated)")
                        except Exception as batch_err:
                            logger.warning(f"⚠️ Batch upsert failed, trying per-record: {batch_err}")
                            # Try per-record upsert
                            for rec in records_batch:
                                try:
                                    # Always pass namespace parameter
                                    index.upsert_records(namespace=namespace, records=[rec])
                                    saved_count += 1
                                except Exception as rec_err:
                                    logger.error(f"❌ Failed to upsert record {rec.get('_id')}: {rec_err}")
                                    db_session.rollback()
                        
                        # Clear batch
                        records_batch = []
                
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk_idx} of {title[:50]}: {str(e)}")
                    db_session.rollback()
                    continue
        
        except Exception as e:
            rule_title = rule.get('title', 'Unknown')[:50]
            logger.error(f"Error saving rule {rule_title}: {str(e)}")
            db_session.rollback()
            continue
    
    # Upsert remaining records
    if records_batch:
        try:
            # Always pass namespace parameter (None or string value)
            index.upsert_records(namespace=namespace, records=records_batch)
            db_session.commit()
            saved_count += len(records_batch)
            logger.info(f"✅ Upserted final batch of {len(records_batch)} records to Pinecone")
        except Exception as batch_err:
            logger.warning(f"⚠️ Final batch upsert failed, trying per-record: {batch_err}")
            # Try per-record upsert
            for rec in records_batch:
                try:
                    # Always pass namespace parameter
                    index.upsert_records(namespace=namespace, records=[rec])
                    db_session.commit()
                    saved_count += 1
                except Exception as rec_err:
                    logger.error(f"❌ Failed to upsert record {rec.get('_id')}: {rec_err}")
                    db_session.rollback()
    
    logger.info(f"💾 Saved {saved_count} rule chunks to PostgreSQL + Pinecone")
    return saved_count


def run_all_crawlers():
    """
    Run all regulatory crawlers and ingest rules into PostgreSQL + Pinecone.
    
    Workflow (similar to internal rules):
    1. Crawl each regulator's website
    2. Extract PDF content and metadata
    3. Check for duplicates (by URL)
    4. Chunk large documents (>2000 words)
    5. Generate embeddings with context prefix
    6. Batch upsert to Pinecone (50 vectors at a time)
    7. Save to PostgreSQL
    """
    logger.info("="*80)
    logger.info("🚀 EXTERNAL RULES INGESTION JOB - START")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    logger.info("="*80)
    
    db = SessionLocal()
    
    try:
        total_saved = 0
        total_chunks = 0
        
        # HKMA (Hong Kong Monetary Authority)
        logger.info("\n" + "="*80)
        logger.info("[1/3] HKMA - Hong Kong Monetary Authority")
        logger.info("="*80)
        try:
            hkma_crawler = HKMACrawler(use_cached_html=False)
            logger.info(f"Crawling: {hkma_crawler.base_url}")
            
            hkma_circulars = hkma_crawler.crawl()
            logger.info(f"✅ Crawled {len(hkma_circulars)} circulars")
            
            if hkma_circulars:
                hkma_saved = save_rules_to_db(hkma_circulars, db, "HKMA", "HK")
                total_saved += hkma_saved
                logger.info(f"💾 Ingested {hkma_saved} rule chunks to PostgreSQL + Pinecone")
            else:
                logger.warning("⚠️  No new HKMA circulars found")
                
        except Exception as e:
            logger.error(f"❌ HKMA crawler failed: {str(e)}", exc_info=True)
        
        # MAS (Monetary Authority of Singapore)
        logger.info("\n" + "="*80)
        logger.info("[2/3] MAS - Monetary Authority of Singapore")
        logger.info("="*80)
        
        try:
            mas_crawler = MASCrawler(use_cached_html=False)
            logger.info(f"Crawling: {mas_crawler.base_url}")
            
            mas_notices = mas_crawler.crawl()
            logger.info(f"✅ Crawled {len(mas_notices)} notices")
            
            if mas_notices:
                mas_saved = save_rules_to_db(mas_notices, db, "MAS", "SG")
                total_saved += mas_saved
                logger.info(f"💾 Ingested {mas_saved} rule chunks to PostgreSQL + Pinecone")
            else:
                logger.warning("⚠️  No new MAS notices found")
                
        except Exception as e:
            logger.error(f"❌ MAS crawler failed: {str(e)}", exc_info=True)
        
        # FINMA (Swiss Financial Market Supervisory Authority)
        logger.info("\n" + "="*80)
        logger.info("[3/3] FINMA - Swiss Financial Market Supervisory Authority")
        logger.info("="*80)
        
        try:
            finma_crawler = FINMACrawler(use_cached_html=False)
            logger.info(f"Crawling: {finma_crawler.base_url}")
            
            finma_circulars = finma_crawler.crawl()
            logger.info(f"✅ Crawled {len(finma_circulars)} circulars")
            
            if finma_circulars:
                finma_saved = save_rules_to_db(finma_circulars, db, "FINMA", "CH")
                total_saved += finma_saved
                logger.info(f"💾 Ingested {finma_saved} rule chunks to PostgreSQL + Pinecone")
            else:
                logger.warning("⚠️  No new FINMA circulars found")
                
        except Exception as e:
            logger.error(f"❌ FINMA crawler failed: {str(e)}", exc_info=True)
        
        # Final summary
        logger.info("\n" + "="*80)
        logger.info("📊 INGESTION JOB SUMMARY")
        logger.info("="*80)
        logger.info(f"✅ Total rule chunks saved: {total_saved}")
        logger.info(f"💾 Saved to: PostgreSQL (external_rules table) + Pinecone (external index)")
        logger.info(f"⏰ Completed at: {datetime.utcnow().isoformat()}")
        logger.info("="*80)
        logger.info("🎉 External rules ingestion complete!")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"❌ Critical error in ingestion job: {str(e)}", exc_info=True)
    
    finally:
        db.close()


def main():
    """Entry point for cron job"""
    run_all_crawlers()


if __name__ == "__main__":
    main()
