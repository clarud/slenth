#!/bin/bash

# Quick setup and run script for transaction workflow testing

echo "================================="
echo "Transaction Workflow Test Setup"
echo "================================="
echo ""

# Load .env file if it exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
    echo "✅ Environment variables loaded"
else
    echo "⚠️  .env file not found"
fi

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  No virtual environment detected."
    echo "Attempting to activate slenth_env_2..."
    
    if [ -d "slenth_env_2/bin" ]; then
        source slenth_env_2/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found. Please activate your Python environment."
        exit 1
    fi
fi

# Check Python version
echo ""
echo "Checking Python version..."
python --version

# Install/update dependencies
echo ""
echo "Checking dependencies..."
pip install -q python-dotenv langgraph langchain-openai pinecone groq

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data/logs data/workflow_results

# Check environment variables
echo ""
echo "Checking environment variables..."
if [ -z "$GROQ_API_KEY" ]; then
    echo "⚠️  GROQ_API_KEY not set"
else
    echo "✅ GROQ_API_KEY found"
fi

if [ -z "$PINECONE_API_KEY" ]; then
    echo "⚠️  PINECONE_API_KEY not set"
else
    echo "✅ PINECONE_API_KEY found"
fi

# Run the workflow test
echo ""
echo "================================="
echo "Running Workflow Test"
echo "================================="
echo ""

python scripts/test_workflow_execution.py

echo ""
echo "================================="
echo "Test Complete"
echo "================================="
echo ""
echo "Check output files in:"
echo "  - data/logs/"
echo "  - data/workflow_results/"
