#!/usr/bin/env python3
"""
Script to remove VectorDBService imports from all agent files.
We're using Pinecone directly, not Qdrant via VectorDBService.
"""

import re
from pathlib import Path

# Agent files to fix
agent_files = [
    "agents/part1/feature_service.py",
    "agents/part1/bayesian_engine.py",
    "agents/part1/pattern_detector.py",
    "agents/part1/decision_fusion.py",
    "agents/part1/analyst_writer.py",
    "agents/part1/alert_composer.py",
    "agents/part1/remediation_orchestrator.py",
    "agents/part1/persistor.py",
]

project_root = Path(__file__).parent.parent

for file_path in agent_files:
    full_path = project_root / file_path
    
    if not full_path.exists():
        print(f"⚠️  Skipping {file_path} (not found)")
        continue
    
    print(f"Processing {file_path}...")
    
    with open(full_path, 'r') as f:
        content = f.read()
    
    # Remove import line
    content = re.sub(r'from services\.vector_db import VectorDBService\n', '', content)
    
    # Remove vector_service parameter from __init__
    content = re.sub(
        r'(def __init__\([^)]*), vector_service: VectorDBService = None\)',
        r'\1)',
        content
    )
    
    # Remove self.vector_db assignment
    content = re.sub(r'\s*self\.vector_db = vector_service\n', '\n', content)
    
    with open(full_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {file_path}")

print("\n✅ All agent files fixed!")
print("VectorDBService imports removed - now using Pinecone directly.")
