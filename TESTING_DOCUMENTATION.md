# SLENTH AML System - Comprehensive Test Suite Documentation

## 📋 Overview

This document describes the comprehensive test suite for the SLENTH Anti-Money Laundering (AML) monitoring and regulatory compliance system.

## 🗂️ Test Structure

```
tests/
├── agents/
│   ├── part1/                          # Transaction monitoring agents (13 agents)
│   │   └── test_all_agents.py         # 100+ tests for Part 1 agents
│   └── part2/                          # Document corroboration agents (10 agents)
│       └── test_all_agents.py         # 80+ tests for Part 2 agents
├── workflows/
│   └── test_workflows.py              # 30+ tests for LangGraph workflows
├── services/
│   └── test_services.py               # 40+ tests for services layer
├── crawlers/                           # Regulatory scraper tests
│   ├── test_hkma.py
│   ├── test_mas.py
│   └── test_finma.py
├── internal-rules/                     # Internal rules ingestion tests
│   ├── test_load_internal_rules.py
│   └── test_pinecone_integration_new.py
└── api/                                # API endpoint tests
    ├── test_transactions.py
    ├── test_documents.py
    └── test_alerts.py
```

## 🧪 Test Coverage by Component

### 1. Part 1: Transaction Monitoring Agents (13 Agents)
**File:** `tests/agents/part1/test_all_agents.py`

#### Agents Tested:
1. **ContextBuilderAgent** - 5 tests
   - Query context creation
   - Transaction details inclusion
   - History retrieval
   - Error handling
   
2. **RetrievalAgent** - 4 tests
   - Rule retrieval from vector DB
   - Hybrid search (BM25 + semantic)
   - Filtering by jurisdiction/date
   - Empty results handling

3. **ApplicabilityAgent** - 4 tests
   - Rule applicability assessment
   - Confidence scoring
   - LLM-based reasoning
   - Empty rules handling

4. **EvidenceMapperAgent** - 3 tests
   - Evidence identification
   - Present/missing evidence mapping
   - Field extraction

5. **ControlTestAgent** - 3 tests
   - Pass/fail determination
   - Severity assignment
   - Compliance scoring

6. **FeatureServiceAgent** - 4 tests
   - Amount features
   - Velocity features
   - Structuring indicators
   - Historical patterns

7. **BayesianEngineAgent** - 3 tests
   - Posterior probability calculation
   - Risk distribution updates
   - Category scoring

8. **PatternDetectorAgent** - 3 tests
   - Structuring detection
   - Layering patterns
   - Circular transfers

9. **DecisionFusionAgent** - 4 tests
   - Risk score calculation (0-100)
   - Risk band assignment (Low/Medium/High/Critical)
   - Multi-source fusion
   - Threshold application

10. **AnalystWriterAgent** - 3 tests
    - Compliance summary generation
    - Rule citations
    - Evidence references

11. **AlertComposerAgent** - 4 tests
    - Alert creation for high risk
    - Role-based routing (Front/Compliance/Legal)
    - SLA assignment
    - Low risk filtering

12. **RemediationOrchestratorAgent** - 3 tests
    - Action suggestion
    - Owner assignment
    - Playbook integration

13. **PersistorAgent** - 3 tests
    - Database persistence
    - Audit trail creation
    - Transaction updates

**Integration Tests:** 2 tests
- Sequential agent chaining
- Error propagation

**Total:** ~50 tests

---

### 2. Part 2: Document Corroboration Agents (10 Agents)
**File:** `tests/agents/part2/test_all_agents.py`

#### Agents Tested:
1. **DocumentIntakeAgent** - 5 tests
   - Document type classification
   - Multi-format handling (PDF, images, text)
   - Metadata extraction
   - Normalization

2. **OCRAgent** - 5 tests
   - Text extraction from PDFs
   - Image OCR
   - Multi-page processing
   - Confidence scoring

3. **FormatValidationAgent** - 5 tests
   - Formatting error detection (spacing, fonts)
   - Spelling/grammar checks
   - Structure validation
   - Template matching

4. **NLPValidationAgent** - 5 tests
   - Entity extraction (names, addresses, amounts)
   - Field validation
   - Schema conformity
   - Cross-field consistency

5. **ImageForensicsAgent** - 5 tests
   - EXIF metadata analysis
   - Error Level Analysis (ELA)
   - AI-generated detection
   - Tampering heuristics

6. **BackgroundCheckAgent** (World-Check One) - 6 tests
   - PEP screening
   - Sanctions list checking
   - Adverse media screening
   - API integration
   - Match result parsing
   - Error handling

7. **CrossReferenceAgent** - 5 tests
   - Transaction correlation
   - KYC record linking
   - Discrepancy detection
   - Historical comparison

8. **DocumentRiskAgent** - 5 tests
   - Risk score aggregation (0-100)
   - Risk level categorization
   - Background check integration
   - Multi-finding fusion

9. **ReportGeneratorAgent** - 5 tests
   - PDF report generation
   - Finding summarization
   - Evidence citations
   - Recommendation generation

10. **EvidenceStorekeeperAgent** - 5 tests
    - Raw document storage
    - Extracted text archiving
    - Version control
    - Retention compliance

**Integration Tests:** 3 tests
- Sequential document processing
- Risk score aggregation
- Error handling

**Total:** ~55 tests

---

### 3. Workflow Tests
**File:** `tests/workflows/test_workflows.py`

#### Transaction Workflow Tests (Part 1):
- Workflow creation and compilation
- End-to-end execution
- All 13 agents execute
- Risk score generation
- Compliance analysis generation
- State preservation
- Error collection
- Processing time tracking

**Tests:** 8 tests

#### Document Workflow Tests (Part 2):
- Workflow creation
- Synchronous execution (no Celery queue)
- All 10 agents execute
- Risk score calculation
- PDF report generation
- Immediate result return

**Tests:** 6 tests

#### Workflow State Tests:
- TransactionWorkflowState structure
- DocumentWorkflowState structure
- State mutability
- Type checking

**Tests:** 3 tests

#### Error Handling Tests:
- Missing data handling
- Agent failure recovery
- Missing file content

**Tests:** 3 tests

#### Conditional Edge Tests:
- High risk → alerts
- Low risk → skip remediation
- Dynamic routing

**Tests:** 2 tests

#### Performance Tests:
- Transaction workflow timing
- Document workflow timing

**Tests:** 2 tests

#### Integration Tests:
- Alert creation for high risk
- Report generation

**Tests:** 2 tests

**Total:** ~26 tests

---

### 4. Services Tests
**File:** `tests/services/test_services.py`

#### Pinecone DB Service:
- Service initialization
- Text-based semantic search
- Metadata filtering
- Record upsert (inference API)
- Index statistics

**Tests:** 5 tests

#### LLM Service:
- Service initialization
- Chat completion
- Structured output (JSON)
- API error handling

**Tests:** 4 tests

#### Alert Service:
- Service initialization
- Alert creation
- Status-based retrieval
- Alert acknowledgment
- Team routing
- SLA calculation

**Tests:** 6 tests

#### Audit Service:
- Service initialization
- Action logging
- System event logging
- Audit trail retrieval
- Immutability enforcement

**Tests:** 5 tests

#### World-Check One Service:
- Service initialization
- Individual screening
- Organization screening
- PEP screening
- Sanctions screening
- Adverse media screening
- API error handling
- Match result parsing

**Tests:** 8 tests

#### Integration Tests:
- LLM + Vector DB (RAG)
- Alert + Audit integration

**Tests:** 2 tests

**Total:** ~30 tests

---

### 5. Internal Rules Tests
**Files:** 
- `tests/internal-rules/test_load_internal_rules.py`
- `tests/internal-rules/test_pinecone_integration_new.py`

#### Ingestion Tests:
- JSON file loading
- Empty passage filtering
- Metadata structure (flat, not nested)
- Vector ID matching
- Text context inclusion
- Batch upsert
- Directory handling
- Malformed JSON handling
- Text truncation (512 chars)
- Multiple file processing
- Pinecone client initialization
- Success return value
- Upsert failure handling

**Tests:** 13 tests

#### Data Format Tests:
- JSON schema validation
- Pinecone record format (inference API)
- Batch format validation
- Metadata size limits

**Tests:** 3 tests

#### Integration Tests:
- Actual JSON file existence
- File structure validation
- Data format validation

**Tests:** 3 tests

**Total:** ~19 tests

---

### 6. Crawler Tests
**Files:** 
- `tests/crawlers/test_hkma.py`
- `tests/crawlers/test_mas.py`
- `tests/crawlers/test_finma.py`

#### Per-Crawler Tests:
- URL scraping
- Content extraction
- PDF downloading
- Metadata extraction
- Error handling
- Rate limiting

**Tests per crawler:** 6 tests
**Total:** ~18 tests (3 crawlers × 6 tests)

---

## 🎯 Total Test Count

| Component | Test File | Test Count |
|-----------|-----------|------------|
| Part 1 Agents | test_all_agents.py (part1) | ~50 |
| Part 2 Agents | test_all_agents.py (part2) | ~55 |
| Workflows | test_workflows.py | ~26 |
| Services | test_services.py | ~30 |
| Internal Rules | test_load_internal_rules.py | ~19 |
| Crawlers | test_*.py | ~18 |
| **TOTAL** | | **~198 tests** |

---

## 🚀 Running Tests

### Run All Tests
```bash
python run_all_tests.py all
```

### Run Specific Test Suite
```bash
# Part 1 agents only
python run_all_tests.py part1

# Part 2 agents only
python run_all_tests.py part2

# Workflows only
python run_all_tests.py workflows

# Services only
python run_all_tests.py services

# Internal rules only
python run_all_tests.py internal-rules

# Crawlers only
python run_all_tests.py crawlers
```

### Run Quick Smoke Tests
```bash
python run_all_tests.py quick
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
```

### Run Specific Test File
```bash
pytest tests/agents/part1/test_all_agents.py -v
```

### Run Specific Test Class
```bash
pytest tests/agents/part1/test_all_agents.py::TestContextBuilderAgent -v
```

### Run Specific Test Method
```bash
pytest tests/agents/part1/test_all_agents.py::TestContextBuilderAgent::test_context_builder_execution -v
```

---

## 📊 Test Coverage Goals

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| Agents (Part 1) | 80%+ | ✅ Comprehensive |
| Agents (Part 2) | 80%+ | ✅ Comprehensive |
| Workflows | 85%+ | ✅ Comprehensive |
| Services | 75%+ | ✅ Comprehensive |
| Crawlers | 70%+ | ✅ Good |
| API Endpoints | 80%+ | ⚠️ To be added |
| Database Models | 60%+ | ⚠️ To be added |

---

## 🔧 Test Infrastructure

### Fixtures Used:
- `sample_transaction` - Mock transaction data
- `sample_document` - Mock document data
- `sample_state` - Mock workflow state
- `mock_db_session` - Mock database session
- `mock_llm_service` - Mock LLM API
- `mock_vector_service` - Mock Pinecone
- `mock_embedding_service` - Mock embeddings
- `mock_pinecone_client` - Mock Pinecone client
- `mock_worldcheck_api` - Mock World-Check API

### Mocking Strategy:
- **External APIs:** Fully mocked (OpenAI, Pinecone, World-Check)
- **Database:** Mocked with MagicMock
- **File I/O:** Mocked with mock_open
- **Network calls:** Patched with unittest.mock

---

## 🐛 Testing Best Practices

### 1. Test Organization
- ✅ One test class per agent/service
- ✅ Descriptive test names (`test_what_is_being_tested`)
- ✅ Arrange-Act-Assert pattern
- ✅ Fixtures for common setup

### 2. Async Testing
- ✅ Use `@pytest.mark.asyncio` for async tests
- ✅ Mock async methods with `AsyncMock`
- ✅ Await all async calls

### 3. Mocking
- ✅ Mock external dependencies
- ✅ Patch at the correct import location
- ✅ Use context managers for patches
- ✅ Verify mock calls with assertions

### 4. Assertions
- ✅ Assert expected behavior
- ✅ Check return types
- ✅ Validate data structures
- ✅ Test error conditions

### 5. Coverage
- ✅ Test happy paths
- ✅ Test error conditions
- ✅ Test edge cases
- ✅ Test integration points

---

## 📝 Adding New Tests

### For New Agents:
1. Add test class to appropriate file (part1 or part2)
2. Create fixtures for mock data
3. Test execution, output structure, and error handling
4. Add integration test if needed

### For New Services:
1. Add test class to `test_services.py`
2. Mock external dependencies
3. Test initialization, main methods, and error handling
4. Add integration test with related services

### For New Workflows:
1. Add tests to `test_workflows.py`
2. Test workflow compilation
3. Test end-to-end execution
4. Test conditional edges
5. Test error recovery

---

## 🔍 Continuous Integration

### GitHub Actions Workflow:
```yaml
name: Run Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python run_all_tests.py all
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 📈 Test Metrics

### Key Metrics to Track:
- **Total test count:** ~198 tests
- **Execution time:** < 5 minutes (with mocks)
- **Coverage:** 75%+ target
- **Pass rate:** 100% target
- **Flaky tests:** 0 target

### Performance Benchmarks:
- Agent tests: < 30s
- Workflow tests: < 45s
- Service tests: < 30s
- Integration tests: < 60s

---

## 🎓 Testing Philosophy

1. **Fast Feedback:** Tests should run quickly with mocks
2. **Isolation:** Each test is independent
3. **Clarity:** Test names explain what's being tested
4. **Maintainability:** Easy to update when code changes
5. **Coverage:** High coverage without redundancy
6. **Real-world:** Test actual use cases

---

## 📚 References

- [Pytest Documentation](https://docs.pytest.org/)
- [AsyncIO Testing](https://docs.python.org/3/library/asyncio-dev.html)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)

---

## ✅ Summary

This comprehensive test suite provides:
- **~198 tests** covering all major components
- **High coverage** of critical business logic
- **Fast execution** with mocked dependencies
- **Clear organization** by component
- **Easy to extend** for new features
- **CI/CD ready** with coverage reporting

The test suite ensures the SLENTH AML system is robust, reliable, and maintainable.
