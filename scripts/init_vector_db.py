#!/usr/bin/env python3
"""
Initialize Qdrant vector database collections.
Creates collections for external and internal rules with appropriate configuration.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import argparse

from config import settings


def init_qdrant_collections(reset: bool = False):
    """
    Initialize Qdrant collections for rules storage.
    
    Args:
        reset: If True, delete collections before creating
    """
    try:
        logger.info("🔄 Connecting to Qdrant vector database...")
        logger.info(f"Host: {settings.qdrant_host}:{settings.qdrant_port}")
        
        # Create client
        client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
        )
        
        # Test connection
        collections_response = client.get_collections()
        logger.info(f"✅ Connected to Qdrant")
        logger.info(f"Existing collections: {len(collections_response.collections)}")
        
        # Collection names
        collections = [
            settings.qdrant_collection_external_rules,
            settings.qdrant_collection_internal_rules,
        ]
        
        for collection_name in collections:
            # Check if collection exists
            existing_collections = [c.name for c in collections_response.collections]
            collection_exists = collection_name in existing_collections
            
            if collection_exists:
                if reset:
                    logger.warning(f"⚠️  Deleting collection: {collection_name}")
                    client.delete_collection(collection_name=collection_name)
                    collection_exists = False
                else:
                    logger.info(f"✅ Collection already exists: {collection_name}")
                    continue
            
            # Create collection
            logger.info(f"🔨 Creating collection: {collection_name}")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"✅ Collection created: {collection_name}")
        
        # List all collections
        collections_response = client.get_collections()
        logger.info(f"✅ Qdrant initialized with {len(collections_response.collections)} collections:")
        for collection in collections_response.collections:
            info = client.get_collection(collection_name=collection.name)
            logger.info(f"   - {collection.name}: {info.vectors_count} vectors")
        
        logger.info("🎉 Qdrant initialization complete!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Qdrant initialization failed: {e}")
        logger.exception(e)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Initialize Qdrant vector database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete collections before creating (WARNING: deletes all vectors)"
    )
    args = parser.parse_args()
    
    if args.reset:
        confirmation = input("⚠️  This will DELETE ALL VECTORS. Type 'yes' to confirm: ")
        if confirmation.lower() != "yes":
            logger.info("Aborted.")
            return
    
    success = init_qdrant_collections(reset=args.reset)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
