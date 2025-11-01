# Part 2 Agents - Complete Implementation Documentation

**Last Updated:** November 1, 2025  
**Status:** 7/10 Agents Fully Implemented

---

## 📊 Overview

This document provides detailed documentation for all implemented Part 2 agents, including what they analyze, their inputs/outputs, and scoring methodology.

---

## 1️⃣ DocumentIntakeAgent

### **Purpose**
Accept and validate uploaded documents, classify document type, extract basic metadata.

### **What is Analyzed**
- ✅ File existence and accessibility
- ✅ File size limits (max 50MB)
- ✅ File format validation (PDF)
- ✅ PDF integrity (not corrupted)
- ✅ PDF metadata (creator, producer, dates)
- ✅ Page count and structure
- ✅ Document type classification (purchase_agreement, id_document, contract, etc.)

### **Input Requirements**
```python
{
    "file_path": "path/to/document.pdf",
    "document_id": "doc_123",
    "document": {"document_type": "purchase_agreement"}  # Optional hint
}
```

### **Output**
```python
{
    "file_valid": True,                    # Boolean: File passes validation
    "document_type": "purchase_agreement", # Classified type
    "metadata": {
        "file_name": "contract.pdf",
        "file_size_mb": 2.5,
        "page_count": 15,
        "has_images": True,
        "creator": "Adobe Acrobat",
        "producer": "Adobe PDF Library",
        "creation_date": "2024-01-15",
        "modification_date": "2024-01-20",
        "title": "Purchase Agreement",
        "author": "John Doe",
        "encrypted": False
    },
    "errors": []  # List of validation errors if any
}
```

### **Scoring/Validation**
- Binary: Pass/Fail
- Fails if: file missing, too large, corrupted, or wrong format

---

## 2️⃣ OCRAgent

### **Purpose**
Extract text from PDF documents (including scanned pages), perform entity extraction.

### **What is Analyzed**
- ✅ Text extraction from each PDF page
- ✅ OCR on scanned/image-based pages (using EasyOCR)
- ✅ Entity extraction:
  - Dates (various formats)
  - Monetary amounts (with currency symbols)
  - Email addresses
  - Phone numbers
  - Potential person names (NER patterns)
- ✅ Text quality metrics (character count, readability)

### **Input Requirements**
```python
{
    "file_path": "path/to/document.pdf",
    "document_id": "doc_123",
    "metadata": {...}  # From DocumentIntakeAgent
}
```

### **Output**
```python
{
    "ocr_text": "[Page 1]\nPurchase Agreement...\n[Page 2]\n...",  # Full extracted text
    "page_texts": [
        {
            "page_number": 1,
            "text": "Purchase Agreement between...",
            "char_count": 1500,
            "method": "text_extraction"  # or "easyocr"
        },
        # ... more pages
    ],
    "ocr_output_path": "data/ocr_output/doc_123_ocr.txt",  # Saved text file
    "text_length": 15000,                # Total character count
    "has_text": True,                    # Boolean: text successfully extracted
    "extracted_entities": {
        "dates": ["01/05/2024", "15-Jan-2024"],
        "amounts": ["$500,000", "CHF 1,200"],
        "emails": ["john@example.com"],
        "phone_numbers": ["+1-555-0123"],
        "potential_names": ["John Doe", "Jane Smith"]
    }
}
```

### **Scoring/Validation**
- Binary: Pass/Fail
- Passes if: `text_length > 50` characters
- OCR quality indicator: `char_count` per page

---

## 3️⃣ BackgroundCheckAgent

### **Purpose**
Screen individuals/entities mentioned in the document against PEP, sanctions, and criminal databases using Dilisense API.

### **What is Analyzed**
- ✅ Name extraction from OCR text (3 patterns)
- ✅ PEP (Politically Exposed Person) screening
- ✅ Sanctions list screening
- ✅ Criminal database screening
- ✅ Risk level assessment per entity
- ✅ Batch processing (up to 10 entities)

### **Input Requirements**
```python
{
    "ocr_text": "Agreement between Mr. John Doe...",
    "extracted_entities": {"potential_names": ["John Doe"]},
    "document_id": "doc_123"
}
```

### **Output**
```python
{
    "background_check_results": [
        {
            "name": "John Doe",
            "match_status": "clear",      # or "match", "possible_match"
            "risk_level": "low",          # low, medium, high, critical
            "is_pep": False,
            "is_sanctioned": False,
            "is_criminal": False,
            "total_hits": 0,
            "match_details": {...}
        },
        # ... more entities
    ],
    "pep_found": False,                   # Boolean: ANY PEP detected
    "sanctions_found": False,             # Boolean: ANY sanctions detected
    "background_risk_score": 0,           # 0-100 (0=safe, 100=critical)
    "screened_entities": ["John Doe"]     # List of names screened
}
```

### **Scoring Methodology**
```python
Risk Score Calculation:
- Base: 0 points
- Each PEP match: +75 points
- Each sanctions match: +90 points
- Each criminal match: +50 points
- Capped at: 100 points

Risk Bands:
- 0-25:   LOW
- 26-50:  MEDIUM
- 51-75:  HIGH
- 76-100: CRITICAL
```

---

## 4️⃣ FormatValidationAgent

### **Purpose**
Validate document structure, check spelling/grammar, assess completeness.

### **What is Analyzed**
- ✅ Document structure:
  - Required sections present (title, parties, terms, signatures)
  - Logical section ordering
  - Proper formatting
- ✅ Spelling and grammar:
  - Spell checking (pyspellchecker)
  - Grammar patterns
  - Capitalization consistency
- ✅ Completeness:
  - Missing sections
  - Placeholder content detection
  - Required fields present
- ✅ Red flags:
  - Suspicious keywords (urgent, immediate, offshore)
  - Unusual patterns
  - Formatting inconsistencies

### **Input Requirements**
```python
{
    "ocr_text": "Full document text...",
    "document_type": "purchase_agreement",
    "extracted_entities": {...}
}
```

### **Output**
```python
{
    "format_valid": False,                # Boolean: overall validation
    "format_quality_score": 46,           # 0-100
    "completeness_score": 46,             # 0-100
    "spelling_errors": 28,                # Count of misspelled words
    "format_validation_issues": [
        {
            "type": "missing_section",
            "severity": "high",
            "description": "Missing 'Payment Terms' section",
            "location": "document_structure"
        },
        # ... more issues
    ],
    "missing_sections": ["payment_terms", "signatures"],
    "red_flags": [
        "Document contains 'urgent' keyword",
        "Suspicious offshore reference"
    ],
    "structure_issues": ["Poor capitalization consistency"]
}
```

### **Scoring Methodology**
```python
Completeness Score (starts at 100):
- Missing document type: -20
- No key entities: -10
- Missing sections: -10 per section
- Spelling errors: -1 per 5 errors (max -20)
- Red flags: -5 per flag
- Structure issues: -3 per issue

Valid if: completeness_score >= 70
```

---

## 5️⃣ NLPValidationAgent

### **Purpose**
Semantic validation using LLM to detect contradictions, inconsistencies, and logical errors.

### **What is Analyzed**
- ✅ Semantic consistency:
  - Contradictory statements
  - Timeline inconsistencies
  - Logical gaps
- ✅ Document completeness (semantic level)
- ✅ Suspicious patterns:
  - Unusual clauses
  - Missing logic
  - Calculation errors
- ✅ Content quality assessment

### **Input Requirements**
```python
{
    "ocr_text": "Full document text...",
    "document_type": "purchase_agreement",
    "extracted_entities": {...}
}
```

### **Output**
```python
{
    "nlp_valid": False,                   # Boolean: overall validation
    "consistency_score": 60,              # 0-100
    "contradictions": [
        {
            "type": "date_inconsistency",
            "severity": "high",
            "description": "Signing date before agreement date",
            "locations": ["page 1", "page 5"]
        },
        # ... more contradictions
    ],
    "timeline_issues": [
        "Payment date precedes contract date"
    ],
    "semantic_issues": [
        {
            "type": "incomplete",
            "severity": "medium",
            "description": "Missing payment amount specification"
        }
    ],
    "calculation_errors": [],
    "suspicious_patterns": [
        "Unusual offshore transaction mention"
    ]
}
```

### **Scoring Methodology**
```python
Consistency Score (from LLM analysis):
- Base: 100
- Critical issues: -30 per issue
- High severity: -20 per issue
- Medium severity: -10 per issue
- Low severity: -5 per issue
- Capped at: 0-100

Valid if: consistency_score >= 70
```

### **LLM Integration**
- Model: Groq (llama-3.3-70b-versatile)
- Temperature: 0.3
- Max tokens: 1000
- Document-specific prompts for different types

---

## 6️⃣ PDFForensicsAgent

### **Purpose**
Analyze PDF structure, detect tampering, assess document integrity.

### **What is Analyzed**
- ✅ PDF metadata extraction:
  - Creator software
  - Producer
  - Creation/modification dates
  - Encryption status
- ✅ Structural analysis:
  - XRef table inspection
  - Incremental updates detection
  - Linearization check
- ✅ Tampering indicators:
  - Multiple XRef tables (critical)
  - Non-linearized updates (medium)
  - Mismatched metadata (high)
- ✅ Software trust assessment:
  - Trusted: Adobe, Microsoft, etc.
  - Suspicious: Online converters, unknown tools
- ✅ Document quality issues:
  - Single page documents (low)
  - No metadata (medium)

### **Input Requirements**
```python
{
    "file_path": "path/to/document.pdf",
    "metadata": {...}  # From DocumentIntakeAgent
}
```

### **Output**
```python
{
    "pdf_metadata": {
        "creator": "PDFium",
        "producer": "PDFium",
        "creation_date": "D:20251030150723",
        "mod_date": None,
        "title": "",
        "author": "",
        "encrypted": False,
        "page_count": 1
    },
    "tampering_detected": True,           # Boolean: tampering indicators found
    "tampering_indicators": [
        {
            "type": "multiple_xref_tables",
            "severity": "critical",
            "description": "Multiple xref tables detected (2)",
            "details": "Document may have been modified after creation"
        }
    ],
    "software_trust_level": "unknown",    # trusted, unknown, suspicious
    "integrity_score": 65,                # 0-100
    "forensics_issues": [...],
    "document_hash": "a18abb1bf31d7b9a..."  # SHA-256 hash
}
```

### **Scoring Methodology**
```python
Integrity Score (starts at 100):
- Critical tampering: -30 per indicator
- High severity: -20
- Medium severity: -10
- Low severity: -5
- Software trust:
  - Unknown: -0
  - Suspicious: -15
- Quality issues: -5 per issue

Tampering detected if: any critical/high indicators found
```

---

## 7️⃣ ImageForensicsAgent ⭐ **NEW!**

### **Purpose**
Advanced image analysis for AI generation detection, tampering detection, and EXIF analysis.

### **What is Analyzed**

#### **A. Image Extraction**
- ✅ Extracts all images from PDF
- ✅ Supports direct image files (JPG, PNG)

#### **B. EXIF Metadata Analysis**
- ✅ Camera make/model
- ✅ Software used (detects AI generators!)
- ✅ Date/time information
- ✅ GPS coordinates
- ✅ Editing software detection

#### **C. AI-Generated Image Detection**
- ✅ Image statistics (smoothness, gradients)
- ✅ Common AI resolutions (512x512, 1024x1024)
- ✅ LLM-powered visual analysis
- ✅ EXIF software signatures (Midjourney, DALL-E, Stable Diffusion)

#### **D. Pixel-Level Tampering Detection** (7 Techniques!)

1. **Edge Consistency Analysis**
   - Laplacian variance
   - Detects unnatural edge patterns
   - Threshold: >500 variance

2. **Noise Pattern Analysis**
   - 64x64 block analysis
   - Detects inconsistent noise across regions
   - Identifies edited areas

3. **Double JPEG Compression Detection**
   - DCT (Discrete Cosine Transform) analysis
   - Detects 8x8 block artifacts
   - Reveals re-saved/edited images

4. **Copy-Move Forgery Detection**
   - ORB feature detector
   - Finds cloned/duplicated regions
   - "Clone stamp" detection

5. **Histogram Uniformity Analysis**
   - Color distribution analysis
   - Detects synthetic images

6. **Lighting Consistency Analysis**
   - HSV brightness analysis
   - Quadrant-based comparison
   - Detects composited images

7. **Block Artifact Detection**
   - 8x8 JPEG block boundary analysis
   - Detects partial editing
   - Compression mismatch detection

#### **E. Reverse Image Search**
- ✅ Perceptual hash generation
- ⚠️ API integration ready (stub)

### **Input Requirements**
```python
{
    "file_path": "path/to/document.pdf",  # or image.jpg
    "document_id": "doc_123"
}
```

### **Output**
```python
{
    "images_analyzed": 1,
    "ai_generated_detected": False,       # Boolean: AI generation detected
    "ai_detection_confidence": 0,         # 0-100
    "image_tampering_detected": True,     # Boolean: tampering detected
    "exif_issues": [
        {
            "type": "missing_metadata",
            "severity": "low",
            "description": "No camera metadata found - may be screenshot or generated"
        }
    ],
    "image_forensics_score": 65,          # 0-100
    "image_findings": [
        {
            "image_index": 0,
            "page": 1,
            "width": 2550,
            "height": 3300,
            "format": "png",
            "color_mode": "RGB",
            "size_kb": 1050.5,
            "exif_data": {...},
            "ai_generated_likely": False,
            "ai_confidence": 0,
            "ai_indicators": [],
            "tampering_detected": True,
            "tampering_confidence": 45,
            "tampering_indicators": [
                "inconsistent_noise_pattern",
                "double_jpeg_compression"
            ],
            "pixel_anomalies": [
                {
                    "type": "noise_inconsistency",
                    "regions": 12
                },
                {
                    "type": "compression_artifact",
                    "evidence": "edge_variance=0.1234"
                }
            ]
        }
    ],
    "reverse_search_results": [
        {
            "search_performed": True,
            "image_hash": "3a7f8d2e...",
            "matches_found": 0,
            "note": "Reverse search ready (requires API integration)"
        }
    ]
}
```

### **Scoring Methodology**
```python
Image Forensics Score (starts at 100):

AI Generation Penalty:
- If AI detected: -20 to -40 (based on confidence)
- Max AI confidence: up to 40 points deduction

Tampering Penalty:
- If tampering detected: -30 points
- Based on pixel anomaly confidence

EXIF Issues:
- Per issue: -5 points
- Max EXIF deduction: -20 points

Tampering Confidence Thresholds:
- Edge inconsistency: +20
- Noise inconsistency: +15
- Double JPEG: +25
- Clone detection: +30
- Histogram uniform: +15
- Lighting mismatch: +20
- Block artifacts: +10
- Detected if: confidence >= 30
```

---

## 8️⃣ DocumentRiskAgent

### **Purpose**
Aggregate all agent findings into comprehensive risk assessment with recommendations.

### **What is Analyzed**
- ✅ Weighted score aggregation from all agents
- ✅ Risk factor identification
- ✅ Risk band classification
- ✅ Manual review determination
- ✅ Recommendation generation

### **Input Requirements**
```python
{
    # All previous agent outputs
    "format_quality_score": 46,
    "consistency_score": 60,
    "integrity_score": 65,
    "background_risk_score": 75,
    "has_text": True,
    "pep_found": True,
    "tampering_detected": True,
    # ... etc
}
```

### **Output**
```python
{
    "overall_risk_score": 29.3,           # 0-100 (weighted average)
    "risk_band": "LOW",                   # LOW, MEDIUM, HIGH, CRITICAL
    "requires_manual_review": True,       # Boolean: needs human review
    "component_scores": {
        "background_check": 100,
        "format_validation": 46,
        "nlp_validation": 60,
        "ocr_quality": 100,
        "pdf_forensics": 65,
        "image_forensics": 65
    },
    "risk_factors": [
        {
            "type": "pdf_tampering",
            "severity": "critical",
            "description": "PDF shows signs of tampering",
            "component": "pdf_forensics"
        },
        {
            "type": "pep_detected",
            "severity": "high",
            "description": "Politically Exposed Person matched",
            "component": "background_check"
        }
    ],
    "recommendations": [
        {
            "action": "request_original",
            "description": "Request original/certified PDF copy",
            "priority": "high"
        },
        {
            "action": "enhanced_due_diligence",
            "description": "Perform EDD, seek senior approval",
            "priority": "high"
        }
    ]
}
```

### **Scoring Methodology**
```python
Component Weights:
- Format validation: 20%
- NLP validation: 20%
- PDF forensics: 30%
- Background check: 25%
- OCR quality: 5%

Overall Score = Weighted average of all components

Risk Bands:
- 0-30:   LOW (but may still need review)
- 31-60:  MEDIUM
- 61-80:  HIGH
- 81-100: CRITICAL

Manual Review Required if:
- Risk score > 60, OR
- PEP detected, OR
- Sanctions detected, OR
- Critical tampering detected, OR
- AI-generated images detected
```

---

## 📊 Complete Workflow Example

```python
Input: Swiss_Home_Purchase_Agreement.pdf

Agent Outputs:
1. DocumentIntake:    ✅ Valid PDF, 1 page, 1.08 MB
2. OCR:               ✅ 1,928 characters extracted
3. BackgroundCheck:   ❌ PEP found (risk: 75/100)
4. FormatValidation:  ❌ Score: 46/100 (28 spelling errors)
5. NLPValidation:     ❌ Score: 60/100 (3 contradictions)
6. PDFForensics:      ❌ Score: 65/100 (tampering detected)
7. ImageForensics:    ❌ Score: 65/100 (tampering detected)
8. DocumentRisk:      ⚠️  LOW but requires review

Final Verdict: 📋 REVIEW REQUIRED
Overall Risk: 29.3/100
Risk Band: LOW
Manual Review: YES (PEP + tampering flags)
```

---

## 🚧 Not Yet Implemented

### 9. CrossReferenceAgent (In Progress)
- Purpose: Correlate with transaction history and KYC data
- Status: Requires Part 1 transaction workflow integration
- Note: Depends on transaction data availability

### 10. ReportGeneratorAgent (Skeleton Only)
- Purpose: Generate comprehensive PDF/HTML reports
- Status: Placeholder only

### 11. EvidenceStorekeeperAgent (Skeleton Only)
- Purpose: Persist evidence, documents, and analysis results
- Status: Placeholder only

---

## 📚 Dependencies

### Core Libraries:
```
PyMuPDF==1.24.14        # PDF processing
Pillow==12.0.0          # Image processing
opencv-python==4.12.0   # Computer vision
ExifRead==3.5.1         # EXIF metadata
easyocr==1.7.2          # OCR
pyspellchecker==0.8.1   # Spell checking
torch==2.9.0            # Deep learning (for OCR)
```

### External APIs:
- **Dilisense API** - Background screening (PEP, sanctions, criminal)
- **Groq API** - LLM for semantic validation

---

## 🎯 Success Criteria by Agent

| Agent | Pass Criteria |
|-------|--------------|
| DocumentIntake | File valid, not corrupted |
| OCR | Text length > 50 chars |
| BackgroundCheck | No PEP/sanctions found |
| FormatValidation | Score >= 70 |
| NLPValidation | Score >= 70 |
| PDFForensics | Score >= 70, no tampering |
| ImageForensics | Score >= 70, no AI/tampering |
| DocumentRisk | Risk band = LOW + no manual review flags |

---

**End of Documentation**  
For multi-format support strategy, see: `MULTI_FORMAT_SUPPORT.md`
