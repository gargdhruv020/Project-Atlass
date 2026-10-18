"""
Copilot Query Endpoints
Orchestrates agentic analysis using LangGraph workflow.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.query import QueryRequest, QueryResponse, SourceCitation
from app.schemas.chat import ChatResponse
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
    result: ChatResponse = run_copilot_workflow(
        db=db,
        query=request.query,
        client_id=request.client_id,
        report_id=request.report_id
    )

    citations = [
        SourceCitation(
            report_id=c.report_id,
            title=c.title or c.report_title,
            metric=c.metric,
            period=c.period,
            region=c.region,
            value=c.value,
            source_type=c.source_type
        )
        for c in result.citations
    ]

    return QueryResponse(
        query=request.query,
        client_id=request.client_id,
        answer=result.answer,
        access_granted=not ("do not have access" in result.answer.lower() or "unauthorized" in result.answer.lower()),
        citations=citations,
        metadata={
            "confidence": result.confidence,
            "escalated": result.escalated,
            "derived_values_count": len(result.derived_values),
            "conflicts_count": len(result.conflicts)
        }
    )
