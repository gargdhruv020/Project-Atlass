"""
Copilot Query Endpoints
Orchestrates agentic analysis using LangGraph workflow.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.query import QueryRequest, QueryResponse, SourceCitation
from app.agents.workflow import run_copilot_workflow

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])

@router.post("/query", response_model=QueryResponse)
def execute_query(request: QueryRequest, db: Session = Depends(get_db)):
    """
    Execute AI Market Research Copilot query through the agent workflow:
    1. Validates client access against MySQL.
    2. Retrieves structured metrics from MySQL and semantic chunks from ChromaDB.
    3. Synthesizes an evidence-grounded response with source citations.
    """
    result = run_copilot_workflow(
        db=db,
        query=request.query,
        client_id=request.client_id,
        report_id=request.report_id
    )

    citations = [
        SourceCitation(
            report_id=c.get("report_id"),
            title=c.get("title"),
            metric=c.get("metric"),
            period=c.get("period"),
            region=c.get("region"),
            value=c.get("value"),
            source_type=c.get("source_type", "relational_sql")
        )
        for c in result.get("citations", [])
    ]

    return QueryResponse(
        query=request.query,
        client_id=request.client_id,
        answer=result.get("final_answer", ""),
        access_granted=result.get("access_granted", True),
        citations=citations,
        metadata={
            "metrics_count": len(result.get("metrics", [])),
            "vector_chunks_count": len(result.get("unstructured_docs", []))
        }
    )
