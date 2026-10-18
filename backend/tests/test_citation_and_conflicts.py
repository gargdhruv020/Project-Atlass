"""
Automated Test Suite for Citation Validator and Source-Conflict Detector
Covers:
1. Citation metadata coverage (report_id, report_title, page, claim, supporting_excerpt, source_type).
2. Fabricated citation rejection (fake report IDs and out-of-bounds page numbers).
3. Entitlement restrictions on citations.
4. Source-conflict detection for R-101 vs R-102 without averaging.
5. Prevention of unauthorized figure leakage in conflict explanations.
6. Neutralization of illegal averaging in generated answers.
7. Excision of ungrounded numerical claims and confidence calibration.
8. Proper labeling and input citation of derived estimates.
"""

import pytest
from app.schemas.chat import CitationItem, ConflictItem, ChatResponse
from app.tools.citation_validator import CitationValidator, ConflictDetector, REPORT_CATALOG_REGISTRY
from app.agents.workflow import run_copilot_workflow
from app.retrieval.rag_pipeline import RAGPipeline


# =====================================================================
# 1. Citation Metadata & Coverage
# =====================================================================

def test_citation_metadata_coverage_and_real_catalog():
    """Verify citations contain all required fields and map to verified catalog metadata."""
    citations_in = [
        CitationItem(
            report_id="R-101",
            metric="Market size",
            value="USD 4.21 B",
            period="2024",
            page=1,
            source_type="vector_retrieval",
            text_snippet="Global valuation reached USD 4.21 Billion."
        )
    ]
    permitted = {"R-101", "R-102"}
    valid, dropped = CitationValidator.validate_citations(citations_in, permitted)

    assert len(dropped) == 0
    assert len(valid) == 1
    c = valid[0]
    assert c.report_id == "R-101"
    assert c.report_title == "Global Smart Water Meter Market 2025"
    assert c.title == c.report_title
    assert c.page == 1
    assert c.claim is not None
    assert c.supporting_excerpt is not None
    assert c.source_type == "vector_retrieval"


def test_fabricated_citation_rejected():
    """Verify citations referencing non-existent report IDs are rejected."""
    citations_in = [
        CitationItem(
            report_id="R-999",  # Fabricated report
            metric="Market size",
            value="USD 99 B",
            page=1
        ),
        CitationItem(
            report_id="R-FAKE",
            metric="CAGR",
            value="25%"
        )
    ]
    permitted = {"R-101", "R-102", "R-999", "R-FAKE"}
    valid, dropped = CitationValidator.validate_citations(citations_in, permitted)

    assert len(valid) == 0
    assert len(dropped) == 2
    assert any("fabricated" in d.lower() for d in dropped)


def test_fabricated_page_number_rejected():
    """Verify page numbers exceeding report's actual page count are rejected."""
    # R-102 only has 2 pages in catalog registry
    citations_in = [
        CitationItem(
            report_id="R-102",
            metric="Market size",
            value="USD 3.87 B",
            page=99  # Fabricated page
        ),
        CitationItem(
            report_id="R-102",
            metric="Market size",
            value="USD 3.87 B",
            page=0  # Invalid non-positive page
        )
    ]
    permitted = {"R-102"}
    valid, dropped = CitationValidator.validate_citations(citations_in, permitted)

    assert len(valid) == 0
    assert len(dropped) == 2
    assert any("exceeds max pages" in d for d in dropped)
    assert any("must be positive" in d for d in dropped)


def test_citation_entitlement_restrictions():
    """Verify client cannot cite unentitled reports even if they exist in catalog."""
    citations_in = [
        CitationItem(
            report_id="R-101",  # Paid report client has NOT purchased
            metric="Market size",
            value="USD 4.21 B",
            page=1
        )
    ]
    # Client only has R-102 and R-103
    permitted = {"R-102", "R-103"}
    valid, dropped = CitationValidator.validate_citations(citations_in, permitted)

    assert len(valid) == 0
    assert len(dropped) == 1
    assert "lacks entitlement" in dropped[0]


# =====================================================================
# 2. Source-Conflict Detection & Scope Disambiguation
# =====================================================================

def test_source_conflict_detection_seed_scenario():
    """
    Verify seed scenario: R-101 ($4.21B, full system) vs R-102 ($3.87B, hardware only).
    Confirms:
    1. Divergences are detected.
    2. Scopes are explained separately.
    3. Neither value is selected as solely correct.
    4. Unresolved flag is True.
    """
    metrics = [
        {
            "report_id": "R-101",
            "metric": "Market size",
            "value": "USD 4.21 B",
            "period": "2024",
            "scope_note": "Includes hardware, software and services"
        },
        {
            "report_id": "R-102",
            "metric": "Market size",
            "value": "USD 3.87 B",
            "period": "2024",
            "scope_note": "AMR/AMI hardware only"
        },
        {
            "report_id": "R-101",
            "metric": "CAGR",
            "value": "11.2%",
            "period": "2025-2030",
            "scope_note": "Full system forecast"
        },
        {
            "report_id": "R-102",
            "metric": "CAGR",
            "value": "9.8%",
            "period": "2024-2029",
            "scope_note": "Hardware endpoints forecast"
        }
    ]
    permitted = {"R-101", "R-102"}
    conflicts = ConflictDetector.detect_conflicts(metrics=metrics, chunks=[], permitted_reports=permitted)

    assert len(conflicts) == 2
    market_conf = next(c for c in conflicts if c.metric == "Market size")
    assert "R-101" in market_conf.sources
    assert "R-102" in market_conf.sources
    assert "Methodological divergence" in market_conf.description
    assert "distinct technological" in market_conf.description
    assert market_conf.unresolved is True
    assert "Includes hardware, software and services" in market_conf.scope_differences["R-101"]
    assert "AMR/AMI hardware only" in market_conf.scope_differences["R-102"]


def test_no_leak_of_unauthorized_figures_in_conflict():
    """
    Security Test: A client without entitlement to R-101 (e.g., C-02)
    must NOT receive conflict records revealing R-101's protected figures.
    """
    metrics = [
        {
            "report_id": "R-101",
            "metric": "Market size",
            "value": "USD 4.21 B",
            "period": "2024",
            "scope_note": "Includes hardware, software and services"
        },
        {
            "report_id": "R-102",
            "metric": "Market size",
            "value": "USD 3.87 B",
            "period": "2024",
            "scope_note": "AMR/AMI hardware only"
        }
    ]
    # Client C-02 only has R-102 and R-103 (NO R-101)
    permitted_c02 = {"R-102", "R-103"}
    conflicts = ConflictDetector.detect_conflicts(metrics=metrics, chunks=[], permitted_reports=permitted_c02)

    # Must NOT detect conflict with R-101 because R-101 is forbidden for C-02
    assert len(conflicts) == 0


def test_illegal_averaging_neutralized_in_answer():
    """
    Verify that if an answer presents an averaged value (e.g. $4.04B),
    CitationValidator detects the illegal averaging and replaces it with separate cited scopes.
    """
    answer_with_illegal_avg = (
        "### Market Research Findings:\n"
        "The smart water meter market size was an average of USD 4.04 B in 2024."
    )
    citations = [
        CitationItem(report_id="R-101", metric="Market size", value="USD 4.21 B"),
        CitationItem(report_id="R-102", metric="Market size", value="USD 3.87 B")
    ]
    permitted = {"R-101", "R-102"}
    metrics = [
        {"report_id": "R-101", "metric": "Market size", "value": "USD 4.21 B"},
        {"report_id": "R-102", "metric": "Market size", "value": "USD 3.87 B"}
    ]

    revised_ans, valid_cits, conf, esc = CitationValidator.sanitize_and_revise_answer(
        answer=answer_with_illegal_avg,
        citations=citations,
        permitted_reports=permitted,
        derived_values={},
        metrics=metrics,
        chunks=[],
        conflicts=[]
    )

    # Must NOT contain the averaged 4.04 figure
    assert "4.04" not in revised_ans
    assert "USD 4.21 B" in revised_ans
    assert "USD 3.87 B" in revised_ans
    assert "must not be averaged" in revised_ans.lower() or "distinct" in revised_ans.lower()


def test_ungrounded_numerical_claims_excised():
    """
    Verify that ungrounded / hallucinated statistics are stripped from the answer,
    reducing confidence score.
    """
    answer_with_hallucination = (
        "### Market Research Findings:\n"
        "- Verified size: USD 4.21 B in 2024 from Report R-101.\n"
        "- Hallucinated figure: USD 7.85 B according to unverified blog.\n"
        "- Verified CAGR: 11.2% over forecast period.\n"
        "- Hallucinated growth: 28.5% in emerging markets."
    )
    citations = [
        CitationItem(report_id="R-101", metric="Market size", value="USD 4.21 B"),
        CitationItem(report_id="R-101", metric="CAGR", value="11.2%")
    ]
    metrics = [
        {"report_id": "R-101", "metric": "Market size", "value": "USD 4.21 B"},
        {"report_id": "R-101", "metric": "CAGR", "value": "11.2%"}
    ]
    permitted = {"R-101"}

    revised_ans, valid_cits, conf, esc = CitationValidator.sanitize_and_revise_answer(
        answer=answer_with_hallucination,
        citations=citations,
        permitted_reports=permitted,
        derived_values={},
        metrics=metrics,
        chunks=[],
        conflicts=[]
    )

    # Hallucinated figures must be excised
    assert "7.85" not in revised_ans
    assert "28.5" not in revised_ans
    # Grounded facts must remain
    assert "4.21" in revised_ans
    assert "11.2" in revised_ans
    # Confidence must reflect unsupported claims
    assert conf < 0.90


# =====================================================================
# 3. Derived Value Validation & Citation of Source Inputs
# =====================================================================

def test_derived_values_explicitly_labeled_and_cited():
    """Verify derived values cite source inputs, formulas, and assumptions."""
    derived = {
        "projected_market_size_2028": "6.44 USD Billion",
        "projected_market_size_2028_formula": "4.21 × (1 + 0.1120)^4",
        "apac_market_size_calculated": "1.60 USD Billion",
        "apac_derivation_formula": "4.21 × (38.0%)"
    }
    metrics = [
        {"report_id": "R-101", "metric": "Market size", "value": "USD 4.21 B"},
        {"report_id": "R-101", "metric": "CAGR", "value": "11.2%"},
        {"report_id": "R-101", "metric": "Regional share", "value": "38%"}
    ]
    permitted = {"R-101"}

    ground_truth = CitationValidator.collect_authorized_ground_truth(
        metrics=metrics,
        chunks=[],
        derived_values=derived,
        citations=[],
        permitted_reports=permitted
    )

    # Ground truth must recognize the calculated 6.44 and 1.60 as authorized derived values
    assert 6.44 in ground_truth["known_numbers"]
    assert 1.60 in ground_truth["known_numbers"]
    assert any("Derived Value" in s for s in ground_truth["number_sources"].get(6.44, []))


# =====================================================================
# 4. End-to-End Workflow Conflict & Citation Integration
# =====================================================================

def test_agent_workflow_c01_sees_both_scopes_with_citations(db):
    """
    Verify client C-01 (authorized for R-101 and R-102) receives both separate figures,
    with explicit citations to R-101 and R-102 and no averaging.
    """
    response = run_copilot_workflow(
        db=db,
        client_id="C-01",
        query="What is the 2024 market size for smart water meters?"
    )

    assert isinstance(response, ChatResponse)
    assert response.escalated is False
    assert len(response.citations) >= 2
    # Both sources cited
    cited_reps = {c.report_id for c in response.citations if c.report_id}
    assert "R-101" in cited_reps
    assert "R-102" in cited_reps

    # Both values present separately
    assert "4.21" in response.answer
    assert "3.87" in response.answer
    assert "4.04" not in response.answer  # No averaging

    # Conflict list populated
    assert len(response.conflicts) > 0
    assert any(c.metric == "Market size" for c in response.conflicts)


def test_agent_workflow_c02_entitlement_boundary_no_r101_leak(db):
    """
    Verify client C-02 (authorized ONLY for R-103 and public R-102)
    does NOT see R-101 figures in answers, citations, or conflict records.
    """
    response = run_copilot_workflow(
        db=db,
        client_id="C-02",
        query="What is the 2024 market size for smart water meters?"
    )

    assert isinstance(response, ChatResponse)
    # C-02 must see R-102's figure ($3.87B, hardware only)
    assert "3.87" in response.answer

    # C-02 must NOT see R-101's protected figure ($4.21B)
    assert "4.21" not in response.answer
    for c in response.citations:
        assert c.report_id != "R-101"

    # Conflicts field for C-02 must NOT mention R-101
    for conf in response.conflicts:
        assert "R-101" not in conf.sources
        assert "4.21" not in conf.description
