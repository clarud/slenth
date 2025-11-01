# Part 2: Document Corroboration - Implementation Plan

**Branch:** `nic_part2`  
**Developer:** niclammm  
**Status:** 🚧 In Progress  
**Updated:** November 1, 2025

---

## 📊 Overview

Part 2 provides **synchronous document validation and risk assessment** for AML compliance. Unlike Part 1 (async via Celery), Part 2 executes immediately and returns complete results.

### Key Features
- ✅ Multi-format document processing (PDF, images, text)
- ✅ OCR text extraction from scanned documents
- ✅ Format validation (structure, spelling, completeness)
- ✅ Image forensics (tampering detection, EXIF analysis, AI-generated detection)
- ✅ Background checks via World-Check One API
- ✅ Cross-reference with transaction history and alerts
- ✅ Real-time risk scoring with evidence tracking

---

## 🔄 Workflow Architecture

### LangGraph Workflow (Sequential)

```
┌─────────────────────┐
│  POST /documents    │
│     /upload         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                     DOCUMENT WORKFLOW                        │
│                    (Synchronous Execution)                   │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
    ┌─────────────────┐
    │ 1. DocumentIntake│  ← Classify document type, validate file
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
    │    2. OCR       │  ← Extract text from images/PDFs
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
    │ 3. FormatValid. │  ← Check structure, spelling, missing fields
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
    │ 4. NLPValidation│  ← Semantic consistency, entity extraction
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
    │ 5. ImageForensics│ ← EXIF, tampering, AI-detection
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
        │                │
    │6. BackgroundCheck│ ← Dilisense API for entities
    │                │
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
    │7. CrossReference│  ← Link with transactions/alerts
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
    │ 8. DocumentRisk │  ← Calculate risk score (0-100)
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
    │9. ReportGenerator│ ← Generate compliance report
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
    │10. EvidenceStore│  ← Save evidence to DB
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────┐
    │   Return JSON   │
    │   Response      │
    └─────────────────┘
```

---

## 📝 Implementation Checklist

### ✅ Phase 0: Infrastructure (COMPLETED)
- [x] Database models (`Document`, `Evidence` tables)
- [x] Pydantic schemas (`DocumentUpload`, `DocumentRiskAssessment`)
- [x] API endpoints (`POST /documents/upload`, `GET /documents/{id}/risk`)
- [x] LangGraph workflow skeleton
- [x] All agent class structures created

### 🚧 Phase 1: Core Document Processing (PRIORITY 1)

#### Agent 1: DocumentIntake (`document_intake.py`)
**Status:** ⏳ TODO  
**Estimated Time:** 1 hour  
**Dependencies:** None

**Requirements:**
- [ ] Detect file type (PDF, PNG, JPG, TIFF, TXT)
- [ ] Validate file size and format
- [ ] Extract basic metadata (filename, size, upload_date)
- [ ] Classify document category (ID, contract, bank statement, invoice, etc.)
- [ ] Store file to `data/uploaded_docs/` with UUID naming
- [ ] Return normalized document object

**Implementation Details:**
```python
# Pseudo-code structure
- Use python-magic or mimetypes for file type detection
- Store original file with UUID: f"{uuid4()}.{extension}"
- Use LLM (optional) to classify document type from filename
- Validation: max 50MB, allowed types: [pdf, png, jpg, jpeg, tiff, txt]
```

**Output to State:**
```python
{
    "document_type": "passport" | "contract" | "bank_statement" | etc.,
    "file_type": "pdf" | "image",
    "stored_file_path": "/data/uploaded_docs/{uuid}.pdf",
    "file_metadata": {
        "size_bytes": 1024000,
        "original_filename": "passport.pdf"
    }
}
```

---

#### Agent 2: OCR (`ocr.py`)
**Status:** ⏳ TODO  
**Estimated Time:** 1.5 hours  
**Dependencies:** Agent 1

**Requirements:**
- [ ] Skip OCR if file is already text (TXT, or text-based PDF)
- [ ] Extract text from images using Tesseract
- [ ] Extract text from scanned PDFs using PyMuPDF + Tesseract
- [ ] Handle multi-language documents (eng + chi_sim)
- [ ] Clean extracted text (remove excess whitespace, fix encoding)
- [ ] Save OCR output to `data/ocr_output/{document_id}.txt`
- [ ] Calculate OCR confidence score

**Implementation Details:**
```python
# Use pytesseract for image OCR
- Convert PDF to images using pdf2image
- Run Tesseract with config: --oem 3 --psm 6
- Languages: eng+chi_sim (from config.tesseract_lang)
- For native PDFs: try PyMuPDF.get_text() first
- If no text found: convert to image and OCR
```

**Output to State:**
```python
{
    "extracted_text": "full text content...",
    "ocr_confidence": 0.92,  # 0-1 scale
    "ocr_output_path": "/data/ocr_output/{doc_id}.txt",
    "text_length": 5420,
    "is_ocr_required": true | false
}
```

---

#### Agent 3: FormatValidation (`format_validation.py`)
**Status:** ⏳ TODO  
**Estimated Time:** 1.5 hours  
**Dependencies:** Agent 2

**Requirements:**
- [ ] Check for required fields based on document type
- [ ] Detect spelling and grammar errors (using language_tool_python or LLM)
- [ ] Identify missing sections (e.g., signature, date, amounts)
- [ ] Validate date formats and consistency
- [ ] Check for suspicious formatting (unusual fonts, overlapping text)
- [ ] Generate list of format issues with severity levels

**Implementation Details:**
```python
# Use LLM-based validation
- Define document type templates (e.g., passport requires: name, dob, number, expiry)
- Use GPT-4 to analyze extracted text against template
- Prompt: "Analyze this {doc_type} document for missing fields, errors, inconsistencies"
- Return structured validation results
```

**Output to State:**
```python
{
    "format_validation": {
        "is_valid": false,
        "issues": [
            {
                "type": "missing_field",
                "field": "signature",
                "severity": "high",
                "description": "Document is missing required signature"
            },
            {
                "type": "spelling_error",
                "text": "recieve",
                "correction": "receive",
                "severity": "low"
            }
        ],
        "missing_fields": ["signature", "date"],
        "completeness_score": 0.75  # 0-1
    }
}
```

---

#### Agent 4: NLPValidation (`nlp_validation.py`)
**Status:** ⏳ TODO  
**Estimated Time:** 1.5 hours  
**Dependencies:** Agent 3

**Requirements:**
- [ ] Extract named entities (persons, organizations, locations, dates)
- [ ] Check semantic consistency across document sections
- [ ] Detect contradictions or inconsistencies in content
- [ ] Validate entity relationships (e.g., dates chronologically valid)
- [ ] Compare entities against expected values (if provided)
- [ ] Generate NLP insights report

**Implementation Details:**
```python
# Use spaCy + LLM
- spaCy for NER extraction: en_core_web_lg model
- Extract entities: PERSON, ORG, GPE, DATE, MONEY, etc.
- Use LLM to check consistency:
  - "Are there any contradictions in this document?"
  - "Does the timeline make sense?"
- Compare extracted entities with document metadata if available
```

**Output to State:**
```python
{
    "nlp_validation": {
        "entities": [
            {"type": "PERSON", "text": "John Doe", "confidence": 0.98},
            {"type": "ORG", "text": "Acme Corp", "confidence": 0.95},
            {"type": "DATE", "text": "2024-03-15", "confidence": 0.99}
        ],
        "inconsistencies": [
            {
                "type": "date_mismatch",
                "description": "Signature date (2024-01-01) is before document date (2024-03-15)",
                "severity": "high"
            }
        ],
        "consistency_score": 0.82  # 0-1
    }
}
```

---

### 🚧 Phase 2: Image Analysis (PRIORITY 2)

#### Agent 5: ImageForensics (`image_forensics.py`)
**Status:** ⏳ TODO  
**Estimated Time:** 2 hours  
**Dependencies:** Agent 1

**Requirements:**
- [ ] EXIF metadata extraction (camera, GPS, timestamp, software)
- [ ] Error Level Analysis (ELA) for tampering detection
- [ ] Detect copy-paste manipulations using clone detection
- [ ] Check for AI-generated images (frequency analysis, noise patterns)
- [ ] Reverse image search (optional - using Google/Bing API)
- [ ] Calculate image authenticity score

**Implementation Details:**
```python
# Use OpenCV, PIL.ExifTags, and custom algorithms
- EXIF: Use ExifRead library
- ELA: Compare original vs re-compressed JPEG artifacts
- Clone detection: SIFT/ORB feature matching
- AI detection: Check noise patterns, frequency domain analysis
- Reverse search: requests to TinEye or Google Images API
```

**Output to State:**
```python
{
    "image_forensics": {
        "has_exif": true,
        "exif_data": {
            "camera": "iPhone 12 Pro",
            "software": "Adobe Photoshop 2024",  # RED FLAG
            "gps": {"lat": 22.3193, "lon": 114.1694},
            "timestamp": "2024:03:15 10:23:45"
        },
        "tampering_detected": true,
        "tampering_indicators": [
            {
                "type": "ela_anomaly",
                "description": "High error level in signature region",
                "confidence": 0.87
            },
            {
                "type": "metadata_inconsistency",
                "description": "Photoshop editing detected",
                "confidence": 0.95
            }
        ],
        "authenticity_score": 0.45,  # 0-1 (low = suspicious)
        "is_ai_generated": false
    }
}
```

---

### 🚧 Phase 3: External Verification (PRIORITY 3)

#### Agent 6: BackgroundCheck (`background_check.py`)
**Status:** ⏳ TODO  
**Estimated Time:** 1.5 hours  
**Dependencies:** Agent 4 (needs entities)

**Requirements:**
- [ ] Extract person/org names from NLP validation results
- [ ] Query World-Check One API for each entity
- [ ] Check for PEP (Politically Exposed Person) status
- [ ] Check for sanctions lists (OFAC, UN, EU)
- [ ] Check for adverse media mentions
- [ ] Calculate entity risk scores

**Implementation Details:**
```python
# Use services/worldcheck.py service
- Get entities from state["nlp_validation"]["entities"]
- Filter for PERSON and ORG types
- Call worldcheck_service.screen_entity() for each
- Aggregate results and calculate risk scores
- Handle API errors and rate limits
```

**Output to State:**
```python
{
    "background_check": {
        "entities_screened": 3,
        "findings": [
            {
                "entity": "John Doe",
                "is_pep": true,
                "pep_details": "Former government official - Finance Ministry",
                "sanctions": [],
                "adverse_media": ["Tax evasion allegations (2020)"],
                "risk_level": "high",
                "risk_score": 0.85
            }
        ],
        "overall_risk": "high",
        "highest_risk_score": 0.85
    }
}
```

---

#### Agent 7: CrossReference (`cross_reference.py`)
**Status:** ⏳ TODO  
**Estimated Time:** 1.5 hours  
**Dependencies:** Agent 6

**Requirements:**
- [ ] Query transactions table for related customer/account
- [ ] Query alerts table for existing alerts on these entities
- [ ] Compare document amounts with transaction amounts
- [ ] Check if document supports or contradicts transaction patterns
- [ ] Identify related cases in case management system
- [ ] Generate cross-reference report

**Implementation Details:**
```python
# Use SQLAlchemy to query related records
- Extract customer_id, account numbers from entities
- Query transactions: filter by customer_id, date range (±30 days)
- Query alerts: filter by entity names, customer_id
- Compare document data with transaction data
- Calculate correlation score
```

**Output to State:**
```python
{
    "cross_reference": {
        "related_transactions": [
            {
                "transaction_id": "TXN-12345",
                "amount": 500000.00,
                "currency": "USD",
                "date": "2024-03-10",
                "matches_document": true
            }
        ],
        "related_alerts": [
            {
                "alert_id": "ALT-789",
                "severity": "high",
                "created_at": "2024-03-12",
                "description": "Large cash transaction"
            }
        ],
        "related_cases": [],
        "correlation_score": 0.78,  # How well document supports transactions
        "discrepancies": [
            "Document amount (450k) differs from transaction amount (500k)"
        ]
    }
}
```

---

### 🚧 Phase 4: Risk Assessment & Reporting (PRIORITY 4)

#### Agent 8: DocumentRisk (`document_risk.py`)
**Status:** ⏳ TODO  
**Estimated Time:** 1.5 hours  
**Dependencies:** Agents 3-7

**Requirements:**
- [ ] Aggregate all validation scores from previous agents
- [ ] Apply weighted scoring algorithm
- [ ] Calculate overall document risk score (0-100)
- [ ] Determine risk band (LOW, MEDIUM, HIGH, CRITICAL)
- [ ] Generate risk summary with key factors
- [ ] Create actionable recommendations

**Implementation Details:**
```python
# Weighted scoring model
weights = {
    "format_validation": 0.15,
    "nlp_validation": 0.15,
    "image_forensics": 0.25,
    "background_check": 0.30,
    "cross_reference": 0.15
}

risk_score = sum(score * weight for score, weight in zip(scores, weights))
risk_band = calculate_risk_band(risk_score)
```

**Output to State:**
```python
{
    "document_risk": {
        "overall_score": 72,  # 0-100
        "risk_band": "HIGH",
        "component_scores": {
            "format_completeness": 75,
            "content_consistency": 82,
            "image_authenticity": 45,  # LOW = HIGH RISK
            "entity_risk": 85,
            "transaction_correlation": 78
        },
        "risk_factors": [
            "Image shows signs of tampering (ELA anomalies)",
            "Entity flagged as PEP with adverse media",
            "Document amount differs from transaction"
        ],
        "recommendations": [
            "Request original unedited document",
            "Conduct enhanced due diligence on John Doe",
            "Verify transaction amount discrepancy"
        ],
        "requires_manual_review": true
    }
}
```

---

#### Agent 9: ReportGenerator (`report_generator.py`)
**Status:** ⏳ TODO  
**Estimated Time:** 1 hour  
**Dependencies:** Agent 8

**Requirements:**
- [ ] Generate comprehensive compliance report
- [ ] Include executive summary
- [ ] Detail all validation findings
- [ ] List all evidence with timestamps
- [ ] Include visualizations (if possible)
- [ ] Format as structured JSON and HTML
- [ ] Save report to `data/reports/{document_id}.json`

**Implementation Details:**
```python
# Use Jinja2 templates for HTML generation
- Create JSON report structure
- Generate HTML report using template
- Include charts/graphs for risk scores
- Add timeline of processing steps
- Format for compliance officer review
```

**Output to State:**
```python
{
    "report": {
        "document_id": "DOC-123",
        "generated_at": "2024-03-15T14:30:00Z",
        "executive_summary": "High-risk document with tampering indicators...",
        "sections": {
            "document_info": {...},
            "validation_results": {...},
            "forensics_analysis": {...},
            "background_screening": {...},
            "risk_assessment": {...},
            "recommendations": [...]
        },
        "report_path": "/data/reports/DOC-123.json",
        "html_report_path": "/data/reports/DOC-123.html"
    }
}
```

---

#### Agent 10: EvidenceStorekeeper (`evidence_storekeeper.py`)
**Status:** ⏳ TODO  
**Estimated Time:** 1 hour  
**Dependencies:** Agent 9

**Requirements:**
- [ ] Save all evidence to database (`evidence` table)
- [ ] Update document status to COMPLETED
- [ ] Create audit trail entries
- [ ] Link evidence to document_id
- [ ] Store processing metrics (duration, agent execution times)
- [ ] Return final workflow state

**Implementation Details:**
```python
# Use SQLAlchemy to persist data
- Insert records into Evidence table for each finding
- Update Document.status = "completed"
- Insert audit_log entries
- Calculate total processing time
- Commit transaction
```

**Output to State:**
```python
{
    "evidence_stored": true,
    "evidence_count": 15,
    "database_records": {
        "document_id": "DOC-123",
        "evidence_ids": ["EV-1", "EV-2", ...],
        "audit_log_ids": ["AUDIT-1", "AUDIT-2", ...]
    },
    "processing_metrics": {
        "total_duration_seconds": 12.5,
        "agent_durations": {
            "document_intake": 0.3,
            "ocr": 4.2,
            "format_validation": 1.5,
            ...
        }
    }
}
```

---

## 🧪 Testing Strategy

### Unit Tests (per agent)
```bash
# Test each agent individually
pytest tests/agents/part2/test_document_intake.py -v
pytest tests/agents/part2/test_ocr.py -v
pytest tests/agents/part2/test_image_forensics.py -v
```

### Integration Tests
```bash
# Test full workflow
pytest tests/workflows/test_document_workflow.py -v
```

### Test Documents
- ✅ `Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf` (provided)
- Create test cases for:
  - Clean passport scan (should pass)
  - Tampered invoice (should detect)
  - AI-generated ID document (should flag)
  - Missing signature contract (should detect)

---

## 📊 Success Metrics

### Functional Requirements
- [ ] Successfully process PDF documents
- [ ] Successfully process image documents (PNG, JPG)
- [ ] OCR accuracy > 90% for clean scans
- [ ] Detect tampering with > 80% accuracy
- [ ] Complete workflow in < 15 seconds
- [ ] Generate comprehensive reports

### Code Quality
- [ ] All agents have proper error handling
- [ ] Comprehensive logging at each step
- [ ] Type hints on all functions
- [ ] Docstrings for all classes/methods
- [ ] No hardcoded values (use config.py)

---

## 🚀 Quick Start Commands

### 1. Install Dependencies (if needed)
```powershell
cd "c:\Users\nicla\OneDrive\Desktop\Coding stuff\Projects\SingHack Hackathon\slenth"
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install  # For crawling (if needed later)
```

### 2. Set Environment Variables
```powershell
# Create .env file with required variables
cp .env.example .env
# Edit .env and add:
# OPENAI_API_KEY=your_key_here
# DATABASE_URL=your_postgres_url
# etc.
```

### 3. Run FastAPI Server
```powershell
cd slenth
uvicorn app.main:app --reload --port 8000
```

### 4. Test Document Upload
```powershell
# Using curl or Postman
curl -X POST http://localhost:8000/documents/upload `
  -F "file=@Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf" `
  -F "document_type=contract"
```

---

## 📚 Key Resources

### Libraries Used
- **pytesseract**: OCR text extraction
- **PyMuPDF**: PDF text extraction
- **opencv-python**: Image processing, ELA analysis
- **ExifRead**: EXIF metadata extraction
- **pillow**: Image manipulation
- **spacy**: NLP and NER extraction
- **langchain**: LLM integration
- **langgraph**: Workflow orchestration

### Documentation
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [World-Check API](https://developers.refinitiv.com/world-check-one-api)

---

## 🎯 Implementation Order (Recommended)

1. **Start with Agent 1 (DocumentIntake)** - Foundation for all others
2. **Then Agent 2 (OCR)** - Critical for text extraction
3. **Agent 8 (DocumentRisk)** - Can be stubbed early for testing
4. **Agent 10 (EvidenceStorekeeper)** - Needed for persistence
5. **Agent 3-4 (Validation agents)** - Core functionality
6. **Agent 5 (ImageForensics)** - Complex but impactful
7. **Agent 6-7 (External checks)** - Depends on external APIs
8. **Agent 9 (ReportGenerator)** - Final output formatting

---

## 🐛 Known Issues / Considerations

1. **Tesseract Installation**: Requires system-level installation on Windows
   - Download from: https://github.com/UB-Mannheim/tesseract/wiki
   - Add to PATH or set `tesseract_path` in config.py

2. **World-Check API**: Requires paid subscription
   - For testing: use mock responses in `services/worldcheck.py`

3. **Large File Processing**: PDFs > 10MB may be slow
   - Consider adding file size limits
   - Implement async processing if needed

4. **Image Format Support**: Focus on common formats first
   - PDF, PNG, JPG, TIFF
   - Add others (HEIC, WebP) later if needed

---

## ✅ Definition of Done

Each agent is considered complete when:
- [ ] Code implementation matches specification above
- [ ] Error handling for all edge cases
- [ ] Logging at INFO level for progress, DEBUG for details
- [ ] Type hints and docstrings present
- [ ] Manual testing passed with sample documents
- [ ] Integration with workflow confirmed
- [ ] Output state structure matches specification

---

**Ready to start implementing!** 🚀

Suggest starting with **DocumentIntake** → **OCR** → **DocumentRisk** → **EvidenceStorekeeper** to get an end-to-end flow working first.
