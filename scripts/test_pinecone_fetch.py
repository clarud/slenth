"""Test fetching a specific record by ID to see its namespace."""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.pinecone_db import PineconeService

def main():
    print("Testing Pinecone fetch by ID...\n")
    
    service = PineconeService(index_type="internal")
    
    # Try to fetch using the index directly
    try:
        # List some IDs from the index (try fetch operation)
        result = service.index.fetch(
            ids=["1", "2", "3", "rule_1", "rule_2"],  # Common ID patterns
            namespace=""  # Empty string - where data actually is
        )
        print(f"Fetch with namespace='': {len(result.vectors)} records found")
        if result.vectors:
            for id, data in list(result.vectors.items())[:2]:
                print(f"\n  ID: {id}")
                print(f"  Metadata keys: {list(data.metadata.keys()) if data.metadata else 'None'}")
    except Exception as e:
        print(f"Fetch with namespace='': ERROR - {e}")
    
    # Try with __default__
    try:
        result = service.index.fetch(
            ids=["1", "2", "3", "rule_1", "rule_2"],
            namespace="__default__"
        )
        print(f"\nFetch with namespace='__default__': {len(result.vectors)} records found")
    except Exception as e:
        print(f"\nFetch with namespace='__default__': ERROR - {e}")

if __name__ == "__main__":
    main()
