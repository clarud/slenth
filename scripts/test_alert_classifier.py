"""
Test script for Alert Classification System

Tests the AlertClassifier to ensure proper role assignment and 
remediation workflow generation for various transaction scenarios.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.alert_classifier import AlertClassifier
from db.models import AlertRole


def test_sanctions_alert():
    """Test sanctions hit scenario."""
    print("\n" + "="*80)
    print("TEST 1: Sanctions Hit - Should route to LEGAL team")
    print("="*80)
    
    classifier = AlertClassifier()
    
    transaction = {
        "transaction_id": "TEST-001",
        "amount": 50000,
        "sanctions_hit": True,
        "pep_indicator": False
    }
    
    role, alert_type, workflow = classifier.classify_alert(
        transaction=transaction,
        risk_score=95.0,
        risk_band="Critical",
        control_results=[],
        pattern_detections={},
        features={"is_high_value": True, "is_cross_border": True}
    )
    
    print(f"✅ Role: {role.value.upper()} (Expected: LEGAL)")
    print(f"✅ Alert Type: {alert_type}")
    print(f"📋 Remediation Workflow:\n{workflow[:300]}...")
    
    assert role == AlertRole.LEGAL, f"Expected LEGAL, got {role}"
    assert alert_type == "sanctions_breach"
    print("\n✅ TEST PASSED")


def test_structuring_pattern():
    """Test structuring/smurfing pattern detection."""
    print("\n" + "="*80)
    print("TEST 2: Structuring Pattern - Should route to COMPLIANCE team")
    print("="*80)
    
    classifier = AlertClassifier()
    
    transaction = {
        "transaction_id": "TEST-002",
        "amount": 9500,
        "sanctions_hit": False,
        "pep_indicator": False
    }
    
    role, alert_type, workflow = classifier.classify_alert(
        transaction=transaction,
        risk_score=75.0,
        risk_band="High",
        control_results=[],
        pattern_detections={"structuring": 85},
        features={"potential_structuring": True}
    )
    
    print(f"✅ Role: {role.value.upper()} (Expected: COMPLIANCE)")
    print(f"✅ Alert Type: {alert_type}")
    print(f"📋 Remediation Workflow:\n{workflow[:300]}...")
    
    assert role == AlertRole.COMPLIANCE, f"Expected COMPLIANCE, got {role}"
    assert alert_type == "structuring_pattern"
    print("\n✅ TEST PASSED")


def test_high_value_transaction():
    """Test high value transaction - should route to FRONT team."""
    print("\n" + "="*80)
    print("TEST 3: High Value Transaction - Should route to FRONT team")
    print("="*80)
    
    classifier = AlertClassifier()
    
    transaction = {
        "transaction_id": "TEST-003",
        "amount": 150000,
        "sanctions_hit": False,
        "pep_indicator": False
    }
    
    role, alert_type, workflow = classifier.classify_alert(
        transaction=transaction,
        risk_score=35.0,
        risk_band="Low",
        control_results=[],
        pattern_detections={},
        features={"is_high_value": True, "is_cross_border": False}
    )
    
    print(f"✅ Role: {role.value.upper()} (Expected: FRONT)")
    print(f"✅ Alert Type: {alert_type}")
    print(f"📋 Remediation Workflow:\n{workflow[:300]}...")
    
    assert role == AlertRole.FRONT, f"Expected FRONT, got {role}"
    print("\n✅ TEST PASSED")


def test_pep_high_risk():
    """Test PEP with high risk score."""
    print("\n" + "="*80)
    print("TEST 4: PEP High Risk - Should route to LEGAL team")
    print("="*80)
    
    classifier = AlertClassifier()
    
    transaction = {
        "transaction_id": "TEST-004",
        "amount": 250000,
        "sanctions_hit": False,
        "pep_indicator": True
    }
    
    role, alert_type, workflow = classifier.classify_alert(
        transaction=transaction,
        risk_score=75.0,
        risk_band="High",
        control_results=[],
        pattern_detections={},
        features={"is_high_value": True}
    )
    
    print(f"✅ Role: {role.value.upper()} (Expected: LEGAL)")
    print(f"✅ Alert Type: {alert_type}")
    print(f"📋 Remediation Workflow:\n{workflow[:300]}...")
    
    assert role == AlertRole.LEGAL, f"Expected LEGAL, got {role}"
    assert alert_type == "pep_high_risk"
    print("\n✅ TEST PASSED")


def test_high_risk_jurisdiction():
    """Test transaction to high-risk jurisdiction."""
    print("\n" + "="*80)
    print("TEST 5: High Risk Jurisdiction - Should route to COMPLIANCE team")
    print("="*80)
    
    classifier = AlertClassifier()
    
    transaction = {
        "transaction_id": "TEST-005",
        "amount": 75000,
        "sanctions_hit": False,
        "pep_indicator": False
    }
    
    role, alert_type, workflow = classifier.classify_alert(
        transaction=transaction,
        risk_score=60.0,
        risk_band="Medium",
        control_results=[],
        pattern_detections={},
        features={"is_high_risk_country": True, "is_cross_border": True}
    )
    
    print(f"✅ Role: {role.value.upper()} (Expected: COMPLIANCE)")
    print(f"✅ Alert Type: {alert_type}")
    print(f"📋 Remediation Workflow:\n{workflow[:300]}...")
    
    assert role == AlertRole.COMPLIANCE, f"Expected COMPLIANCE, got {role}"
    assert alert_type == "high_risk_jurisdiction"
    print("\n✅ TEST PASSED")


def test_critical_control_failures():
    """Test critical regulatory rule breaches."""
    print("\n" + "="*80)
    print("TEST 6: Critical Control Failures - Should route to LEGAL team")
    print("="*80)
    
    classifier = AlertClassifier()
    
    transaction = {
        "transaction_id": "TEST-006",
        "amount": 100000,
        "sanctions_hit": False,
        "pep_indicator": False
    }
    
    control_results = [
        {
            "status": "fail",
            "severity": "critical",
            "rule_title": "FINMA AML Act Section 5",
            "compliance_score": 15
        },
        {
            "status": "fail",
            "severity": "critical",
            "rule_title": "MAS Notice 626 Section 8.2",
            "compliance_score": 20
        }
    ]
    
    role, alert_type, workflow = classifier.classify_alert(
        transaction=transaction,
        risk_score=85.0,
        risk_band="Critical",
        control_results=control_results,
        pattern_detections={},
        features={}
    )
    
    print(f"✅ Role: {role.value.upper()} (Expected: LEGAL)")
    print(f"✅ Alert Type: {alert_type}")
    print(f"📋 Remediation Workflow:\n{workflow[:300]}...")
    
    assert role == AlertRole.LEGAL, f"Expected LEGAL, got {role}"
    assert alert_type == "critical_rule_breach"
    print("\n✅ TEST PASSED")


def test_missing_documentation():
    """Test missing documentation scenario."""
    print("\n" + "="*80)
    print("TEST 7: Missing Documentation - Should route to FRONT team")
    print("="*80)
    
    classifier = AlertClassifier()
    
    transaction = {
        "transaction_id": "TEST-007",
        "amount": 50000,
        "sanctions_hit": False,
        "pep_indicator": False,
        "swift_f70_purpose": None,  # Missing purpose
        "originator_name": None  # Missing originator
    }
    
    role, alert_type, workflow = classifier.classify_alert(
        transaction=transaction,
        risk_score=35.0,
        risk_band="Low",
        control_results=[],
        pattern_detections={},
        features={"is_high_value": True}
    )
    
    print(f"✅ Role: {role.value.upper()} (Expected: FRONT)")
    print(f"✅ Alert Type: {alert_type}")
    print(f"📋 Remediation Workflow:\n{workflow[:300]}...")
    
    assert role == AlertRole.FRONT, f"Expected FRONT, got {role}"
    assert alert_type == "missing_documentation"
    assert "transaction purpose" in workflow
    print("\n✅ TEST PASSED")


def test_layering_pattern():
    """Test rapid fund movement / layering detection."""
    print("\n" + "="*80)
    print("TEST 8: Layering Pattern - Should route to COMPLIANCE team")
    print("="*80)
    
    classifier = AlertClassifier()
    
    transaction = {
        "transaction_id": "TEST-008",
        "amount": 80000,
        "sanctions_hit": False,
        "pep_indicator": False
    }
    
    role, alert_type, workflow = classifier.classify_alert(
        transaction=transaction,
        risk_score=70.0,
        risk_band="High",
        control_results=[],
        pattern_detections={"layering": 78, "rapid_movement": 75},
        features={}
    )
    
    print(f"✅ Role: {role.value.upper()} (Expected: COMPLIANCE)")
    print(f"✅ Alert Type: {alert_type}")
    print(f"📋 Remediation Workflow:\n{workflow[:300]}...")
    
    assert role == AlertRole.COMPLIANCE, f"Expected COMPLIANCE, got {role}"
    assert alert_type == "layering_pattern"
    print("\n✅ TEST PASSED")


def test_alert_description():
    """Test alert description generation."""
    print("\n" + "="*80)
    print("TEST 9: Alert Description Generation")
    print("="*80)
    
    classifier = AlertClassifier()
    
    control_results = [
        {
            "status": "fail",
            "rule_title": "ADGM AML Part 4.35",
            "rationale": "Missing transaction purpose",
            "severity": "medium"
        },
        {
            "status": "fail",
            "rule_title": "HKMA AML Guideline Section 3",
            "rationale": "Insufficient KYC documentation",
            "severity": "high"
        }
    ]
    
    description = classifier.get_alert_description(
        transaction_id="TEST-009",
        risk_score=55.0,
        risk_band="Medium",
        alert_type="multiple_control_failures",
        control_results=control_results
    )
    
    print(f"Generated Description:\n{description}")
    
    assert "TEST-009" in description
    assert "Medium" in description
    assert "55" in description
    assert "Control Test Failures" in description
    assert len(description) > 100
    print("\n✅ TEST PASSED")


def run_all_tests():
    """Run all alert classification tests."""
    print("\n" + "="*80)
    print("🧪 ALERT CLASSIFICATION SYSTEM - TEST SUITE")
    print("="*80)
    
    tests = [
        test_sanctions_alert,
        test_structuring_pattern,
        test_high_value_transaction,
        test_pep_high_risk,
        test_high_risk_jurisdiction,
        test_critical_control_failures,
        test_missing_documentation,
        test_layering_pattern,
        test_alert_description
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print(f"📊 TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*80)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"❌ {failed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
