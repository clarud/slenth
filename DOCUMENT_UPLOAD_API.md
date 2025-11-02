# Document Upload API - Part 2 Integration

## Overview

The document upload API integrates Part 2 document corroboration workflow with Part 1 transaction monitoring. It supports two modes:

1. **Linked Mode** (with `transaction_id`): Links document to a Part 1 transaction and stores all findings in the database
2. **Standalone Mode** (without `transaction_id`): Analyzes document and returns results only (no DB storage of findings)

## Endpoint

### POST `/documents/upload`

Upload and process a document (PDF, JPEG, or PNG) synchronously.

**Supported File Types:**
- PDF (`.pdf`)
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)

**Request:**
```http
POST /documents/upload
Content-Type: multipart/form-data

file: <binary file data>
transaction_id: <optional transaction ID>
document_type: <optional document type hint>
```

**Parameters:**
- `file` (required): The document file to upload
- `transaction_id` (optional): Transaction ID from Part 1 to link document to
- `document_type` (optional): Document type hint (e.g., `purchase_agreement`, `id_document`, `bank_statement`)

**Response:**
```json
{
  "document_id": "DOC-20241101-103000",
  "filename": "purchase_agreement.pdf",
  "file_size": 2048576,
  "file_type": "pdf",
  "status": "completed",
  "transaction_id": "TXN-20241101-001",  // null if standalone
  "uploaded_at": "2024-11-01T10:30:00Z",
  "risk_score": 45.0,
  "risk_level": "Medium",
  "processing_completed_at": "2024-11-01T10:30:15Z",
  "processing_time_seconds": 15.2,
  "total_findings": 8,
  "findings_summary": {
    "format": 2,
    "content": 3,
    "image_forensics": 1,
    "background_check": 1,
    "cross_reference": 1
  },
  "report_path": "/uploads/reports/DOC-20241101-103000_report.pdf"
}
```

## Usage Examples

### Example 1: Upload with Transaction ID (Linked Mode)

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@purchase_agreement.pdf" \
  -F "transaction_id=TXN-20241101-001" \
  -F "document_type=purchase_agreement"
```

**Behavior:**
- Document is linked to transaction `TXN-20241101-001`
- All findings are stored in `document_findings` table
- Document record is created in `documents` table with `transaction_id` set
- Full workflow state is stored in `documents.metadata` JSONB column

### Example 2: Upload without Transaction ID (Standalone Mode)

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@id_document.jpg" \
  -F "document_type=id_document"
```

**Behavior:**
- Document is analyzed standalone (not linked to any transaction)
- Results are returned in API response
- Document record is created in `documents` table without `transaction_id`
- Findings are stored in `documents.metadata` but NOT in `document_findings` table

### Example 3: Python Client

```python
import requests

# With transaction_id
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/documents/upload',
        files={'file': ('document.pdf', f, 'application/pdf')},
        data={
            'transaction_id': 'TXN-20241101-001',
            'document_type': 'purchase_agreement'
        }
    )

result = response.json()
print(f"Risk Score: {result['risk_score']}")
print(f"Findings: {result['total_findings']}")
```

## Part 2 Workflow

The document upload triggers a 10-agent workflow:

1. **DocumentIntake**: Validates file type, size, and extracts metadata
2. **OCR**: Extracts text from PDF/images using Tesseract
3. **FormatValidation**: Checks document structure, formatting, consistency
4. **NLPValidation**: Analyzes content, detects anomalies, extracts entities
5. **ImageForensics**: Detects image manipulation, metadata inconsistencies
6. **BackgroundCheck**: Checks entities against watchlists (Dilisense API)
7. **CrossReference**: Compares with Part 1 transaction data (if `transaction_id` provided)
8. **DocumentRisk**: Calculates overall risk score (0-100) and risk band
9. **ReportGenerator**: Creates PDF report with findings
10. **EvidenceStorekeeper**: Stores evidence and audit trail

## Database Schema

### `documents` Table

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    document_id VARCHAR(100) UNIQUE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER,
    file_type VARCHAR(50),
    mime_type VARCHAR(100),
    document_type VARCHAR(100),
    status VARCHAR(20),
    transaction_id VARCHAR(255) REFERENCES transactions(transaction_id),  -- NEW
    risk_score FLOAT,
    risk_band VARCHAR(20),
    metadata JSONB,  -- NEW: stores complete workflow state
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_documents_transaction_id ON documents(transaction_id);
```

### `document_findings` Table

```sql
CREATE TABLE document_findings (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    finding_type VARCHAR(50),  -- format, nlp, image_forensics, background_check, cross_reference
    finding_category VARCHAR(100),
    finding_severity VARCHAR(20),  -- LOW, MEDIUM, HIGH, CRITICAL
    finding_description TEXT,
    finding_details JSONB,  -- NEW: complete finding object
    detected_at TIMESTAMP,  -- NEW: when finding was detected
    created_at TIMESTAMP
);
```

## Migration

Run the migration to add new columns:

```bash
psql -U postgres -d slenth -f migrations/add_document_transaction_link.sql
```

## Testing

Run the test script:

```bash
python test_document_upload.py
```

This tests:
1. Upload with transaction_id (linked mode)
2. Upload without transaction_id (standalone mode)
3. Retrieve risk assessment

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents/upload` | Upload and process document |
| GET | `/documents/{document_id}/risk` | Get risk assessment |
| GET | `/documents/{document_id}/findings` | Get detailed findings |
| GET | `/documents/{document_id}/report` | Download PDF report |
| POST | `/documents/{document_id}/acknowledge` | Acknowledge review |

## Error Handling

### Invalid File Type
```json
{
  "detail": "Unsupported file type: docx. Supported: pdf, jpg, jpeg, png"
}
```

### Transaction Not Found
```json
{
  "detail": "Transaction TXN-20241101-001 not found"
}
```

### Processing Error
```json
{
  "detail": "Error processing document: <error message>"
}
```

## Frontend Integration

The frontend should:

1. **For Part 1 Transactions**: Include a "Upload Supporting Document" button that passes the `transaction_id`
2. **For Standalone Analysis**: Provide a separate "Analyze Document" page without `transaction_id`
3. **Display Results**: Show risk score, findings breakdown, and download link for PDF report

Example React component:

```typescript
// Upload linked to transaction
const uploadDocumentForTransaction = async (file: File, transactionId: string) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('transaction_id', transactionId);
  formData.append('document_type', 'purchase_agreement');
  
  const response = await fetch('/documents/upload', {
    method: 'POST',
    body: formData
  });
  
  return response.json();
};

// Upload standalone
const uploadDocumentStandalone = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('/documents/upload', {
    method: 'POST',
    body: formData
  });
  
  return response.json();
};
```

## Configuration

Configure upload settings in `config.py`:

```python
# Document upload settings
upload_dir = "uploads/documents"
max_upload_size_mb = 50  # Maximum file size in MB
```

## Notes

- Processing is **synchronous** - the API call blocks until document processing is complete
- Average processing time: 10-30 seconds depending on document complexity
- OCR processing may take longer for image-heavy PDFs or large images
- Background check (Dilisense API) may add 2-5 seconds if enabled
