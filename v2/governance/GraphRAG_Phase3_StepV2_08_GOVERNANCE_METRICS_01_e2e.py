from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(name, filename):

    path = HERE / filename

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


resilience_mod = load(
    "v2_resilience_adapter",
    "GraphRAG_Phase3_StepV2_08_RECORD_ADAPTER_01_query.py",
)

governance_mod = load(
    "v2_governance_adapter",
    "GraphRAG_Phase3_StepV2_08_GOVERNANCE_ADAPTER_01_state.py",
)

metrics_mod = load(
    "v2_metrics_engine",
    "GraphRAG_Phase3_StepV2_08_METRICS_ENGINE_01_calculator.py",
)


def ev(
    q,
    t,
    event_type,
    provider,
    latency,
    retryable=False,
    recovered=False,
):

    return {
        "schema_version": "1.0",
        "event_id":
            f"{q}-{event_type}-{provider}",
        "query_id": q,
        "trace_id": t,
        "provider": provider,
        "attempt": 1,
        "event_type": event_type,
        "retryable": retryable,
        "fallback_used": False,
        "recovered": recovered,
        "latency_ms": latency,
        "final_provider": provider,
    }


# ============================================================
# RESILIENCE EVENTS
# ============================================================

events = [

    # Q1 normal
    ev("Q001", "T001", "ATTEMPT", "openai", 100),
    ev("Q001", "T001", "SUCCESS", "openai", 100),

    # Q2 retry -> recovered
    ev("Q002", "T002", "ATTEMPT", "openai", 200),
    ev(
        "Q002",
        "T002",
        "RETRYABLE_FAILURE",
        "openai",
        200,
        retryable=True,
    ),
    ev(
        "Q002",
        "T002",
        "SUCCESS",
        "openai",
        200,
        recovered=True,
    ),

    # Q3 retry -> no recovery
    ev("Q003", "T003", "ATTEMPT", "openai", 300),
    ev(
        "Q003",
        "T003",
        "RETRYABLE_FAILURE",
        "openai",
        300,
        retryable=True,
    ),

    # Q4 normal resilience path
    ev("Q004", "T004", "ATTEMPT", "deepseek", 400),
    ev("Q004", "T004", "SUCCESS", "deepseek", 400),
]


# ============================================================
# GOVERNED RUNTIME STATES
# ============================================================

states = {

    "Q001": {
        "judge_allowed": True,
        "judge_verdict": "PASS",
        "final_status": "APPROVED",
    },

    "Q002": {
        "judge_allowed": True,
        "judge_verdict": "PASS",
        "final_status": "APPROVED",
    },

    "Q003": {
        "judge_allowed": True,
        "judge_verdict": "REVISE",
        "final_status": "PENDING_REVIEW",
    },

    "Q004": {
        "judge_allowed": False,
        "judge_verdict": "NOT_EVALUATED",
        "final_status": "ESCALATED",
    },
}


original_events = deepcopy(events)
original_states = deepcopy(states)


# ============================================================
# EVENT GRAIN -> QUERY GRAIN
# ============================================================

records = (
    resilience_mod.resilience_events_to_query_records(
        events
    )
)


# ============================================================
# GOVERNANCE OVERLAY
# ============================================================

for record in records:

    query_id = record["query_id"]

    if query_id not in states:
        raise RuntimeError(
            f"MISSING_GOVERNED_STATE:{query_id}"
        )

    governance_fields = (
        governance_mod.governed_state_to_metric_fields(
            states[query_id]
        )
    )

    record.update(
        governance_fields
    )


# ============================================================
# METRICS
# ============================================================

metrics = (
    metrics_mod.calculate_governance_metrics(
        records
    )
)


expected = {

    "query_count":
        4,

    "retry_rate":
        0.5,

    "retry_recovery_rate":
        0.5,

    "escalation_rate":
        0.25,

    "judge_rejection_rate":
        0.333333,

    "p95_latency_ms":
        400.0,
}


print("")
print("=" * 72)
print("STEP V2-08D-05")
print("COMBINED GOVERNANCE METRICS E2E")
print("=" * 72)


print("")
print("===== A. QUERY RECORDS =====")

for record in records:

    print("")
    print("QUERY_ID         :", record["query_id"])
    print("RETRY_USED       :", record["retry_used"])
    print("RETRY_RECOVERED  :", record["retry_recovered"])
    print("ESCALATED        :", record["escalated"])
    print("JUDGE_EXECUTED   :", record["judge_executed"])
    print("JUDGE_REJECTED   :", record["judge_rejected"])
    print("LATENCY_MS       :", record["latency_ms"])


print("")
print("===== B. GOVERNANCE METRICS =====")

for key in expected:

    print(
        f"{key:28}: {metrics[key]}"
    )


print("")
print("===== C. EXPECTED VALUE VALIDATION =====")

failures = []

for key, expected_value in expected.items():

    actual = metrics[key]

    passed = (
        actual == expected_value
    )

    print(
        f"{key:28}: "
        f"EXPECTED={expected_value} "
        f"ACTUAL={actual} "
        f"PASS={passed}"
    )

    if not passed:
        failures.append(key)


print("")
print("===== D. JUDGE DENOMINATOR VALIDATION =====")

judge_executed_count = sum(
    1
    for r in records
    if r["judge_executed"] is True
)

judge_rejected_count = sum(
    1
    for r in records
    if r["judge_rejected"] is True
)

print(
    "TOTAL QUERIES        :",
    len(records),
)

print(
    "JUDGE EXECUTED       :",
    judge_executed_count,
)

print(
    "JUDGE REJECTED       :",
    judge_rejected_count,
)

print(
    "EXPECTED RATE        : 1 / 3 = 0.333333"
)

judge_denominator_pass = (
    judge_executed_count == 3
    and judge_rejected_count == 1
    and metrics["judge_rejection_rate"]
        == 0.333333
)

print(
    "JUDGE DENOMINATOR    :",
    "PASS"
    if judge_denominator_pass
    else "FAIL",
)


print("")
print("===== E. UNPROVEN SIGNAL SAFETY =====")

safe_fields = [
    "evidence_required",
    "missing_evidence",
    "provenance_evaluated",
    "provenance_failed",
    "span_evaluated",
    "unknown_span",
]

unproven_safe = all(
    record.get(field) is None
    for record in records
    for field in safe_fields
)

print(
    "EVIDENCE / PROVENANCE / SPAN :",
    "NOT INVENTED / PASS"
    if unproven_safe
    else "FAIL",
)


print("")
print("===== F. SOURCE IMMUTABILITY =====")

events_safe = (
    events == original_events
)

states_safe = (
    states == original_states
)

print(
    "RESILIENCE EVENTS UNCHANGED :",
    "PASS"
    if events_safe
    else "FAIL",
)

print(
    "GOVERNED STATES UNCHANGED   :",
    "PASS"
    if states_safe
    else "FAIL",
)


print("")
print("===== G. FINAL GATE =====")

passed = (
    not failures
    and judge_denominator_pass
    and unproven_safe
    and events_safe
    and states_safe
)

if passed:

    print("STEP V2-08D-05: PASS")
    print("RESILIENCE -> QUERY RECORD: PASS")
    print("GOVERNED STATE OVERLAY: PASS")
    print("RETRY RATE: PASS")
    print("RETRY RECOVERY RATE: PASS")
    print("ESCALATION RATE: PASS")
    print("JUDGE REJECTION RATE: PASS")
    print("JUDGE DENOMINATOR: PASS")
    print("P95 LATENCY: PASS")
    print("UNPROVEN SIGNAL SAFETY: PASS")
    print("SOURCE IMMUTABILITY: PASS")

else:

    print("STEP V2-08D-05: BLOCKED")
    print("FAILED METRICS:", failures)

    raise SystemExit(1)