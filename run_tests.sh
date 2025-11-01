#!/bin/bash
# Quick test runner for internal rules ingestion

echo "=================================================="
echo "Internal Rules Testing - Quick Start"
echo "=================================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null
then
    echo "❌ pytest not found. Installing..."
    pip install pytest pytest-mock pytest-cov
    echo ""
fi

echo "📋 Available test commands:"
echo ""
echo "1. Run all tests"
echo "   pytest tests/ -v"
echo ""
echo "2. Run Pinecone integration tests"
echo "   pytest tests/test_pinecone_integration.py -v"
echo ""
echo "3. Run loading script tests"
echo "   pytest tests/test_load_internal_rules.py -v"
echo ""
echo "4. Run with coverage"
echo "   pytest tests/ --cov=services --cov=scripts --cov-report=html"
echo ""
echo "5. Run specific test class"
echo "   pytest tests/test_pinecone_integration.py::TestPineconeDataIngestion -v"
echo ""
echo "6. Skip integration tests (no Pinecone required)"
echo "   pytest tests/ -v -m 'not integration'"
echo ""

echo "=================================================="
echo "Quick Test Run (Unit Tests Only)"
echo "=================================================="
echo ""

# Run unit tests (no Pinecone required)
echo "Running unit tests..."
pytest tests/test_pinecone_integration.py::TestPineconeDataIngestion -v --tb=short
pytest tests/test_load_internal_rules.py::TestLoadInternalRulesScript::test_skip_empty_passages -v --tb=short
pytest tests/test_load_internal_rules.py::TestDataFormatValidation -v --tb=short

echo ""
echo "=================================================="
echo "Test Results Summary"
echo "=================================================="
echo ""
echo "✅ If tests passed: Your data formats and logic are correct"
echo ""
echo "Next steps:"
echo "1. Set environment variables:"
echo "   export PINECONE_API_KEY=your-key"
echo "   export PINECONE_INTERNAL_INDEX_HOST=your-host"
echo "   export OPENAI_API_KEY=your-key"
echo ""
echo "2. Run loading script:"
echo "   python scripts/load_internal_rules_pinecone.py"
echo ""
echo "3. Verify data:"
echo "   pytest tests/test_pinecone_integration.py::TestPineconeServiceIntegration -v"
echo ""
echo "=================================================="
