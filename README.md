# Project Atlas &mdash; Market Research Report Copilot

Project Atlas is an enterprise-grade AI-powered Market Research Report Copilot that provides evidence-grounded answers to market intelligence inquiries while strictly respecting client purchase entitlements.

---

## 1. System Overview

- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/) providing high-performance RESTful endpoints, strict Pydantic v2 data validation, request timeout middleware, and live health diagnostics.
- **Agent Orchestrator**: [LangGraph](https://github.com/langchain-ai/langgraph) 8-node state graph coordinating intent classification, permissions, SQL metric retrieval, semantic vector search, deterministic calculations, critique, escalation, and evidence synthesis.
- **Relational Storage**: [MySQL 8.0](https://www.mysql.com/) storing structured application data (`clients`, `reports`, `market_metrics`, `escalation_tickets`).
- **Vector Storage**: [ChromaDB](https://www.trychroma.com/) providing local persistent vector embeddings of report narratives (exclusively local, zero Pinecone/cloud lock-in).
- **Embeddings**: [Hugging Face](https://huggingface.co/) `sentence-transformers/all-MiniLM-L6-v2` via local ONNX runtime with optional Ollama embedding integration.
- **Deterministic Calculator**: Pure Python CAGR projection engine ($FV = BV \times (1 + CAGR)^n$) and regional share derivation with forecast window guardrails.
- **Citation & Conflict Validator**: Strict attribution of factual claims to authentic report metadata; explicit scope conflict detection preventing illegal averaging.
- **Analyst Escalation Service**: MySQL-backed human escalation workflow with automated ticket generation, status tracking, and duplicate suppression.
- **Security & Authorization**: Header-based API key validation (`X-API-Key` or `Authorization: Bearer <key>`) and strict entitlement enforcement preventing unauthorized report data leaks.

Additional documentation:
* System Integration Architecture: [`docs/system-integration.md`](docs/system-integration.md)
* CodeIgniter 3 PHP Portal Integration: [`docs/php-portal-integration.md`](docs/php-portal-integration.md)
* Architecture Overview: [`docs/architecture.md`](docs/architecture.md)
* Analyst Escalation Workflow: [`docs/analyst-escalation-workflow.md`](docs/analyst-escalation-workflow.md)
* Entitlement Authorization Flow: [`docs/entitlement-authorization-flow.md`](docs/entitlement-authorization-flow.md)
* Vector Database Integration: [`docs/vector-database-integration.md`](docs/vector-database-integration.md)
* RAG Pipeline Architecture: [`docs/rag-pipeline-architecture.md`](docs/rag-pipeline-architecture.md)
* Database Inspection: [`docs/database-inspection.md`](docs/database-inspection.md)
* Schema Gap Analysis: [`docs/schema-gap-analysis.md`](docs/schema-gap-analysis.md)

---

## 2. API Endpoints

All primary endpoints are exposed directly at the root level and under `/api/v1/`:

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Live diagnostic reporting for all 5 subsystems (`mysql`, `chromadb`, `embeddings`, `llm`, `langgraph`) | No |
| `POST` | `/chat` | Submit research questions to the Copilot (returns `answer`, `citations`, `confidence`, `conflicts`, `derived_values`, `escalated`) | Yes (`X-API-Key`) |
| `POST` | `/ingest` | Chunk and ingest report text or documents into local persistent ChromaDB | Yes (`X-API-Key`) |
| `GET` | `/escalations` | List analyst escalation tickets (supports `client_id` and `status` filters) | Yes (`X-API-Key`) |
| `GET` | `/api/v1/reports` | List all market research reports and associated metrics | No |
| `GET` | `/api/v1/clients/{id}/access-check` | Verify if a specific client can access a target report | No |

---

## 3. Local Quickstart

### 3.1 Clone & Environment Setup
```bash
git clone https://github.com/gargdhruv020/Project-Atlass.git
cd Project-Atlass

# Copy environment template
cp .env.example .env
```

Ensure your `.env` contains valid credentials:
```ini
# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DEBUG=false
REQUEST_TIMEOUT_SECONDS=30
MAX_REQUEST_SIZE_BYTES=10000000

# Security & API Key
API_KEY=atlas-dev-key-2026
SECRET_KEY=atlas-insecure-secret-key-change-in-production

# MySQL Database Configuration
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=project_atlas

# Vector Storage (ChromaDB Local Persistence Exclusively)
CHROMA_PERSIST_DIRECTORY=chroma_data
CHROMA_COLLECTION_NAME=market_reports

# Embeddings (Hugging Face / Ollama)
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# LLM Generation Model & API
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_API_BASE=http://localhost:11434

# RAG & Escalation Parameters
RAG_SIMILARITY_THRESHOLD=0.60
RAG_TOP_K=4
ESCALATION_CONFIDENCE_THRESHOLD=0.70
```

### 3.2 Install Dependencies
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r backend/requirements.txt
```

### 3.3 Exact Startup Commands

#### 1. Start the FastAPI Backend Server:
```bash
# Windows PowerShell / CMD:
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload

# Linux / macOS:
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

#### 2. Start the CodeIgniter 3 Legacy PHP Client Portal:
```bash
# Local PHP built-in server (accessible at http://127.0.0.1:8080):
php -S 127.0.0.1:8080 -t php-portal

# Or launch all services via Docker Compose:
docker-compose up --build
```

---

## 4. Exact Test Execution Commands

To execute the automated test suites:

```bash
# Run the complete test suite (105 tests across 11 test modules):
.venv\Scripts\pytest.exe backend/tests -v

# Run the end-to-end integration test suite specifically:
.venv\Scripts\pytest.exe backend/tests/test_application_integration.py -v

# Run health diagnostics test:
.venv\Scripts\pytest.exe backend/tests/test_health.py -v

# Run escalation workflow tests:
.venv\Scripts\pytest.exe backend/tests/test_escalation_workflow.py -v

# Run vector store tests:
.venv\Scripts\pytest.exe backend/tests/test_vector_store.py -v
```

---

## 5. OpenAPI Documentation

Once the server is running, interactive OpenAPI documentation is available at:
* **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **OpenAPI JSON Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 6. Example API Requests

### 6.1 Health Check (`GET /health`)
```bash
curl -X GET http://127.0.0.1:8000/health
```

**Sample Response**:
```json
{
  "status": "healthy",
  "project": "Project Atlas",
  "version": "1.0.0",
  "dependencies": {
    "mysql": {
      "status": "connected",
      "database": "project_atlas",
      "version": "8.0.41",
      "host": "127.0.0.1:3306"
    },
    "chromadb": {
      "status": "available",
      "collection": "market_reports",
      "total_vectors": 12,
      "persist_directory": "C:\\Project-Atlass\\chroma_data"
    },
    "embeddings": {
      "status": "ready",
      "provider": "huggingface",
      "model": "sentence-transformers/all-MiniLM-L6-v2",
      "active_mode": "huggingface-local"
    },
    "llm": {
      "status": "reachable",
      "provider": "ollama",
      "model": "llama3.2",
      "fallback_active": false
    },
    "langgraph": {
      "status": "ready",
      "workflow": "copilot_agent_graph",
      "nodes": [
        "router",
        "entitlement_checker",
        "retriever",
        "read_only_sql",
        "calculator",
        "critic",
        "escalation",
        "writer"
      ]
    }
  }
}
```

### 6.2 Research Copilot Query (`POST /chat`)
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: atlas-dev-key-2026" \
  -d '{
    "client_id": "C-01",
    "query": "What is the 2024 global smart water meter market size in R-101 and what is the projected size for 2026 using its 11.2% CAGR?"
  }'
```

**Sample Response**:
```json
{
  "answer": "### Research Findings:\n- **Market Size (2024)**: **4.21 USD Billion** (Includes hardware, software and services; Source: Report R-101)\n- **Projected Market Size (2026)**: **5.21 USD Billion** [Derived Value]\n  - Calculation: $4.21 × (1 + 0.112)^2 = 5.21 USD Billion",
  "citations": [
    {
      "report_id": "R-101",
      "title": "Global Smart Water Meter Market 2025",
      "metric": "Market Size",
      "period": "2024",
      "region": "Global",
      "value": "4.21 USD Billion",
      "page": 4,
      "source_type": "relational_sql",
      "text_snippet": "Global smart water meter market reached $4.21B in 2024"
    }
  ],
  "confidence": 0.95,
  "conflicts": [],
  "derived_values": {
    "projected_market_size_R-101_2026": "5.21 USD Billion",
    "projected_market_size_R-101_2026_formula": "4.21 × (1 + 0.1120)^2"
  },
  "escalated": false,
  "client_id": "C-01",
  "conversation_id": null,
  "escalation_ticket": null
}
```

### 6.3 Report Ingestion (`POST /ingest`)
```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: atlas-dev-key-2026" \
  -d '{
    "report_id": "R-104",
    "title": "Industrial IoT Water Sensing Report 2025",
    "content": "# Industrial IoT Water Sensing Report 2025\nIndustrial smart flow sensors grew 14.5% year-over-year in North America."
  }'
```

### 6.4 List Escalations (`GET /escalations`)
```bash
curl -X GET "http://127.0.0.1:8000/escalations?client_id=C-01&status=open" \
  -H "X-API-Key: atlas-dev-key-2026"
```