"""
Agent Graph State Definition for Project Atlas LangGraph Workflow
Defines strongly typed, explicit state schema for routing, entitlement verification,
multi-source retrieval, calculation, critique, synthesis, and escalation.
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal


class AgentGraphState(TypedDict, total=False):
    # Initial Request Inputs
    query: str
    client_id: str
    conversation_id: Optional[str]
    target_report_id: Optional[str]

    # Router Classification
    intent: Literal[
        "factual_lookup",
        "comparison",
        "calculation_projection",
        "sql_aggregate",
        "out_of_scope",
        "unsafe_unauthorized"
    ]
    routing_reason: str

    # Entitlement & Authorization
    is_authenticated: bool
    is_authorized: bool
    permitted_reports: List[str]
    access_message: Optional[str]
    escalation_ticket_id: Optional[str]

    # Retrieved Evidence
    retrieved_metrics: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    sql_aggregate_results: Optional[Dict[str, Any]]

    # Calculations & Derived Values
    derived_values: Dict[str, Any]

    # Critic & Fact-Checker
    conflicts: List[Dict[str, Any]]
    critic_notes: List[str]
    is_grounded: bool
    confidence_score: float

    # Final Output Synthesis
    final_answer: str
    citations: List[Dict[str, Any]]
    escalated: bool

    # Observability & Execution Metrics
    node_history: List[str]
    execution_latencies: Dict[str, float]
    token_usage: Dict[str, int]
    retry_count: int
    error: Optional[str]
