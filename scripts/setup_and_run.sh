#!/bin/bash
# Setup environment variables for internal rules ingestion

# Required: Pinecone API key
export PINECONE_API_KEY="your-pinecone-api-key-here"

# Required: Pinecone internal rules index host
# Example: https://your-index-abc123.svc.pinecone.io
export PINECONE_INTERNAL_INDEX_HOST="your-internal-index-host-here"

# Run the ingestion script
python scripts/load_internal_rules_pinecone.py
