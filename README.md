# SLENTH - AML Monitoring System

> **Agentic AI for Real-Time AML Monitoring and Document Corroboration**
> 
> Julius Baer Hackathon Solution

**🎉 Implementation Status: ~60% Complete (Infrastructure Ready)**

---

## 📊 Quick Status

| Component | Status | Progress |
|-----------|--------|----------|
| Services Layer | ✅ Complete | 100% |
| API Endpoints | ✅ Complete | 100% |
| Workflows | ✅ Complete | 100% |
| Agent Skeletons | ✅ Complete | 100% |
| Agent Logic | ⏳ In Progress | 10% |
| Crawlers | ⏳ Pending | 0% |

📋 **See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for detailed breakdown**

---

## 🎯 Project Overview

SLENTH is a comprehensive Anti-Money Laundering (AML) compliance system that uses **agentic AI workflows** powered by **LangGraph** to provide:

### Part 1: Real-Time AML Transaction Monitoring
- Automated ingestion of external regulatory circulars (HKMA, MAS, FINMA)
- API-driven internal rules management with versioning
- Real-time transaction compliance evaluation using RAG
- Multi-role alerts (Front Office, Compliance, Legal)
- Automated remediation workflows

### Part 2: Document & Image Corroboration
- Multi-format document processing (PDF, images, text)
- OCR extraction and format validation
- Image forensics (tampering detection, EXIF analysis, AI-generated detection)
- Background checks via World-Check One API
- Cross-reference with transaction history

---

## 🏗️ Architecture

### Processing Modes
- **Part 1**: **Async** processing via Celery + Redis queue (high throughput)
- **Part 2**: **Synchronous** processing (immediate results)

### Infrastructure
- **Database**: Cloud PostgreSQL (structured data)
- **Vector DB**: Qdrant (regulatory rules, RAG)
- **Queue**: Redis (Part 1 only)
- **LLM**: OpenAI GPT-4 / Anthropic Claude
- **Embeddings**: text-embedding-3-large

---

## 📁 Project Structure

See full structure in the project. Key components:

- **`app/`** - FastAPI application and API endpoints
- **`agents/`** - LangGraph agents (Part 1: 13 agents, Part 2: 10 agents)
- **`workflows/`** - LangGraph workflow orchestration
- **`services/`** - Business logic (vector DB, LLM, embeddings, alerts)
- **`db/`** - Database models and connections
- **`crawlers/`** - Regulatory website scrapers
- **`worker/`** - Celery workers (Part 1 only)
- **`scripts/`** - Utility scripts and simulators

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Cloud PostgreSQL database
- Redis (local via Homebrew)
- Docker (for Qdrant)
- Tesseract OCR
- OpenAI API key

### Installation

```bash
# Clone and setup
git clone https://github.com/clarud/slenth.git
cd slenth

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install

# Install Tesseract OCR (macOS)
brew install tesseract

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start infrastructure
brew services start redis
docker run -d -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  --name slenth-qdrant qdrant/qdrant

# Initialize databases
python scripts/init_db.py
python scripts/init_vector_db.py
python scripts/load_internal_rules.py

# Run application
# Terminal 1:
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 (Part 1 only):
celery -A worker.celery_app worker -l info -Q default -c 4
```

### Access Points

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## 📡 API Examples

### Part 1: Process Transaction (Async)

```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN001",
    "amount": 50000,
    "currency": "USD",
    "customer_id": "CUST123",
    "originator_country": "HK",
    "beneficiary_country": "SG"
  }'
```

### Part 2: Upload Document (Synchronous)

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@data/Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf" \
  -F "document_type=purchase_agreement"
```

---

## 📝 Implementation Status

### ✅ Completed
- [x] Project structure
- [x] Configuration management
- [x] Database models (14 tables)
- [x] Main FastAPI app
- [x] Health check endpoints
- [x] Requirements and dependencies
- [x] Documentation

### 🚧 To Be Implemented

Based on `AGENTIC_AML_WORKFLOW_PLAN.md`, you need to implement:

1. **API Endpoints** (`app/api/`)
   - transactions.py, documents.py, internal_rules.py, alerts.py, cases.py

2. **Agents** (`agents/`)
   - Part 1: 13 agents for transaction monitoring
   - Part 2: 10 agents for document corroboration

3. **Workflows** (`workflows/`)
   - LangGraph workflows for Part 1 and Part 2

4. **Services** (`services/`)
   - Vector DB, embeddings, LLM, alerts, World-Check One

5. **Crawlers** (`crawlers/`)
   - HKMA, MAS, FINMA regulatory scrapers

6. **Worker** (`worker/`)
   - Celery configuration and tasks

7. **Scripts** (`scripts/`)
   - Database init, transaction simulator

---

## 📚 Documentation

- **Full Implementation Plan**: `AGENTIC_AML_WORKFLOW_PLAN.md`
- **Problem Statement**: `README copy.md`
- **API Docs**: http://localhost:8000/docs (when running)

---

## 🔧 Development

Follow implementation order:
1. Services layer (vector DB, LLM, embeddings)
2. Workflow foundations
3. Part 1 agents and workflow
4. Part 2 agents and workflow
5. API endpoints
6. Crawlers and cron jobs
7. Testing

---

**Built for Julius Baer Hackathon 2025** 🚀
