"""
Ingest FINMA PDFs from Local Directory

This script parses FINMA PDF files from a local directory and ingests them into:
1. PostgreSQL database (external_rules table)
2. Pinecone vector database (external index)

Following the same pattern as external_rules_ingestion.py:
- Chunk large documents (>2000 words)
- Prepare text with context prefix
- Use Pinecone's built-in inference API (auto-generates embeddings)
- Batch upsert to Pinecone + PostgreSQL

Usage:
    python ingest_finma_pdfs.py
"""

import sys
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from uuid import uuid4
import io

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pinecone import Pinecone
from PyPDF2 import PdfReader

from db.database import SessionLocal
from db.models import ExternalRule
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chunking configuration (same as external_rules_ingestion)
MAX_CHUNK_SIZE = 2000  # words per chunk
CHUNK_OVERLAP = 200  # words overlap between chunks

# FINMA PDFs directory
FINMA_PDF_DIR = Path(r"c:\Users\clare\OneDrive\Desktop\finma")


def chunk_text(text: str, max_words: int = MAX_CHUNK_SIZE, overlap_words: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks based on word count.
    Same as external_rules_ingestion.py
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
    Prepare text for embedding with context (same as external_rules_ingestion).
    Format: "Source Jurisdiction - Title [Chunk X]: Content"
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


def generate_rule_id(regulator: str, title: str, filename: str) -> str:
    """
    Generate unique rule_id from regulator + title + filename hash.
    """
    import hashlib
    
    # Create hash of title + filename for uniqueness
    hash_input = f"{title}{filename}".encode('utf-8')
    hash_hex = hashlib.md5(hash_input).hexdigest()[:12]
    
    # Format: REGULATOR-HASH (e.g., FINMA-3f8a7b2c9d1e)
    return f"{regulator}-{hash_hex}"


def extract_metadata_from_filename(filename: str) -> Dict:
    """
    Extract metadata from FINMA PDF filename.
    Examples:
      - finma rs 2026 01.pdf -> year=2026, number=01
      - finma rs 2025 04 20250305.pdf -> year=2025, number=04, date=20250305
      - finma rs 2016 03 20240626_de.pdf -> year=2016, number=03, date=20240626, lang=de
    
    Returns:
        Dict with year, number, date, language
    """
    metadata = {
        "year": None,
        "number": None,
        "date": None,
        "language": "en",  # default to English
    }
    
    # Pattern: finma rs YYYY NN [YYYYMMDD] [_lang].pdf
    match = re.search(r'finma\s+rs\s+(\d{4})\s+(\d{2})', filename, re.IGNORECASE)
    if match:
        metadata["year"] = int(match.group(1))
        metadata["number"] = match.group(2)
    
    # Extract date if present (8 digits: YYYYMMDD)
    date_match = re.search(r'(\d{8})', filename)
    if date_match:
        date_str = date_match.group(1)
        try:
            metadata["date"] = datetime.strptime(date_str, "%Y%m%d")
        except:
            pass
    
    # Extract language code
    lang_match = re.search(r'_(de|fr|it|en)\.pdf$', filename, re.IGNORECASE)
    if lang_match:
        metadata["language"] = lang_match.group(1).lower()
    
    return metadata


def parse_pdf(pdf_path: Path) -> Dict:
    """
    Parse a FINMA PDF and extract text and metadata.
    
    Returns:
        Dict with title, content, metadata
    """
    logger.info(f"Parsing PDF: {pdf_path.name}")
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            
            # Extract metadata
            file_metadata = extract_metadata_from_filename(pdf_path.name)
            
            # Get title from PDF metadata or filename
            title = ""
            if reader.metadata and reader.metadata.get('/Title'):
                title = reader.metadata.get('/Title')
            
            if not title or len(title) < 5:
                # Generate title from filename and metadata
                if file_metadata["year"] and file_metadata["number"]:
                    title = f"FINMA Circular {file_metadata['year']}/{file_metadata['number']}"
                else:
                    title = pdf_path.stem.replace('_', ' ').title()
            
            # Extract text from all pages
            text_parts = []
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num} from {pdf_path.name}: {e}")
                    continue
            
            content = "\n\n".join(text_parts)
            
            # Build the rule dictionary
            rule = {
                "title": title,
                "content": content,
                "source": "FINMA",
                "jurisdiction": "CH",
                "rule_type": "circular",
                "filename": pdf_path.name,
                "url": f"file://{pdf_path}",  # Use file path as URL
                "date": file_metadata.get("date"),
                "metadata": {
                    "year": file_metadata.get("year"),
                    "number": file_metadata.get("number"),
                    "language": file_metadata.get("language"),
                    "pages": len(reader.pages),
                    "word_count": len(content.split()),
                    "parsed_at": datetime.utcnow().isoformat(),
                }
            }
            
            logger.info(f"✅ Parsed: {title[:60]} ({len(content.split())} words, {len(reader.pages)} pages)")
            return rule
            
    except Exception as e:
        logger.error(f"❌ Failed to parse {pdf_path.name}: {e}")
        raise


def ingest_rules_to_db(rules: List[Dict], db_session, regulator: str = "FINMA", jurisdiction: str = "CH") -> int:
    """
    Ingest FINMA rules to PostgreSQL + Pinecone vector database.
    Uses Pinecone's built-in inference API (no OpenAI needed).
    
    Same pattern as save_rules_to_db in external_rules_ingestion.py:
    1. Check for duplicates (by filename/URL)
    2. Chunk large documents
    3. Prepare text with context prefix
    4. Batch upsert to Pinecone (Pinecone generates embeddings)
    5. Store in PostgreSQL
    
    Returns:
        Number of rules saved
    """
    # Initialize Pinecone client
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index(host=settings.pinecone_external_index_host)
    namespace = "__default__"
    
    saved_count = 0
    records_batch = []
    
    for rule in rules:
        try:
            # Validate content
            content = rule.get("content", "").strip()
            if not content or len(content) < 100:
                logger.warning(f"Skipping rule with insufficient content: {rule.get('title', 'Unknown')[:50]}")
                continue
            
            title = rule.get("title", "")
            url = rule.get("url", "")
            filename = rule.get("filename", "")
            
            # Check for duplicates by URL/filename
            existing = db_session.query(ExternalRule).filter(
                ExternalRule.source_url == url
            ).first()
            
            if existing:
                logger.info(f"⏭️  Rule already exists (URL match): {title[:50]}")
                continue
            
            # Generate rule_id
            rule_id = generate_rule_id(regulator, title, filename)
            
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
                        effective_date=rule.get("date"),
                        vector_id=vector_id,
                        chunk_index=chunk_idx if len(chunks) > 1 else None,
                        meta={
                            "crawled_at": datetime.utcnow().isoformat(),
                            "rule_type": rule.get("rule_type", "circular"),
                            "total_chunks": len(chunks),
                            "word_count": len(chunk_content.split()),
                            "full_word_count": len(content.split()),
                            "filename": filename,
                            **rule.get("metadata", {}),
                        },
                        scraped_at=datetime.utcnow(),
                    )
                    
                    db_session.add(db_rule)
                    db_session.flush()  # Get the ID without committing
                    
                    # Prepare Pinecone record (flat structure for inference API)
                    record = {
                        "_id": vector_id,
                        "text": text_for_embedding,  # Full text with context for embedding
                        # Metadata fields at top level
                        "rule_id": chunk_rule_id,
                        "regulator": regulator,
                        "jurisdiction": jurisdiction,
                        "title": title[:500],
                        "passage_text": chunk_content[:512],
                        "url": url[:500],
                        "chunk_index": chunk_idx if len(chunks) > 1 else 0,
                        "total_chunks": len(chunks),
                        "published_date": rule.get("date").isoformat() if rule.get("date") else None,
                        "rule_type": rule.get("rule_type", "circular"),
                        "word_count": len(chunk_content.split()),
                        "is_active": True,
                        "ingestion_date": datetime.utcnow().isoformat(),
                        "filename": filename,
                    }
                    
                    # Add to batch
                    records_batch.append(record)
                    
                    # Batch upsert every 96 records
                    if len(records_batch) >= 96:
                        try:
                            index.upsert_records(namespace=namespace, records=records_batch)
                            db_session.commit()
                            saved_count += len(records_batch)
                            logger.info(f"✅ Upserted batch of {len(records_batch)} records to Pinecone")
                        except Exception as batch_err:
                            logger.warning(f"⚠️ Batch upsert failed, trying per-record: {batch_err}")
                            for rec in records_batch:
                                try:
                                    index.upsert_records(namespace=namespace, records=[rec])
                                    db_session.commit()
                                    saved_count += 1
                                except Exception as rec_err:
                                    logger.error(f"❌ Failed to upsert record {rec.get('_id')}: {rec_err}")
                                    db_session.rollback()
                        
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
            index.upsert_records(namespace=namespace, records=records_batch)
            db_session.commit()
            saved_count += len(records_batch)
            logger.info(f"✅ Upserted final batch of {len(records_batch)} records to Pinecone")
        except Exception as batch_err:
            logger.warning(f"⚠️ Final batch upsert failed, trying per-record: {batch_err}")
            for rec in records_batch:
                try:
                    index.upsert_records(namespace=namespace, records=[rec])
                    db_session.commit()
                    saved_count += 1
                except Exception as rec_err:
                    logger.error(f"❌ Failed to upsert record {rec.get('_id')}: {rec_err}")
                    db_session.rollback()
    
    logger.info(f"💾 Saved {saved_count} rule chunks to PostgreSQL + Pinecone")
    return saved_count


def main():
    """Main entry point - parse FINMA PDFs and ingest to database"""
    logger.info("="*80)
    logger.info("🚀 FINMA PDF INGESTION - START")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    logger.info(f"PDF Directory: {FINMA_PDF_DIR}")
    logger.info("="*80)
    
    # Check directory exists
    if not FINMA_PDF_DIR.exists():
        logger.error(f"❌ Directory not found: {FINMA_PDF_DIR}")
        return
    
    # Find all PDF files
    pdf_files = list(FINMA_PDF_DIR.glob("*.pdf"))
    logger.info(f"\n📁 Found {len(pdf_files)} PDF files in directory")
    
    if not pdf_files:
        logger.warning("⚠️  No PDF files found")
        return
    
    # Parse all PDFs
    rules = []
    for pdf_file in pdf_files:
        try:
            rule = parse_pdf(pdf_file)
            rules.append(rule)
        except Exception as e:
            logger.error(f"❌ Failed to parse {pdf_file.name}: {e}")
            continue
    
    logger.info(f"\n✅ Successfully parsed {len(rules)} PDFs")
    
    if not rules:
        logger.warning("⚠️  No rules extracted from PDFs")
        return
    
    # Ingest to database
    logger.info("\n" + "="*80)
    logger.info("💾 INGESTING TO POSTGRESQL + PINECONE")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        saved_count = ingest_rules_to_db(rules, db, regulator="FINMA", jurisdiction="CH")
        
        # Final summary
        logger.info("\n" + "="*80)
        logger.info("📊 INGESTION SUMMARY")
        logger.info("="*80)
        logger.info(f"📄 PDFs processed: {len(rules)}")
        logger.info(f"✅ Rule chunks saved: {saved_count}")
        logger.info(f"💾 Saved to: PostgreSQL (external_rules table) + Pinecone (external index)")
        logger.info(f"⏰ Completed at: {datetime.utcnow().isoformat()}")
        logger.info("="*80)
        logger.info("🎉 FINMA PDF ingestion complete!")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"❌ Critical error in ingestion: {str(e)}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
