# Alert Classification Logic - How Alerts Are Assigned

## Overview

The `AlertClassifier` service determines which team (Front/Compliance/Legal) should handle each alert based on transaction characteristics, risk patterns, and rule violations. This document explains how the classification works and how to ensure diverse alert routing.

---

## Classification Decision Tree (Priority Order)

The classifier evaluates conditions in **strict priority order**:

### 1. 🔴 LEGAL TEAM (Highest Priority)

**Sanctions Breach**
- **Trigger**: `sanctions_hit = True`
- **Alert Type**: `sanctions_breach`
- **Why Legal**: Direct regulatory violation, immediate reporting required
- **Remediation**: Freeze transaction, file SAR within 24h, escalate to regulator

**PEP High Risk**
- **Trigger**: `pep_indicator = True` AND `risk_score >= 70`
- **Alert Type**: `pep_high_risk`
- **Why Legal**: Corruption/bribery risk, reputational damage potential
- **Remediation**: Enhanced Due Diligence (EDD), senior approval, potential SAR

**Critical Rule Breach**
- **Trigger**: `critical_failures exist` AND `risk_score >= 80`
- **Alert Type**: `critical_rule_breach`
- **Why Legal**: Severe regulatory non-compliance
- **Remediation**: Suspend transaction, audit report, regulatory filing

---

### 2. 🟡 COMPLIANCE TEAM (Medium Priority)

**Structuring Pattern**
- **Trigger**: `structuring_score >= 70`
- **Alert Type**: `structuring_pattern`
- **How Detected**:
  - Multiple transactions just below reporting threshold ($9,000-$10,000)
  - Round amounts with high frequency (e.g., $50,000 x 5 times in 24h)
  - Pattern: `is_near_threshold AND transaction_count > 2`
- **Why Compliance**: Classic money laundering typology requiring SAR
- **Remediation**: Aggregate analysis, SAR filing, enhanced monitoring

**Layering Pattern**
- **Trigger**: `layering_score >= 70` OR `rapid_movement_score >= 70`
- **Alert Type**: `layering_pattern`
- **How Detected**:
  - Cross-border + high velocity: `is_cross_border AND transaction_count > 5`
  - Large cross-border amount: `is_cross_border AND amount > $100,000`
- **Why Compliance**: Complex money laundering scheme, requires tracing
- **Remediation**: Map transaction flow, identify beneficiaries, potential SAR

**Velocity Anomaly**
- **Trigger**: `velocity_anomaly_score >= 70`
- **Alert Type**: `velocity_anomaly`
- **How Detected**:
  - Very high frequency: `transaction_count_24h > 10` → score 85
  - High frequency: `transaction_count_24h > 5` → score 70
- **Why Compliance**: Unusual behavior requiring KYC update and monitoring
- **Remediation**: Update KYC, verify business purpose, enhanced monitoring

**High-Risk Jurisdiction**
- **Trigger**: `is_high_risk_country = True` AND `risk_score >= 50`
- **Alert Type**: `high_risk_jurisdiction`
- **High-Risk Countries** (58 countries):
  - FATF Grey/Black Lists
  - Sanctions targets: IR, KP, SY, RU, VE, MM, etc.
  - High corruption: AF, SO, YE, SD, SS, etc.
  - Tax havens with AML concerns: KY, PA, BB, etc.
- **Why Compliance**: Requires enhanced scrutiny for sanctions/embargoes
- **Remediation**: Verify FATF status, check sanctions, document rationale

**Multiple Control Failures**
- **Trigger**: `high_failures exist` AND `risk_score >= 60`
- **Alert Type**: `multiple_control_failures`
- **Why Compliance**: Cumulative risk requiring manual review
- **Remediation**: Request documentation, manual review, potential SAR

---

### 3. 🔵 FRONT TEAM (Lowest Priority)

**Missing Documentation**
- **Trigger**: `missing_docs exist` AND `risk_score >= 30`
- **Missing Docs Detection**:
  - No transaction purpose: `swift_f70_purpose is empty`
  - No KYC date: `customer_kyc_date is None`
  - No originator details (high-value): `is_high_value AND originator_name is empty`
- **Why Front**: Client relationship management, KYC updates
- **Remediation**: Contact client, request docs, 5-day deadline, escalate if not received

**High-Value Transaction**
- **Trigger**: `is_high_value = True` AND `risk_score < 50`
- **Definition**: `amount > $10,000`
- **Why Front**: Requires client verification but not suspicious
- **Remediation**: Contact Relationship Manager, verify transaction, document source of funds

**Cross-Border Transaction**
- **Trigger**: `is_cross_border = True` AND `risk_score >= 40`
- **Why Front**: Routine verification for international transfers
- **Remediation**: Verify beneficiary KYC, confirm legitimacy, document relationship

---

## How Pattern Scores Are Inferred

When the `PatternDetectorAgent` is not fully implemented (scores = 0), the classifier **infers scores from transaction characteristics**:

### Structuring Score Inference

```python
# High structuring (score 75):
- Amount just below threshold: $9,000-$10,000 or $4,500-$5,000
- Multiple transactions: transaction_count_24h > 2

# Moderate structuring (score 60):
- Round amount: amount % 1000 == 0
- High value: amount > $50,000
- Multiple transactions: transaction_count_24h > 1
```

### Layering Score Inference

```python
# High layering (score 80):
- Cross-border transaction
- High velocity: transaction_count_24h > 5

# Moderate layering (score 65):
- Cross-border transaction
- Large amount: amount > $100,000
```

### Velocity Anomaly Score Inference

```python
# Very high velocity (score 85):
- transaction_count_24h > 10

# High velocity (score 70):
- transaction_count_24h > 5
```

### PEP Indicator Inference

```python
# PEP likely (if risk_score >= 65):
- High-risk jurisdictions: RU, UA, BY, KZ, AZ, VE, ZW, NG
- Large amount: amount > $100,000
```

---

## Why All Alerts Were "missing_documentation"

**Root Cause**: Transaction data lacked diverse risk indicators:

1. **Empty Pattern Scores**: `pattern_detections = {}`
   - No structuring_score
   - No layering_score
   - No velocity_anomaly_score

2. **No Risk Flags**:
   - `pep_indicator = False`
   - `sanctions_hit = False`
   - `high_risk_country = None`

3. **Missing Documentation**:
   - `swift_f70_purpose` empty
   - `customer_kyc_date` None
   
4. **Classification Result**:
   - ❌ All Legal team conditions failed
   - ❌ All Compliance team conditions failed
   - ✅ **Missing docs condition matched** → FRONT OFFICE

---

## How to Diversify Alerts

### Option 1: Enhanced Transaction Simulator (Recommended)

Add diverse risk indicators to your CSV data:

```csv
transaction_id,amount,originator_country,beneficiary_country,pep_indicator,sanctions_hit,swift_f70_purpose,customer_kyc_date
TXN001,95000,RU,US,true,false,Trade Payment,2023-01-15
TXN002,9800,GB,CH,false,false,,
TXN003,150000,US,IR,false,true,Wire Transfer,2024-05-10
TXN004,50000,HK,KY,false,false,Investment,2022-03-20
```

### Option 2: Use Enhanced Inference (Current Implementation)

The classifier now automatically:
- ✅ Infers structuring from amount patterns
- ✅ Infers layering from cross-border velocity
- ✅ Infers velocity anomalies from frequency
- ✅ Detects 58 high-risk countries
- ✅ Infers PEP risk from jurisdictions + amounts

### Option 3: Implement Pattern Detector Agent

Create real pattern detection logic in `agents/part1/pattern_detector.py`:

```python
# Analyze transaction history to detect:
- Structuring patterns across multiple transactions
- Layering through account chains
- Velocity changes (sudden spikes)
- Round-trip circular transfers
```

---

## Testing Alert Diversity

### 1. Check Current Alert Distribution

```bash
python -c "
from db.database import SessionLocal
from db.models import Alert
from collections import Counter

db = SessionLocal()
alerts = db.query(Alert).all()

roles = Counter([a.role.value for a in alerts])
types = Counter([a.alert_type for a in alerts])

print('Alert Distribution by Role:')
for role, count in roles.items():
    print(f'  {role}: {count}')
    
print('\nAlert Distribution by Type:')
for alert_type, count in types.items():
    print(f'  {alert_type}: {count}')
"
```

### 2. Submit Diverse Test Transactions

```python
# LEGAL Team Alert - Sanctions
{
    "amount": 500000,
    "originator_country": "US",
    "beneficiary_country": "IR",  # Sanctioned country
    "swift_f70_purpose": "Trade",
    "customer_kyc_date": "2024-01-01"
}

# COMPLIANCE Team Alert - Structuring
{
    "amount": 9500,  # Just below threshold
    "originator_country": "GB",
    "beneficiary_country": "CH",
    "swift_f70_purpose": "Wire",
    "customer_kyc_date": "2024-01-01"
}
# Submit 3+ similar transactions in 24h

# FRONT Team Alert - Missing Docs
{
    "amount": 25000,
    "originator_country": "HK",
    "beneficiary_country": "SG",
    "swift_f70_purpose": "",  # Missing
    "customer_kyc_date": null  # Missing
}
```

### 3. View Results

```bash
python scripts/view_transaction_results.py <transaction_id>
```

Look for:
- 🧭 Front Team alerts (missing_documentation, high_value_transaction)
- 🕵️‍♀️ Compliance Team alerts (structuring_pattern, high_risk_jurisdiction)
- ⚖️ Legal Team alerts (sanctions_breach, pep_high_risk)

---

## Key Takeaways

1. **Priority Matters**: Legal > Compliance > Front
   - If a transaction matches multiple conditions, highest priority wins

2. **Risk Score Matters**: Even if patterns detected, low risk_score may not trigger alert
   - Legal: typically risk_score >= 70
   - Compliance: typically risk_score >= 50
   - Front: typically risk_score >= 30

3. **Inference Helps**: Enhanced classifier now infers patterns from transaction data
   - No need for full PatternDetector implementation
   - Analyzes amounts, frequencies, countries, cross-border flags

4. **58 High-Risk Countries**: Automatically flagged for compliance review
   - Based on FATF lists, sanctions, and AML concerns

5. **Testing**: Submit transactions with varied characteristics to see diverse alerts
   - Different countries (especially high-risk)
   - Different amounts (structuring range, high-value)
   - Different frequencies (velocity)
   - Missing vs complete documentation

---

## Next Steps

1. ✅ **Current**: Enhanced inference implemented
2. 🔄 **Test**: Submit new transactions with diverse characteristics
3. 🔄 **Verify**: Check alert distribution across teams
4. 📋 **Optional**: Implement full PatternDetectorAgent for real-time pattern analysis
5. 📋 **Optional**: Add WorldCheck API for real PEP/sanctions screening
