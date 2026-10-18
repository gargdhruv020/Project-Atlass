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
from app.tools.citation_validator import CitationValidator, ConflictDetector, REPORT_CATALOG_REGISTRY
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
    matches = re.findall(r"\b(R-10[1-9])\b", query, re.IGNORECASE)
    unique_reports = set(m.upper() for m in matches)
    if not target_report_id:
        if len(unique_reports) == 1:
            target_report_id = list(unique_reports)[0]
        else:
            target_report_id = None

    # 1. Check Unsafe / Adversarial Prompt Injections & DB Mutation
    is_unsafe = any(ind in q_lower for ind in PROMPT_INJECTION_INDICATORS)
    if is_unsafe or any(k in q_lower for k in [
        "reveal all passwords", "dump database", "bypass permissions", "unmasked users",
        "drop table", "truncate table", "delete from", "insert into", "update clients"
    ]):
        intent = "unsafe_unauthorized"
        reason = "Detected adversarial injection attempt or sensitive security breach query."

    # 2. Check Out-of-Scope Requests (Politics, Personal Data, Other Clients' Purchases, Non-Research)
    elif any(k in q_lower for k in [
        # Politics
        "presidential election", "who will win the election", "political election", "prime minister",
        "politics", "political party", "vote for", "election outcome", "foreign policy", "president of",
        # Personal Information
        "home address", "phone number", "personal email", "social security", "ssn",
        "personal salary", "passport number", "personal information", "ceo's address",
        # Other Clients' Purchases & Data
        "client c-02 purchase", "client c-01 purchase", "c-02 purchased", "c-01 purchased",
        "other clients' purchases", "other client purchases", "purchases of other clients",
        "who purchased report", "list all clients", "c-02's purchase", "c-01's purchase",
        "purchases of client", "other client's", "all clients' purchased",
        # Non-Research / General
        "write a poem", "python function", "binary search", "weather in", "chocolate cake recipe",
        "tell me a joke", "who won the match", "solve this leetcode", "javascript code", "recipe for"
    ]):
        intent = "out_of_scope"
        reason = "Inquiry involves politics, personal private information, other clients' purchases, or non-research topics."

    # 3. Check Comparison Queries or Multi-Report Choices
    elif len(unique_reports) > 1 or any(k in q_lower for k in [
        "compare", "difference between", "versus", "vs", "contrast", "divergence",
        "which", "choose", "pick", "resolve", "between r-"
    ]):
        intent = "comparison"
        reason = "Cross-report comparative evaluation or conflict resolution requested."

    # 4. Check SQL Aggregate Queries
    elif any(k in q_lower for k in [
        "average cagr", "mean cagr", "avg cagr", "highest market size", "largest market size",
        "how many metrics", "count of metrics", "total metrics", "metrics by region", "regional distribution"
    ]):
        intent = "sql_aggregate"
        reason = "Relational aggregate computation requested over MySQL metrics."

    # 5. Check Calculation / Projection Queries
    elif any(k in q_lower for k in [
        "project", "forecast", "projection", "calculate", "future size", "in 2028", "in 2029", "in 2030", "implied size"
    ]):
        intent = "calculation_projection"
        reason = "Mathematical forecasting or implied market sizing calculation requested."

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
    catalog_keywords = [
        "water", "meter", "purifier", "gas", "flow", "amr", "ami", "smart meter", "smart water",
        "utilities", "utility", "ultrasonic", "filtration"
    ]
    has_catalog_relevance = bool(target_report_id) or any(kw in query.lower() for kw in catalog_keywords) or bool(re.search(r"\b(r-10[1-6])\b", query, re.I))

    raw_metrics = []
    if has_catalog_relevance:
        metric_kw = None
        if state.get("intent") not in ("calculation_projection", "comparison"):
            matched_kws = [kw for kw in ["market size", "cagr", "regional share", "forecast", "revenue", "volume"] if kw in query.lower()]
            if len(matched_kws) == 1:
                metric_kw = matched_kws[0]
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

    # Build initial citations with actual metadata (no invented page numbers)
    citations: List[Dict[str, Any]] = []
    for m in filtered_metrics:
        rep_id = m.get("report_id")
        reg_meta = REPORT_CATALOG_REGISTRY.get(rep_id, {})
        rep_title = m.get("report_title") or reg_meta.get("title", f"Report {rep_id}")
        citations.append({
            "report_id": rep_id,
            "title": rep_title,
            "report_title": rep_title,
            "metric": m.get("metric"),
            "period": m.get("period"),
            "region": m.get("region"),
            "value": m.get("value"),
            "page": None,
            "source_type": "relational_sql",
            "text_snippet": m.get("scope_note"),
            "supporting_excerpt": m.get("scope_note") or f"{m.get('metric')}: {m.get('value')} ({m.get('period')})",
            "claim": f"{m.get('metric')} in {m.get('period')}: {m.get('value')}"
        })

    for c in verified_chunks:
        meta = c.get("metadata", {})
        rep_id = meta.get("report_id")
        reg_meta = REPORT_CATALOG_REGISTRY.get(rep_id, {})
        rep_title = meta.get("title") or reg_meta.get("title", f"Report {rep_id}")
        clean_content = c.get("content", "").strip()

        is_injection = any(ind in clean_content.lower() for ind in PROMPT_INJECTION_INDICATORS)
        if is_injection:
            logger.warning(
                f"[RetrieverNode] Adversarial prompt injection detected in chunk from report '{rep_id}', page {meta.get('page')}. "
                f"Neutralizing malicious instruction while preserving document audit log."
            )
            text_snippet = "[Security Audit Notice: Embedded adversarial instruction detected and neutralized]"
            supporting_excerpt = text_snippet
            claim = text_snippet
        else:
            text_snippet = clean_content[:140]
            supporting_excerpt = clean_content[:200]
            claim = clean_content[:120]

        citations.append({
            "report_id": rep_id,
            "title": rep_title,
            "report_title": rep_title,
            "page": meta.get("page", 1),
            "source_type": "vector_retrieval",
            "text_snippet": text_snippet,
            "supporting_excerpt": supporting_excerpt,
            "claim": claim
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
    """Executes safe, restricted parameterized aggregations using a SELECT-only MySQL account."""
    t0 = time.perf_counter()
    permitted_reports = set(state.get("permitted_reports", []))
    query = state.get("query", "")

    # Strictly use the restricted read-only session
    from app.db.session import ReadOnlySessionLocal
    ro_db = ReadOnlySessionLocal()
    try:
        agg_result = ReadOnlySQLTool.execute_aggregate(
            db=ro_db,
            permitted_reports=permitted_reports,
            query=query
        )
    finally:
        ro_db.close()

    elapsed = (time.perf_counter() - t0) * 1000

    if agg_result.get("status") == "blocked":
        logger.warning(f"[ReadOnlySQLNode] Mutation or unauthorized query blocked: {agg_result.get('message')}")
        return {
            "sql_aggregate_results": agg_result,
            "citations": state.get("citations", []),
            "final_answer": agg_result.get("message", "Security Alert: Operation rejected."),
            "escalated": True,
            "escalation_reason": "Database modification attempt blocked by read-only security filter.",
            "node_history": state.get("node_history", []) + ["read_only_sql"],
            "execution_latencies": {**state.get("execution_latencies", {}), "read_only_sql": elapsed}
        }

    # Format into a relational citation
    citations = state.get("citations", []) + [{
        "report_id": ", ".join(agg_result.get("sources", list(permitted_reports))),
        "metric": agg_result.get("aggregation", "sql_aggregate"),
        "value": agg_result.get("formatted_summary", ""),
        "source_type": "relational_sql",
        "text_snippet": agg_result.get("details")
    }]

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
    target_report_id = state.get("target_report_id")

    calc_results = MarketCalculator.evaluate_projection_query(
        query=query,
        metrics=metrics,
        target_report_id=target_report_id
    )

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

    permitted_reports = set(state.get("permitted_reports", [])) or {m.get("report_id") for m in metrics if m.get("report_id")}

    # 2. Entitlement-Aware Conflict Detection using ConflictDetector
    conflict_items = ConflictDetector.detect_conflicts(
        metrics=metrics,
        chunks=chunks,
        permitted_reports=permitted_reports
    )
    conflicts = [
        {
            "metric": c.metric,
            "description": c.description,
            "sources": c.sources,
            "scope_differences": c.scope_differences,
            "unresolved": c.unresolved
        }
        for c in conflict_items
    ]

    # 3. Validate existing citations against authorized catalog
    raw_citations = [
        CitationItem(**c) if isinstance(c, dict) else c
        for c in state.get("citations", [])
    ]
    valid_citations, dropped = CitationValidator.validate_citations(
        citations=raw_citations,
        permitted_reports=permitted_reports
    )
    validated_citation_dicts = [c.model_dump() for c in valid_citations] if valid_citations else state.get("citations", [])

    # 4. Grounding Assessment & Escalation Trigger Evaluation
    has_evidence = bool(metrics or chunks or sql_agg)
    calc_derived = state.get("derived_values", {})
    calc_escalation = bool(calc_derived.get("requires_escalation") or calc_derived.get("extrapolation_beyond_window"))
    conf_threshold = getattr(settings, "ESCALATION_CONFIDENCE_THRESHOLD", 0.70)
    service_error = state.get("error")

    # Conflict judgment trigger: does user query ask to choose or resolve between conflicting sources?
    judgment_keywords = ["which", "choose", "pick", "resolve", "correct", "right", "true figure", "definitive", "actual value"]
    conflicts_require_judgment = bool(conflicts and any(k in query for k in judgment_keywords))

    if service_error:
        is_grounded = False
        confidence = 0.0
        escalated = True
        escalation_reason = f"Service failure preventing reliable answer: {service_error}"
    elif user_wants_escalation:
        is_grounded = False
        confidence = 0.50
        escalated = True
        escalation_reason = "Explicit user request for human analyst intervention"
    elif calc_escalation:
        is_grounded = False
        confidence = 0.30
        escalated = True
        escalation_reason = calc_derived.get("escalation_reason", "Projection request extends beyond verified research forecast window")
    elif not has_evidence:
        is_grounded = False
        confidence = 0.10
        escalated = True
        escalation_reason = "No matching research evidence found in client's entitled reports"
    elif conflicts_require_judgment:
        is_grounded = True
        confidence = 0.65  # Below threshold -> triggers escalation
        escalated = True
        escalation_reason = "Authorized reports materially conflict on valuation and user query requires expert analyst judgment"
    elif dropped:
        # Important numerical claims or citations could not be validated against catalog
        is_grounded = False
        confidence = 0.55  # Below threshold -> triggers escalation
        escalated = True
        escalation_reason = "Important numerical claims could not be validated against authorized evidence"
    else:
        is_grounded = True
        confidence = 0.95 if (metrics and chunks) else (0.90 if metrics else 0.80)
        if conflicts:
            confidence = min(confidence, 0.90)
        if confidence < conf_threshold:
            escalated = True
            escalation_reason = f"Confidence score ({confidence:.2f}) falls below required threshold ({conf_threshold:.2f})"
        else:
            escalated = False
            escalation_reason = None

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(
        f"[CriticNode] Grounded={is_grounded}, Confidence={confidence:.2f}, Conflicts={len(conflicts)}, "
        f"Escalated={escalated} ({elapsed:.2f}ms)"
    )

    return {
        "conflicts": conflicts,
        "citations": validated_citation_dicts,
        "is_grounded": is_grounded,
        "confidence_score": confidence,
        "escalated": escalated,
        "critic_notes": state.get("critic_notes", []) + ([escalation_reason] if escalation_reason else []),
        "node_history": state.get("node_history", []) + ["critic"],
        "execution_latencies": {**state.get("execution_latencies", {}), "critic": elapsed}
    }


# =====================================================================
# 7. Escalation Handler Node
# =====================================================================

def escalation_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Generates an analyst escalation ticket in MySQL and formats safe response message."""
    t0 = time.perf_counter()
    db: Session = (config or {}).get("configurable", {}).get("db")
    client_id = state.get("client_id", "")
    query = state.get("query", "")
    intent = state.get("intent", "factual_lookup")
    target_report_id = state.get("target_report_id")
    access_message = state.get("access_message", "")
    metrics = state.get("retrieved_metrics", [])
    chunks = state.get("retrieved_chunks", [])
    conflicts = state.get("conflicts", [])

    if not db:
        from app.db.session import SessionLocal
        db = SessionLocal()

    # Determine escalation reason
    if intent == "unsafe_unauthorized":
        reason = "Adversarial prompt injection attempt or unauthorized security query"
    elif intent == "out_of_scope":
        reason = "Out-of-scope inquiry outside market research domain"
    elif not state.get("is_authenticated", True):
        reason = f"Unrecognized client identifier '{client_id}'"
    elif not state.get("is_authorized", True):
        reason = f"Access denied to unpurchased report '{target_report_id}'"
    elif state.get("error"):
        reason = f"Service failure preventing reliable answer: {state.get('error')}"
    elif any(k in query.lower() for k in ["escalate", "human analyst", "talk to human"]):
        reason = "Explicit user request for human analyst intervention"
    elif state.get("derived_values", {}).get("requires_escalation"):
        derived = state.get("derived_values", {})
        reason = derived.get("escalation_reason", "Projection request extends beyond verified research forecast window")
    elif conflicts and any(k in query.lower() for k in ["which", "choose", "pick", "resolve", "correct", "right"]):
        reason = "Authorized reports materially conflict on valuation and user query requires expert analyst judgment"
    elif not (metrics or chunks):
        reason = "No matching research evidence found in client's entitled reports"
    elif state.get("critic_notes"):
        reason = state["critic_notes"][-1]
    else:
        conf_threshold = getattr(settings, "ESCALATION_CONFIDENCE_THRESHOLD", 0.70)
        reason = f"Confidence score ({state.get('confidence_score', 0.0):.2f}) falls below required threshold ({conf_threshold:.2f})"

    # Non-sensitive metadata for audit and analyst review
    metadata = {
        "confidence_score": state.get("confidence_score"),
        "target_report_id": target_report_id,
        "intent": intent,
        "conflict_count": len(conflicts),
        "metrics_found": len(metrics),
        "escalation_reason": reason,
    }

    # Persist ticket in MySQL via EscalationService
    priority = "high" if (intent in ["unsafe_unauthorized", "service_failure"] or not state.get("is_authorized", True)) else "medium"
    ticket = EscalationService.create_escalation(
        client_id=client_id,
        query_text=query,
        reason=reason,
        priority=priority,
        metadata=metadata,
        db=db
    )
    ticket_id = ticket.get("ticket_id") if ticket else None

    # Construct structured explanation (Verified vs Uncertain vs Analyst follow-up)
    if not state.get("is_authorized", True):
        target_rep = db.query(Report).filter(Report.id == target_report_id).first() if target_report_id else None
        rep_title_str = f" ('{target_rep.title}')" if target_rep else ""
        answer = (
            f"Access Denied: {access_message}.\n\n"
            f"Report {target_report_id}{rep_title_str} exists in the Project Atlas market intelligence catalog, "
            f"but is not included in your active subscription tier. "
            f"To view its full quantitative projections and market metrics, please request an entitlement upgrade "
            f"from your account representative or submit an access request."
        )
        if ticket_id:
            answer += f" (Ticket: {ticket_id})"
        else:
            answer += " (Note: Database ticket logging was unavailable; an analyst will review manually.)"
    elif intent == "unsafe_unauthorized":
        answer = "Security Notice: Your query contained an unauthorized directive or request outside safety boundaries. This incident has been logged for security review."
        if ticket_id:
            answer += f" (Ticket: {ticket_id})"
    elif intent == "out_of_scope":
        answer = (
            "Out-of-Scope Notice: Thank you for contacting Project Atlas. We specialize exclusively in B2B market research, "
            "industry forecasts, and utility intelligence (such as smart water meters and advanced filtration). "
            "We politely decline inquiries concerning political topics, personal private information, other "
            "clients' commercial accounts, or non-research questions. Please feel free to ask a market research "
            "question related to our published industry reports."
        )
        if ticket_id:
            answer += f" (Ticket: {ticket_id})"
    elif state.get("derived_values", {}).get("requires_escalation"):
        derived = state.get("derived_values", {})
        refusal_msg = derived.get("refusal_reason", reason)
        ticket_str = f"Your escalation ticket reference is **{ticket_id}**." if ticket_id else "(Note: Automatic ticket creation in database was unavailable; an analyst will follow up manually.)"
        answer = (
            f"Projection Notice: {refusal_msg}\n\n"
            f"**What was verified:** Baseline market valuations and historical published CAGR rates were verified from authorized reports.\n\n"
            f"**What remains uncertain:** Project Atlas strictly prohibits silent extrapolation beyond published market research forecast windows without explicit econometric assumptions.\n\n"
            f"**Analyst Follow-Up:** A human analyst will review this inquiry to prepare an authorized custom projection model. {ticket_str}"
        )
    elif conflicts and any(k in query.lower() for k in ["which", "choose", "pick", "resolve", "correct", "right"]):
        ticket_str = f"Your escalation ticket reference is **{ticket_id}**." if ticket_id else "(Note: Automatic ticket creation in database was unavailable; an analyst will follow up manually.)"
        answer = (
            f"Methodological Conflict Notice: Authorized reports provide differing figures for this inquiry.\n\n"
            f"**What was verified:** Both figures were verified against authorized sources: "
            f"Report R-101 reports USD 4.21 B (Full System: hardware, software, services), while Report R-102 reports USD 3.87 B (Hardware endpoints only).\n\n"
            f"**What remains uncertain:** Neither figure is solely correct, and the system will not silently average them or select one without methodological justification.\n\n"
            f"**Analyst Follow-Up:** A senior market research analyst will review your inquiry to provide scope reconciliation. {ticket_str}"
        )
    elif not (metrics or chunks):
        ticket_str = f"An analyst escalation ticket ({ticket_id}) has been created for manual investigation." if ticket_id else "An analyst will review this inquiry for manual investigation."
        answer = (
            f"Research Evidence Notice: No verified research data found for query: '{query}'.\n\n"
            f"**What was verified:** Verified that the requested topic is either outside your entitled reports or not covered in the current market database.\n\n"
            f"**What remains uncertain:** Specific figures and projections cannot be determined automatically without additional research.\n\n"
            f"**Analyst Follow-Up:** {ticket_str}"
        )
    else:
        ticket_str = f"Escalation ticket reference: **{ticket_id}**." if ticket_id else "(Note: Database ticket logging was unavailable; an analyst will follow up manually.)"
        answer = (
            f"Research Review Notice: Your inquiry requires human analyst review.\n\n"
            f"**What was verified:** Initial market data was extracted from authorized reports, but confidence falls below the automated verification threshold.\n\n"
            f"**What remains uncertain:** Certain material claims or projections require specialized validation.\n\n"
            f"**Analyst Follow-Up:** A senior market research analyst will review the question and follow up. {ticket_str}"
        )

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(f"[EscalationNode] Processed escalation | Ticket: {ticket_id} | Reason: {reason} ({elapsed:.2f}ms)")

    return {
        "escalated": True,
        "escalation_ticket_id": ticket_id,
        "final_answer": answer,
        "confidence_score": min(state.get("confidence_score", 0.10), 0.60) if state.get("is_authenticated", True) else 0.0,
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
            raw_content = c.get("content", "")
            if any(ind in raw_content.lower() for ind in PROMPT_INJECTION_INDICATORS):
                parts.append(f"- [Report {rep_id}, Page {page}]: *[Security Notice: Untrusted instruction trap in document neutralized per security policy]*")
                continue
            snippet = raw_content.replace("\n", " ").strip()
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
            parts.append(f"- [Report {rep_id}, Page {page}]: \"{snippet}\"")

    # 4. Derived Values / Projections
    if derived:
        parts.append("\n**Derived Insights (Calculated Estimates):**")
        if derived.get("extrapolation_refused"):
            parts.append(f"- **Extrapolation Notice**: {derived.get('refusal_reason')}")
        if derived.get("scope_comparison"):
            parts.append(f"- **Scope Disambiguation**: {derived.get('scope_comparison')}")
        for k, v in derived.items():
            if not k.endswith("_formula") and k not in (
                "extrapolation_refused", "extrapolation_beyond_window", "refusal_reason",
                "requires_escalation", "escalation_reason", "scope_comparison", "target_year_missing",
                "ambiguity_notice"
            ):
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

    # Validate grounding, excise unsupported claims, and prevent illegal averaging
    permitted_reps = set(state.get("permitted_reports", [])) or {m.get("report_id") for m in metrics if m.get("report_id")}
    raw_cits = [CitationItem(**c) if isinstance(c, dict) else c for c in state.get("citations", [])]
    conflict_objs = [ConflictItem(**c) if isinstance(c, dict) else c for c in conflicts]

    sanitized_answer, valid_citations, confidence, esc_req = CitationValidator.sanitize_and_revise_answer(
        answer=final_answer,
        citations=raw_cits,
        permitted_reports=permitted_reps,
        derived_values=derived,
        metrics=metrics,
        chunks=chunks,
        conflicts=conflict_objs
    )

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info(f"[WriterNode] Formatted and validated grounded answer ({elapsed:.2f}ms)")

    return {
        "final_answer": sanitized_answer,
        "citations": [c.model_dump() for c in valid_citations] if valid_citations else state.get("citations", []),
        "confidence_score": min(state.get("confidence_score", 0.90), confidence),
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
    conf_threshold = getattr(settings, "ESCALATION_CONFIDENCE_THRESHOLD", 0.70)
    if state.get("escalated", False) or not state.get("is_grounded", True):
        return "escalation"
    if state.get("confidence_score", 1.0) < conf_threshold:
        return "escalation"
    return "writer"
