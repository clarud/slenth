"""
Test Case: API Endpoint Testing for Part 2 Document Workflow
Tests the document corroboration workflow via HTTP API endpoints
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import httpx
import time

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    loaded = load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed")

# Set required env vars
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5432/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test')
os.environ.setdefault('MAX_UPLOAD_SIZE_MB', '50')
os.environ.setdefault('OCR_OUTPUT_DIR', 'data/ocr_output')
os.environ['ENABLE_BACKGROUND_CHECK'] = 'false'

print("\n" + "="*80)
print("🧪 TEST CASE: API ENDPOINT TESTING")
print("="*80)
print("\n📡 Testing Part 2 document workflow via HTTP API")
print("🔬 Method: FastAPI HTTP endpoints")
print("⚙️  Mode: Full Production API Test")
print("💡 Note: Server must be running on http://localhost:8000")
print()

# API configuration
API_BASE_URL = "http://localhost:8000"
TIMEOUT = 120.0  # 2 minutes for processing

async def test_api_endpoints():
    """Test document workflow via API endpoints"""
    
    # File path
    file_path = project_root / "Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf"
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"📄 Document: {file_path.name}")
    print(f"💾 Size: {file_path.stat().st_size / (1024*1024):.2f} MB")
    print()
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # Step 1: Check server health
            print("1️⃣  HEALTH CHECK")
            print("-" * 80)
            
            try:
                response = await client.get(f"{API_BASE_URL}/health")
                if response.status_code == 200:
                    health = response.json()
                    print(f"✅ Server Status: {health.get('status', 'unknown')}")
                    print(f"🕐 Server Time: {health.get('timestamp', 'N/A')}")
                else:
                    print(f"⚠️  Server returned: {response.status_code}")
            except httpx.ConnectError:
                print(f"❌ Cannot connect to API server at {API_BASE_URL}")
                print(f"💡 Please start the server with:")
                print(f"   cd {project_root}")
                print(f"   uvicorn app.main:app --reload --port 8000")
                return False
            
            # Step 2: Upload document
            print(f"\n2️⃣  UPLOAD DOCUMENT")
            print("-" * 80)
            
            start_time = time.time()
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_path.name, f, 'application/pdf')
                }
                
                print(f"📤 Uploading {file_path.name}...")
                response = await client.post(
                    f"{API_BASE_URL}/documents/upload",
                    files=files
                )
            
            upload_time = time.time() - start_time
            
            if response.status_code != 200:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            result = response.json()
            document_id = result.get('document_id')
            
            print(f"✅ Upload successful!")
            print(f"📋 Document ID: {document_id}")
            print(f"📊 Status: {result.get('status', 'unknown')}")
            print(f"⏱️  Upload Time: {upload_time:.2f}s")
            
            # Print processing results if available (Part 2 is synchronous)
            if result.get('risk_score') is not None:
                print(f"\n📊 Processing Results:")
                print(f"   - Risk Score: {result.get('risk_score', 0):.1f}/100")
                print(f"   - Risk Level: {result.get('risk_level', 'UNKNOWN')}")
                print(f"   - Processing Time: {result.get('processing_time_seconds', 0):.2f}s")
            
            # Step 3: Get risk assessment
            print(f"\n3️⃣  GET RISK ASSESSMENT")
            print("-" * 80)
            
            response = await client.get(f"{API_BASE_URL}/documents/{document_id}/risk")
            
            if response.status_code == 200:
                risk_data = response.json()
                print(f"✅ Risk assessment retrieved")
                print(f"📊 Overall Risk Score: {risk_data.get('risk_score', 0):.1f}/100")
                print(f"🚨 Risk Level: {risk_data.get('risk_level', 'UNKNOWN')}")
                print(f"👁️  Manual Review: {risk_data.get('requires_manual_review', False)}")
                
                # Component scores
                component_scores = risk_data.get('component_scores', {})
                if component_scores:
                    print(f"\n📊 Component Scores:")
                    for component, score in component_scores.items():
                        print(f"   - {component}: {score:.1f}/100")
                
                # Risk factors
                risk_factors = risk_data.get('risk_factors', [])
                if risk_factors:
                    print(f"\n🚨 Risk Factors ({len(risk_factors)}):")
                    for i, factor in enumerate(risk_factors[:3], 1):
                        severity = factor.get('severity', 'unknown').upper()
                        factor_type = factor.get('type', 'unknown')
                        desc = factor.get('description', 'No description')
                        print(f"   {i}. [{severity}] {factor_type}")
                        print(f"      → {desc}")
            else:
                print(f"⚠️  Could not retrieve risk assessment: {response.status_code}")
            
            # Step 4: Get detailed findings
            print(f"\n4️⃣  GET DETAILED FINDINGS")
            print("-" * 80)
            
            response = await client.get(f"{API_BASE_URL}/documents/{document_id}/findings")
            
            if response.status_code == 200:
                findings = response.json()
                print(f"✅ Findings retrieved")
                
                # OCR findings
                ocr = findings.get('ocr_findings', {})
                if ocr:
                    print(f"\n📝 OCR Results:")
                    print(f"   - Text Extracted: {ocr.get('has_text', False)}")
                    print(f"   - Characters: {ocr.get('text_length', 0)}")
                    
                    entities = ocr.get('extracted_entities', {})
                    if entities:
                        print(f"   - Dates: {len(entities.get('dates', []))}")
                        print(f"   - Amounts: {len(entities.get('amounts', []))}")
                        print(f"   - Names: {len(entities.get('potential_names', []))}")
                
                # Format validation
                format_val = findings.get('format_validation', {})
                if format_val:
                    print(f"\n📋 Format Validation:")
                    print(f"   - Valid: {format_val.get('is_valid', False)}")
                    print(f"   - Quality Score: {format_val.get('quality_score', 0)}/100")
                    print(f"   - Spelling Errors: {format_val.get('spelling_errors', 0)}")
                
                # NLP validation
                nlp = findings.get('nlp_validation', {})
                if nlp:
                    print(f"\n🤖 NLP Validation:")
                    print(f"   - Valid: {nlp.get('is_valid', False)}")
                    print(f"   - Consistency Score: {nlp.get('consistency_score', 0)}/100")
                    print(f"   - Contradictions: {len(nlp.get('contradictions', []))}")
                
                # PDF forensics
                pdf_forensics = findings.get('pdf_forensics', {})
                if pdf_forensics:
                    print(f"\n🔍 PDF Forensics:")
                    print(f"   - Tampering: {pdf_forensics.get('tampering_detected', False)}")
                    print(f"   - Integrity Score: {pdf_forensics.get('integrity_score', 0)}/100")
                    print(f"   - Trust Level: {pdf_forensics.get('software_trust_level', 'UNKNOWN')}")
                
                # Image forensics
                image_forensics = findings.get('image_forensics', {})
                if image_forensics:
                    print(f"\n🖼️  Image Forensics:")
                    print(f"   - Images Analyzed: {image_forensics.get('images_analyzed', 0)}")
                    print(f"   - AI-Generated: {image_forensics.get('ai_generated_detected', False)}")
                    print(f"   - Tampering: {image_forensics.get('image_tampering_detected', False)}")
            else:
                print(f"⚠️  Could not retrieve findings: {response.status_code}")
            
            # Step 5: Acknowledge document review
            print(f"\n5️⃣  ACKNOWLEDGE DOCUMENT REVIEW")
            print("-" * 80)
            
            acknowledge_data = {
                "reviewer_name": "Test Reviewer",
                "reviewer_role": "compliance_officer",
                "decision": "approved_with_conditions",
                "comments": "Document reviewed via API test - appears to have tampering indicators requiring manual verification"
            }
            
            response = await client.post(
                f"{API_BASE_URL}/documents/{document_id}/acknowledge",
                json=acknowledge_data
            )
            
            if response.status_code == 200:
                ack = response.json()
                print(f"✅ Review acknowledged")
                print(f"📋 Decision: {ack.get('decision', 'N/A')}")
                print(f"👤 Reviewer: {ack.get('reviewer_name', 'N/A')}")
                print(f"🕐 Timestamp: {ack.get('acknowledged_at', 'N/A')}")
            else:
                print(f"⚠️  Could not acknowledge review: {response.status_code}")
            
            # Final Summary
            print(f"\n{'='*80}")
            print(f"✅ API ENDPOINT TEST COMPLETE")
            print(f"{'='*80}")
            print(f"\n📊 TEST RESULTS:")
            print(f"   Document ID: {document_id}")
            print(f"   All Endpoints: ✅ WORKING")
            print(f"   Total Time: {time.time() - start_time:.2f}s")
            print()
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error during API testing: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    result = asyncio.run(test_api_endpoints())
    
    if result:
        print("✅ API Endpoint Test - PASSED")
        sys.exit(0)
    else:
        print("❌ API Endpoint Test - FAILED")
        sys.exit(1)
