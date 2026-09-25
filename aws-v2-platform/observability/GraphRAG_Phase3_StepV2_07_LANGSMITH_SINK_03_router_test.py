from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent

ROUTER_PATH = (
    HERE
    / "GraphRAG_Phase3_StepV2_06_OBSERVABILITY_SINKS_01_router.py"
)

ADAPTER_PATH = (
    HERE
    / "GraphRAG_Phase3_StepV2_07_LANGSMITH_SINK_01_adapter.py"
)


def load_module(name: str, path: Path):

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_IMPORT_SPEC_FAILED: {path}"
        )

    module = importlib.util.module_from_spec(spec)

    # Register dynamically loaded module before execution.
    # dataclasses may resolve cls.__module__ through sys.modules.
    sys.modules[name] = module

    spec.loader.exec_module(module)

    return module


router_module = load_module(
    "graphrag_v2_sink_router",
    ROUTER_PATH,
)

adapter_module = load_module(
    "graphrag_v2_langsmith_sink",
    ADAPTER_PATH,
)

TelemetrySinkRouter = router_module.TelemetrySinkRouter
MemorySink = router_module.MemorySink
FailingSink = router_module.FailingSink
LangSmithSink = adapter_module.LangSmithSink


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
# CANONICAL EVENT
# ============================================================

event = {
    "schema_version": "1.0",
    "event_id": "EVT-ROUTER-001",
    "timestamp_utc": "2026-09-17T00:05:00Z",
    "service": "graphrag-v2",
    "environment": "offline-router-test",
    "query_id": "Q-ROUTER-001",
    "trace_id": "TRACE-ROUTER-001",
    "provider": "openai",
    "attempt": 2,
    "event_type": "FALLBACK",
    "retryable": True,
    "fallback_used": True,
    "recovered": True,
    "error_type": "TimeoutError",
    "message": "controlled multi-sink test",
    "latency_ms": 1800,
    "success": True,
    "final_provider": "deepseek",
}

original_event = copy.deepcopy(event)


# ============================================================
# BUILD THREE SINKS
# ============================================================

memory_sink = MemorySink(
    name="memory"
)

fake_client = FakeLangSmithClient()

langsmith_sink = LangSmithSink(
    client=fake_client,
    project_name="graphrag-v2-offline-router-test",
)

failing_sink = FailingSink()


# Important:
# Failing sink is intentionally placed BETWEEN
# two healthy delivery paths.

router = TelemetrySinkRouter(
    sinks=[
        memory_sink,
        failing_sink,
        langsmith_sink,
    ]
)


# ============================================================
# TEST 1 - MULTI-SINK DELIVERY
# ============================================================

print()
print("===== TEST 1 - MULTI-SINK DELIVERY =====")

results = router.emit(event)

assert len(results) == 3

for result in results:
    print(
        f"SINK={result.sink} "
        f"SUCCESS={result.success} "
        f"ERROR={result.error_type}"
    )

assert results[0].sink == "memory"
assert results[0].success is True

assert results[1].sink == "intentional_failure"
assert results[1].success is False
assert results[1].error_type == "RuntimeError"

assert results[2].sink == "langsmith"
assert results[2].success is True

print("MULTI-SINK DELIVERY   : PASS")


# ============================================================
# TEST 2 - FAILURE ISOLATION
# ============================================================

print()
print("===== TEST 2 - FAILURE ISOLATION =====")

assert len(memory_sink.received) == 1
assert len(fake_client.calls) == 1

print("MEMORY BEFORE FAILURE : PASS")
print("FAILING SINK          : CONTROLLED FAIL")
print("LANGSMITH AFTER FAIL  : PASS")
print("FAILURE ISOLATION     : PASS")


# ============================================================
# TEST 3 - CORRELATION PRESERVATION
# ============================================================

print()
print("===== TEST 3 - CORRELATION PRESERVATION =====")

memory_event = memory_sink.received[0]
langsmith_call = fake_client.calls[0]

assert memory_event["query_id"] == event["query_id"]
assert memory_event["trace_id"] == event["trace_id"]

assert (
    langsmith_call["inputs"]["query_id"]
    == event["query_id"]
)

assert (
    langsmith_call["inputs"]["trace_id"]
    == event["trace_id"]
)

print("QUERY ID PRESERVED    :", event["query_id"])
print("TRACE ID PRESERVED    :", event["trace_id"])
print("CANONICAL CORRELATION : PASS")


# ============================================================
# TEST 4 - FALLBACK / RECOVERY METADATA
# ============================================================

print()
print("===== TEST 4 - FALLBACK + RECOVERY METADATA =====")

metadata = (
    langsmith_call["kwargs"]
    ["extra"]
    ["metadata"]
)

assert metadata["provider"] == "openai"
assert metadata["attempt"] == 2
assert metadata["fallback_used"] is True
assert metadata["recovered"] is True
assert metadata["final_provider"] == "deepseek"

print("ORIGINAL PROVIDER     :", metadata["provider"])
print("ATTEMPT               :", metadata["attempt"])
print("FALLBACK USED         :", metadata["fallback_used"])
print("RECOVERED             :", metadata["recovered"])
print("FINAL PROVIDER        :", metadata["final_provider"])
print("RESILIENCE METADATA   : PASS")


# ============================================================
# TEST 5 - EVENT IMMUTABILITY
# ============================================================

print()
print("===== TEST 5 - EVENT IMMUTABILITY =====")

assert event == original_event

print("ORIGINAL EVENT MUTATED : NO")
print("DEEPCOPY ISOLATION     : PASS")


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("============================================================")
print("STEP V2-07C-04: PASS")
print("MULTI-SINK ROUTER INTEGRATION: CLOSED PASS")
print("MEMORY SINK            : PASS")
print("FAILING SINK           : CONTROLLED FAIL")
print("LANGSMITH SINK         : PASS")
print("FAILURE ISOLATION      : PASS")
print("CANONICAL CORRELATION  : PASS")
print("RESILIENCE METADATA    : PASS")
print("EVENT IMMUTABILITY     : PASS")
print("REAL LANGSMITH CALL    : NO")
print("============================================================")

