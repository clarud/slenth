"""
Test script for document upload endpoint with two scenarios:
1. WITH transaction_id - stores findings in DB
2. WITHOUT transaction_id - returns analysis only
"""

import requests
import json
from pathlib import Path

# API base URL
BASE_URL = "http://localhost:8000"

def test_upload_with_transaction():
    """Test document upload linked to a transaction"""
    print("\n" + "="*80)
    print("TEST 1: Upload document WITH transaction_id")
    print("="*80)
    
    # First, create a test transaction or use existing one
    # For this test, we'll use a placeholder transaction_id
    transaction_id = "TXN-20241101-001"
    
    # Prepare test file (you can use any PDF/JPG/PNG)
    test_file_path = Path("test_docs/sample_document.pdf")
    
    if not test_file_path.exists():
        print(f"⚠️  Test file not found: {test_file_path}")
        print("Creating a dummy file for testing...")
        test_file_path.parent.mkdir(exist_ok=True)
        # Create a minimal PDF for testing
        test_file_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF")
    
    # Upload document
    with open(test_file_path, 'rb') as f:
        files = {'file': ('sample_document.pdf', f, 'application/pdf')}
        data = {
            'transaction_id': transaction_id,
            'document_type': 'purchase_agreement'
        }
        
        print(f"\n📤 Uploading document linked to transaction: {transaction_id}")
        response = requests.post(
            f"{BASE_URL}/documents/upload",
            files=files,
            data=data
        )
    
    print(f"\n📊 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Upload successful!")
        print(f"   Document ID: {result['document_id']}")
        print(f"   Transaction ID: {result.get('transaction_id', 'N/A')}")
        print(f"   Status: {result['status']}")
        print(f"   Risk Score: {result.get('risk_score', 'N/A')}")
        print(f"   Risk Level: {result.get('risk_level', 'N/A')}")
        print(f"   Processing Time: {result.get('processing_time_seconds', 0):.2f}s")
        print(f"   Total Findings: {result.get('total_findings', 0)}")
        
        if result.get('findings_summary'):
            print("\n   Findings Breakdown:")
            for finding_type, count in result['findings_summary'].items():
                print(f"      - {finding_type}: {count}")
        
        if result.get('report_path'):
            print(f"\n   Report: {result['report_path']}")
        
        return result['document_id']
    else:
        print(f"\n❌ Upload failed: {response.text}")
        return None


def test_upload_standalone():
    """Test document upload without transaction_id (standalone analysis)"""
    print("\n" + "="*80)
    print("TEST 2: Upload document WITHOUT transaction_id (standalone)")
    print("="*80)
    
    # Prepare test file
    test_file_path = Path("test_docs/sample_image.jpg")
    
    if not test_file_path.exists():
        print(f"⚠️  Test file not found: {test_file_path}")
        print("Creating a dummy JPG for testing...")
        # Create a minimal JPG (1x1 red pixel)
        test_file_path.write_bytes(
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
            b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
            b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00'
            b'\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\xff\xc4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00'
            b'\x08\x01\x01\x00\x00?\x00\x7f\xd9'
        )
    
    # Upload document WITHOUT transaction_id
    with open(test_file_path, 'rb') as f:
        files = {'file': ('sample_image.jpg', f, 'image/jpeg')}
        data = {
            'document_type': 'id_document'
        }
        
        print(f"\n📤 Uploading standalone document (no transaction link)")
        response = requests.post(
            f"{BASE_URL}/documents/upload",
            files=files,
            data=data
        )
    
    print(f"\n📊 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Upload successful!")
        print(f"   Document ID: {result['document_id']}")
        print(f"   Transaction ID: {result.get('transaction_id', 'None - Standalone')}")
        print(f"   Status: {result['status']}")
        print(f"   Risk Score: {result.get('risk_score', 'N/A')}")
        print(f"   Risk Level: {result.get('risk_level', 'N/A')}")
        print(f"   Processing Time: {result.get('processing_time_seconds', 0):.2f}s")
        print(f"   Total Findings: {result.get('total_findings', 0)}")
        
        if result.get('findings_summary'):
            print("\n   Findings Breakdown:")
            for finding_type, count in result['findings_summary'].items():
                print(f"      - {finding_type}: {count}")
        
        print("\n   Note: Since no transaction_id was provided, findings are returned")
        print("         in the response but NOT stored in the database.")
        
        return result['document_id']
    else:
        print(f"\n❌ Upload failed: {response.text}")
        return None


def test_get_document_risk(document_id):
    """Test getting document risk assessment"""
    print("\n" + "="*80)
    print(f"TEST 3: Get document risk assessment for {document_id}")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/documents/{document_id}/risk")
    
    print(f"\n📊 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Risk assessment retrieved!")
        print(f"   Risk Score: {result.get('risk_score', 'N/A')}")
        print(f"   Risk Level: {result.get('risk_level', 'N/A')}")
        print(f"   Total Findings: {result.get('total_findings', 0)}")
        
        print("\n   Risk Breakdown:")
        print(f"      - Format Risk: {result.get('format_risk', 0)}")
        print(f"      - Content Risk: {result.get('content_risk', 0)}")
        print(f"      - Image Risk: {result.get('image_risk', 0)}")
        print(f"      - Background Check Risk: {result.get('background_check_risk', 0)}")
        
        if result.get('key_issues'):
            print("\n   Key Issues:")
            for issue in result['key_issues']:
                print(f"      - {issue}")
    else:
        print(f"\n❌ Failed to get risk assessment: {response.text}")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("DOCUMENT UPLOAD API TESTS")
    print("="*80)
    print("\nTesting two scenarios:")
    print("1. Upload WITH transaction_id - stores findings in DB")
    print("2. Upload WITHOUT transaction_id - returns analysis only")
    
    # Test 1: With transaction_id
    doc_id_1 = test_upload_with_transaction()
    
    # Test 2: Without transaction_id
    doc_id_2 = test_upload_standalone()
    
    # Test 3: Get risk assessment (if first upload succeeded)
    if doc_id_1:
        test_get_document_risk(doc_id_1)
    
    print("\n" + "="*80)
    print("TESTS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
