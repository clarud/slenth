# How to Trigger and Monitor the Agentic Workflow

## 🚀 Quick Start (Simplest Method)

```bash
cd /Users/chenxiangrui/Projects/slenth
python scripts/test_workflow_execution.py
```

This will execute the workflow with **detailed logging** showing every step.

---

## 📋 What You'll See

### 1. **Console Output** (Real-time)

```
================================================================================
STARTING TRANSACTION WORKFLOW EXECUTION
================================================================================
Transaction ID: TXN_20251101_143023
Amount: USD 250,000.00
Route: HK → SG
Customer Risk: high
================================================================================

2025-11-01 14:30:25 - INFO - Transaction workflow compiled successfully
2025-11-01 14:30:26 - INFO - ContextBuilder executed
2025-11-01 14:30:27 - INFO - Retrieval executed - Found 8 rules
2025-11-01 14:30:28 - INFO - Applicability executed - 5 rules applicable
2025-11-01 14:30:29 - INFO - EvidenceMapper executed
2025-11-01 14:30:30 - INFO - ControlTest executed - 3 failed, 2 passed
2025-11-01 14:30:31 - INFO - FeatureService executed - 15 features extracted
2025-11-01 14:30:32 - INFO - BayesianEngine executed
2025-11-01 14:30:33 - INFO - PatternDetector executed - 2 patterns found
2025-11-01 14:30:34 - INFO - DecisionFusion executed - Risk Score: 85
2025-11-01 14:30:35 - INFO - AnalystWriter executed
2025-11-01 14:30:36 - INFO - AlertComposer executed - 2 alerts created
2025-11-01 14:30:37 - INFO - RemediationOrchestrator executed - 3 actions
2025-11-01 14:30:38 - INFO - Persistor executed

================================================================================
WORKFLOW EXECUTION COMPLETED
================================================================================
Final Risk Score: 85
Risk Band: High
Applicable Rules: 5
Alerts Generated: 2
Processing Time: 12.34s
================================================================================
```

### 2. **Detailed Log File** (All debug info)

Saved to: `data/logs/workflow_execution_20251101_143023.log`

Contains:
- Full LLM prompts and responses
- Vector search queries and results
- Feature extraction details
- Bayesian probability calculations
- Pattern detection logic
- Complete state at each step

### 3. **JSON Results File** (Structured data)

Saved to: `data/workflow_results/workflow_result_20251101_143023.json`

```json
{
  "transaction_id": "TXN_20251101_143023",
  "risk_score": 85,
  "risk_band": "High",
  "applicable_rules": [...],
  "control_results": [...],
  "features": {...},
  "detected_patterns": [...],
  "alerts": [...],
  "compliance_analysis": "...",
  "remediation_actions": [...],
  "processing_time": 12.34
}
```

### 4. **Summary Report** (Human-readable)

```
================================================================================
WORKFLOW EXECUTION SUMMARY
================================================================================

📊 Transaction:
  ID: TXN_20251101_143023
  Amount: USD 250,000.00

⚠️  Risk Assessment:
  Risk Score: 85
  Risk Band: High

📋 Rules Analysis:
  Retrieved Rules: 8
  Applicable Rules: 5

🔍 Control Tests: 5
  Passed: 2
  Failed: 3

🎯 Patterns Detected: 2
  - structuring: Multiple transactions below threshold
  - velocity: High transaction frequency

🚨 Alerts Generated: 2
  - High: Large wire transfer to high-risk jurisdiction
  - Medium: Customer profile inconsistent

📝 Compliance Analysis:
  Transaction presents elevated risk due to...

🔧 Remediation Actions: 3
  - manual_review: Flag for analyst review
  - kyc_refresh: Update customer due diligence

⏱️  Performance:
  Processing Time: 12.34s
```

---

## 🎯 Testing Different Scenarios

Edit `scripts/test_workflow_execution.py` line 395:

```python
# Test different scenarios:
transaction = create_sample_transaction(scenario="high_risk")     # ✅ Default
# transaction = create_sample_transaction(scenario="medium_risk") # 🟡 Medium
# transaction = create_sample_transaction(scenario="low_risk")    # 🟢 Low
# transaction = create_sample_transaction(scenario="structuring") # 🔴 Structuring
```

**Scenarios:**

| Scenario | Amount | Route | Risk | Description |
|----------|--------|-------|------|-------------|
| `high_risk` | $250K | HK→SG | High | Large cross-border transfer |
| `medium_risk` | $50K | US→UK | Medium | Business payment |
| `low_risk` | $5K | US→US | Low | Domestic personal transfer |
| `structuring` | $9.5K | US→MX | Medium | Below threshold, suspicious |

---

## 🔍 Understanding Agent Flow

The workflow executes **13 agents sequentially**:

```
1. ContextBuilder       → Builds query context from transaction
                           Output: query_context, transaction_history
                           
2. Retrieval           → Searches rules via Pinecone embeddings
                          Output: retrieved_rules (internal + external)
                          
3. Applicability       → LLM determines which rules apply
                          Output: applicable_rules
                          
4. EvidenceMapper      → Maps evidence requirements
                          Output: evidence_mapping (present/missing)
                          
5. ControlTest         → Tests controls, pass/fail determination
                          Output: control_results
                          
6. FeatureService      → Extracts transaction features
                          Output: features (15+ features)
                          
7. BayesianEngine      → Calculates risk probabilities
                          Output: posterior_probabilities
                          
8. PatternDetector     → Detects suspicious patterns
                          Output: detected_patterns
                          
9. DecisionFusion      → Fuses signals into risk score
                          Output: risk_score, risk_band
                          
10. AnalystWriter      → Generates compliance narrative
                           Output: compliance_analysis
                           
11. AlertComposer      → Creates alerts for high risk
                           Output: alerts[]
                           
12. RemediationOrch... → Suggests remediation actions
                           Output: remediation_actions[]
                           
13. Persistor          → Saves to database
                           Output: persistor_executed
```

---

## 🛠️ Adding Custom Logging to Agents

To see more detail from specific agents, add logging:

### Example: `agents/part1/retrieval.py`

```python
import logging
import time

logger = logging.getLogger(__name__)

class RetrievalAgent:
    async def execute(self, state):
        start_time = time.time()
        
        # 📝 Log start
        logger.info("="*60)
        logger.info("🚀 RETRIEVAL AGENT - Starting")
        logger.info(f"   Transaction: {state.get('transaction_id')}")
        logger.info("="*60)
        
        # Get context
        query_context = state.get("query_context", "")
        logger.debug(f"Query context: {query_context[:200]}...")
        
        # 🔍 Search internal rules
        logger.info("Searching internal rules index...")
        internal_results = await self.pinecone_internal.search_by_text(
            query_text=query_context,
            top_k=10
        )
        logger.info(f"✅ Found {len(internal_results)} internal rules")
        
        # Log sample
        if internal_results:
            sample = internal_results[0]
            logger.debug(f"Sample rule: {sample.get('metadata', {}).get('rule_id')}")
        
        # 🔍 Search external rules
        logger.info("Searching external rules index...")
        external_results = await self.pinecone_external.search_by_text(
            query_text=query_context,
            top_k=5
        )
        logger.info(f"✅ Found {len(external_results)} external rules")
        
        # Combine
        all_rules = internal_results + external_results
        
        # 📊 Log completion
        duration = time.time() - start_time
        logger.info("-"*60)
        logger.info(f"✅ RETRIEVAL AGENT - Completed")
        logger.info(f"   Total rules: {len(all_rules)}")
        logger.info(f"   Duration: {duration:.3f}s")
        logger.info("="*60)
        
        return {
            **state,
            "retrieved_rules": all_rules,
            "retrieval_executed": True,
        }
```

---

## 📊 Inspecting Results Programmatically

### Load and analyze:

```python
import json

# Load results
with open('data/workflow_results/workflow_result_20251101_143023.json') as f:
    result = json.load(f)

# Check risk assessment
print(f"Risk Score: {result['risk_score']}")
print(f"Risk Band: {result['risk_band']}")

# Check agent execution
agents = [
    'context_builder', 'retrieval', 'applicability', 'evidence_mapper',
    'control_test', 'feature_service', 'bayesian_engine', 'pattern_detector',
    'decision_fusion', 'analyst_writer', 'alert_composer', 
    'remediation_orchestrator', 'persistor'
]

for agent in agents:
    executed = result.get(f"{agent}_executed", False)
    status = "✅" if executed else "❌"
    print(f"{status} {agent}")

# View alerts
for alert in result.get('alerts', []):
    print(f"🚨 {alert['severity']}: {alert['title']}")

# View remediation actions
for action in result.get('remediation_actions', []):
    print(f"🔧 {action['action_type']}: {action['description']}")
```

---

## 🐛 Troubleshooting

### Import Errors

```bash
# Install missing dependencies
pip install langgraph langchain-openai pinecone groq sqlalchemy
```

### Environment Variables Missing

Check your `.env` file has:

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-20b
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INTERNAL_INDEX_HOST=https://internal-rules-xxx.pinecone.io
PINECONE_EXTERNAL_INDEX_HOST=https://external-rules-xxx.pinecone.io
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=your-secret-key
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Database Connection Fails

```python
# In test script, comment out database operations temporarily
# db_session = SessionLocal()  # Comment this
db_session = None  # Use None for testing without DB
```

### Pinecone Index Not Found

Check your Pinecone dashboard:
1. Indexes exist: `internal-rules`, `external-rules`
2. Inference API enabled
3. Index hosts are correct in `.env`

---

## 🚀 Alternative Execution Methods

### Method 1: Direct Python (Simplest)

```bash
python scripts/test_workflow_execution.py
```

### Method 2: With Shell Script

```bash
chmod +x scripts/run_workflow_test.sh
./scripts/run_workflow_test.sh
```

### Method 3: Via Celery Worker (Production)

```bash
# Start worker
celery -A worker.celery_app worker --loglevel=info

# In another terminal, submit task
python -c "
from worker.tasks import process_transaction
result = process_transaction.delay({
    'transaction_id': 'TXN001',
    'amount': 50000,
    'currency': 'USD'
})
print(result.get())
"
```

### Method 4: Via API (Production)

```bash
# Start FastAPI server
uvicorn app.main:app --reload

# Submit transaction
curl -X POST http://localhost:8000/api/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN001",
    "amount": 50000,
    "currency": "USD",
    "customer_id": "CUST123"
  }'
```

### Method 5: Interactive Python Shell

```python
import asyncio
from sqlalchemy.orm import Session
from db.database import SessionLocal
from services.llm import LLMService
from services.pinecone_db import PineconeService
from workflows.transaction_workflow import execute_transaction_workflow

# Setup
db = SessionLocal()
llm = LLMService()
pinecone_internal = PineconeService(index_type="internal")
pinecone_external = PineconeService(index_type="external")

# Transaction
transaction = {
    "transaction_id": "TXN_TEST",
    "amount": 75000,
    "currency": "USD",
    "customer_id": "CUST456"
}

# Execute
result = asyncio.run(execute_transaction_workflow(
    transaction, db, llm, pinecone_internal, pinecone_external
))

# Inspect
print(f"Risk Score: {result['risk_score']}")
print(f"Alerts: {len(result['alerts'])}")
```

---

## 📁 Files Created

1. **`scripts/test_workflow_execution.py`** - Main test script with logging
2. **`scripts/agent_logging_config.py`** - Logging helper functions
3. **`scripts/run_workflow_test.sh`** - Shell script for easy execution
4. **`WORKFLOW_EXECUTION_GUIDE.md`** - Detailed execution guide
5. **`WORKFLOW_EXECUTION_HOWTO.md`** - This quick reference

---

## ✅ Next Steps

1. **Run the test script:**
   ```bash
   python scripts/test_workflow_execution.py
   ```

2. **Review the output:**
   - Check console for summary
   - Read log file for details
   - Inspect JSON for raw data

3. **Test different scenarios:**
   - Edit scenario in test script
   - Run again and compare results

4. **Add custom logging:**
   - Update specific agents
   - See more detailed execution

5. **Integrate with your app:**
   - Use via Celery for async processing
   - Use via API for production
   - Monitor logs in real-time

**Happy workflow testing!** 🎉
