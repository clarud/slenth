# Part 2 Document Upload Integration - Implementation Summary

## What Was Implemented

### 1. Database Schema Updates

**`documents` table:**
- Added `transaction_id` column (VARCHAR(255), nullable, indexed) - links to Part 1 transactions
- Added `metadata` column (JSONB) - stores complete workflow state and findings
- Added foreign key relationship to `transactions` table

**`document_findings` table:**
- Added `finding_details` column (JSONB) - stores complete finding object from workflow
- Added `detected_at` column (TIMESTAMP) - tracks when finding was detected

**Migration file:** `migrations/add_document_transaction_link.sql`

### 2. API Endpoint Updates

**POST `/documents/upload`**

Enhanced to support two modes:

#### Mode 1: Linked to Transaction (WITH transaction_id)
- Validates transaction exists before processing
- Links document to Part 1 transaction
- Stores ALL findings in `document_findings` table
- Stores complete workflow state in `documents.metadata`
- Enables Part 1 + Part 2 corroboration analysis

#### Mode 2: Standalone Analysis (WITHOUT transaction_id)
- Processes document independently
- Returns complete analysis in API response
- Creates document record but doesn't store findings in `document_findings` table
- Useful for quick document verification without transaction context

**New Parameters:**
- `file` (required) - PDF, JPEG, or PNG file
- `transaction_id` (optional) - links to Part 1 transaction
- `document_type` (optional) - hints document type (purchase_agreement, id_document, etc.)

**Enhanced Response:**
```json
{
  "document_id": "DOC-...",
  "transaction_id": "TXN-...",  // or null
  "risk_score": 45.0,
  "risk_level": "Medium",
  "total_findings": 8,
  "findings_summary": {
    "format": 2,
    "content": 3,
    "image_forensics": 1,
    "background_check": 1,
    "cross_reference": 1
  },
  "report_path": "/path/to/report.pdf",
  "processing_time_seconds": 15.2
}
```

### 3. Workflow Integration

The document upload automatically triggers the complete Part 2 workflow:

1. **DocumentIntake** - Validates file (PDF/JPG/PNG only)
2. **OCR** - Extracts text
3. **FormatValidation** - Checks structure
4. **NLPValidation** - Analyzes content
5. **ImageForensics** - Detects manipulation
6. **BackgroundCheck** - Watchlist screening
7. **CrossReference** - Compares with transaction data (if transaction_id provided)
8. **DocumentRisk** - Calculates risk score
9. **ReportGenerator** - Creates PDF report
10. **EvidenceStorekeeper** - Stores audit trail

### 4. Finding Storage Logic

**With transaction_id:**
```python
# Store findings in database
for finding in all_findings:
    DocumentFinding(
        document_id=document.id,
        finding_type="format/nlp/image_forensics/background_check/cross_reference",
        finding_severity="low/medium/high/critical",
        finding_description="...",
        finding_details=complete_finding_object,
        detected_at=datetime.utcnow()
    )
```

**Without transaction_id:**
```python
# Store in metadata but not in document_findings table
document.metadata = {
    "workflow_state": {
        "format_findings": [...],
        "content_findings": [...],
        "image_findings": [...],
        # ... all findings
    }
}
```

### 5. Model Updates

**`db/models.py`:**
- Added `transaction_id` field to `Document` model
- Added `metadata` field to `Document` model
- Added relationship: `transaction = relationship("Transaction", backref="documents")`
- Added `finding_details` field to `DocumentFinding` model
- Added `detected_at` field to `DocumentFinding` model

**`app/schemas/document.py`:**
- Updated `DocumentUploadResponse` to include:
  - `transaction_id`
  - `total_findings`
  - `findings_summary`
  - `report_path`

### 6. File Type Validation

Only accepts:
- **PDF** (.pdf)
- **JPEG** (.jpg, .jpeg)
- **PNG** (.png)

Returns 400 error for unsupported file types.

### 7. Testing

Created comprehensive test script: `test_document_upload.py`

Tests:
1. ✅ Upload with transaction_id (linked mode)
2. ✅ Upload without transaction_id (standalone mode)
3. ✅ Get risk assessment
4. ✅ Invalid file type rejection
5. ✅ Transaction validation

### 8. Documentation

Created detailed API documentation: `DOCUMENT_UPLOAD_API.md`

Includes:
- API endpoint specifications
- Usage examples (curl, Python)
- Database schema
- Frontend integration examples
- Error handling
- Configuration options

## File Changes

### Modified Files:
1. `db/models.py` - Added transaction_id, metadata, finding_details, detected_at
2. `app/api/documents.py` - Completely rewrote upload endpoint with two modes
3. `app/schemas/document.py` - Updated DocumentUploadResponse schema

### New Files:
1. `migrations/add_document_transaction_link.sql` - Database migration
2. `test_document_upload.py` - Test script
3. `DOCUMENT_UPLOAD_API.md` - API documentation

## Key Features

### ✅ Dual Mode Operation
- **Linked**: Full integration with Part 1 transactions, complete DB storage
- **Standalone**: Quick analysis, results-only response

### ✅ Complete Workflow Integration
- All 10 Part 2 agents execute automatically
- Synchronous processing (no queuing)
- Results available immediately

### ✅ Comprehensive Finding Storage
- Format validation findings
- Content/NLP findings
- Image forensics findings
- Background check findings
- Cross-reference findings (when transaction_id provided)

### ✅ Risk Assessment
- 0-100 risk score
- Risk band (Low/Medium/High/Critical)
- Breakdown by category
- PDF report generation

### ✅ Transaction Corroboration
- When transaction_id provided, CrossReference agent compares:
  - Names in document vs transaction parties
  - Amounts in document vs transaction amount
  - Dates in document vs transaction dates
  - Jurisdictions and locations

## Frontend Integration Points

### 1. Transaction Detail Page
Add "Upload Supporting Document" button:
```typescript
<Button onClick={() => uploadDocument(file, transaction.id)}>
  Upload Supporting Document
</Button>
```

### 2. Standalone Document Analysis Page
Add document upload without transaction:
```typescript
<Button onClick={() => uploadDocument(file, null)}>
  Analyze Document
</Button>
```

### 3. Display Results
Show:
- Risk score gauge
- Findings breakdown chart
- Download PDF report button
- View detailed findings link

## Usage Flow

### Scenario 1: Compliance Officer Reviews Transaction
1. Officer reviews flagged transaction in Part 1
2. Clicks "Upload Supporting Document"
3. Selects purchase agreement PDF
4. System automatically:
   - Runs all 10 Part 2 agents
   - Compares document data with transaction data
   - Stores findings in database
   - Links to transaction record
5. Officer sees combined Part 1 + Part 2 risk assessment

### Scenario 2: Quick Document Verification
1. User uploads document without transaction context
2. System runs Part 2 workflow
3. Returns analysis immediately
4. No transaction linkage, no detailed DB storage
5. User can download PDF report

## Next Steps

1. **Run Migration:**
   ```bash
   psql -U postgres -d slenth -f migrations/add_document_transaction_link.sql
   ```

2. **Test Endpoint:**
   ```bash
   python test_document_upload.py
   ```

3. **Frontend Integration:**
   - Add upload buttons to transaction detail page
   - Create standalone document analysis page
   - Display results and PDF report

4. **Optional Enhancements:**
   - Add webhook for async processing
   - Add batch upload support
   - Add document comparison feature
   - Add document version tracking

## Configuration Required

In `config.py`:
```python
# Document settings
upload_dir = "uploads/documents"
max_upload_size_mb = 50

# Supported file types (enforced in API)
SUPPORTED_FILE_TYPES = ['pdf', 'jpg', 'jpeg', 'png']
```

## Notes

- Processing is **synchronous** - takes 10-30 seconds per document
- File size limit: 50MB (configurable)
- Background check requires Dilisense API key
- OCR requires Tesseract installation
- Image forensics requires PIL/Pillow
- PDF processing requires PyMuPDF
