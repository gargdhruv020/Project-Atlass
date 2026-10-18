# Project Atlas &mdash; System Architecture

## 1. Overview

**Project Atlas** is an AI-powered Market Research Report Copilot designed to provide grounded, citation-backed answers to complex market intelligence questions while enforcing client purchase permissions.

The system combines:
1. **Relational MySQL Database** for structured report metadata, granular market metrics (market size, CAGR, forecasts), and client subscription access control.
2. **Local ChromaDB Vector Store** for persistent semantic search over narrative report text and qualitative insights.
3. **LangGraph Agent Workflow** for orchestrating permission validation, multi-source retrieval (SQL + Vector), and grounded answer synthesis.
4. **FastAPI Backend** exposing RESTful endpoints for the Copilot API, diagnostics, reports, and client access checks.
5. **CodeIgniter 3 Portal** providing a legacy PHP web interface for client account and subscription management.
6. **Docker Compose** containerizing the backend, PHP portal, and MySQL services for unified local development and deployment.

---

## 2. Component Architecture

```mermaid
flowchart TD
    Client["Client / User / PHP Portal"] -->|HTTP / REST| API["FastAPI Gateway (/api/v1)"]
    
    subgraph Backend ["FastAPI Backend (Python 3.11+)"]
        API --> Endpoints["Endpoints: /health, /reports, /clients, /copilot/query"]
        Endpoints --> LG["LangGraph Agent Workflow"]
        
        subgraph CopilotAgent ["LangGraph Orchestrator"]
            PNode["1. Permission Check Node"]
            RNode["2. Dual Retrieval Node"]
            SNode["3. Synthesis Node"]
            PNode --> RNode --> SNode
        end
        
        LG --> Tools["Agent Tools"]
        Tools --> DBTool["SQL Database Tool"]
        Tools --> VecTool["Chroma Vector Tool"]
    end
    
    subgraph DataStorage ["Data & Storage Layer"]
        DBTool -->|SQL Queries (Read-Only)| MySQL[("MySQL 8.0 ('project_atlas')\n- clients\n- reports\n- market_metrics")]
        VecTool -->|Vector Search| Chroma[("Local ChromaDB ('chroma_data/')\n- Semantic Report Chunks")]
    end
    
    subgraph LegacyPortal ["Legacy Web Layer"]
        PHPPortal["CodeIgniter 3 Portal (php-portal/)\nApache + PHP 7.4"] -->|Direct Query| MySQL
        PHPPortal -.->|API Requests| API
    end
```

---

## 3. Directory Layout & Module Responsibilities

| Directory | Purpose |
| :--- | :--- |
| `backend/app/api/` | FastAPI API routes and versioned routers (`/api/v1`). |
| `backend/app/core/` | Global configuration and environment settings (`Settings`). |
| `backend/app/db/` | Database engine, session factories (`SessionLocal`), and FastAPI dependencies. |
| `backend/app/models/` | SQLAlchemy ORM models matching existing MySQL tables (`clients`, `reports`, `market_metrics`). |
| `backend/app/schemas/` | Pydantic request/response schemas for data validation and API documentation. |
| `backend/app/services/` | Business logic for reports, market metrics, and client permissions. |
| `backend/app/ingestion/` | Document parsing, text chunking, and preparation for embedding. |
| `backend/app/retrieval/` | ChromaDB vector store client and persistence management. |
| `backend/app/agents/` | LangGraph multi-step workflow for the Market Research Copilot. |
| `backend/app/tools/` | Reusable tools providing SQL querying and vector search for the agent. |
| `backend/app/security/` | Client authorization, API key validation, and sensitive data masking. |
| `backend/app/observability/` | Structured logging, diagnostic tracing, and health checks. |
| `backend/tests/` | Automated test suite separated from production code. |
| `scripts/` | Standalone operational and inspection utilities (`inspect_database.py`). |
| `documents/` | Source PDF, Markdown, and text market research reports. |
| `chroma_data/` | Local persistent ChromaDB index files (excluded from Git). |
| `php-portal/` | CodeIgniter 3 legacy client portal. |
| `docker/` | Dockerfiles for backend and PHP portal. |
| `docs/` | System architecture, schema documentation, and inspection logs. |
| `evaluation/` | Benchmark query sets and evaluation test cases. |

---

## 4. Security & Isolation Principles

- **No Hardcoded Secrets**: All credentials and connection strings are managed via `.env` and loaded through `app/core/config.py`.
- **Git Exclusions**: Local databases, vector index caches (`chroma_data/*`), temporary documents, and `.env` files are ignored in `.gitignore`.
- **Data Protection**: Client contact emails and sensitive authentication credentials are automatically masked before being surfaced in API responses or logs.
- **Read-Only Guarantees**: Introspection and Copilot retrieval operations execute read-only queries, preserving database integrity.

---

## 5. LangGraph Agent Workflow Architecture

Project Atlas utilizes **LangGraph** (`langgraph.graph.StateGraph`) to orchestrate a strongly typed, deterministic agent workflow. The agent coordinates 8 specialized nodes with explicit state transitions, conditional branching, failure handling, and multi-layer entitlement security.

### 5.1 Workflow State Diagram

```mermaid
flowchart TD
    Start([User Request]) --> RouterNode["1. Router Node\n(Intent Classification)"]
    
    RouterNode -->|factual / comparison / calc / sql| EntitlementsNode["2. Entitlement Checker Node\n(Authoritative MySQL Validation)"]
    RouterNode -->|unsafe_unauthorized / out_of_scope| EscalationNode["7. Escalation Handler Node\n(MySQL Ticket + Safe Notice)"]
    
    EntitlementsNode -->|Access Authorized\nIntent == sql_aggregate| SQLToolNode["4. Read-Only SQL Tool Node\n(Restricted Parameterized Aggregates)"]
    EntitlementsNode -->|Access Authorized\nFactual / Comparison / Calc| RetrieverNode["3. Retriever Node\n(ChromaDB + MySQL with Independent Gate)"]
    EntitlementsNode -->|Access Denied / Unauthenticated| EscalationNode
    
    RetrieverNode -->|Intent == calculation_projection| CalculatorNode["5. Calculator Node\n(Deterministic CAGR & Regional Share)"]
    RetrieverNode -->|Factual / Comparison| CriticNode["6. Critic / Fact-Checker Node\n(Conflict Detection, Grounding, Citations)"]
    
    SQLToolNode --> CriticNode
    CalculatorNode --> CriticNode
    
    CriticNode -->|Grounded Evidence Available| WriterNode["8. Writer Node\n(Grounded ChatResponse Synthesis)"]
    CriticNode -->|Missing Evidence / Low Confidence / Explicit Escalation| EscalationNode
    
    EscalationNode --> WriterNode
    WriterNode --> EndNode([Structured API Response])
```

### 5.2 The 8 Workflow Components

| Node | Component | Responsibility & Safety Measures |
| :--- | :--- | :--- |
| `router` | **Router** | Classifies query into 1 of 6 intents: `factual_lookup`, `comparison`, `calculation_projection`, `sql_aggregate`, `out_of_scope`, `unsafe_unauthorized`. Extracts target report IDs. |
| `entitlement_checker` | **Entitlement Checker** | Queries MySQL `clients` and `reports`. Verifies client authentication and computes permitted report scope. Pre-checks target report permissions before retrieval. |
| `retriever` | **Retriever** | Retrieves ChromaDB chunks and MySQL structured metrics. **Hard Python Gate**: Re-verifies every chunk against MySQL permissions, purging unauthorized chunks before LLM context. |
| `read_only_sql` | **Read-Only SQL Tool** | Executes safe aggregate computations (e.g. `AVG(CAGR)`, `COUNT`, `MAX`) strictly over permitted reports. Rejects all mutation/DDL keywords (`DROP`, `INSERT`, `UPDATE`, `DELETE`). |
| `calculator` | **Calculator** | Deterministic mathematical calculations: CAGR future projections ($V_{\text{future}} = V_{\text{base}} \times (1 + r)^{\Delta t}$) and regional sizing without floating-point estimation. |
| `critic` | **Critic / Fact-Checker** | Analyzes methodological divergences across reports (e.g. R-101 vs R-102 scopes), validates citation grounding, flags ungrounded claims, and calibrates confidence score. |
| `escalation` | **Escalation Handler** | Creates an analyst ticket in MySQL `escalations` table for access denials, ungrounded inquiries, or unsafe requests **without logging protected report text**. |
| `writer` | **Writer** | Packages final grounded answer, citations, derived formulas, conflict explanations, and safe catalog upgrade offers into the standard Pydantic `ChatResponse`. |

### 5.3 Failure & Loop Protection
- **No Backward Loops**: The state transition graph is strictly forward-directed, mathematically preventing infinite loops.
- **Tool Fallbacks**: If external LLM or database queries encounter timeouts or disconnects, nodes fail gracefully into deterministic grounded synthesis.
- **Untrusted Document Boundary**: Retrieved text is isolated within `<untrusted_document_evidence>` XML tags with strict system directives ignoring embedded commands.

