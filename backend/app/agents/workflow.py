"""
Project Atlas LangGraph Agent Workflow
Orchestrates:
1. Router: Intent classification (factual, comparison, calculation, sql_aggregate, out_of_scope, unsafe).
2. Entitlement Checker: Authoritative MySQL client permission validation.
3. Retriever: ChromaDB vector search + MySQL structured metric retrieval with strict hard verification.
4. Read-Only SQL Tool: Safe parameterized aggregations over permitted data.
5. Calculator: Deterministic CAGR future projections and regional share sizing.
6. Critic / Fact-Checker: Grounding audit, citation validation, conflict analysis, and confidence scoring.
7. Escalation Handler: Creation of analyst escalation ticket in MySQL without leaking protected data.
8. Writer: Synthesis of grounded structured ChatResponse.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END

from app.agents.state import AgentGraphState
from app.agents.nodes import (
    router_node,
    entitlement_checker_node,
    retriever_node,
    read_only_sql_node,
    calculator_node,
    critic_node,
    escalation_node,
    writer_node,
    route_after_router,
    route_after_entitlements,
    route_after_retriever,
    route_after_critic
)
from app.schemas.chat import ChatResponse, CitationItem, ConflictItem
from app.observability.logger import logger


def build_copilot_graph() -> Any:
    """Builds and compiles the StateGraph for Project Atlas Copilot Agent."""
    workflow = StateGraph(AgentGraphState)

    # 1. Register all 8 workflow nodes
    workflow.add_node("router", router_node)
    workflow.add_node("entitlement_checker", entitlement_checker_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("read_only_sql", read_only_sql_node)
    workflow.add_node("calculator", calculator_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("escalation", escalation_node)
    workflow.add_node("writer", writer_node)

    # 2. Set Entrypoint
    workflow.set_entry_point("router")

    # 3. Add Conditional Transitions
    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {
            "escalation": "escalation",
            "entitlement_checker": "entitlement_checker"
        }
    )

    workflow.add_conditional_edges(
        "entitlement_checker",
        route_after_entitlements,
        {
            "escalation": "escalation",
            "read_only_sql": "read_only_sql",
            "retriever": "retriever"
        }
    )

    workflow.add_conditional_edges(
        "retriever",
        route_after_retriever,
        {
            "calculator": "calculator",
            "critic": "critic"
        }
    )

    workflow.add_edge("read_only_sql", "critic")
    workflow.add_edge("calculator", "critic")

    workflow.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "escalation": "escalation",
            "writer": "writer"
        }
    )

    workflow.add_edge("escalation", "writer")
    workflow.add_edge("writer", END)

    return workflow.compile()


# Compile Singleton Agent Graph
copilot_agent_graph = build_copilot_graph()


def run_copilot_workflow(
    db: Session,
    query: str,
    client_id: str,
    conversation_id: Optional[str] = None,
    report_id: Optional[str] = None
) -> ChatResponse:
    """
    Executes the compiled LangGraph workflow end-to-end and returns a structured ChatResponse.
    """
    logger.info(f"[LangGraph] Initiating agent workflow for client='{client_id}', query='{query[:60]}...'")

    initial_state: AgentGraphState = {
        "query": query,
        "client_id": client_id,
        "conversation_id": conversation_id,
        "target_report_id": report_id,
        "is_authenticated": True,
        "is_authorized": True,
        "permitted_reports": [],
        "retrieved_metrics": [],
        "retrieved_chunks": [],
        "sql_aggregate_results": None,
        "derived_values": {},
        "conflicts": [],
        "critic_notes": [],
        "citations": [],
        "final_answer": "",
        "escalated": False,
        "confidence_score": 0.0,
        "node_history": [],
        "execution_latencies": {},
        "token_usage": {"prompt_tokens": len(query.split()) * 2, "completion_tokens": 0},
        "retry_count": 0,
        "error": None
    }

    config = {"configurable": {"db": db}}

    # Execute graph with state propagation
    final_state: AgentGraphState = copilot_agent_graph.invoke(initial_state, config=config)

    # Convert citations to Pydantic CitationItem
    pydantic_citations: List[CitationItem] = []
    for c in final_state.get("citations", []):
        pydantic_citations.append(CitationItem(
            report_id=c.get("report_id"),
            title=c.get("title"),
            metric=c.get("metric"),
            period=c.get("period"),
            region=c.get("region"),
            value=c.get("value"),
            page=c.get("page"),
            source_type=c.get("source_type", "relational_sql"),
            text_snippet=c.get("text_snippet")
        ))

    # Convert conflicts to Pydantic ConflictItem
    pydantic_conflicts: List[ConflictItem] = []
    for cf in final_state.get("conflicts", []):
        pydantic_conflicts.append(ConflictItem(
            metric=cf.get("metric", "Methodological Conflict"),
            description=cf.get("description", ""),
            sources=cf.get("sources", [])
        ))

    return ChatResponse(
        answer=final_state.get("final_answer", ""),
        citations=pydantic_citations,
        confidence=float(final_state.get("confidence_score", 0.0)),
        conflicts=pydantic_conflicts,
        derived_values=final_state.get("derived_values", {}),
        escalated=bool(final_state.get("escalated", False)),
        client_id=client_id,
        conversation_id=conversation_id,
        escalation_ticket=final_state.get("escalation_ticket_id")
    )
