# Project Atlas &mdash; Market Research Report Copilot

Project Atlas is an AI-powered Market Research Report Copilot that provides evidence-grounded answers to market research inquiries while strictly respecting client purchase permissions.

---

## Architecture Overview

- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/) providing RESTful endpoints, OpenAPI documentation, and health diagnostics.
- **Agent Orchestrator**: [LangGraph](https://github.com/langchain-ai/langgraph) managing the multi-step retrieval and synthesis workflow.
- **Relational Storage**: [MySQL 8.0](https://www.mysql.com/) storing structured application data (`clients`, `reports`, `market_metrics`).
- **Vector Storage**: [ChromaDB](https://www.trychroma.com/) storing local persistent vector embeddings of unstructured report narratives.
- **Legacy Client Portal**: [CodeIgniter 3](https://codeigniter.com/) legacy PHP web interface.
- **Containerization**: [Docker Compose](https://docs.docker.com/compose/) defining services for unified execution.

Detailed architecture description is available at [`docs/architecture.md`](docs/architecture.md).
Database inspection results are available at [`docs/database-inspection.md`](docs/database-inspection.md).

---

## Project Structure

```text
Project-Atlass/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI versioned routers (/api/v1)
│   │   ├── core/            # Configuration and environment settings
│   │   ├── db/              # SQLAlchemy session and engine management
│   │   ├── models/          # ORM models (Client, Report, MarketMetric)
│   │   ├── schemas/         # Pydantic request and response schemas
│   │   ├── services/        # Business logic & permission verification
│   │   ├── ingestion/       # Document loaders and text chunkers
│   │   ├── retrieval/       # ChromaDB vector store client
│   │   ├── agents/          # LangGraph agent workflow
│   │   ├── tools/           # SQL and Vector retrieval tools
│   │   ├── security/        # Access control and data masking
│   │   ├── observability/   # Structured logging and telemetry
│   │   └── main.py          # FastAPI application entry point
│   ├── tests/               # Pytest automated test suite
│   └── requirements.txt     # Backend Python dependencies
├── scripts/
│   └── inspect_database.py  # Read-only MySQL introspection script
├── documents/               # Source research reports (PDF, MD, TXT)
│   └── sample_reports/
├── chroma_data/             # Local ChromaDB persistent vector storage
├── php-portal/              # CodeIgniter 3 legacy client portal
├── docker/                  # Dockerfiles for backend and PHP portal
├── docs/                    # Architecture and database documentation
├── evaluation/              # Benchmark prompts and evaluation cases
├── .env.example             # Placeholder environment template
├── .gitignore               # Excludes secrets, venv, and vector cache
├── docker-compose.yml       # Multi-container orchestration
└── README.md
```

---

## Quickstart

### 1. Setup Environment
```bash
# Clone the repository
git clone https://github.com/gargdhruv020/Project-Atlass.git
cd Project-Atlass

# Copy environment template and configure MySQL credentials
cp .env.example .env

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Run Database Inspection
```bash
python scripts/inspect_database.py
```

### 3. Run Backend Locally
```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
Interactive API docs will be accessible at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 4. Run with Docker Compose
```bash
docker-compose up --build
```
- FastAPI Backend: `http://localhost:8000`
- CodeIgniter 3 Portal: `http://localhost:8080`
- MySQL Server: `localhost:3306`

---

## Testing
Run the automated test suite:
```bash
pytest backend/tests
```