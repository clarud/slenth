# Agentic AML Monitoring and Document Corroboration — Implementation Plan

## Overview
- Build two interacting agentic workflows that collaborate via explicit message contracts:
  - Part 1: Real-Time AML Monitoring and Alerts (streaming transactions, rules, Bayesian inference)
  - Part 2: Document and Image Corroboration (OCR, NLP validation, image forensics)
- Use `transactions_mock_1000_for_participants.csv` to simulate a real-time stream.
- Use `Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf` as the sample corroboration document.
- Maintain clear separation between internal vs. external docs/databases and version external documents scraped from regulator/monetary sites.

## Agentic Architecture
Agents are autonomous services (or tasks) that exchange typed messages. Decisions emerge from agent interactions, not a single monolith.

Part 1 — Real-Time Monitoring Agents:
- Source Ingestion Agent: Scrapes regulatory/monetary sites, stores external documents, versions them, emits NewRuleDocs messages.
- Rule Synthesis Agent: Parses external circulars, updates rule set/CPT priors, emits RuleUpdates.
- Transaction Stream Agent: Publishes TransactionEvents from the CSV simulator (real-time push), handles ordering/offsets.
- Feature Engineering Agent: Transforms events to Features (per-event and windowed), emits FeatureVectors.
- Sequence Aggregation Agent: Builds transaction episodes (session/window across related transactions), emits EpisodeSummaries.
- Bayesian Inference Agent: Combines Features + EpisodeSummaries + RuleUpdates to produce RiskPosteriors (per event and per episode).
- Alert Orchestrator Agent: Applies thresholds/policies, deduplicates across windows, creates Alerts and opens Cases.
- Remediation Agent: Suggests actions and playbooks; updates AuditLog.
- Audit/Governance Agent: Ensures full lineage, message journaling, and reproducibility.

Part 2 — Document & Image Corroboration Agents:
- Document Intake Agent: Accepts uploads; normalizes to internal format; emits DocReceived.
- OCR Agent: Runs OCR on scans; emits ExtractedText and Regions.
- NLP Validation Agent: Extracts fields (names, dates, addresses, amounts); checks schema/template, consistency, and cross-field validation; emits DocFindings.
- Image Forensics Agent: EXIF checks, error-level analysis, basic tampering heuristics; emits ImageFindings. (Reverse image search stubbed/offline.)
- Cross-Reference Agent: Correlates doc fields with transaction history, client profiles, and external rules; emits CrossRefFindings.
- Document Risk Agent: Aggregates findings to DocRiskScore; stores evidence; notifies Alert Orchestrator.
- Evidence Storekeeper Agent: Manages storage for raw docs, extracted text, embeddings, and versioned external docs.

Integration Agents:
- Coordinator/Scheduler: Orchestrates multi-agent graphs (e.g., LangGraph-style DAG with retries and state).
- API Gateway: Presents a consistent API/UI; brokers commands to agents.

## Tech Stack Recommendations
- Language: Python 3.11
- Orchestration/Agents: LangGraph or simple asyncio task graph; alternative: Celery for queues. For hackathon speed, start with in-process LangGraph-like coordinator.
- API/UI: FastAPI for REST and WebSocket; Streamlit for quick demo dashboard.
- Streaming/Queue: In-memory channel for hackathon; upgrade path: Redis Streams or Kafka.
- Databases:
  - Internal DB (transactions, alerts, cases, audit): SQLite (hackathon) → PostgreSQL (prod)
  - External DB (scraped docs, versions, sources): separate SQLite file (hackathon) → dedicated PostgreSQL database (prod)
- OCR/PDF: `pytesseract` + Tesseract, `PyMuPDF` (fitz) or `pdfminer.six` for PDFs
- NLP: `regex`, `dateparser`, optional spaCy small model (if allowed offline); rule-based first
- Image Forensics: `Pillow` (error level analysis), `exifread`
- Bayesian Networks: `pgmpy` or `pomegranate`
- Feature Engineering: `pandas`, `numpy`, `scikit-learn` utilities (scalers, encoders)
- Embeddings/Similarity (optional offline): `sentence-transformers` local model or lightweight TF-IDF; FAISS index if embeddings used
- Packaging/Dev: `poetry` or `pip-tools`, `pytest`
- Containerization: Docker + docker-compose (optional for demo)

## Data and Storage Design
Directory-backed object store for raw docs and derived artifacts; relational DBs for metadata and audit.

Internal DB (SQLite `internal.db`):
- `transactions` (id, timestamp, account_id, counterparty_id, amount, currency, country, channel, raw, hash)
- `features` (transaction_id, feature_key, feature_value, window_id)
- `episodes` (episode_id, account_id, start_ts, end_ts, num_txn, stats_json)
- `alerts` (alert_id, subject_type, subject_id, severity, reason, risk_score, created_at, state)
- `cases` (case_id, alert_id, owner, status, created_at, updated_at)
- `audit_logs` (id, actor, action, payload, created_at)
- `bn_models` (id, name, version, spec_json, cpt_json, created_at)

External DB (SQLite `external.db`):
- `sources` (source_id, name, base_url, jurisdiction)
- `documents` (doc_id, source_id, doc_type, url, current_version_id)
- `document_versions` (version_id, doc_id, fetched_at, hash, path, metadata_json)
- `extracted_fields` (version_id, field_key, field_value, confidence)
- `external_rules` (rule_id, version_id, rule_type, rule_json, active_from, active_to)

Object Store (filesystem):
- `data/raw_docs/` raw uploads; `data/external_docs/` scraped; `data/ocr/` text/regions; `data/embeddings/` FAISS or TF-IDF artifacts

## Message Contracts (Pydantic models)
- `TransactionEvent`, `FeatureVector`, `EpisodeSummary`
- `NewRuleDocs`, `RuleUpdate`, `RiskPosterior`
- `Alert`, `CaseUpdate`, `AuditEntry`
- `DocReceived`, `ExtractedText`, `DocFindings`, `ImageFindings`, `CrossRefFindings`, `DocRiskScore`

## End-to-End Workflows
Part 1 — Real-Time Monitoring
1) Source Ingestion Agent scrapes, stores `document_versions` in External DB, emits `NewRuleDocs`.
2) Rule Synthesis Agent parses into `external_rules` and emits `RuleUpdate` (also updates BN priors).
3) Transaction Stream Agent reads `transactions_mock_1000_for_participants.csv`, publishes `TransactionEvent`s.
4) Feature Engineering Agent creates `FeatureVector`s (per-txn + rolling windows).
5) Sequence Aggregation Agent forms `EpisodeSummary` (sessionization per account/counterparty/time window).
6) Bayesian Inference Agent fuses `FeatureVector`s + `EpisodeSummary` + `RuleUpdate`s into `RiskPosterior` (probabilities for typologies: structuring, layering, circular transfers, sanctions evasion).
7) Alert Orchestrator Agent thresholds, deduplicates, escalates; persists `alerts`, opens `cases`.
8) Remediation Agent suggests actions; Audit/Governance logs all steps.

Part 2 — Document & Image Corroboration
1) Document Intake Agent saves file under `data/raw_docs/`, records in Internal DB, emits `DocReceived`.
2) OCR Agent extracts text/regions; saves under `data/ocr/`, emits `ExtractedText`.
3) NLP Validation Agent extracts key fields (names, addresses, dates, amounts, IDs), validates structure/templates; emits `DocFindings`.
4) Image Forensics Agent performs EXIF + ELA + simple tamper checks; emits `ImageFindings`.
5) Cross-Reference Agent aligns document entities with transaction history and `external_rules`; emits `CrossRefFindings`.
6) Document Risk Agent aggregates to `DocRiskScore`; notifies Alert Orchestrator for unified case management.

Integration
- Cross-link alerts to document findings and vice versa; case views show both event and evidence trails.

## Evaluation of Additional Ideas
1) Sequential processing of transactions: INCLUDED. Implement `Sequence Aggregation Agent` with sliding windows and episode building to detect distributed schemes.
2) Feature engineering/extraction: INCLUDED. Rich feature set feeding BN, thresholds, and rules.
3) Bayesian networks for inference: INCLUDED. `Bayesian Inference Agent` uses BN over typology variables with CPTs updated by rules/data.

## Features and Signals (examples)
- Per-transaction: amount z-score by account, country risk score, channel risk, merchant MCC risk, name/ID screening flags.
- Windowed: velocity (#txns per window), burstiness, structuring indicators (many small → large), round-trip distance (geo/IP), counterparty graph degree.
- Document: field mismatch with KYC, amount/date/address consistency, template conformity, OCR confidence, EXIF anomalies.

## Repository Layout
- `agents/`
  - `part1/` (source_ingestion.py, rule_synthesis.py, transaction_stream.py, features.py, sequence_agg.py, bayes_infer.py, alert_orchestrator.py, remediation.py)
  - `part2/` (document_intake.py, ocr.py, nlp_validate.py, image_forensics.py, cross_reference.py, doc_risk.py, evidence_store.py)
- `pipelines/` (graphs.py for orchestration DAGs; run_part1.py; run_part2.py; run_integrated.py)
- `api/` (main.py FastAPI, routers for alerts, docs, upload; websocket endpoints)
- `data/` (`transactions_mock_1000_for_participants.csv`, `Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf`, `raw_docs/`, `external_docs/`, `ocr/`, `embeddings/`)
- `db/` (schemas.sql, seed/ migrations/; `internal.db`, `external.db` during dev)
- `models/` (bn_spec.json, cpt.json; feature_config.yaml; rules/)
- `configs/` (app.yaml, thresholds.yaml, windows.yaml, sources.yaml)
- `scripts/` (simulate_stream.py, scrape_stub.py, load_rules.py)
- `docs/` (architecture.svg, api.md)
- `tests/` (unit & minimal e2e)

## Step-by-Step Build Plan (Hackathon)
1) Bootstrap repo layout; add configs and DB schema files; wire minimal FastAPI.
2) Implement Transaction Stream Agent reading CSV and publishing in-memory.
3) Implement Feature Engineering Agent with basic per-event + rolling stats; persist to `features`.
4) Implement Sequence Aggregation Agent (sliding window, episode stats) to `episodes`.
5) Implement Bayesian Inference Agent with pgmpy/pomegranate and a small BN; output `RiskPosterior`.
6) Implement Alert Orchestrator with thresholds and dedup; persist `alerts` and link to `cases`.
7) Implement Document Intake + OCR + NLP Validation + Image Forensics; output findings and `DocRiskScore`.
8) Implement Cross-Reference Agent to tie docs to transactions and rules; enrich alerts.
9) Implement Source Ingestion Agent (scrape stub reading offline HTML/PDFs) with versioning in External DB; Rule Synthesis Agent stubs mapping to rules JSON and BN priors.
10) Add Audit/Governance Agent to persist `audit_logs` on every message.
11) Add Streamlit dashboard or minimal FastAPI+HTML views for alerts, cases, documents.
12) Package demo flows (`run_part1.py`, `run_part2.py`, `run_integrated.py`), plus sample notebooks if time.

## Scraping and Versioning Strategy (External Docs)
- Maintain `sources` catalog with base URLs; `scrape_stub.py` loads local snapshots (offline), computes SHA-256 hash, increments `document_versions` when content hash changes.
- Parse to `external_rules` using rule templates (regex + YAML spec) and link `version_id`.
- Store raw files under `data/external_docs/{source}/{doc_id}/{version_id}.pdf` (or .html).

## Bayesian Network Design (Initial)
- Nodes (examples): `HighAmount`, `HighVelocity`, `Structuring`, `RoundTrip`, `SanctionedCounterparty`, `PEPMatch`, `DocMismatch`, `ImageTamper`, `Suspicious`
- Parents: `HighAmount`→`Structuring`, `HighVelocity`→`Structuring`, `DocMismatch`→`Suspicious`, `ImageTamper`→`Suspicious`, `SanctionedCounterparty`→`Suspicious`, `Structuring`→`Suspicious`
- Priors/CPTs: Seed from expert rules; allow online calibration by counting outcomes (Dirichlet priors) for hackathon.

## APIs and Contracts
- REST endpoints: `/alerts`, `/cases`, `/documents`, `/upload`, `/status`
- WebSocket: `/ws/transactions` stream, `/ws/alerts` push notifications
- Pydantic models mirror Message Contracts section.

## Audit and Governance
- Every agent logs input, output, decision rationale, and artifacts paths to `audit_logs`.
- Case view assembles all evidence and provenance for defensibility.

## Demo Instructions (Target)
- `python scripts/simulate_stream.py` to feed `transactions_mock_1000_for_participants.csv` into the pipeline.
- `python pipelines/run_part1.py` to run Part 1 agents end-to-end; view alerts via API/Streamlit.
- `python pipelines/run_part2.py --file data/Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf` for doc pipeline.
- `python pipelines/run_integrated.py` to run both and see cross-references.

## Notes and Limitations
- Reverse image search requires external network; keep as stub with clear TODO.
- Scraping should be stubbed with offline snapshots; versioning remains fully implemented locally.
- For speed, start with in-process message bus; swap to Redis/Kafka if time permits.

## Success Criteria Mapping
- Objective Achievement: End-to-end alerting + doc risk with audit trails.
- Creativity: Agentic interactions, BN-driven decisions, episode-level detection.
- Design: Clean UI slices in Streamlit/FastAPI.
- Presentation: Clear architecture/storyline anchored to agents and auditability.
- Technical Depth: BN, windowed features, doc forensics, versioned external rules.

