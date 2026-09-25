from __future__ import annotations

import importlib.util
import io
import json
import sys
from copy import deepcopy
from pathlib import Path


BASE = Path(__file__).resolve().parent


ROUTER_FILE = (
    BASE
    / "GraphRAG_Phase3_StepV2_06_OBSERVABILITY_SINKS_01_router.py"
)

CLOUD_FILE = (
    BASE
    / "GraphRAG_Phase3_StepV2_06_OBSERVABILITY_SINKS_03_cloudwatch_json.py"
)

LANG_FILE = (
    BASE
    / "GraphRAG_Phase3_StepV2_07_LANGSMITH_SINK_01_adapter.py"
)

COMPOSITION_FILE = (
    BASE
    / "GraphRAG_Phase3_StepV2_07_RUNTIME_COMPOSITION_01_wiring.py"
)


def load_module(name, path):

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED: {path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[name] = module

    spec.loader.exec_module(
        module
    )

    return module


router_mod = load_module(
    "v2_router_07f",
    ROUTER_FILE,
)

cloud_mod = load_module(
    "v2_cloud_07f",
    CLOUD_FILE,
)

lang_mod = load_module(
    "v2_lang_07f",
    LANG_FILE,
)

composition_mod = load_module(
    "v2_composition_07f",
    COMPOSITION_FILE,
)


TelemetrySinkRouter = (
    router_mod.TelemetrySinkRouter
)

CloudWatchStructuredJsonSink = (
    cloud_mod.CloudWatchStructuredJsonSink
)

LangSmithSink = (
    lang_mod.LangSmithSink
)

ResilienceObservabilityComposition = (
    composition_mod.ResilienceObservabilityComposition
)


class FakeLangSmithClient:

    def __init__(self):
        self.calls = []

    def create_run(self, **kwargs):
        self.calls.append(
            deepcopy(kwargs)
        )


# ============================================================
# CANONICAL EVENTS
# ============================================================

events = [

    {
        "schema_version": "1.0",
        "event_id": "EVT-07F-001",
        "timestamp_utc": "2026-09-17T00:00:01Z",
        "service": "multi-agent-graphrag",
        "environment": "v2-runtime-test",

        "query_id": "Q-07F-001",
        "trace_id": "TRACE-07F-001",

        "provider": "openai",
        "attempt": 1,
        "event_type": "RETRYABLE_FAILURE",

        "retryable": True,
        "fallback_used": False,
        "recovered": False,

        "error_type": "ProviderTimeoutError",
        "latency_ms": 100.0,
        "success": False,
        "final_provider": None,
    },

    {
        "schema_version": "1.0",
        "event_id": "EVT-07F-002",
        "timestamp_utc": "2026-09-17T00:00:02Z",
        "service": "multi-agent-graphrag",
        "environment": "v2-runtime-test",

        "query_id": "Q-07F-001",
        "trace_id": "TRACE-07F-001",

        "provider": "deepseek",
        "attempt": 2,
        "event_type": "RECOVERY_SUCCESS",

        "retryable": False,
        "fallback_used": True,
        "recovered": True,

        "error_type": None,
        "latency_ms": 220.0,
        "success": True,
        "final_provider": "deepseek",
    },
]


original_events = deepcopy(events)


# ============================================================
# BUILD REAL ROUTER + REAL SINK ADAPTERS
# ============================================================

cloud_buffer = io.StringIO()

cloud_sink = (
    CloudWatchStructuredJsonSink(
        stream=cloud_buffer
    )
)


fake_langsmith = (
    FakeLangSmithClient()
)


langsmith_sink = (
    LangSmithSink(
        client=fake_langsmith,
        project_name=(
            "GraphRAG-V2-Runtime-Composition-Test"
        ),
    )
)


router = (
    TelemetrySinkRouter(
        sinks=[
            cloud_sink,
            langsmith_sink,
        ]
    )
)


composition = (
    ResilienceObservabilityComposition(
        router=router
    )
)


# ============================================================
# DELIVER EVENTS
# ============================================================

print(
    "===== RUNTIME COMPOSITION DELIVERY ====="
)


summary = composition.deliver_events(
    events
)


print(
    "EVENT COUNT          :",
    summary.event_count,
)

print(
    "DELIVERY COUNT       :",
    summary.delivery_count,
)

print(
    "FAILED DELIVERY COUNT:",
    summary.failed_delivery_count,
)


# ============================================================
# CLOUDWATCH VALIDATION
# ============================================================

cloud_lines = [
    line
    for line in cloud_buffer
        .getvalue()
        .splitlines()
    if line.strip()
]


cloud_events = [
    json.loads(line)
    for line in cloud_lines
]


print("")
print("===== CLOUDWATCH PATH =====")

print(
    "CLOUDWATCH EVENTS :",
    len(cloud_events),
)


# ============================================================
# LANGSMITH VALIDATION
# ============================================================

print("")
print("===== LANGSMITH PATH =====")

print(
    "LANGSMITH RUNS :",
    len(fake_langsmith.calls),
)


# ============================================================
# CORRELATION VALIDATION
# ============================================================

print("")
print("===== CORRELATION =====")


for index, source_event in enumerate(events):

    cloud_event = cloud_events[index]

    lang_call = fake_langsmith.calls[index]

    lang_inputs = (
        lang_call.get(
            "inputs",
            {},
        )
    )

    lang_metadata = (
        lang_call
        .get("extra", {})
        .get("metadata", {})
    )


    query_match = (
        source_event["query_id"]
        == cloud_event["query_id"]
        == lang_inputs["query_id"]
    )

    trace_match = (
        source_event["trace_id"]
        == cloud_event["trace_id"]
        == lang_inputs["trace_id"]
    )

    event_match = (
        source_event["event_id"]
        == cloud_event["event_id"]
        == lang_metadata["event_id"]
    )


    print(
        source_event["event_id"],
        "QUERY_MATCH=",
        query_match,
        "TRACE_MATCH=",
        trace_match,
        "EVENT_MATCH=",
        event_match,
    )


    if not (
        query_match
        and trace_match
        and event_match
    ):
        raise AssertionError(
            "RUNTIME_CORRELATION_FAILED"
        )


# ============================================================
# FINAL ASSERTIONS
# ============================================================

if summary.event_count != 2:
    raise AssertionError(
        "EVENT_COUNT_INVALID"
    )


if summary.delivery_count != 4:
    raise AssertionError(
        "DELIVERY_COUNT_INVALID"
    )


if summary.failed_delivery_count != 0:
    raise AssertionError(
        "UNEXPECTED_DELIVERY_FAILURE"
    )


if len(cloud_events) != 2:
    raise AssertionError(
        "CLOUDWATCH_EVENT_COUNT_INVALID"
    )


if len(fake_langsmith.calls) != 2:
    raise AssertionError(
        "LANGSMITH_RUN_COUNT_INVALID"
    )


if events != original_events:
    raise AssertionError(
        "SOURCE_EVENTS_MUTATED"
    )


print("")
print(
    "SOURCE EVENT IMMUTABILITY : PASS"
)


print("")
print("============================================================")
print("STEP V2-07F-03: PASS")
print("V2 COMPOSITION LAYER: PASS")
print("CANONICAL EVENT -> ROUTER: PASS")
print("ROUTER -> CLOUDWATCH: PASS")
print("ROUTER -> LANGSMITH: PASS")
print("CROSS-SINK CORRELATION: PASS")
print("SOURCE EVENT IMMUTABILITY: PASS")
print("REAL AWS CALL: NO")
print("REAL LANGSMITH CALL: NO")
print("PROVIDER CALL: NO")
print("============================================================")