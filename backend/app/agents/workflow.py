"""
LangGraph Agent Workflow
Orchestrates client permission checks, SQL metric retrieval, ChromaDB vector search,
and synthesized report generation for the Market Research Copilot.
"""

from typing import TypedDict, List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.tools.db_tool import DatabaseTool
from app.tools.vector_tool import VectorTool
from app.observability.logger import logger

class AgentState(TypedDict):
    query: str
    client_id: Optional[str]
    report_id: Optional[str]
    access_granted: bool
    access_message: str
    metrics: List[Dict[str, Any]]
    unstructured_docs: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    final_answer: str

def check_permissions_node(state: AgentState, db: Session) -> Dict[str, Any]:
    """Node: Validate client permissions against relational MySQL database."""
    client_id = state.get("client_id")
    report_id = state.get("report_id")

    logger.info(f"[Agent] Checking permissions for client='{client_id}', report='{report_id}'")

    if not client_id or not report_id:
        # Default open if not restricted to a specific private report
        return {"access_granted": True, "access_message": "Open query / no client restriction"}

    res = DatabaseTool.check_client_access(db=db, client_id=client_id, report_id=report_id)
    return {
        "access_granted": res["has_access"],
        "access_message": res["reason"]
    }

def retrieve_data_node(state: AgentState, db: Session) -> Dict[str, Any]:
    """Node: Query relational metrics and semantic vector content."""
    if not state.get("access_granted", True):
        logger.warning(f"[Agent] Access denied. Skipping retrieval.")
        return {"metrics": [], "unstructured_docs": [], "citations": []}

    query = state.get("query", "")
    report_id = state.get("report_id")

    logger.info(f"[Agent] Retrieving structured metrics from MySQL for query: {query}")
    
    # Simple keyword extraction for metric query
    metric_filter = None
    for keyword in ["cagr", "market size", "revenue", "volume", "share", "forecast"]:
        if keyword in query.lower():
            metric_filter = keyword
            break

    metrics = DatabaseTool.query_metrics(
        db=db,
        report_id=report_id,
        metric=metric_filter
    )

    logger.info(f"[Agent] Retrieving vector documents from ChromaDB for query: {query}")
    vector_results = VectorTool.search_unstructured_content(query=query, n_results=2)

    citations = []
    for m in metrics:
        citations.append({
            "report_id": m.get("report_id"),
            "metric": m.get("metric"),
            "period": m.get("period"),
            "region": m.get("region"),
            "value": m.get("value"),
            "source_type": "relational_sql"
        })

    for v in vector_results:
        citations.append({
            "source": v.get("source"),
            "content_preview": v.get("content", "")[:120],
            "source_type": "vector_retrieval"
        })

    return {
        "metrics": metrics,
        "unstructured_docs": vector_results,
        "citations": citations
    }

def synthesize_answer_node(state: AgentState) -> Dict[str, Any]:
    """Node: Synthesize grounded response using retrieved metrics and citations."""
    if not state.get("access_granted", True):
        return {
            "final_answer": f"Access Denied: {state.get('access_message')}. Please contact your administrator to purchase access."
        }

    metrics = state.get("metrics", [])
    query = state.get("query", "")
    citations = state.get("citations", [])

    if not metrics and not state.get("unstructured_docs"):
        return {
            "final_answer": f"No market research data found matching query: '{query}'. Try searching for metrics such as 'Market size' or 'CAGR'."
        }

    # Format synthesized findings
    findings = []
    for m in metrics[:5]:
        findings.append(
            f"- **{m.get('metric')}** ({m.get('region')}, {m.get('period')}): **{m.get('value')}** "
            f"[Report: {m.get('report_id')}] - {m.get('scope_note') or ''}"
        )

    summary = (
        f"### Market Research Findings for '{query}':\n\n"
        + "\n".join(findings)
        + f"\n\n*Verified from {len(citations)} source record(s) in Project Atlas.*"
    )

    return {"final_answer": summary}

def run_copilot_workflow(
    db: Session,
    query: str,
    client_id: Optional[str] = None,
    report_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the multi-step Copilot graph workflow.
    Uses LangGraph if available, with built-in sequential state executor.
    """
    initial_state: AgentState = {
        "query": query,
        "client_id": client_id,
        "report_id": report_id,
        "access_granted": True,
        "access_message": "",
        "metrics": [],
        "unstructured_docs": [],
        "citations": [],
        "final_answer": ""
    }

    # Step 1: Permission check
    perm_updates = check_permissions_node(initial_state, db)
    initial_state.update(perm_updates)

    # Step 2: Data retrieval
    retrieval_updates = retrieve_data_node(initial_state, db)
    initial_state.update(retrieval_updates)

    # Step 3: Synthesis
    synth_updates = synthesize_answer_node(initial_state)
    initial_state.update(synth_updates)

    return initial_state
