"""
Deterministic Market Intelligence Calculator Tool
Performs verified mathematical operations for CAGR forecasting, regional sizing,
and financial growth metrics without LLM estimation or floating-point drift.
"""

import re
import math
from typing import Dict, Any, Optional, List, Tuple, Union


# Verified research forecast windows and scope definitions for Project Atlas catalog
REPORT_FORECAST_WINDOWS: Dict[str, Dict[str, Any]] = {
    "R-101": {
        "title": "Global Smart Water Meter Market 2025",
        "publisher": "CMR",
        "base_year": 2024,
        "max_forecast_year": 2030,
        "cagr_percent": 11.2,
        "base_value": 4.21,
        "unit": "USD Billion",
        "scope": "Full System (Hardware, telemetry, MDMS software, and cloud utility services)",
    },
    "R-102": {
        "title": "Smart Water Metering: Industry Outlook 2024",
        "publisher": "Aquila Insights (third party)",
        "base_year": 2024,
        "max_forecast_year": 2029,
        "cagr_percent": 9.8,
        "base_value": 3.87,
        "unit": "USD Billion",
        "scope": "Physical AMR/AMI hardware endpoints only (excludes analytics and integration)",
    },
    "R-103": {
        "title": "Residential Water Purifier Market 2025",
        "publisher": "Frost & Sullivan",
        "base_year": 2024,
        "max_forecast_year": 2031,
        "cagr_percent": 7.4,
        "base_value": 9.15,
        "unit": "USD Billion",
        "scope": "Residential water purification equipment, membranes, and replacement filters",
    },
    "R-104": {
        "title": "Industrial Water Treatment Solutions 2025",
        "publisher": "Global Industry Analysts",
        "base_year": 2024,
        "max_forecast_year": 2030,
        "cagr_percent": 6.8,
        "base_value": 14.50,
        "unit": "USD Billion",
        "scope": "Industrial filtration, reverse osmosis, and chemical wastewater treatment",
    },
    "R-105": {
        "title": "Smart Irrigation Systems Outlook 2025",
        "publisher": "AgTech Research",
        "base_year": 2024,
        "max_forecast_year": 2030,
        "cagr_percent": 13.5,
        "base_value": 2.10,
        "unit": "USD Billion",
        "scope": "IoT agricultural controllers, soil sensors, and automated precision valves",
    },
    "R-106": {
        "title": "Wastewater Leak Detection Technologies 2024",
        "publisher": "HydroMetrics Advisory",
        "base_year": 2024,
        "max_forecast_year": 2029,
        "cagr_percent": 8.5,
        "base_value": 1.75,
        "unit": "USD Billion",
        "scope": "Acoustic loggers, satellite synthetic aperture radar, and pipeline telemetry",
    },
}


class MarketCalculator:
    """
    Deterministic calculator for market research projections and derivations.
    Guarantees mathematical precision, input validation, scope disambiguation,
    and strict refusal of silent extrapolation beyond verified forecast windows.
    """

    @classmethod
    def validate_numeric(
        cls,
        val: Any,
        field_name: str = "Value",
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """Validates that an input is a valid finite float within bounds."""
        if val is None:
            return False, None, f"{field_name} cannot be null/None."
        try:
            num = float(val)
        except (ValueError, TypeError):
            return False, None, f"{field_name} must be a valid numeric value, received: '{val}'."

        if math.isnan(num) or math.isinf(num):
            return False, None, f"{field_name} must be a finite number."

        if min_val is not None and num < min_val:
            return False, None, f"{field_name} must be >= {min_val}, received: {num}."

        if max_val is not None and num > max_val:
            return False, None, f"{field_name} must be <= {max_val}, received: {num}."

        return True, num, None

    @classmethod
    def validate_year(
        cls,
        year: Any,
        field_name: str = "Year"
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """Validates that an input represents a valid 4-digit calendar year."""
        if year is None:
            return False, None, f"{field_name} cannot be null/None."
        try:
            val_f = float(year)
            if not val_f.is_integer():
                return False, None, f"{field_name} must be an integer year, received: {year}."
            y_int = int(val_f)
        except (ValueError, TypeError):
            return False, None, f"{field_name} must be an integer year, received: '{year}'."

        if y_int < 1900 or y_int > 2100:
            return False, None, f"{field_name} must be between 1900 and 2100, received: {y_int}."

        return True, y_int, None

    @classmethod
    def validate_cagr(
        cls,
        cagr_percent: Optional[float] = None,
        cagr_decimal: Optional[float] = None,
    ) -> Tuple[bool, Optional[float], Optional[float], Optional[str]]:
        """
        Validates CAGR rate and ensures consistency between percentage and decimal forms.
        Enforces realistic economic boundaries (-100% to +1000%).
        """
        if cagr_percent is None and cagr_decimal is None:
            return False, None, None, "CAGR must be provided as either a percentage or decimal."

        if cagr_percent is not None:
            ok, p_val, err = cls.validate_numeric(cagr_percent, "CAGR percent", min_val=-100.0, max_val=1000.0)
            if not ok:
                return False, None, None, err
            d_val = round(p_val / 100.0, 6)
            return True, round(p_val, 4), d_val, None
        else:
            ok, d_val, err = cls.validate_numeric(cagr_decimal, "CAGR decimal", min_val=-1.0, max_val=10.0)
            if not ok:
                return False, None, None, err
            p_val = round(d_val * 100.0, 4)
            return True, p_val, round(d_val, 6), None

    @classmethod
    def project_cagr(
        cls,
        base_value: float,
        base_year: int,
        target_year: int,
        cagr_percent: Optional[float] = None,
        cagr_decimal: Optional[float] = None,
        unit: str = "USD Billion",
        report_id: Optional[str] = None,
        max_forecast_year: Optional[int] = None,
        scope_note: Optional[str] = None,
        allow_extrapolation: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculates future market projection using standard compounding:
        Future Value = Base Value × (1 + CAGR)^n

        Where:
        - Base Value is the starting market valuation (> 0).
        - CAGR is the annual compound growth rate expressed as a decimal (e.g. 11.2% -> 0.112).
        - n is the number of annual compounding periods (target_year - base_year).

        Strictly enforces forecast window constraints and refuses silent extrapolation.
        """
        # 1. Validate Base Value
        ok_base, b_val, err_base = cls.validate_numeric(base_value, "Base value", min_val=0.0001)
        if not ok_base:
            return {
                "error": err_base,
                "validation_error": True,
                "field": "base_value"
            }

        # 2. Validate Base Year & Target Year
        ok_by, b_yr, err_by = cls.validate_year(base_year, "Base year")
        if not ok_by:
            return {"error": err_by, "validation_error": True, "field": "base_year"}

        ok_ty, t_yr, err_ty = cls.validate_year(target_year, "Target year")
        if not ok_ty:
            return {"error": err_ty, "validation_error": True, "field": "target_year"}

        if t_yr < b_yr:
            return {
                "error": f"Target year ({t_yr}) must be after base year ({b_yr}).",
                "validation_error": True,
                "field": "target_year"
            }

        # 3. Validate CAGR
        ok_cagr, p_cagr, d_cagr, err_cagr = cls.validate_cagr(cagr_percent, cagr_decimal)
        if not ok_cagr:
            return {"error": err_cagr, "validation_error": True, "field": "cagr"}

        # 4. Check Forecast Window & Refuse Silent Extrapolation
        effective_max = max_forecast_year
        rep_meta = REPORT_FORECAST_WINDOWS.get(report_id, {}) if report_id else {}
        if effective_max is None and rep_meta:
            effective_max = rep_meta.get("max_forecast_year")

        is_extrapolation = False
        refusal_msg = None
        if effective_max is not None and t_yr > effective_max:
            is_extrapolation = True
            refusal_msg = (
                f"Target year ({t_yr}) extends beyond the verified forecast window ({b_yr}–{effective_max}) "
                f"of Report {report_id or 'catalog'}. Silent extrapolation beyond published research "
                f"methodology is prohibited."
            )
            if not allow_extrapolation:
                return {
                    "error": refusal_msg,
                    "extrapolation_beyond_window": True,
                    "refusal_reason": refusal_msg,
                    "requires_escalation": True,
                    "escalation_reason": refusal_msg,
                    "base_value": b_val,
                    "base_year": b_yr,
                    "target_year": t_yr,
                    "max_forecast_year": effective_max,
                    "report_id": report_id,
                    "cagr_percent": p_cagr,
                    "cagr_decimal": d_cagr,
                    "unit": unit
                }

        # 5. Calculate Projection in Python
        delta_years = t_yr - b_yr
        projected = b_val * math.pow(1.0 + d_cagr, delta_years)
        rounded_projected = round(projected, 2)

        formula = f"{b_val} × (1 + {d_cagr:.4f})^{delta_years}"
        verbose_formula = (
            f"Future Value = Base Value × (1 + CAGR)^n = "
            f"{b_val} × (1 + {d_cagr:.4f})^{delta_years} = {rounded_projected:.2f} {unit}"
        )

        resolved_scope = scope_note or rep_meta.get("scope", "Standard market scope")

        assumptions = [
            f"Compounding periods: {delta_years} annual compounding cycles ({b_yr} to {t_yr})",
            f"Constant annual growth rate (CAGR) of {p_cagr:.2f}% ({d_cagr:.4f} decimal)",
            f"Starting baseline valuation of {b_val} {unit} in year {b_yr}",
            f"Scope definition: {resolved_scope}",
            f"Source report: {report_id or 'Specified parameters'}"
        ]
        if is_extrapolation:
            assumptions.append(f"WARNING: Extrapolated beyond verified report window ({effective_max})")

        return {
            "base_value": b_val,
            "base_year": b_yr,
            "target_year": t_yr,
            "cagr_percent": p_cagr,
            "cagr_decimal": d_cagr,
            "delta_years": delta_years,
            "compounding_periods": delta_years,
            "projected_value": rounded_projected,
            "formatted_result": f"{rounded_projected:.2f} {unit}",
            "unit": unit,
            "units": unit,
            "derivation_formula": formula,
            "verbose_formula": verbose_formula,
            "calculation_type": "cagr_future_projection",
            "is_derived_estimate": True,
            "label": "Derived Estimate",
            "source_report_id": report_id,
            "quoted_source_value": f"{b_val} {unit} ({b_yr})",
            "quoted_cagr": f"{p_cagr:.1f}%",
            "scope_note": resolved_scope,
            "assumptions": assumptions,
            "extrapolation_beyond_window": is_extrapolation,
            "extrapolation_warning": refusal_msg if is_extrapolation else None,
            "requires_escalation": is_extrapolation
        }

    @classmethod
    def calculate_regional_share(
        cls,
        global_size: float,
        share_percent: float,
        region: str = "Regional",
        unit: str = "USD Billion",
        report_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates implied regional market size from global size and percentage share:
        V_regional = V_global × (share / 100)
        """
        ok_glob, g_val, err_glob = cls.validate_numeric(global_size, "Global size", min_val=0.0001)
        if not ok_glob:
            return {"error": err_glob, "validation_error": True, "field": "global_size"}

        ok_sh, s_val, err_sh = cls.validate_numeric(share_percent, "Share percentage", min_val=0.0, max_val=100.0)
        if not ok_sh:
            return {"error": err_sh, "validation_error": True, "field": "share_percent"}

        fraction = s_val / 100.0
        regional_size = round(g_val * fraction, 2)
        formula = f"{g_val} × ({s_val}%)"
        verbose_formula = (
            f"Regional Size = Global Size × (Regional Share / 100) = "
            f"{g_val} × ({s_val:.1f}%) = {regional_size:.2f} {unit}"
        )

        return {
            "global_size": g_val,
            "share_percent": s_val,
            "region": region,
            "calculated_size": regional_size,
            "formatted_result": f"{regional_size:.2f} {unit}",
            "unit": unit,
            "units": unit,
            "derivation_formula": formula,
            "verbose_formula": verbose_formula,
            "calculation_type": "regional_implied_market_size",
            "is_derived_estimate": True,
            "label": "Derived Estimate",
            "source_report_id": report_id,
            "assumptions": [
                f"Global market base valuation: {g_val} {unit}",
                f"{region} regional market share: {s_val:.1f}%",
                f"Linear proportional distribution without regional margin adjustments"
            ]
        }

    @classmethod
    def resolve_projection_ambiguity(
        cls,
        reports_data: Dict[str, Dict[str, Any]],
        target_year: int
    ) -> Dict[str, Any]:
        """
        Disambiguates between multiple eligible reports (e.g., R-101 vs R-102)
        without arbitrarily picking one. Computes projections for both distinct scopes
        and formats comparative analysis.
        """
        results: Dict[str, Any] = {}
        projections: List[Dict[str, Any]] = []

        for rep_id, data in reports_data.items():
            b_val = data.get("base_size")
            b_yr = data.get("base_year", 2024)
            cagr = data.get("cagr_rate")
            scope = data.get("scope_note") or REPORT_FORECAST_WINDOWS.get(rep_id, {}).get("scope")

            if b_val and cagr:
                proj = cls.project_cagr(
                    base_value=b_val,
                    base_year=b_yr,
                    target_year=target_year,
                    cagr_percent=cagr,
                    unit="USD Billion",
                    report_id=rep_id,
                    scope_note=scope
                )
                if "error" not in proj:
                    results[f"projected_market_size_{rep_id}_{target_year}"] = proj["formatted_result"]
                    results[f"projected_market_size_{rep_id}_{target_year}_formula"] = proj["derivation_formula"]
                    projections.append(proj)
                elif proj.get("extrapolation_beyond_window"):
                    results[f"extrapolation_refused_{rep_id}"] = proj["refusal_reason"]
                    results["requires_escalation"] = True

        if len(projections) > 1:
            # Multi-scope comparison: explain why the figures differ
            p_summaries = [
                f"{p['source_report_id']} ({'Full System' if 'R-101' in p['source_report_id'] else 'Hardware Endpoints'}): {p['formatted_result']}"
                for p in projections
            ]
            results[f"projected_market_size_{target_year}"] = " | ".join(p_summaries)
            results["scope_comparison"] = (
                "Notice: Multiple market reports cover this sector with differing methodological scopes. "
                + " | ".join([
                    f"Report {p['source_report_id']} scopes {p['scope_note']} yielding {p['formatted_result']} (CAGR {p['cagr_percent']}%)"
                    for p in projections
                ])
            )
        elif len(projections) == 1:
            p = projections[0]
            results[f"projected_market_size_{target_year}"] = p["formatted_result"]
            results[f"projected_market_size_{target_year}_formula"] = p["derivation_formula"]
            results["scope_note"] = p["scope_note"]

        return results

    @classmethod
    def evaluate_projection_query(
        cls,
        query: str,
        metrics: list,
        target_report_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extracts projection target from query and applies calculation against retrieved metrics.
        Detects ambiguities, refuses silent extrapolation beyond forecast windows,
        and provides multi-report scope disambiguation.
        """
        results: Dict[str, Any] = {}

        # 1. Target Year Extraction from query
        year_match = re.search(r"\b(202[5-9]|203[0-9]|204[0-9])\b", query)
        target_year = int(year_match.group(1)) if year_match else None

        # Check for relative periods like "in 3 years", "5-year forecast"
        if not target_year:
            rel_match = re.search(r"\b(?:in|over|next)\s+(\d+)\s+years?\b", query, re.IGNORECASE)
            if rel_match:
                target_year = 2024 + int(rel_match.group(1))

        # 2. Group metrics by report_id
        reports_data: Dict[str, Dict[str, Any]] = {}
        for m in metrics:
            rep = m.get("report_id") or "Unknown"
            if target_report_id and rep != target_report_id:
                continue

            entry = reports_data.setdefault(rep, {
                "base_size": None,
                "base_year": None,
                "cagr_rate": None,
                "scope_note": m.get("scope_note")
            })

            val_str = str(m.get("value") or "")
            metric_name = (m.get("metric") or "").lower()

            if "market size" in metric_name and entry["base_size"] is None:
                num_match = re.search(r"(\d+\.?\d*)", val_str)
                period_match = re.search(r"\b(202[0-9])\b", str(m.get("period") or ""))
                if num_match:
                    entry["base_size"] = float(num_match.group(1))
                    entry["base_year"] = int(period_match.group(1)) if period_match else 2024
                    if m.get("scope_note"):
                        entry["scope_note"] = m.get("scope_note")

            if "cagr" in metric_name and entry["cagr_rate"] is None:
                rate_match = re.search(r"(\d+\.?\d*)%", val_str)
                if rate_match:
                    entry["cagr_rate"] = float(rate_match.group(1))
                    if m.get("scope_note") and not entry.get("scope_note"):
                        entry["scope_note"] = m.get("scope_note")

        # 3. If target year found, evaluate projections
        if target_year:
            # Check for forecast window violations across reports
            extrapolations = []
            for rep_id in list(reports_data.keys()):
                window = REPORT_FORECAST_WINDOWS.get(rep_id)
                if window and target_year > window["max_forecast_year"]:
                    extrapolations.append((rep_id, window["max_forecast_year"]))

            if extrapolations and not target_report_id:
                # Target year exceeds one or more report windows
                all_exceeded = len(extrapolations) == len(reports_data)
                if all_exceeded:
                    rep_names = ", ".join([f"{r} (ends {w})" for r, w in extrapolations])
                    results["extrapolation_refused"] = True
                    results["extrapolation_beyond_window"] = True
                    results["refusal_reason"] = (
                        f"Target year ({target_year}) extends beyond the published forecast windows "
                        f"for available reports: {rep_names}. Silent extrapolation beyond published "
                        f"research methodology is prohibited."
                    )
                    results["requires_escalation"] = True
                    results["escalation_reason"] = results["refusal_reason"]
                    return results

            # Compute projections with multi-report disambiguation
            ambiguity_results = cls.resolve_projection_ambiguity(reports_data, target_year)
            results.update(ambiguity_results)
        elif any(k in query.lower() for k in ["project", "forecast", "growth", "future", "market size"]):
            # Missing target year ambiguity detection
            results["target_year_missing"] = True
            results["ambiguity_notice"] = (
                "A target forecast year was not specified in the query. "
                "Please specify a target year (e.g., 2028, 2030) to compute CAGR projections."
            )

        # 4. Check for regional share derivation
        global_size = None
        apac_share = None
        for m in metrics:
            metric_name = (m.get("metric") or "").lower()
            region = m.get("region")
            val_str = str(m.get("value") or "")

            if "market size" in metric_name and region == "Global" and global_size is None:
                num_match = re.search(r"(\d+\.?\d*)", val_str)
                if num_match:
                    global_size = float(num_match.group(1))

            if "share" in metric_name and region == "APAC" and apac_share is None:
                share_match = re.search(r"(\d+\.?\d*)%", val_str)
                if share_match:
                    apac_share = float(share_match.group(1))

        if global_size and apac_share:
            reg_calc = cls.calculate_regional_share(
                global_size=global_size,
                share_percent=apac_share,
                region="APAC",
                unit="USD Billion"
            )
            if "error" not in reg_calc:
                results["apac_market_size_calculated"] = reg_calc["formatted_result"]
                results["apac_derivation_formula"] = reg_calc["derivation_formula"]

        return results
