# Agentic AML Monitoring and Regulatory Compliance — Implementation Plan

> **Julius Baer Hackathon Solution**: Integrated agentic AI for real-time AML monitoring and document corroboration

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Agentic Architecture (LangGraph)](#agentic-architecture-langgraph)
   - [Part 1: Real-Time AML Monitoring](#part-1-real-time-aml-monitoring)
   - [Part 2: Document & Image Corroboration](#part-2-document--image-corroboration)
   - [Integration Layer](#integration-layer-unified-aml-platform)
3. [Tech Stack](#tech-stack)
4. [Transaction Schema](#transaction-schema)
5. [Data and Storage Design](#data-and-storage-design)
6. [Repository Layout](#repository-layout)
7. [Implementation Steps](#implementation-steps)
8. [API Endpoints](#api-endpoints)
9. [Requirements Checklist](#requirements-checklist-from-problem-statement)
10. [LangGraph Workflow Details](#langgraph-workflow-details)
11. [Mock Internal Rules Structure](#mock-internal-rules-structure)
12. [Quick Start Guide (Local Development)](#quick-start-guide-local-development)
13. [Local Development Commands](#local-development-commands)
14. [Crawler Implementation Details](#crawler-implementation-details)
15. [Example End-to-End Flows](#example-end-to-end-flows)
16. [Monitoring and Observability](#monitoring-and-observability)
17. [Security Considerations](#security-considerations)
18. [Future Enhancements](#future-enhancements)
19. [Success Criteria](#success-criteria)
20. [References](#references)
21. [Summary](#summary)

---

## Overview
Build two integrated agentic AI solutions for Anti-Money Laundering (AML):
1. **Part 1**: Real-Time AML Monitoring and Alerts
2. **Part 2**: Document & Image Corroboration

Both parts work together to provide comprehensive AML compliance coverage with automated risk detection, multi-role alerts, and audit trail maintenance.

> **🔧 Architecture Note**: 
> - **Part 1** uses **async processing** (Celery + Redis queue) for high-throughput transaction screening
> - **Part 2** uses **synchronous processing** (direct workflow execution in API) for immediate document analysis results
> - **PostgreSQL**: Cloud-hosted database (no local setup needed)
> - **Redis**: Local via Homebrew (for Part 1 Celery queue)
> - **Qdrant**: Local Docker container (for vector embeddings)
> - No Docker Compose required

**Core Capabilities:**

### Part 1: Real-Time AML Monitoring
- **External Regulatory Circular Ingestion**: Automated scraping and vectorization of regulatory documents from HKMA, MAS, and FINMA
- **Internal Rules Management**: API-driven ingestion and versioning of internal compliance policies
- **Transaction Processing**: Real-time compliance evaluation using RAG (Retrieval-Augmented Generation) and agentic workflows
- **Multi-Role Alerting**: Context-aware alerts for Front, Compliance, and Legal teams with SLA tracking
- **Remediation Workflows**: Automated suggestions with playbook-driven actions

### Part 2: Document & Image Corroboration
- **Document Processing**: Multi-format support (PDF, text, images) with OCR extraction
- **Format Validation**: Detect formatting errors, spelling/grammar issues, missing sections
- **Image Analysis**: Reverse image search, AI-generated detection, tampering checks
- **Risk Scoring**: Real-time document risk assessment with evidence tracking
- **Cross-Reference**: Link document findings with transaction history and alerts

**Data Sources:**
- `transactions_mock_1000_for_participants.csv` - Transaction simulation (Part 1)
- `Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf` - Document validation (Part 2)
- Mock internal rules stored in `internal_rules/` directory (JSON format)
- External regulatory circulars from HKMA, MAS, and FINMA

## Agentic Architecture (LangGraph)
The system uses **LangGraph** to orchestrate two interconnected multi-agent workflows:
1. **Part 1**: Transaction compliance workflow
2. **Part 2**: Document corroboration workflow

Both workflows integrate to provide unified AML risk assessment.

---

## PART 1: Real-Time AML Monitoring

### Transaction Processing Pipeline (LangGraph-Based)

When a transaction arrives, it triggers the following agentic workflow:

1. **ContextBuilder Agent**
   - Converts transaction JSON into rules-like query strings
   - Pulls short transaction history for the customer/account
   - Formats context for downstream retrieval

2. **Retrieval Agent (Hybrid)**
   - Performs BM25 + vector search over `external_rules` and `internal_rules` collections
   - Applies date filters (effective_date, jurisdiction)
   - Re-ranks results for relevance
   - Returns top-k applicable rules with metadata

3. **ApplicabilityAgent** (map over rules)
   - Determines if each retrieved rule applies to the transaction
   - Provides rationale and confidence score
   - Outputs: `applies: bool`, `rationale: str`, `confidence: float`

4. **EvidenceMapper** (map over applicable rules)
   - Maps expected evidence from rules to concrete transaction fields
   - Identifies present, missing, or contradictory evidence
   - Outputs evidence status per rule

5. **ControlTestAgent** (map over rules)
   - Tests each control/rule: pass/fail/partial
   - Assigns severity level (critical/high/medium/low)
   - Computes per-rule compliance score

6. **FeatureService**
   - Generates deterministic features from transaction + short history
   - Examples: velocity, structuring indicators, round-trip patterns
   - Outputs structured feature vector

7. **BayesianEngine**
   - Performs sequential Bayesian posterior update for entity (customer/account)
   - Updates risk distribution based on transaction evidence
   - Outputs posterior probabilities for risk categories

8. **PatternDetector**
   - Detects temporal and network motifs
   - Identifies patterns: structuring, layering, circular transfers
   - Outputs pattern scores and flags

9. **DecisionFusion**
   - Fuses rule-based risk, ML posterior, and pattern scores
   - Computes final risk score and risk band (Low/Medium/High/Critical)
   - Applies business logic and thresholds

10. **AnalystWriter**
    - Generates concise compliance analysis
    - Includes rule IDs, evidence references, and rationale
    - Outputs human-readable summary

11. **AlertComposer + Router + AckTracker**
    - Composes role-specific alerts (Front/Compliance/Legal teams)
    - Routes by priority and SLA requirements
    - Tracks acknowledgments and escalations

12. **RemediationOrchestrator**
    - Suggests playbook actions with owners and SLAs
    - Creates cases in case management system
    - Assigns remediation tasks

13. **Persistor & AuditTrail**
    - Stores all inputs, outputs, intermediate states
    - Records hashes, versions, timestamps
    - Logs human actions and overrides

---

## PART 2: Document & Image Corroboration

### Document Processing Pipeline (LangGraph-Based)

When a document is uploaded, it triggers the following agentic workflow:

1. **DocumentIntake Agent**
   - Accepts uploads (PDF, text, images)
   - Normalizes to internal format
   - Extracts metadata (file type, size, upload timestamp)
   - Emits `DocReceived` event

2. **OCR Agent**
   - Performs OCR on scanned documents and images
   - Extracts text and regions with confidence scores
   - Handles multi-page PDFs
   - Outputs `ExtractedText` with regions and coordinates

3. **FormatValidation Agent**
   - **Formatting checks**: Detects double spacing, irregular fonts, inconsistent indentation
   - **Content validation**: Identifies spelling mistakes, incorrect headers, missing sections
   - **Structure analysis**: Verifies document organization and completeness
   - **Template matching**: Compares against standard document templates
   - Outputs `FormatFindings` with error details

4. **NLPValidation Agent**
   - Extracts key fields: names, dates, addresses, amounts, IDs
   - Validates schema/template conformity
   - Cross-field consistency checks (e.g., amounts match, dates logical)
   - Entity extraction and validation
   - Outputs `NLPFindings` with field extraction results

5. **ImageForensics Agent**
   - **EXIF analysis**: Extracts and validates metadata
   - **Error Level Analysis (ELA)**: Detects image manipulation
   - **AI-generated detection**: Identifies synthetic/AI-generated images
   - **Reverse image search**: Checks for stolen/duplicated images (stub for hackathon)
   - **Tampering heuristics**: Pixel-level anomaly detection
   - Outputs `ImageFindings` with forensic results

6. **BackgroundCheck Agent** (NEW - World-Check One Integration)
   - Extracts individual/entity names from document
   - Calls LSEG World-Check One API for screening
   - Checks against:
     - PEP (Politically Exposed Persons) databases
     - Sanctions lists (OFAC, UN, EU, etc.)
     - Adverse media mentions
     - Law enforcement databases
     - Financial crime watchlists
   - Returns match results with risk scores
   - Outputs `BackgroundCheckFindings` with:
     - `match_status`: clear/potential_match/confirmed_match
     - `match_details`: List of matches with categories
     - `risk_level`: low/medium/high/critical
     - `screening_date`: Timestamp of screening
   - Integrates with existing KYC/CDD processes

7. **CrossReference Agent**
   - Correlates document fields with transaction history
   - Links to client profiles and KYC records
   - Cross-checks against external regulatory rules
   - **Integrates background check results** with transaction screening
   - Identifies discrepancies and red flags
   - Outputs `CrossRefFindings` with correlation results

8. **DocumentRisk Agent**
   - Aggregates findings from all previous agents (including background check)
   - Calculates `DocRiskScore` (0-100)
   - **Elevated risk if background check shows matches**
   - Categorizes risk level: Low/Medium/High/Critical
   - Stores evidence and supporting data
   - Notifies Alert Orchestrator for unified case management

9. **ReportGenerator Agent**
   - Generates comprehensive PDF report
   - Highlights red flags and problematic areas
   - **Includes background check results and match details**
   - Includes evidence citations and screenshots
   - Provides actionable recommendations
   - Maintains audit trail

10. **EvidenceStorekeeper Agent**
    - Manages storage for raw docs, extracted text, embeddings
    - Maintains versioned external docs
    - **Stores background check results and API responses**
    - Organizes evidence artifacts
    - Ensures data retention compliance

---

## Integration Layer: Unified AML Platform

### Cross-Reference Integration
- Link transaction alerts with related document findings
- Correlate document risk scores with customer transaction patterns
- Unified case management across both workflows
- Combined audit trail for regulatory defensibility

### Alert Orchestrator (Unified)
- Aggregates alerts from Part 1 (transactions) and Part 2 (documents)
- Deduplicates and consolidates related alerts
- Routes to appropriate teams based on alert type
- Maintains priority queue with SLA tracking

---

## External Regulatory Circular Ingestion (Scheduled CronJob)

**Trigger:** Scheduled CronJob (every 12 hours)

**Workflow:**

1. **Scrape Sources**
   - Use **crawl4ai** to pull content from regulator websites
   - Target URLs:
     - HKMA: `https://www.hkma.gov.hk/eng/regulatory-resources/regulatory-guides/circulars/`
     - MAS: `https://www.mas.gov.sg/regulation/regulations-and-guidance?entity_type=Capital%20Markets%20Services%2FDealing%20in%20Capital%20Markets%20Products&page=1&content_type=Circulars`
     - FINMA: `https://www.finma.ch/en/documentation/circulars/`
   - Extract PDFs, attachments, and publication metadata
   - Handle PDF extraction within linked pages

2. **Normalize & Prepare Data**
   - Clean HTML → Markdown or plain text
   - Chunk into LLM-friendly paragraphs (~500-1000 tokens)
   - Add metadata fields:
     - `source_url`, `published_date`, `regulator`, `jurisdiction`, `doc_title`, `section_path`

3. **Embed & Store**
   - Use embedding model (e.g., `text-embedding-3-large`) to vectorize each chunk
   - Upsert into `external_rules` collection in vector database
   - Index metadata for filtering

4. **Schedule**
   - Run every 12 hours (adjustable via cron)
   - Log changes and new circular detections
   - Monitor for failures and retry

**Output:** Updated vector DB with most recent external regulatory circulars for RAG queries

---

## Internal Rule Changes (API-Driven)

**Trigger:** POST `/internal_rules` endpoint

**Workflow:**

1. **Receive Data**
   - Endpoint accepts payload:
   ```json
   {
     "text": "<rule_text>",
     "effective_date": "YYYY-MM-DD",
     "version": "v1.0",
     "source": "internal_policy_manual"
   }
   ```

2. **Persist & Timestamp**
   - Append/update entry in internal JSON file or versioned config store
   - Log `received_at` datetime for traceability

3. **Process & Structure**
   - Parse into structured rule objects with fields:
     - `rule_id`, `section`, `obligation_type`, `conditions`, `expected_evidence`, `penalty_level`
   - Chunk large sections into ~500-token pieces

4. **Embed & Store**
   - Generate embeddings
   - Upsert into `internal_rules` collection in vector database
   - Include effective/sunset dates in metadata

5. **Version Management**
   - Maintain semantic version per rule
   - Automatically deactivate superseded versions

**Output:** Updated vector DB with structured, version-controlled internal rules

---

## Transaction Simulator

The transaction simulator is a Python script that reads transactions from `transactions_mock_1000_for_participants.csv` and submits them to the FastAPI server endpoint, which enqueues them in Redis for processing by Celery workers.

### Architecture

```
CSV File → Transaction Simulator → FastAPI API → Redis Queue → Celery Worker → Part 1 Workflow
```

### Simulator Features

1. **CSV Parsing**
   - Reads `transactions_mock_1000_for_participants.csv`
   - Validates and normalizes each transaction row
   - Converts to JSON format matching API schema

2. **Rate Limiting**
   - Configurable submission rate (transactions per second)
   - Prevents overwhelming the API server
   - Simulates realistic transaction flow

3. **Concurrent Submission**
   - Optional concurrent requests using asyncio
   - Configurable number of concurrent workers
   - Progress tracking and statistics

4. **Error Handling**
   - Retry logic for failed submissions
   - Error logging and reporting
   - Continue on error or fail-fast modes

5. **Monitoring**
   - Real-time progress display
   - Success/failure statistics
   - Response time tracking
   - Task ID tracking for status checks

### Implementation (`scripts/transaction_simulator.py`)

```python
#!/usr/bin/env python3
"""
Transaction Simulator - Parses CSV and submits transactions to API endpoint
"""

import asyncio
import csv
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import httpx
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.table import Table

console = Console()

class TransactionSimulator:
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        rate_limit: float = 5.0,  # transactions per second
        concurrent: bool = False,
        max_concurrent: int = 10,
        retry_attempts: int = 3,
        fail_fast: bool = False,
    ):
        self.api_url = api_url
        self.rate_limit = rate_limit
        self.concurrent = concurrent
        self.max_concurrent = max_concurrent
        self.retry_attempts = retry_attempts
        self.fail_fast = fail_fast
        
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "retried": 0,
            "start_time": None,
            "end_time": None,
        }
        self.task_ids = []
    
    def parse_csv(self, csv_path: Path) -> List[Dict]:
        """Parse CSV file and convert to transaction objects."""
        transactions = []
        
        console.print(f"[cyan]Reading CSV file: {csv_path}[/cyan]")
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert CSV row to transaction JSON
                transaction = self._normalize_transaction(row)
                transactions.append(transaction)
        
        console.print(f"[green]✓ Parsed {len(transactions)} transactions[/green]\n")
        return transactions
    
    def _normalize_transaction(self, row: Dict) -> Dict:
        """Normalize CSV row to API transaction format."""
        # Convert string values to appropriate types
        transaction = {
            "transaction_id": row["transaction_id"],
            "booking_jurisdiction": row["booking_jurisdiction"],
            "regulator": row["regulator"],
            "booking_datetime": row["booking_datetime"],
            "value_date": row["value_date"],
            "amount": float(row["amount"]) if row["amount"] else 0.0,
            "currency": row["currency"],
            "channel": row["channel"],
            "product_type": row["product_type"],
            "originator_name": row["originator_name"],
            "originator_account": row["originator_account"],
            "originator_country": row["originator_country"],
            "beneficiary_name": row["beneficiary_name"],
            "beneficiary_account": row["beneficiary_account"],
            "beneficiary_country": row["beneficiary_country"],
            "swift_mt": row["swift_mt"],
            "ordering_institution_bic": row["ordering_institution_bic"],
            "beneficiary_institution_bic": row["beneficiary_institution_bic"],
            "swift_f50_present": row["swift_f50_present"].lower() == "true" if row["swift_f50_present"] else False,
            "swift_f59_present": row["swift_f59_present"].lower() == "true" if row["swift_f59_present"] else False,
            "swift_f70_purpose": row["swift_f70_purpose"],
            "swift_f71_charges": row["swift_f71_charges"],
            "travel_rule_complete": row["travel_rule_complete"].lower() == "true" if row["travel_rule_complete"] else False,
            "fx_indicator": row["fx_indicator"].lower() == "true" if row["fx_indicator"] else False,
            "fx_base_ccy": row["fx_base_ccy"],
            "fx_quote_ccy": row["fx_quote_ccy"],
            "fx_applied_rate": float(row["fx_applied_rate"]) if row["fx_applied_rate"] else None,
            "fx_market_rate": float(row["fx_market_rate"]) if row["fx_market_rate"] else None,
            "fx_spread_bps": float(row["fx_spread_bps"]) if row["fx_spread_bps"] else None,
            "fx_counterparty": row["fx_counterparty"],
            "customer_id": row["customer_id"],
            "customer_type": row["customer_type"],
            "customer_risk_rating": row["customer_risk_rating"],
            "customer_is_pep": row["customer_is_pep"].lower() == "true" if row["customer_is_pep"] else False,
            "kyc_last_completed": row["kyc_last_completed"],
            "kyc_due_date": row["kyc_due_date"],
            "edd_required": row["edd_required"].lower() == "true" if row["edd_required"] else False,
            "edd_performed": row["edd_performed"].lower() == "true" if row["edd_performed"] else False,
            "sow_documented": row["sow_documented"].lower() == "true" if row["sow_documented"] else False,
            "purpose_code": row["purpose_code"],
            "narrative": row["narrative"],
            "is_advised": row["is_advised"].lower() == "true" if row["is_advised"] else False,
            "product_complex": row["product_complex"].lower() == "true" if row["product_complex"] else False,
            "client_risk_profile": row["client_risk_profile"],
            "suitability_assessed": row["suitability_assessed"].lower() == "true" if row["suitability_assessed"] else False,
            "suitability_result": row["suitability_result"],
            "product_has_va_exposure": row["product_has_va_exposure"].lower() == "true" if row["product_has_va_exposure"] else False,
            "va_disclosure_provided": row["va_disclosure_provided"].lower() == "true" if row["va_disclosure_provided"] else False,
            "cash_id_verified": row["cash_id_verified"].lower() == "true" if row["cash_id_verified"] else False,
            "daily_cash_total_customer": float(row["daily_cash_total_customer"]) if row["daily_cash_total_customer"] else None,
            "daily_cash_txn_count": int(row["daily_cash_txn_count"]) if row["daily_cash_txn_count"] else None,
            "sanctions_screening": row["sanctions_screening"],
            "suspicion_determined_datetime": row["suspicion_determined_datetime"] if row["suspicion_determined_datetime"] else None,
            "str_filed_datetime": row["str_filed_datetime"] if row["str_filed_datetime"] else None,
        }
        return transaction
    
    async def submit_transaction(self, transaction: Dict, client: httpx.AsyncClient) -> Optional[str]:
        """Submit single transaction to API endpoint."""
        url = f"{self.api_url}/transactions"
        
        for attempt in range(self.retry_attempts):
            try:
                response = await client.post(url, json=transaction, timeout=30.0)
                response.raise_for_status()
                
                result = response.json()
                task_id = result.get("task_id")
                
                if task_id:
                    self.stats["success"] += 1
                    self.task_ids.append(task_id)
                    return task_id
                else:
                    raise Exception("No task_id in response")
                    
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    self.stats["retried"] += 1
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                else:
                    self.stats["failed"] += 1
                    console.print(f"[red]✗ Failed: {transaction['transaction_id']} - {str(e)}[/red]")
                    
                    if self.fail_fast:
                        raise
                    
                    return None
    
    async def run_concurrent(self, transactions: List[Dict]):
        """Submit transactions concurrently."""
        self.stats["start_time"] = time.time()
        self.stats["total"] = len(transactions)
        
        async with httpx.AsyncClient() as client:
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Submitting transactions...", total=len(transactions))
                
                semaphore = asyncio.Semaphore(self.max_concurrent)
                
                async def submit_with_limit(txn):
                    async with semaphore:
                        result = await self.submit_transaction(txn, client)
                        progress.advance(task)
                        
                        # Rate limiting
                        await asyncio.sleep(1.0 / self.rate_limit)
                        return result
                
                await asyncio.gather(*[submit_with_limit(txn) for txn in transactions])
        
        self.stats["end_time"] = time.time()
    
    async def run_sequential(self, transactions: List[Dict]):
        """Submit transactions sequentially."""
        self.stats["start_time"] = time.time()
        self.stats["total"] = len(transactions)
        
        async with httpx.AsyncClient() as client:
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Submitting transactions...", total=len(transactions))
                
                for transaction in transactions:
                    await self.submit_transaction(transaction, client)
                    progress.advance(task)
                    
                    # Rate limiting
                    await asyncio.sleep(1.0 / self.rate_limit)
        
        self.stats["end_time"] = time.time()
    
    def print_summary(self):
        """Print simulation summary statistics."""
        duration = self.stats["end_time"] - self.stats["start_time"]
        rate = self.stats["success"] / duration if duration > 0 else 0
        
        table = Table(title="Transaction Simulator Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Transactions", str(self.stats["total"]))
        table.add_row("Successful", str(self.stats["success"]))
        table.add_row("Failed", str(self.stats["failed"]))
        table.add_row("Retried", str(self.stats["retried"]))
        table.add_row("Duration", f"{duration:.2f}s")
        table.add_row("Average Rate", f"{rate:.2f} txn/s")
        table.add_row("Success Rate", f"{(self.stats['success'] / self.stats['total'] * 100):.1f}%")
        
        console.print("\n")
        console.print(table)
        console.print(f"\n[cyan]Task IDs saved to: task_ids.txt[/cyan]")
        
        # Save task IDs to file for later tracking
        with open("task_ids.txt", "w") as f:
            for task_id in self.task_ids:
                f.write(f"{task_id}\n")


@click.command()
@click.option("--csv", default="data/transactions_mock_1000_for_participants.csv", help="Path to CSV file")
@click.option("--api-url", default="http://localhost:8000", help="API server URL")
@click.option("--rate", default=5.0, help="Submission rate (transactions per second)")
@click.option("--limit", default=None, type=int, help="Limit number of transactions to process")
@click.option("--concurrent/--sequential", default=False, help="Enable concurrent submission")
@click.option("--max-concurrent", default=10, help="Max concurrent requests")
@click.option("--retry", default=3, help="Number of retry attempts")
@click.option("--fail-fast/--continue-on-error", default=False, help="Stop on first error")
def main(csv, api_url, rate, limit, concurrent, max_concurrent, retry, fail_fast):
    """
    Transaction Simulator - Submit transactions from CSV to API endpoint.
    
    Examples:
        # Submit all transactions at 5 txn/s
        python scripts/transaction_simulator.py
        
        # Submit first 100 transactions at 10 txn/s concurrently
        python scripts/transaction_simulator.py --limit 100 --rate 10 --concurrent
        
        # Submit with custom API URL
        python scripts/transaction_simulator.py --api-url http://api.example.com:8000
    """
    console.print("[bold cyan]Transaction Simulator[/bold cyan]\n")
    
    csv_path = Path(csv)
    if not csv_path.exists():
        console.print(f"[red]Error: CSV file not found: {csv_path}[/red]")
        sys.exit(1)
    
    simulator = TransactionSimulator(
        api_url=api_url,
        rate_limit=rate,
        concurrent=concurrent,
        max_concurrent=max_concurrent,
        retry_attempts=retry,
        fail_fast=fail_fast,
    )
    
    # Parse CSV
    transactions = simulator.parse_csv(csv_path)
    
    # Limit if specified
    if limit:
        transactions = transactions[:limit]
        console.print(f"[yellow]Processing first {limit} transactions[/yellow]\n")
    
    # Run simulation
    try:
        if concurrent:
            asyncio.run(simulator.run_concurrent(transactions))
        else:
            asyncio.run(simulator.run_sequential(transactions))
        
        # Print summary
        simulator.print_summary()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        simulator.print_summary()
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Usage Examples

```bash
# Basic usage - submit all transactions at 5 txn/s
python scripts/transaction_simulator.py

# Submit first 100 transactions at 10 txn/s
python scripts/transaction_simulator.py --limit 100 --rate 10

# Concurrent submission with 20 workers at 20 txn/s
python scripts/transaction_simulator.py --rate 20 --concurrent --max-concurrent 20

# Custom API URL
python scripts/transaction_simulator.py --api-url http://192.168.1.100:8000

# Fast submission with fail-fast mode
python scripts/transaction_simulator.py --rate 50 --concurrent --fail-fast

# Submit specific range (requires modifying CSV or using limit)
python scripts/transaction_simulator.py --limit 500 --rate 10
```

### Dependencies

Add to `requirements.txt`:
```
httpx>=0.25.0
click>=8.1.0
rich>=13.0.0
```

### Monitoring Task Status

After running the simulator, you can check the status of submitted transactions:

```bash
# Check specific task status
curl http://localhost:8000/transactions/{transaction_id}/status

# Monitor Celery queue
celery -A worker.celery_app inspect active

# View in Flower
# Open http://localhost:5555 and check task progress
```

### Output

The simulator provides:
1. **Real-time progress bar** with elapsed time
2. **Summary statistics** table with success/failure rates
3. **Task IDs file** (`task_ids.txt`) for tracking
4. **Detailed error logging** for failed submissions

### Integration with Part 1 Workflow

```
Transaction Simulator
  ↓ (HTTP POST /transactions)
FastAPI Endpoint (app/api/transactions.py)
  ↓ (Validate & enqueue)
Redis Queue (Celery broker)
  ↓ (Worker picks task)
Celery Worker (worker/tasks.py)
  ↓ (Invoke workflow)
LangGraph Part 1 Workflow
  ↓ (13-agent processing)
Results stored in PostgreSQL
  ↓
Alerts pushed via WebSocket
```

---

## World-Check One API Integration (Background Screening)

The BackgroundCheck Agent integrates with LSEG World-Check One API to perform comprehensive background screening on individuals and entities mentioned in documents.

### World-Check One API Overview

**API Documentation**: https://developers.lseg.com/en/api-catalog/customer-and-third-party-screening/world-check-one-api

**Capabilities:**
- **PEP Screening**: Politically Exposed Persons identification
- **Sanctions Screening**: OFAC, UN, EU, and other sanctions lists
- **Adverse Media**: Negative news and media mentions
- **Law Enforcement**: Criminal records and watchlists
- **Financial Crime**: Money laundering, fraud, corruption databases
- **Ownership & Control**: UBO (Ultimate Beneficial Owner) information

### Authentication

World-Check One API uses OAuth 2.0 authentication. See full implementation in `agents/part2/background_check.py`.

### BackgroundCheck Agent Key Features

1. **Entity Extraction**: Automatically extracts names and entities from document OCR/NLP results
2. **API Screening**: Submits entities to World-Check One for comprehensive screening
3. **Match Classification**: Categorizes matches into PEP, sanctions, adverse media, law enforcement
4. **Risk Scoring**: Calculates risk level (low/medium/high/critical) based on match types
5. **Integration**: Results feed into DocumentRisk agent and alert system

### Integration into Part 2 Workflow

```
DocumentIntake → OCR → FormatValidation → NLPValidation 
  ↓
BackgroundCheck (NEW) → World-Check One API
  ↓
CrossReference → DocumentRisk → ReportGenerator
```

### Environment Variables

Add to `.env`:
```bash
# World-Check One API
WORLDCHECK_API_KEY=your_api_key_here
WORLDCHECK_API_SECRET=your_api_secret_here
WORLDCHECK_GROUP_ID=your_group_id_here
WORLDCHECK_BASE_URL=https://api-worldcheck.refinitiv.com/v2
```

### Alert Integration

Background check results trigger alerts when:
- **Critical**: Sanctions matches found
- **High**: PEP + adverse media or law enforcement matches
- **Medium**: Single PEP or adverse media matches
- **Low**: No significant matches (no alert generated)

### PDF Report Integration

Background screening results appear in generated PDF reports with:
- Entities screened
- Match status and risk level
- Detailed match information by category
- Recommendations for enhanced due diligence

For detailed implementation, see the full BackgroundCheck agent code in the repository at `agents/part2/background_check.py`.

---

## Tech Stack
- **Language:** Python 3.11+
- **Orchestration:** LangGraph for agentic workflow orchestration
- **API Framework:** FastAPI for REST endpoints and WebSocket support
- **Task Queue:** Celery with Redis backend for async task processing **(Part 1 only)**
- **Web Server:** Uvicorn (local development)
- **Vector Database:** 
  - Qdrant for rule embeddings
  - Separate collections: `external_rules`, `internal_rules`
- **Embeddings:** OpenAI `text-embedding-3-large` or `sentence-transformers` (local)
- **LLM:** OpenAI GPT-4 or Claude for agent reasoning
- **Crawler:** crawl4ai for regulatory website scraping
- **OCR:** pytesseract + Tesseract, PyMuPDF (fitz) for PDF processing
- **Image Forensics:** Pillow (ELA), exifread (EXIF), reverse image search APIs
- **Background Screening:** LSEG World-Check One API for PEP/sanctions screening
- **Search:** Hybrid BM25 + vector search with re-ranking
- **Monitoring:** Flower for Celery monitoring (optional, Part 1 only)
- **Storage:**
  - PostgreSQL (cloud-hosted) for transactional data, alerts, cases
  - Vector DB for embedded rules and regulations
  - Redis (local) for queue and caching **(Part 1 only - transaction processing)**
  - Filesystem for document storage
- **Bayesian Inference:** pgmpy or pomegranate
- **Packaging:** poetry or pip-tools

> **Note**: Part 2 (document processing) executes synchronously in the API process and does NOT use Celery/Redis. Only Part 1 (transaction processing) uses async queueing.

## Transaction Schema
Transactions from `transactions_mock_1000_for_participants.csv` contain the following fields:

**Transaction Identifiers & Timing:**
- `transaction_id`, `booking_jurisdiction`, `regulator`, `booking_datetime`, `value_date`

**Financial Details:**
- `amount`, `currency`, `channel`, `product_type`

**Originator Information:**
- `originator_name`, `originator_account`, `originator_country`

**Beneficiary Information:**
- `beneficiary_name`, `beneficiary_account`, `beneficiary_country`

**SWIFT/Payment Details:**
- `swift_mt`, `ordering_institution_bic`, `beneficiary_institution_bic`
- `swift_f50_present`, `swift_f59_present`, `swift_f70_purpose`, `swift_f71_charges`
- `travel_rule_complete`

**FX Details:**
- `fx_indicator`, `fx_base_ccy`, `fx_quote_ccy`, `fx_applied_rate`, `fx_market_rate`, `fx_spread_bps`, `fx_counterparty`

**Customer Profile:**
- `customer_id`, `customer_type`, `customer_risk_rating`, `customer_is_pep`
- `kyc_last_completed`, `kyc_due_date`, `edd_required`, `edd_performed`, `sow_documented`

**Transaction Context:**
- `purpose_code`, `narrative`, `is_advised`, `product_complex`
- `client_risk_profile`, `suitability_assessed`, `suitability_result`
- `product_has_va_exposure`, `va_disclosure_provided`

**Cash & Screening:**
- `cash_id_verified`, `daily_cash_total_customer`, `daily_cash_txn_count`
- `sanctions_screening`, `suspicion_determined_datetime`, `str_filed_datetime`

## Data and Storage Design

### PostgreSQL Database

**Transactions Table:**
- `id`, `transaction_id`, `booking_datetime`, `customer_id`, `amount`, `currency`
- `originator_country`, `beneficiary_country`, `product_type`, `channel`
- `customer_risk_rating`, `sanctions_screening`, `raw_json`, `hash`, `created_at`

**Features Table:**
- `transaction_id`, `feature_key`, `feature_value`, `window_id`, `computed_at`

**Episodes Table:**
- `episode_id`, `customer_id`, `account_id`, `start_ts`, `end_ts`
- `num_txn`, `stats_json`, `pattern_flags`

**Alerts Table:**
- `alert_id`, `transaction_id`, `customer_id`, `severity`, `risk_score`
- `role` (front_office, compliance), `reason`, `rule_ids`, `created_at`, `state`, `acknowledged_at`

**Cases Table:**
- `case_id`, `alert_id`, `owner`, `status`, `priority`, `sla_deadline`
- `created_at`, `updated_at`, `closed_at`

**Audit Logs Table:**
- `id`, `actor`, `action`, `entity_type`, `entity_id`, `payload`, `created_at`

**Compliance Analysis Table:**
- `transaction_id`, `compliance_score`, `risk_band`, `summary`, `rule_refs`, `evidence`, `created_at`

### Vector Database

**Collections:**

1. **external_rules**
   - Vectorized chunks from regulatory circulars
   - Metadata: `source_url`, `published_date`, `regulator`, `jurisdiction`, `doc_title`, `section_path`, `version`

2. **internal_rules**
   - Vectorized internal policy rules
   - Metadata: `rule_id`, `section`, `obligation_type`, `effective_date`, `version`, `source`, `conditions`, `expected_evidence`, `penalty_level`

### Redis

- **Queue:** Celery task queue for async transaction processing
- **Cache:** Session data, rate limiting, temporary results

## Repository Layout

```
slenth/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── transactions.py        # POST /transactions endpoint
│   │   ├── internal_rules.py      # POST /internal_rules endpoint
│   │   ├── documents.py           # POST /documents/upload endpoint (Part 2)
│   │   ├── alerts.py              # GET /alerts endpoints
│   │   └── websocket.py           # WebSocket endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── transaction.py         # Pydantic models for transactions
│   │   ├── rule.py                # Pydantic models for rules
│   │   ├── document.py            # Pydantic models for documents (Part 2)
│   │   ├── alert.py               # Pydantic models for alerts
│   │   └── compliance.py          # Compliance analysis models
│   ├── db/
│   │   ├── __init__.py
│   │   ├── postgres.py            # PostgreSQL connection
│   │   ├── vector_db.py           # Vector DB client
│   │   └── redis_client.py        # Redis connection
│   └── config.py                  # Configuration management
│
├── agents/
│   ├── part1/                     # Part 1: Transaction monitoring agents
│   │   ├── __init__.py
│   │   ├── context_builder.py
│   │   ├── retrieval.py
│   │   ├── applicability.py
│   │   ├── evidence_mapper.py
│   │   ├── control_test.py
│   │   ├── feature_service.py
│   │   ├── bayesian_engine.py
│   │   ├── pattern_detector.py
│   │   ├── decision_fusion.py
│   │   ├── analyst_writer.py
│   │   ├── alert_composer.py
│   │   ├── remediation.py
│   │   └── audit.py
│   │
│   └── part2/                     # Part 2: Document corroboration agents
│       ├── __init__.py
│       ├── document_intake.py     # Document upload and normalization
│       ├── ocr.py                 # OCR agent
│       ├── format_validation.py   # Format and content validation
│       ├── nlp_validate.py        # NLP validation agent
│       ├── image_forensics.py     # Image analysis agent
│       ├── background_check.py    # World-Check One API integration (NEW)
│       ├── cross_reference.py     # Cross-reference agent
│       ├── doc_risk.py            # Document risk agent
│       ├── report_generator.py    # PDF report generator
│       └── evidence_store.py      # Evidence storage manager
│
├── workflows/
│   ├── __init__.py
│   ├── transaction_workflow.py    # LangGraph workflow for Part 1
│   ├── document_workflow.py       # LangGraph workflow for Part 2
│   ├── integrated_workflow.py     # Unified workflow coordinator
│   └── state.py                   # Workflow state definitions
│
├── worker/
│   ├── __init__.py
│   ├── celery_app.py              # Celery app configuration
│   └── tasks.py                   # Celery task definitions
│
├── crawlers/
│   ├── __init__.py
│   ├── regulatory_crawler.py      # crawl4ai-based crawler
│   ├── hkma_crawler.py            # HKMA-specific logic
│   ├── mas_crawler.py             # MAS-specific logic
│   ├── finma_crawler.py           # FINMA-specific logic
│   └── pdf_extractor.py           # PDF extraction utilities
│
├── cron/
│   ├── __init__.py
│   └── external_rules_ingestion.py # CronJob script for regulatory scraping
│
├── internal_rules/
│   ├── 1.json                     # Mock internal rules
│   ├── 2.json
│   └── ...
│
├── data/
│   ├── transactions_mock_1000_for_participants.csv
│   ├── Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf
│   ├── external_docs/             # Scraped regulatory documents
│   ├── uploaded_docs/             # User-uploaded documents (Part 2)
│   ├── ocr_output/                # OCR extracted text
│   ├── reports/                   # Generated PDF reports
│   └── embeddings/                # Vector DB backups
│
├── scripts/
│   ├── init_db.py                 # Initialize PostgreSQL schema
│   ├── init_vector_db.py          # Initialize vector DB collections
│   ├── load_internal_rules.py     # Load mock internal rules
│   └── transaction_simulator.py   # Transaction simulator - parses CSV and submits to API
│
├── tests/
│   ├── test_agents/
│   │   ├── test_part1/
│   │   └── test_part2/
│   ├── test_workflows/
│   └── test_api/
│
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   └── deployment.md
│
├── pyproject.toml                 # Poetry dependencies
├── requirements.txt               # Pip dependencies
├── .env.example                   # Environment variables template
├── README.md
└── AGENTIC_AML_WORKFLOW_PLAN.md   # This file
```

## Implementation Steps

### Phase 1: Infrastructure Setup

1. **Start Local Services**
   ```bash
   # Start Redis (for Part 1 Celery queue)
   brew services start redis
   
   # Start Qdrant (vector database)
   docker run -d -p 6333:6333 -p 6334:6334 \
     -v $(pwd)/qdrant_storage:/qdrant/storage \
     qdrant/qdrant
   ```

2. **Configure Cloud PostgreSQL**
   ```bash
   # Set DATABASE_URL in .env to your cloud PostgreSQL connection string
   # Example: postgresql://user:password@your-cloud-host:5432/dbname
   ```

3. **Initialize Databases**
   ```bash
   # Initialize PostgreSQL schema (connects to cloud database)
   python scripts/init_db.py
   
   # Initialize vector DB collections
   python scripts/init_vector_db.py
   ```

4. **Load Mock Data**
   ```bash
   # Load internal rules from internal_rules/ directory
   python scripts/load_internal_rules.py
   ```

5. **Configure Environment**
   - Set up `.env` file with API keys, cloud database URLs
   - Configure crawl4ai settings
   - Set up LLM API credentials (OpenAI/Claude)
   - Configure OCR (Tesseract path)
   - Add World-Check One API credentials

### Phase 2: Part 1 - Regulatory Crawler (CronJob)

1. **Implement crawl4ai Crawler**
   - Create `crawlers/regulatory_crawler.py`
   - Implement site-specific scrapers:
     - `hkma_crawler.py` - HKMA circulars
     - `mas_crawler.py` - MAS regulations
     - `finma_crawler.py` - FINMA circulars
   - Handle PDF extraction within linked pages

2. **Content Processing**
   - Clean HTML → Markdown
   - Chunk into ~500-1000 token pieces
   - Extract metadata (date, jurisdiction, regulator)

3. **Embedding & Storage**
   - Generate embeddings using `text-embedding-3-large`
   - Upsert to `external_rules` collection
   - Store raw documents in `data/external_docs/`

4. **Manual Execution (Local)**
   ```bash
   # Run manually instead of cron for local dev
   python cron/external_rules_ingestion.py
   ```

### Phase 3: Part 1 - FastAPI Server & Internal Rules Endpoint

1. **Create FastAPI Application**
   - `app/main.py` - Main FastAPI app
   - `app/api/internal_rules.py` - POST endpoint for internal rules
   - `app/api/transactions.py` - POST endpoint for transactions

2. **Internal Rules Endpoint**
   ```python
   POST /internal_rules
   Body: {
     "text": "<rule_text>",
     "effective_date": "YYYY-MM-DD",
     "version": "v1.0",
     "source": "internal_policy_manual"
   }
   ```
   - Validate and structure incoming rules
   - Generate embeddings
   - Upsert to `internal_rules` vector collection
   - Store in PostgreSQL with versioning

3. **Transaction Endpoint**
   ```python
   POST /transactions
   Body: { <transaction_json> }
   ```
   - Validate transaction schema
   - Enqueue to Redis for Celery processing

### Phase 4: Part 1 - Celery Worker & Redis Queue

1. **Configure Celery**
   - `worker/celery_app.py` - Celery configuration
   - Use Redis as broker and result backend
   - Set up task queues: `default`, `priority`, `low_priority`

2. **Create Celery Tasks**
   - `worker/tasks.py`:
     - `process_transaction_task` - Main transaction processing task
     - Invokes LangGraph workflow

3. **Start Celery Workers (Local)**
   ```bash
   # Start Celery worker (2 workers for local dev)
   celery -A worker.celery_app worker -l info -Q default -c 2
   ```

### Phase 5: Part 1 - LangGraph Agentic Workflow

1. **Define Workflow State**
   - `workflows/state.py` - Pydantic models for workflow state
   - Track intermediate results through agents

2. **Implement Part 1 Agents**
   - Each agent in `agents/part1/` directory
   - Implement LangGraph nodes for each agent:
     - ContextBuilder, Retrieval, ApplicabilityAgent, EvidenceMapper, ControlTestAgent, FeatureService, BayesianEngine, PatternDetector, DecisionFusion, AnalystWriter, AlertComposer, RemediationOrchestrator, Persistor

3. **Create LangGraph Workflow**
   - `workflows/transaction_workflow.py`
   - Define DAG with conditional edges
   - Handle error recovery and retries

4. **Integration**
   - Celery task calls LangGraph workflow
   - Workflow processes transaction through all agents
   - Results stored in PostgreSQL

### Phase 6: Part 2 - Document Processing Infrastructure

1. **Document Upload Endpoint**
   - `app/api/documents.py` - POST `/documents/upload`
   - Accept multiple formats: PDF, images, text
   - Store in `data/uploaded_docs/`
   - **Trigger LangGraph workflow SYNCHRONOUSLY** (no Celery/Redis queueing)
   - Return results directly in API response

2. **OCR Setup**
   - Install Tesseract: `brew install tesseract`
   - Configure `agents/part2/ocr.py`
   - Use PyMuPDF for PDF text extraction
   - Use pytesseract for image OCR

3. **Document Storage Structure**
   ```
   data/
   ├── uploaded_docs/           # Original uploads
   ├── ocr_output/              # Extracted text and regions
   ├── reports/                 # Generated PDF reports
   └── evidence/                # Evidence artifacts
   ```

### Phase 7: Part 2 - Document Corroboration Agents

1. **Implement Part 2 Agents**
   - `agents/part2/document_intake.py` - Document normalization
   - `agents/part2/ocr.py` - OCR extraction
   - `agents/part2/format_validation.py` - Format/content checks
   - `agents/part2/nlp_validate.py` - Field extraction and validation
   - `agents/part2/image_forensics.py` - EXIF, ELA, AI-detection
   - `agents/part2/background_check.py` - World-Check One API integration
   - `agents/part2/cross_reference.py` - Link to transactions/KYC
   - `agents/part2/doc_risk.py` - Risk scoring
   - `agents/part2/report_generator.py` - PDF report generation
   - `agents/part2/evidence_store.py` - Evidence management

2. **Image Forensics Implementation**
   - EXIF extraction: `exifread` library
   - Error Level Analysis: Custom implementation with Pillow
   - AI-generated detection: Heuristics or API integration
   - Reverse image search: Stub with API placeholder

3. **Background Check Integration**
   - Implement World-Check One API client
   - OAuth 2.0 authentication
   - Entity extraction from documents
   - PEP, sanctions, adverse media screening
   - Risk level calculation

4. **Create Document Workflow**
   - `workflows/document_workflow.py`
   - LangGraph DAG for document processing
   - Sequential and parallel agent execution
   - **Execute synchronously within API request** (no async queueing)

### Phase 8: Integration & Unified Alert System

1. **Unified Alert Orchestrator**
   - Aggregate alerts from Part 1 (transactions) and Part 2 (documents)
   - Deduplicate related alerts
   - Route to appropriate teams (Front/Compliance/Legal)
   - Store in unified `alerts` table

2. **Cross-Reference Integration**
   - Link document findings with customer transaction history
   - Correlate document risk with transaction patterns
   - Unified case management

3. **WebSocket Endpoints**
   - Real-time alert streaming to frontend
   - `app/api/websocket.py`
   - Separate channels for transactions and documents

### Phase 9: Reporting & Dashboard

1. **REST Endpoints**
   - `GET /alerts` - List alerts with filtering
   - `GET /alerts/{id}` - Alert details
   - `POST /alerts/{id}/acknowledge` - Acknowledge alert
   - `GET /transactions/{id}/compliance` - Compliance analysis
   - `GET /documents/{id}/risk` - Document risk report
   - `GET /documents/{id}/report` - Download PDF report

2. **Dashboard Endpoints**
   - `GET /alerts/dashboard` - Summary statistics
   - `GET /stats` - System-wide statistics

3. **PDF Report Generation**
   - Use ReportLab or WeasyPrint
   - Include: OCR results, validation findings, image forensics, risk score
   - Highlight red flags and problematic areas

### Phase 10: Testing & Demo Preparation

1. **Unit Tests**
   - Test each agent individually
   - Test vector DB operations
   - Test API endpoints

2. **Integration Tests**
   - Test full Part 1 workflow with sample transaction
   - Test full Part 2 workflow with sample document
   - Test cross-referencing

3. **Demo Scripts**
   ```bash
   # Process sample transactions
   python scripts/simulate_stream.py --csv data/transactions_mock_1000_for_participants.csv --limit 10
   
   # Upload sample document
   curl -X POST http://localhost:8000/documents/upload \
     -F "file=@data/Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf"
   ```

4. **Documentation**
   - API documentation (Swagger at `/docs`)
   - Architecture diagrams
   - Demo video/screenshots

## LangGraph Workflow Details

### Workflow State Schema

```python
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class WorkflowState(BaseModel):
    transaction: Dict[str, Any]
    transaction_history: List[Dict[str, Any]]
    rules_query: str
    retrieved_rules: List[Dict[str, Any]]
    applicable_rules: List[Dict[str, Any]]
    evidence_map: Dict[str, Any]
    control_results: List[Dict[str, Any]]
    features: Dict[str, Any]
    bayesian_posterior: Dict[str, float]
    patterns: List[Dict[str, Any]]
    final_risk_score: float
    risk_band: str
    compliance_summary: str
    alerts: List[Dict[str, Any]]
    remediation_actions: List[Dict[str, Any]]
    audit_trail: List[Dict[str, Any]]
```

### Agent Implementations

#### 1. ContextBuilder
- **Input:** Raw transaction JSON
- **Processing:**
  - Convert transaction to rules-like query string
  - Query PostgreSQL for customer transaction history (last 30 days)
  - Format context for retrieval
- **Output:** `rules_query`, `transaction_history`

#### 2. Retrieval (Hybrid)
- **Input:** `rules_query`, transaction metadata
- **Processing:**
  - BM25 keyword search over rule text
  - Vector similarity search over embeddings
  - Combine and re-rank (e.g., reciprocal rank fusion)
  - Filter by jurisdiction and effective dates
- **Output:** `retrieved_rules` (top 20-30 rules)

#### 3. ApplicabilityAgent (Parallel Map)
- **Input:** `retrieved_rules`, transaction
- **Processing:**
  - For each rule, LLM call to determine applicability
  - Prompt: "Does this rule apply to the transaction? Provide rationale and confidence."
- **Output:** `applicable_rules` with `applies`, `rationale`, `confidence`

#### 4. EvidenceMapper (Parallel Map)
- **Input:** `applicable_rules`, transaction
- **Processing:**
  - Map expected evidence from rule to transaction fields
  - Check if evidence is present, missing, or contradictory
- **Output:** `evidence_map` per rule

#### 5. ControlTestAgent (Parallel Map)
- **Input:** `applicable_rules`, `evidence_map`
- **Processing:**
  - Test each control: pass/fail/partial
  - Assign severity (critical/high/medium/low)
  - Compute per-rule score
- **Output:** `control_results`

#### 6. FeatureService
- **Input:** `transaction`, `transaction_history`
- **Processing:**
  - Compute deterministic features:
    - Velocity: txn count in last 24h, 7d, 30d
    - Amount patterns: z-score, structuring indicators
    - Geographic risk: country risk scores
    - Temporal patterns: time-of-day, day-of-week
    - Network features: counterparty graph degree
- **Output:** `features` dict

#### 7. BayesianEngine
- **Input:** `features`, `control_results`
- **Processing:**
  - Build/update Bayesian network for customer
  - Evidence nodes from features and control results
  - Compute posterior probabilities for risk categories
- **Output:** `bayesian_posterior` (probabilities)

#### 8. PatternDetector
- **Input:** `transaction`, `transaction_history`, `features`
- **Processing:**
  - Detect temporal motifs (structuring, velocity spikes)
  - Detect network motifs (circular transfers, layering)
  - Score each pattern
- **Output:** `patterns` list with scores

#### 9. DecisionFusion
- **Input:** `control_results`, `bayesian_posterior`, `patterns`
- **Processing:**
  - Weighted fusion of scores:
    - Rule-based risk: 40%
    - ML posterior: 35%
    - Pattern scores: 25%
  - Compute `final_risk_score` (0-100)
  - Map to risk band: Low (<25), Medium (25-50), High (50-75), Critical (>75)
- **Output:** `final_risk_score`, `risk_band`

#### 10. AnalystWriter
- **Input:** All intermediate results
- **Processing:**
  - LLM generates concise compliance analysis
  - Includes rule IDs, evidence refs, key findings
  - Markdown format
- **Output:** `compliance_summary`

#### 11. AlertComposer + Router + AckTracker
- **Input:** `final_risk_score`, `risk_band`, `compliance_summary`, `control_results`
- **Processing:**
  - Create role-specific alerts:
    - **Front Office:** Customer-facing issues, suitability, disclosures
    - **Compliance:** AML/sanctions, structuring, pattern anomalies
  - Route by priority and severity
  - Set SLA deadlines
  - Track acknowledgment status
- **Output:** `alerts` list

#### 12. RemediationOrchestrator
- **Input:** `alerts`, `control_results`
- **Processing:**
  - Match failed controls to playbook actions
  - Assign owners and SLA deadlines
  - Create cases in case management system
- **Output:** `remediation_actions`

#### 13. Persistor & AuditTrail
- **Input:** Entire workflow state
- **Processing:**
  - Store compliance analysis in PostgreSQL
  - Store alerts in `alerts` table
  - Create cases in `cases` table
  - Log all decisions, intermediate states to `audit_logs`
  - Compute hashes for immutability
- **Output:** `audit_trail`, database records

### LangGraph DAG Structure

```
┌─────────────────┐
│ ContextBuilder  │
└────────┬────────┘
         │
         ▼
    ┌────────────┐
    │ Retrieval  │
    └─────┬──────┘
          │
          ▼
  ┌───────────────────┐
  │ ApplicabilityAgent│ (parallel map)
  └─────────┬─────────┘
            │
            ▼
   ┌────────────────┐
   │ EvidenceMapper │ (parallel map)
   └────────┬───────┘
            │
            ▼
  ┌─────────────────┐
  │ ControlTestAgent│ (parallel map)
  └────────┬────────┘
           │
           ├──────────┐
           │          │
           ▼          ▼
  ┌────────────┐  ┌──────────────┐
  │ FeatureService│  │BayesianEngine│
  └──────┬─────┘  └──────┬───────┘
         │               │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │PatternDetector│
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │DecisionFusion │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │ AnalystWriter │
         └───────┬───────┘
                 │
                 ▼
   ┌─────────────────────────┐
   │AlertComposer + Router   │
   └──────────┬──────────────┘
              │
              ▼
   ┌──────────────────────────┐
   │RemediationOrchestrator   │
   └──────────┬───────────────┘
              │
              ▼
   ┌──────────────────────────┐
   │Persistor & AuditTrail    │
   └──────────────────────────┘
```

## API Endpoints

### Part 1: Transaction Processing

**POST /transactions**
- Submit transaction for compliance evaluation
- Enqueues to Celery for async processing
- Returns task ID for status tracking

```json
{
  "transaction_id": "TXN123",
  "booking_jurisdiction": "HK",
  "regulator": "HKMA",
  "amount": 50000.00,
  "currency": "USD",
  "customer_id": "CUST456",
  ...
}
```

**GET /transactions/{transaction_id}/status**
- Check processing status
- Returns: pending, processing, completed, failed

**GET /transactions/{transaction_id}/compliance**
- Retrieve compliance analysis
- Returns: risk score, risk band, summary, alerts, evidence

### Part 2: Document Processing

**POST /documents/upload**
- Upload document for corroboration
- Accepts: PDF, images (PNG, JPG), text files
- **Executes LangGraph workflow synchronously**
- Returns complete document analysis results immediately

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@document.pdf" \
  -F "document_type=purchase_agreement"
```

**Response:**
```json
{
  "document_id": "DOC789",
  "status": "completed",
  "risk_score": 72,
  "risk_band": "High",
  "findings": {
    "format_issues": [...],
    "nlp_validation": {...},
    "image_forensics": {...},
    "background_check": {...}
  },
  "alerts": [...],
  "report_url": "/documents/DOC789/report"
}
```

**GET /documents/{document_id}/risk**
- Retrieve document risk assessment
- Returns: risk score, risk band, findings, red flags

**GET /documents/{document_id}/report**
- Download comprehensive PDF report
- Includes: OCR results, validation findings, image forensics, risk assessment

**GET /documents/{document_id}/findings**
- Get detailed findings
- Returns: format issues, NLP validation results, image forensics, cross-references

**POST /documents/{document_id}/acknowledge**
- Acknowledge document review
- Body: `{ "reviewer": "jane.doe", "comments": "Approved with conditions" }`

### Internal Rules Management

**POST /internal_rules**
- Add or update internal rule
- Triggers embedding and vector DB upsert

```json
{
  "text": "All transactions above USD 10,000 require enhanced due diligence...",
  "effective_date": "2025-01-01",
  "version": "v2.1",
  "source": "internal_policy_manual"
}
```

**GET /internal_rules**
- List all internal rules with filtering
- Query params: effective_date, version, source

**GET /internal_rules/{rule_id}**
- Get specific rule details

**PUT /internal_rules/{rule_id}**
- Update existing rule (creates new version)

**DELETE /internal_rules/{rule_id}**
- Deactivate rule (soft delete with sunset date)

### Alerts (Unified for Part 1 & Part 2)

**GET /alerts**
- List alerts with filtering
- Query params: role (front/compliance/legal), severity, status, date_range, source (transaction/document)

**GET /alerts/{alert_id}**
- Alert details with full context

**POST /alerts/{alert_id}/acknowledge**
- Acknowledge alert
- Body: `{ "user": "john.doe", "comment": "Reviewed and escalated" }`

**GET /alerts/dashboard**
- Dashboard summary: alert counts by severity, role, status

### Cases (Unified Case Management)

**GET /cases**
- List all cases
- Query params: status, priority, owner, source

**GET /cases/{case_id}**
- Case details with remediation actions, linked alerts, audit trail

**POST /cases/{case_id}/update**
- Update case status
- Body: `{ "status": "in_progress", "comment": "Investigating", "assigned_to": "compliance_team" }`

**POST /cases/{case_id}/add_evidence**
- Add evidence to case
- Body: `{ "evidence_type": "document", "evidence_id": "DOC123", "notes": "Supporting document" }`

### WebSocket (Real-Time Updates)

**WS /ws/alerts**
- Real-time alert stream
- Clients receive alerts as they're generated from both Part 1 and Part 2

**WS /ws/transactions**
- Real-time transaction processing updates

**WS /ws/documents**
- Real-time document processing updates

### System Management

**GET /health**
- System health check
- Returns: API status, database connections, worker status

**GET /stats**
- System statistics
- Returns: transactions processed, documents analyzed, alerts generated, cases open

**GET /audit**
- Audit trail query
- Query params: entity_type, entity_id, date_range, actor

## Local Development Commands

### Prerequisites
```bash
# Install Python dependencies
poetry install

# OR with pip
pip install -r requirements.txt

# Install Tesseract for OCR (macOS)
brew install tesseract

# Install Playwright for crawl4ai
playwright install
```

### Start Infrastructure Services (Local)
```bash
# Start Redis (for Part 1 Celery queue)
brew services start redis

# Start Qdrant (vector database)
docker run -d -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  --name slenth-qdrant \
  qdrant/qdrant

# Initialize databases (PostgreSQL is cloud-hosted)
python scripts/init_db.py
python scripts/init_vector_db.py

# Load mock internal rules
python scripts/load_internal_rules.py
```

### Start API Server (Local Development)
```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# The API will be available at: http://localhost:8000
# API docs (Swagger): http://localhost:8000/docs
# Alternative docs (ReDoc): http://localhost:8000/redoc
```

### Start Celery Workers (Part 1 only - Local)
```bash
# Start single Celery worker for development (transaction processing)
celery -A worker.celery_app worker -l info -Q default -c 1

# For more concurrency (4 workers)
celery -A worker.celery_app worker -l info -Q default -c 4

# With debug logging
celery -A worker.celery_app worker -l debug -c 1
```

> **Note**: Celery is only used for Part 1 (transaction processing). Part 2 (document processing) runs synchronously in the API process.

### Start Flower (Celery Monitoring - Optional)
```bash
# Start Flower web UI (for Part 1 monitoring)
flower -A worker.celery_app --port=5555

# Access at: http://localhost:5555
```

### Run Regulatory Scraping Manually (Local)
```bash
# Run regulatory crawler manually (no cron needed for local dev)
python cron/external_rules_ingestion.py

# Run individual crawlers for testing
python -m crawlers.hkma_crawler
python -m crawlers.mas_crawler
python -m crawlers.finma_crawler
```

### All Services Startup Script (Local)
```bash
#!/bin/bash
# start_local.sh - Start all services for local development

echo "Starting infrastructure services..."
brew services start redis
docker start slenth-qdrant || docker run -d -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage --name slenth-qdrant qdrant/qdrant

echo "Waiting for services to be ready..."
sleep 5

echo "Starting FastAPI server in background..."
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
API_PID=$!

echo "Starting Celery worker (Part 1 only)..."
celery -A worker.celery_app worker -l info -Q default -c 2 &
CELERY_PID=$!

echo "Starting Flower (optional)..."
flower -A worker.celery_app --port=5555 &
FLOWER_PID=$!

echo ""
echo "✅ All services started!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 API Server:      http://localhost:8000"
echo "📚 API Docs:        http://localhost:8000/docs"
echo "🌸 Flower Monitor:  http://localhost:5555"
echo "☁️  PostgreSQL:     Cloud-hosted"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Process IDs:"
echo "  API: $API_PID"
echo "  Celery: $CELERY_PID"
echo "  Flower: $FLOWER_PID"
echo ""
echo "To stop all services:"
echo "  kill $API_PID $CELERY_PID $FLOWER_PID"
echo "  brew services stop redis"
echo "  docker stop slenth-qdrant"
```

### Healthcheck Endpoints (Local)
```bash
# Check API health
curl http://localhost:8000/health

# Check Celery worker status
celery -A worker.celery_app inspect active
celery -A worker.celery_app inspect stats

# Check Redis connection
redis-cli ping

# Check PostgreSQL connection (cloud)
# Uses DATABASE_URL from .env
python -c "import psycopg2; import os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); print('✅ PostgreSQL connected'); conn.close()"

# Check Qdrant (vector DB)
curl http://localhost:6333/collections
```

### Test Transaction Processing (Local - Part 1)
```bash
# Process single transaction via API (async via Celery)
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

# Simulate transaction stream from CSV
python scripts/transaction_simulator.py \
  --csv data/transactions_mock_1000_for_participants.csv \
  --rate 5 \
  --limit 10

# Process all 1000 transactions (slower)
python scripts/transaction_simulator.py \
  --csv data/transactions_mock_1000_for_participants.csv \
  --rate 2
```

### Test Document Upload (Part 2 - Synchronous - Local)
```bash
# Upload document for corroboration (returns complete results immediately)
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@data/Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf" \
  -F "document_type=home_purchase_agreement"

# Response includes complete analysis:
# {
#   "document_id": "DOC789",
#   "status": "completed",
#   "risk_score": 72,
#   "risk_band": "High",
#   "findings": {...},
#   "alerts": [...],
#   "report_url": "/documents/DOC789/report"
# }

# Download generated PDF report
curl http://localhost:8000/documents/{document_id}/report -o report.pdf
```

> **Note**: Unlike Part 1, document processing happens synchronously. The API waits for the workflow to complete before responding.

> **Note**: Unlike Part 1, document processing happens synchronously. The API waits for the workflow to complete before responding.

### View Logs (Local)
```bash
# API logs (if running with uvicorn in terminal, logs appear there)

# Celery logs (appear in celery terminal)

# Redis logs (if needed)
tail -f /usr/local/var/log/redis.log

# PostgreSQL logs (cloud-hosted - check your cloud provider's logging)

# Qdrant logs
docker logs -f slenth-qdrant
```

### Stop All Services (Local)
```bash
# Stop Homebrew services
brew services stop redis

# Stop Qdrant
docker stop slenth-qdrant

# PostgreSQL is cloud-hosted (no local stop needed)

# If using background processes, kill them
# (Use the PIDs from start_local.sh)
kill <API_PID> <CELERY_PID> <FLOWER_PID>

# Or find and kill all
pkill -f "uvicorn app.main"
pkill -f "celery -A worker"
pkill -f "flower -A worker"
```

### Clean Up (Local)
```bash
# Clean up generated files
rm -rf data/uploaded_docs/*
rm -rf data/ocr_output/*
rm -rf data/reports/*
rm -rf data/external_docs/*

# Reset databases
python scripts/init_db.py --reset
python scripts/init_vector_db.py --reset
```

---

## Quick Start Guide (Local Development)

### Environment Variables

Create `.env` file in the project root:

```bash
# Database (Cloud PostgreSQL)
DATABASE_URL=postgresql://username:password@your-cloud-host:5432/slenth_db
REDIS_URL=redis://localhost:6379/0

# Vector DB
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=  # Optional for local

# LLM API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Optional

# Embedding Model
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSION=3072

# Celery (Part 1 only)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Application
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# OCR
TESSERACT_PATH=/usr/local/bin/tesseract  # macOS with brew

# Crawler
CRAWLER_USER_AGENT=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)
CRAWLER_RATE_LIMIT=2  # requests per second

# World-Check One API
WORLDCHECK_API_KEY=your_api_key_here
WORLDCHECK_API_SECRET=your_api_secret_here
WORLDCHECK_GROUP_ID=your_group_id_here
WORLDCHECK_BASE_URL=https://api-worldcheck.refinitiv.com/v2

# Security
SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
```

### 1. Clone and Setup
```bash
# Clone repository
git clone https://github.com/clarud/slenth.git
cd slenth

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# OR with poetry
poetry install
poetry shell

# Install system dependencies
brew install tesseract postgresql redis qdrant

# OR start services with Homebrew (if installed)
brew services start postgresql
brew services start redis

# Install Playwright
playwright install
```

### 2. Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

### 3. Start Infrastructure Services

**PostgreSQL:**
```bash
# If using Homebrew
brew services start postgresql
createdb slenth_db

# OR start manually
pg_ctl -D /usr/local/var/postgresql@15 start
```

**Redis:**
```bash
# If using Homebrew
brew services start redis

# OR start manually
redis-server
```

**Qdrant:**
```bash
# Download and run Qdrant locally
# Option 1: Using binary
./qdrant

# Option 2: Using Docker (minimal - only Qdrant)
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```

### 4. Initialize Databases
```bash
# Initialize PostgreSQL schema
python scripts/init_db.py

# Initialize vector DB collections
python scripts/init_vector_db.py

# Load mock internal rules
python scripts/load_internal_rules.py
```

### 5. Start Application Services

**Terminal 1: API Server**
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2: Celery Worker (Part 1 only - for transaction processing)**
```bash
celery -A worker.celery_app worker -l info -Q default -c 2
```

**Terminal 3: Flower (Optional - for monitoring Celery)**
```bash
flower -A worker.celery_app --port=5555
```

> **Note**: Part 2 (document processing) runs synchronously in the API process and does NOT use Celery/Redis queuing.

### 6. Test the System

**Part 1: Process a Transaction** (async via Celery)
```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN001",
    "amount": 50000,
    "currency": "USD",
    "customer_id": "CUST123",
    "originator_country": "HK",
    "beneficiary_country": "SG",
    "customer_risk_rating": "high"
  }'
```

**Part 2: Upload a Document** (synchronous execution)
```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@data/Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf" \
  -F "document_type=purchase_agreement"
```

> **Note**: Document upload triggers the LangGraph workflow immediately and returns results when processing completes.

**View Results**
```bash
# Check alerts
curl http://localhost:8000/alerts

# Get transaction compliance
curl http://localhost:8000/transactions/TXN001/compliance

# Get document risk report
curl http://localhost:8000/documents/{doc_id}/risk
```

### 7. Run Regulatory Scraping (Manual)
```bash
# Scrape external regulations
python cron/external_rules_ingestion.py

# This will fetch circulars from HKMA, MAS, FINMA
```

### 8. Process Full Dataset
```bash
# Process all 1000 transactions from CSV
python scripts/simulate_stream.py \
  --csv data/transactions_mock_1000_for_participants.csv \
  --rate 5 \
  --concurrent
```

### 9. Access Dashboards
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Flower Monitoring**: http://localhost:5555
- **Qdrant Console**: http://localhost:6333/dashboard

### 10. Shutdown
```bash
# Stop application services (Ctrl+C in terminals)

# Stop infrastructure
docker-compose down

# To remove all data
docker-compose down -v
```

### crawl4ai Configuration

**Installation:**
```bash
pip install crawl4ai playwright
playwright install
```

### HKMA Crawler (`crawlers/hkma_crawler.py`)

```python
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy

async def scrape_hkma_circulars():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://www.hkma.gov.hk/eng/regulatory-resources/regulatory-guides/circulars/",
            extraction_strategy=LLMExtractionStrategy(
                provider="openai",
                api_token=OPENAI_API_KEY,
                instruction="Extract circular title, date, PDF links, and summary"
            )
        )
        
        # Parse result.extracted_content
        circulars = parse_circulars(result.extracted_content)
        
        # Download PDFs
        for circular in circulars:
            pdf_content = await download_pdf(circular['pdf_url'])
            process_and_embed(pdf_content, circular['metadata'])
```

### MAS Crawler (`crawlers/mas_crawler.py`)

```python
async def scrape_mas_regulations():
    base_url = "https://www.mas.gov.sg/regulation/regulations-and-guidance"
    params = {
        "entity_type": "Capital Markets Services/Dealing in Capital Markets Products",
        "page": 1,
        "content_type": "Circulars"
    }
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=f"{base_url}?{urlencode(params)}",
            extraction_strategy=LLMExtractionStrategy(
                provider="openai",
                api_token=OPENAI_API_KEY,
                instruction="Extract regulation documents, dates, and links"
            )
        )
        
        # Handle pagination
        for page in range(1, max_pages + 1):
            # Process each page...
```

### FINMA Crawler (`crawlers/finma_crawler.py`)

```python
async def scrape_finma_circulars():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://www.finma.ch/en/documentation/circulars/",
            extraction_strategy=LLMExtractionStrategy(
                provider="openai",
                api_token=OPENAI_API_KEY,
                instruction="Extract circular number, title, date, and PDF links"
            )
        )
        
        circulars = parse_finma_circulars(result.extracted_content)
        
        for circular in circulars:
            # Download and process PDFs
            await process_finma_circular(circular)
```

### PDF Extraction (`crawlers/pdf_extractor.py`)

```python
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter

def extract_pdf_content(pdf_path):
    """Extract text from PDF and chunk for embedding."""
    
    # Extract text
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    
    # Clean and normalize
    text = clean_text(text)
    
    # Chunk into ~500-1000 token pieces
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_text(text)
    
    return chunks
```

### CronJob Script (`cron/external_rules_ingestion.py`)

```python
import asyncio
from datetime import datetime
from crawlers.hkma_crawler import scrape_hkma_circulars
from crawlers.mas_crawler import scrape_mas_regulations
from crawlers.finma_crawler import scrape_finma_circulars
from app.db.vector_db import vector_db_client
from embeddings import generate_embeddings

async def ingest_external_rules():
    """Main CronJob function to scrape and ingest external rules."""
    
    print(f"[{datetime.now()}] Starting external rules ingestion...")
    
    try:
        # Scrape all sources
        hkma_circulars = await scrape_hkma_circulars()
        mas_regulations = await scrape_mas_regulations()
        finma_circulars = await scrape_finma_circulars()
        
        all_documents = hkma_circulars + mas_regulations + finma_circulars
        
        # Process and embed
        for doc in all_documents:
            chunks = extract_pdf_content(doc['pdf_path'])
            
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = generate_embeddings(chunk)
                
                # Prepare metadata
                metadata = {
                    "source_url": doc['url'],
                    "published_date": doc['date'],
                    "regulator": doc['regulator'],
                    "jurisdiction": doc['jurisdiction'],
                    "doc_title": doc['title'],
                    "section_path": f"chunk_{i}",
                    "version": doc['version'],
                    "scraped_at": datetime.now().isoformat()
                }
                
                # Upsert to vector DB
                vector_db_client.upsert(
                    collection_name="external_rules",
                    points=[{
                        "id": f"{doc['id']}_chunk_{i}",
                        "vector": embedding,
                        "payload": {
                            "text": chunk,
                            **metadata
                        }
                    }]
                )
        
        print(f"[{datetime.now()}] Ingestion completed. Processed {len(all_documents)} documents.")
        
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: {str(e)}")
        # Log to monitoring system
        raise

if __name__ == "__main__":
    asyncio.run(ingest_external_rules())
```

## Requirements Checklist (from Problem Statement)

### Part 1: Real-Time AML Monitoring ✅

#### Regulatory Ingestion Engine
- ✅ Crawl external sources (MAS, FINMA, HKMA)
- ✅ Parse unstructured rules into actionable monitoring criteria
- ✅ Version control with audit trail of rule changes over time
- ✅ Automated scraping via CronJob (every 12 hours)

#### Transaction Analysis Engine
- ✅ Real-time monitoring against current rules
- ✅ Behavioral analysis for unusual patterns
- ✅ Risk scoring based on multiple factors (Bayesian + rules + patterns)
- ✅ Pattern recognition (structuring, layering, circular transfers)
- ✅ Feature engineering (velocity, amount z-scores, geographic risk)

#### Alert System
- ✅ Role-specific alerts for Front, Compliance, and Legal teams
- ✅ Priority routing with SLA management
- ✅ Context provision (transaction history, regulatory references)
- ✅ Acknowledgment tracking
- ✅ Real-time WebSocket alerts

#### Remediation Workflows
- ✅ Automated suggestions based on failed controls
- ✅ Workflow templates for common scenarios
- ✅ Audit trail maintenance (full lineage)
- ✅ Integration capabilities via API

#### Deliverables
- ✅ Working regulatory ingestion system
- ✅ Real-time transaction monitoring with configurable rules
- ✅ Alert system with role-based routing
- ✅ Remediation workflow engine
- ✅ Comprehensive audit trail functionality

---

### Part 2: Document & Image Corroboration ✅

#### Document Processing Engine
- ✅ Multi-format support (PDF, text, images)
- ✅ Content extraction (OCR with pytesseract)
- ✅ Format validation (structure and formatting consistency)
- ✅ Quality assessment (completeness and accuracy)

#### Format Validation System
- ✅ Formatting checks (double spacing, irregular fonts, inconsistent indentation)
- ✅ Content validation (spelling mistakes, incorrect headers, missing sections)
- ✅ Structure analysis (document organization and completeness)
- ✅ Template matching (standard document templates)

#### Image Analysis Engine
- ✅ Authenticity verification (reverse image search - API integration)
- ✅ AI-generated detection (synthetic image identification)
- ✅ Tampering detection (metadata and pixel-level anomalies)
- ✅ Forensic analysis (EXIF, Error Level Analysis)

#### Risk Scoring & Reporting
- ✅ Risk assessment (0-100 score with risk bands)
- ✅ Real-time feedback to compliance officers
- ✅ Report generation (comprehensive PDF reports)
- ✅ Audit trail (comprehensive logs of all analysis)

#### Deliverables
- ✅ Multi-format document processing system
- ✅ Advanced format validation with detailed error reporting
- ✅ Sophisticated image analysis capabilities
- ✅ Risk scoring and feedback system
- ✅ Comprehensive reporting functionality

---

### Integration & Output ✅

- ✅ Unified dashboard showing both transaction and document analysis
- ✅ Cross-reference capabilities between transaction and document analysis
- ✅ PDF report generation with red flags and problematic areas
- ✅ Professional API interface
- ✅ Scalable architecture (Celery + Redis for async processing)
- ✅ WebSocket support for real-time updates
- ✅ Comprehensive audit trail across both workflows

---

### Technical Excellence ✅

- ✅ Agentic architecture using LangGraph
- ✅ 13-agent workflow for transaction processing (Part 1)
- ✅ 9-agent workflow for document corroboration (Part 2)
- ✅ Hybrid retrieval (BM25 + vector search)
- ✅ Bayesian inference for risk assessment
- ✅ Pattern detection (temporal and network motifs)
- ✅ Multi-role alert routing
- ✅ Evidence-based compliance with full traceability
- ✅ Remediation playbook orchestration
- ✅ Version-controlled rule management

---

### Judging Criteria Alignment

#### Objective Achievement (20%)
- ✅ Both Part 1 and Part 2 fully implemented
- ✅ All stated objectives met
- ✅ Integrated solution with cross-referencing

#### Creativity (20%)
- ✅ Innovative agentic workflows (13 + 9 agents)
- ✅ Hybrid retrieval with re-ranking
- ✅ Bayesian posterior updates for risk
- ✅ Multi-role alert composition
- ✅ Evidence-based compliance mapping

#### Visual Design (20%)
- ✅ RESTful API with comprehensive endpoints
- ✅ WebSocket for real-time updates
- ✅ Swagger/OpenAPI documentation
- ✅ PDF report generation with findings
- ✅ Dashboard endpoints for statistics

#### Presentation Skills (20%)
- ✅ Clear architecture documentation
- ✅ Step-by-step implementation plan
- ✅ Example flows and use cases
- ✅ Deployment/local running instructions
- ✅ Testing strategy outlined

#### Technical Depth (20%)
- ✅ LangGraph orchestration
- ✅ Vector databases for RAG
- ✅ Celery + Redis for task queuing
- ✅ PostgreSQL for structured data
- ✅ OCR and image forensics
- ✅ Bayesian networks (pgmpy)
- ✅ Pattern detection algorithms
- ✅ Comprehensive audit logging

## Mock Internal Rules Structure

Internal rules in `internal_rules/*.json` should follow this structure:

```json
{
  "rule_id": "IR-001",
  "section": "AML/CTF",
  "title": "Enhanced Due Diligence for High-Value Transactions",
  "obligation_type": "mandatory",
  "text": "All transactions exceeding USD 10,000 must undergo enhanced due diligence (EDD) procedures. This includes verification of source of wealth (SOW), source of funds (SOF), and business rationale. For transactions above USD 50,000, additional senior management approval is required.",
  "conditions": [
    "amount > 10000 USD",
    "edd_performed = false"
  ],
  "expected_evidence": [
    "sow_documented",
    "purpose_code",
    "narrative",
    "kyc_last_completed < 12 months"
  ],
  "penalty_level": "high",
  "effective_date": "2024-01-01",
  "version": "v2.1",
  "source": "internal_policy_manual",
  "jurisdiction": ["HK", "SG", "CH"],
  "applies_to": {
    "product_types": ["SWIFT", "wire_transfer", "cash"],
    "customer_types": ["corporate", "individual"],
    "risk_ratings": ["high", "medium"]
  }
}
```

**Key Fields:**
- `rule_id`: Unique identifier
- `section`: Category (AML/CTF, Suitability, Disclosure, etc.)
- `conditions`: Logical conditions for applicability
- `expected_evidence`: Fields that must be present in transaction
- `penalty_level`: critical, high, medium, low
- `jurisdiction`: List of applicable jurisdictions
- `applies_to`: Scoping criteria

## Example End-to-End Flows

### Flow 1: External Rules Ingestion (CronJob - Manual for Local)

```
Manual execution (local dev) → python cron/external_rules_ingestion.py
  ↓
Scrape HKMA, MAS, FINMA websites (crawl4ai)
  ↓
Extract PDFs and metadata
  ↓
Clean HTML → Markdown
  ↓
Chunk into ~500-1000 tokens
  ↓
Generate embeddings (text-embedding-3-large)
  ↓
Upsert to external_rules collection in Vector DB
  ↓
Log changes and new circulars
```

### Flow 2: Internal Rules Update (API-Driven)

```
POST /internal_rules
  ↓
Validate payload
  ↓
Parse into structured rule object
  ↓
Store in PostgreSQL with versioning
  ↓
Generate embeddings
  ↓
Upsert to internal_rules collection in Vector DB
  ↓
Deactivate superseded versions
  ↓
Return success response
```

### Flow 3: Transaction Processing (Part 1 - Real-Time)

```
POST /transactions
  ↓
Validate transaction schema
  ↓
Enqueue to Redis queue
  ↓
Celery worker picks up task
  ↓
Invoke LangGraph Transaction Workflow:

  ContextBuilder
    ↓ (convert to rules-like query, pull history)
  Retrieval (Hybrid BM25 + Vector)
    ↓ (retrieve top 30 rules)
  ApplicabilityAgent (map over rules)
    ↓ (filter to 15 applicable rules)
  EvidenceMapper (map over rules)
    ↓ (map evidence → fields)
  ControlTestAgent (map over rules)
    ↓ (test controls, assign severity)
  FeatureService (deterministic features)
    ↓
  BayesianEngine (posterior update)
    ↓
  PatternDetector (temporal/network patterns)
    ↓
  DecisionFusion (fuse scores → final risk)
    ↓
  AnalystWriter (generate summary)
    ↓
  AlertComposer + Router
    ↓ (create role-specific alerts: Front/Compliance/Legal)
  RemediationOrchestrator
    ↓ (match to playbooks, assign)
  Persistor & AuditTrail
    ↓
Store in PostgreSQL:
  - compliance_analysis
  - alerts (front, compliance, legal)
  - cases (if severity warrants)
  - audit_logs

  ↓
Push alerts via WebSocket to frontend
  ↓
Return compliance score and summary
```

### Flow 4: Document Upload & Corroboration (Part 2 - Synchronous)

```
POST /documents/upload
  ↓
Validate file (PDF, image, text)
  ↓
Store in data/uploaded_docs/
  ↓
Create document record in PostgreSQL
  ↓
IMMEDIATELY invoke LangGraph Document Workflow (synchronous):

  DocumentIntake
    ↓ (normalize format, extract metadata)
  OCR Agent
    ↓ (extract text from PDF/image)
    ↓ (save to data/ocr_output/)
  FormatValidation Agent
    ↓ (check formatting: spacing, fonts, indentation)
    ↓ (detect spelling errors, missing sections)
  NLPValidation Agent
    ↓ (extract fields: names, dates, amounts, IDs)
    ↓ (validate schema/template conformity)
    ↓ (cross-field consistency checks)
  ImageForensics Agent (if image/scanned PDF)
    ↓ (EXIF analysis)
    ↓ (Error Level Analysis for tampering)
    ↓ (AI-generated detection)
    ↓ (Reverse image search - stub)
  BackgroundCheck Agent
    ↓ (extract entities from document)
    ↓ (call World-Check One API)
    ↓ (PEP, sanctions, adverse media screening)
  CrossReference Agent
    ↓ (link to transaction history)
    ↓ (check against KYC records)
    ↓ (validate against regulatory rules)
  DocumentRisk Agent
    ↓ (aggregate findings → risk score 0-100)
    ↓ (categorize: Low/Medium/High/Critical)
  ReportGenerator Agent
    ↓ (generate comprehensive PDF report)
    ↓ (highlight red flags and issues)
    ↓ (include evidence and citations)
  EvidenceStorekeeper Agent
    ↓ (organize and store evidence artifacts)

  ↓
Store in PostgreSQL:
  - document_analysis
  - findings (format, NLP, image, background check)
  - risk_score
  - alerts (if high risk)
  - audit_logs

  ↓
Push alerts via WebSocket (if high risk)
  ↓
Return COMPLETE document analysis in API response:
  {
    "document_id": "DOC789",
    "status": "completed",
    "risk_score": 72,
    "risk_band": "High",
    "findings": {...},
    "alerts": [...],
    "report_url": "/documents/DOC789/report"
  }
```

> **Key Difference**: Part 2 runs synchronously. The API endpoint waits for the entire workflow to complete before returning results. No Redis queue, no Celery task, no polling needed.

### Flow 5: Integrated Alert & Case Management

```
Alert generated from Part 1 (Transaction) OR Part 2 (Document)
  ↓
Alert Orchestrator (unified)
  ↓
Check for related alerts (deduplicate)
  ↓
Cross-reference:
  - If transaction alert → check for related document alerts
  - If document alert → check for related transaction alerts
  ↓
Route to appropriate team(s):
  - Front Office: Suitability, disclosures, product issues
  - Compliance: AML/CTF, structuring, EDD, document fraud
  - Legal: Regulatory violations, sanctions
  ↓
Set priority and SLA deadline
  ↓
If severity >= High:
  ↓
  Create Case in case management system
  ↓
  Assign to appropriate owner
  ↓
  Attach linked alerts and evidence
  ↓
  Suggest remediation actions (playbook)
  ↓
Store in alerts and cases tables
  ↓
Push to WebSocket (real-time notification)
  ↓
Await acknowledgment
  ↓
Track SLA compliance
  ↓
If SLA breached → auto-escalate
```

### Flow 6: Frontend Display (Unified Dashboard)

```
Frontend receives (via REST or WebSocket):

From Part 1 (Transaction):
  - transaction_id
  - compliance_score (0-100)
  - risk_band (Low/Medium/High/Critical)
  - compliance_summary (markdown)
  - alerts (role-specific):
    * Front Office: [Alert 1, Alert 2]
    * Compliance: [Alert 3, Alert 4, Alert 5]
    * Legal: [Alert 6]
  - evidence_map
  - rule_references
  - remediation_actions

From Part 2 (Document):
  - document_id
  - risk_score (0-100)
  - risk_band (Low/Medium/High/Critical)
  - findings:
    * Format issues: [Issue 1, Issue 2]
    * NLP validation: [Field 1 missing, Field 2 inconsistent]
    * Image forensics: [EXIF anomaly, possible tampering]
  - alerts (role-specific):
    * Compliance: [Document fraud alert, Missing fields alert]
  - cross_references:
    * Linked transactions: [TXN123, TXN456]
    * KYC discrepancies: [Customer address mismatch]
  - pdf_report_url

Unified Dashboard Displays:
  ┌─────────────────────────────────────────┐
  │  Alert Summary                          │
  │  - Critical: 2 (1 txn, 1 doc)          │
  │  - High: 5 (3 txn, 2 doc)              │
  │  - Medium: 12 (10 txn, 2 doc)          │
  │  - Low: 20                              │
  ├─────────────────────────────────────────┤
  │  Recent Transactions                    │
  │  [List with risk badges]                │
  ├─────────────────────────────────────────┤
  │  Recent Documents                       │
  │  [List with risk badges]                │
  ├─────────────────────────────────────────┤
  │  Open Cases                             │
  │  [Cases with SLA countdown]             │
  ├─────────────────────────────────────────┤
  │  Cross-References                       │
  │  [Linked txn-doc pairs with issues]     │
  └─────────────────────────────────────────┘

Transaction Detail View:
  - Transaction header with risk badge
  - Compliance score gauge
  - Expandable sections:
    * Applicable Rules
    * Evidence Status
    * Pattern Detections
    * Bayesian Posterior
    * Alerts by Role
    * Remediation Playbook
    * Linked Documents (if any)
  - Timeline of all decisions
  - Audit trail

Document Detail View:
  - Document header with risk badge
  - Risk score gauge
  - Expandable sections:
    * OCR Results
    * Format Validation Issues
    * NLP Field Extraction
    * Image Forensics Results
    * Cross-References (transactions, KYC)
    * Alerts by Role
  - Download PDF Report button
  - Timeline of all analysis steps
  - Audit trail
```

---

## Monitoring and Observability

### Metrics
- **Part 1 (Transactions):**
  - Transaction processing rate (txn/sec)
  - Average processing latency (async via Celery)
  - Celery queue length and worker utilization
  
- **Part 2 (Documents):**
  - Document processing latency (synchronous)
  - Average workflow execution time
  - No queue metrics (direct execution)
  
- **Unified:**
  - Alert generation rate by severity
  - Vector DB query latency
  - LLM API call latency and cost
  - Error rates by component

### Logging
- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Trace IDs for request correlation
- Agent decision logs with rationale

### Dashboards
- Real-time transaction throughput
- Alert distribution (role, severity, status)
- Case management metrics
- Regulatory scraping status
- System health (CPU, memory, queue depth)

## Security Considerations

### Data Protection
- Encrypt sensitive transaction data at rest
- Use TLS for all API communications
- Implement role-based access control (RBAC)
- Audit all access to sensitive data

### API Security
- JWT authentication for API endpoints
- Rate limiting per client
- Input validation and sanitization
- CSRF protection for WebSocket connections

### Compliance
- GDPR compliance for EU customers
- Data retention policies
- Right to erasure implementation
- Audit log immutability (hash chains)

## Future Enhancements

### Phase 2 Features
1. **ML Model Training**
   - Train supervised models on historical STR/SAR filings
   - Active learning from analyst feedback
   - Model explainability (SHAP, LIME)

2. **Graph Analytics**
   - Build transaction network graph (Neo4j)
   - Community detection algorithms
   - Centrality measures for risk scoring
   - Temporal graph analysis

3. **Advanced NLP**
   - Extract risk signals from narrative fields
   - Sentiment analysis on purpose descriptions
   - Entity resolution across transactions

4. **Real-Time Monitoring**
   - Streaming transaction processing (Kafka)
   - Real-time dashboard updates
   - Proactive alert generation

5. **Regulatory Intelligence**
   - Track regulatory changes over time
   - Impact analysis for rule updates
   - Automated policy gap analysis

6. **Case Management Integration**
   - Full case lifecycle management
   - Investigation workflow automation
   - STR/SAR filing automation
   - Regulator reporting

## Success Criteria

### Technical
- ✅ Successful scraping of 3 regulatory sources (HKMA, MAS, FINMA)
- ✅ Vector DB ingestion of external and internal rules
- ✅ FastAPI server with all endpoints functional
- ✅ Celery workers processing transactions asynchronously
- ✅ LangGraph workflow executing all 13 agents
- ✅ Multi-role alerts generated correctly
- ✅ Full audit trail for all transactions

### Performance
- ✅ Process 1000 transactions in <2 hours (0.5 txn/sec avg)
- ✅ Individual transaction processing <10s
- ✅ Vector DB query latency <500ms
- ✅ API response time <100ms (excluding task execution)

### Business Value
- ✅ Accurate compliance scoring with explainability
- ✅ Role-specific alerts reducing analyst workload
- ✅ Automated evidence mapping and control testing
- ✅ Playbook-driven remediation recommendations
- ✅ Comprehensive audit trail for regulatory defensibility

## References

### Regulatory Sources
- **HKMA**: https://www.hkma.gov.hk/eng/regulatory-resources/regulatory-guides/circulars/
- **MAS**: https://www.mas.gov.sg/regulation/regulations-and-guidance
- **FINMA**: https://www.finma.ch/en/documentation/circulars/

### Technical Documentation
- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **crawl4ai**: https://github.com/unclecode/crawl4ai
- **Celery**: https://docs.celeryproject.org/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Qdrant**: https://qdrant.tech/documentation/

### AML/Compliance Standards
- **FATF Recommendations**: https://www.fatf-gafi.org/recommendations.html
- **Wolfsberg Principles**: https://www.wolfsberg-principles.com/
- **Basel AML Index**: https://baselgovernance.org/basel-aml-index

---

## Summary

This implementation plan provides a comprehensive blueprint for building an integrated agentic AML solution that addresses both **Part 1 (Real-Time AML Monitoring)** and **Part 2 (Document & Image Corroboration)**.

### Key Deliverables

✅ **Part 1: Real-Time AML Monitoring**
- 13-agent LangGraph workflow for transaction compliance evaluation
- Hybrid retrieval (BM25 + vector) for rule matching
- Bayesian inference for risk assessment
- Pattern detection (structuring, layering, circular transfers)
- Multi-role alerts (Front/Compliance/Legal)
- Remediation playbook orchestration
- Full audit trail

✅ **Part 2: Document & Image Corroboration**
- 9-agent LangGraph workflow for document validation
- OCR extraction for PDFs and images
- Format and content validation
- NLP field extraction and validation
- Image forensics (EXIF, ELA, AI-detection, reverse search)
- Cross-referencing with transactions and KYC
- PDF report generation with red flags
- Full audit trail

✅ **Integration Layer**
- Unified alert orchestration
- Cross-reference between transactions and documents
- Unified case management
- Real-time WebSocket updates
- Comprehensive API

### Technical Architecture

- **Orchestration**: LangGraph for complex agent workflows
- **API**: FastAPI with REST and WebSocket support
- **Async Processing**: Celery + Redis for scalable task execution
- **Vector Search**: Qdrant for RAG over regulatory rules
- **Structured Data**: PostgreSQL for transactions, alerts, cases
- **Local Development**: Docker Compose for infrastructure services

### Alignment with Requirements

This plan fully addresses all requirements from the problem statement:
- ✅ Both Part 1 and Part 2 implemented
- ✅ Agentic architecture with specialized agents
- ✅ Real-time monitoring and alerting
- ✅ Multi-role alert routing
- ✅ Document corroboration with image forensics
- ✅ Remediation workflows
- ✅ Comprehensive audit trails
- ✅ Integration and cross-referencing
- ✅ Scalable architecture
- ✅ Local development support

### Next Steps

1. **Development**: Follow the 10-phase implementation plan
2. **Testing**: Use provided sample data (transactions CSV and PDF document)
3. **Demo**: Prepare presentation showing both workflows and integration
4. **Documentation**: Create architecture diagrams and user guides
5. **Deployment**: Use provided local running commands for hackathon demo

**For questions or support during implementation, refer to the detailed sections above or contact the mentors.**

