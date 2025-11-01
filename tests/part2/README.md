# Part 2 Tests

This folder contains test files for Part 2 (Document Corroboration) agents.

## 🧪 Test Files

### `test_simple.py`
**Standalone test script** - Tests the 3 implemented agents without full config dependencies.

**Features:**
- ✅ No database required
- ✅ Minimal environment setup
- ✅ Pure Python (works in virtual environment)
- ✅ EasyOCR integration
- ✅ Dilisense API testing

**Usage:**
```bash
# Using virtual environment Python
..\..\..\.venv312\Scripts\python.exe test_simple.py <path_to_pdf>

# Example
..\..\..\.venv312\Scripts\python.exe test_simple.py ..\..\Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf
```

**Tests:**
1. Document Intake - PDF validation
2. OCR - Text extraction with EasyOCR
3. Background Check - Dilisense screening

### `test_part2_agents.py`
**Full integration test** - Tests agents with complete config and dependencies.

**Requires:**
- Database connection
- Full `.env` configuration
- All services initialized

**Usage:**
```bash
python test_part2_agents.py <path_to_pdf>
```

## 📊 Test Output

Test results are saved as JSON files:
- `test_output_test_YYYYMMDD_HHMMSS.json`

These files contain:
- Validation results
- OCR extracted text length
- Screening results
- Risk scores
- Error messages

## 🎯 Running Tests

### Quick Test (Recommended)
```powershell
# Set encoding for emoji support
$env:PYTHONIOENCODING="utf-8"

# Navigate to tests folder
cd "tests\part2"

# Run test
..\..\..\..\.venv312\Scripts\python.exe test_simple.py ..\..\Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf
```

### Expected Output
```
✅ Valid: True
📄 Type: purchase_agreement
📊 Pages: 1
✅ Text Extracted: True
📝 Length: 1,928 chars
✅ Screened: 1 entities
🚨 PEP Found: YES
🚨 Risk Score: 40/100
```

## 📋 Test Checklist

### DocumentIntakeAgent
- [x] PDF validation works
- [x] File size limits enforced
- [x] Document type detection
- [x] Metadata extraction
- [ ] End-to-end with real documents

### OCRAgent
- [x] Text extraction from native PDFs
- [x] EasyOCR for scanned PDFs
- [x] Entity extraction (dates, amounts, names)
- [x] OCR output saved
- [ ] Performance benchmarks

### BackgroundCheckAgent
- [x] Dilisense API integration
- [x] Name extraction from text
- [x] PEP detection
- [x] Risk scoring
- [ ] Batch screening tests
- [ ] False positive handling

## 🔧 Troubleshooting

### EasyOCR Not Found
**Problem:** `ModuleNotFoundError: No module named 'easyocr'`

**Solution:**
```bash
# Install in virtual environment
..\..\..\.venv312\Scripts\python.exe -m pip install easyocr
```

### Wrong Python Interpreter
**Problem:** Tests use Anaconda Python instead of virtual environment

**Solution:** Always use the full path to virtual environment Python:
```bash
..\..\..\.venv312\Scripts\python.exe test_simple.py <pdf>
```

### Unicode Errors in PowerShell
**Problem:** `UnicodeEncodeError` with emoji characters

**Solution:**
```powershell
$env:PYTHONIOENCODING="utf-8"
```

## 📝 Adding New Tests

To add tests for new agents:

1. Update `test_simple.py` with new agent class
2. Add agent to test workflow
3. Update output display
4. Document expected results

---

**Last Updated:** November 1, 2025  
**Status:** 3/10 agents tested ✅
