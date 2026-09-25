from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent

ADAPTER_PATH = (
    HERE
    / "GraphRAG_Phase3_StepV2_07_LANGSMITH_SINK_01_adapter.py"
)


# ============================================================
# LOAD ADAPTER
# ============================================================

spec = importlib.util.spec_from_file_location(
    "graphrag_v2_langsmith_sink",
    ADAPTER_PATH,
)

if spec is None or spec.loader is None:
    raise RuntimeError("ADAPTER_IMPORT_SPEC_FAILED")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

LangSmithSink = module.LangSmithSink


# ============================================================
# FAKE LANGSMITH CLIENT
# ============================================================

class FakeLangSmithClient:

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_run(
        self,
        name: str,
        inputs: dict[str, Any],
        run_type: str,
        **kwargs: Any,
    ) -> None:

        self.calls.append(
            {
                "name": name,
                "inputs": copy.deepcopy(inputs),
                "run_type": run_type,
                "kwargs": copy.deepcopy(kwargs),
            }
        )


# ============================================================
# CANONICAL TEST EVENT
# ============================================================

event = {
    "schema_version": "1.0",
    "event_id": "EVT-TEST-001",
    "timestamp_utc": "2026-09-16T23:50:00Z",
    "service": "graphrag-v2",
    "environment": "offline-test",
    "query_id": "Q-TEST-001",
    "trace_id": "TRACE-TEST-001",
    "provider": "openai",
    "attempt": 2,
    "event_type": "RETRY",
    "retryable": True,
    "fallback_used": False,
    "recovered": False,
    "error_type": "TimeoutError",
    "message": "controlled offline test",
    "latency_ms": 1250,
    "success": False,
    "final_provider": None,
}

original_event = copy.deepcopy(event)


# ============================================================
# TEST 1 - NORMAL DELIVERY
# ============================================================

print()
print("===== TEST 1 - NORMAL DELIVERY =====")

client = FakeLangSmithClient()

sink = LangSmithSink(
    client=client,
    project_name="graphrag-v2-offline-test",
)

sink.emit(event)

assert len(client.calls) == 1

call = client.calls[0]

assert call["name"] == "resilience.retry"
assert call["run_type"] == "tool"

assert call["inputs"]["query_id"] == "Q-TEST-001"
assert call["inputs"]["trace_id"] == "TRACE-TEST-001"

assert (
    call["kwargs"]["project_name"]
    == "graphrag-v2-offline-test"
)

metadata = call["kwargs"]["extra"]["metadata"]

assert metadata["event_id"] == "EVT-TEST-001"
assert metadata["provider"] == "openai"
assert metadata["attempt"] == 2
assert metadata["event_type"] == "RETRY"
assert metadata["retryable"] is True
assert metadata["fallback_used"] is False
assert metadata["recovered"] is False
assert metadata["error_type"] == "TimeoutError"
assert metadata["latency_ms"] == 1250
assert metadata["final_provider"] is None

print("NORMAL DELIVERY       : PASS")
print("CREATE_RUN CALL COUNT :", len(client.calls))
print("RUN NAME              :", call["name"])
print("RUN TYPE              :", call["run_type"])
print("QUERY ID              :", call["inputs"]["query_id"])
print("TRACE ID              :", call["inputs"]["trace_id"])
print("PROVIDER              :", metadata["provider"])
print("ATTEMPT               :", metadata["attempt"])


# ============================================================
# TEST 2 - ORIGINAL EVENT IMMUTABILITY
# ============================================================

print()
print("===== TEST 2 - EVENT IMMUTABILITY =====")

assert event == original_event

print("ORIGINAL EVENT MUTATED : NO")
print("EVENT IMMUTABILITY     : PASS")


# ============================================================
# TEST 3 - REQUIRED FIELD VALIDATION
# ============================================================

print()
print("===== TEST 3 - MISSING FIELD CONTROL =====")

bad_event = copy.deepcopy(event)
del bad_event["trace_id"]

bad_client = FakeLangSmithClient()

bad_sink = LangSmithSink(
    client=bad_client,
    project_name="graphrag-v2-offline-test",
)

controlled_failure = False

try:

    bad_sink.emit(bad_event)

except ValueError as exc:

    controlled_failure = True

    assert "LANGSMITH_SINK_MISSING_FIELDS" in str(exc)
    assert "trace_id" in str(exc)

    print("CONTROLLED ERROR TYPE :", type(exc).__name__)
    print("CONTROLLED ERROR      :", str(exc))

assert controlled_failure is True
assert len(bad_client.calls) == 0

print("MISSING FIELD CONTROL : PASS")
print("API-LIKE CALL MADE    : NO")


# ============================================================
# TEST 4 - OPTIONAL PROJECT NAME
# ============================================================

print()
print("===== TEST 4 - OPTIONAL PROJECT NAME =====")

client_no_project = FakeLangSmithClient()

sink_no_project = LangSmithSink(
    client=client_no_project,
)

sink_no_project.emit(event)

call_no_project = client_no_project.calls[0]

assert "project_name" not in call_no_project["kwargs"]

print("OPTIONAL PROJECT NAME : PASS")


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("============================================================")
print("STEP V2-07C-03: PASS")
print("LANGSMITH OFFLINE CONTRACT TEST: CLOSED PASS")
print("NORMAL DELIVERY       : PASS")
print("EVENT IMMUTABILITY    : PASS")
print("MISSING FIELD CONTROL : PASS")
print("PROJECT NAME CONTROL  : PASS")
print("REAL LANGSMITH CALL   : NO")
print("============================================================")
