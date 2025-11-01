"""
Test script to ingest a single PDF into PostgreSQL + Pinecone

This script:
1. Manually specifies 1 PDF URL
2. Downloads and extracts content
3. Chunks the text
4. Upserts to Pinecone (with auto-embedding)
5. Saves to PostgreSQL

Usage: python test_single_pdf_ingest.py
"""

import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import logging
import requests
import PyPDF2
import io

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pinecone import Pinecone
from db.database import SessionLocal
from db.models import ExternalRule
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_pdf(url: str) -> str:
    """Download PDF and extract text"""
    logger.info(f"📥 Downloading PDF from: {url}")
    
    response = requests.get(url, timeout=30, verify=False)
    response.raise_for_status()
    
    # Extract text using PyPDF2
    pdf_file = io.BytesIO(response.content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    
    logger.info(f"✅ Extracted {len(text)} chars, {len(text.split())} words")
    return text.strip()


def chunk_text(text: str, max_words: int = 2000, overlap_words: int = 200):
    """Split text into overlapping chunks"""
    words = text.split()
    
    if len(words) <= max_words:
        return [text]
    
    chunks = []
    start_idx = 0
    
    while start_idx < len(words):
        end_idx = start_idx + max_words
        chunk_words = words[start_idx:end_idx]
        chunks.append(" ".join(chunk_words))
        
        start_idx += (max_words - overlap_words)
        
        if end_idx >= len(words):
            break
    
    return chunks


def prepare_text_for_embedding(regulator: str, jurisdiction: str, title: str, content: str, chunk_idx=None):
    """Format text with context for embedding"""
    prefix_parts = [f"{regulator} {jurisdiction} - {title}"]
    if chunk_idx is not None:
        prefix_parts.append(f"[Chunk {chunk_idx}]")
    
    prefix = " ".join(prefix_parts) + ": "
    return prefix + content


def main():
    """Test ingestion with 1 PDF"""
    
    # TEST DATA - Using fake content to test Pinecone ingestion
    TEST_PDF_URL = "https://www.hkma.gov.hk/test/sample.pdf"
    TEST_TITLE = "Anti-Money Laundering Guidance for Authorized Institutions"
    TEST_REGULATOR = "HKMA"
    TEST_JURISDICTION = "HK"
    TEST_DATE = datetime(2024, 1, 15)
    
    # Fake content for testing (realistic AML content)
    content = """
    Hong Kong Monetary Authority
    
    Anti-Money Laundering and Counter-Financing of Terrorism Guidance
    
    1. Introduction
    Authorized institutions (AIs) are required to comply with the Anti-Money Laundering and Counter-Terrorist Financing Ordinance (AMLO). This circular provides guidance on implementing effective AML/CFT controls.
    
    2. Customer Due Diligence
    AIs must conduct customer due diligence (CDD) measures when:
    - Establishing a business relationship
    - Carrying out occasional transactions above the threshold
    - There is a suspicion of money laundering or terrorist financing
    - There are doubts about the veracity of previously obtained customer identification data
    
    3. Risk Assessment
    AIs should adopt a risk-based approach to AML/CFT. This includes:
    - Identifying and assessing money laundering and terrorist financing risks
    - Designing and implementing controls to manage and mitigate assessed risks
    - Monitoring the effectiveness of controls and enhancing them if necessary
    
    4. Enhanced Due Diligence
    Enhanced due diligence measures should be applied for higher-risk customers including:
    - Politically exposed persons (PEPs)
    - Customers from high-risk jurisdictions
    - Complex corporate structures
    - Non-face-to-face business relationships
    
    5. Transaction Monitoring
    AIs must establish systems and controls to:
    - Monitor ongoing transactions and activities
    - Identify unusual or suspicious transactions
    - Report suspicious transactions to the Joint Financial Intelligence Unit (JFIU)
    
    6. Record Keeping
    Records must be maintained for at least 5 years including:
    - Customer identification records
    - Transaction records
    - Records of analysis and investigations
    
    7. Staff Training
    All relevant staff should receive regular AML/CFT training covering:
    - Legal and regulatory requirements
    - Internal policies and procedures
    - Detection and reporting of suspicious activities
    - New typologies and emerging risks
    
    8. Compliance and Audit
    AIs should have:
    - Independent audit function to test AML/CFT systems
    - Regular compliance reviews
    - Senior management oversight
    
    This guidance is effective immediately and supersedes all previous circulars on this topic.
    """ * 50  # Repeat to make it longer for chunking test
    
    logger.info("="*80)
    logger.info("🧪 TEST: Single PDF Ingestion")
    logger.info("="*80)
    logger.info(f"📄 Title: {TEST_TITLE}")
    logger.info(f"🔗 URL: {TEST_PDF_URL}")
    logger.info(f"📝 Using test content ({len(content)} chars, {len(content.split())} words)")
    logger.info("")
    
    try:
        
        if len(content) < 100:
            logger.error("❌ PDF content too short, aborting")
            return
        
        # Step 2: Chunk content
        chunks = chunk_text(content)
        logger.info(f"📑 Split into {len(chunks)} chunks")
        
        # Step 3: Initialize Pinecone
        logger.info("🔧 Connecting to Pinecone...")
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(host=settings.pinecone_external_index_host)
        logger.info(f"✅ Connected to Pinecone index")
        
        # Step 4: Initialize database
        db = SessionLocal()
        logger.info("✅ Connected to PostgreSQL")
        
        # Step 5: Check for duplicates
        existing = db.query(ExternalRule).filter(
            ExternalRule.source_url == TEST_PDF_URL
        ).first()
        
        if existing:
            logger.warning(f"⚠️  Document already exists in database (ID: {existing.id})")
            logger.info("Deleting existing record for clean test...")
            db.delete(existing)
            db.commit()
        
        # Step 6: Process each chunk
        records_batch = []
        saved_count = 0
        
        import hashlib
        rule_id_base = f"{TEST_REGULATOR}-{hashlib.md5(TEST_TITLE.encode()).hexdigest()[:12]}"
        
        for chunk_idx, chunk_content in enumerate(chunks):
            # Generate IDs
            vector_id = str(uuid4())
            chunk_rule_id = f"{rule_id_base}-{chunk_idx}" if len(chunks) > 1 else rule_id_base
            
            # Prepare text for embedding
            text_for_embedding = prepare_text_for_embedding(
                TEST_REGULATOR, TEST_JURISDICTION, TEST_TITLE, 
                chunk_content, chunk_idx if len(chunks) > 1 else None
            )
            
            logger.info(f"📝 Processing chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk_content.split())} words)")
            
            # Save to PostgreSQL
            db_rule = ExternalRule(
                rule_id=chunk_rule_id,
                regulator=TEST_REGULATOR,
                jurisdiction=TEST_JURISDICTION,
                rule_title=TEST_TITLE,
                rule_text=chunk_content,
                source_url=TEST_PDF_URL,
                document_title=TEST_TITLE,
                section_path="",
                published_date=TEST_DATE,
                effective_date=TEST_DATE,
                vector_id=vector_id,
                chunk_index=chunk_idx if len(chunks) > 1 else None,
                metadata={
                    "crawled_at": datetime.utcnow().isoformat(),
                    "rule_type": "guidance",
                    "total_chunks": len(chunks),
                    "word_count": len(chunk_content.split()),
                },
                scraped_at=datetime.utcnow(),
            )
            
            db.add(db_rule)
            db.flush()
            
            # Prepare Pinecone record
            record = {
                "_id": vector_id,
                "text": text_for_embedding,
                "rule_id": chunk_rule_id,
                "regulator": TEST_REGULATOR,
                "jurisdiction": TEST_JURISDICTION,
                "title": TEST_TITLE[:500],
                "passage_text": chunk_content[:512],
                "url": TEST_PDF_URL[:500],
                "chunk_index": chunk_idx if len(chunks) > 1 else 0,
                "total_chunks": len(chunks),
                "published_date": TEST_DATE.isoformat(),
                "rule_type": "guidance",
                "word_count": len(chunk_content.split()),
                "is_active": True,
                "ingestion_date": datetime.utcnow().isoformat(),
            }
            
            records_batch.append(record)
        
        # Step 7: Batch upsert to Pinecone
        logger.info(f"🚀 Upserting {len(records_batch)} records to Pinecone...")
        index.upsert_records(namespace="__default__", records=records_batch)
        logger.info(f"✅ Pinecone upsert successful (embeddings auto-generated)")
        
        # Step 8: Commit to PostgreSQL
        db.commit()
        saved_count = len(records_batch)
        logger.info(f"✅ Saved {saved_count} chunks to PostgreSQL")
        
        # Final summary
        logger.info("")
        logger.info("="*80)
        logger.info("📊 INGESTION SUMMARY")
        logger.info("="*80)
        logger.info(f"✅ Successfully ingested {saved_count} chunks")
        logger.info(f"📄 Document: {TEST_TITLE}")
        logger.info(f"💾 Storage: PostgreSQL ✓  |  Pinecone ✓")
        logger.info(f"🔢 Total chunks: {len(chunks)}")
        logger.info(f"📝 Total words: {len(content.split())}")
        logger.info("="*80)
        logger.info("🎉 Test completed successfully!")
        logger.info("="*80)
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        if 'db' in locals():
            db.rollback()
            db.close()


if __name__ == "__main__":
    main()
