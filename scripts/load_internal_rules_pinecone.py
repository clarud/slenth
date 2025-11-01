#!/usr/bin/env python3
"""
Load mock internal rules from internal_rules/ directory into Pinecone vector database.

This script:
1. Reads JSON files from internal_rules/ directory
2. Uses Pinecone's built-in inference API to generate embeddings
3. Stores vectors with metadata in Pinecone for similarity search

Note: Uses Pinecone's inference API (no OpenAI needed)

Required Environment Variables:
- PINECONE_API_KEY: Your Pinecone API key
- PINECONE_INTERNAL_INDEX_HOST: Host URL for internal rules index
"""
import sys
import json
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from pinecone import Pinecone
from dotenv import load_dotenv

# Add project root to path for db imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    logger_init = logging.getLogger(__name__)
    logger_init.info(f"Loaded environment variables from {env_path}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_internal_rules():
    """Load internal rules from JSON files to Pinecone."""
    try:
        # Get environment variables
        api_key = os.getenv("PINECONE_API_KEY")
        index_host = os.getenv("PINECONE_INTERNAL_INDEX_HOST")
        
        if not api_key:
            logger.error("❌ PINECONE_API_KEY environment variable not set")
            return False
        
        if not index_host:
            logger.error("❌ PINECONE_INTERNAL_INDEX_HOST environment variable not set")
            return False
        
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
        
        # Initialize Pinecone
        logger.info("🔧 Initializing Pinecone service...")
        pc = Pinecone(api_key=api_key)
        index = pc.Index(host=index_host)
        
        logger.info(f"📦 Using Pinecone internal index: {index_host}")
        logger.info("📝 Using Pinecone's built-in embedding model (no OpenAI required)")
        
        # For Pinecone API 2025-04+, don't specify namespace for default namespace
        # Specifying "__default__" causes data to go to "" but we can't query ""
        # Not specifying namespace at all ensures data can be queried properly
        namespace = None  # Don't specify namespace - let Pinecone handle it
        loaded_count = 0
        
        # Collect records for batch upsert
        records_to_upsert = []
        
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
                    
                    # Create record with text and metadata at top level
                    # (Pinecone inference API expects flat structure)
                    record = {
                        "_id": passage_id,
                        "text": text_for_embedding,
                        # Metadata fields at top level
                        "passage_id": passage_id,
                        "document_id": int(document_id) if document_id is not None else None,
                        "passage_ref": passage_ref,
                        "passage_text": passage_text[:512],  # Truncate for metadata storage
                        "full_text_length": len(passage_text),
                        "source_file": json_file.name,
                        "is_active": True,
                        "jurisdiction": "ADGM",  # Based on the AML Rulebook content
                        "document_type": "aml_rulebook",
                        "ingestion_date": datetime.now(timezone.utc).isoformat(),
                    }
                    
                    records_to_upsert.append(record)
                    loaded_count += 1
                
                logger.info(f"   ✅ Prepared {len([p for p in passages if p.get('Passage', '').strip()])} passages from {json_file.name}")
                
            except Exception as e:
                logger.error(f"   ❌ Error loading {json_file.name}: {e}")
                continue
        
        # Upsert all records to Pinecone
        if records_to_upsert:
            logger.info(f"🚀 Upserting {len(records_to_upsert)} records to Pinecone...")
            logger.info("   Pinecone will generate embeddings using its inference API")
            
            def _safe_id(rec: dict) -> str:
                try:
                    return str(rec.get("_id", rec.get("passage_id", "<no-id>")))
                except Exception:
                    return "<invalid-id>"

            # Upsert with batch fallback and per-record retry for problematic items
            try:
                batch_size = 96
                total_batches = (len(records_to_upsert) - 1) // batch_size + 1
                for i in range(0, len(records_to_upsert), batch_size):
                    batch = records_to_upsert[i:i + batch_size]
                    try:
                        # Don't specify namespace to avoid API 2025-04 issues
                        # Specifying "__default__" causes data to be stored in "" which can't be queried
                        if namespace:
                            index.upsert_records(namespace=namespace, records=batch)
                        else:
                            index.upsert_records(records=batch)
                        logger.info(f"   ✅ Upserted batch {i//batch_size + 1}/{total_batches}")
                    except Exception as be:
                        # Batch failed — try single-record upserts to isolate/skips bad records
                        logger.warning(f"   ⚠️ Batch upsert failed (batch {i//batch_size + 1}), attempting per-record upsert: {be}")
                        for rec in batch:
                            try:
                                if namespace:
                                    index.upsert_records(namespace=namespace, records=[rec])
                                else:
                                    index.upsert_records(records=[rec])
                                logger.info(f"      ✅ Upserted record {_safe_id(rec)}")
                            except Exception as sre:
                                rec_id = _safe_id(rec)
                                logger.error(f"      ❌ Skipping record {rec_id} due to upsert error: {sre}")
                                # write failed rec id to a file for inspection
                                try:
                                    failed_log = Path(__file__).parent.parent / "failed_upserts.log"
                                    with open(failed_log, "a", encoding="utf-8") as fh:
                                        fh.write(f"{datetime.now(timezone.utc).isoformat()} - {rec_id} - {sre}\n")
                                except Exception as fh_err:
                                    logger.error(f"         ⚠️ Could not write failed record to log: {fh_err}")
                logger.info(f"💾 Successfully attempted upsert for {len(records_to_upsert)} rules to Pinecone (some records may have been skipped)")
            except Exception as e:
                logger.error(f"❌ Failed to upsert records to Pinecone: {e}")
                return False
        
        # Get index stats
        try:
            stats = index.describe_index_stats()
            total_vectors = stats.get('total_vector_count', 0)
        except Exception as e:
            logger.warning(f"⚠️  Could not get index stats: {e}")
            total_vectors = "N/A"
        
        # Summary
        logger.info("=" * 70)
        logger.info("📊 SUMMARY")
        logger.info("=" * 70)
        logger.info(f"✅ Loaded to Pinecone: {loaded_count} rules")
        logger.info(f"📦 Total in Pinecone index: {total_vectors} vectors")
        logger.info("=" * 70)
        logger.info("🎉 Internal rules loading complete!")
        logger.info("   Pinecone: ✅")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load internal rules: {e}")
        logger.exception(e)
        return False


def load_internal_rules_to_postgres():
    """Load internal rules from JSON files to PostgreSQL database."""
    try:
        from db.database import SessionLocal
        from db.models import InternalRule
        from sqlalchemy.exc import IntegrityError
        
        # Get database URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("❌ DATABASE_URL environment variable not set")
            return False
        
        logger.info(f"✅ Using database: {database_url.split('@')[-1]}")  # Hide credentials
        
        # Initialize database session
        db = SessionLocal()
        
        # Get internal_rules directory
        rules_dir = Path(__file__).parent.parent / "internal_rules"
        if not rules_dir.exists():
            logger.error(f"❌ Internal rules directory not found: {rules_dir}")
            return False
        
        # Get all JSON files
        json_files = sorted(rules_dir.glob("*.json"))
        if not json_files:
            logger.error(f"❌ No JSON files found in {rules_dir}")
            return False
        
        logger.info(f"📂 Found {len(json_files)} JSON files")
        logger.info("=" * 70)
        
        # Track statistics
        total_rules = 0
        loaded_count = 0
        updated_count = 0
        skipped_count = 0
        
        # Process each JSON file
        for json_file in json_files:
            logger.info(f"📄 Processing: {json_file.name}")
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                
                if not isinstance(rules, list):
                    logger.warning(f"⚠️  {json_file.name} does not contain a list, skipping")
                    continue
                
                file_rule_count = 0
                for rule_data in rules:
                    total_rules += 1
                    
                    # Skip empty passages
                    passage = rule_data.get("Passage", "").strip()
                    if not passage:
                        skipped_count += 1
                        continue
                    
                    rule_id = rule_data.get("ID")
                    passage_id = rule_data.get("PassageID", "")
                    document_id = rule_data.get("DocumentID")
                    
                    if not rule_id:
                        logger.warning(f"⚠️  Rule missing ID, skipping")
                        skipped_count += 1
                        continue
                    
                    # Truncate long fields to fit database constraints
                    source_str = f"ADGM_AML_Rulebook_Doc_{document_id}"
                    if len(source_str) > 100:
                        source_str = source_str[:100]
                    
                    policy_ref = passage_id[:100] if len(passage_id) > 100 else passage_id
                    
                    # Check if rule already exists
                    existing_rule = db.query(InternalRule).filter(
                        InternalRule.rule_id == rule_id
                    ).first()
                    
                    if existing_rule:
                        # Update existing rule
                        existing_rule.rule_text = passage
                        existing_rule.policy_reference = policy_ref
                        existing_rule.source = source_str
                        existing_rule.meta = {
                            "PassageID": passage_id,
                            "DocumentID": document_id,
                            "file": json_file.name
                        }
                        existing_rule.updated_at = datetime.now(timezone.utc)
                        updated_count += 1
                    else:
                        # Create new rule
                        new_rule = InternalRule(
                            rule_id=rule_id,
                            rule_text=passage,
                            rule_category="AML",
                            rule_priority="medium",
                            version="1.0",
                            effective_date=datetime.now(timezone.utc),
                            is_active=True,
                            source=source_str,
                            policy_reference=policy_ref,
                            vector_id=rule_id,  # Same as rule_id for Pinecone reference
                            meta={
                                "PassageID": passage_id,
                                "DocumentID": document_id,
                                "file": json_file.name
                            },
                            created_by="system",
                            approved_by="system"
                        )
                        db.add(new_rule)
                        loaded_count += 1
                    
                    file_rule_count += 1
                    
                    # Commit in batches of 100
                    if file_rule_count % 100 == 0:
                        try:
                            db.commit()
                            logger.info(f"   💾 Committed {file_rule_count} rules from {json_file.name}")
                        except IntegrityError as e:
                            logger.error(f"   ❌ Integrity error: {e}")
                            db.rollback()
                
                # Commit remaining rules
                try:
                    db.commit()
                    logger.info(f"   ✅ Processed {file_rule_count} rules from {json_file.name}")
                except IntegrityError as e:
                    logger.error(f"   ❌ Integrity error on commit: {e}")
                    db.rollback()
                except Exception as e:
                    logger.error(f"   ❌ Error on commit: {e}")
                    db.rollback()
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse {json_file.name}: {e}")
                continue
            except Exception as e:
                logger.error(f"❌ Error processing {json_file.name}: {e}")
                logger.exception(e)
                continue
        
        # Close database session
        db.close()
        
        # Summary
        logger.info("=" * 70)
        logger.info("📊 SUMMARY")
        logger.info("=" * 70)
        logger.info(f"📝 Total rules found: {total_rules}")
        logger.info(f"✅ New rules created: {loaded_count}")
        logger.info(f"🔄 Rules updated: {updated_count}")
        logger.info(f"⏭️  Rules skipped (empty): {skipped_count}")
        logger.info("=" * 70)
        logger.info("🎉 Internal rules loading to PostgreSQL complete!")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load internal rules to PostgreSQL: {e}")
        logger.exception(e)
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load internal rules to Pinecone and/or PostgreSQL"
    )
    parser.add_argument(
        '--target',
        choices=['pinecone', 'postgres', 'both'],
        default='pinecone',
        help='Target database(s) to load rules into (default: pinecone)'
    )
    
    args = parser.parse_args()
    
    success = True
    
    if args.target in ['pinecone', 'both']:
        logger.info("🚀 Loading internal rules to Pinecone vector database...")
        success = load_internal_rules() and success
    
    if args.target in ['postgres', 'both']:
        logger.info("\n🚀 Loading internal rules to PostgreSQL database...")
        success = load_internal_rules_to_postgres() and success
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
