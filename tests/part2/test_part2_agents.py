"""
Test script for Part 2 agents (DocumentIntake, OCR, BackgroundCheck)

Usage:
    python test_part2_agents.py path/to/test.pdf
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from agents.part2.document_intake import DocumentIntakeAgent
from agents.part2.ocr import OCRAgent
from agents.part2.background_check import BackgroundCheckAgent


async def test_agents(pdf_path: str):
    """
    Test the three implemented agents on a PDF file.
    
    Args:
        pdf_path: Path to PDF file to test
    """
    print("=" * 80)
    print("🧪 TESTING PART 2 AGENTS")
    print("=" * 80)
    
    # Check if file exists
    if not Path(pdf_path).exists():
        print(f"❌ ERROR: File not found: {pdf_path}")
        return
    
    print(f"\n📄 Testing with file: {pdf_path}")
    print(f"📁 File size: {Path(pdf_path).stat().st_size / 1024:.2f} KB")
    print()
    
    # Initialize state
    state = {
        "file_path": pdf_path,
        "document_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "document": {
            "document_type": "purchase_agreement"
        },
        "errors": []
    }
    
    # ========================================
    # AGENT 1: Document Intake
    # ========================================
    print("=" * 80)
    print("1️⃣  DOCUMENT INTAKE AGENT")
    print("=" * 80)
    
    intake_agent = DocumentIntakeAgent()
    try:
        state = await intake_agent.execute(state)
        
        print(f"✅ File Valid: {state.get('file_valid')}")
        print(f"📝 Document Type: {state.get('document_type')}")
        
        metadata = state.get('metadata', {})
        print(f"\n📊 Metadata:")
        print(f"  - Pages: {metadata.get('page_count', 'N/A')}")
        print(f"  - File Name: {metadata.get('file_name', 'N/A')}")
        print(f"  - Has Images: {metadata.get('has_images', 'N/A')}")
        print(f"  - Is Encrypted: {metadata.get('is_encrypted', 'N/A')}")
        if metadata.get('title'):
            print(f"  - Title: {metadata.get('title')}")
        if metadata.get('author'):
            print(f"  - Author: {metadata.get('author')}")
        
        if state.get('errors'):
            print(f"\n⚠️  Errors: {', '.join(state.get('errors'))}")
        
        if not state.get('file_valid'):
            print("\n❌ File validation failed. Stopping test.")
            return
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # ========================================
    # AGENT 2: OCR
    # ========================================
    print("=" * 80)
    print("2️⃣  OCR AGENT")
    print("=" * 80)
    
    ocr_agent = OCRAgent()
    try:
        state = await ocr_agent.execute(state)
        
        ocr_text = state.get('ocr_text', '')
        text_length = len(ocr_text)
        
        print(f"✅ Text Extracted: {state.get('has_text')}")
        print(f"📝 Text Length: {text_length:,} characters")
        print(f"📄 Pages Processed: {len(state.get('page_texts', []))}")
        
        # Show first 500 characters of extracted text
        if ocr_text:
            print(f"\n📖 Text Preview (first 500 chars):")
            print("-" * 80)
            print(ocr_text[:500])
            if text_length > 500:
                print(f"... ({text_length - 500:,} more characters)")
            print("-" * 80)
        
        # Show extracted entities
        entities = state.get('extracted_entities', {})
        print(f"\n🔍 Extracted Entities:")
        print(f"  - Dates: {len(entities.get('dates', []))} found")
        if entities.get('dates'):
            print(f"    Examples: {', '.join(entities['dates'][:3])}")
        
        print(f"  - Amounts: {len(entities.get('amounts', []))} found")
        if entities.get('amounts'):
            print(f"    Examples: {', '.join(entities['amounts'][:3])}")
        
        print(f"  - Emails: {len(entities.get('emails', []))} found")
        if entities.get('emails'):
            print(f"    Examples: {', '.join(entities['emails'][:3])}")
        
        print(f"  - Phone Numbers: {len(entities.get('phone_numbers', []))} found")
        if entities.get('phone_numbers'):
            print(f"    Examples: {', '.join(entities['phone_numbers'][:3])}")
        
        print(f"  - Potential Names: {len(entities.get('potential_names', []))} found")
        if entities.get('potential_names'):
            print(f"    Examples: {', '.join(entities['potential_names'][:3])}")
        
        if state.get('ocr_output_path'):
            print(f"\n💾 OCR output saved to: {state['ocr_output_path']}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # ========================================
    # AGENT 3: Background Check
    # ========================================
    print("=" * 80)
    print("3️⃣  BACKGROUND CHECK AGENT (Dilisense API)")
    print("=" * 80)
    
    background_agent = BackgroundCheckAgent()
    try:
        state = await background_agent.execute(state)
        
        screened = state.get('screened_entities', [])
        results = state.get('background_check_results', [])
        
        print(f"✅ Entities Screened: {len(screened)}")
        if screened:
            print(f"   Names: {', '.join(screened)}")
        
        print(f"\n🚨 Findings:")
        print(f"  - PEP Found: {'⚠️  YES' if state.get('pep_found') else '✅ No'}")
        print(f"  - Sanctions Found: {'🚨 YES' if state.get('sanctions_found') else '✅ No'}")
        print(f"  - Background Risk Score: {state.get('background_risk_score', 0)}/100")
        
        # Show detailed results for each screened entity
        if results:
            print(f"\n📊 Detailed Screening Results:")
            for i, result in enumerate(results, 1):
                print(f"\n  {i}. {result.get('name', 'Unknown')}")
                print(f"     - Match Status: {result.get('match_status', 'N/A')}")
                print(f"     - Risk Level: {result.get('risk_level', 'N/A')}")
                print(f"     - Total Hits: {result.get('total_hits', 0)}")
                print(f"     - Is PEP: {'Yes' if result.get('is_pep') else 'No'}")
                print(f"     - Is Sanctioned: {'Yes' if result.get('is_sanctioned') else 'No'}")
                
                # Show matches if any
                if result.get('matches'):
                    print(f"     - Matches: {len(result['matches'])} record(s)")
                    for match in result['matches'][:2]:  # Show first 2 matches
                        print(f"       • {match.get('source_type', 'N/A')} - {match.get('source_id', 'N/A')}")
        
        if state.get('background_check_skipped'):
            print("\n⚠️  Background check was skipped (disabled in config)")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # ========================================
    # SUMMARY
    # ========================================
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ Agents Executed: 3/3")
    print(f"   1. DocumentIntake: {'✅ Pass' if state.get('file_valid') else '❌ Fail'}")
    print(f"   2. OCR: {'✅ Pass' if state.get('has_text') else '⚠️  Limited text'}")
    print(f"   3. BackgroundCheck: {'✅ Pass' if state.get('background_check_executed') else '❌ Fail'}")
    
    print(f"\n📈 Overall Risk Assessment:")
    print(f"   - Background Risk: {state.get('background_risk_score', 0)}/100")
    print(f"   - PEP Risk: {'HIGH' if state.get('pep_found') else 'LOW'}")
    print(f"   - Sanctions Risk: {'CRITICAL' if state.get('sanctions_found') else 'LOW'}")
    
    total_errors = len(state.get('errors', []))
    if total_errors > 0:
        print(f"\n⚠️  Total Errors: {total_errors}")
        for error in state.get('errors', []):
            print(f"   - {error}")
    else:
        print(f"\n✅ No errors encountered")
    
    # Save full state to JSON
    output_file = f"test_output_{state['document_id']}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        # Convert state to JSON-serializable format
        json_state = {
            k: v for k, v in state.items() 
            if k not in ['ocr_text', 'page_texts']  # Exclude large text fields
        }
        json_state['ocr_text_length'] = len(state.get('ocr_text', ''))
        json_state['page_count'] = len(state.get('page_texts', []))
        json.dump(json_state, f, indent=2, default=str)
    
    print(f"\n💾 Full results saved to: {output_file}")
    print()
    print("=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_part2_agents.py <path_to_pdf>")
        print("\nExample:")
        print("  python test_part2_agents.py Swiss_Home_Purchase_Agreement.pdf")
        print("  python test_part2_agents.py data/test_document.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Run the async test
    asyncio.run(test_agents(pdf_path))


if __name__ == "__main__":
    main()
