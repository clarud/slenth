#!/usr/bin/env python3
"""
Load mock internal rules from internal_rules/ directory into PostgreSQL and Qdrant.
"""
import sys
import json
from pathlib import Path
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import InternalRule
from config import settings


def load_internal_rules():
    """Load internal rules from JSON files."""
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
        
        # Create database session
        db: Session = SessionLocal()
        
        try:
            loaded_count = 0
            skipped_count = 0
            
            for json_file in sorted(json_files):
                logger.info(f"📄 Processing: {json_file.name}")
                
                try:
                    # Load JSON
                    with open(json_file, 'r', encoding='utf-8') as f:
                        rule_data = json.load(f)
                    
                    # Generate rule ID if not present
                    rule_id = rule_data.get('rule_id', f"RULE_{json_file.stem}")
                    
                    # Check if rule already exists
                    existing = db.query(InternalRule).filter(
                        InternalRule.rule_id == rule_id
                    ).first()
                    
                    if existing:
                        logger.info(f"   ⏭️  Rule already exists: {rule_id}")
                        skipped_count += 1
                        continue
                    
                    # Create InternalRule instance
                    rule = InternalRule(
                        rule_id=rule_id,
                        rule_text=rule_data.get('text', rule_data.get('rule_text', '')),
                        rule_category=rule_data.get('category', 'general'),
                        rule_priority=rule_data.get('priority', 'medium'),
                        version=rule_data.get('version', 'v1.0'),
                        effective_date=datetime.fromisoformat(
                            rule_data.get('effective_date', datetime.utcnow().isoformat())
                        ),
                        is_active=rule_data.get('is_active', True),
                        source=rule_data.get('source', 'internal_policy_manual'),
                        policy_reference=rule_data.get('policy_reference'),
                        metadata=rule_data.get('metadata', {}),
                        created_by='system',
                        approved_by=rule_data.get('approved_by', 'admin'),
                    )
                    
                    db.add(rule)
                    loaded_count += 1
                    logger.info(f"   ✅ Loaded: {rule_id}")
                    
                except Exception as e:
                    logger.error(f"   ❌ Error loading {json_file.name}: {e}")
                    continue
            
            # Commit all rules
            db.commit()
            logger.info(f"💾 Committed {loaded_count} rules to database")
            
            # Summary
            logger.info("=" * 60)
            logger.info(f"✅ Loaded: {loaded_count} rules")
            logger.info(f"⏭️  Skipped: {skipped_count} rules (already exist)")
            logger.info(f"📊 Total in database: {db.query(InternalRule).count()} rules")
            logger.info("=" * 60)
            
            # Note about vector DB
            logger.info("📝 Note: Rules loaded to PostgreSQL")
            logger.info("   To load embeddings to Qdrant, implement embedding service")
            logger.info("   and call it from services/vector_db.py")
            
            logger.info("🎉 Internal rules loading complete!")
            return True
            
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to load internal rules: {e}")
        logger.exception(e)
        return False


def main():
    """Main entry point."""
    logger.info("🚀 Loading internal rules from JSON files...")
    success = load_internal_rules()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
