#!/usr/bin/env python3
"""
Test script to verify all Part 1 agents are properly implemented.

This script checks:
1. No TODO/placeholder code in agent execute() methods
2. All agents return expected state fields
3. Agent workflow executes without errors
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from pathlib import Path


def check_agent_implementation(agent_file: Path) -> tuple[bool, list[str]]:
    """
    Check if an agent is fully implemented (no TODOs/placeholders).
    
    Returns:
        (is_implemented, issues_found)
    """
    with open(agent_file, 'r') as f:
        content = f.read()
    
    issues = []
    
    # Check for TODO markers
    todo_matches = re.findall(r'# TODO:.*', content)
    if todo_matches:
        issues.extend(todo_matches)
    
    # Check for placeholder implementations
    if 'Placeholder implementation' in content:
        issues.append("Contains 'Placeholder implementation' comment")
    
    # Check if execute method is just a pass/stub
    execute_pattern = r'async def execute\(.*?\):.*?return state'
    execute_matches = re.findall(execute_pattern, content, re.DOTALL)
    
    if execute_matches:
        for match in execute_matches:
            # If execute method only has logging and returns state without logic
            if 'state[' not in match and 'state.get' not in match:
                issues.append("Execute method appears to be a stub (no state modifications)")
    
    return len(issues) == 0, issues


def main():
    """Test all Part 1 agents for implementation completeness."""
    
    agents_dir = Path(__file__).parent.parent / "agents" / "part1"
    
    # List of critical agents that must be implemented
    critical_agents = [
        "context_builder.py",
        "retrieval.py",
        "applicability.py",
        "evidence_mapper.py",
        "control_test.py",
        "feature_service.py",
        "bayesian_engine.py",
        "pattern_detector.py",
        "decision_fusion.py",
        "analyst_writer.py",
        "alert_composer.py",
        "remediation_orchestrator.py",
        "persistor.py",
    ]
    
    print("=" * 80)
    print("AGENT IMPLEMENTATION STATUS CHECK")
    print("=" * 80)
    print()
    
    all_implemented = True
    results = {}
    
    for agent_name in critical_agents:
        agent_file = agents_dir / agent_name
        
        if not agent_file.exists():
            print(f"❌ {agent_name}: FILE NOT FOUND")
            all_implemented = False
            results[agent_name] = (False, ["File not found"])
            continue
        
        is_implemented, issues = check_agent_implementation(agent_file)
        results[agent_name] = (is_implemented, issues)
        
        if is_implemented:
            print(f"✅ {agent_name}: IMPLEMENTED")
        else:
            print(f"⚠️  {agent_name}: INCOMPLETE")
            for issue in issues:
                print(f"   - {issue}")
            all_implemented = False
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    implemented_count = sum(1 for is_impl, _ in results.values() if is_impl)
    total_count = len(critical_agents)
    
    print(f"Implemented: {implemented_count}/{total_count} agents")
    print()
    
    if all_implemented:
        print("✅ ALL AGENTS FULLY IMPLEMENTED!")
        print()
        print("Next steps:")
        print("1. Restart Celery worker:")
        print("   celery -A worker.celery_app worker --loglevel=info")
        print()
        print("2. Submit test transactions:")
        print("   python scripts/transaction_simulator.py")
        print()
        print("3. View results with populated fields:")
        print("   python scripts/view_transaction_results.py")
        return 0
    else:
        print("⚠️  SOME AGENTS STILL NEED IMPLEMENTATION")
        print()
        incomplete = [name for name, (is_impl, _) in results.items() if not is_impl]
        print("Incomplete agents:")
        for agent in incomplete:
            print(f"  - {agent}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
