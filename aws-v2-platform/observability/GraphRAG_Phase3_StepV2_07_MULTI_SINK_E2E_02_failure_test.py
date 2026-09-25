from __future__ import annotations

import importlib.util
import io
import json
import sys
from copy import deepcopy
from pathlib import Path


BASE = Path(__file__).resolve().parent

ROUTER_FILE = BASE / "GraphRAG_Phase3_StepV2_06_OBSERVABILITY_SINKS_01_router.py"
CLOUD_FILE = BASE / "GraphRAG_Phase3_StepV2_06_OBSERVABILITY_SINKS_03_cloudwatch_json.py"
LANG_FILE = BASE / "GraphRAG_Phase3_StepV2_07_LANGSMITH_SINK_01_adapter.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)

    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_SPEC_FAILED: {path}")

    module = importlib.util.module_from_spec(spec)

    # Required for dataclass/module introspection.
    sys.modules[name] = module

    spec.loader.exec_module(module)

    return module


router_mod = load_module("v2_router_failure", ROUTER_FILE)
cloud_mod = load_module("v2_cloud_failure", CLOUD_FILE)
lang_mod = load_module("v2_lang_failure", LANG_FILE)


TelemetrySinkRouter = router_mod.TelemetrySinkRouter
CloudWatchStructuredJsonSink = cloud_mod.CloudWatchStructuredJsonSink
LangSmithSink = lang_mod.LangSmithSink


# ==========================================================
# TEST SUPPORT
# ==========================================================

class SuccessfulLangSmithClient:

    def __init__(self):
        self.calls = []

    def create_run(self, **kwargs):
        self.calls.append(deepcopy(kwargs))


class FailingLangSmithClient:

    def create_run(self, **kwargs):
        raise RuntimeError("CONTROLLED_LANGSMITH_FAILURE")


class FailingStream:

    def write(self, value):
        raise RuntimeError("CONTROLLED_CLOUDWATCH_FAILURE")

    def flush(self):
        pass


canonical_event = {
    "schema_version": "1.0",
    "event_id": "EVT-V2-07E-FAILURE-001",
    "timestamp_utc": "2026-09-17T00:00:00Z",
    "service": "multi-agent-graphrag",
    "environment": "v2-failure-isolation-test",

    "query_id": "Q-V2-07E-FAILURE-001",
    "trace_id": "TRACE-V2-07E-FAILURE-001",

    "provider": "openai",
    "attempt": 2,
    "event_type": "RETRY_RECOVERED",

    "retryable": True,
    "fallback_used": True,
    "recovered": True,

    "error_type": "ProviderTransientError",
    "message": "Controlled multi-sink failure isolation test",
    "latency_ms": 456.0,

    "success": True,
    "final_provider": "deepseek",
}


original_event = deepcopy(canonical_event)


# ==========================================================
# SCENARIO A
# CLOUDWATCH FAILS -> LANGSMITH MUST STILL SUCCEED
# ==========================================================

print("")
print("============================================================")
print("SCENARIO A")
print("CLOUDWATCH FAILS -> LANGSMITH MUST STILL SUCCEED")
print("============================================================")


failing_cloudwatch = CloudWatchStructuredJsonSink(
    stream=FailingStream()
)

successful_langsmith_client = SuccessfulLangSmithClient()

successful_langsmith = LangSmithSink(
    client=successful_langsmith_client,
    project_name="GraphRAG-V2-Failure-Isolation-Test",
)


router_a = TelemetrySinkRouter(
    sinks=[
        failing_cloudwatch,
        successful_langsmith,
    ]
)


results_a = router_a.emit(canonical_event)


for result in results_a:
    print(
        f"SINK={result.sink} "
        f"SUCCESS={result.success} "
        f"ERROR_TYPE={result.error_type} "
        f"MESSAGE={result.message}"
    )


if len(results_a) != 2:
    raise AssertionError(
        f"SCENARIO_A_RESULT_COUNT_INVALID: {len(results_a)}"
    )


cloud_result_a = results_a[0]
lang_result_a = results_a[1]


if cloud_result_a.success:
    raise AssertionError(
        "SCENARIO_A_CLOUDWATCH_SHOULD_HAVE_FAILED"
    )


if not lang_result_a.success:
    raise AssertionError(
        "SCENARIO_A_LANGSMITH_DID_NOT_SURVIVE"
    )


if len(successful_langsmith_client.calls) != 1:
    raise AssertionError(
        "SCENARIO_A_LANGSMITH_CALL_NOT_DELIVERED"
    )


lang_call_a = successful_langsmith_client.calls[0]

lang_inputs_a = lang_call_a.get("inputs", {})

lang_metadata_a = (
    lang_call_a
    .get("extra", {})
    .get("metadata", {})
)


if lang_inputs_a.get("query_id") != canonical_event["query_id"]:
    raise AssertionError("SCENARIO_A_QUERY_ID_MISMATCH")


if lang_inputs_a.get("trace_id") != canonical_event["trace_id"]:
    raise AssertionError("SCENARIO_A_TRACE_ID_MISMATCH")


if lang_metadata_a.get("event_id") != canonical_event["event_id"]:
    raise AssertionError("SCENARIO_A_EVENT_ID_MISMATCH")


print("")
print("SCENARIO A CLOUDWATCH FAILURE : CONTROLLED")
print("SCENARIO A LANGSMITH DELIVERY : PASS")
print("SCENARIO A CORRELATION         : PASS")
print("SCENARIO A FAILURE ISOLATION   : PASS")


# ==========================================================
# SCENARIO B
# LANGSMITH FAILS -> CLOUDWATCH MUST STILL SUCCEED
# ==========================================================

print("")
print("============================================================")
print("SCENARIO B")
print("LANGSMITH FAILS -> CLOUDWATCH MUST STILL SUCCEED")
print("============================================================")


cloud_buffer_b = io.StringIO()

successful_cloudwatch = CloudWatchStructuredJsonSink(
    stream=cloud_buffer_b
)

failing_langsmith = LangSmithSink(
    client=FailingLangSmithClient(),
    project_name="GraphRAG-V2-Failure-Isolation-Test",
)


router_b = TelemetrySinkRouter(
    sinks=[
        successful_cloudwatch,
        failing_langsmith,
    ]
)


results_b = router_b.emit(canonical_event)


for result in results_b:
    print(
        f"SINK={result.sink} "
        f"SUCCESS={result.success} "
        f"ERROR_TYPE={result.error_type} "
        f"MESSAGE={result.message}"
    )


if len(results_b) != 2:
    raise AssertionError(
        f"SCENARIO_B_RESULT_COUNT_INVALID: {len(results_b)}"
    )


cloud_result_b = results_b[0]
lang_result_b = results_b[1]


if not cloud_result_b.success:
    raise AssertionError(
        "SCENARIO_B_CLOUDWATCH_DID_NOT_SURVIVE"
    )


if lang_result_b.success:
    raise AssertionError(
        "SCENARIO_B_LANGSMITH_SHOULD_HAVE_FAILED"
    )


cloud_raw_b = cloud_buffer_b.getvalue().strip()

if not cloud_raw_b:
    raise AssertionError(
        "SCENARIO_B_CLOUDWATCH_OUTPUT_EMPTY"
    )


cloud_event_b = json.loads(cloud_raw_b)


if cloud_event_b.get("query_id") != canonical_event["query_id"]:
    raise AssertionError("SCENARIO_B_QUERY_ID_MISMATCH")


if cloud_event_b.get("trace_id") != canonical_event["trace_id"]:
    raise AssertionError("SCENARIO_B_TRACE_ID_MISMATCH")


if cloud_event_b.get("event_id") != canonical_event["event_id"]:
    raise AssertionError("SCENARIO_B_EVENT_ID_MISMATCH")


print("")
print("SCENARIO B LANGSMITH FAILURE : CONTROLLED")
print("SCENARIO B CLOUDWATCH DELIVERY: PASS")
print("SCENARIO B CORRELATION        : PASS")
print("SCENARIO B FAILURE ISOLATION  : PASS")


# ==========================================================
# EVENT IMMUTABILITY
# ==========================================================

print("")
print("============================================================")
print("EVENT IMMUTABILITY")
print("============================================================")


immutable = canonical_event == original_event

print("ORIGINAL EVENT UNCHANGED=" + str(immutable))


if not immutable:
    raise AssertionError(
        "CANONICAL_EVENT_MUTATED"
    )


# ==========================================================
# FINAL GOVERNANCE GATE
# ==========================================================

scenario_a_pass = (
    not cloud_result_a.success
    and lang_result_a.success
)

scenario_b_pass = (
    cloud_result_b.success
    and not lang_result_b.success
)


if not scenario_a_pass:
    raise AssertionError(
        "SCENARIO_A_FAILURE_ISOLATION_FAILED"
    )


if not scenario_b_pass:
    raise AssertionError(
        "SCENARIO_B_FAILURE_ISOLATION_FAILED"
    )


print("")
print("============================================================")
print("STEP V2-07E-03: PASS")
print("CLOUDWATCH FAILURE -> LANGSMITH SURVIVES: PASS")
print("LANGSMITH FAILURE -> CLOUDWATCH SURVIVES: PASS")
print("CORRELATION PRESERVED: PASS")
print("EVENT IMMUTABILITY: PASS")
print("OBSERVABILITY FAILURE ISOLATION: PASS")
print("REAL AWS CALL: NO")
print("REAL LANGSMITH API CALL: NO")
print("PROVIDER CALL: NO")
print("============================================================")