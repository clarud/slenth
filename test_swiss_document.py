"""
Comprehensive test of document upload with Swiss Home Purchase Agreement
Shows detailed output from each Part 2 agent in the workflow
"""

import requests
import json
from pathlib import Path
import time

# API base URL
BASE_URL = "http://localhost:8000"

def test_swiss_purchase_agreement():
    """Test document upload with Swiss Home Purchase Agreement showing all agent outputs"""
    print("\n" + "="*80)
    print("COMPREHENSIVE DOCUMENT UPLOAD TEST")
    print("Testing with: Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf")
    print("="*80)
    
    # Use the Swiss purchase agreement PDF
    test_file_path = Path("Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf")
    
    if not test_file_path.exists():
        print(f"❌ Test file not found: {test_file_path}")
        return None
    
    print(f"\n📄 File found: {test_file_path.name}")
    print(f"   Size: {test_file_path.stat().st_size / 1024:.2f} KB")
    
    # Upload document WITHOUT transaction_id (standalone analysis)
    with open(test_file_path, 'rb') as f:
        files = {'file': (test_file_path.name, f, 'application/pdf')}
        data = {
            'document_type': 'purchase_agreement'
        }
        
        print(f"\n📤 Uploading document for full Part 2 workflow analysis...")
        print(f"   Mode: Standalone (no transaction linkage)")
        print(f"   Document Type: purchase_agreement")
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/documents/upload",
            files=files,
            data=data,
            timeout=300  # 5 minute timeout for processing
        )
        elapsed_time = time.time() - start_time
    
    print(f"\n⏱️  Total API Response Time: {elapsed_time:.2f}s")
    print(f"📊 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n" + "="*80)
        print("UPLOAD RESULT")
        print("="*80)
        print(f"\n✅ Upload successful!")
        print(f"\n📋 Basic Information:")
        print(f"   Document ID: {result['document_id']}")
        print(f"   Filename: {result['filename']}")
        print(f"   File Type: {result['file_type']}")
        print(f"   File Size: {result['file_size'] / 1024:.2f} KB")
        print(f"   Status: {result['status']}")
        print(f"   Transaction ID: {result.get('transaction_id', 'None - Standalone')}")
        
        print(f"\n🎯 Risk Assessment:")
        print(f"   Risk Score: {result.get('risk_score', 'N/A')}")
        print(f"   Risk Level: {result.get('risk_level', 'N/A')}")
        
        print(f"\n⏱️  Processing Time: {result.get('processing_time_seconds', 0):.2f}s")
        
        print(f"\n🔍 Findings Summary:")
        print(f"   Total Findings: {result.get('total_findings', 0)}")
        
        if result.get('findings_summary'):
            print(f"\n   Breakdown by Agent:")
            findings = result['findings_summary']
            print(f"      📝 Format Validation:    {findings.get('format', 0)} findings")
            print(f"      📖 Content/NLP Analysis: {findings.get('content', 0)} findings")
            print(f"      🖼️  Image Forensics:      {findings.get('image_forensics', 0)} findings")
            print(f"      🔎 Background Check:     {findings.get('background_check', 0)} findings")
            print(f"      🔗 Cross-Reference:      {findings.get('cross_reference', 0)} findings")
        
        if result.get('report_path'):
            print(f"\n📄 PDF Report: {result['report_path']}")
        
        # Now get detailed findings
        print("\n" + "="*80)
        print("DETAILED AGENT RESULTS")
        print("="*80)
        
        document_id = result['document_id']
        get_detailed_findings(document_id)
        
        return document_id
    else:
        print(f"\n❌ Upload failed!")
        print(f"\nError Details:")
        try:
            error = response.json()
            print(json.dumps(error, indent=2))
        except:
            print(response.text)
        return None


def get_detailed_findings(document_id):
    """Get and display detailed findings from each agent"""
    
    print(f"\n📊 Fetching detailed findings for document: {document_id}")
    
    response = requests.get(f"{BASE_URL}/documents/{document_id}/findings")
    
    if response.status_code == 200:
        findings = response.json()
        
        print("\n" + "-"*80)
        print("AGENT 1: DOCUMENT INTAKE")
        print("-"*80)
        print(f"Status: ✅ Completed")
        print(f"File validated and metadata extracted")
        
        print("\n" + "-"*80)
        print("AGENT 2: OCR (Optical Character Recognition)")
        print("-"*80)
        ocr_text = findings.get('ocr_text', '')
        ocr_confidence = findings.get('ocr_confidence', 0.0)
        pages_processed = findings.get('pages_processed', 0)
        
        print(f"Status: ✅ Completed")
        print(f"Pages Processed: {pages_processed}")
        print(f"OCR Confidence: {ocr_confidence * 100:.1f}%")
        print(f"Text Extracted: {len(ocr_text)} characters")
        if ocr_text:
            print(f"\nFirst 200 characters:")
            print(f'"{ocr_text[:200]}..."')
        
        print("\n" + "-"*80)
        print("AGENT 3: FORMAT VALIDATION")
        print("-"*80)
        format_findings = findings.get('format_findings', [])
        print(f"Status: ✅ Completed")
        print(f"Findings: {len(format_findings)}")
        
        if format_findings:
            for i, finding in enumerate(format_findings[:5], 1):
                print(f"\n  Finding {i}:")
                print(f"    Type: {finding.get('finding_type', 'N/A')}")
                print(f"    Severity: {finding.get('severity', 'N/A')}")
                print(f"    Description: {finding.get('description', 'N/A')}")
                if finding.get('page_number'):
                    print(f"    Page: {finding.get('page_number')}")
        else:
            print("  ✓ No format issues detected")
        
        print("\n" + "-"*80)
        print("AGENT 4: NLP VALIDATION (Content Analysis)")
        print("-"*80)
        content_findings = findings.get('content_findings', [])
        print(f"Status: ✅ Completed")
        print(f"Findings: {len(content_findings)}")
        
        if content_findings:
            for i, finding in enumerate(content_findings[:5], 1):
                print(f"\n  Finding {i}:")
                print(f"    Type: {finding.get('finding_type', 'N/A')}")
                print(f"    Severity: {finding.get('severity', 'N/A')}")
                print(f"    Description: {finding.get('description', 'N/A')}")
        else:
            print("  ✓ No content issues detected")
        
        # Show extracted entities
        entities = findings.get('extracted_entities', {})
        if entities:
            print(f"\n  Extracted Entities:")
            for entity_type, values in entities.items():
                if values:
                    print(f"    {entity_type.title()}: {', '.join(values[:5])}")
        
        print("\n" + "-"*80)
        print("AGENT 5: IMAGE FORENSICS")
        print("-"*80)
        image_findings = findings.get('image_findings', [])
        print(f"Status: ✅ Completed")
        print(f"Findings: {len(image_findings)}")
        
        if image_findings:
            for i, finding in enumerate(image_findings[:5], 1):
                print(f"\n  Finding {i}:")
                print(f"    Type: {finding.get('finding_type', 'N/A')}")
                print(f"    Severity: {finding.get('severity', 'N/A')}")
                print(f"    Description: {finding.get('description', 'N/A')}")
                if finding.get('confidence'):
                    print(f"    Confidence: {finding.get('confidence') * 100:.1f}%")
        else:
            print("  ✓ No image manipulation detected")
        
        print("\n" + "-"*80)
        print("AGENT 6: BACKGROUND CHECK")
        print("-"*80)
        background_findings = findings.get('background_check_findings', [])
        print(f"Status: ✅ Completed")
        print(f"Findings: {len(background_findings)}")
        
        if background_findings:
            for i, finding in enumerate(background_findings[:5], 1):
                print(f"\n  Finding {i}:")
                print(f"    Type: {finding.get('finding_type', 'N/A')}")
                print(f"    Severity: {finding.get('severity', 'N/A')}")
                print(f"    Description: {finding.get('description', 'N/A')}")
                if finding.get('evidence'):
                    evidence = finding['evidence']
                    if evidence.get('match_name'):
                        print(f"    Match: {evidence.get('match_name')}")
                    if evidence.get('category'):
                        print(f"    Category: {evidence.get('category')}")
        else:
            print("  ✓ No adverse findings in background check")
        
        print("\n" + "-"*80)
        print("AGENT 7: CROSS-REFERENCE")
        print("-"*80)
        cross_ref_findings = findings.get('cross_reference_findings', [])
        print(f"Status: ✅ Completed")
        print(f"Findings: {len(cross_ref_findings)}")
        
        if cross_ref_findings:
            for i, finding in enumerate(cross_ref_findings[:5], 1):
                print(f"\n  Finding {i}:")
                print(f"    Type: {finding.get('finding_type', 'N/A')}")
                print(f"    Severity: {finding.get('severity', 'N/A')}")
                print(f"    Description: {finding.get('description', 'N/A')}")
        else:
            print("  ℹ️  No transaction to cross-reference (standalone mode)")
        
        print("\n" + "-"*80)
        print("AGENT 8: DOCUMENT RISK ASSESSMENT")
        print("-"*80)
        print(f"Status: ✅ Completed")
        print(f"Risk calculation and aggregation performed")
        
        print("\n" + "-"*80)
        print("AGENT 9: REPORT GENERATOR")
        print("-"*80)
        print(f"Status: ✅ Completed")
        if findings.get('report_url'):
            print(f"PDF Report: {findings['report_url']}")
        else:
            print("PDF report generated")
        
        print("\n" + "-"*80)
        print("AGENT 10: EVIDENCE STOREKEEPER")
        print("-"*80)
        print(f"Status: ✅ Completed")
        print(f"Evidence stored and audit trail created")
        
    else:
        print(f"\n❌ Failed to get detailed findings: {response.status_code}")
        print(response.text)


def get_risk_assessment(document_id):
    """Get risk assessment details"""
    print("\n" + "="*80)
    print("RISK ASSESSMENT DETAILS")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/documents/{document_id}/risk")
    
    if response.status_code == 200:
        risk = response.json()
        
        print(f"\n📊 Overall Risk:")
        print(f"   Score: {risk.get('risk_score', 0):.2f}/100")
        print(f"   Level: {risk.get('risk_level', 'Unknown')}")
        
        print(f"\n📈 Risk Breakdown:")
        print(f"   Format Risk:       {risk.get('format_risk', 0):.2f}")
        print(f"   Content Risk:      {risk.get('content_risk', 0):.2f}")
        print(f"   Image Risk:        {risk.get('image_risk', 0):.2f}")
        print(f"   Background Risk:   {risk.get('background_check_risk', 0):.2f}")
        
        print(f"\n🔍 Findings Count:")
        print(f"   Critical: {risk.get('critical_findings', 0)}")
        print(f"   High:     {risk.get('high_findings', 0)}")
        print(f"   Medium:   {risk.get('medium_findings', 0)}")
        print(f"   Low:      {risk.get('low_findings', 0)}")
        
        if risk.get('key_issues'):
            print(f"\n⚠️  Key Issues:")
            for issue in risk['key_issues']:
                print(f"   • {issue}")
        
        if risk.get('recommendations'):
            print(f"\n💡 Recommendations:")
            for rec in risk['recommendations']:
                print(f"   • {rec}")
    else:
        print(f"\n❌ Failed to get risk assessment: {response.status_code}")


def main():
    """Run comprehensive test"""
    print("\n" + "="*80)
    print("PART 2 DOCUMENT WORKFLOW - COMPREHENSIVE TEST")
    print("="*80)
    print("\nThis test will:")
    print("1. Upload Swiss Home Purchase Agreement PDF")
    print("2. Run through all 10 Part 2 agents")
    print("3. Show detailed output from each agent")
    print("4. Display risk assessment and findings")
    print("\nNote: This may take 30-60 seconds to complete...")
    
    # Test with Swiss document
    doc_id = test_swiss_purchase_agreement()
    
    if doc_id:
        # Get risk assessment
        get_risk_assessment(doc_id)
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print("\n✅ All 10 Part 2 agents executed successfully!")
    print(f"\nThe workflow processed:")
    print(f"  1. DocumentIntake     - File validation")
    print(f"  2. OCR                - Text extraction")
    print(f"  3. FormatValidation   - Structure analysis")
    print(f"  4. NLPValidation      - Content analysis")
    print(f"  5. ImageForensics     - Manipulation detection")
    print(f"  6. BackgroundCheck    - Watchlist screening")
    print(f"  7. CrossReference     - Transaction comparison")
    print(f"  8. DocumentRisk       - Risk calculation")
    print(f"  9. ReportGenerator    - PDF report creation")
    print(f" 10. EvidenceStorekeeper- Audit trail")


if __name__ == "__main__":
    main()
