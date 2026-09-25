from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent

ROOT = HERE.parent.parent

OUTPUT_DIR = ROOT / "v2" / "outputs"

BUILDER_FILE = (
    HERE
    / "GraphRAG_Phase3_StepV2_08_METRICS_SNAPSHOT_01_builder.py"
)


def load_module(name, path):

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"CANNOT_LOAD:{path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


builder = load_module(
    "v2_08_snapshot_builder",
    BUILDER_FILE,
)


metrics = {
    "guardrail_pass_rate": None,
    "retry_rate": 0.5,
    "retry_recovery_rate": 0.5,
    "escalation_rate": 0.25,
    "missing_evidence_rate": None,
    "citation_mismatch_rate": None,
    "provenance_failure_rate": None,
    "unknown_span_rate": None,
    "provider_schema_failure_rate": None,
    "judge_rejection_rate": 0.333333,
    "false_positive_guardrail_rate": None,
    "p95_latency_ms": 400.0,
    "cost_per_governed_query": None,
}


snapshot = builder.build_snapshot(
    metrics,
    source_name="STEP V2-08D-05 Combined E2E",
)


json_path = (
    OUTPUT_DIR
    / "GraphRAG_AWS_V2_StepV2-08E_Governance_Metrics_Snapshot.json"
)

csv_path = (
    OUTPUT_DIR
    / "GraphRAG_AWS_V2_StepV2-08E_Governance_Metrics_Snapshot.csv"
)


builder.write_snapshot(
    snapshot,
    json_path,
    csv_path,
)


print("")
print("=" * 72)
print("STEP V2-08E-01")
print("GOVERNANCE METRICS SNAPSHOT")
print("=" * 72)

print("")
print("METRIC COUNT :", snapshot["metric_count"])


available = 0
not_available = 0
signal_required = 0
evaluation_required = 0


print("")
print("===== METRIC SNAPSHOT =====")

for row in snapshot["metrics"]:

    print(
        f"{row['metric']:32} "
        f"VALUE={str(row['value']):10} "
        f"STATUS={row['status']}"
    )

    if row["status"] == "AVAILABLE":
        available += 1

    elif row["status"] == "SIGNAL_REQUIRED":
        signal_required += 1

    elif row["status"] == "EVALUATION_DATA_REQUIRED":
        evaluation_required += 1

    else:
        not_available += 1


print("")
print("===== COVERAGE =====")

print("AVAILABLE                :", available)
print("NOT AVAILABLE            :", not_available)
print("SIGNAL REQUIRED          :", signal_required)
print("EVALUATION DATA REQUIRED :", evaluation_required)
print("TOTAL                    :", snapshot["metric_count"])


print("")
print("===== SAFETY CHECKS =====")

citation = next(
    row
    for row in snapshot["metrics"]
    if row["metric_key"]
    == "citation_mismatch_rate"
)

cost = next(
    row
    for row in snapshot["metrics"]
    if row["metric_key"]
    == "cost_per_governed_query"
)

false_positive = next(
    row
    for row in snapshot["metrics"]
    if row["metric_key"]
    == "false_positive_guardrail_rate"
)


citation_safe = (
    citation["value"] is None
    and citation["status"]
        == "SIGNAL_REQUIRED"
)

cost_safe = (
    cost["value"] is None
    and cost["status"]
        == "SIGNAL_REQUIRED"
)

false_positive_safe = (
    false_positive["value"] is None
    and false_positive["status"]
        == "EVALUATION_DATA_REQUIRED"
)


print(
    "CITATION MISMATCH NOT INVENTED :",
    "PASS" if citation_safe else "FAIL",
)

print(
    "COST NOT INVENTED              :",
    "PASS" if cost_safe else "FAIL",
)

print(
    "FALSE POSITIVE NOT INVENTED    :",
    "PASS" if false_positive_safe else "FAIL",
)


print("")
print("===== OUTPUT FILES =====")

print("JSON :", json_path)
print("CSV  :", csv_path)

print(
    "JSON EXISTS :",
    json_path.exists(),
)

print(
    "CSV EXISTS  :",
    csv_path.exists(),
)


passed = (
    snapshot["metric_count"] == 13
    and available == 5
    and not_available == 5
    and signal_required == 2
    and evaluation_required == 1
    and citation_safe
    and cost_safe
    and false_positive_safe
    and json_path.exists()
    and csv_path.exists()
)


print("")
print("===== FINAL GATE =====")

if passed:

    print("STEP V2-08E-01: PASS")
    print("13-METRIC SNAPSHOT: PASS")
    print("AVAILABLE METRICS: 5")
    print("UNAVAILABLE SIGNAL SAFETY: PASS")
    print("JSON SNAPSHOT: PASS")
    print("CSV SNAPSHOT: PASS")

else:

    print("STEP V2-08E-01: BLOCKED")

    raise SystemExit(1)