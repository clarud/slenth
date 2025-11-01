# Part 2 Tests - Document Corroboration Workflow

This folder contains integration tests for the Part 2 document corroboration workflow.

## 🧪 Test Files

### `test_case_1_pdf.py` ✅
**Purpose:** Complete end-to-end workflow test for PDF documents (Direct Agent Testing)  
**Document:** `Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf`  
**Agents Tested:** 8 agents (Intake → OCR → Background Check → Format → NLP → PDF Forensics → Image Forensics → Risk)

**Features:**
- ✅ Tests all 8 implemented Part 2 agents sequentially
- ✅ Direct agent execution (no API server required)
- ✅ Background check disabled (preserves Dilisense API credits)
- ✅ Uses Groq LLM for NLP validation
- ✅ Comprehensive output with agent-by-agent results
- ✅ Final risk assessment and recommendations

**Usage:**
```powershell
# Navigate to tests folder
cd tests\part2

# Run test
..\..\..\.venv312\Scripts\python.exe test_case_1_pdf.py
```

### `test_api_endpoints.py` ✅
**Purpose:** Test document workflow via HTTP API endpoints (Production Testing)  
**Document:** `Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf`  
**Endpoints Tested:** Upload, Risk Assessment, Findings, Acknowledge

**Features:**
- ✅ Tests complete API layer (HTTP endpoints)
- ✅ Requires running FastAPI server
- ✅ Tests all document endpoints
- ✅ Validates request/response schemas
- ✅ Tests synchronous workflow execution
- ✅ Verifies acknowledgment flow

**Usage:**
```powershell
# Terminal 1: Start API server
cd slenth
uvicorn app.main:app --reload --port 8000

# Terminal 2: Run API test
cd tests\part2
$env:PYTHONIOENCODING="utf-8"
..\..\..\.venv312\Scripts\python.exe test_api_endpoints.py
```

**Expected Output:**
```
🧪 TEST CASE 1: PDF WORKFLOW (NO DILISENSE)
📄 Document: Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf
⚙️  Mode: Full Production Workflow (Background Check DISABLED)

1️⃣  DOCUMENT INTAKE AGENT
✅ Valid: True
📄 Format: PDF
📊 Pages: 1
💾 Size: 0.52 MB

2️⃣  OCR AGENT
✅ Text Extracted: True
📝 Characters: 1928
📄 Pages: 1

3️⃣  BACKGROUND CHECK AGENT (SKIPPED)
⏭️  Background check disabled (ENABLE_BACKGROUND_CHECK=false)
💡 No Dilisense API credits consumed

... [continues through all 8 agents]

📊 Overall Risk Score: 45.0/100
🚨 Risk Band: MEDIUM
👁️  Manual Review Required: False
```

**Expected Output:**
```
🧪 TEST CASE: API ENDPOINT TESTING
📡 Testing Part 2 document workflow via HTTP API

1️⃣  HEALTH CHECK
✅ Server Status: healthy
🕐 Server Time: 2025-11-02T...

2️⃣  UPLOAD DOCUMENT
📤 Uploading Swiss_Home_Purchase_Agreement...
✅ Upload successful!
📋 Document ID: DOC-20251102-123456
📊 Status: completed
📊 Risk Score: 39.1/100
📊 Risk Level: MEDIUM

3️⃣  GET RISK ASSESSMENT
✅ Risk assessment retrieved
📊 Overall Risk Score: 39.1/100
🚨 Risk Level: MEDIUM

4️⃣  GET DETAILED FINDINGS
✅ Findings retrieved
📝 OCR Results...
📋 Format Validation...
🤖 NLP Validation...

5️⃣  ACKNOWLEDGE DOCUMENT REVIEW
✅ Review acknowledged
📋 Decision: approved_with_conditions
```

---

## 📋 Agent Coverage

| Agent | Status | Description |
|-------|--------|-------------|
| 1. DocumentIntake | ✅ | File validation, format detection, metadata extraction |
| 2. OCR | ✅ | Text extraction (PyMuPDF + EasyOCR) |
| 3. BackgroundCheck | ⏭️ | PEP/sanctions screening (SKIPPED - no API credits) |
| 4. FormatValidation | ✅ | Structure, spelling, completeness checks |
| 5. NLPValidation | ✅ | Semantic consistency via LLM |
| 6. PDFForensics | ✅ | Tampering detection, integrity scoring |
| 7. ImageForensics | ✅ | AI detection, EXIF analysis, ELA |
| 8. DocumentRisk | ✅ | Risk aggregation and scoring |
| 9. ReportGenerator | ❌ | Not yet implemented |
| 10. EvidenceStorekeeper | ❌ | Not yet implemented |

**Status:** 8/10 agents implemented and tested ✅

---

## ⚙️ Configuration

### Environment Variables Required

Set in `.env` file at project root:
```bash
# Required
GROQ_API_KEY=your_groq_key_here

# Optional (if not using Groq for embeddings)
OPENAI_API_KEY=your_openai_key_here

# Disable background check to preserve API credits
ENABLE_BACKGROUND_CHECK=false
```

### Dilisense Background Check

**IMPORTANT:** Background check is **DISABLED** by default in tests to preserve API credits.

The test sets: `os.environ['ENABLE_BACKGROUND_CHECK'] = 'false'`

To enable (if you have credits):
```python
# In test file, change line 38 to:
os.environ['ENABLE_BACKGROUND_CHECK'] = 'true'
```

---

## � Test Results Interpretation

### Risk Bands
- **LOW (0-30):** Document appears legitimate, minimal concerns
- **MEDIUM (31-60):** Some issues detected, review recommended
- **HIGH (61-85):** Significant concerns, manual review required
- **CRITICAL (86-100):** Severe issues, escalate immediately

### Common Issues Detected
- **Format issues:** Missing sections, poor document quality
- **OCR errors:** Low text extraction quality, unreadable content
- **Tampering detected:** PDF metadata anomalies, suspicious modifications
- **Semantic inconsistencies:** Contradictions in document content
- **Image forensics flags:** AI-generated images, EXIF tampering

---

## 🔧 Troubleshooting

### EasyOCR Not Found
**Problem:** `ModuleNotFoundError: No module named 'easyocr'`

**Solution:**
```bash
..\..\..\.venv312\Scripts\python.exe -m pip install easyocr
```

### PyMuPDF Not Found
**Problem:** `ModuleNotFoundError: No module named 'fitz'`

**Solution:**
```bash
..\..\..\.venv312\Scripts\python.exe -m pip install PyMuPDF
```

### GROQ_API_KEY not set
**Problem:** `ValidationError: 1 validation error for Settings`

**Solution:** Add to `.env` file:
```bash
GROQ_API_KEY=your_key_here
```

### Background check runs (consuming credits)
**Problem:** Test makes Dilisense API calls

**Solution:** Ensure `os.environ['ENABLE_BACKGROUND_CHECK'] = 'false'` is set **before** config imports

### Unicode Errors in PowerShell
**Problem:** `UnicodeEncodeError` with emoji characters

**Solution:**
```powershell
$env:PYTHONIOENCODING="utf-8"
```

---

## � Next Steps

1. ✅ Run `test_case_1_pdf.py` to verify 8 agents work end-to-end
2. 🔄 Implement `ReportGeneratorAgent` (generate PDF reports)
3. 🔄 Implement `EvidenceStorekeeperAgent` (persist to database)
4. 🔄 Add test cases for JPG and PNG formats
5. 🚀 Deploy to production

---

**Last Updated:** November 2, 2025  
**Test Coverage:** 8/10 agents (80%) ✅
