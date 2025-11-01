# 🚀 SLENTH Quick Start Guide

## Prerequisites Checklist

- [ ] Python 3.9+ installed
- [ ] PostgreSQL running (cloud or local)
- [ ] Redis running locally
- [ ] Qdrant Docker container running
- [ ] Environment variables configured

---

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 2. Configure Environment

Create `.env` file in project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/slenth

# Redis (Part 1 only)
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_URL=http://localhost:6333

# OpenAI
OPENAI_API_KEY=your_openai_key

# Anthropic (optional)
ANTHROPIC_API_KEY=your_anthropic_key

# World-Check (optional)
WORLDCHECK_API_KEY=your_worldcheck_key

# App Settings
APP_NAME=SLENTH
APP_ENV=development
LOG_LEVEL=INFO
```

---

## 3. Start Infrastructure

### Terminal 1: Redis
```bash
redis-server
```

### Terminal 2: Qdrant
```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

---

## 4. Initialize Database

```bash
# Run migrations
alembic upgrade head

# Verify connection
python -c "from db.database import engine; print('✅ Database connected!')"
```

---

## 5. Start Application

### Terminal 3: Celery Worker (Part 1)
```bash
celery -A worker.celery_app worker --loglevel=info
```

### Terminal 4: FastAPI Server
```bash
uvicorn app.main:app --reload --port 8000
```

---

## 6. Verify Installation

Open browser to:
- **Swagger UI:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

Expected health response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-01T...",
  "services": {
    "database": "connected",
    "redis": "connected",
    "qdrant": "connected"
  }
}
```

---

## 7. Test Basic Flow

### Test Transaction Submission
```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_type": "transfer",
    "amount": 50000,
    "currency": "USD",
    "sender_account": "HK123456",
    "sender_country": "HK",
    "receiver_account": "US789012",
    "receiver_country": "US",
    "jurisdiction": "HK"
  }'
```

Expected response:
```json
{
  "transaction_id": "txn_...",
  "task_id": "celery_task_id",
  "status": "queued",
  "message": "Transaction queued for processing"
}
```

### Check Status
```bash
curl http://localhost:8000/transactions/{task_id}/status
```

---

## 8. Run Demo Scripts (Optional)

### Simulate Batch Transactions
```bash
python scripts/transaction_simulator.py
```

### Run Regulatory Crawlers
```bash
python cron/external_rules_ingestion.py
```

---

## Troubleshooting

### Issue: Celery not connecting to Redis
**Solution:** Check Redis is running on port 6379
```bash
redis-cli ping  # Should return PONG
```

### Issue: Database connection failed
**Solution:** Verify PostgreSQL connection string in .env
```bash
psql $DATABASE_URL -c "SELECT 1"
```

### Issue: Qdrant not accessible
**Solution:** Check Docker container is running
```bash
curl http://localhost:6333/health  # Should return 200
```

### Issue: Import errors
**Solution:** Reinstall dependencies
```bash
pip install --upgrade -r requirements.txt
```

---

## Quick Command Reference

```bash
# Start all services (requires tmux or separate terminals)
redis-server
docker run -p 6333:6333 qdrant/qdrant
celery -A worker.celery_app worker --loglevel=info
uvicorn app.main:app --reload

# Check logs
tail -f logs/app.log

# Stop all services
pkill redis-server
docker stop $(docker ps -q --filter ancestor=qdrant/qdrant)
pkill celery
pkill uvicorn
```

---

## API Endpoints Quick Reference

### Transactions (Part 1 - Async)
- `POST /transactions` - Submit transaction
- `GET /transactions/{id}/status` - Check processing status
- `GET /transactions/{id}/compliance` - Get compliance report

### Documents (Part 2 - Sync)
- `POST /documents/upload` - Upload document (immediate processing)
- `GET /documents/{id}/risk` - Get risk assessment
- `GET /documents/{id}/report` - Get detailed report

### Internal Rules
- `POST /internal_rules` - Create rule (auto-embedded in vector DB)
- `GET /internal_rules` - List all rules
- `PUT /internal_rules/{id}` - Update rule
- `DELETE /internal_rules/{id}` - Delete rule

### Alerts
- `GET /alerts` - List alerts (filter by role, severity, status)
- `POST /alerts/{id}/acknowledge` - Acknowledge alert
- `GET /alerts/dashboard/stats` - Get dashboard statistics

### Cases
- `GET /cases` - List cases
- `POST /cases` - Create case
- `PUT /cases/{id}` - Update case
- `POST /cases/{id}/close` - Close case

---

## Performance Tips

1. **Scale Celery workers** for higher throughput:
   ```bash
   celery -A worker.celery_app worker --concurrency=4
   ```

2. **Use Redis connection pooling** (already configured)

3. **Enable Qdrant indexing** for faster vector search:
   ```python
   # Already configured in VectorDBService
   ```

4. **Monitor with Flower** (Celery monitoring):
   ```bash
   pip install flower
   celery -A worker.celery_app flower
   # Open http://localhost:5555
   ```

---

## Support

- **Documentation:** See README.md, AGENTIC_AML_WORKFLOW_PLAN.md
- **Implementation Details:** See FINAL_IMPLEMENTATION_REPORT.md
- **API Reference:** http://localhost:8000/docs

---

**Ready to go! 🚀**
