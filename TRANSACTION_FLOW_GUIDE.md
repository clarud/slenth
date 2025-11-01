# Transaction Processing Flow Documentation

## Overview

This document explains how the transaction processing flow works in the Slenth AML system, from transaction submission to final compliance analysis.

## Architecture Components

### 1. **Transaction Simulator** (`scripts/transaction_simulator.py`)
- **Purpose**: Simulates bulk transaction submissions from CSV files
- **Location**: `scripts/transaction_simulator.py`
- **CSV Source**: `transactions_mock_1000_for_participants.csv`

### 2. **FastAPI REST API** (`app/api/transactions.py`)
- **Purpose**: Receives transaction submissions and queues them for processing
- **Endpoints**:
  - `POST /transactions` - Submit transaction (returns task_id)
  - `GET /transactions/{transaction_id}/status` - Check processing status
  - `GET /transactions/{transaction_id}/compliance` - Get compliance results

### 3. **Redis Message Broker**
- **Purpose**: Message queue for Celery tasks
- **Role**: Stores pending tasks until workers are available

### 4. **Celery Worker** (`worker/tasks.py`)
- **Purpose**: Asynchronous task processor
- **Configuration**: `worker/celery_app.py`
- **Main Task**: `process_transaction` - Orchestrates the workflow

### 5. **Transaction Workflow** (`workflows/transaction_workflow.py`)
- **Purpose**: Executes 13-agent analysis pipeline
- **Agents**: Context Builder → Retrieval → Applicability → Evidence Mapper → Control Test → Feature Service → Bayesian Engine → Pattern Detector → Decision Fusion → Analyst Writer → Alert Composer → Remediation → Persistor

### 6. **PostgreSQL Database**
- **Tables**:
  - `transactions` - Transaction records
  - `compliance_analysis` - Analysis results
  - `alerts` - Generated alerts
  - `audit_logs` - Audit trail

## Transaction Flow (Step-by-Step)

### Step 1: Transaction Creation
```python
# Transaction Simulator creates a transaction from CSV
transaction = {
    "transaction_id": "TXN_20251102_001",
    "amount": 250000.0,
    "currency": "USD",
    "originator_country": "HK",
    "beneficiary_country": "SG",
    "customer_risk_rating": "high",
    # ... more fields
}
```

### Step 2: API Submission
```python
# POST /transactions
response = requests.post(
    "http://localhost:8000/transactions",
    json=transaction
)

# Returns:
{
    "transaction_id": "TXN_20251102_001",
    "task_id": "abc123-def456-...",
    "status": "queued",
    "message": "Transaction queued for processing"
}
```

**What happens internally:**
1. FastAPI endpoint receives transaction
2. Creates `Transaction` record in PostgreSQL (status: PROCESSING)
3. Calls `process_transaction.delay(transaction)` - queues to Redis
4. Stores `task_id` in transaction metadata
5. Returns immediately with `task_id`

### Step 3: Redis Queuing
```
Redis Queue: [task_1, task_2, task_3, ...]
             ↓
        Celery Worker (pulls tasks)
```

- Task stored in Redis with serialized transaction data
- Redis acts as FIFO queue
- Multiple workers can pull tasks concurrently

### Step 4: Celery Worker Execution
```python
# worker/tasks.py: process_transaction task
@celery_app.task(bind=True, name="process_transaction")
def process_transaction(self, transaction: Dict[str, Any]):
    # 1. Update task state to "PROCESSING"
    self.update_state(state="PROCESSING", meta={...})
    
    # 2. Initialize services
    llm_service = LLMService()  # Groq
    pinecone_internal = PineconeService(index_type="internal")
    pinecone_external = PineconeService(index_type="external")
    
    # 3. Execute workflow
    final_state = asyncio.run(
        execute_transaction_workflow(
            transaction=transaction,
            db_session=db,
            llm_service=llm_service,
            pinecone_internal=pinecone_internal,
            pinecone_external=pinecone_external,
        )
    )
    
    # 4. Return results
    return {
        "status": "completed",
        "risk_score": final_state.get("risk_score"),
        "risk_band": final_state.get("risk_band"),
        # ...
    }
```

### Step 5: Workflow Execution (13 Agents)

**Agent Pipeline:**

1. **Context Builder** - Builds transaction context, historical data
2. **Retrieval** - Retrieves 20 relevant rules from Pinecone
3. **Applicability** - Filters to ~5 applicable rules using LLM
4. **Evidence Mapper** - Maps transaction fields to rule requirements
5. **Control Test** - Tests compliance against each rule (~4 tests)
6. **Feature Service** - Extracts 20+ risk features
7. **Bayesian Engine** - Calculates posterior probabilities
8. **Pattern Detector** - Detects suspicious patterns
9. **Decision Fusion** - Aggregates signals into risk score (0-100)
10. **Analyst Writer** - Generates compliance narrative
11. **Alert Composer** - Creates alerts if needed
12. **Remediation** - Suggests remediation actions
13. **Persistor** - Saves results to database

**Processing Time:** ~18-35 seconds per transaction

### Step 6: Database Persistence

**Tables Updated:**
```sql
-- Update transaction status
UPDATE transactions 
SET status = 'COMPLETED',
    processing_completed_at = NOW()
WHERE transaction_id = 'TXN_20251102_001';

-- Create compliance analysis
INSERT INTO compliance_analysis (
    transaction_id,
    compliance_score,
    risk_band,
    applicable_rules,
    control_test_results,
    processing_time_seconds,
    ...
) VALUES (...);

-- Create alert
INSERT INTO alerts (
    alert_id,
    transaction_id,
    severity,
    title,
    description,
    ...
) VALUES (...);
```

### Step 7: Status Check

```python
# GET /transactions/{transaction_id}/status
response = requests.get(
    f"http://localhost:8000/transactions/{transaction_id}/status"
)

# Returns:
{
    "transaction_id": "TXN_20251102_001",
    "task_id": "abc123-def456-...",
    "task_status": "SUCCESS",  # or PENDING, PROCESSING, FAILURE
    "status": "completed",
    "risk_score": 40.0,
    "risk_band": "Medium",
    "processing_time": 18.5
}
```

## How to Test the Full Flow

### Prerequisites
```bash
# 1. Start PostgreSQL (should already be running)
# Your Supabase instance

# 2. Start Redis
redis-server

# 3. Start Celery Worker
celery -A worker.celery_app worker --loglevel=info

# 4. Start FastAPI Server
python -m uvicorn app.main:app --reload
```

### Option 1: Use the Test Script (Recommended)
```bash
# Run the comprehensive test
python scripts/test_full_transaction_flow.py

# With custom API URL
python scripts/test_full_transaction_flow.py --api-url http://localhost:8000
```

**What it does:**
1. ✅ Creates a test transaction
2. ✅ Submits to API endpoint
3. ✅ Monitors Celery task status (polls every 2s)
4. ✅ Verifies database records
5. ✅ Displays detailed results

**Expected Output:**
```
🚀 STARTING FULL TRANSACTION FLOW TEST
======================================================================
✅ Created test transaction: TEST_20251102_001234
======================================================================
📤 STEP 1: Submitting transaction to API
======================================================================
   Endpoint: http://localhost:8000/transactions
   ✅ Transaction queued successfully!
   Task ID: abc123-def456-...
   
======================================================================
⏳ STEP 2: Monitoring Celery task execution
======================================================================
   Status: SUCCESS         | Elapsed:  19s
   ✅ Task completed successfully!
   
======================================================================
🔍 STEP 3: Verifying database persistence
======================================================================
   ✅ Transaction record found
   ✅ Compliance analysis found
      Risk Score: 40.0
      Risk Band: MEDIUM
      Processing Time: 18.69s
   ✅ Found 1 alert(s)
      • MEDIUM: Transaction Risk Alert: Medium

✅ TEST COMPLETED SUCCESSFULLY!
```

### Option 2: Use Transaction Simulator (Bulk Testing)
```bash
# Submit 100 transactions in batches
python scripts/transaction_simulator.py
```

**Configuration in `transaction_simulator.py`:**
```python
simulator.simulate(
    csv_path=str(csv_path),
    batch_size=10,    # 10 transactions per batch
    delay=2.0         # 2 second delay between batches
)
```

### Option 3: Manual API Testing
```bash
# Submit a transaction
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TEST_MANUAL_001",
    "amount": 250000.0,
    "currency": "USD",
    "originator_country": "HK",
    "beneficiary_country": "SG",
    "customer_id": "CUST_001",
    "customer_risk_rating": "high",
    "booking_jurisdiction": "HK",
    "regulator": "HKMA",
    "booking_datetime": "2025-11-02T00:00:00Z"
  }'

# Check status (use task_id from response)
curl http://localhost:8000/transactions/TEST_MANUAL_001/status

# Get compliance results
curl http://localhost:8000/transactions/TEST_MANUAL_001/compliance
```

## Monitoring & Debugging

### Check Celery Worker Logs
```bash
# Worker should show:
[2025-11-02 00:00:00,000: INFO/MainProcess] Task process_transaction[abc123] received
[2025-11-02 00:00:00,000: INFO/ForkPoolWorker-1] Task abc123: Processing transaction TEST_001
[2025-11-02 00:00:18,000: INFO/ForkPoolWorker-1] Task abc123: Completed transaction TEST_001
[2025-11-02 00:00:18,000: INFO/MainProcess] Task process_transaction[abc123] succeeded
```

### Check Redis Queue
```bash
# Connect to Redis CLI
redis-cli

# Check pending tasks
KEYS celery-task-meta-*
LLEN celery  # Queue length

# Check task status
GET celery-task-meta-abc123-def456-...
```

### Check Database
```sql
-- Check recent transactions
SELECT transaction_id, status, processing_started_at, processing_completed_at
FROM transactions
ORDER BY created_at DESC
LIMIT 10;

-- Check compliance analysis
SELECT t.transaction_id, c.compliance_score, c.risk_band, c.processing_time_seconds
FROM transactions t
JOIN compliance_analysis c ON c.transaction_id = t.id
ORDER BY t.created_at DESC
LIMIT 10;

-- Check alerts
SELECT a.alert_id, a.severity, a.title, t.transaction_id
FROM alerts a
JOIN transactions t ON a.transaction_id = t.id
ORDER BY a.created_at DESC
LIMIT 10;
```

## Performance Characteristics

- **API Response Time**: < 100ms (just queues to Redis)
- **Workflow Processing**: 18-35 seconds per transaction
- **Throughput**: ~100-200 transactions/minute (with 4 workers)
- **Scalability**: Horizontal (add more Celery workers)

## Error Handling

### Task Failure
- Task state set to "FAILURE" in Celery
- Error logged in Celery worker
- Transaction status updated to "FAILED" in database
- Error details available via status endpoint

### Retry Mechanism
- Currently no automatic retries
- Can be configured in `celery_app.py`:
```python
@celery_app.task(bind=True, autoretry_for=(Exception,), max_retries=3)
def process_transaction(self, transaction):
    ...
```

## Summary

The transaction flow is a **fully asynchronous, scalable pipeline** that:
1. ✅ Accepts transactions via REST API
2. ✅ Queues to Redis for reliable processing
3. ✅ Processes via Celery workers (can scale horizontally)
4. ✅ Executes 13-agent AI workflow for compliance analysis
5. ✅ Persists results to PostgreSQL
6. ✅ Provides real-time status tracking
7. ✅ Takes ~18-35 seconds end-to-end

**Use the test script** to verify your complete setup is working correctly!
