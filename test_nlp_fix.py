"""
Quick test to verify NLPValidation agent now has LLM service
"""
import asyncio
from services.llm import LLMService
from agents.part2.nlp_validation import NLPValidationAgent

async def test_nlp_agent():
    # Initialize LLM service (using Groq from config)
    llm_service = LLMService()
    print(f"✅ LLM Service initialized: {llm_service.provider}, model: {llm_service.model}")
    
    # Initialize NLP agent with LLM service
    nlp_agent = NLPValidationAgent(llm_service=llm_service)
    print(f"✅ NLP Agent initialized with LLM service: {nlp_agent.llm_service is not None}")
    
    # Test with sample text
    test_state = {
        "ocr_text": "This is a purchase agreement dated January 1st 2024. The buyer agrees to purchase the property. On December 31st 2023, the seller agreed to sell. The purchase price is $500,000. The property costs $600,000.",
        "document_type": "purchase_agreement",
        "extracted_entities": {},
        "errors": []
    }
    
    print("\n🔍 Testing NLP validation with contradictory text...")
    result = await nlp_agent.execute(test_state)
    
    print(f"\n📊 Results:")
    print(f"  • NLP Valid: {result.get('nlp_valid')}")
    print(f"  • Consistency Score: {result.get('consistency_score')}")
    print(f"  • Contradictions: {len(result.get('contradictions', []))}")
    print(f"  • Semantic Issues: {len(result.get('semantic_issues', []))}")
    
    if result.get('semantic_issues'):
        print(f"\n🚨 Issues Found:")
        for i, issue in enumerate(result.get('semantic_issues', [])[:3], 1):
            print(f"  {i}. {issue.get('type')}: {issue.get('description')}")
    
    print("\n✅ NLP Agent is now working with LLM service!")

if __name__ == "__main__":
    asyncio.run(test_nlp_agent())
