"""
Direct Pinecone query test using the OLD query API (not Records search API).
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.pinecone_db import PineconeService
from services.embeddings import EmbeddingService

def main():
    print("Testing Pinecone query (not search)...\n")
    
    service = PineconeService(index_type="internal")
    
    # Generate embedding for test query
    embedding_service = EmbeddingService()
    query_embedding = embedding_service.get_embedding("AML compliance transaction monitoring")
    
    print(f"Generated embedding of dimension: {len(query_embedding)}\n")
    
    # Try query with empty string namespace (where data actually is)
    try:
        print("Querying with namespace='' (empty string)...")
        result = service.index.query(
            vector=query_embedding,
            top_k=5,
            namespace="",  # Empty string
            include_metadata=True
        )
        print(f"✅ Found {len(result.matches)} results!")
        for i, match in enumerate(result.matches[:3], 1):
            print(f"\n{i}. ID: {match.id}")
            print(f"   Score: {match.score:.4f}")
            if match.metadata:
                print(f"   Title: {match.metadata.get('title', 'N/A')[:60]}")
                print(f"   Source: {match.metadata.get('source', 'N/A')}")
    except Exception as e:
        print(f"❌ ERROR: {e}\n")
    
    # Try with __default__
    try:
        print("\nQuerying with namespace='__default__'...")
        result = service.index.query(
            vector=query_embedding,
            top_k=5,
            namespace="__default__",
            include_metadata=True
        )
        print(f"✅ Found {len(result.matches)} results!")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    main()
