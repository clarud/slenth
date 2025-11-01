"""
Test ImageForensicsAgent

Tests EXIF extraction, tampering detection, and metadata analysis
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
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

# Import agent directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "image_forensics",
    project_root / "agents" / "part2" / "image_forensics.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ImageForensicsAgent = module.ImageForensicsAgent


async def test_image_forensics(pdf_path: str):
    """Test image forensics agent on a PDF"""
    
    print("=" * 80)
    print("🔍 IMAGE FORENSICS AGENT TEST")
    print("=" * 80)
    print(f"\n📄 PDF: {pdf_path}\n")
    
    # Initialize agent
    agent = ImageForensicsAgent()
    
    # Setup state
    state = {
        "file_path": pdf_path,
        "metadata": {
            "file_name": Path(pdf_path).name,
            "has_images": True  # We know this PDF has images
        },
        "errors": []
    }
    
    # Execute agent
    result = await agent.execute(state)
    
    print("-" * 80)
    print("📊 FORENSICS RESULTS")
    print("-" * 80)
    print()
    
    print(f"✅ Forensics Executed: {result.get('image_forensics_executed', False)}")
    print(f"📸 Has EXIF: {result.get('has_exif', False)}")
    print(f"📊 Authenticity Score: {result.get('authenticity_score', 0)}/100")
    print(f"⚠️  Tampering Indicators: {len(result.get('tampering_indicators', []))}")
    print(f"📋 Forensics Issues: {len(result.get('forensics_issues', []))}")
    print()
    
    # Show EXIF data
    exif_data = result.get('exif_data', {})
    if exif_data:
        print("📸 EXIF Data Found:")
        print("-" * 80)
        for image_id, exif in exif_data.items():
            print(f"\n{image_id}:")
            # Show important EXIF tags
            important_tags = ['DateTime', 'DateTimeOriginal', 'Make', 'Model', 'Software', 
                            'ProcessingSoftware', 'Orientation', 'XResolution', 'YResolution']
            for tag in important_tags:
                if tag in exif:
                    print(f"  {tag}: {exif[tag]}")
            
            # Show total tags
            print(f"  Total EXIF tags: {len(exif)}")
        print()
    else:
        print("❌ No EXIF data found")
        print()
    
    # Show software detected
    software = result.get('software_detected')
    if software:
        print(f"⚠️  Editing Software Detected: {software}")
        print()
    
    # Show tampering indicators
    tampering = result.get('tampering_indicators', [])
    if tampering:
        print(f"🚨 Tampering Indicators ({len(tampering)}):")
        print("-" * 80)
        for i, indicator in enumerate(tampering, 1):
            print(f"{i}. [{indicator.get('severity', 'N/A').upper()}] {indicator.get('type', 'N/A')}")
            print(f"   {indicator.get('description', 'N/A')}")
            if 'image_index' in indicator:
                print(f"   Image: #{indicator['image_index']}")
        print()
    else:
        print("✅ No tampering indicators found")
        print()
    
    # Show forensics issues
    issues = result.get('forensics_issues', [])
    if issues:
        print(f"📋 Forensics Issues ({len(issues)}):")
        print("-" * 80)
        for i, issue in enumerate(issues, 1):
            print(f"{i}. [{issue.get('severity', 'N/A').upper()}] {issue.get('type', 'N/A')}")
            print(f"   {issue.get('description', 'N/A')}")
        print()
    else:
        print("✅ No forensics issues found")
        print()
    
    # Assessment
    score = result.get('authenticity_score', 0)
    print("=" * 80)
    print("🎯 ASSESSMENT")
    print("=" * 80)
    print()
    
    if score >= 80:
        assessment = "✅ HIGH AUTHENTICITY - Image appears genuine"
    elif score >= 60:
        assessment = "⚠️  MEDIUM AUTHENTICITY - Some concerns detected"
    elif score >= 40:
        assessment = "⚠️  LOW AUTHENTICITY - Multiple issues detected"
    else:
        assessment = "❌ VERY LOW AUTHENTICITY - Significant tampering/editing detected"
    
    print(f"{assessment}")
    print(f"Score: {score}/100")
    print()
    
    if result.get('errors'):
        print(f"⚠️  Errors: {len(result['errors'])}")
        for error in result['errors']:
            print(f"   - {error}")
        print()
    
    print("=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_image_forensics.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    asyncio.run(test_image_forensics(pdf_path))
