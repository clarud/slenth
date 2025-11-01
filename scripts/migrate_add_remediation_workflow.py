"""
Database migration script to add remediation_workflow column to alerts table.

This script checks if the column exists and adds it if necessary.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from db.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_column_exists():
    """Check if remediation_workflow column exists in alerts table."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='alerts' AND column_name='remediation_workflow'
        """))
        return result.fetchone() is not None


def add_remediation_workflow_column():
    """Add remediation_workflow column to alerts table."""
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE alerts 
            ADD COLUMN IF NOT EXISTS remediation_workflow TEXT
        """))
        conn.commit()
        logger.info("✅ Added remediation_workflow column to alerts table")


def main():
    """Main migration function."""
    logger.info("Starting database migration...")
    
    try:
        if check_column_exists():
            logger.info("✅ remediation_workflow column already exists. No migration needed.")
        else:
            logger.info("📝 Adding remediation_workflow column to alerts table...")
            add_remediation_workflow_column()
            logger.info("✅ Migration complete!")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
