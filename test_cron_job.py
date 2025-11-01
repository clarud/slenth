"""
Test the external rules ingestion cron job

This script tests the cron job in file-saving mode to avoid database dependencies.
Run: python test_cron_job.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variable to save to file instead of DB
output_file = tempfile.mktemp(suffix=".jsonl")
os.environ["CRAWLER_SAVE_TO_FILE"] = output_file

print("=" * 80)
print("Testing External Rules Ingestion Cron Job")
print("=" * 80)
print(f"Output file: {output_file}\n")

try:
    # Import and run the cron job
    from cron.external_rules_ingestion import run_all_crawlers
    
    print("Starting cron job test...\n")
    run_all_crawlers()
    
    # Check results
    print("\n" + "=" * 80)
    print("Test Results")
    print("=" * 80)
    
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"\nTotal rules saved: {len(lines)}")
        
        # Parse and display summary
        import json
        sources = {}
        for line in lines:
            try:
                rule = json.loads(line)
                source = rule.get('source', 'Unknown')
                sources[source] = sources.get(source, 0) + 1
            except:
                continue
        
        print("\nBreakdown by source:")
        for source, count in sources.items():
            print(f"  {source}: {count} rules")
        
        # Show sample rules
        print("\nSample rules:")
        for i, line in enumerate(lines[:3], 1):
            try:
                rule = json.loads(line)
                title = rule.get('title', 'No title')[:70]
                source = rule.get('source', '?')
                words = len(rule.get('content', '').split())
                print(f"  [{i}] [{source}] {title}... ({words} words)")
            except:
                continue
        
        # Cleanup
        os.remove(output_file)
        print(f"\nCleaned up temporary file: {output_file}")
    else:
        print("ERROR: No output file created")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Clean up environment
    if "CRAWLER_SAVE_TO_FILE" in os.environ:
        del os.environ["CRAWLER_SAVE_TO_FILE"]

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
