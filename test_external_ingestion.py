"""Test the updated external_rules_ingestion.py workflow"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import logging
from cron.external_rules_ingestion import run_all_crawlers

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("TESTING UPDATED EXTERNAL RULES INGESTION")
print("=" * 80)
print("\nUpdated workflow:")
print("  1. HKMA: Crawl + Use crawler's save_to_db()")
print("  2. MAS: Crawl + Use crawler's save_to_db()")
print("  3. FINMA: Parse local PDFs + Use save_rules_to_db()")
print("\n" + "=" * 80)
print()

# Run the ingestion job
run_all_crawlers()

print("\n" + "=" * 80)
print("✅ INGESTION TEST COMPLETE")
print("=" * 80)
