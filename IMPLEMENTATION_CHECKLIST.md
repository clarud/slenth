# SLENTH Implementation Checklist

> Track your implementation progress against the requirements in `AGENTIC_AML_WORKFLOW_PLAN.md`

## ✅ Foundation (Completed)

- [x] Project structure created
- [x] `requirements.txt` with all dependencies
- [x] `.env.example` with all configuration variables
- [x] `config.py` for settings management
- [x] Database models (14 tables in `db/models.py`)
- [x] Database connection setup (`db/database.py`)
- [x] Main FastAPI app (`app/main.py`)
- [x] Health check endpoints (`app/api/health.py`)
- [x] Database initialization scripts
- [x] README documentation
- [x] Data directory structure

---

## 🚧 Core Implementation Tasks

### 1. API Endpoints (`app/api/`)

#### `app/api/transactions.py` - Part 1
- [ ] `POST /transactions` - Submit transaction for processing
- [ ] `GET /transactions/{transaction_id}/status` - Check processing status
- [ ] `GET /transactions/{transaction_id}/compliance` - Get compliance analysis
- [ ] Enqueue transaction to Celery for async processing
- [ ] Return task ID for tracking

#### `app/api/documents.py` - Part 2  
- [ ] `POST /documents/upload` - Upload document (executes workflow synchronously)
- [ ] `GET /documents/{document_id}/risk` - Get risk assessment
- [ ] `GET /documents/{document_id}/report` - Download PDF report
- [ ] `GET /documents/{document_id}/findings` - Get detailed findings
- [ ] `POST /documents/{document_id}/acknowledge` - Acknowledge review
- [ ] **Important**: Execute workflow immediately (no Celery/Redis)

#### `app/api/internal_rules.py`
- [ ] `POST /internal_rules` - Add/update internal rule
- [ ] `GET /internal_rules` - List rules with filtering
- [ ] `GET /internal_rules/{rule_id}` - Get specific rule
- [ ] `PUT /internal_rules/{rule_id}` - Update rule (creates new version)
- [ ] `DELETE /internal_rules/{rule_id}` - Deactivate rule

#### `app/api/alerts.py`
- [ ] `GET /alerts` - List alerts with filtering (role, severity, status, source)
- [ ] `GET /alerts/{alert_id}` - Get alert details
- [ ] `POST /alerts/{alert_id}/acknowledge` - Acknowledge alert
- [ ] `GET /alerts/dashboard` - Dashboard summary statistics

#### `app/api/cases.py`
- [ ] `GET /cases` - List cases with filtering
- [ ] `GET /cases/{case_id}` - Get case details
- [ ] `POST /cases` - Create case
- [ ] `PUT /cases/{case_id}` - Update case
- [ ] `POST /cases/{case_id}/close` - Close case

### 2. Pydantic Schemas (`app/schemas/`)

- [ ] `transaction.py` - Transaction request/response models
- [ ] `document.py` - Document request/response models
- [ ] `rule.py` - Rule request/response models
- [ ] `alert.py` - Alert request/response models
- [ ] `case.py` - Case request/response models
- [ ] Validation schemas with proper type hints

### 3. Services Layer (`services/`)

#### `services/vector_db.py` - Qdrant Client
- [ ] Initialize Qdrant client
- [ ] Upsert vectors with metadata
- [ ] Hybrid search (BM25 + vector search)
- [ ] Filter by date, jurisdiction, etc.
- [ ] Delete vectors
- [ ] Batch operations

#### `services/embeddings.py` - Embedding Generation
- [ ] Initialize OpenAI embeddings client
- [ ] Generate embeddings for text
- [ ] Batch embedding generation
- [ ] Handle rate limits and retries

#### `services/llm.py` - LLM Client
- [ ] Initialize OpenAI/Anthropic client
- [ ] Chat completion
- [ ] Streaming support
- [ ] Token counting
- [ ] Error handling and retries
- [ ] Cost tracking

#### `services/alert_service.py` - Alert Management
- [ ] Create alerts with SLA deadlines
- [ ] Route alerts by role (Front/Compliance/Legal)
- [ ] Check SLA breaches
- [ ] Send WebSocket notifications
- [ ] Deduplicate alerts
- [ ] Link alerts to cases

#### `services/worldcheck.py` - World-Check One Client
- [ ] OAuth 2.0 authentication
- [ ] Search individuals/entities
- [ ] Screen against PEP, sanctions, adverse media
- [ ] Parse and categorize results
- [ ] Handle rate limits

#### `services/audit.py` - Audit Logging
- [ ] Log all system actions
- [ ] Store in audit_logs table
- [ ] Track actor, action, target, context

### 4. Part 1: Transaction Monitoring Agents (`agents/part1/`)

Implement 13 agents as LangGraph nodes:

- [ ] `context_builder.py` - Convert transaction to query, pull history
- [ ] `retrieval.py` - Hybrid BM25 + vector search for rules
- [ ] `applicability.py` - Determine which rules apply
- [ ] `evidence_mapper.py` - Map evidence to transaction fields
- [ ] `control_test.py` - Test controls, assign severity
- [ ] `feature_service.py` - Extract deterministic features
- [ ] `bayesian_engine.py` - Bayesian probability update
- [ ] `pattern_detector.py` - Detect temporal/network patterns
- [ ] `decision_fusion.py` - Fuse scores into final risk
- [ ] `analyst_writer.py` - Generate compliance summary
- [ ] `alert_composer.py` - Create role-specific alerts
- [ ] `remediation_orchestrator.py` - Match to playbooks
- [ ] `persistor.py` - Save results to PostgreSQL

### 5. Part 2: Document Processing Agents (`agents/part2/`)

Implement 10 agents as LangGraph nodes:

- [ ] `document_intake.py` - Normalize document format
- [ ] `ocr.py` - Extract text with pytesseract/PyMuPDF
- [ ] `format_validation.py` - Check formatting, spelling, structure
- [ ] `nlp_validate.py` - Extract fields, validate schema
- [ ] `image_forensics.py` - EXIF, ELA, AI-detection
- [ ] `background_check.py` - World-Check One API integration
- [ ] `cross_reference.py` - Link to transactions/KYC
- [ ] `doc_risk.py` - Calculate risk score
- [ ] `report_generator.py` - Generate PDF report
- [ ] `evidence_store.py` - Manage evidence artifacts

### 6. Workflows (`workflows/`)

#### `workflows/state.py` - State Definitions
- [ ] Define Pydantic models for workflow state
- [ ] TransactionState for Part 1
- [ ] DocumentState for Part 2
- [ ] Intermediate state tracking

#### `workflows/transaction_workflow.py` - Part 1
- [ ] Create LangGraph workflow
- [ ] Connect all 13 agents as nodes
- [ ] Define conditional edges
- [ ] Handle error recovery
- [ ] Execute workflow from Celery task

#### `workflows/document_workflow.py` - Part 2
- [ ] Create LangGraph workflow
- [ ] Connect all 10 agents as nodes
- [ ] Sequential and parallel execution
- [ ] **Execute synchronously** (no Celery)
- [ ] Return complete results immediately

### 7. Crawlers (`crawlers/`)

#### `crawlers/regulatory_crawler.py` - Base Crawler
- [ ] Initialize crawl4ai
- [ ] Configure Playwright
- [ ] Handle rate limiting
- [ ] Extract PDFs and metadata
- [ ] Clean HTML to Markdown

#### `crawlers/hkma_crawler.py` - HKMA Circulars
- [ ] Scrape HKMA website
- [ ] Extract circular links
- [ ] Download PDFs
- [ ] Parse metadata (date, title)

#### `crawlers/mas_crawler.py` - MAS Regulations
- [ ] Scrape MAS website
- [ ] Extract regulation links
- [ ] Download documents
- [ ] Parse metadata

#### `crawlers/finma_crawler.py` - FINMA Circulars
- [ ] Scrape FINMA website
- [ ] Extract circular links
- [ ] Download documents
- [ ] Parse metadata

#### `crawlers/pdf_extractor.py` - PDF Utilities
- [ ] Extract text from PDF
- [ ] Chunk into paragraphs
- [ ] Preserve structure and metadata

### 8. Worker (`worker/`) - Part 1 Only

#### `worker/celery_app.py` - Celery Configuration
- [ ] Initialize Celery app
- [ ] Configure Redis broker
- [ ] Set up task queues
- [ ] Configure serialization
- [ ] Add task routes

#### `worker/tasks.py` - Celery Tasks
- [ ] `process_transaction_task` - Main transaction processing
- [ ] Invoke LangGraph workflow
- [ ] Handle errors and retries
- [ ] Store results
- [ ] Send notifications

### 9. Cron Jobs (`cron/`)

#### `cron/external_rules_ingestion.py` - Regulatory Scraping
- [ ] Schedule: Every 12 hours (manual for local dev)
- [ ] Run all crawlers (HKMA, MAS, FINMA)
- [ ] Chunk documents
- [ ] Generate embeddings
- [ ] Upsert to Qdrant
- [ ] Store in PostgreSQL
- [ ] Log changes

### 10. Scripts (`scripts/`)

#### `scripts/transaction_simulator.py` - Transaction Simulator
- [ ] Parse `transactions_mock_1000_for_participants.csv`
- [ ] Submit to `/transactions` endpoint
- [ ] Rate limiting support
- [ ] Concurrent submission
- [ ] Progress tracking
- [ ] Store task IDs
- [ ] CLI with click

#### Other Scripts (already created)
- [x] `init_db.py` - Initialize PostgreSQL
- [x] `init_vector_db.py` - Initialize Qdrant
- [x] `load_internal_rules.py` - Load JSON rules

---

## 📋 Testing Checklist

### Unit Tests
- [ ] Test each agent individually with mock inputs
- [ ] Test vector DB operations
- [ ] Test embedding generation
- [ ] Test LLM calls
- [ ] Test alert routing
- [ ] Test SLA calculation

### Integration Tests
- [ ] Test full transaction workflow
- [ ] Test full document workflow
- [ ] Test API endpoints
- [ ] Test Celery task execution
- [ ] Test WebSocket connections

### End-to-End Tests
- [ ] Process sample transactions
- [ ] Upload sample documents
- [ ] Verify compliance scores
- [ ] Check alert generation
- [ ] Validate audit trail

---

## 📝 Documentation Checklist

- [x] README with quickstart
- [x] Implementation plan (AGENTIC_AML_WORKFLOW_PLAN.md)
- [ ] API documentation (add examples to Swagger)
- [ ] Agent documentation (docstrings)
- [ ] Workflow diagrams
- [ ] Deployment guide

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] API keys secured
- [ ] Rate limits configured

### Infrastructure
- [ ] Cloud PostgreSQL provisioned
- [ ] Redis deployed (for Part 1)
- [ ] Qdrant deployed
- [ ] Load balancer configured
- [ ] SSL/TLS certificates

### Monitoring
- [ ] Health checks configured
- [ ] Logging enabled
- [ ] Metrics collection
- [ ] Alert thresholds set
- [ ] Dashboard created

---

## 💡 Implementation Tips

1. **Start with Services**: Implement `services/` first as they're used by agents
2. **Test Incrementally**: Test each component before moving to next
3. **Use Mock Data**: Test with sample transactions/documents
4. **Log Everything**: Add comprehensive logging for debugging
5. **Handle Errors**: Implement proper error handling and retries
6. **Follow the Plan**: Refer to `AGENTIC_AML_WORKFLOW_PLAN.md` for details

---

## 📚 Key References

- **Implementation Plan**: `AGENTIC_AML_WORKFLOW_PLAN.md`
- **Problem Statement**: `README copy.md`
- **Database Models**: `db/models.py`
- **Configuration**: `config.py` and `.env.example`

---

**Track your progress by checking off items as you complete them! 🎯**
