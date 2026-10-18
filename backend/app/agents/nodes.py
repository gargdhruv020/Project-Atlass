"""
LangGraph Nodes for Project Atlas Agent Workflow
Implements:
1. Router: Intent classification (factual, comparison, calculation, sql_aggregate, out_of_scope, unsafe).
2. Entitlement Checker: Authoritative MySQL client permission validation.
3. Retriever: ChromaDB vector search + MySQL structured metric retrieval with strict hard verification.
4. Read-Only SQL Tool: Safe parameterized aggregations over permitted data.
5. Calculator: Deterministic CAGR future projections and regional share sizing.
6. Critic / Fact-Checker: Grounding audit, citation validation, conflict analysis, and confidence scoring.
7. Writer: Synthesis of grounded structured ChatResponse.
8. Escalation Handler: Creation of analyst escalation ticket in MySQL without leaking protected data.
"""

import re
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.agents.state import AgentGraphState
from app.services.client_service import ClientService
from app.services.escalation_service import EscalationService
from app.models.report import Report
from app.tools.db_tool import DatabaseTool
from app.tools.calculator import MarketCalculator
from app.tools.sql_tool import ReadOnlySQLTool
from app.retrieval.vector_store import vector_store_service
from app.retrieval.rag_pipeline import PROMPT_INJECTION_INDICATORS
from app.schemas.chat import ChatResponse, CitationItem, ConflictItem
from app.observability.logger import logger


# =====================================================================
# 1. Router Node
# =====================================================================

def router_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Classifies user query into one of 6 distinct intent categories."""
    t0 = time.perf_counter()
    query = state.get("query", "").strip()
    q_lower = query.lower()

    # Extract target report ID if present in query
    target_report_id = state.get("target_report_id")
    if not target_report_id:
        match = re.search(r"\b(R-10[1-9])\b", query, re.IGNORECASE)
        if match:
            target_report_id = match.group(1).upper()

    # 1. Check Unsafe / Adversarial Prompt Injections
    is_unsafe = any(ind in q_lower for ind in PROMPT_INJECTION_INDICATORS)
    if is_unsafe or any(k in q_lower for k in ["reveal all passwords", "dump database", "bypass permissions", "unmasked users"]):
        intent = "unsafe_unauthorized"
        reason = "Detected adversarial injection attempt or sensitive security breach query."

    # 2. Check Out-of-Scope Requests
    elif any(k in q_lower for k in [
        "write a poem", "python function", "binary search", "weather in", "chocolate cake recipe",
        "tell me a joke", "who won the match", "solve this leetcode", "javascript code"
    ]):
        intent = "out_of_scope"
        reason = "Inquiry is unrelated to market research or business intelligence reports."

    # 3. Check SQL Aggregate Queries
    elif any(k in q_lower for k in [
        "average cagr", "mean cagr", "avg cagr", "highest market size", "largest market size",
        "how many metrics", "count of metrics", "total metrics", "metrics by region", "regional distribution"
    ]):
        intent = "sql_aggregate"
        reason = "Relational aggregate computation requested over MySQL metrics."

    # 4. Check Calculation / Projection Queries
    elif any(k in q_lower for k in [
        "project", "forecast", "projection", "calculate", "future size", "in 2028", "in 2029", "in 2030", "implied size"
    ]):
        intent = "calculation_projection"
        reason = "Mathematical forecasting or implied market sizing calculation requested."

    # 5. Check Comparison Queries
    elif any(k in q_lower for k in ["compare", "difference between", "versus", "vs", "contrast", "divergence"]):
        intent = "comparison"
        reason = "Cross-report comparative evaluation requested."

    # 6. Default to Factual Lookup
    else:
        intent = "factual_lookup"
        reason = "Standard factual market research lookup."

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(f"[RouterNode] Query classified as '{intent}' ({elapsed:.2f}ms) | Reason: {reason}")

    return {
        "intent": intent,
        "routing_reason": reason,
        "target_report_id": target_report_id,
        "node_history": state.get("node_history", []) + ["router"],
        "execution_latencies": {**state.get("execution_latencies", {}), "router": elapsed}
    }


# =====================================================================
# 2. Entitlement Checker Node
# =====================================================================

def entitlement_checker_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Verifies calling client exists and retrieves authorized report scope from MySQL."""
    t0 = time.perf_counter()
    db: Session = (config or {}).get("configurable", {}).get("db")
    client_id = state.get("client_id", "")
    target_report_id = state.get("target_report_id")

    if not db:
        from app.db.session import SessionLocal
        db = SessionLocal()

    # 1. Validate Client Exists
    client = ClientService.get_client(db, client_id)
    if not client:
        elapsed = (time.perf_counter() - t0) * 1000
        logger.warning(f"[EntitlementCheckerNode] Client '{client_id}' not found in database.")
        return {
            "is_authenticated": False,
            "is_authorized": False,
            "permitted_reports": [],
            "access_message": f"Client '{client_id}' is not recognized in the system.",
            "escalated": True,
            "node_history": state.get("node_history", []) + ["entitlement_checker"],
            "execution_latencies": {**state.get("execution_latencies", {}), "entitlement_checker": elapsed}
        }

    # 2. Retrieve Permitted Scope from MySQL
    permitted = list(ClientService.get_permitted_reports(db, client_id))

    # 3. Target Report Pre-Check if Scoped
    if target_report_id:
        has_access, reason = ClientService.check_report_access(db, client_id, target_report_id)
        if not has_access:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.warning(
                f"ACCESS_DENIED: client='{client_id}' attempted access to unpurchased report='{target_report_id}'"
            )
            return {
                "is_authenticated": True,
                "is_authorized": False,
                "permitted_reports": permitted,
                "access_message": reason,
                "escalated": True,
                "node_history": state.get("node_history", []) + ["entitlement_checker"],
                "execution_latencies": {**state.get("execution_latencies", {}), "entitlement_checker": elapsed}
            }

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(
        f"[EntitlementCheckerNode] Client '{client_id}' authorized. Permitted scope: {permitted} ({elapsed:.2f}ms)"
    )

    return {
        "is_authenticated": True,
        "is_authorized": True,
        "permitted_reports": permitted,
        "access_message": "Access authorized.",
        "node_history": state.get("node_history", []) + ["entitlement_checker"],
        "execution_latencies": {**state.get("execution_latencies", {}), "entitlement_checker": elapsed}
    }


# =====================================================================
# 3. Retriever Node
# =====================================================================

def retriever_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Retrieves structured MySQL metrics and ChromaDB chunks with hard Python validation."""
    t0 = time.perf_counter()
    db: Session = (config or {}).get("configurable", {}).get("db")
    client_id = state.get("client_id", "")
    query = state.get("query", "")
    target_report_id = state.get("target_report_id")
    permitted_reports = set(state.get("permitted_reports", []))

    if not db:
        from app.db.session import SessionLocal
        db = SessionLocal()

    # 1. Structured Metrics from MySQL
    metric_kw = None
    if state.get("intent") not in ("calculation_projection", "comparison"):
        for kw in ["market size", "cagr", "regional share", "forecast", "revenue", "volume"]:
            if kw in query.lower():
                metric_kw = kw
                break

    raw_metrics = DatabaseTool.query_metrics(db=db, report_id=target_report_id, metric=metric_kw)
    filtered_metrics = []
    seen = set()
    for m in raw_metrics:
        rep = m.get("report_id")
        if rep in permitted_reports:
            tup = (rep, m.get("metric"), m.get("region"), m.get("period"), m.get("value"))
            if tup not in seen:
                seen.add(tup)
                filtered_metrics.append(m)

    # 2. ChromaDB Semantic Vector Retrieval
    vector_results = []
    try:
        vector_results = vector_store_service.entitled_similarity_search(
            db=db,
            client_id=client_id,
            query=query,
            n_results=settings.RAG_TOP_K,
            report_id=target_report_id,
            similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD
        )
    except Exception as e:
        logger.warning(f"[RetrieverNode] ChromaDB search error: {e}")

    # 3. Hard Python Gate: Validate every single chunk before inclusion
    verified_chunks = []
    for c in vector_results:
        rep_id = c.get("metadata", {}).get("report_id")
        has_perm, _ = ClientService.check_report_access(db, client_id, rep_id)
        if has_perm:
            verified_chunks.append(c)
        else:
            logger.error(f"ACCESS_DENIED_CHUNK: Blocked unentitled chunk from '{rep_id}' for '{client_id}'")

    # Build initial citations
    citations: List[Dict[str, Any]] = []
    for m in filtered_metrics:
        citations.append({
            "report_id": m.get("report_id"),
            "metric": m.get("metric"),
            "period": m.get("period"),
            "region": m.get("region"),
            "value": m.get("value"),
            "source_type": "relational_sql",
            "text_snippet": m.get("scope_note")
        })

    for c in verified_chunks:
        meta = c.get("metadata", {})
        citations.append({
            "report_id": meta.get("report_id"),
            "title": meta.get("title"),
            "page": meta.get("page", 1),
            "source_type": "vector_retrieval",
            "text_snippet": c.get("content", "")[:140]
        })

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(
        f"[RetrieverNode] Retrieved {len(filtered_metrics)} metrics, {len(verified_chunks)} vector chunks ({elapsed:.2f}ms)"
    )

    return {
        "retrieved_metrics": filtered_metrics,
        "retrieved_chunks": verified_chunks,
        "citations": citations,
        "node_history": state.get("node_history", []) + ["retriever"],
        "execution_latencies": {**state.get("execution_latencies", {}), "retriever": elapsed}
    }


# =====================================================================
# 4. Read-Only SQL Tool Node
# =====================================================================

def read_only_sql_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Executes safe, restricted parameterized aggregations over MySQL."""
    t0 = time.perf_counter()
    db: Session = (config or {}).get("configurable", {}).get("db")
    permitted_reports = set(state.get("permitted_reports", []))
    query = state.get("query", "")

    if not db:
        from app.db.session import SessionLocal
        db = SessionLocal()

    agg_result = ReadOnlySQLTool.execute_aggregate(
        db=db,
        permitted_reports=permitted_reports,
        query=query
    )

    # Format into a relational citation
    citations = state.get("citations", []) + [{
        "report_id": ", ".join(agg_result.get("sources", list(permitted_reports))),
        "metric": agg_result.get("aggregation", "sql_aggregate"),
        "value": agg_result.get("formatted_summary", ""),
        "source_type": "relational_sql",
        "text_snippet": agg_result.get("details")
    }]

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(f"[ReadOnlySQLNode] Aggregate executed: {agg_result.get('aggregation')} ({elapsed:.2f}ms)")

    return {
        "sql_aggregate_results": agg_result,
        "citations": citations,
        "node_history": state.get("node_history", []) + ["read_only_sql"],
        "execution_latencies": {**state.get("execution_latencies", {}), "read_only_sql": elapsed}
    }


# =====================================================================
# 5. Calculator Node
# =====================================================================

def calculator_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Performs deterministic market growth projections and regional derivations."""
    t0 = time.perf_counter()
    query = state.get("query", "")
    metrics = state.get("retrieved_metrics", [])

    calc_results = MarketCalculator.evaluate_projection_query(query=query, metrics=metrics)

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(f"[CalculatorNode] Derived {len(calc_results)} value(s) ({elapsed:.2f}ms)")

    return {
        "derived_values": {**state.get("derived_values", {}), **calc_results},
        "node_history": state.get("node_history", []) + ["calculator"],
        "execution_latencies": {**state.get("execution_latencies", {}), "calculator": elapsed}
    }


# =====================================================================
# 6. Critic / Fact-Checker Node
# =====================================================================

def critic_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Inspects evidence grounding, detects methodological conflicts, and scores confidence."""
    t0 = time.perf_counter()
    metrics = state.get("retrieved_metrics", [])
    chunks = state.get("retrieved_chunks", [])
    sql_agg = state.get("sql_aggregate_results")
    query = state.get("query", "").lower()

    # 1. Check for explicit user request for escalation
    user_wants_escalation = any(
        k in query for k in ["escalate", "human analyst", "talk to human", "support ticket"]
    )

    # 2. Conflict Detection across reports
    conflicts: List[Dict[str, Any]] = []
    metrics_by_name: Dict[str, List[Dict[str, Any]]] = {}
    for m in metrics:
        name = (m.get("metric") or "").lower()
        metrics_by_name.setdefault(name, []).append(m)

    for name, items in metrics_by_name.items():
        if len(items) > 1:
            reps = list({i.get("report_id") for i in items if i.get("report_id")})
            if len(reps) > 1:
                desc = [f"{i.get('report_id')}: {i.get('value')} ({i.get('period')}, {i.get('scope_note') or 'standard scope'})" for i in items]
                conflicts.append({
                    "metric": items[0].get("metric", name.title()),
                    "description": "Methodological divergence across reports: " + "; ".join(desc),
                    "sources": reps
                })

    # 3. Grounding Assessment
    has_evidence = bool(metrics or chunks or sql_agg)
    if user_wants_escalation:
        is_grounded = False
        confidence = 0.50
        escalated = True
    elif not has_evidence:
        is_grounded = False
        confidence = 0.10
        escalated = True
    else:
        is_grounded = True
        confidence = 0.95 if (metrics and chunks) else (0.90 if metrics else 0.80)
        if conflicts:
            confidence = min(confidence, 0.90)
        escalated = False

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(
        f"[CriticNode] Grounded={is_grounded}, Confidence={confidence:.2f}, Conflicts={len(conflicts)} ({elapsed:.2f}ms)"
    )

    return {
        "conflicts": conflicts,
        "is_grounded": is_grounded,
        "confidence_score": confidence,
        "escalated": escalated,
        "node_history": state.get("node_history", []) + ["critic"],
        "execution_latencies": {**state.get("execution_latencies", {}), "critic": elapsed}
    }


# =====================================================================
# 7. Escalation Handler Node
# =====================================================================

def escalation_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Generates an analyst escalation ticket and formats safe response message."""
    t0 = time.perf_counter()
    db: Session = (config or {}).get("configurable", {}).get("db")
    client_id = state.get("client_id", "")
    query = state.get("query", "")
    intent = state.get("intent", "factual_lookup")
    target_report_id = state.get("target_report_id")
    access_message = state.get("access_message", "")

    if not db:
        from app.db.session import SessionLocal
        db = SessionLocal()

    # Determine escalation reason
    if intent == "unsafe_unauthorized":
        reason = "Adversarial prompt injection attempt or unauthorized security query"
        answer = "Security Notice: Your query contained an unauthorized directive or request outside safety boundaries. This incident has been logged for security review."
    elif intent == "out_of_scope":
        reason = "Out-of-scope inquiry outside market research domain"
        answer = "Out-of-Scope Notice: Project Atlas is dedicated to market research and industry intelligence. Your inquiry does not match our market research catalog."
    elif not state.get("is_authenticated", True):
        reason = f"Unrecognized client identifier '{client_id}'"
        answer = f"Client '{client_id}' is not recognized in the system."
    elif not state.get("is_authorized", True):
        target_rep = db.query(Report).filter(Report.id == target_report_id).first() if target_report_id else None
        rep_title_str = f" ('{target_rep.title}')" if target_rep else ""
        reason = f"Access denied to unpurchased report '{target_report_id}'"
        ticket = EscalationService.create_escalation(client_id=client_id, query_text=query, reason=reason, priority="high")
        ticket_id = ticket.get("ticket_id")
        answer = (
            f"Access Denied: {access_message}.\n\n"
            f"Report {target_report_id}{rep_title_str} exists in the Project Atlas market intelligence catalog, "
            f"but is not included in your active subscription tier. "
            f"To view its full quantitative projections and market metrics, please request an entitlement upgrade "
            f"from your account representative or submit an access request (Ticket: {ticket_id})."
        )
        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "escalated": True,
            "escalation_ticket_id": ticket_id,
            "final_answer": answer,
            "confidence_score": 0.0,
            "node_history": state.get("node_history", []) + ["escalation"],
            "execution_latencies": {**state.get("execution_latencies", {}), "escalation": elapsed}
        }
    elif any(k in query.lower() for k in ["escalate", "human analyst", "talk to human"]):
        reason = "Explicit user request for human analyst intervention"
        answer = "Your request has been routed to a senior market research analyst for human review."
    else:
        reason = "No matching research evidence found in client's entitled reports"
        answer = (
            f"No verified research data found for query: '{query}'. "
            f"The requested topic is either outside your entitled reports or not covered in the current market database. "
            f"An analyst escalation ticket has been created for manual investigation."
        )

    ticket = EscalationService.create_escalation(
        client_id=client_id,
        query_text=query,
        reason=reason,
        priority="high" if intent == "unsafe_unauthorized" else "medium"
    )
    ticket_id = ticket.get("ticket_id")

    if not answer.endswith(f"({ticket_id}).") and "escalation ticket" in answer.lower():
        answer += f" (Ticket: {ticket_id})"

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(f"[EscalationNode] Created ticket '{ticket_id}' | Reason: {reason} ({elapsed:.2f}ms)")

    return {
        "escalated": True,
        "escalation_ticket_id": ticket_id,
        "final_answer": answer,
        "confidence_score": state.get("confidence_score", 0.10) if state.get("is_authenticated", True) else 0.0,
        "node_history": state.get("node_history", []) + ["escalation"],
        "execution_latencies": {**state.get("execution_latencies", {}), "escalation": elapsed}
    }


# =====================================================================
# 8. Writer Node
# =====================================================================

def writer_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Produces the final grounded answer and formats structured response."""
    t0 = time.perf_counter()
    db: Session = (config or {}).get("configurable", {}).get("db")
    client_id = state.get("client_id", "")
    query = state.get("query", "")
    metrics = state.get("retrieved_metrics", [])
    chunks = state.get("retrieved_chunks", [])
    sql_agg = state.get("sql_aggregate_results")
    derived = state.get("derived_values", {})
    conflicts = state.get("conflicts", [])
    existing_answer = state.get("final_answer")

    if not db:
        from app.db.session import SessionLocal
        db = SessionLocal()

    # If answer already prepared by escalation node, return it
    if existing_answer and state.get("escalated", False):
        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "node_history": state.get("node_history", []) + ["writer"],
            "execution_latencies": {**state.get("execution_latencies", {}), "writer": elapsed}
        }

    # Format synthesized findings
    parts = [f"### Market Research Findings for '{query}':"]

    # 1. SQL Aggregates if present
    if sql_agg and "formatted_summary" in sql_agg:
        parts.append(f"\n**Relational Aggregate Analysis:**\n- {sql_agg['formatted_summary']}")

    # 2. Structured Metrics
    if metrics:
        parts.append("\n**Verified Market Metrics:**")
        for m in metrics:
            scope = f" - *Note: {m.get('scope_note')}*" if m.get("scope_note") else ""
            parts.append(
                f"- **{m.get('metric')}** ({m.get('region')}, {m.get('period')}): **{m.get('value')}** "
                f"*(Source: Report {m.get('report_id')})*{scope}"
            )

    # 3. Vector Narrative Insights
    if chunks:
        parts.append("\n**Key Narrative Insights (from Entitled Reports):**")
        for c in chunks[:3]:
            meta = c.get("metadata", {})
            rep_id = meta.get("report_id", "Unknown")
            page = meta.get("page", 1)
            snippet = c.get("content", "").replace("\n", " ").strip()
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
            parts.append(f"- [Report {rep_id}, Page {page}]: \"{snippet}\"")

    # 4. Derived Values / Projections
    if derived:
        parts.append("\n**Derived Insights (Calculated Estimates):**")
        for k, v in derived.items():
            if not k.endswith("_formula"):
                label = k.replace("_", " ").title()
                formula_str = f" *(Formula: {derived.get(f'{k}_formula', '')})*" if f"{k}_formula" in derived else ""
                parts.append(f"- **{label}**: `{v}`{formula_str}")

    # 5. Methodological Conflicts
    if conflicts:
        parts.append("\n**Methodological Divergences & Source Scopes:**")
        for conf in conflicts:
            parts.append(f"- *{conf['metric']}*: {conf['description']}")

    # 6. Check for unpurchased catalog reports to offer upgrade
    try:
        unpurchased_meta = ClientService.get_unpurchased_reports_metadata(db, client_id)
        relevant = []
        for unp in unpurchased_meta:
            title_words = set(re.findall(r"\w+", unp["title"].lower()))
            query_words = set(re.findall(r"\w+", query.lower()))
            overlap = title_words.intersection(query_words) - {
                "market", "report", "the", "and", "in", "for", "outlook", "industry", "global", "2024", "2025"
            }
            if overlap:
                relevant.append(unp)

        if relevant:
            parts.append("\n**Additional Research Available in Project Atlas Library:**")
            for r in relevant[:2]:
                parts.append(
                    f"- Report {r['id']} ('{r['title']}'): Premium {r['access']} report available. "
                    f"Submit an access request or contact your account representative to upgrade your subscription."
                )
    except Exception as e:
        logger.debug(f"Catalog upgrade check error: {e}")

    final_answer = "\n".join(parts)
    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(f"[WriterNode] Formatted grounded answer ({elapsed:.2f}ms)")

    return {
        "final_answer": final_answer,
        "node_history": state.get("node_history", []) + ["writer"],
        "execution_latencies": {**state.get("execution_latencies", {}), "writer": elapsed}
    }


# =====================================================================
# Conditional Edge Routing Functions
# =====================================================================

def route_after_router(state: AgentGraphState) -> str:
    """Routes based on router intent classification."""
    intent = state.get("intent", "factual_lookup")
    if intent in ("unsafe_unauthorized", "out_of_scope"):
        return "escalation"
    return "entitlement_checker"


def route_after_entitlements(state: AgentGraphState) -> str:
    """Routes based on client authentication and report entitlement status."""
    if not state.get("is_authenticated", True) or not state.get("is_authorized", True):
        return "escalation"
    if state.get("intent") == "sql_aggregate":
        return "read_only_sql"
    return "retriever"


def route_after_retriever(state: AgentGraphState) -> str:
    """Routes calculation queries to calculator; others directly to critic."""
    if state.get("intent") == "calculation_projection":
        return "calculator"
    return "critic"


def route_after_critic(state: AgentGraphState) -> str:
    """Routes ungrounded or low-confidence questions to escalation handler."""
    if state.get("escalated", False) or not state.get("is_grounded", True):
        return "escalation"
    return "writer"
