from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent

ENGINE = (
    HERE
    / "GraphRAG_Phase3_StepV2_08_METRICS_ENGINE_01_calculator.py"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Cannot load module: {path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module

    spec.loader.exec_module(module)

    return module


engine = load_module(
    "v2_08_metrics_engine",
    ENGINE,
)


records = [
    {
        "query_id": "Q001",
        "guardrail_pass": True,
        "retry_used": False,
        "retry_recovered": False,
        "escalated": False,
        "evidence_required": True,
        "missing_evidence": False,
        "provenance_evaluated": True,
        "provenance_failed": False,
        "span_evaluated": True,
        "unknown_span": False,
        "provider_schema_evaluated": True,
        "provider_schema_failed": False,
        "judge_executed": True,
        "judge_rejected": False,
        "evaluation_known_valid": True,
        "latency_ms": 100,
    },
    {
        "query_id": "Q002",
        "guardrail_pass": True,
        "retry_used": True,
        "retry_recovered": True,
        "escalated": False,
        "evidence_required": True,
        "missing_evidence": False,
        "provenance_evaluated": True,
        "provenance_failed": False,
        "span_evaluated": True,
        "unknown_span": False,
        "provider_schema_evaluated": True,
        "provider_schema_failed": False,
        "judge_executed": True,
        "judge_rejected": True,
        "evaluation_known_valid": True,
        "latency_ms": 200,
    },
    {
        "query_id": "Q003",
        "guardrail_pass": False,
        "retry_used": True,
        "retry_recovered": False,
        "escalated": True,
        "evidence_required": True,
        "missing_evidence": True,
        "provenance_evaluated": True,
        "provenance_failed": True,
        "span_evaluated": True,
        "unknown_span": True,
        "provider_schema_evaluated": True,
        "provider_schema_failed": True,
        "judge_executed": False,
        "judge_rejected": False,
        "evaluation_known_valid": True,
        "latency_ms": 300,
    },
    {
        "query_id": "Q004",
        "guardrail_pass": True,
        "retry_used": False,
        "retry_recovered": False,
        "escalated": False,
        "evidence_required": True,
        "missing_evidence": False,
        "provenance_evaluated": True,
        "provenance_failed": False,
        "span_evaluated": True,
        "unknown_span": False,
        "provider_schema_evaluated": True,
        "provider_schema_failed": False,
        "judge_executed": True,
        "judge_rejected": False,
        "evaluation_known_valid": True,
        "latency_ms": 400,
    },
]


result = engine.calculate_governance_metrics(
    records
)


expected = {
    "query_count": 4,

    "guardrail_pass_rate": 0.75,

    "retry_rate": 0.50,

    "retry_recovery_rate": 0.50,

    "escalation_rate": 0.25,

    "missing_evidence_rate": 0.25,

    "provenance_failure_rate": 0.25,

    "unknown_span_rate": 0.25,

    "provider_schema_failure_rate": 0.25,

    "judge_rejection_rate": round(
        1 / 3,
        6,
    ),

    "false_positive_guardrail_rate": 0.25,

    "p95_latency_ms": 400.0,
}


print("")
print("=" * 64)
print("STEP V2-08D-01")
print("GOVERNANCE METRICS ENGINE DETERMINISTIC TEST")
print("=" * 64)

print("")
print("===== A. COMPUTED METRICS =====")

for key, value in result.items():
    if key != "signal_status":
        print(
            f"{key:38}: {value}"
        )


print("")
print("===== B. EXPECTED VALUE VALIDATION =====")

failures = []

for key, expected_value in expected.items():

    actual = result.get(key)

    passed = actual == expected_value

    print(
        f"{key:38}: "
        f"EXPECTED={expected_value} "
        f"ACTUAL={actual} "
        f"PASS={passed}"
    )

    if not passed:
        failures.append(key)


print("")
print("===== C. SIGNAL-GAP VALIDATION =====")

citation_gap = (
    result["citation_mismatch_rate"] is None
    and result["signal_status"][
        "citation_mismatch_rate"
    ] == "SIGNAL_REQUIRED"
)

cost_gap = (
    result["cost_per_governed_query"] is None
    and result["signal_status"][
        "cost_per_governed_query"
    ] == "SIGNAL_REQUIRED"
)

print(
    "CITATION MISMATCH SIGNAL GAP :",
    "PASS" if citation_gap else "FAIL",
)

print(
    "COST SIGNAL GAP              :",
    "PASS" if cost_gap else "FAIL",
)


print("")
print("===== D. FINAL GATE =====")

passed = (
    not failures
    and citation_gap
    and cost_gap
)

if passed:

    print("STEP V2-08D-01: PASS")
    print("METRICS ENGINE: PASS")
    print("NUMERATOR / DENOMINATOR LOGIC: PASS")
    print("P95 LATENCY LOGIC: PASS")
    print("MISSING SIGNAL HANDLING: PASS")

else:

    print("STEP V2-08D-01: BLOCKED")
    print(
        "FAILED METRICS:",
        failures,
    )

    raise SystemExit(1)