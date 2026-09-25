from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path


HERE = Path(__file__).resolve().parent

ADAPTER = (
    HERE
    / "GraphRAG_Phase3_StepV2_08_RECORD_ADAPTER_01_query.py"
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


adapter = load_module(
    "v2_08_query_adapter",
    ADAPTER,
)


query_id = "query-v2-08d-02b-001"
trace_id = "trace-v2-08d-02b-001"

base = {
    "schema_version": "1.0",
    "query_id": query_id,
    "trace_id": trace_id,
    "primary_provider": "openai",
    "fallback_provider": "deepseek",
    "primary_attempts": 2,
    "fallback_attempts": 1,
    "latency_ms": 1202.96,
    "final_provider": "deepseek",
    "success": True,
}


events = [
    {
        **base,
        "event_id": "EVT-001",
        "provider": "openai",
        "attempt": 1,
        "event_type": "ATTEMPT",
        "retryable": False,
        "fallback_used": False,
        "recovered": False,
        "error_type": None,
    },
    {
        **base,
        "event_id": "EVT-002",
        "provider": "openai",
        "attempt": 1,
        "event_type": "RETRYABLE_FAILURE",
        "retryable": True,
        "fallback_used": False,
        "recovered": False,
        "error_type": "ProviderTimeoutError",
    },
    {
        **base,
        "event_id": "EVT-003",
        "provider": "openai",
        "attempt": 1,
        "event_type": "BACKOFF",
        "retryable": False,
        "fallback_used": False,
        "recovered": False,
        "error_type": None,
    },
    {
        **base,
        "event_id": "EVT-004",
        "provider": "openai",
        "attempt": 2,
        "event_type": "ATTEMPT",
        "retryable": False,
        "fallback_used": False,
        "recovered": False,
        "error_type": None,
    },
    {
        **base,
        "event_id": "EVT-005",
        "provider": "openai",
        "attempt": 2,
        "event_type": "RETRYABLE_FAILURE",
        "retryable": True,
        "fallback_used": False,
        "recovered": False,
        "error_type": "ProviderTimeoutError",
    },
    {
        **base,
        "event_id": "EVT-006",
        "provider": "deepseek",
        "attempt": 1,
        "event_type": "FALLBACK_START",
        "retryable": False,
        "fallback_used": True,
        "recovered": False,
        "error_type": None,
    },
    {
        **base,
        "event_id": "EVT-007",
        "provider": "deepseek",
        "attempt": 1,
        "event_type": "SUCCESS",
        "retryable": False,
        "fallback_used": True,
        "recovered": True,
        "error_type": None,
    },
]


original = deepcopy(events)

records = adapter.resilience_events_to_query_records(
    events
)


print("")
print("=" * 68)
print("STEP V2-08D-02B")
print("QUERY-LEVEL GOVERNANCE RECORD ADAPTER")
print("=" * 68)


print("")
print("===== A. GRAIN VALIDATION =====")

print("SOURCE EVENT COUNT :", len(events))
print("QUERY RECORD COUNT :", len(records))


if len(records) != 1:
    raise AssertionError(
        "EXPECTED EXACTLY ONE QUERY RECORD"
    )


record = records[0]


print("")
print("===== B. QUERY RECORD =====")

for key, value in record.items():
    print(
        f"{key:34}: {value}"
    )


print("")
print("===== C. RESILIENCE MAPPING VALIDATION =====")

checks = {
    "QUERY ID": (
        record["query_id"] == query_id
    ),

    "RETRY USED": (
        record["retry_used"] is True
    ),

    "RETRY RECOVERED": (
        record["retry_recovered"] is True
    ),

    "FALLBACK USED": (
        record["fallback_used"] is True
    ),

    "FINAL PROVIDER": (
        record["final_provider"] == "deepseek"
    ),

    "LATENCY NOT SUMMED": (
        record["latency_ms"] == 1202.96
    ),

    "EVENT COUNT": (
        record["resilience_event_count"] == 7
    ),

    "SUCCESS EVENT PRESENT": (
        "SUCCESS"
        in record["resilience_event_types"]
    ),
}


for name, passed in checks.items():

    print(
        f"{name:28}: "
        f"{'PASS' if passed else 'FAIL'}"
    )


print("")
print("===== D. UNMAPPED GOVERNANCE SIGNAL SAFETY =====")

unmapped_safe = (
    record["guardrail_pass"] is None
    and record["provenance_evaluated"] is False
    and record["span_evaluated"] is False
    and record["judge_executed"] is False
)

print(
    "GUARDRAIL FIELD NOT INVENTED :",
    "PASS" if record["guardrail_pass"] is None else "FAIL",
)

print(
    "PROVENANCE NOT INVENTED      :",
    "PASS" if record["provenance_evaluated"] is False else "FAIL",
)

print(
    "SPAN RESULT NOT INVENTED     :",
    "PASS" if record["span_evaluated"] is False else "FAIL",
)

print(
    "JUDGE RESULT NOT INVENTED    :",
    "PASS" if record["judge_executed"] is False else "FAIL",
)


print("")
print("===== E. SOURCE IMMUTABILITY =====")

immutable = (
    events == original
)

print(
    "SOURCE EVENTS UNCHANGED :",
    "PASS" if immutable else "FAIL",
)


print("")
print("===== F. FINAL GATE =====")

passed = (
    all(checks.values())
    and unmapped_safe
    and immutable
)

if passed:

    print("STEP V2-08D-02B: PASS")
    print("EVENT -> QUERY GRAIN: PASS")
    print("RETRY MAPPING: PASS")
    print("RECOVERY MAPPING: PASS")
    print("FALLBACK MAPPING: PASS")
    print("QUERY LATENCY MAPPING: PASS")
    print("UNMAPPED SIGNAL SAFETY: PASS")
    print("SOURCE EVENT IMMUTABILITY: PASS")

else:

    print("STEP V2-08D-02B: BLOCKED")
    raise SystemExit(1)