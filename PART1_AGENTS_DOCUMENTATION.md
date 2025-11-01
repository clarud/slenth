# Part 1 Agents Documentation

This document provides comprehensive information about the 13 agents in Part 1 of the transaction workflow system. These agents work sequentially to analyze transactions for AML (Anti-Money Laundering) compliance and regulatory violations.

## Overview

The Part 1 workflow processes transactions through 13 specialized agents, each responsible for a specific aspect of compliance analysis:

1. **ContextBuilder** - Transaction context extraction
2. **Retrieval** - Rule retrieval via hybrid search
3. **Applicability** - Rule applicability determination
4. **FeatureService** - Feature engineering
5. **PatternDetector** - AML pattern detection
6. **BayesianEngine** - Risk probability calculation
7. **EvidenceMapper** - Evidence field mapping
8. **ControlTest** - Control compliance testing
9. **DecisionFusion** - Risk score aggregation
10. **AlertComposer** - Role-based alert generation
11. **AnalystWriter** - Compliance report writing
12. **Persistor** - Data persistence and audit trail
13. **RemediationOrchestrator** - Remediation action planning

---

## Agent 1: ContextBuilderAgent

### Purpose
Build query context from transaction data by converting transaction JSON into rule-like query strings and pulling short transaction history.

### Logic
1. Extract key fields from transaction (jurisdiction, customer_risk, amount, counterparty countries)
2. Build query strings that match regulatory rule language
3. Fetch recent transaction history for customer (last 30 days)
4. Format as structured context dictionary

### Inputs
- `transaction`: Transaction data dictionary
- `db_session`: Database session for querying transaction history

### Outputs
- `query_strings`: List[str] - Natural language queries for rule retrieval
- `transaction_history`: List[Dict] - Recent transactions for the customer
- `context_summary`: str - Formatted summary of context

### Key Features
- Jurisdiction-based query generation
- Risk rating-based queries
- PEP (Politically Exposed Person) detection
- EDD (Enhanced Due Diligence) requirement checking
- High-value transaction identification
- Cross-border transaction flagging
- Transaction history aggregation (30-day window)

### Implementation Status
✅ **Fully Implemented**

---

## Agent 2: RetrievalAgent

### Purpose
Perform semantic search to retrieve applicable regulatory rules from both internal and external rule repositories using Pinecone's integrated embeddings.

### Logic
1. Take query_strings from ContextBuilder
2. Perform semantic search using Pinecone's built-in embedding (no separate embedding service needed)
3. Search both internal_rules (Pinecone internal index) and external_rules (Pinecone external index)
4. Apply filters (jurisdiction, effective_date, is_active)
5. Re-rank results by relevance
6. Return top-k applicable rules with metadata
7. Deduplicate results across sources

### Inputs
- `query_strings`: List[str] - Query strings from ContextBuilder
- `transaction`: Transaction data for jurisdiction filtering
- `pinecone_internal`: PineconeService for internal rules (PINECONE_INTERNAL_INDEX_HOST)
- `pinecone_external`: PineconeService for external rules (PINECONE_EXTERNAL_INDEX_HOST)

### Outputs
- `applicable_rules`: List[Dict] - Retrieved rules with metadata
  - `rule_id`: Unique identifier
  - `text`: Rule content
  - `score`: Relevance score
  - `metadata`: Jurisdiction, effective_date, source, etc.

### Key Features
- Dual-source retrieval (internal + external rules)
- Pinecone integrated embeddings (no separate embedding service)
- Jurisdiction-based filtering
- Effective date validation
- Semantic search via Pinecone
- Deduplication across sources
- Top-k re-ranking (top_k=10 per query)

### Implementation Example
```python
# Pinecone semantic search with integrated embeddings
results = index.search(
    namespace="internal-rules",
    query={
        "inputs": {"text": query_text},
        "top_k": 10
    },
    fields=["text", "rule_id", "jurisdiction", "effective_date", "severity"]
)
```

### Environment Variables
- `PINECONE_API_KEY`: Pinecone API key
- `PINECONE_INTERNAL_INDEX_HOST`: Internal rules index host
- `PINECONE_EXTERNAL_INDEX_HOST`: External rules index host

### Implementation Status
✅ **Fully Implemented**

---

## Agent 3: ApplicabilityAgent

### Purpose
Determine if each retrieved rule actually applies to the specific transaction using LLM-based reasoning.

### Logic
1. For each rule from RetrievalAgent
2. Use LLM to determine applicability
3. Provide rationale and confidence score
4. Filter to only applicable rules (applies=True)

### Inputs
- `applicable_rules`: List[Dict] - Rules from RetrievalAgent
- `transaction`: Transaction data
- `llm_service`: LLM service for applicability determination

### Outputs
- `applicable_rules_filtered`: List[Dict] - Only rules that apply
  - `applies`: bool - True/False
  - `rationale`: str - Explanation
  - `confidence`: float (0.0-1.0)

### Key Features
- LLM-based reasoning for applicability
- Transaction context matching
- Rule-transaction alignment scoring
- Confidence scoring
- Automatic filtering (top 10 rules for efficiency)
- JSON-formatted responses

### Prompt Structure
```
RULE: [rule_text]
TRANSACTION: [transaction_details]
Respond with: {applies, rationale, confidence}
```

### LLM Configuration
- **Provider**: Groq
- **Model**: `openai/gpt-oss-20b`
- **Base URL**: `https://api.groq.com/openai/v1`
- **API Key**: `GROQ_API_KEY` (from environment)

### Implementation Status
✅ **Fully Implemented**

---

## Agent 4: FeatureServiceAgent

### Purpose
Generate deterministic features from transaction data and transaction history for pattern detection and risk scoring.

### Logic
1. Extract basic transaction features (amount, type, geography)
2. Calculate velocity features from transaction history
3. Detect structuring indicators
4. Compute geographic risk factors
5. Identify customer behavior patterns

### Inputs
- `transaction`: Transaction data
- `transaction_history`: List[Dict] - Historical transactions

### Outputs
- `features`: Dict - Feature vectors and flags
  - `amount`: float
  - `is_high_value`: bool (>10,000)
  - `is_round_number`: bool
  - `transaction_count_24h`: int
  - `transaction_count_7d`: int
  - `total_volume_7d`: float
  - `avg_amount_7d`: float
  - `is_cross_border`: bool
  - `is_high_risk_country`: bool
  - `potential_structuring`: bool

### Key Features
- Velocity metrics (24h, 7d)
- Transaction volume analysis
- Geographic risk assessment
- Round number detection
- Structuring pattern identification
- High-value transaction flagging
- Cross-border transaction detection

### Implementation Status
✅ **Fully Implemented**

---

## Agent 5: PatternDetectorAgent

### Purpose
Detect temporal and network AML patterns such as structuring, layering, and circular transfers.

### Logic
1. Analyze transaction sequences for structuring (multiple transactions below threshold)
2. Detect layering (complex transaction chains)
3. Identify circular transfers (round-trip funds)
4. Flag rapid movement (quick in-and-out)
5. Calculate velocity anomalies (unusual transaction frequency)

### Inputs
- `transaction`: Current transaction
- `transaction_history`: Historical transactions
- `features`: Features from FeatureServiceAgent

### Outputs
- `patterns_detected`: List[Dict]
  - `pattern_type`: str (structuring, layering, circular, rapid_movement, velocity)
  - `confidence`: float
  - `description`: str

### Key Features
- Structuring detection
- Layering analysis
- Circular transfer identification
- Rapid movement flagging
- Velocity anomaly detection
- Pattern confidence scoring

### Implementation Status
⚠️ **Placeholder** - Requires full implementation

---

## Agent 6: BayesianEngineAgent

### Purpose
Perform sequential Bayesian posterior update for entity risk assessment based on transaction evidence.

### Logic
1. Load prior risk distribution for customer
2. Update posterior based on transaction evidence
3. Consider rule violations, patterns, and features
4. Output posterior probabilities for risk categories

### Inputs
- `transaction`: Transaction data
- `customer_id`: Customer identifier
- `control_results`: Results from ControlTest
- `patterns_detected`: Patterns from PatternDetector
- `features`: Features from FeatureService

### Outputs
- `bayesian_posterior`: Dict[risk_category] -> probability
  - `low`: float
  - `medium`: float
  - `high`: float
  - `critical`: float

### Key Features
- Prior risk distribution loading
- Evidence-based posterior update
- Multi-factor risk integration
- Probability distribution output
- Sequential learning capability

### Implementation Status
⚠️ **Placeholder** - Requires full implementation

---

## Agent 7: EvidenceMapperAgent

### Purpose
Map expected evidence from applicable rules to concrete transaction fields, identifying present, missing, and contradictory evidence.

### Logic
1. For each applicable rule
2. Extract expected_evidence fields from rule
3. Map to concrete transaction fields
4. Identify present evidence
5. Flag missing evidence
6. Detect contradictory evidence

### Inputs
- `applicable_rules_filtered`: Filtered rules from ApplicabilityAgent
- `transaction`: Transaction data with all fields

### Outputs
- `evidence_map`: Dict[rule_id] -> {present, missing, contradictory}
  - `present`: List[str] - Available evidence fields
  - `missing`: List[str] - Required but missing fields
  - `contradictory`: List[str] - Conflicting evidence

### Key Features
- Rule-to-field mapping
- Documentation requirement checking
- Threshold-based evidence validation
- Missing evidence detection
- Per-rule evidence tracking

### Implementation Status
✅ **Fully Implemented**

---

## Agent 8: ControlTestAgent

### Purpose
Test each control/rule to determine pass/fail/partial status with severity assignment and compliance scoring.

### Logic
1. For each applicable rule
2. Test control based on available evidence
3. Assign severity (critical/high/medium/low)
4. Compute per-rule compliance score (0-100)
5. Provide rationale for test result

### Inputs
- `applicable_rules_filtered`: Filtered rules
- `transaction`: Transaction data
- `evidence_map`: Evidence mapping from EvidenceMapper
- `llm_service`: LLM for control testing

### Outputs
- `control_results`: List[Dict]
  - `rule_id`: str
  - `rule_title`: str
  - `status`: str (pass/fail/partial)
  - `severity`: str (critical/high/medium/low)
  - `compliance_score`: float (0-100)
  - `rationale`: str

### Key Features
- LLM-based control testing
- Evidence-aware assessment
- Severity-based scoring
- Detailed rationale generation
- Per-rule compliance tracking

### Prompt Structure
```
RULE: [title, description, severity]
TRANSACTION: [transaction_details]
EVIDENCE AVAILABLE: [evidence_map]
Respond with: {status, rationale, compliance_score}
```

### LLM Configuration
- **Provider**: Groq
- **Model**: `openai/gpt-oss-20b`
- **Base URL**: `https://api.groq.com/openai/v1`
- **API Key**: `GROQ_API_KEY` (from environment)

### Implementation Status
✅ **Fully Implemented**

---

## Agent 9: DecisionFusionAgent

### Purpose
Fuse rule-based, ML, and pattern-based scores into a final risk score and risk band determination.

### Logic
1. Collect scores from ControlTest, BayesianEngine, PatternDetector
2. Apply weighted fusion algorithm
3. Compute final risk_score (0-100)
4. Determine risk_band (Low/Medium/High/Critical)
5. Generate score breakdown for transparency

### Inputs
- `control_results`: Control test results
- `bayesian_posterior`: Bayesian risk probabilities
- `pattern_scores`: Pattern detection scores

### Outputs
- `risk_score`: float (0-100)
- `risk_band`: str (Low/Medium/High/Critical)
- `score_breakdown`: Dict
  - `rule_based_score`: float
  - `ml_score`: float
  - `pattern_score`: float

### Key Features
- Multi-source score fusion
- Severity-weighted aggregation
- Configurable fusion weights
- Risk band mapping
- Transparent score breakdown

### Weighting Schema
```python
severity_weights = {
    "critical": 1.0,
    "high": 0.7,
    "medium": 0.4,
    "low": 0.2
}

fusion_weights = {
    "rule_based": 0.50,
    "ml_based": 0.30,
    "pattern_based": 0.20
}
```

### Risk Band Thresholds
- **Low**: risk_score < 30
- **Medium**: 30 ≤ risk_score < 60
- **High**: 60 ≤ risk_score < 85
- **Critical**: risk_score ≥ 85

### Implementation Status
✅ **Fully Implemented**

---

## Agent 10: AlertComposerAgent

### Purpose
Compose role-specific alerts routed to Front Office, Compliance, or Legal teams based on findings and severity.

### Logic
1. Determine alert severity from risk_band
2. Route alerts by role based on findings
3. Set SLA deadlines based on severity + role
4. Deduplicate alerts
5. Create alert records in database

### Inputs
- `risk_score`: float
- `risk_band`: str
- `control_results`: Control test results
- `transaction`: Transaction data

### Outputs
- `alerts_generated`: List[Dict]
  - `alert_type`: str
  - `severity`: str
  - `assigned_to`: str (Front/Compliance/Legal)
  - `sla_deadline`: datetime
  - `alert_details`: Dict

### Key Features
- Role-based alert routing
- SLA deadline calculation
- Alert deduplication
- Multi-role alerting
- Priority-based assignment

### Alert Routing Rules
- **Critical risk** → Compliance + Legal
- **High risk** → Compliance
- **Medium risk** → Front Office + Compliance
- **Low risk** → Front Office

### SLA Deadlines
- **Critical**: 4 hours
- **High**: 24 hours
- **Medium**: 48 hours
- **Low**: 72 hours

### Implementation Status
⚠️ **Placeholder** - Requires full implementation

---

## Agent 11: AnalystWriterAgent

### Purpose
Generate concise, human-readable compliance analysis summary with key findings, regulatory concerns, and recommendations.

### Logic
1. Summarize key findings from all agents
2. Include rule IDs and violations
3. Reference evidence
4. Provide rationale
5. Generate structured report with sections

### Inputs
- `transaction`: Transaction data
- `control_results`: Control test results
- `risk_score`: Risk score
- `risk_band`: Risk band
- `pattern_scores`: Pattern scores
- `llm_service`: LLM for report generation

### Outputs
- `analyst_report`: str - Full report (300-500 words)
- `compliance_summary`: str - Short version (500 chars)
- `recommendations`: List[str] - Action recommendations

### Key Features
- LLM-generated professional reports
- Multi-section structure
- Evidence-based findings
- Actionable recommendations
- Executive summary generation

### Report Structure
1. **Executive Summary**
2. **Key Findings**
3. **Regulatory Concerns**
4. **Recommendations**

### LLM Configuration
- **Provider**: Groq
- **Model**: `openai/gpt-oss-20b`
- **Base URL**: `https://api.groq.com/openai/v1`
- **API Key**: `GROQ_API_KEY` (from environment)

### Implementation Status
✅ **Fully Implemented**

---

## Agent 12: PersistorAgent

### Purpose
Persist all analysis results to database and maintain comprehensive audit trail for regulatory compliance.

### Logic
1. Store ComplianceAnalysis to database
2. Update Transaction record with risk scores
3. Create Alert records
4. Create Case records if needed
5. Log to AuditLog
6. Store data hashes and versions

### Inputs
- `transaction_id`: Transaction identifier
- `risk_score`: Final risk score
- `risk_band`: Risk band
- `applicable_rules`: All applicable rules
- `control_results`: Control test results
- `analyst_report`: Analyst report
- `db_session`: Database session

### Outputs
- `persisted`: bool - Success flag
- `records_created`: List[str] - Created record IDs

### Key Features
- Multi-table persistence
- Audit trail creation
- Transaction status updates
- Compliance record creation
- Alert record generation
- Case management integration
- Version control
- Data integrity checks

### Database Operations
1. Update `Transaction` record
2. Create `ComplianceAnalysis` record
3. Create `Alert` records
4. Create `Case` records (if threshold met)
5. Create `AuditLog` entries
6. Commit with error handling

### Implementation Status
✅ **Fully Implemented**

---

## Agent 13: RemediationOrchestratorAgent

### Purpose
Suggest remediation actions with assigned owners and SLA deadlines based on compliance findings.

### Logic
1. Map findings to remediation playbooks
2. Assign action owners (Front/Compliance/Legal)
3. Set SLA deadlines
4. Create cases if needed
5. Link alerts to cases

### Inputs
- `control_results`: Failed/partial controls
- `risk_band`: Risk severity
- `transaction`: Transaction data
- `alerts_generated`: Generated alerts

### Outputs
- `remediation_actions`: List[Dict]
  - `action`: str - Remediation action
  - `owner`: str - Assigned role
  - `sla_deadline`: datetime
  - `priority`: str
  - `linked_case_id`: str (optional)

### Key Features
- Playbook-based recommendations
- Owner assignment logic
- SLA deadline calculation
- Case creation automation
- Alert-to-case linking
- Priority-based routing

### Remediation Playbooks
- **Missing EDD** → Compliance review, 24h SLA
- **Structuring detected** → Investigate + SAR filing
- **High-risk jurisdiction** → Enhanced monitoring
- **PEP without EDD** → Immediate EDD completion
- **Threshold violations** → Regulatory reporting

### Implementation Status
⚠️ **Placeholder** - Requires full implementation

---

## Workflow Execution Flow

```
Transaction Input
    ↓
1. ContextBuilder → query_strings, transaction_history
    ↓
2. Retrieval → applicable_rules
    ↓
3. Applicability → applicable_rules_filtered
    ↓
4. FeatureService → features
    ↓
5. PatternDetector → patterns_detected
    ↓
6. BayesianEngine → bayesian_posterior
    ↓
7. EvidenceMapper → evidence_map
    ↓
8. ControlTest → control_results
    ↓
9. DecisionFusion → risk_score, risk_band
    ↓
10. AlertComposer → alerts_generated
    ↓
11. AnalystWriter → analyst_report
    ↓
12. Persistor → persisted records
    ↓
13. RemediationOrchestrator → remediation_actions
    ↓
Workflow Complete
```

---

## Implementation Status Summary

| Agent # | Agent Name | Status | Complexity |
|---------|------------|--------|------------|
| 1 | ContextBuilder | ✅ Complete | Medium |
| 2 | Retrieval | ✅ Complete | High |
| 3 | Applicability | ✅ Complete | Medium |
| 4 | FeatureService | ✅ Complete | Low |
| 5 | PatternDetector | ⚠️ Placeholder | High |
| 6 | BayesianEngine | ⚠️ Placeholder | High |
| 7 | EvidenceMapper | ✅ Complete | Medium |
| 8 | ControlTest | ✅ Complete | Medium |
| 9 | DecisionFusion | ✅ Complete | Medium |
| 10 | AlertComposer | ⚠️ Placeholder | Medium |
| 11 | AnalystWriter | ✅ Complete | Low |
| 12 | Persistor | ✅ Complete | Medium |
| 13 | RemediationOrchestrator | ⚠️ Placeholder | Medium |

**Legend:**
- ✅ Complete: Fully implemented with logic
- ⚠️ Placeholder: Structure exists, logic needs implementation

---

## Shared Dependencies

All agents inherit from `Part1Agent` base class and may utilize:

### Services
- `LLMService`: Groq-based reasoning (openai/gpt-oss-20b model)
- `PineconeService`: Pinecone vector store with integrated embeddings (internal/external indexes)
- `AuditService`: Audit trail logging
- `AlertService`: Alert management

**Note**: `VectorDBService` and `EmbeddingService` are deprecated. Pinecone provides integrated embeddings.

### Database Models
- `Transaction`: Transaction records
- `ComplianceAnalysis`: Analysis results
- `Alert`: Alert records
- `Case`: Case management
- `AuditLog`: Audit trail

### State Management
All agents receive and return a `state` dictionary that accumulates:
- Transaction data
- Intermediate results
- Agent outputs
- Error tracking

---

## Agent Configuration

### Environment Variables
```bash
# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INTERNAL_INDEX_HOST=your_internal_index_host
PINECONE_EXTERNAL_INDEX_HOST=your_external_index_host

# LLM Configuration (Groq)
GROQ_API_KEY=your_groq_api_key
```

### Agent Initialization
```python
agent = AgentClass(
    llm_service=llm_service,        # Groq LLM service
    pinecone_internal=pinecone_internal,  # For Retrieval (internal rules)
    pinecone_external=pinecone_external,  # For Retrieval (external rules)
    audit_service=audit_service,     # For Persistor
    alert_service=alert_service,     # For Persistor
    db_session=db_session           # For database operations
)
```

**Note**: `vector_service` and `embedding_service` are deprecated and removed from configuration.

---

## Error Handling

All agents implement consistent error handling:

```python
try:
    # Agent logic
    state["agent_completed"] = True
except Exception as e:
    logger.error(f"Error in {AgentName}: {str(e)}", exc_info=True)
    state["errors"] = state.get("errors", []) + [f"{AgentName}: {str(e)}"]
    # Graceful degradation
```

---

## Testing

Each agent has corresponding test files in `tests/agents/`:
- Unit tests for individual methods
- Integration tests with mock services
- End-to-end workflow tests

---

## Technology Stack

### Vector Database
- **Platform**: Pinecone
- **Indexes**: 
  - Internal Rules Index (PINECONE_INTERNAL_INDEX_HOST)
  - External Rules Index (PINECONE_EXTERNAL_INDEX_HOST)
- **Embeddings**: Pinecone integrated embeddings (no separate service needed)
- **Search Method**: Semantic search with metadata filtering

### LLM Provider
- **Provider**: Groq
- **Model**: `openai/gpt-oss-20b`
- **Base URL**: `https://api.groq.com/openai/v1`
- **Use Cases**: 
  - Rule applicability determination
  - Control testing
  - Analyst report generation
  - Pattern reasoning (future)

### Pinecone Search Example
```python
from pinecone import Pinecone

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(host=os.getenv("PINECONE_INTERNAL_INDEX_HOST"))

# Semantic search with integrated embeddings
results = index.search(
    namespace="internal-rules",
    query={
        "inputs": {"text": query_text},
        "top_k": 10
    },
    fields=["text", "rule_id", "jurisdiction", "severity", "effective_date"]
)

# Process results
for match in results.get("result", {}).get("hits", []):
    metadata = match.get("fields", {})
    # Access rule data from metadata
```

### Groq LLM Example (LangChain LCEL)
```python
from langchain_openai import ChatOpenAI
import os

# Configure ChatOpenAI to point at Groq
llm = ChatOpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
    model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
    temperature=0.2,
)

# Use LCEL invoke pattern
response = llm.invoke([
    {"role": "system", "content": "You are a compliance analyst."},
    {"role": "user", "content": "Analyze this transaction for compliance issues..."}
])

# response.content contains the model's reply
result = response.content
```

---

## Future Enhancements

1. **PatternDetector**: Implement graph-based network analysis
2. **BayesianEngine**: Add probabilistic reasoning models
3. **AlertComposer**: Integrate with external ticketing systems
4. **RemediationOrchestrator**: Expand playbook library
5. **All agents**: Add performance metrics and monitoring
6. **Retrieval**: Implement hybrid search (semantic + BM25) if needed
7. **LLM**: Add fallback providers for reliability

---

## Documentation References

- `AGENTIC_AML_WORKFLOW_PLAN.md` - Overall workflow design
- `IMPLEMENTATION_STATUS.md` - Current implementation status
- `TESTING_DOCUMENTATION.md` - Testing guidelines
- `workflows/transaction_workflow.py` - Workflow orchestration
- `services/pinecone_db.py` - Pinecone integration
- `services/llm.py` - Groq LLM service

---

**Last Updated**: November 2025  
**Version**: 1.1  
**Maintainer**: Slenth Development Team
