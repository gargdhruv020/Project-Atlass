# One-Page Note — What I Would Do With One More Week

**Project Atlas — Market Research Report Copilot**  
*Author / Candidate Note for Technical Reviewers*

---

## 1. Executive Summary & Current State

Project Atlas currently achieves **100% compliance across all 10 mandatory evaluation scenarios**, passes **132/132 unit and integration tests**, and provides a containerized dual-tier architecture (FastAPI Python backend + CodeIgniter 3 PHP web portal) with strict RBAC entitlement enforcement, deterministic CAGR calculations, and automatic analyst escalation.

With **one additional engineering week**, I would advance the system from a verified technical evaluation prototype into a horizontally scalable, production-grade enterprise platform by focusing on five strategic pillars:

---

## 2. Seven-Day Engineering Plan

### Day 1–2: Automated Multi-Format Ingestion & Relational Table Extraction
* **Current Limitation**: Structured numerical metrics (`market_metrics`) were pre-seeded in MySQL for Reports R-101 and R-102. Report R-103 exists as narrative markdown and was ingested into ChromaDB vector storage, requiring vector search fallback for R-103 CAGR calculations.
* **With One More Week**:
  * Build an automated tabular parser in `ReportIngestionService` supporting HTML `<table>`, Markdown pipes, and PDF table extractors (using `pdfplumber` or `camelot-py`).
  * Automatically parse, validate, and write extracted metrics into MySQL `market_metrics` at ingestion time so that all reports enjoy first-class relational SQL querying and CAGR derivations.

### Day 2–3: Spatio-Temporal Disambiguation & Semantic Drift Guardrails
* **Current Limitation**: When a query specifies an unrepresented historical year (e.g., 1995) or an unpopulated geographic region (e.g., Antarctica), semantic search can drift toward the closest available global 2024 metric.
* **With One More Week**:
  * Implement an explicit Named Entity & Temporal Extractor in `critic_node` to detect years ($< 2020$ or $> 2035$) and geographic entities.
  * Cross-reference extracted query entities against the retrieved document metadata. If requested temporal or regional boundaries are missing, immediately downgrade confidence to $< 0.20$ and trigger a human analyst escalation ticket stating: *"Requested geographic region or historical period is not covered in the market database."*

### Day 3–4: Interactive Conversational Clarification Loop (Multi-Turn)
* **Current Limitation**: When a user asks for a projection without specifying a target year (e.g., *"Calculate future market projection from R-101"*), the calculator flags `target_year_missing` and falls back to baseline summaries rather than asking the user.
* **With One More Week**:
  * Introduce an `ask_clarification` node in the LangGraph state graph.
  * Respond conversationally: *"To calculate this projection, what target horizon would you like to model (e.g., 2028, 2030, or 2035)?"*
  * Persist pending state in MySQL `conversations` session so the user's next message immediately resumes the deterministic CAGR formula.

### Day 4–5: Hybrid Sparse-Dense Retrieval & Cross-Encoder Reranking
* **Current Limitation**: Dense semantic vector embeddings (`all-MiniLM-L6-v2`) excel at broad conceptual search but can miss exact keyword matches for niche technical abbreviations or report section codes.
* **With One More Week**:
  * Implement a hybrid retrieval pipeline pairing BM25 (sparse keyword search) with ChromaDB (dense semantic search).
  * Merge results using **Reciprocal Rank Fusion (RRF)**:
    $$RRF(d) = \sum_{m \in M} \frac{1}{60 + r_m(d)}$$
  * Add a local Cross-Encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to score the top-10 chunks before LLM synthesis, significantly boosting retrieval precision.

### Day 5–6: Production Distributed Caching, Rate Limiting & Streaming Responses
* **Current Limitation**: Response caching is stored in-memory in `chat_service.py`, and responses are delivered as complete JSON payloads upon completion.
* **With One More Week**:
  * Replace the local memory dictionary with an external Redis instance to support horizontally scaled FastAPI backend worker replicas.
  * Add token-bucket rate limiting (e.g., 60 requests/minute per client).
  * Implement Server-Sent Events (SSE) streaming on `/chat/stream` for real-time word-by-word token generation in the CodeIgniter 3 chat view.

### Day 6–7: CI/CD Pipeline & Relational Schema Normalization
* **Current Limitation**: The client-report entitlement is stored as a comma-separated string (`clients.purchased_reports`), and tests are run locally via pytest.
* **With One More Week**:
  * Establish a GitHub Actions CI/CD pipeline (`.github/workflows/test.yml`) running the 132 pytest suite, PHPUnit tests, Docker builds, and evaluation benchmarks on every push.
  * Execute migration script `02-normalize-entitlements.sql` to normalize `clients.purchased_reports` into a proper relational join table (`client_report_entitlements`) with foreign key constraints.

---

## 3. Summary Impact Table

| Area | Prototype State | Production State (With +1 Week) |
| :--- | :--- | :--- |
| **Document Ingestion** | Markdown / ChromaDB text chunking | Automated HTML/Markdown table parsing into relational MySQL rows |
| **Query Disambiguation** | Single-turn fallback to baseline | Multi-turn conversational clarification loop in LangGraph |
| **Search Precision** | Dense embeddings (384-d MiniLM) | Hybrid BM25 + Dense ChromaDB with Reciprocal Rank Fusion & Reranking |
| **Guardrails** | Input regex & keyword safety filters | Entity-aware spatio-temporal boundary validation in Critic node |
| **Scalability** | In-memory SHA-256 caching | Distributed Redis cache, token rate-limiting, and SSE streaming |
| **Infrastructure** | Local Docker Compose | Automated GitHub Actions CI/CD with linting, security scans, and tests |

---
*For the complete detailed technical analysis and architecture diagrams, see [`docs/one-more-week.md`](docs/one-more-week.md).*
