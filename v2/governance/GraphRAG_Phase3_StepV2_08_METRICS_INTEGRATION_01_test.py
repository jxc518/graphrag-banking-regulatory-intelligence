from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path


HERE = Path(__file__).resolve().parent

ADAPTER_FILE = (
    HERE
    / "GraphRAG_Phase3_StepV2_08_RECORD_ADAPTER_01_query.py"
)

ENGINE_FILE = (
    HERE
    / "GraphRAG_Phase3_StepV2_08_METRICS_ENGINE_01_calculator.py"
)


def load_module(name, path):

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"CANNOT_LOAD_MODULE:{path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


adapter_mod = load_module(
    "v2_08_record_adapter",
    ADAPTER_FILE,
)

engine_mod = load_module(
    "v2_08_metrics_engine",
    ENGINE_FILE,
)


# ============================================================
# VERIFY REAL INTERFACE
# ============================================================

if not hasattr(
    adapter_mod,
    "resilience_events_to_query_records",
):
    raise RuntimeError(
        "REAL_ADAPTER_FUNCTION_NOT_FOUND"
    )


def event(
    query_id,
    trace_id,
    event_type,
    provider,
    latency_ms,
    retryable=False,
    recovered=False,
    fallback_used=False,
    final_provider=None,
):

    return {
        "schema_version": "1.0",
        "event_id":
            f"{query_id}-{event_type}-{provider}",
        "query_id": query_id,
        "trace_id": trace_id,
        "provider": provider,
        "attempt": 1,
        "event_type": event_type,
        "retryable": retryable,
        "fallback_used": fallback_used,
        "recovered": recovered,
        "latency_ms": latency_ms,
        "final_provider": final_provider,
    }


events = [

    # Q1 - NORMAL SUCCESS

    event(
        "Q001",
        "T001",
        "ATTEMPT",
        "openai",
        100,
        final_provider="openai",
    ),

    event(
        "Q001",
        "T001",
        "SUCCESS",
        "openai",
        100,
        final_provider="openai",
    ),


    # Q2 - RETRY THEN RECOVERY

    event(
        "Q002",
        "T002",
        "ATTEMPT",
        "openai",
        200,
        final_provider="openai",
    ),

    event(
        "Q002",
        "T002",
        "RETRYABLE_FAILURE",
        "openai",
        200,
        retryable=True,
        final_provider="openai",
    ),

    event(
        "Q002",
        "T002",
        "ATTEMPT",
        "openai",
        200,
        final_provider="openai",
    ),

    event(
        "Q002",
        "T002",
        "SUCCESS",
        "openai",
        200,
        recovered=True,
        final_provider="openai",
    ),


    # Q3 - RETRY WITHOUT RECOVERY

    event(
        "Q003",
        "T003",
        "ATTEMPT",
        "openai",
        300,
        final_provider="openai",
    ),

    event(
        "Q003",
        "T003",
        "RETRYABLE_FAILURE",
        "openai",
        300,
        retryable=True,
        final_provider="openai",
    ),


    # Q4 - NORMAL SUCCESS

    event(
        "Q004",
        "T004",
        "ATTEMPT",
        "deepseek",
        400,
        final_provider="deepseek",
    ),

    event(
        "Q004",
        "T004",
        "SUCCESS",
        "deepseek",
        400,
        final_provider="deepseek",
    ),
]


original_events = deepcopy(events)


# ============================================================
# REAL ADAPTER FUNCTION
# ============================================================

records = (
    adapter_mod.resilience_events_to_query_records(
        events
    )
)


# ============================================================
# REAL METRICS ENGINE
# ============================================================

metrics = (
    engine_mod.calculate_governance_metrics(
        records
    )
)


expected = {
    "query_count": 4,
    "retry_rate": 0.5,
    "retry_recovery_rate": 0.5,
    "p95_latency_ms": 400.0,
}


print("")
print("=" * 72)
print("STEP V2-08D-03-FIX1")
print("REAL ADAPTER FUNCTION -> METRICS ENGINE")
print("=" * 72)


print("")
print("===== A. REAL INTERFACE =====")

print(
    "ADAPTER FUNCTION :",
    "resilience_events_to_query_records",
)

print(
    "METRICS FUNCTION :",
    "calculate_governance_metrics",
)


print("")
print("===== B. GRAIN TRANSFORMATION =====")

print(
    "SOURCE EVENT COUNT :",
    len(events),
)

print(
    "QUERY RECORD COUNT :",
    len(records),
)

print(
    "EVENT -> QUERY     :",
    f"{len(events)} -> {len(records)}",
)


print("")
print("===== C. QUERY RECORDS =====")

for record in records:

    print("")
    print(
        "QUERY_ID          :",
        record["query_id"],
    )

    print(
        "EVENT COUNT       :",
        record["resilience_event_count"],
    )

    print(
        "RETRY USED        :",
        record["retry_used"],
    )

    print(
        "RETRY RECOVERED   :",
        record["retry_recovered"],
    )

    print(
        "FALLBACK USED     :",
        record["fallback_used"],
    )

    print(
        "FINAL PROVIDER    :",
        record["final_provider"],
    )

    print(
        "LATENCY_MS        :",
        record["latency_ms"],
    )


print("")
print("===== D. GOVERNANCE METRICS =====")

for key in [
    "query_count",
    "retry_rate",
    "retry_recovery_rate",
    "p95_latency_ms",
]:
    print(
        f"{key:28}: {metrics[key]}"
    )


print("")
print("===== E. EXPECTED VALUE VALIDATION =====")

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
print("===== F. UNMAPPED GOVERNANCE SAFETY =====")

guardrail_safe = all(
    record.get("guardrail_pass") is None
    for record in records
)

judge_safe = all(
    record.get("judge_executed") is False
    and record.get("judge_rejected") is False
    for record in records
)

print(
    "GUARDRAIL NOT INVENTED :",
    "PASS"
    if guardrail_safe
    else "FAIL",
)

print(
    "JUDGE NOT INVENTED     :",
    "PASS"
    if judge_safe
    else "FAIL",
)


print("")
print("===== G. SOURCE IMMUTABILITY =====")

immutable = (
    events == original_events
)

print(
    "SOURCE EVENTS UNCHANGED:",
    "PASS"
    if immutable
    else "FAIL",
)


print("")
print("===== H. FINAL GATE =====")

passed = (
    not failures
    and guardrail_safe
    and judge_safe
    and immutable
)

if passed:

    print("STEP V2-08D-03-FIX1: PASS")
    print("REAL ADAPTER INTERFACE: PASS")
    print("EVENT -> QUERY ADAPTER: PASS")
    print("QUERY -> METRICS ENGINE: PASS")
    print("RETRY RATE: PASS")
    print("RETRY RECOVERY RATE: PASS")
    print("P95 LATENCY: PASS")
    print("UNMAPPED GOVERNANCE SAFETY: PASS")
    print("SOURCE IMMUTABILITY: PASS")

else:

    print("STEP V2-08D-03-FIX1: BLOCKED")
    print(
        "FAILED METRICS:",
        failures,
    )

    raise SystemExit(1)