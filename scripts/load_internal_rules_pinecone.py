#!/usr/bin/env python3
"""
Load mock internal rules from internal_rules/ directory into Pinecone vector database.

This script:
1. Reads JSON files from internal_rules/ directory
2. Generates embeddings for each rule
3. Stores vectors with metadata in Pinecone for similarity search
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from config import settings
from services.embeddings import EmbeddingService
from services.pinecone_db import PineconeService


def load_internal_rules():
    """Load internal rules from JSON files to Pinecone."""
    try:
        # Get internal_rules directory
        rules_dir = Path(__file__).parent.parent / "internal_rules"
        
        if not rules_dir.exists():
            logger.error(f"❌ Rules directory not found: {rules_dir}")
            return False
        
        # Get all JSON files
        json_files = list(rules_dir.glob("*.json"))
        logger.info(f"📁 Found {len(json_files)} rule files in {rules_dir}")
        
        if not json_files:
            logger.warning("⚠️  No JSON files found in internal_rules/")
            return False
        
        # Initialize services
        logger.info("🔧 Initializing services...")
        embedding_service = EmbeddingService()
        pinecone_service = PineconeService(index_type="internal")
        
        logger.info(f"📦 Using Pinecone internal index: {settings.pinecone_internal_index_host}")
        
        loaded_count = 0
        
        vectors_to_upsert = []
        metadata_to_upsert = []
        ids_to_upsert = []
        
        for json_file in sorted(json_files):
            logger.info(f"📄 Processing: {json_file.name}")
            
            try:
                # Load JSON - array of passage objects
                with open(json_file, 'r', encoding='utf-8') as f:
                    passages = json.load(f)
                
                if not isinstance(passages, list):
                    logger.warning(f"   ⚠️  Expected array of passages, got {type(passages)}")
                    continue
                
                # Process each passage in the document
                for passage_obj in passages:
                    # Skip empty passages
                    passage_text = passage_obj.get('Passage', '').strip()
                    if not passage_text:
                        continue
                    
                    # Use the UUID from JSON as vector ID
                    passage_id = passage_obj.get('ID')
                    if not passage_id:
                        logger.warning(f"   ⚠️  Passage missing ID: {passage_obj}")
                        continue
                    
                    document_id = passage_obj.get('DocumentID')
                    passage_ref = passage_obj.get('PassageID', '')
                    
                    # Prepare text for embedding with context
                    text_for_embedding = f"Document {document_id} - {passage_ref}: {passage_text}"
                    
                    # Generate embedding
                    embedding = embedding_service.embed_text(text_for_embedding)
                    
                    # Prepare metadata for Pinecone
                    metadata = {
                        "passage_id": passage_id,
                        "document_id": document_id,
                        "passage_ref": passage_ref,
                        "passage_text": passage_text[:1000],  # Truncate for metadata storage
                        "full_text_length": len(passage_text),
                        "source_file": json_file.name,
                        "is_active": True,
                        "jurisdiction": "ADGM",  # Based on the AML Rulebook content
                        "document_type": "aml_rulebook",
                        "ingestion_date": datetime.utcnow().isoformat(),
                    }
                    
                    # Add to batch
                    vectors_to_upsert.append(embedding)
                    metadata_to_upsert.append(metadata)
                    ids_to_upsert.append(passage_id)
                    
                    loaded_count += 1
                
                logger.info(f"   ✅ Prepared {len([p for p in passages if p.get('Passage', '').strip()])} passages from {json_file.name}")
                
            except Exception as e:
                logger.error(f"   ❌ Error loading {json_file.name}: {e}")
                continue
        
        # Upsert all vectors to Pinecone
        if vectors_to_upsert:
            logger.info(f"🚀 Upserting {len(vectors_to_upsert)} vectors to Pinecone...")
            success = pinecone_service.upsert_vectors(
                vectors=vectors_to_upsert,
                metadata_list=metadata_to_upsert,
                ids=ids_to_upsert
            )
            
            if success:
                logger.info(f"💾 Successfully upserted {len(vectors_to_upsert)} rules to Pinecone")
            else:
                logger.error("❌ Failed to upsert vectors to Pinecone")
                return False
        
        # Get index stats
        stats = pinecone_service.get_index_stats()
        
        # Summary
        logger.info("=" * 70)
        logger.info("📊 SUMMARY")
        logger.info("=" * 70)
        logger.info(f"✅ Loaded to Pinecone: {loaded_count} rules")
        logger.info(f"📦 Total in Pinecone index: {stats.get('total_vectors', 'N/A')} vectors")
        logger.info("=" * 70)
        logger.info("🎉 Internal rules loading complete!")
        logger.info("   Pinecone: ✅")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load internal rules: {e}")
        logger.exception(e)
        return False


def main():
    """Main entry point."""
    logger.info("🚀 Loading internal rules to Pinecone vector database...")
    success = load_internal_rules()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
