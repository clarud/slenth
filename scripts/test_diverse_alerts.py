"""
Test Diverse Alerts

Submits transactions designed to trigger different alert types:
- Legal team: sanctions, PEP
- Compliance team: structuring, layering, high-risk jurisdiction
- Front team: missing docs, high-value, cross-border
"""

import requests
import time
from datetime import datetime

API_URL = "http://localhost:8000/transactions"

def submit_transaction(payload):
    """Submit a transaction and return task_id"""
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        task_id = result.get("task_id")
        print(f"✅ Submitted: {payload['transaction_id']} -> task_id={task_id}")
        return task_id
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# Test transactions to trigger different alert types

test_transactions = [
    # 1. LEGAL - Sanctions Hit (Iran)
    {
        "transaction_id": f"TEST_SANCTIONS_{int(time.time())}",
        "booking_jurisdiction": "HK",
        "regulator": "HKMA",
        "booking_datetime": datetime.utcnow().isoformat(),
        "value_date": datetime.utcnow().date().isoformat(),
        "amount": 500000,
        "currency": "USD",
        "channel": "SWIFT",
        "product_type": "wire_transfer",
        "originator_name": "Global Trading Ltd",
        "originator_account": "ACC001",
        "originator_country": "US",
        "beneficiary_name": "Tehran Industries",
        "beneficiary_account": "ACC999",
        "beneficiary_country": "IR",  # Iran - sanctioned
        "swift_mt": "MT103",
        "swift_f70_purpose": "Trade Payment",
        "customer_id": "CUST001",
        "customer_type": "corporate",
        "customer_risk_rating": "high",
        "customer_kyc_date": "2024-01-01"
    },
    
    # 2. LEGAL - PEP High Risk (Russia + Large Amount)
    {
        "transaction_id": f"TEST_PEP_{int(time.time())}",
        "booking_jurisdiction": "SG",
        "regulator": "MAS",
        "booking_datetime": datetime.utcnow().isoformat(),
        "value_date": datetime.utcnow().date().isoformat(),
        "amount": 850000,
        "currency": "EUR",
        "channel": "SWIFT",
        "product_type": "wire_transfer",
        "originator_name": "Oligarch Holdings",
        "originator_account": "ACC002",
        "originator_country": "RU",  # Russia - PEP risk
        "beneficiary_name": "Swiss Bank Account",
        "beneficiary_account": "ACC888",
        "beneficiary_country": "CH",
        "swift_mt": "MT103",
        "swift_f70_purpose": "Investment",
        "customer_id": "CUST002",
        "customer_type": "individual",
        "customer_risk_rating": "high",
        "customer_kyc_date": "2024-02-01",
        "pep_indicator": True
    },
    
    # 3. COMPLIANCE - High-Risk Jurisdiction (Pakistan)
    {
        "transaction_id": f"TEST_HIGHRISK_{int(time.time())}",
        "booking_jurisdiction": "HK",
        "regulator": "HKMA",
        "booking_datetime": datetime.utcnow().isoformat(),
        "value_date": datetime.utcnow().date().isoformat(),
        "amount": 250000,
        "currency": "USD",
        "channel": "SWIFT",
        "product_type": "wire_transfer",
        "originator_name": "ABC Trading",
        "originator_account": "ACC003",
        "originator_country": "GB",
        "beneficiary_name": "Karachi Enterprises",
        "beneficiary_account": "ACC777",
        "beneficiary_country": "PK",  # Pakistan - high-risk
        "swift_mt": "MT103",
        "swift_f70_purpose": "Trade Settlement",
        "customer_id": "CUST003",
        "customer_type": "corporate",
        "customer_risk_rating": "medium",
        "customer_kyc_date": "2024-03-01"
    },
    
    # 4. COMPLIANCE - Structuring Pattern (just below threshold)
    {
        "transaction_id": f"TEST_STRUCT_{int(time.time())}",
        "booking_jurisdiction": "US",
        "regulator": "FinCEN",
        "booking_datetime": datetime.utcnow().isoformat(),
        "value_date": datetime.utcnow().date().isoformat(),
        "amount": 9800,  # Just below $10k threshold
        "currency": "USD",
        "channel": "SWIFT",
        "product_type": "wire_transfer",
        "originator_name": "John Smith",
        "originator_account": "ACC004",
        "originator_country": "US",
        "beneficiary_name": "Cash Services Inc",
        "beneficiary_account": "ACC666",
        "beneficiary_country": "US",
        "swift_mt": "MT103",
        "swift_f70_purpose": "Wire Transfer",
        "customer_id": "CUST004",
        "customer_type": "individual",
        "customer_risk_rating": "medium",
        "customer_kyc_date": "2024-04-01"
    },
    
    # 5. COMPLIANCE - Layering (cross-border + high amount)
    {
        "transaction_id": f"TEST_LAYER_{int(time.time())}",
        "booking_jurisdiction": "HK",
        "regulator": "HKMA",
        "booking_datetime": datetime.utcnow().isoformat(),
        "value_date": datetime.utcnow().date().isoformat(),
        "amount": 350000,
        "currency": "USD",
        "channel": "SWIFT",
        "product_type": "wire_transfer",
        "originator_name": "Multi Corp",
        "originator_account": "ACC005",
        "originator_country": "HK",
        "beneficiary_name": "Offshore Holdings",
        "beneficiary_account": "ACC555",
        "beneficiary_country": "KY",  # Cayman Islands
        "swift_mt": "MT103",
        "swift_f70_purpose": "Fund Transfer",
        "customer_id": "CUST005",
        "customer_type": "corporate",
        "customer_risk_rating": "medium",
        "customer_kyc_date": "2024-05-01"
    },
    
    # 6. FRONT - Missing Documentation
    {
        "transaction_id": f"TEST_MISSING_{int(time.time())}",
        "booking_jurisdiction": "SG",
        "regulator": "MAS",
        "booking_datetime": datetime.utcnow().isoformat(),
        "value_date": datetime.utcnow().date().isoformat(),
        "amount": 45000,
        "currency": "SGD",
        "channel": "SWIFT",
        "product_type": "wire_transfer",
        "originator_name": "Local Business",
        "originator_account": "ACC006",
        "originator_country": "SG",
        "beneficiary_name": "Regional Partner",
        "beneficiary_account": "ACC444",
        "beneficiary_country": "MY",
        "swift_mt": "MT103",
        "swift_f70_purpose": "",  # MISSING
        "customer_id": "CUST006",
        "customer_type": "corporate",
        "customer_risk_rating": "low",
        # No customer_kyc_date - MISSING
    },
    
    # 7. FRONT - High-Value (but not suspicious)
    {
        "transaction_id": f"TEST_HIGHVAL_{int(time.time())}",
        "booking_jurisdiction": "HK",
        "regulator": "HKMA",
        "booking_datetime": datetime.utcnow().isoformat(),
        "value_date": datetime.utcnow().date().isoformat(),
        "amount": 75000,
        "currency": "HKD",
        "channel": "SWIFT",
        "product_type": "wire_transfer",
        "originator_name": "Tech Startup Ltd",
        "originator_account": "ACC007",
        "originator_country": "HK",
        "beneficiary_name": "Software Vendor",
        "beneficiary_account": "ACC333",
        "beneficiary_country": "US",
        "swift_mt": "MT103",
        "swift_f70_purpose": "Software License",
        "customer_id": "CUST007",
        "customer_type": "corporate",
        "customer_risk_rating": "low",
        "customer_kyc_date": "2024-06-01"
    },
    
    # 8. FRONT - Cross-Border
    {
        "transaction_id": f"TEST_XBORDER_{int(time.time())}",
        "booking_jurisdiction": "SG",
        "regulator": "MAS",
        "booking_datetime": datetime.utcnow().isoformat(),
        "value_date": datetime.utcnow().date().isoformat(),
        "amount": 120000,
        "currency": "EUR",
        "channel": "SWIFT",
        "product_type": "wire_transfer",
        "originator_name": "Export Company",
        "originator_account": "ACC008",
        "originator_country": "SG",
        "beneficiary_name": "Import Partner",
        "beneficiary_account": "ACC222",
        "beneficiary_country": "DE",
        "swift_mt": "MT103",
        "swift_f70_purpose": "Trade Payment",
        "customer_id": "CUST008",
        "customer_type": "corporate",
        "customer_risk_rating": "low",
        "customer_kyc_date": "2024-07-01"
    },
]

print("="*70)
print("SUBMITTING DIVERSE TEST TRANSACTIONS")
print("="*70)

submitted = []
for i, txn in enumerate(test_transactions, 1):
    print(f"\n[{i}/{len(test_transactions)}] {txn['transaction_id']}")
    print(f"    Amount: {txn['amount']} {txn['currency']}")
    print(f"    Route: {txn['originator_country']} → {txn['beneficiary_country']}")
    
    task_id = submit_transaction(txn)
    if task_id:
        submitted.append((txn['transaction_id'], task_id))
    
    time.sleep(1)  # Small delay between submissions

print("\n" + "="*70)
print(f"✅ Submitted {len(submitted)} test transactions")
print("="*70)
print("\nWait 30-60 seconds for processing, then check alerts:")
print("  python scripts/check_alert_distribution.py")
print("\nOr view specific transaction:")
print(f"  python scripts/view_transaction_results.py {submitted[0][0] if submitted else 'TRANSACTION_ID'}")
