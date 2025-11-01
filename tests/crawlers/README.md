# Crawler Tests

This directory contains comprehensive tests for regulatory circular crawlers.

## Test Structure

```
tests/crawlers/
├── conftest.py              # Test fixtures and configuration
├── test_hkma.py            # HKMA crawler tests
├── test_mas.py             # MAS crawler tests
├── test_finma.py           # FINMA crawler tests
├── test_integration.py     # Integration tests for all crawlers
├── run_tests.py            # Test runner script
└── README.md               # This file
```

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
```

### Run All Tests

```bash
# Basic run
pytest tests/crawlers/

# With verbose output
pytest tests/crawlers/ -v

# With coverage
pytest tests/crawlers/ --cov=crawlers --cov-report=html
```

### Run Specific Tests

```bash
# Run only HKMA tests
pytest tests/crawlers/test_hkma.py

# Run only MAS tests
pytest tests/crawlers/test_mas.py

# Run only FINMA tests
pytest tests/crawlers/test_finma.py

# Run integration tests
pytest tests/crawlers/test_integration.py
```

### Run by Test Markers

```bash
# Run integration tests only
pytest tests/crawlers/ -m integration

# Run performance tests only
pytest tests/crawlers/ -m performance

# Run quick unit tests only (exclude integration)
pytest tests/crawlers/ -m "not integration"
```

### Using Test Runner Script

```bash
# Run all tests
python tests/crawlers/run_tests.py

# Run specific file
python tests/crawlers/run_tests.py --file test_hkma

# Run with verbose output
python tests/crawlers/run_tests.py --verbose

# Run integration tests
python tests/crawlers/run_tests.py --integration

# Run manual comprehensive test
python tests/crawlers/run_tests.py --manual
```

## Test Categories

### Unit Tests
Tests individual crawler methods in isolation with mocked dependencies.

Example:
```bash
pytest tests/crawlers/test_hkma.py::TestHKMACrawler::test_crawler_initialization
```

### Integration Tests
Tests complete workflows including database operations.

```bash
pytest tests/crawlers/ -m integration
```

### Performance Tests
Tests crawler performance and speed.

```bash
pytest tests/crawlers/ -m performance
```

## Manual Testing

Each test file can be run directly for manual testing:

```bash
# Test HKMA crawler manually
python tests/crawlers/test_hkma.py

# Test MAS crawler manually
python tests/crawlers/test_mas.py

# Test FINMA crawler manually
python tests/crawlers/test_finma.py

# Run comprehensive test
python tests/crawlers/test_integration.py
```

## Test Coverage

Generate HTML coverage report:

```bash
pytest tests/crawlers/ --cov=crawlers --cov-report=html
open htmlcov/index.html
```

## What's Tested

### For Each Crawler (HKMA, MAS, FINMA):

1. **Initialization**
   - Correct source and jurisdiction
   - Base URL configuration

2. **Crawling**
   - Returns list of circulars
   - Correct data structure
   - Required fields present
   - Data type validation

3. **HTML Parsing**
   - Handles mock HTML correctly
   - Extracts titles, dates, URLs
   - Parses content

4. **Database Operations**
   - Saves to database
   - Handles duplicates
   - Creates vector embeddings

5. **Error Handling**
   - Network errors
   - Parse errors
   - Invalid data

6. **Data Quality**
   - Title length checks
   - Content validation
   - Date format validation
   - URL format validation

### Integration Tests:

1. **Multi-Crawler**
   - All crawlers run successfully
   - Consistent output format
   - Correct jurisdictions
   - Parallel execution

2. **Database Workflow**
   - Crawl → Parse → Save → Retrieve
   - Vector embedding generation
   - Duplicate prevention

3. **Performance**
   - Reasonable execution time
   - Parallel speedup

## Test Fixtures

Available fixtures (from `conftest.py`):

- `mock_db_session` - In-memory SQLite database
- `mock_embedding_service` - Mocked embedding service
- `mock_vector_db` - Mocked vector database
- `sample_hkma_html` - Sample HKMA HTML page
- `sample_mas_html` - Sample MAS HTML page
- `sample_finma_html` - Sample FINMA HTML page

## Expected Output

When tests pass, you should see:

```
tests/crawlers/test_hkma.py ................    [25%]
tests/crawlers/test_mas.py ..............      [50%]
tests/crawlers/test_finma.py ............      [75%]
tests/crawlers/test_integration.py ....        [100%]

==================== 42 passed in 5.23s ====================
```

## Troubleshooting

### Import Errors
```bash
# Ensure project root is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/Users/chenxiangrui/Projects/slenth"
```

### Database Errors
```bash
# Check database models are created
python -c "from db.database import Base, engine; Base.metadata.create_all(engine)"
```

### Async Warnings
```bash
# Install pytest-asyncio
pip install pytest-asyncio
```

### Network Errors
Mock web requests are used by default. For real web scraping tests:
```bash
pytest tests/crawlers/ --real-network
```

## Continuous Integration

Add to CI/CD pipeline:

```yaml
# .github/workflows/test.yml
- name: Run Crawler Tests
  run: |
    pip install pytest pytest-asyncio pytest-cov
    pytest tests/crawlers/ -v --cov=crawlers
```

## Future Enhancements

- [ ] Real web scraping tests (with VCR.py for recording)
- [ ] Rate limiting tests
- [ ] Retry mechanism tests
- [ ] HTML structure change detection
- [ ] Multi-language content tests
- [ ] Webhook notification tests
- [ ] Scheduling tests

---

**Last Updated:** November 1, 2025
