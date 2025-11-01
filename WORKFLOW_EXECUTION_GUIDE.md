# Running the Transaction Workflow with Detailed Logging

This guide explains how to execute the Part 1 transaction monitoring workflow and see detailed output at each step.

## Quick Start

### 1. Run the Test Script

```bash
cd /Users/chenxiangrui/Projects/slenth
python scripts/test_workflow_execution.py
```

This will:
- ✅ Set up comprehensive logging
- ✅ Initialize services (Groq LLM, Pinecone)
- ✅ Create a sample high-risk transaction
- ✅ Execute all 13 agents in sequence
- ✅ Save detailed logs and results
- ✅ Display a summary

### 2. View Output

**Console Output:** Shows INFO-level logs with key steps
**Log File:** Saved to `data/logs/workflow_execution_YYYYMMDD_HHMMSS.log` (DEBUG-level details)
**Results File:** Saved to `data/workflow_results/workflow_result_YYYYMMDD_HHMMSS.json`

---

## Testing Different Scenarios

Edit line 395 in `scripts/test_workflow_execution.py`:

```python
# Change the scenario:
transaction = create_sample_transaction(scenario="high_risk")     # Default
# transaction = create_sample_transaction(scenario="medium_risk")
# transaction = create_sample_transaction(scenario="low_risk")
# transaction = create_sample_transaction(scenario="structuring")
```

**Scenarios:**
- `high_risk`: $250K wire transfer, HK → SG, high-risk customer
- `medium_risk`: $50K business payment, US → UK
- `low_risk`: $5K personal transfer, domestic
- `structuring`: $9.5K to Mexico (multiple similar transactions)

---

## Understanding the Output

### Console Output Structure

```
================================================================================
Logging configured:
  Console: INFO level
  File: data/logs/workflow_execution_20251101_143022.log
  File level: DEBUG
================================================================================

2025-11-01 14:30:22 - INFO - Initializing database...
2025-11-01 14:30:22 - INFO - Initializing services...
2025-11-01 14:30:22 - INFO -   - LLM Service (Groq)
2025-11-01 14:30:22 - INFO -   - Pinecone Internal Index
2025-11-01 14:30:22 - INFO -   - Pinecone External Index

2025-11-01 14:30:23 - INFO - Creating sample transaction...
2025-11-01 14:30:23 - INFO - Created transaction: TXN_20251101_143023

2025-11-01 14:30:23 - INFO - Executing workflow...

================================================================================
STARTING TRANSACTION WORKFLOW EXECUTION
================================================================================
Transaction ID: TXN_20251101_143023
Amount: USD 250,000.00
Route: HK → SG
Customer Risk: high
================================================================================

[Each agent executes here with its own logging...]

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

### Summary Report

After execution, you'll see:

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

🔢 Features Extracted: 15
  High Value: True
  Cross-Border: True

🎯 Patterns Detected: 2
  - structuring: Multiple transactions below threshold
  - velocity: High transaction frequency

🚨 Alerts Generated: 2
  - High: Large wire transfer to high-risk jurisdiction
  - Medium: Customer profile inconsistent with transaction

📝 Compliance Analysis:
  Transaction presents elevated risk due to high value, cross-border nature...

🔧 Remediation Actions: 3
  - manual_review: Flag for analyst review
  - kyc_refresh: Update customer due diligence
  - enhanced_monitoring: Monitor next 10 transactions

⏱️  Performance:
  Processing Time: 12.34s
```

---

## Detailed Log File

The log file contains DEBUG-level details including:

- **Agent Execution:** Start/end timestamps for each agent
- **LLM Calls:** Full prompts and responses from Groq
- **Vector Searches:** Queries sent to Pinecone and results returned
- **Feature Extraction:** All calculated features
- **Bayesian Inference:** Probability calculations
- **Pattern Detection:** Pattern matching logic
- **Decision Fusion:** Risk score calculation details
- **Database Operations:** All DB queries and insertions

Example log entries:

```
2025-11-01 14:30:25 - agents.part1.retrieval - DEBUG - execute:45 - Query context length: 342
2025-11-01 14:30:25 - agents.part1.retrieval - INFO - execute:52 - Searching internal rules index...
2025-11-01 14:30:26 - services.pinecone_db - DEBUG - search_by_text:78 - Pinecone search: top_k=10
2025-11-01 14:30:26 - agents.part1.retrieval - INFO - execute:57 - Found 8 internal rules
```

---

## Adding Logging to Individual Agents

To see more detailed logs from specific agents, add logging statements:

### Example: Update `agents/part1/retrieval.py`

```python
import logging
import time

logger = logging.getLogger(__name__)

class RetrievalAgent:
    async def execute(self, state):
        start_time = time.time()
        
        # Log start
        logger.info("="*60)
        logger.info(f"🚀 RetrievalAgent - Starting")
        logger.info(f"Transaction: {state.get('transaction_id')}")
        
        # Your existing code...
        query_context = state.get("query_context", "")
        logger.debug(f"Query context: {query_context[:100]}...")
        
        # Search
        logger.info("Searching internal rules...")
        internal_results = await self.pinecone_internal.search_by_text(...)
        logger.info(f"Found {len(internal_results)} rules")
        
        # Log completion
        duration = time.time() - start_time
        logger.info(f"✅ RetrievalAgent - Completed in {duration:.3f}s")
        logger.info("="*60)
        
        return {
            **state,
            "retrieved_rules": internal_results,
            "retrieval_executed": True,
        }
```

See `scripts/agent_logging_config.py` for helper functions and examples.

---

## Inspecting Results Programmatically

### Load and analyze results:

```python
import json

# Load results
with open('data/workflow_results/workflow_result_20251101_143023.json') as f:
    result = json.load(f)

# Inspect specific parts
print(f"Risk Score: {result['risk_score']}")
print(f"Applicable Rules: {len(result['applicable_rules'])}")

# Check each agent's execution
for agent in ['context_builder', 'retrieval', 'applicability', ...]:
    key = f"{agent}_executed"
    print(f"{agent}: {result.get(key, False)}")

# View alerts
for alert in result.get('alerts', []):
    print(f"Alert: {alert['severity']} - {alert['title']}")
```

---

## Troubleshooting

### Issue: Services not initialized

**Error:** `No module named 'services'`

**Solution:**
```bash
# Make sure you're in the project root
cd /Users/chenxiangrui/Projects/slenth
python scripts/test_workflow_execution.py
```

### Issue: Environment variables missing

**Error:** `ValidationError: Field required`

**Solution:** Ensure your `.env` file has all required variables:
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your-key-here
GROQ_MODEL=openai/gpt-oss-20b
PINECONE_API_KEY=your-key-here
PINECONE_INTERNAL_INDEX_HOST=https://...
PINECONE_EXTERNAL_INDEX_HOST=https://...
DATABASE_URL=postgresql://...
```

### Issue: Pinecone connection fails

**Error:** `PineconeException: Failed to connect`

**Solution:** 
1. Verify your `PINECONE_API_KEY` is correct
2. Check index hosts are properly set
3. Ensure indexes exist in Pinecone dashboard

### Issue: Groq API errors

**Error:** `GroqException: Rate limit exceeded`

**Solution:**
1. Check your Groq API key
2. Implement rate limiting in `services/llm.py`
3. Use a different model with higher limits

---

## Running in Production

For production deployment:

1. **Use Celery worker:**
   ```bash
   celery -A worker.celery_app worker --loglevel=info
   ```

2. **Submit transactions via API:**
   ```bash
   curl -X POST http://localhost:8000/api/transactions \
     -H "Content-Type: application/json" \
     -d @sample_transaction.json
   ```

3. **Monitor with logs:**
   ```bash
   tail -f data/logs/workflow_execution_*.log
   ```

---

## Next Steps

1. ✅ Run the test script to verify workflow execution
2. ✅ Review logs to understand each agent's behavior
3. ✅ Add custom logging to specific agents you're debugging
4. ✅ Test different transaction scenarios
5. ✅ Integrate with your frontend/API layer
6. ✅ Set up monitoring and alerting

---

## Files Created

- `scripts/test_workflow_execution.py` - Main test script
- `scripts/agent_logging_config.py` - Logging utilities
- `data/logs/workflow_execution_*.log` - Execution logs
- `data/workflow_results/workflow_result_*.json` - Results data
- `WORKFLOW_EXECUTION_GUIDE.md` - This file

**Happy testing!** 🚀
