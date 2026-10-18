# Project Atlas &mdash; Market Research Report Copilot

Project Atlas is an enterprise-grade AI-powered Market Research Report Copilot that provides evidence-grounded answers to market intelligence inquiries while strictly respecting client purchase entitlements.

---

## 1. System Overview

- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/) providing high-performance RESTful endpoints, strict Pydantic v2 data validation, and health diagnostics.
- **Agent Orchestrator**: [LangGraph](https://github.com/langchain-ai/langgraph) multi-step state graph coordinating permissions, SQL metric retrieval, and semantic vector search.
- **Relational Storage**: [MySQL 8.0](https://www.mysql.com/) storing structured application data (`clients`, `reports`, `market_metrics`).
- **Vector Storage**: [ChromaDB](https://www.trychroma.com/) providing local persistent vector embeddings of report narratives.
- **Security & Authorization**: Header-based API key validation (`X-API-Key` or `Authorization: Bearer <key>`) and client entitlement enforcement.
- **Legacy Client Portal**: [CodeIgniter 3](https://codeigniter.com/) legacy PHP web interface.
- **Containerization**: [Docker Compose](https://docs.docker.com/compose/) defining services for unified execution.

Detailed architecture description is available at [`docs/architecture.md`](docs/architecture.md).  
Database inspection results are available at [`docs/database-inspection.md`](docs/database-inspection.md).  
Schema gap analysis & proposed migrations are at [`docs/schema-gap-analysis.md`](docs/schema-gap-analysis.md).

---

## 2. API Endpoints

All primary endpoints are exposed directly at the root level and under `/api/v1/`:

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Application health and dependency diagnostics (MySQL, ChromaDB, LangGraph) | No |
| `POST` | `/chat` | Submit research questions to the Copilot (returns answer, citations, confidence, conflicts, derived values, escalation) | Yes (`X-API-Key`) |
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

Ensure your `.env` contains:
```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=project_atlas
API_KEY=atlas-dev-key-2026
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

### 3.3 Run the FastAPI Backend
```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

---

## 4. OpenAPI Documentation

Once the server is running, interactive OpenAPI documentation is available at:
* **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **OpenAPI JSON Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 5. Example API Requests

### 5.1 Health Check (`GET /health`)
```bash
curl -X GET http://127.0.0.1:8000/health
```

### 5.2 Research Copilot Query (`POST /chat`)
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: atlas-dev-key-2026" \
  -d '{
    "client_id": "C-01",
    "query": "What is the CAGR for Smart Water Meters according to report R-101?",
    "report_id": "R-101"
  }'
```

**Sample Response**:
```json
{
  "answer": "### Research Findings for 'What is the CAGR for Smart Water Meters according to report R-101?':\n- **CAGR** (Global, 2025-2030): **11.2%** *(Source: Report R-101)*",
  "citations": [
    {
      "report_id": "R-101",
      "metric": "CAGR",
      "period": "2025-2030",
      "region": "Global",
      "value": "11.2%",
      "source_type": "relational_sql",
      "text_snippet": "Forecast period stated as 2025-2030"
    }
  ],
  "confidence": 0.95,
  "conflicts": [],
  "derived_values": {},
  "escalated": false,
  "client_id": "C-01",
  "conversation_id": null,
  "escalation_ticket": null
}
```

### 5.3 Report Ingestion (`POST /ingest`)
```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: atlas-dev-key-2026" \
  -d '{
    "report_id": "R-101",
    "title": "Global Smart Water Meter Market 2025",
    "content": "Smart water metering deployments are expanding rapidly across North America and Europe driven by utility digitization initiatives."
  }'
```

### 5.4 List Escalations (`GET /escalations`)
```bash
curl -X GET "http://127.0.0.1:8000/escalations?client_id=C-02" \
  -H "X-API-Key: atlas-dev-key-2026"
```

---

## 6. Running Tests

Run the full automated test suite (20 tests covering validation, authentication, authorization, dual retrieval, and health diagnostics):
```bash
pytest backend/tests -v
```