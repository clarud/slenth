"""
Debug script to check what's actually in the database after document upload
"""
from db.database import SessionLocal
from db.models import Document
import json

def check_latest_document():
    """Check the latest document in database"""
    db = SessionLocal()
    
    try:
        # Get the most recent document
        doc = db.query(Document).order_by(Document.created_at.desc()).first()
        
        if not doc:
            print("No documents found in database")
            return
        
        print("="*80)
        print("LATEST DOCUMENT IN DATABASE")
        print("="*80)
        print(f"\nDocument ID: {doc.document_id}")
        print(f"Filename: {doc.filename}")
        print(f"Status: {doc.status}")
        print(f"Transaction ID: {doc.transaction_id}")
        print(f"Risk Score: {doc.risk_score}")
        print(f"Risk Band: {doc.risk_band}")
        
        print(f"\n" + "="*80)
        print("WORKFLOW METADATA")
        print("="*80)
        
        if doc.workflow_metadata:
            print(json.dumps(doc.workflow_metadata, indent=2, default=str))
        else:
            print("No workflow metadata stored")
        
        print(f"\n" + "="*80)
        print("FINDINGS")
        print("="*80)
        
        # Check if there are any findings
        if doc.findings:
            print(f"Found {len(doc.findings)} findings:")
            for finding in doc.findings:
                print(f"\n  - Type: {finding.finding_type}")
                print(f"    Severity: {finding.finding_severity}")
                print(f"    Description: {finding.finding_description}")
        else:
            print("No findings stored in database")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_latest_document()
