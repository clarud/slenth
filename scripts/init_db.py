#!/usr/bin/env python3
"""
Initialize PostgreSQL database schema.
Creates all tables defined in SQLAlchemy models.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text
import argparse

from db.database import engine, Base, init_db
from db import models
from config import settings


def create_schema(reset: bool = False):
    """
    Create database schema.
    
    Args:
        reset: If True, drop all tables before creating
    """
    try:
        logger.info("🔄 Connecting to cloud PostgreSQL database...")
        logger.info(f"Database: {settings.database_url.host}")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✅ Connected to PostgreSQL: {version}")
        
        if reset:
            logger.warning("⚠️  RESET flag detected - dropping all tables...")
            Base.metadata.drop_all(bind=engine)
            logger.info("✅ All tables dropped")
        
        # Create tables
        logger.info("🔨 Creating database tables...")
        init_db()
        
        # List created tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
        
        logger.info(f"✅ Database initialized with {len(tables)} tables:")
        for table in tables:
            logger.info(f"   - {table}")
        
        logger.info("🎉 Database initialization complete!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        logger.exception(e)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Initialize PostgreSQL database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables before creating (WARNING: deletes all data)"
    )
    args = parser.parse_args()
    
    if args.reset:
        confirmation = input("⚠️  This will DELETE ALL DATA. Type 'yes' to confirm: ")
        if confirmation.lower() != "yes":
            logger.info("Aborted.")
            return
    
    success = create_schema(reset=args.reset)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
