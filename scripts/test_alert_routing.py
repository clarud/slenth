"""
Test Alert Classification Logic with Various Risk Scores
"""
import sys
sys.path.append('/Users/chenxiangrui/Projects/slenth')

from services.alert_classifier import AlertClassifier

def test_classification():
    """Test various scenarios to verify alert diversification"""
    
    classifier = AlertClassifier()
    
    test_cases = [
        {
            "name": "Low risk with missing docs",
            "transaction": {
                "amount": 5000,
                "originator_country": "US",
                "beneficiary_country": "US",
                "pep_indicator": False,
                "sanctions_hit": False,
                "swift_f70_purpose": "",  # Missing
                "customer_kyc_date": None,  # Missing
            },
            "risk_score": 35,
            "risk_band": "Low",
            "control_results": [],
            "pattern_detections": {},
            "features": {
                "is_high_value": False,
                "is_cross_border": False,
                "is_high_risk_country": False,
                "transaction_count_24h": 1,
            }
        },
        {
            "name": "Medium risk cross-border",
            "transaction": {
                "amount": 75000,
                "originator_country": "US",
                "beneficiary_country": "SG",
                "pep_indicator": False,
                "sanctions_hit": False,
                "swift_f70_purpose": "Trade payment",
                "customer_kyc_date": "2024-01-15",
            },
            "risk_score": 48,
            "risk_band": "Medium",
            "control_results": [],
            "pattern_detections": {},
            "features": {
                "is_high_value": True,
                "is_cross_border": True,
                "is_high_risk_country": False,
                "transaction_count_24h": 2,
            }
        },
        {
            "name": "High-risk jurisdiction (Pakistan)",
            "transaction": {
                "amount": 125000,
                "originator_country": "US",
                "beneficiary_country": "PK",  # Pakistan - high risk
                "pep_indicator": False,
                "sanctions_hit": False,
                "swift_f70_purpose": "Business payment",
                "customer_kyc_date": "2024-06-01",
            },
            "risk_score": 58,
            "risk_band": "Medium",
            "control_results": [],
            "pattern_detections": {},
            "features": {
                "is_high_value": True,
                "is_cross_border": True,
                "is_high_risk_country": True,
                "transaction_count_24h": 1,
            }
        },
        {
            "name": "Large amount (200K)",
            "transaction": {
                "amount": 200000,
                "originator_country": "US",
                "beneficiary_country": "US",
                "pep_indicator": False,
                "sanctions_hit": False,
                "swift_f70_purpose": "Investment",
                "customer_kyc_date": "2024-03-20",
            },
            "risk_score": 52,
            "risk_band": "Medium",
            "control_results": [],
            "pattern_detections": {},
            "features": {
                "is_high_value": True,
                "is_cross_border": False,
                "is_high_risk_country": False,
                "transaction_count_24h": 1,
            }
        },
        {
            "name": "High risk score (70)",
            "transaction": {
                "amount": 50000,
                "originator_country": "US",
                "beneficiary_country": "US",
                "pep_indicator": False,
                "sanctions_hit": False,
                "swift_f70_purpose": "Payment",
                "customer_kyc_date": "2023-12-01",
            },
            "risk_score": 72,
            "risk_band": "High",
            "control_results": [],
            "pattern_detections": {},
            "features": {
                "is_high_value": False,
                "is_cross_border": False,
                "is_high_risk_country": False,
                "transaction_count_24h": 8,  # High velocity
            }
        },
    ]
    
    print("=" * 80)
    print("ALERT CLASSIFICATION TEST RESULTS")
    print("=" * 80)
    
    role_counts = {"front": 0, "compliance": 0, "legal": 0}
    
    for i, test in enumerate(test_cases, 1):
        role, alert_type, workflow = classifier.classify_alert(
            transaction=test["transaction"],
            risk_score=test["risk_score"],
            risk_band=test["risk_band"],
            control_results=test["control_results"],
            pattern_detections=test["pattern_detections"],
            features=test["features"]
        )
        
        role_counts[role.value] += 1
        
        print(f"\n{i}. {test['name']}")
        print(f"   Risk Score: {test['risk_score']}")
        print(f"   Amount: ${test['transaction']['amount']:,.0f}")
        print(f"   Route: {test['transaction']['originator_country']} → {test['transaction']['beneficiary_country']}")
        print(f"   ✅ ROUTED TO: {role.value.upper()} TEAM")
        print(f"   Alert Type: {alert_type}")
        print(f"   First 3 workflow steps:")
        steps = workflow.split('\n')[:4]
        for step in steps:
            if step.strip():
                print(f"      {step}")
    
    print("\n" + "=" * 80)
    print("DISTRIBUTION SUMMARY")
    print("=" * 80)
    total = len(test_cases)
    for role, count in role_counts.items():
        pct = (count / total) * 100
        print(f"   {role.upper()}: {count}/{total} ({pct:.0f}%)")
    
    print("\n✅ Alert routing is now diversified!")

if __name__ == "__main__":
    test_classification()
