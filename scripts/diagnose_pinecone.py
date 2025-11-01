"""
Diagnostic script to check Pinecone index health and contents.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import settings
from services.pinecone_db import PineconeService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def diagnose_index(index_type: str):
    """Diagnose a Pinecone index."""
    print(f"\n{'=' * 80}")
    print(f"🔍 DIAGNOSING {index_type.upper()} INDEX")
    print(f"{'=' * 80}\n")
    
    try:
        # Initialize service
        service = PineconeService(index_type=index_type)
        
        # Get index stats
        print(f"📊 Index Statistics:")
        stats = service.get_index_stats()
        print(f"   Total Vectors: {stats.get('total_vectors', 0)}")
        print(f"   Dimension: {stats.get('dimension', 0)}")
        print(f"   Namespaces: {stats.get('namespaces', {})}")
        
        # Try searching with a simple query
        print(f"\n🔎 Test Search (query: 'AML compliance', namespace: '__default__', NO FILTERS):")
        results = service.search_by_text(
            query_text="AML compliance",
            top_k=5,
            filters=None,  # No filters
            namespace="__default__"
        )
        print(f"   Results found: {len(results)}")
        
        if results:
            print(f"\n   Top 3 Results:")
            for i, result in enumerate(results[:3], 1):
                print(f"   {i}. ID: {result.get('rule_id', 'N/A')}")
                print(f"      Score: {result.get('score', 0):.4f}")
                # Show all available fields to debug
                print(f"      Available fields: {list(result.keys())}")
                print(f"      Text preview: {str(result.get('text', 'N/A'))[:100]}...")
                print()
        else:
            print(f"   ⚠️  No results found in __default__ namespace!")
        
        # Try with different query
        print(f"\n🔎 Test Search (query: 'transaction monitoring', namespace: '__default__'):")
        results_empty = service.search_by_text(
            query_text="transaction monitoring",
            top_k=5,
            namespace="__default__"
        )
        print(f"   Results found: {len(results_empty)}")
        
        return stats, results
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def main():
    """Main diagnostic function."""
    print("\n" + "=" * 80)
    print("🏥 PINECONE HEALTH CHECK")
    print("=" * 80)
    
    print(f"\n📋 Configuration:")
    print(f"   API Key: {settings.pinecone_api_key[:10]}...")
    print(f"   Internal Host: {settings.pinecone_internal_index_host}")
    print(f"   External Host: {settings.pinecone_external_index_host}")
    
    # Diagnose internal index
    internal_stats, internal_results = diagnose_index("internal")
    
    # Diagnose external index
    external_stats, external_results = diagnose_index("external")
    
    # Summary
    print(f"\n{'=' * 80}")
    print("📝 SUMMARY")
    print(f"{'=' * 80}\n")
    
    if internal_stats:
        print(f"✅ Internal Index: {internal_stats.get('total_vectors', 0)} vectors")
        if internal_stats.get('total_vectors', 0) == 0:
            print(f"   ⚠️  WARNING: Internal index is empty!")
            print(f"   💡 Run: python scripts/load_internal_rules_pinecone.py")
    else:
        print(f"❌ Internal Index: Failed to connect")
    
    if external_stats:
        print(f"✅ External Index: {external_stats.get('total_vectors', 0)} vectors")
        if external_stats.get('total_vectors', 0) == 0:
            print(f"   ⚠️  WARNING: External index is empty!")
    else:
        print(f"❌ External Index: Failed to connect")
    
    print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    main()
