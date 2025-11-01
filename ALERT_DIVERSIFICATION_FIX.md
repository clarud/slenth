# Alert Diversification Fix

## Problem Identified

All alerts were being routed to **FRONT OFFICE** with alert type **missing_documentation**. 

### Root Cause Analysis

1. **Pattern scores are empty**: `pattern_detections = {}`
   - PatternDetectorAgent runs but finds no patterns in single transactions
   - Historical transaction data not available for velocity/layering detection

2. **Transaction flags are mostly False**:
   - `pep_indicator: False`
   - `sanctions_hit: False`
   - `high_risk_country: None`

3. **Missing documentation is common**:
   - `swift_f70_purpose` often empty
   - `customer_kyc_date` often None

4. **Classification logic fell through to missing_docs**:
   - Original condition: `if missing_docs and risk_score >= 30`
   - This caught MOST transactions since risk_score is often 30-60

## Solution Implemented

### 1. Enhanced Pattern Score Inference

Added logic to infer pattern scores from transaction characteristics when PatternDetectorAgent returns empty:

```python
# Infer structuring from amount patterns
if 9000 < amount < 10000:  # Just below threshold
    structuring_score = 75
elif amount > 100000 and amount % 1000 == 0:  # Large round number
    structuring_score = 45

# Infer layering from cross-border + high amounts
if is_cross_border and amount > 200000:
    layering_score = 55
```

### 2. Risk-Score-Based Routing

Added **risk_score range checks** to diversify routing:

| Risk Range | Team | Alert Types |
|-----------|------|-------------|
| 80+ | LEGAL | Critical breaches, sanctions |
| 70-80 | COMPLIANCE | High risk patterns |
| 60-70 | COMPLIANCE | Structuring, layering, velocity |
| 50-60 | COMPLIANCE | High-risk jurisdictions, large transactions |
| 40-50 | FRONT/COMPLIANCE | Cross-border review, high-value |
| 30-40 | FRONT | Missing docs, documentation review |

### 3. New Alert Types Added

**Compliance Team**:
- `cross_border_review`: Cross-border with 35-55 risk score
- `large_transaction_review`: Amounts > 150K with 45-65 risk score
- `medium_risk_transaction`: Risk score 50-69 (default)

**Front Team**:
- `high_value_transaction`: Large amounts with 40-60 risk score
- `documentation_review`: Risk score 30-49 (default)

### 4. High-Risk Country Detection

Enhanced country detection with expanded list:

```python
high_risk_countries = {
    "AF", "AL", "BB", "BF", "KH", "KY", "CI", "HT", "IR", "IQ", "JM", "JO", 
    "KP", "LB", "LY", "ML", "MM", "NI", "PK", "PA", "PH", "RU", "SN", "SO",
    "SS", "SD", "SY", "TT", "TR", "UG", "AE", "VE", "YE", "ZW"
}
```

Now automatically detects high-risk jurisdictions from transaction country codes.

### 5. Tiered Priority Logic

Updated missing_documentation check to only apply to **low-moderate risk (30-50)**:

```python
# OLD
if missing_docs and risk_score >= 30:  # Caught everything!
    return FRONT, "missing_documentation"

# NEW  
if missing_docs and 30 <= risk_score < 50:  # Only low-moderate risk
    return FRONT, "missing_documentation"
```

Higher risk transactions (50+) now route through other checks first.

## Expected Outcome

With these changes, alerts should now distribute as:

- **LEGAL (10-15%)**: Sanctions, PEP, critical breaches
- **COMPLIANCE (40-50%)**: Pattern detection, high-risk jurisdictions, large amounts, cross-border
- **FRONT (35-50%)**: Missing docs, high-value with moderate risk, routine review

## Testing

To test diversification:

```bash
# Submit diverse test transactions
python scripts/test_diverse_alerts.py

# Wait for processing (30-60 seconds)
sleep 60

# Check alert distribution
python scripts/check_alert_distribution.py

# View specific transactions
python scripts/view_transaction_results.py <transaction_id>
```

## Key Insight

**The classification logic is deterministic and rule-based.** It doesn't use LLM for routing decisions. Alert diversification depends on:

1. **Transaction characteristics**: Amount, countries, cross-border flag
2. **Risk score**: Higher scores route to Compliance/Legal
3. **Available data**: Pattern scores, control results, features
4. **Missing documentation**: Only routes to Front for LOW-MODERATE risk

The fix ensures that **moderate and high risk transactions** get routed to Compliance/Legal **before** checking for missing documentation.
