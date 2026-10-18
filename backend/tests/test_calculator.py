"""
Unit and Integration Tests for Deterministic Market Intelligence Calculator
Tests CAGR compounding projections, forecast window enforcement, silent extrapolation refusal,
scope disambiguation between R-101 and R-102, and input validation.
"""

import pytest
from app.tools.calculator import MarketCalculator, REPORT_FORECAST_WINDOWS
from app.agents.workflow import run_copilot_workflow
from app.schemas.chat import ChatResponse


# =====================================================================
# 1. Core Mathematical Projections & Compounding Periods
# =====================================================================

def test_cagr_projection_standard_calculation():
    """Verify standard CAGR projection matches exact mathematical formula: V * (1 + r)^n."""
    # R-101 baseline: $4.21B in 2024 at 11.2% CAGR for 4 years to 2028
    # 4.21 * (1 + 0.112)^4 = 4.21 * 1.52928 = 6.4382... -> 6.44
    res = MarketCalculator.project_cagr(
        base_value=4.21,
        base_year=2024,
        target_year=2028,
        cagr_percent=11.2,
        unit="USD Billion",
        report_id="R-101"
    )

    assert "error" not in res
    assert res["projected_value"] == 6.44
    assert res["delta_years"] == 4
    assert res["compounding_periods"] == 4
    assert res["cagr_percent"] == 11.2
    assert res["cagr_decimal"] == 0.112
    assert res["is_derived_estimate"] is True
    assert res["label"] == "Derived Estimate"
    assert res["units"] == "USD Billion"
    assert "6.44 USD Billion" in res["formatted_result"]
    assert "4.21 × (1 + 0.1120)^4" in res["derivation_formula"]
    assert "Future Value = Base Value × (1 + CAGR)^n" in res["verbose_formula"]
    assert res["quoted_source_value"] == "4.21 USD Billion (2024)"
    assert res["quoted_cagr"] == "11.2%"
    assert len(res["assumptions"]) >= 4
    assert res["extrapolation_beyond_window"] is False


def test_cagr_projection_zero_growth():
    """Verify projection with 0% CAGR yields unchanged future value."""
    res = MarketCalculator.project_cagr(
        base_value=5.50,
        base_year=2024,
        target_year=2030,
        cagr_percent=0.0,
        unit="USD Billion"
    )
    assert "error" not in res
    assert res["projected_value"] == 5.50
    assert res["delta_years"] == 6
    assert "5.50 USD Billion" in res["formatted_result"]


def test_cagr_projection_single_and_multi_period():
    """Verify calculations for 1, 2, and 5 compounding periods."""
    base = 10.0
    cagr = 10.0  # 10%

    # n = 1: 10.0 * 1.10 = 11.00
    res_1 = MarketCalculator.project_cagr(base_value=base, base_year=2024, target_year=2025, cagr_percent=cagr)
    assert res_1["projected_value"] == 11.00
    assert res_1["delta_years"] == 1

    # n = 2: 10.0 * (1.10)^2 = 12.10
    res_2 = MarketCalculator.project_cagr(base_value=base, base_year=2024, target_year=2026, cagr_percent=cagr)
    assert res_2["projected_value"] == 12.10
    assert res_2["delta_years"] == 2

    # n = 5: 10.0 * (1.10)^5 = 10.0 * 1.61051 = 16.11
    res_5 = MarketCalculator.project_cagr(base_value=base, base_year=2024, target_year=2029, cagr_percent=cagr)
    assert res_5["projected_value"] == 16.11
    assert res_5["delta_years"] == 5


def test_cagr_decimal_and_percentage_equivalence():
    """Verify supplying cagr_decimal=0.112 produces identical results to cagr_percent=11.2."""
    res_pct = MarketCalculator.project_cagr(
        base_value=4.21, base_year=2024, target_year=2028, cagr_percent=11.2
    )
    res_dec = MarketCalculator.project_cagr(
        base_value=4.21, base_year=2024, target_year=2028, cagr_decimal=0.112
    )

    assert res_pct["projected_value"] == res_dec["projected_value"]
    assert res_pct["derivation_formula"] == res_dec["derivation_formula"]
    assert res_pct["cagr_percent"] == res_dec["cagr_percent"]


def test_cagr_negative_growth_market_contraction():
    """Verify negative CAGR handles market contraction correctly."""
    # Market size $10.0B contracting at -5.0% annually for 2 years:
    # 10.0 * (1 - 0.05)^2 = 10.0 * 0.9025 = 9.03
    res = MarketCalculator.project_cagr(
        base_value=10.0,
        base_year=2024,
        target_year=2026,
        cagr_percent=-5.0
    )
    assert "error" not in res
    assert res["projected_value"] == 9.03
    assert res["cagr_percent"] == -5.0


# =====================================================================
# 2. Input Validation & Boundary Checking
# =====================================================================

def test_input_validation_invalid_numeric_values():
    """Verify non-numeric and negative/zero base values are strictly rejected."""
    # Non-numeric base value string
    res1 = MarketCalculator.project_cagr(base_value="not_a_number", base_year=2024, target_year=2028, cagr_percent=10.0)
    assert "error" in res1
    assert res1["validation_error"] is True

    # Negative base value
    res2 = MarketCalculator.project_cagr(base_value=-4.21, base_year=2024, target_year=2028, cagr_percent=10.0)
    assert "error" in res2
    assert "positive" in res2["error"].lower() or ">=" in res2["error"]

    # Zero base value
    res3 = MarketCalculator.project_cagr(base_value=0.0, base_year=2024, target_year=2028, cagr_percent=10.0)
    assert "error" in res3

    # None base value
    res4 = MarketCalculator.project_cagr(base_value=None, base_year=2024, target_year=2028, cagr_percent=10.0)
    assert "error" in res4


def test_input_validation_invalid_years_and_periods():
    """Verify target year before base year and invalid year formats are rejected."""
    # Target year before base year
    res1 = MarketCalculator.project_cagr(base_value=4.21, base_year=2024, target_year=2020, cagr_percent=11.2)
    assert "error" in res1
    assert "must be after base year" in res1["error"]

    # Non-integer fractional year
    res2 = MarketCalculator.project_cagr(base_value=4.21, base_year=2024.5, target_year=2028, cagr_percent=11.2)
    assert "error" in res2
    assert "integer" in res2["error"]

    # Out of bounds calendar year
    res3 = MarketCalculator.project_cagr(base_value=4.21, base_year=1800, target_year=2028, cagr_percent=11.2)
    assert "error" in res3


def test_input_validation_invalid_cagr_range():
    """Verify CAGR below -100% or above 1000% is rejected as economically invalid."""
    # CAGR below -100% (impossible total loss > 100%)
    res1 = MarketCalculator.project_cagr(base_value=4.21, base_year=2024, target_year=2028, cagr_percent=-150.0)
    assert "error" in res1

    # CAGR above 1000%
    res2 = MarketCalculator.project_cagr(base_value=4.21, base_year=2024, target_year=2028, cagr_percent=1500.0)
    assert "error" in res2

    # Missing both percent and decimal CAGR
    res3 = MarketCalculator.project_cagr(base_value=4.21, base_year=2024, target_year=2028)
    assert "error" in res3


# =====================================================================
# 3. Forecast Window Enforcement & Silent Extrapolation Refusal
# =====================================================================

def test_forecast_window_refusal_for_r101():
    """Verify tool refuses silent extrapolation when target year exceeds R-101 window (2024-2030)."""
    # R-101 verified window ends in 2030. Querying 2032 must be refused.
    res = MarketCalculator.project_cagr(
        base_value=4.21,
        base_year=2024,
        target_year=2032,
        cagr_percent=11.2,
        report_id="R-101",
        allow_extrapolation=False
    )

    assert "error" in res
    assert res["extrapolation_beyond_window"] is True
    assert res["requires_escalation"] is True
    assert "Silent extrapolation beyond published research methodology is prohibited" in res["refusal_reason"]
    assert res["max_forecast_year"] == 2030


def test_forecast_window_refusal_for_r102():
    """Verify tool refuses silent extrapolation when target year exceeds R-102 window (2024-2029)."""
    # R-102 verified window ends in 2029. Querying 2030 must be refused.
    res = MarketCalculator.project_cagr(
        base_value=3.87,
        base_year=2024,
        target_year=2030,
        cagr_percent=9.8,
        report_id="R-102",
        allow_extrapolation=False
    )

    assert "error" in res
    assert res["extrapolation_beyond_window"] is True
    assert res["requires_escalation"] is True
    assert res["max_forecast_year"] == 2029


def test_forecast_window_allowed_with_explicit_warning():
    """Verify tool allows calculation only when allow_extrapolation=True with clear warnings."""
    res = MarketCalculator.project_cagr(
        base_value=4.21,
        base_year=2024,
        target_year=2032,
        cagr_percent=11.2,
        report_id="R-101",
        allow_extrapolation=True
    )

    assert "error" not in res
    assert res["extrapolation_beyond_window"] is True
    assert res["requires_escalation"] is True
    assert res["extrapolation_warning"] is not None
    assert any("Extrapolated beyond" in a for a in res["assumptions"])


# =====================================================================
# 4. Multi-Report Disambiguation & Ambiguity Detection
# =====================================================================

def test_multi_report_disambiguation_r101_and_r102():
    """Verify tool does not arbitrarily pick R-101 vs R-102 when both are retrieved."""
    metrics = [
        {"report_id": "R-101", "metric": "Market size", "region": "Global", "period": "2024", "value": "USD 4.21 B", "scope_note": "Includes hardware, software and services"},
        {"report_id": "R-101", "metric": "CAGR", "region": "Global", "period": "2025-2030", "value": "11.2%", "scope_note": "Forecast period stated as 2025-2030"},
        {"report_id": "R-102", "metric": "Market size", "region": "Global", "period": "2024", "value": "USD 3.87 B", "scope_note": "AMR/AMI hardware only"},
        {"report_id": "R-102", "metric": "CAGR", "region": "Global", "period": "2024-2029", "value": "9.8%", "scope_note": "Different forecast window from R-101"},
    ]

    query = "What is the projected smart water meter market size in 2028?"
    eval_res = MarketCalculator.evaluate_projection_query(query=query, metrics=metrics)

    # Must provide projections for BOTH reports rather than arbitrarily selecting one
    assert "projected_market_size_R-101_2028" in eval_res
    assert "projected_market_size_R-102_2028" in eval_res
    assert "6.44 USD Billion" in eval_res["projected_market_size_R-101_2028"]
    # 3.87 * (1 + 0.098)^4 = 3.87 * 1.45348 = 5.62 USD Billion
    assert "5.62 USD Billion" in eval_res["projected_market_size_R-102_2028"]

    # Scope comparison must explain the methodological difference
    assert "scope_comparison" in eval_res
    assert "Multiple market reports cover this sector" in eval_res["scope_comparison"]


def test_missing_target_year_ambiguity_detection():
    """Verify query without a clear target year flags missing parameter ambiguity."""
    metrics = [
        {"report_id": "R-101", "metric": "Market size", "region": "Global", "period": "2024", "value": "USD 4.21 B"},
        {"report_id": "R-101", "metric": "CAGR", "region": "Global", "period": "2025-2030", "value": "11.2%"},
    ]
    query = "What will the smart water meter market size grow to in the future?"
    eval_res = MarketCalculator.evaluate_projection_query(query=query, metrics=metrics)

    assert eval_res.get("target_year_missing") is True
    assert "ambiguity_notice" in eval_res
    assert "target forecast year was not specified" in eval_res["ambiguity_notice"].lower()


# =====================================================================
# 5. Regional Share Derivations
# =====================================================================

def test_regional_share_calculation_and_validation():
    """Verify regional share calculation and percentage bounds checking."""
    # 4.21 * 38% = 1.60
    res = MarketCalculator.calculate_regional_share(
        global_size=4.21,
        share_percent=38.0,
        region="APAC",
        unit="USD Billion",
        report_id="R-101"
    )
    assert "error" not in res
    assert res["calculated_size"] == 1.60
    assert "1.60 USD Billion" in res["formatted_result"]
    assert res["is_derived_estimate"] is True
    assert len(res["assumptions"]) >= 3

    # Reject invalid percentage (> 100%)
    res_inv = MarketCalculator.calculate_regional_share(global_size=4.21, share_percent=120.0)
    assert "error" in res_inv
    assert res_inv["validation_error"] is True


# =====================================================================
# 6. End-to-End Workflow Integration with Refusal & Escalation
# =====================================================================

def test_agent_workflow_extrapolation_refusal_escalates(db):
    """Verify asking for projection beyond report window triggers escalation instead of silent calculation."""
    # R-101 window ends in 2030. Querying for 2035 must be refused and escalated.
    response = run_copilot_workflow(
        db=db,
        client_id="C-01",
        query="Project the smart water meter market size to 2035 using R-101",
        report_id="R-101"
    )

    assert isinstance(response, ChatResponse)
    assert response.escalated is True
    assert response.escalation_ticket is not None
    assert "extrapolation" in response.answer.lower() or "forecast window" in response.answer.lower()
