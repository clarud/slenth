# Alert Classification System - Implementation Summary

## Overview

Implemented an intelligent alert classification system that automatically determines:
1. **Alert Role**: Which team should handle the alert (Front/Compliance/Legal)
2. **Alert Type**: Specific category of the alert
3. **Remediation Workflow**: Step-by-step actionable workflow unique to each alert type

---

## Architecture

### Components

1. **AlertClassifier Service** (`services/alert_classifier.py`)
   - 376 lines of intelligent classification logic
   - Rule-based decision tree with priority ordering
   - Generates detailed descriptions and remediation workflows

2. **Database Schema** (`db/models.py`)
   - Added `remediation_workflow` field to Alert model (TEXT type)
   - Existing fields: `role`, `severity`, `alert_type`, `description`
   - One-to-one mapping: Each alert has ONE unique remediation workflow

3. **PersistorAgent Integration** (`agents/part1/persistor.py`)
   - Updated to use AlertClassifier for intelligent alert creation
   - Generates rich alert data with context and evidence
   - Stores role, type, description, and remediation workflow

4. **Viewing Tool** (`scripts/view_transaction_results.py`)
   - Enhanced to display role icons (🧭 Front, 🕵️‍♀️ Compliance, ⚖️ Legal)
   - Shows first 8 steps of remediation workflow
   - Color-coded severity indicators

---

## Alert Classification Logic

### Priority Order (Highest to Lowest)

#### 1. **LEGAL TEAM** - Regulatory & Enforcement
```
sanctions_hit                → sanctions_breach
pep_indicator + risk ≥ 70    → pep_high_risk
critical_failures + risk ≥ 80 → critical_rule_breach
```

**Example Workflows:**
- **Sanctions Breach**: Freeze → Investigate → SAR within 24h → Voluntary disclosure
- **PEP High Risk**: EDD → Source of wealth → Senior approval → Enhanced monitoring
- **Critical Rule Breach**: Suspend → Audit report → Regulatory filing → Corrective action

#### 2. **COMPLIANCE TEAM** - Pattern Detection & Analysis
```
structuring_score ≥ 70       → structuring_pattern
layering_score ≥ 70          → layering_pattern
velocity_anomaly ≥ 70        → velocity_anomaly
high_risk_country + risk ≥ 50 → high_risk_jurisdiction
high_failures + risk ≥ 60    → multiple_control_failures
risk ≥ 70                    → high_risk_transaction
risk ≥ 50                    → medium_risk_transaction
```

**Example Workflows:**
- **Structuring Pattern**: Flag for SAR → Analyze linked accounts → Document pattern → File SAR
- **Layering Pattern**: Freeze → Map transaction flow → Identify beneficiaries → SAR if confirmed
- **High-Risk Jurisdiction**: Verify beneficiary → FATF check → Document purpose → Compliance approval

#### 3. **FRONT TEAM** - Client Relationship & Documentation
```
missing_docs + risk ≥ 30     → missing_documentation
is_high_value + risk < 50    → high_value_transaction
is_cross_border + risk ≥ 40  → cross_border_transaction
dormant_account              → dormant_account_reactivation
risk ≥ 30                    → documentation_review
risk < 30                    → routine_monitoring
```

**Example Workflows:**
- **Missing Documentation**: Contact client → Set deadline → Suspend if not provided → Escalate
- **High Value Transaction**: Verify with client → Document justification → Escalate if suspicious
- **Cross-Border**: Verify beneficiary KYC → Check restrictions → Document purpose

---

## Alert Types Catalog

### Legal Team Alerts

| Alert Type | Trigger | SLA | Remediation Steps |
|-----------|---------|-----|-------------------|
| `sanctions_breach` | sanctions_hit = True | 12h | 8 steps: Freeze → Investigate → SAR → Disclosure |
| `pep_high_risk` | PEP + risk ≥ 70 | 12-24h | 8 steps: EDD → Source verification → Approval → Monitoring |
| `critical_rule_breach` | Critical failures + risk ≥ 80 | 12-24h | 8 steps: Suspend → Audit → Regulatory report → Corrective action |

### Compliance Team Alerts

| Alert Type | Trigger | SLA | Remediation Steps |
|-----------|---------|-----|-------------------|
| `structuring_pattern` | Structuring score ≥ 70 | 24-48h | 9 steps: SAR prep → Link analysis → Pattern docs → Filing |
| `layering_pattern` | Layering/rapid movement ≥ 70 | 24h | 9 steps: Freeze → Flow mapping → Investigation → SAR |
| `velocity_anomaly` | Velocity score ≥ 70 | 48h | 8 steps: Calculate velocity → Profile review → Risk adjustment |
| `high_risk_jurisdiction` | High-risk country + risk ≥ 50 | 48h | 8 steps: Beneficiary check → FATF verification → Documentation |
| `multiple_control_failures` | High failures + risk ≥ 60 | 48h | 8 steps: Review failures → Request docs → Investigate → SAR if needed |
| `high_risk_transaction` | Risk score ≥ 70 | 24h | 8 steps: Manual review → Profile check → Risk assessment → SAR prep |
| `medium_risk_transaction` | Risk score ≥ 50 | 48h | 8 steps: Profile review → Documentation check → Escalate if needed |

### Front Team Alerts

| Alert Type | Trigger | SLA | Remediation Steps |
|-----------|---------|-----|-------------------|
| `missing_documentation` | Missing docs + risk ≥ 30 | 48-72h | 8 steps: Identify gaps → Contact client → Deadline → Escalate |
| `high_value_transaction` | High value + risk < 50 | 48-72h | 8 steps: Client contact → Justification → Documentation → Escalate |
| `cross_border_transaction` | Cross-border + risk ≥ 40 | 48h | 8 steps: KYC check → Country verification → Purpose docs |
| `dormant_account_reactivation` | Dormant > 12 months | 72h | 8 steps: Identity verify → Update KYC → Source of funds → Risk update |
| `documentation_review` | Risk ≥ 30 | 72h | 8 steps: Verify details → Check docs → Customer validation → Escalate |
| `routine_monitoring` | Risk < 30 | N/A | 6 steps: Verify profile → Check fields → Proceed if clear |

---

## Implementation Details

### AlertClassifier.classify_alert()

**Inputs:**
- `transaction`: Dict with transaction details
- `risk_score`: Float 0-100
- `risk_band`: String (Low/Medium/High/Critical)
- `control_results`: List of control test outcomes
- `pattern_detections`: Dict of pattern scores
- `features`: Dict of transaction features

**Outputs:**
- `role`: AlertRole enum (FRONT/COMPLIANCE/LEGAL)
- `alert_type`: String (e.g., "structuring_pattern")
- `remediation_workflow`: String with step-by-step instructions

**Logic Flow:**
```python
# Priority 1: Legal (Sanctions, PEP, Critical)
if sanctions_hit:
    return LEGAL, "sanctions_breach", workflow

# Priority 2: Compliance (Patterns, Analysis)
if structuring_score >= 70:
    return COMPLIANCE, "structuring_pattern", workflow

# Priority 3: Front (Documentation, Client Relations)
if missing_docs and risk >= 30:
    return FRONT, "missing_documentation", workflow

# Default: Risk-based routing
if risk >= 70: return COMPLIANCE, "high_risk_transaction", workflow
if risk >= 50: return COMPLIANCE, "medium_risk_transaction", workflow
if risk >= 30: return FRONT, "documentation_review", workflow
```

### AlertClassifier.get_alert_description()

Generates rich alert descriptions with:
- Transaction ID and risk score
- Special indicators (⚠️ CRITICAL, 🚨 AML ALERT)
- Failed control tests (up to 5 shown)
- Alert type classification

**Example Output:**
```
Transaction f7589c12-... flagged with Medium risk (score: 40.00)

📋 Control Test Failures (2):
1. ADGM AML Part 4.35 - Missing transaction purpose
2. HKMA AML Guideline Section 3 - Insufficient KYC documentation

🎯 Alert Type: Multiple Control Failures
```

---

## Database Schema

### Alert Model Fields

```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY,
    alert_id VARCHAR(100) UNIQUE NOT NULL,
    
    -- Classification (NEW INTELLIGENT FIELDS)
    role VARCHAR(20) NOT NULL,  -- 'front', 'compliance', 'legal'
    alert_type VARCHAR(100) NOT NULL,  -- Specific type
    remediation_workflow TEXT,  -- Step-by-step workflow
    
    -- Details
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Context & Evidence
    context JSONB,  -- Risk score, features, rules count
    evidence JSONB,  -- Patterns, control results
    
    -- Source
    source_type VARCHAR(20) NOT NULL,
    transaction_id UUID REFERENCES transactions(id),
    document_id UUID REFERENCES documents(id),
    
    -- Status & Assignment
    status VARCHAR(20) DEFAULT 'PENDING',
    assigned_to VARCHAR(100),
    
    -- SLA
    sla_deadline TIMESTAMP NOT NULL,
    sla_breached BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_alert_role_status ON alerts(role, status);
CREATE INDEX idx_alert_severity_status ON alerts(severity, status);
```

### Example Alert Record

```json
{
  "alert_id": "ALR_f7589c12-dccb-4ae1-8ad3-324db3316a56_20251101182851",
  "role": "compliance",
  "severity": "medium",
  "alert_type": "multiple_control_failures",
  "title": "Compliance Team Alert: Multiple Control Failures",
  "description": "Transaction f7589c12-... flagged with Medium risk (score: 40.00)\n\n📋 Control Test Failures (2):...",
  "remediation_workflow": "Multiple high-severity control failures:\n1. Review all failed controls: ADGM AML Part 4.35, HKMA AML Guideline Section 3\n2. Assess cumulative compliance risk\n3. Request missing documentation from Front Team\n4. Perform manual review of transaction legitimacy\n5. Cross-check with customer's historical transaction pattern\n6. If unjustified: Flag for SAR preparation\n7. Document investigation findings in case notes\n8. Update transaction risk score based on findings",
  "context": {
    "risk_score": 40.0,
    "risk_band": "Medium",
    "applicable_rules_count": 20,
    "features": {
      "amount": 1778002.31,
      "is_high_value": true,
      "is_cross_border": false
    }
  },
  "evidence": {
    "patterns": {
      "structuring": 0,
      "layering": 0,
      "velocity_anomaly": 0
    },
    "controls": [
      {
        "rule_id": "8151da37-21e0-4db1-a019-d7746466f4e4",
        "rule_title": "ADGM AML - Section 8.1.3",
        "status": "fail",
        "severity": "medium",
        "compliance_score": 20
      }
    ]
  },
  "status": "PENDING",
  "sla_deadline": "2025-11-03T18:28:51",
  "created_at": "2025-11-01T18:28:52"
}
```

---

## Testing

### Test Coverage

Created comprehensive test suite (`scripts/test_alert_classifier.py`):

✅ **9/9 Tests Passing**

1. Sanctions hit → Legal team
2. Structuring pattern → Compliance team
3. High value transaction → Front team
4. PEP high risk → Legal team
5. High-risk jurisdiction → Compliance team
6. Critical control failures → Legal team
7. Missing documentation → Front team
8. Layering pattern → Compliance team
9. Alert description generation

**Run tests:**
```bash
python scripts/test_alert_classifier.py
```

---

## Usage

### In Workflow (Automatic)

The PersistorAgent automatically classifies alerts:

```python
# agents/part1/persistor.py

from services.alert_classifier import AlertClassifier

classifier = AlertClassifier()

# Classify based on transaction characteristics
role, alert_type, remediation_workflow = classifier.classify_alert(
    transaction=state.get("transaction", {}),
    risk_score=risk_score,
    risk_band=risk_band_str,
    control_results=state.get("control_results", []),
    pattern_detections=state.get("pattern_scores", {}),
    features=state.get("features", {})
)

# Generate detailed description
description = classifier.get_alert_description(
    transaction_id=transaction_id,
    risk_score=risk_score,
    risk_band=risk_band_str,
    alert_type=alert_type,
    control_results=state.get("control_results", [])
)

# Create alert with intelligent classification
alert = Alert(
    alert_id=f"ALR_{transaction_id}_{timestamp}",
    role=role,  # FRONT/COMPLIANCE/LEGAL
    alert_type=alert_type,  # Specific type
    title=f"{role.value.title()} Team Alert: {alert_type.title()}",
    description=description,
    remediation_workflow=remediation_workflow,
    # ... other fields
)
```

### View Alerts

```bash
# View all transactions and alerts
python scripts/view_transaction_results.py

# View specific transaction with full alert details
python scripts/view_transaction_results.py <transaction_id>
```

**Output includes:**
- Role icon (🧭 Front, 🕵️‍♀️ Compliance, ⚖️ Legal)
- Severity indicator (🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low)
- Alert type and description
- First 8 steps of remediation workflow
- SLA deadline

---

## Migration

If the `remediation_workflow` column doesn't exist:

```bash
python scripts/migrate_add_remediation_workflow.py
```

This script:
- Checks if column exists
- Adds column if needed (TEXT type, nullable)
- Safe to run multiple times

---

## Benefits

### 1. **Intelligent Routing**
- Alerts automatically routed to correct team
- Reduces manual triage time
- Ensures expertise alignment

### 2. **Actionable Workflows**
- Step-by-step instructions unique to each alert
- No ambiguity about next actions
- Compliance-ready documentation

### 3. **Regulatory Compliance**
- Maps to real-world AML requirements
- Includes SAR filing triggers
- Documents decision rationale

### 4. **Scalability**
- Rule-based classification is fast
- No LLM calls needed for routing
- Consistent across all transactions

### 5. **Auditability**
- Every alert has traceable logic
- Remediation steps documented
- Evidence captured in context/evidence fields

---

## Real-World Examples

### Example 1: Structuring Pattern (Compliance Team)

**Trigger:** Transaction score: 75, structuring pattern detected (85% confidence)

**Alert Created:**
- **Role**: Compliance Team 🕵️‍♀️
- **Type**: `structuring_pattern`
- **Severity**: HIGH
- **SLA**: 24 hours

**Remediation Workflow:**
```
1. Flag for SAR preparation - High priority
2. Analyze all linked accounts for same customer/beneficial owner
3. Review transaction history for past 90 days
4. Identify total aggregate amount across structured transactions
5. Document pattern with transaction IDs and timestamps
6. Assess if pattern crosses regulatory reporting threshold
7. If confirmed: File SAR citing structuring pattern
8. Escalate to Legal if aggregate exceeds critical threshold
9. Implement enhanced monitoring on customer profile
```

### Example 2: Missing Documentation (Front Team)

**Trigger:** High-value transaction (£150,000), missing transaction purpose and originator details

**Alert Created:**
- **Role**: Front Team 🧭
- **Type**: `missing_documentation`
- **Severity**: MEDIUM
- **SLA**: 48 hours

**Remediation Workflow:**
```
1. Missing information: transaction purpose, originator details
2. Contact client to request missing documents
3. Notify client of regulatory requirements under AML regulations
4. Set deadline for document submission (typically 5 business days)
5. If documents not provided: Suspend account activity
6. Document all communications with client
7. If deadline breached: Escalate to Compliance for account review
8. Update KYC status once documents received and verified
```

### Example 3: Sanctions Breach (Legal Team)

**Trigger:** Transaction matches sanctioned entity

**Alert Created:**
- **Role**: Legal Team ⚖️
- **Type**: `sanctions_breach`
- **Severity**: CRITICAL
- **SLA**: 12 hours

**Remediation Workflow:**
```
1. Immediately freeze transaction
2. Escalate to Legal & Compliance Heads
3. Conduct full investigation and document findings
4. Prepare voluntary disclosure to regulatory authority (FINMA/MAS/FINCEN)
5. File Suspicious Activity Report (SAR) within 24 hours
6. Assess liability exposure and potential penalties
7. Review all related accounts and transactions for same beneficiary
8. Implement remediation measures to prevent recurrence
```

---

## Future Enhancements

### Potential Improvements

1. **Dynamic Workflow Updates**
   - Adjust workflows based on regulatory changes
   - A/B test different remediation approaches
   - Learn from resolution outcomes

2. **Machine Learning Integration**
   - Train model on historical alert outcomes
   - Predict likelihood of SAR filing
   - Optimize alert routing accuracy

3. **SLA Automation**
   - Auto-escalate approaching deadlines
   - Send notifications to assigned team members
   - Track team performance metrics

4. **Workflow Execution Tracking**
   - Checklist UI for remediation steps
   - Track completion percentage
   - Capture evidence at each step

5. **Cross-Part Integration**
   - Merge Part 1 (transaction) and Part 2 (document) alerts
   - Joint alerts for contradictory evidence
   - Unified case management

---

## Summary

✅ **Implemented**
- Intelligent alert classification (376 lines)
- 15+ unique alert types with specific workflows
- 3-tier routing (Front/Compliance/Legal)
- Comprehensive test suite (9/9 passing)
- Database integration
- Viewing tools with role icons

✅ **Database Schema**
- Added `remediation_workflow` field
- One-to-one mapping per alert
- Rich context and evidence storage

✅ **Real-World Compliance**
- Aligned with FINMA/MAS/HKMA/OFAC requirements
- SAR filing triggers embedded
- Enhanced Due Diligence workflows
- Audit trail documentation

**Result:** Every alert generated by the workflow now has:
1. **Assigned Team** (Front/Compliance/Legal)
2. **Specific Type** (structuring_pattern, pep_high_risk, etc.)
3. **Unique Remediation Workflow** (8-9 actionable steps)
4. **Rich Context** (risk scores, patterns, evidence)
5. **Clear SLA** (12h to 72h based on severity)

---

**Generated:** 2025-11-02  
**Component:** Alert Classification System  
**Status:** Production-Ready ✅
