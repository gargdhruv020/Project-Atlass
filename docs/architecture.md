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
