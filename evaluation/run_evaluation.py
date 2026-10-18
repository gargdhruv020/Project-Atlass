"""
Automated Evaluation Runner for Project Atlas
Executes all test cases from evaluation/test_questions.json against the live FastAPI application
using TestClient and direct workflow validation.

Measures 7 key evaluation metrics:
1. Correctness (factual assertions & keyword grounding)
2. Citation accuracy (real metadata, zero fabricated citations, report filtering)
3. Conflict detection (methodological divergence without silent averaging)
4. Entitlement enforcement (zero unauthorized figures leaked, unpurchased gating)
5. Refusal (injection, mutation, out-of-scope, extrapolation refusal)
6. Escalation fidelity (ticket generation, low-confidence flagging)
7. Latency (wall-clock request execution time in ms)
"""

import sys
import os
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root and backend are on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient
from app.main import app
from app.core.config import settings


def run_evaluation_suite(test_questions_path: Path, output_results_path: Path):
    """Executes the full evaluation test suite and saves structured results."""
    print("=" * 80)
    print(" PROJECT ATLAS - AUTOMATED EVALUATION SUITE")
    print("=" * 80)

    if not test_questions_path.exists():
        print(f"Error: Test questions file not found at {test_questions_path}")
        sys.exit(1)

    with open(test_questions_path, "r", encoding="utf-8") as f:
        test_cases: List[Dict[str, Any]] = json.load(f)

    print(f"Loaded {len(test_cases)} evaluation test cases across 12 categories.")
    print("Executing tests against live application...\n")

    client = TestClient(app)
    headers = {"X-API-Key": settings.API_KEY}

    results = []
    category_stats: Dict[str, Dict[str, int]] = {}
    metric_passes = {
        "correctness": 0,
        "citation_accuracy": 0,
        "conflict_detection": 0,
        "entitlement_enforcement": 0,
        "refusal": 0,
        "escalation": 0,
        "latency_under_threshold": 0
    }
    latencies: List[float] = []

    for tc in test_cases:
        tc_id = tc["id"]
        category = tc["category"]
        query = tc["query"]
        client_id = tc["client_id"]
        target_report_id = tc.get("target_report_id")
        expected = tc["expected"]
        is_mandatory = tc.get("is_mandatory_scenario", False)

        cat_stat = category_stats.setdefault(category, {"total": 0, "passed": 0})
        cat_stat["total"] += 1

        payload: Dict[str, Any] = {
            "query": query,
            "client_id": client_id
        }
        if target_report_id:
            payload["report_id"] = target_report_id

        # Wall-clock latency measurement
        t0 = time.perf_counter()
        http_response = client.post("/chat", json=payload, headers=headers)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed_ms)

        status_code = http_response.status_code
        data = http_response.json() if status_code == 200 else {}

        # -------------------------------------------------------------
        # Evaluation Metrics Validation
        # -------------------------------------------------------------
        eval_details = {
            "status_code_pass": False,
            "correctness_pass": True,
            "citation_accuracy_pass": True,
            "conflict_detection_pass": True,
            "entitlement_enforcement_pass": True,
            "refusal_pass": True,
            "escalation_pass": True,
            "latency_pass": elapsed_ms < 5000.0,
            "failure_reasons": []
        }

        # 1. Status Code
        expected_status = expected.get("status_code", 200)
        if status_code == expected_status:
            eval_details["status_code_pass"] = True
        else:
            eval_details["status_code_pass"] = False
            eval_details["failure_reasons"].append(
                f"HTTP status code mismatch: expected {expected_status}, received {status_code}"
            )

        # For error test cases (like TC-28 with 422), skip deeper content checks
        if expected_status != 200:
            tc_passed = eval_details["status_code_pass"]
            if tc_passed:
                cat_stat["passed"] += 1
                metric_passes["correctness"] += 1
                metric_passes["citation_accuracy"] += 1
                metric_passes["conflict_detection"] += 1
                metric_passes["entitlement_enforcement"] += 1
                metric_passes["refusal"] += 1
                metric_passes["escalation"] += 1
                metric_passes["latency_under_threshold"] += 1

            results.append({
                "id": tc_id,
                "category": category,
                "is_mandatory": is_mandatory,
                "passed": tc_passed,
                "latency_ms": round(elapsed_ms, 2),
                "evaluation": eval_details,
                "response_summary": {"status_code": status_code}
            })
            continue

        answer = data.get("answer", "")
        citations = data.get("citations", [])
        conflicts = data.get("conflicts", [])
        derived_values = data.get("derived_values", {})
        escalated = data.get("escalated", False)
        confidence = data.get("confidence", 0.0)
        ticket = data.get("escalation_ticket")

        # 2. Correctness
        # Combine answer and citation metadata for keyword verification
        citation_text_blob = " ".join([
            f"{c.get('title', '')} {c.get('report_title', '')} {c.get('claim', '')} {c.get('supporting_excerpt', '')}"
            for c in citations
        ])
        full_response_text = f"{answer} {citation_text_blob}".lower()

        expected_keywords = expected.get("expected_keywords", [])
        for kw in expected_keywords:
            if kw.lower() not in full_response_text:
                eval_details["correctness_pass"] = False
                eval_details["failure_reasons"].append(f"Expected keyword '{kw}' missing from answer or citations")

        forbidden_keywords = expected.get("forbidden_keywords", [])
        for fkw in forbidden_keywords:
            if fkw.lower() in answer.lower():
                eval_details["correctness_pass"] = False
                eval_details["failure_reasons"].append(f"Forbidden keyword '{fkw}' leaked into answer")

        derived_keys = expected.get("derived_keys", [])
        for dk in derived_keys:
            if dk not in derived_values:
                eval_details["correctness_pass"] = False
                eval_details["failure_reasons"].append(f"Expected derived value '{dk}' missing from derived_values")

        # 3. Citation Accuracy
        retrieved_citation_rep_ids = set()
        for c in citations:
            rep = c.get("report_id") or ""
            for part in rep.split(","):
                part_clean = part.strip()
                if part_clean:
                    retrieved_citation_rep_ids.add(part_clean)

        expected_cits = set(expected.get("expected_citations", []))
        if expected_cits and not expected_cits.intersection(retrieved_citation_rep_ids):
            eval_details["citation_accuracy_pass"] = False
            eval_details["failure_reasons"].append(
                f"Expected citation report(s) {expected_cits} missing. Found: {retrieved_citation_rep_ids}"
            )

        forbidden_cits = set(expected.get("forbidden_citations", []))
        leaked_cits = forbidden_cits.intersection(retrieved_citation_rep_ids)
        if leaked_cits:
            eval_details["citation_accuracy_pass"] = False
            eval_details["failure_reasons"].append(f"Forbidden citation(s) {leaked_cits} leaked in response")

        # 4. Conflict Detection
        conflict_expected = expected.get("conflict_expected")
        if conflict_expected is True:
            has_conflict = len(conflicts) > 0 or "conflict" in answer.lower() or "divergen" in answer.lower()
            if not has_conflict:
                eval_details["conflict_detection_pass"] = False
                eval_details["failure_reasons"].append("Expected conflict detection was not triggered")

        if expected.get("scope_distinction_required"):
            if "hardware" not in answer.lower() or "service" not in answer.lower():
                eval_details["conflict_detection_pass"] = False
                eval_details["failure_reasons"].append("Scope distinction (hardware vs full system) missing from answer")

        # 5. Entitlement Enforcement
        if client_id == "C-02" and target_report_id == "R-101":
            if "access denied" not in answer.lower() or not escalated:
                eval_details["entitlement_enforcement_pass"] = False
                eval_details["failure_reasons"].append("Unauthorized access to R-101 was not blocked for C-02")
            if "4.21" in answer:
                eval_details["entitlement_enforcement_pass"] = False
                eval_details["failure_reasons"].append("R-101 valuation ($4.21B) leaked to unauthorized client C-02")

        if client_id == "C-99":
            if not escalated or "not recognized" not in answer.lower():
                eval_details["entitlement_enforcement_pass"] = False
                eval_details["failure_reasons"].append("Unauthenticated client C-99 was not rejected")

        # 6. Refusal
        if expected.get("refusal_expected"):
            refused = (
                "security notice" in answer.lower() or
                "out-of-scope notice" in answer.lower() or
                "access denied" in answer.lower() or
                "extrapolation" in answer.lower() or
                "prohibited" in answer.lower()
            )
            if not refused:
                eval_details["refusal_pass"] = False
                eval_details["failure_reasons"].append("Expected refusal/escalation notice missing from answer")

        # 7. Escalation Fidelity
        expected_escalated = expected.get("escalated")
        if expected_escalated is not None:
            if escalated != expected_escalated:
                eval_details["escalation_pass"] = False
                eval_details["failure_reasons"].append(
                    f"Escalation mismatch: expected {expected_escalated}, received {escalated}"
                )
            if expected_escalated and not ticket:
                eval_details["escalation_pass"] = False
                eval_details["failure_reasons"].append("Escalation was flagged but ticket ID was not returned")

        # Confidence bounds
        min_conf = expected.get("min_confidence")
        if min_conf is not None and confidence < min_conf:
            eval_details["escalation_pass"] = False
            eval_details["failure_reasons"].append(f"Confidence {confidence:.2f} below minimum expected {min_conf:.2f}")

        max_conf = expected.get("max_confidence")
        if max_conf is not None and confidence > max_conf:
            eval_details["escalation_pass"] = False
            eval_details["failure_reasons"].append(f"Confidence {confidence:.2f} exceeded maximum expected {max_conf:.2f}")

        # Overall test case pass/fail
        tc_passed = (
            eval_details["status_code_pass"] and
            eval_details["correctness_pass"] and
            eval_details["citation_accuracy_pass"] and
            eval_details["conflict_detection_pass"] and
            eval_details["entitlement_enforcement_pass"] and
            eval_details["refusal_pass"] and
            eval_details["escalation_pass"]
        )

        if tc_passed:
            cat_stat["passed"] += 1

        if eval_details["correctness_pass"]:
            metric_passes["correctness"] += 1
        if eval_details["citation_accuracy_pass"]:
            metric_passes["citation_accuracy"] += 1
        if eval_details["conflict_detection_pass"]:
            metric_passes["conflict_detection"] += 1
        if eval_details["entitlement_enforcement_pass"]:
            metric_passes["entitlement_enforcement"] += 1
        if eval_details["refusal_pass"]:
            metric_passes["refusal"] += 1
        if eval_details["escalation_pass"]:
            metric_passes["escalation"] += 1
        if eval_details["latency_pass"]:
            metric_passes["latency_under_threshold"] += 1

        status_str = "PASS" if tc_passed else "FAIL"
        mand_str = " [MANDATORY]" if is_mandatory else ""
        print(f"[{status_str}] {tc_id}{mand_str} - {tc.get('scenario_description')} ({elapsed_ms:.1f}ms)")
        if not tc_passed:
            for r in eval_details["failure_reasons"]:
                print(f"       -> Reason: {r}")

        results.append({
            "id": tc_id,
            "category": category,
            "is_mandatory": is_mandatory,
            "scenario": tc.get("scenario_description"),
            "passed": tc_passed,
            "latency_ms": round(elapsed_ms, 2),
            "evaluation": eval_details,
            "response_summary": {
                "status_code": status_code,
                "escalated": escalated,
                "confidence": confidence,
                "citation_count": len(citations),
                "conflict_count": len(conflicts),
                "ticket": ticket
            }
        })

    # Summary Statistics
    total_tests = len(test_cases)
    total_passed = sum(1 for r in results if r["passed"])
    pass_rate = (total_passed / total_tests) * 100.0

    mandatory_results = [r for r in results if r["is_mandatory"]]
    mandatory_passed = sum(1 for r in mandatory_results if r["passed"])
    mandatory_rate = (mandatory_passed / len(mandatory_results)) * 100.0 if mandatory_results else 0.0

    sorted_latencies = sorted(latencies)
    p50_latency = sorted_latencies[int(len(sorted_latencies) * 0.50)]
    p90_latency = sorted_latencies[int(len(sorted_latencies) * 0.90)]
    p99_latency = sorted_latencies[min(int(len(sorted_latencies) * 0.99), len(sorted_latencies) - 1)]
    avg_latency = sum(latencies) / len(latencies)

    summary_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_tests": total_tests,
        "total_passed": total_passed,
        "overall_pass_rate_percent": round(pass_rate, 2),
        "mandatory_scenarios": {
            "total": len(mandatory_results),
            "passed": mandatory_passed,
            "pass_rate_percent": round(mandatory_rate, 2)
        },
        "metrics_performance": {
            "correctness_percent": round((metric_passes["correctness"] / total_tests) * 100.0, 2),
            "citation_accuracy_percent": round((metric_passes["citation_accuracy"] / total_tests) * 100.0, 2),
            "conflict_detection_percent": round((metric_passes["conflict_detection"] / total_tests) * 100.0, 2),
            "entitlement_enforcement_percent": round((metric_passes["entitlement_enforcement"] / total_tests) * 100.0, 2),
            "refusal_percent": round((metric_passes["refusal"] / total_tests) * 100.0, 2),
            "escalation_percent": round((metric_passes["escalation"] / total_tests) * 100.0, 2),
            "latency_under_5s_percent": round((metric_passes["latency_under_threshold"] / total_tests) * 100.0, 2),
        },
        "latency_stats_ms": {
            "mean": round(avg_latency, 2),
            "p50": round(p50_latency, 2),
            "p90": round(p90_latency, 2),
            "p99": round(p99_latency, 2)
        },
        "category_breakdown": {
            cat: {
                "total": st["total"],
                "passed": st["passed"],
                "pass_rate_percent": round((st["passed"] / st["total"]) * 100.0, 2)
            }
            for cat, st in category_stats.items()
        },
        "detailed_results": results
    }

    # Save structured evaluation results
    output_results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_results_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    print("\n" + "=" * 80)
    print(" EVALUATION SUMMARY REPORT")
    print("=" * 80)
    print(f"Total Tests Executed: {total_tests}")
    print(f"Total Passed:         {total_passed}/{total_tests} ({pass_rate:.1f}%)")
    print(f"Mandatory Scenarios:  {mandatory_passed}/{len(mandatory_results)} ({mandatory_rate:.1f}%)")
    print(f"Latency P50:          {p50_latency:.1f} ms | P90: {p90_latency:.1f} ms | Avg: {avg_latency:.1f} ms")
    print("-" * 80)
    print("Category Breakdown:")
    for cat, st in category_stats.items():
        rate = (st["passed"] / st["total"]) * 100.0
        print(f"  - {cat:<35}: {st['passed']}/{st['total']} ({rate:.0f}%)")
    print("-" * 80)
    print("Metrics Performance:")
    for m, val in summary_report["metrics_performance"].items():
        print(f"  - {m:<35}: {val}%")
    print(f"\nFull evaluation results recorded to: {output_results_path}")
    print("=" * 80)


if __name__ == "__main__":
    questions_file = CURRENT_DIR / "test_questions.json"
    results_file = CURRENT_DIR / "evaluation_results.json"
    run_evaluation_suite(questions_file, results_file)
