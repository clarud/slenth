# Multi-Format Document Support Strategy

## 📋 Overview

This document outlines the strategy for extending the document processing workflow to support multiple file formats beyond PDF.

---

## 🎯 Supported Formats

### **Currently Supported:**
- ✅ PDF (fully implemented)

### **Target Formats:**
- 📄 **Documents:** PDF, DOCX, DOC, TXT
- 🖼️ **Images:** JPG, JPEG, PNG, TIFF, BMP, WEBP
- 📊 **Spreadsheets:** XLSX, XLS (future)

---

## 🔧 Agent Modifications Required

### **1. DocumentIntakeAgent** 🔄 **NEEDS UPDATE**

**Current:** PDF-only validation  
**Target:** Multi-format support

**Changes Needed:**
```python
# Add format detection
def _detect_format(self, file_path: str) -> dict:
    extension = Path(file_path).suffix.lower()[1:]
    return self.SUPPORTED_FORMATS.get(extension, {})

# Add format-specific metadata extraction
def _extract_metadata_by_format(self, file_path: str, format_info: dict):
    if format_info["category"] == "document":
        if extension == "pdf":
            return self._extract_pdf_metadata(file_path)
        elif extension in ["docx", "doc"]:
            return self._extract_docx_metadata(file_path)
    elif format_info["category"] == "image":
        return self._extract_image_metadata(file_path)
```

**Dependencies:**
- PDF: `PyMuPDF` (already installed)
- DOCX: `python-docx` (need to add)
- Images: `Pillow` (already installed)

---

### **2. OCRAgent** 🔄 **NEEDS UPDATE**

**Current:** Extracts text from PDF pages  
**Target:** Support direct images and DOCX

**Changes Needed:**
```python
async def execute(self, state):
    file_format = state.get("file_format", "pdf")
    
    if file_format == "pdf":
        # Current PDF logic
        return await self._process_pdf(state)
    
    elif file_format in ["jpg", "jpeg", "png", "tiff"]:
        # Direct image OCR
        return await self._process_image(state)
    
    elif file_format == "docx":
        # Extract text from DOCX
        return await self._process_docx(state)
```

**Image OCR Strategy:**
```python
def _process_image(self, state):
    # Use EasyOCR directly on image file
    image_path = state["file_path"]
    result = self.reader.readtext(image_path)
    
    # Extract text
    text = " ".join([item[1] for item in result])
    
    # Run entity extraction
    entities = self._extract_entities(text)
    
    return {"ocr_text": text, "extracted_entities": entities, ...}
```

**DOCX Text Extraction:**
```python
def _process_docx(self, state):
    doc = docx.Document(state["file_path"])
    
    # Extract all paragraphs
    text = "\n".join([para.text for para in doc.paragraphs])
    
    # Extract from tables
    for table in doc.tables:
        for row in table.rows:
            text += "\n" + "\t".join([cell.text for cell in row.cells])
    
    return {"ocr_text": text, "has_text": True, ...}
```

---

### **3. ImageForensicsAgent** ✅ **ALREADY COMPATIBLE!**

**Current:** Extracts images from PDFs, then analyzes  
**Target:** Also accept direct image files

**Changes Needed (Minor):**
```python
async def execute(self, state):
    file_format = state.get("file_format", "pdf")
    
    if file_format == "pdf":
        # Current logic: extract images from PDF
        images = self._extract_images_from_pdf(file_path)
    
    elif file_format in ["jpg", "jpeg", "png", "tiff"]:
        # Direct image analysis
        with open(file_path, 'rb') as f:
            image_bytes = f.read()
        
        images = [{
            "page": 1,
            "index": 0,
            "image_bytes": image_bytes,
            "extension": file_format,
            "width": 0,  # Get from PIL
            "height": 0,
        }]
    
    # Rest of analysis is identical!
    for image_data in images:
        result = await self._analyze_single_image(image_data, ...)
```

**Key Insight:** All the pixel-level analysis (`_detect_tampering`, `_detect_ai_generated`, `_analyze_exif`) works on `image_bytes` — it doesn't care where they came from!

---

### **4. PDFForensicsAgent** ❌ **PDF-SPECIFIC**

**Current:** PDF metadata, xref tables, tampering  
**Target:** Create parallel agents for other formats

**Strategy:**
- Keep `PDFForensicsAgent` for PDFs
- Create `ImageForensicsAgent` for images (already done!)
- Create `DocxForensicsAgent` for DOCX (optional)

**DOCX Forensics Ideas:**
```python
class DocxForensicsAgent(Part2Agent):
    def execute(self, state):
        # Check document properties
        doc = docx.Document(file_path)
        
        # Extract metadata
        properties = doc.core_properties
        created = properties.created
        modified = properties.modified
        author = properties.author
        
        # Check for revisions
        has_track_changes = len(doc.element.xpath('//w:ins')) > 0
        
        # Check for embedded objects
        embedded_count = len(doc.inline_shapes)
        
        return {
            "docx_metadata": {...},
            "has_track_changes": has_track_changes,
            "embedded_objects": embedded_count,
            "integrity_score": ...
        }
```

---

### **5. Other Agents** ✅ **NO CHANGES NEEDED**

These agents work with **extracted text and entities only**:
- ✅ **BackgroundCheckAgent** - Text input only
- ✅ **FormatValidationAgent** - Text input only
- ✅ **NLPValidationAgent** - Text input only
- ✅ **CrossReferenceAgent** - Entities/text only
- ✅ **DocumentRiskAgent** - Aggregates scores only

---

## 📦 Required Dependencies

### **Already Installed:**
```
PyMuPDF==1.24.14      # PDF processing
Pillow==12.0.0         # Image processing
opencv-python==4.12.0  # Image analysis
ExifRead==3.5.1        # EXIF metadata
easyocr==1.7.2         # OCR
torch==2.9.0           # For EasyOCR
```

### **Need to Add:**
```bash
pip install python-docx==1.1.2  # DOCX processing
pip install openpyxl==3.1.5     # XLSX processing (future)
```

---

## 🔄 Workflow Routing Logic

**Key Idea:** Route documents through different agent paths based on format:

```python
async def process_document(file_path: str):
    # Step 1: Intake (determines format)
    state = {"file_path": file_path, ...}
    state = await DocumentIntakeAgent().execute(state)
    
    file_format = state["file_format"]  # "pdf", "jpg", "docx", etc.
    
    # Step 2: Text Extraction (format-aware)
    state = await OCRAgent().execute(state)
    
    # Step 3: Background Check (format-agnostic)
    state = await BackgroundCheckAgent().execute(state)
    
    # Step 4: Format Validation (format-agnostic)
    state = await FormatValidationAgent().execute(state)
    
    # Step 5: NLP Validation (format-agnostic)
    state = await NLPValidationAgent().execute(state)
    
    # Step 6: Format-specific forensics
    if file_format == "pdf":
        state = await PDFForensicsAgent().execute(state)
    elif file_format in ["jpg", "jpeg", "png", "tiff"]:
        # Skip PDF forensics, use image forensics only
        pass
    
    # Step 7: Image Forensics (works for all formats with images)
    state = await ImageForensicsAgent().execute(state)
    
    # Step 8-9: Rest of workflow (format-agnostic)
    state = await CrossReferenceAgent().execute(state)
    state = await DocumentRiskAgent().execute(state)
    
    return state
```

---

## ✅ Implementation Checklist

### **Phase 1: Image Support** (Easiest)
- [ ] Update `DocumentIntakeAgent` to accept JPG/PNG
- [ ] Update `OCRAgent` to process direct images
- [ ] Update `ImageForensicsAgent` to accept direct images
- [ ] Test with sample JPG/PNG files

### **Phase 2: DOCX Support** (Medium)
- [ ] Install `python-docx` dependency
- [ ] Add DOCX metadata extraction to `DocumentIntakeAgent`
- [ ] Add DOCX text extraction to `OCRAgent`
- [ ] (Optional) Create `DocxForensicsAgent`
- [ ] Test with sample DOCX files

### **Phase 3: Configuration** (Easy)
- [ ] Update `config.py` to allow multiple formats:
```python
document_allowed_types: List[str] = Field(
    default=["pdf", "jpg", "jpeg", "png", "docx"],
    env="DOCUMENT_ALLOWED_TYPES"
)
```

---

## 🎯 Benefits

1. **Flexibility** - Accept documents in any format
2. **Reusability** - Most agents don't need changes
3. **Consistency** - Same risk scoring across all formats
4. **Extensibility** - Easy to add new formats later

---

## 🚨 Important Notes

1. **OCR Quality:** Direct images may need preprocessing (deskew, contrast enhancement) for better OCR results

2. **Metadata Availability:** Images have less metadata than PDFs (no xref tables, no object structure)

3. **Forensics Depth:** PDF forensics is more comprehensive than image forensics

4. **Performance:** Processing large images is slower than PDFs

5. **Format Detection:** Always validate format based on **file content**, not just extension (use magic bytes)

---

## 📚 Next Steps

**For Your Use Case:**

1. **Quick Win:** Add JPG/PNG support first (images are common for scanned IDs)
   - Minimal changes needed
   - High impact

2. **Follow-Up:** Add DOCX support
   - Many contracts come as DOCX
   - Easy to implement

3. **Future:** Consider XLSX for bank statements/spreadsheets

**Would you like me to implement Phase 1 (Image Support) now?** 🚀
