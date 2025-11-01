"""
Test PDFForensicsAgent on real PDF document
"""

import asyncio
import sys
import os
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set env vars
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5432/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test')

import logging

logging.basicConfig(level=logging.INFO)

# Import agent directly
import importlib.util

spec = importlib.util.spec_from_file_location(
    "pdf_forensics",
    project_root / "agents" / "part2" / "pdf_forensics.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PDFForensicsAgent = module.PDFForensicsAgent


async def test_pdf_forensics(pdf_path: str):
    """Test PDF forensics on real document"""
    
    print("=" * 80)
    print("🔍 PDF FORENSICS TEST")
    print("=" * 80)
    print(f"\n📄 PDF: {pdf_path}\n")
    
    state = {
        "file_path": pdf_path,
        "metadata": {},
        "errors": []
    }
    
    agent = PDFForensicsAgent()
    result = await agent.execute(state)
    
    print("=" * 80)
    print("📊 PDF METADATA")
    print("=" * 80)
    pdf_meta = result.get("pdf_metadata", {})
    print(f"Title: {pdf_meta.get('title', 'N/A')}")
    print(f"Author: {pdf_meta.get('author', 'N/A')}")
    print(f"Creator: {pdf_meta.get('creator', 'N/A')}")
    print(f"Producer: {pdf_meta.get('producer', 'N/A')}")
    print(f"Creation Date: {pdf_meta.get('creation_date', 'N/A')}")
    print(f"Modification Date: {pdf_meta.get('mod_date', 'N/A')}")
    print(f"Pages: {pdf_meta.get('page_count', 'N/A')}")
    print(f"File Size: {pdf_meta.get('file_size', 0) / 1024:.2f} KB")
    print()
    
    print("=" * 80)
    print("🔐 INTEGRITY ANALYSIS")
    print("=" * 80)
    print(f"✅ Integrity Score: {result.get('integrity_score', 0)}/100")
    print(f"🔒 Document Hash: {result.get('document_hash', 'N/A')[:16]}...")
    print(f"🛡️  Software Trust: {result.get('software_trust_level', 'unknown').upper()}")
    print(f"⚠️  Tampering Detected: {'YES' if result.get('tampering_detected') else 'NO'}")
    print()
    
    if result.get('tampering_indicators'):
        print("🚨 TAMPERING INDICATORS:")
        for indicator in result['tampering_indicators']:
            print(f"   [{indicator['severity'].upper()}] {indicator['type']}")
            print(f"   → {indicator['description']}")
        print()
    
    if result.get('forensics_issues'):
        print(f"📋 FORENSICS ISSUES ({len(result['forensics_issues'])}):")
        for issue in result['forensics_issues']:
            print(f"   [{issue['severity'].upper()}] {issue['type']}")
            print(f"   → {issue['description']}")
        print()
    
    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    if result['integrity_score'] >= 80:
        print("✅ Document appears AUTHENTIC (high integrity)")
    elif result['integrity_score'] >= 60:
        print("⚠️  Document has SOME CONCERNS (medium integrity)")
    else:
        print("❌ Document has SERIOUS ISSUES (low integrity)")
    
    print(f"\n   Integrity Score: {result['integrity_score']}/100")
    print(f"   Software Trust: {result['software_trust_level']}")
    print(f"   Tampering: {'Detected' if result['tampering_detected'] else 'None'}")
    print(f"   Issues: {len(result.get('forensics_issues', []))}")
    
    print()
    print("=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pdf_forensics.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    asyncio.run(test_pdf_forensics(pdf_path))
