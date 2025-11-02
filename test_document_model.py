"""
Simple test to verify Document model works with new fields
"""
from db.database import SessionLocal
from db.models import Document, DocumentStatus
from datetime import datetime
import uuid

def test_document_creation():
    """Test creating a document with new fields"""
    db = SessionLocal()
    
    try:
        print("Testing Document model with new fields...")
        
        # Create a test document
        doc = Document(
            document_id=f"TEST-{uuid.uuid4().hex[:8]}",
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size_bytes=1024,
            file_type="pdf",
            mime_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            transaction_id=None,  # NEW FIELD
            workflow_metadata={"test": "data"},  # NEW FIELD
        )
        
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        print(f"✅ Document created successfully: {doc.document_id}")
        print(f"   - transaction_id: {doc.transaction_id}")
        print(f"   - workflow_metadata: {doc.workflow_metadata}")
        
        # Clean up
        db.delete(doc)
        db.commit()
        
        print("✅ Test passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_document_creation()
