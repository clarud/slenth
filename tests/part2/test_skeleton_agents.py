"""
Test Skeleton Agents: Evidence Storekeeper and Correlation
Demonstrates functionality without Part 1 database integration
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed")

# Set env vars
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5432/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import agents using importlib
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load skeleton agents
evidence_module = load_module("evidence_storekeeper", project_root / "agents" / "part2" / "evidence_storekeeper.py")
EvidenceStorekeeperAgent = evidence_module.EvidenceStorekeeperAgent

correlation_module = load_module("correlation", project_root / "agents" / "part2" / "correlation.py")
CorrelationAgent = correlation_module.CorrelationAgent


async def test_skeleton_agents():
    """Test skeleton agents with mock workflow state"""
    
    print("\n" + "="*80)
    print("🧪 SKELETON AGENTS TEST")
    print("="*80)
    print("\n📋 Testing: Evidence Storekeeper + Correlation Agents")
    print("⚙️  Mode: Skeleton Demo (No DB Integration)")
    print()
    
    # Mock state from complete workflow
    state = {
        "document_id": f"test_skeleton_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "file_path": "test_document.pdf",
        "file_format": "pdf",
        "file_valid": True,
        "metadata": {"page_count": 1, "file_size_mb": 0.5},
        
        # OCR results
        "ocr_text": "Purchase Agreement between John Smith and Miller Tech. Account: CH9300762011623852957",
        "text_length": 150,
        "has_text": True,
        "page_texts": ["Page 1 text..."],
        "extracted_entities": {"potential_names": ["John Smith", "Miller Tech"]},
        
        # Background check results
        "screened_entities": ["John Smith", "Miller Tech"],
        "pep_found": True,
        "sanctions_found": False,
        "background_risk_score": 80,
        "background_check_results": [{"name": "Miller Tech", "is_pep": True}],
        
        # Validation results
        "format_valid": True,
        "format_quality_score": 75,
        "completeness_score": 80,
        "spelling_errors": 5,
        "nlp_valid": True,
        "consistency_score": 70,
        "contradictions": [],
        
        # Forensics results
        "tampering_detected": False,
        "integrity_score": 95,
        "tampering_indicators": [],
        "software_trust_level": "trusted",
        "images_analyzed": 1,
        "ai_generated_detected": False,
        "image_tampering_detected": False,
        "image_forensics_score": 90,
        "exif_issues": [],
        
        # Risk assessment
        "overall_risk_score": 35.5,
        "risk_band": "MEDIUM",
        "requires_manual_review": True,
        "risk_factors": [
            "PEP detected",
            "Manual review required"
        ]
    }
    
    try:
        # 1. Evidence Storekeeper Agent
        print("1️⃣  EVIDENCE STOREKEEPER AGENT")
        print("-" * 80)
        evidence_agent = EvidenceStorekeeperAgent()
        state = await evidence_agent.execute(state)
        
        print(f"✅ Evidence Collected: {state.get('evidence_collected')}")
        print(f"📦 Evidence Items: {state.get('evidence_items_count')}")
        print(f"💾 Storage ID: {state.get('evidence_storage_id')}")
        print(f"📊 Audit Entries: {len(state.get('audit_entries', []))}")
        
        # Show evidence summary
        if state.get('evidence_display_data'):
            display = state['evidence_display_data']
            print(f"\n📋 Evidence Summary:")
            print(f"   Document: {display['document_info']['id']}")
            print(f"   Format: {display['document_info']['format']}")
            print(f"   PEP Found: {display['key_findings']['pep_found']}")
            print(f"   Risk: {display['risk_summary']['score']:.1f}/100 ({display['risk_summary']['band']})")
        
        # 2. Correlation Agent
        print(f"\n2️⃣  CORRELATION AGENT")
        print("-" * 80)
        correlation_agent = CorrelationAgent()
        state = await correlation_agent.execute(state)
        
        print(f"✅ Correlation Executed: {state.get('correlation_executed')}")
        print(f"🔗 Entities Correlated: {state.get('entities_correlated')}")
        print(f"📊 Part 1 Matches: {state.get('part1_matches_found')}")
        print(f"⚠️  Correlation Risk: {state.get('correlation_risk_score')}/100")
        
        # Show correlation report
        if state.get('correlation_report'):
            report = state['correlation_report']
            print(f"\n📋 Correlation Summary:")
            print(f"   Strength: {report['executive_summary']['correlation_strength'].upper()}")
            print(f"   Previous Alerts: {report['executive_summary']['previous_alerts']}")
            print(f"\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"   • {rec}")
        
        # Final Summary
        print(f"\n{'='*80}")
        print(f"✅ SKELETON AGENTS TEST COMPLETE")
        print(f"{'='*80}")
        print(f"\n📊 RESULTS:")
        print(f"   Evidence Items: {state.get('evidence_items_count')}")
        print(f"   Entities Correlated: {state.get('entities_correlated')}")
        print(f"   Part 1 Matches: {state.get('part1_matches_found')} (Simulated)")
        print(f"   Overall Risk: {state.get('overall_risk_score'):.1f}/100")
        print(f"   Correlation Risk: {state.get('correlation_risk_score')}/100")
        print()
        print(f"⚠️  NOTE: Both agents are SKELETON implementations")
        print(f"   Requires Part 1 database integration for full functionality")
        print()
        
        return state
        
    except Exception as e:
        print(f"\n❌ Error in skeleton agents test: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_skeleton_agents())
    
    if result and result.get('evidence_collected') and result.get('correlation_executed'):
        print("✅ Skeleton Agents Test - PASSED")
        sys.exit(0)
    else:
        print("❌ Skeleton Agents Test - FAILED")
        sys.exit(1)
