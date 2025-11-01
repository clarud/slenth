# 🎯 Frontend Integration - Complete API Reference

## Updated API Endpoints Summary

### Base URL: `http://localhost:8000`

---

## 🆕 **NEW ENDPOINTS FOR FRONTEND**

### 1️⃣ **Upload Internal Rules Document**

**Purpose**: Batch upload internal compliance rules via JSON file

```http
POST /internal_rules/upload
Content-Type: multipart/form-data

file: internal_rules.json

Response: 201 Created
{
  "message": "Internal rules uploaded successfully",
  "filename": "internal_rules.json",
  "total_rules": 45,
  "created": 30,
  "updated": 10,
  "skipped": 5,
  "errors": null
}
```

**JSON Format Expected**:
```json
{
  "rules": [
    {
      "title": "Large Cash Transaction Reporting",
      "description": "Report cash transactions over threshold",
      "text": "All cash transactions exceeding CHF 100,000 must be reported within 24 hours...",
      "section": "AML_CASH_REPORTING",
      "obligation_type": "mandatory",
      "conditions": ["amount > 100000", "currency == CHF"],
      "expected_evidence": ["Transaction receipt", "Customer ID"],
      "penalty_level": "high",
      "effective_date": "2025-01-01",
      "version": "v1.0",
      "source": "Internal Policy Manual"
    }
  ]
}
```

---

### 2️⃣ **Trigger Part 2 Document Processing**

**Purpose**: Upload document and trigger synchronous agentic workflow

```http
POST /documents/upload
Content-Type: multipart/form-data

file: purchase_agreement.pdf

Response: 200 OK (after complete processing)
{
  "document_id": "DOC-20251102-103045",
  "filename": "purchase_agreement.pdf",
  "file_size": 2048576,
  "file_type": "application/pdf",
  "status": "completed",
  "uploaded_at": "2025-11-02T10:30:45Z",
  "risk_score": 42.3,
  "risk_level": "medium",
  "processing_completed_at": "2025-11-02T10:31:12Z",
  "processing_time_seconds": 27.5
}
```

**Note**: This endpoint blocks until processing completes (20-60 seconds typical)

---

### 3️⃣ **Get Unified Rules (Internal + External)**

**Purpose**: Fetch both internal policies and external regulatory circulars in one call

```http
GET /rules/all?page=1&page_size=100&rule_type=all

Query Parameters:
- regulator: HKMA | MAS | FINMA (filter external rules)
- jurisdiction: HK | SG | CH (filter external rules)
- section: Section name (filter internal rules)
- is_active: true | false (default: true)
- rule_type: internal | external | all (default: all)
- search: Search text in title and content
- page: Page number (default: 1)
- page_size: Results per page (default: 100)

Response:
{
  "total": 156,
  "internal_count": 45,
  "external_count": 111,
  "rules": [
    {
      "rule_id": "HKMA-3f8a7b2c9d1e",
      "rule_type": "external",
      "title": "AML/CFT Guidance Paper No. 15",
      "description": "Anti-Money Laundering and Counter-Terrorist Financing",
      "text": "Banks should implement a risk-based approach to AML/CFT...",
      "section": "Section 3.2 - Customer Due Diligence",
      "regulator": "HKMA",
      "jurisdiction": "HK",
      "source": "https://www.hkma.gov.hk/eng/...",
      "effective_date": "2024-01-01T00:00:00Z",
      "version": null,
      "is_active": true,
      "created_at": "2025-11-02T00:00:00Z",
      "metadata": {
        "published_date": "2024-01-01",
        "chunk_index": 0,
        "word_count": 1850
      }
    },
    {
      "rule_id": "RULE-001",
      "rule_type": "internal",
      "title": "EDD Required for High-Risk Jurisdictions",
      "description": "Enhanced Due Diligence must be performed for high-risk countries",
      "text": "For all transactions with counterparties in high-risk jurisdictions...",
      "section": "KYC/EDD",
      "regulator": null,
      "jurisdiction": null,
      "source": "Internal Policy Manual",
      "effective_date": "2024-01-01T00:00:00Z",
      "version": "v1.0",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z",
      "metadata": {
        "obligation_type": "mandatory",
        "penalty_level": "high",
        "conditions": ["high_risk_jurisdiction", "transaction_amount > 10000"],
        "expected_evidence": ["edd_report", "source_of_funds_verification"]
      }
    }
  ],
  "page": 1,
  "page_size": 100,
  "filters_applied": {
    "regulator": null,
    "jurisdiction": null,
    "section": null,
    "is_active": true,
    "rule_type": "all",
    "search": null
  }
}
```

---

### 4️⃣ **Get External Rules Only**

**Purpose**: Fetch only external regulatory circulars (HKMA, MAS, FINMA)

```http
GET /rules/external?regulator=HKMA&page=1&page_size=100

Query Parameters:
- regulator: HKMA | MAS | FINMA
- jurisdiction: HK | SG | CH
- search: Search text
- page: Page number
- page_size: Results per page

Response: Same format as /rules/all but only external rules
```

---

### 5️⃣ **Get Internal Rules Only**

**Purpose**: Fetch only internal compliance policies

```http
GET /rules/internal?section=AML_CASH_REPORTING&page=1&page_size=100

Query Parameters:
- section: Section name
- is_active: true | false
- search: Search text
- page: Page number
- page_size: Results per page

Response: Same format as /rules/all but only internal rules
```

---

## 🔄 **Frontend Polling Pattern**

### Transaction Status Polling (Part 1)

```javascript
// Poll every 10 seconds until completed
async function pollTransactionStatus(transactionId) {
  const interval = setInterval(async () => {
    const response = await fetch(`/transactions/${transactionId}/status`);
    const data = await response.json();
    
    console.log(`Status: ${data.status}, Progress: ${data.progress}%`);
    console.log(`Current Step: ${data.current_step}`);
    
    if (data.status === 'completed') {
      clearInterval(interval);
      // Fetch full compliance results
      const results = await fetch(`/transactions/${transactionId}/compliance`);
      const complianceData = await results.json();
      displayResults(complianceData);
    } else if (data.status === 'failed') {
      clearInterval(interval);
      displayError(data.error);
    }
  }, 10000); // 10 seconds
}

// Usage
const submitResponse = await fetch('/transactions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(transactionData)
});
const { transaction_id } = await submitResponse.json();
pollTransactionStatus(transaction_id);
```

---

## 📊 **Complete Frontend Integration Flow**

### Part 1: Transaction Monitoring

```mermaid
1. User submits transaction → POST /transactions
2. Receive task_id and transaction_id
3. Start polling → GET /transactions/{id}/status (every 10s)
4. Display progress bar and current step
5. When status = "completed" → GET /transactions/{id}/compliance
6. Display risk score, alerts, recommendations
7. If alerts generated → Fetch details from GET /alerts
8. If case created → Fetch details from GET /cases/{case_id}
```

### Part 2: Document Corroboration

```mermaid
1. User uploads document → POST /documents/upload (blocks 20-60s)
2. Response includes complete risk assessment
3. Display risk score immediately
4. Fetch detailed findings → GET /documents/{id}/findings
5. Display findings by category (format, content, image, background)
6. Offer PDF report download → GET /documents/{id}/report
7. Allow acknowledgment → POST /documents/{id}/acknowledge
```

### Rules Management

```mermaid
1. Upload internal rules → POST /internal_rules/upload
2. Fetch all rules for display → GET /rules/all
3. Filter by regulator/jurisdiction → GET /rules/all?regulator=HKMA
4. Search rules → GET /rules/all?search=cash+transaction
5. Create/update individual rule → POST /internal_rules
```

---

## 🎨 **Frontend UI Components Needed**

### 1. Transaction Monitoring Dashboard
- **Submit Transaction Form**
- **Status Indicator** (queued → processing → completed)
- **Progress Bar** with current step
- **Compliance Results Card**
  - Risk band (low/medium/high/critical)
  - Risk score (0-100)
  - Rules evaluated/violated
  - Patterns detected
  - Alerts generated
- **Alert List** (filtered by role)
- **Case Link** (if case created)

### 2. Document Upload & Analysis
- **File Upload Dropzone** (PDF, images)
- **Processing Spinner** (20-60s wait)
- **Risk Assessment Card**
  - Overall risk score
  - Risk breakdown (format, content, image, background)
  - Findings count by severity
- **Findings Tabs**
  - Format Issues
  - Content Analysis
  - Image Forensics
  - Background Checks
  - Cross-References
- **PDF Report Download Button**
- **Acknowledge/Approve Button**

### 3. Rules Management
- **Rules List View**
  - Filter by type (internal/external/all)
  - Filter by regulator (HKMA/MAS/FINMA)
  - Filter by jurisdiction
  - Search bar
- **Rule Detail Modal**
  - Full text display
  - Metadata (effective date, version, source)
  - Edit/deactivate buttons (internal rules only)
- **Upload Internal Rules Button** (JSON file)
- **Create New Rule Form** (internal rules)

### 4. Alerts Dashboard
- **Alert List** (filterable by role, severity, status)
- **SLA Indicator** (time remaining, breached warning)
- **Acknowledge Button**
- **Link to Source** (transaction or document)
- **Alert Statistics Cards**
  - Total pending
  - Critical/high count
  - SLA breached count
  - Average resolution time

### 5. Case Management
- **Case List** (filterable by status, type)
- **Case Detail View**
  - Linked alerts
  - Linked transactions/documents
  - Investigation notes
  - Timeline
- **Create Case Button**
- **Close/Resolve Case Button**

---

## 🔐 **Error Handling**

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Display results |
| 201 | Created | Display success message |
| 202 | Accepted | Start polling for status |
| 400 | Bad Request | Show validation errors |
| 404 | Not Found | Display "not found" message |
| 500 | Server Error | Show error, retry button |

### Example Error Response
```json
{
  "error": "Invalid transaction data",
  "message": "booking_jurisdiction is required",
  "path": "/transactions"
}
```

---

## 📝 **Sample Requests for Testing**

### 1. Submit Transaction
```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-TEST-001",
    "booking_jurisdiction": "HK",
    "regulator": "HKMA",
    "booking_datetime": "2025-11-02T10:30:00Z",
    "value_date": "2025-11-02T00:00:00Z",
    "amount": 150000,
    "currency": "USD",
    "channel": "SWIFT",
    "product_type": "Wire Transfer",
    "originator_name": "John Smith",
    "originator_account": "ACC123456",
    "originator_country": "HK",
    "beneficiary_name": "Jane Doe",
    "beneficiary_account": "ACC789012",
    "beneficiary_country": "SG",
    "customer_id": "CUST-001",
    "customer_risk_rating": "medium",
    "swift_mt": "MT103"
  }'
```

### 2. Upload Document
```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@/path/to/document.pdf"
```

### 3. Upload Internal Rules
```bash
curl -X POST http://localhost:8000/internal_rules/upload \
  -F "file=@internal_rules.json"
```

### 4. Fetch All Rules
```bash
curl -X GET "http://localhost:8000/rules/all?page=1&page_size=50&rule_type=all"
```

### 5. Fetch External Rules (HKMA only)
```bash
curl -X GET "http://localhost:8000/rules/external?regulator=HKMA&page=1&page_size=50"
```

### 6. Search Rules
```bash
curl -X GET "http://localhost:8000/rules/all?search=cash%20transaction"
```

---

## 🚀 **Quick Start for Frontend Developers**

1. **Start Backend Services**:
```bash
# Terminal 1: API Server
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery Worker (for Part 1 async processing)
celery -A worker.celery_app worker -l info -Q default -c 4
```

2. **Access API Documentation**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

3. **Test Endpoints**:
- Use Postman collection or Swagger UI
- Check `/health` endpoint first
- Test transaction submission and polling
- Test document upload
- Test rules fetching

4. **Integration Points**:
- Transaction monitoring: Poll `/transactions/{id}/status` every 10s
- Document processing: Single POST blocks until complete
- Rules display: Use `/rules/all` with filters
- Alerts: Fetch via `/alerts` with role filter
- Cases: Fetch via `/cases` with status filter

---

## 📊 **Data Models for Frontend**

### Transaction Status
```typescript
interface TransactionStatus {
  transaction_id: string;
  task_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number | null;  // 0-100
  current_step: string | null;
  error: string | null;
  completed_at: string | null;
}
```

### Compliance Analysis
```typescript
interface ComplianceAnalysis {
  transaction_id: string;
  risk_band: 'low' | 'medium' | 'high' | 'critical';
  risk_score: number;  // 0-100
  rules_evaluated: number;
  rules_violated: number;
  applicable_rules: string[];
  patterns_detected: string[];
  compliance_summary: string;
  recommendations: string[];
  alerts_generated: Alert[];
  processed_at: string;
  processing_time_seconds: number;
}
```

### Document Risk
```typescript
interface DocumentRisk {
  document_id: string;
  risk_score: number;  // 0-100
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  format_risk: number;
  content_risk: number;
  image_risk: number;
  background_check_risk: number;
  total_findings: number;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  key_issues: string[];
  recommendations: string[];
}
```

### Rule Item
```typescript
interface RuleItem {
  rule_id: string;
  rule_type: 'internal' | 'external';
  title: string;
  description: string | null;
  text: string;  // Truncated for list view
  section: string | null;
  regulator: string | null;  // HKMA, MAS, FINMA
  jurisdiction: string | null;  // HK, SG, CH
  source: string | null;
  effective_date: string | null;
  version: string | null;
  is_active: boolean;
  created_at: string;
  metadata: Record<string, any>;
}
```

---

## 🎯 **Success Metrics for Frontend**

- Transaction submission < 2s response time
- Status polling updates every 10s
- Document upload + processing < 60s total
- Rules list loads < 1s (100 items)
- Search results < 500ms
- Alerts dashboard loads < 1s
- Real-time SLA breach indicators
- PDF report downloads immediately

---

**Frontend Ready! 🚀 All endpoints are now available for integration.**
