# Transaction Workflow Field Lifecycle

This document explains what fields are stored in the PostgreSQL database at different stages of transaction processing.

---

## Transaction Table Schema

### Fields Set When Transaction is **SUBMITTED** (via API)

When `POST /transactions` is called, these fields are populated:

#### ✅ Required Fields (Always Set)
```python
# Identity
transaction_id          # Unique transaction identifier from CSV
id                     # Auto-generated UUID (primary key)

# Jurisdictional
booking_jurisdiction   # e.g., "HK", "SG", "CH"
regulator             # e.g., "HKMA", "MAS", "FINMA"
booking_datetime      # Transaction timestamp (ISO 8601)
value_date           # Settlement date (YYYY-MM-DD)

# Financial
amount               # Transaction amount (float)
currency            # 3-letter currency code (USD, GBP, HKD)
channel             # Transaction channel (SWIFT, SEPA, RTGS)
product_type        # Product type (wire_transfer, fx_conversion)

# Parties
originator_name         # Sender name
originator_account      # Sender account number
originator_country      # Sender country (ISO 3166)
beneficiary_name        # Receiver name
beneficiary_account     # Receiver account number
beneficiary_country     # Receiver country (ISO 3166)

# Customer
customer_id            # Customer identifier
customer_type          # "individual", "corporate"
customer_risk_rating   # "Low", "Medium", "High"

# SWIFT
swift_mt              # SWIFT message type (MT103, MT202)

# Metadata
raw_data             # Full transaction payload as JSONB
created_at           # Record creation timestamp
updated_at           # Last update timestamp

# Initial Status
status               # Set to "PENDING"
processing_started_at   # NULL
processing_completed_at # NULL
```

#### 🟡 Optional Fields (May be NULL)
```python
customer_segment              # "retail", "corporate", "domiciliary_company"
customer_kyc_date            # Last KYC date
ordering_institution_bic     # SWIFT BIC
beneficiary_institution_bic  # SWIFT BIC
swift_f50_present           # Boolean flags
swift_f59_present
swift_f70_purpose           # Payment purpose text
swift_f71_charges           # Charge codes
pep_indicator              # PEP flag
sanctions_hit              # Sanctions screening result
high_risk_country          # Geographic risk flag
structuring_flag           # Structuring detection flag
```

---

## Fields Updated During **WORKFLOW EXECUTION**

### 1️⃣ When Workflow **STARTS** (in `workflows/transaction_workflow.py`)

```python
status = "PROCESSING"
processing_started_at = datetime.utcnow()  # Set to current timestamp
```

**Code Location:** `workflows/transaction_workflow.py` → `execute_transaction_workflow()`

```python
# Update transaction status to PROCESSING
transaction_record.status = TransactionStatus.PROCESSING
transaction_record.processing_started_at = datetime.utcnow()
db_session.commit()
```

---

### 2️⃣ When Workflow **COMPLETES** (in `agents/part1/persistor.py`)

```python
status = "COMPLETED"  # or "FAILED" if error
processing_completed_at = datetime.utcnow()  # Set to current timestamp
updated_at = datetime.utcnow()  # Updated automatically
```

**Code Location:** `agents/part1/persistor.py` → `PersistorAgent.execute()`

```python
# Update transaction status to COMPLETED
transaction_record.status = TransactionStatus.COMPLETED
transaction_record.processing_completed_at = datetime.utcnow()
db_session.commit()
```

---

## Additional Tables Created During Workflow

### ComplianceAnalysis Table

Created by `PersistorAgent` after all agents complete:

```python
id = UUID                          # Auto-generated
transaction_id = UUID              # Foreign key to transactions.id
compliance_score = Float           # 0.0 - 100.0
risk_band = RiskBand              # "LOW", "MEDIUM", "HIGH", "CRITICAL"
processing_time_seconds = Float    # Workflow execution time

# Agent Outputs (All JSONB)
applicable_rules = JSONB          # List of applicable AML rules
evidence_map = JSONB              # Evidence mapped to rules
control_test_results = JSONB      # Test results for each rule
pattern_detections = JSONB        # Detected patterns
bayesian_posterior = Float        # Bayesian risk score

# Analyst Output
compliance_summary = Text         # Executive summary
analyst_notes = Text              # Detailed analyst notes

created_at = DateTime             # Analysis timestamp
```

### Alerts Table

Created by `AlertComposerAgent` if risk threshold is exceeded:

```python
id = UUID                     # Auto-generated
alert_id = String             # Human-readable ID (ALR_xxx_timestamp)
source_type = String          # "transaction" or "document"
transaction_id = UUID         # Foreign key to transactions.id

# Alert Details
role = AlertRole             # "COMPLIANCE", "LEGAL", "FRONT"
severity = AlertSeverity     # "LOW", "MEDIUM", "HIGH", "CRITICAL"
alert_type = String          # "transaction_risk", "rule_violation"
title = String              # Alert title
description = Text          # Alert description

# Evidence
context = JSONB             # Risk context (score, features, etc.)
evidence = JSONB            # Supporting evidence (patterns, controls)

# Status Tracking
status = AlertStatus        # "PENDING", "ACKNOWLEDGED", "RESOLVED"
assigned_to = String        # User ID
acknowledged_by = String    # User ID
acknowledged_at = DateTime
resolved_by = String        # User ID
resolved_at = DateTime
resolution_notes = Text

# SLA Management
sla_deadline = DateTime     # Auto-calculated (48 hours from creation)
sla_breached = Boolean      # Auto-updated if deadline passed

created_at = DateTime
updated_at = DateTime
```

---

## Field Lifecycle Summary

### Status Field Progression

```
PENDING → PROCESSING → COMPLETED (success)
                    → FAILED (error)
```

### Timestamp Progression

```
1. created_at              → Set when transaction record created (API submission)
2. processing_started_at   → Set when workflow begins execution
3. processing_completed_at → Set when workflow finishes (success/failure)
4. updated_at             → Updated whenever record is modified
```

### Database State at Each Stage

| Stage | Status | processing_started_at | processing_completed_at | compliance_analysis | alerts |
|-------|--------|----------------------|-------------------------|---------------------|--------|
| **API Submit** | PENDING | NULL | NULL | Does not exist | Does not exist |
| **Workflow Start** | PROCESSING | 2025-11-01 10:00:00 | NULL | Does not exist | Does not exist |
| **Workflow Complete** | COMPLETED | 2025-11-01 10:00:00 | 2025-11-01 10:00:30 | Created with results | Created if risk > threshold |

---

## How to Query Workflow Results

### Check Transaction Status
```sql
SELECT 
    transaction_id,
    status,
    processing_started_at,
    processing_completed_at,
    EXTRACT(EPOCH FROM (processing_completed_at - processing_started_at)) as processing_seconds
FROM transactions
WHERE transaction_id = 'your-txn-id';
```

### Get Compliance Results
```sql
SELECT 
    t.transaction_id,
    ca.risk_band,
    ca.compliance_score,
    ca.processing_time_seconds,
    jsonb_array_length(ca.applicable_rules) as rule_count,
    jsonb_array_length(ca.control_test_results) as test_count
FROM transactions t
JOIN compliance_analysis ca ON t.id = ca.transaction_id
WHERE t.transaction_id = 'your-txn-id';
```

### Get Alerts
```sql
SELECT 
    a.alert_id,
    a.severity,
    a.alert_type,
    a.title,
    a.status,
    t.transaction_id
FROM alerts a
JOIN transactions t ON a.transaction_id = t.id
WHERE t.transaction_id = 'your-txn-id';
```

---

## Python Script to View Results

Use the provided script:

```bash
# View all recent transactions
python scripts/view_transaction_results.py

# View specific transaction details
python scripts/view_transaction_results.py <transaction_id>

# Example
python scripts/view_transaction_results.py ad66338d-b17f-47fc-a966-1b4395351b41
```

This script shows:
- ✅ Transaction basic info
- ✅ Compliance analysis (risk band, score, processing time)
- ✅ Applicable rules
- ✅ Control test results
- ✅ Pattern detections
- ✅ Analyst notes
- ✅ Alerts generated

---

## Workflow Execution Flow

```
1. API receives transaction → Creates Transaction record (status=PENDING)
   ↓
2. Celery worker picks up task → Updates status=PROCESSING, sets processing_started_at
   ↓
3. Workflow executes 13 agents:
   - ContextBuilder → Builds transaction context
   - ApplicabilityAgent → Finds applicable rules (stored in applicable_rules)
   - EvidenceMapper → Maps evidence to rules (stored in evidence_map)
   - ControlTestAgent → Tests controls (stored in control_test_results)
   - FeatureService → Extracts features
   - BayesianEngine → Calculates posterior probability
   - PatternDetector → Detects patterns (stored in pattern_detections)
   - DecisionFusion → Calculates final risk score
   - AnalystWriter → Generates notes (stored in analyst_notes)
   - AlertComposer → Creates alerts if needed
   - RemediationOrchestrator → Suggests remediation
   - Persistor → Saves all results to DB
   ↓
4. Persistor creates:
   - ComplianceAnalysis record (with all agent outputs)
   - Alert records (if risk threshold exceeded)
   - Updates Transaction (status=COMPLETED, processing_completed_at)
   ↓
5. Task completes → Returns result to Celery
```

---

## Example: Complete Transaction Lifecycle

```python
# 1. Initial State (after API submission)
Transaction {
    transaction_id: "ad66338d-b17f-47fc-a966-1b4395351b41",
    status: "PENDING",
    amount: 590012.92,
    currency: "HKD",
    booking_jurisdiction: "HK",
    regulator: "HKMA/SFC",
    processing_started_at: null,
    processing_completed_at: null,
    created_at: "2025-11-01 18:10:33"
}

# 2. During Processing
Transaction {
    ...same fields...
    status: "PROCESSING",
    processing_started_at: "2025-11-01 18:10:35",
    processing_completed_at: null
}

# 3. After Completion
Transaction {
    ...same fields...
    status: "COMPLETED",
    processing_started_at: "2025-11-01 18:10:35",
    processing_completed_at: "2025-11-01 18:11:05"
}

ComplianceAnalysis {
    transaction_id: <UUID of transaction>,
    compliance_score: 40.0,
    risk_band: "MEDIUM",
    processing_time_seconds: 30.5,
    applicable_rules: [...20 rules...],
    control_test_results: [...20 test results...],
    pattern_detections: {structuring: false, unusual_amount: true},
    analyst_notes: "Transaction flagged for high value...",
    created_at: "2025-11-01 18:11:05"
}

Alert {
    alert_id: "ALR_ad66338d_20251101181105",
    transaction_id: <UUID>,
    severity: "MEDIUM",
    alert_type: "transaction_risk",
    title: "Transaction Risk Alert: Medium",
    status: "PENDING",
    sla_deadline: "2025-11-03 18:11:05",
    created_at: "2025-11-01 18:11:05"
}
```
