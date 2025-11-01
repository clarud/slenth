"""
Test NLPValidationAgent - Semantic validation
Tests basic validation without LLM (fallback mode)
"""
import asyncio
import sys
import os
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set minimal env vars
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5432/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-key')

# Import agent directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "nlp_validation",
    str(project_root / "agents" / "part2" / "nlp_validation.py")
)
nlp_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nlp_module)
NLPValidationAgent = nlp_module.NLPValidationAgent


async def test_nlp_validation():
    """Test NLP validation with various scenarios"""
    
    print("=" * 80)
    print("🧪 NLPValidationAgent Tests")
    print("=" * 80)
    print()
    
    # Test 1: Good document
    print("Test 1: Valid Purchase Agreement")
    print("-" * 80)
    
    good_text = """
    Purchase Agreement
    
    This agreement is made on January 15, 2024, between:
    Buyer: John Smith
    Seller: Jane Doe
    
    Property: 123 Main Street, Zurich
    Purchase Price: CHF 1,000,000
    
    Both parties agree to the terms stated herein.
    Signed on January 15, 2024.
    """
    
    state = {
        "ocr_text": good_text,
        "document_type": "purchase_agreement",
        "extracted_entities": {
            "dates": ["January 15, 2024"],
            "amounts": ["CHF 1,000,000"],
            "potential_names": ["John Smith", "Jane Doe"]
        },
        "errors": []
    }
    
    agent = NLPValidationAgent(llm_service=None)  # No LLM for testing
    result = await agent.execute(state)
    
    print(f"✅ NLP Valid: {result['nlp_valid']}")
    print(f"📊 Consistency Score: {result['consistency_score']}/100")
    print(f"❌ Issues Found: {len(result['semantic_issues'])}")
    
    if result['semantic_issues']:
        for issue in result['semantic_issues']:
            print(f"   • [{issue['severity'].upper()}] {issue['type']}: {issue['description']}")
    else:
        print("   ✅ No semantic issues detected")
    print()
    
    # Test 2: Document with placeholders (should fail)
    print("Test 2: Document with Placeholders (Should Fail)")
    print("-" * 80)
    
    bad_text = """
    Purchase Agreement
    
    This agreement is made on [TBD], between:
    Buyer: XXX
    Seller: To Be Determined
    
    Property: [Placeholder]
    Purchase Price: TBD
    
    Lorem ipsum dolor sit amet...
    """
    
    state2 = {
        "ocr_text": bad_text,
        "document_type": "purchase_agreement",
        "extracted_entities": {
            "dates": [],
            "amounts": [],
            "potential_names": []
        },
        "errors": []
    }
    
    result2 = await agent.execute(state2)
    
    print(f"✅ NLP Valid: {result2['nlp_valid']}")
    print(f"📊 Consistency Score: {result2['consistency_score']}/100")
    print(f"❌ Issues Found: {len(result2['semantic_issues'])}")
    
    if result2['semantic_issues']:
        for issue in result2['semantic_issues']:
            print(f"   • [{issue['severity'].upper()}] {issue['type']}: {issue['description']}")
    print()
    
    # Test 3: Document with contradictions
    print("Test 3: Document with Contradictions")
    print("-" * 80)
    
    contradictory_text = """
    Contract Agreement
    
    The parties agree to the following terms.
    However, the parties disagree on the payment schedule.
    
    This contract is valid for one year.
    Note: This contract is invalid after 6 months.
    
    The buyer accepts all terms.
    The buyer rejects the delivery conditions.
    """
    
    state3 = {
        "ocr_text": contradictory_text,
        "document_type": "contract",
        "extracted_entities": {
            "dates": [],
            "amounts": [],
            "potential_names": []
        },
        "errors": []
    }
    
    result3 = await agent.execute(state3)
    
    print(f"✅ NLP Valid: {result3['nlp_valid']}")
    print(f"📊 Consistency Score: {result3['consistency_score']}/100")
    print(f"❌ Issues Found: {len(result3['semantic_issues'])}")
    
    if result3['semantic_issues']:
        for issue in result3['semantic_issues']:
            print(f"   • [{issue['severity'].upper()}] {issue['type']}: {issue['description']}")
    print()
    
    # Test 4: Insufficient text
    print("Test 4: Insufficient Text")
    print("-" * 80)
    
    short_text = "Short document."
    
    state4 = {
        "ocr_text": short_text,
        "document_type": "invoice",
        "extracted_entities": {},
        "errors": []
    }
    
    result4 = await agent.execute(state4)
    
    print(f"✅ NLP Valid: {result4['nlp_valid']}")
    print(f"📊 Consistency Score: {result4['consistency_score']}/100")
    print(f"❌ Issues Found: {len(result4['semantic_issues'])}")
    
    if result4['semantic_issues']:
        for issue in result4['semantic_issues']:
            print(f"   • [{issue['severity'].upper()}] {issue['type']}: {issue['description']}")
    print()
    
    # Summary
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print()
    print(f"Test 1 (Valid): {'✅ PASS' if result['nlp_valid'] else '❌ FAIL'} - Score: {result['consistency_score']}")
    print(f"Test 2 (Placeholders): {'✅ PASS' if not result2['nlp_valid'] else '❌ FAIL'} - Score: {result2['consistency_score']}")
    print(f"Test 3 (Contradictions): {'✅ PASS' if not result3['nlp_valid'] else '❌ FAIL'} - Score: {result3['consistency_score']}")
    print(f"Test 4 (Insufficient): {'✅ PASS' if not result4['nlp_valid'] else '❌ FAIL'} - Score: {result4['consistency_score']}")
    print()
    print("✅ All tests completed!")
    print()
    print("💡 Note: These tests use basic fallback validation.")
    print("   With LLM service, semantic analysis would be much more powerful.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_nlp_validation())
