"""
Deterministic Market Intelligence Calculator Tool
Performs verified mathematical operations for CAGR forecasting, regional sizing,
and financial growth metrics without LLM estimation or floating-point drift.
"""

import re
import math
from typing import Dict, Any, Optional, Tuple


class MarketCalculator:
    """Deterministic calculator for market research projections and derivations."""

    @staticmethod
    def project_cagr(
        base_value: float,
        base_year: int,
        target_year: int,
        cagr_percent: float,
        unit: str = "USD Billion"
    ) -> Dict[str, Any]:
        """
        Calculates future market projection using standard compounding:
        V_future = V_base * (1 + r) ^ delta_t
        """
        if target_year <= base_year:
            return {
                "error": f"Target year ({target_year}) must be after base year ({base_year})."
            }
        if base_value <= 0:
            return {"error": "Base value must be positive."}

        delta_t = target_year - base_year
        rate = cagr_percent / 100.0
        projected = base_value * math.pow(1.0 + rate, delta_t)
        rounded_projected = round(projected, 2)

        formula = f"{base_value} × (1 + {rate:.4f})^{delta_t}"

        return {
            "base_value": base_value,
            "base_year": base_year,
            "target_year": target_year,
            "cagr_percent": cagr_percent,
            "delta_years": delta_t,
            "projected_value": rounded_projected,
            "formatted_result": f"{rounded_projected:.2f} {unit}",
            "derivation_formula": formula,
            "calculation_type": "cagr_future_projection"
        }

    @staticmethod
    def calculate_regional_share(
        global_size: float,
        share_percent: float,
        region: str = "Regional",
        unit: str = "USD Billion"
    ) -> Dict[str, Any]:
        """
        Calculates implied regional market size from global size and percentage share:
        V_regional = V_global * (share / 100)
        """
        if global_size <= 0:
            return {"error": "Global size must be positive."}
        if share_percent < 0 or share_percent > 100:
            return {"error": "Share percentage must be between 0 and 100."}

        fraction = share_percent / 100.0
        regional_size = round(global_size * fraction, 2)
        formula = f"{global_size} × ({share_percent}%)"

        return {
            "global_size": global_size,
            "share_percent": share_percent,
            "region": region,
            "calculated_size": regional_size,
            "formatted_result": f"{regional_size:.2f} {unit}",
            "derivation_formula": formula,
            "calculation_type": "regional_implied_market_size"
        }

    @classmethod
    def evaluate_projection_query(
        cls,
        query: str,
        metrics: list
    ) -> Dict[str, Any]:
        """
        Extracts projection target from query and applies calculation against retrieved metrics.
        """
        results: Dict[str, Any] = {}

        # 1. Check for target year in query (e.g., "project to 2028", "market size in 2030")
        year_match = re.search(r"\b(202[6-9]|203[0-5])\b", query)
        target_year = int(year_match.group(1)) if year_match else None

        # Look for base size and CAGR in retrieved metrics
        base_size = None
        base_year = None
        cagr_rate = None

        for m in metrics:
            val_str = str(m.get("value") or "")
            metric_name = (m.get("metric") or "").lower()

            if "market size" in metric_name and base_size is None:
                num_match = re.search(r"(\d+\.?\d*)", val_str)
                period_match = re.search(r"\b(202[0-9])\b", str(m.get("period") or ""))
                if num_match:
                    base_size = float(num_match.group(1))
                    base_year = int(period_match.group(1)) if period_match else 2024

            if "cagr" in metric_name and cagr_rate is None:
                rate_match = re.search(r"(\d+\.?\d*)%", val_str)
                if rate_match:
                    cagr_rate = float(rate_match.group(1))

        if target_year and base_size and cagr_rate:
            proj = cls.project_cagr(
                base_value=base_size,
                base_year=base_year or 2024,
                target_year=target_year,
                cagr_percent=cagr_rate,
                unit="USD Billion"
            )
            if "error" not in proj:
                key = f"projected_market_size_{target_year}"
                results[key] = proj["formatted_result"]
                results[f"{key}_formula"] = proj["derivation_formula"]

        # 2. Check for regional share derivation
        global_size = None
        apac_share = None
        for m in metrics:
            metric_name = (m.get("metric") or "").lower()
            region = m.get("region")
            val_str = str(m.get("value") or "")

            if "market size" in metric_name and region == "Global":
                num_match = re.search(r"(\d+\.?\d*)", val_str)
                if num_match:
                    global_size = float(num_match.group(1))

            if "share" in metric_name and region == "APAC":
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
