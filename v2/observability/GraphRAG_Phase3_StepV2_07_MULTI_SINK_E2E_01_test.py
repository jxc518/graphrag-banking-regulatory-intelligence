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

    # Important for dataclass/module introspection.
    sys.modules[name] = module

    spec.loader.exec_module(module)
    return module


router_mod = load_module("v2_router", ROUTER_FILE)
cloud_mod = load_module("v2_cloudwatch", CLOUD_FILE)
lang_mod = load_module("v2_langsmith", LANG_FILE)


TelemetrySinkRouter = router_mod.TelemetrySinkRouter
CloudWatchStructuredJsonSink = cloud_mod.CloudWatchStructuredJsonSink
LangSmithSink = lang_mod.LangSmithSink


class FakeLangSmithClient:

    def __init__(self):
        self.calls = []

    def create_run(self, **kwargs):
        self.calls.append(deepcopy(kwargs))


canonical_event = {
    "schema_version": "1.0",
    "event_id": "EVT-V2-07E-001",
    "timestamp_utc": "2026-09-17T00:00:00Z",
    "service": "multi-agent-graphrag",
    "environment": "v2-integration-test",

    "query_id": "Q-V2-07E-001",
    "trace_id": "TRACE-V2-07E-001",

    "provider": "openai",
    "attempt": 2,
    "event_type": "RETRY_RECOVERED",

    "retryable": True,
    "fallback_used": True,
    "recovered": True,

    "error_type": "ProviderTransientError",
    "message": "Controlled V2 multi-sink integration test",
    "latency_ms": 321.0,

    "success": True,
    "final_provider": "deepseek",
}


original_event = deepcopy(canonical_event)


# ---------------------------------------------------------
# CloudWatch sink: capture stdout-style structured JSON
# ---------------------------------------------------------

cloud_buffer = io.StringIO()

cloud_sink = CloudWatchStructuredJsonSink(
    stream=cloud_buffer
)


# ---------------------------------------------------------
# LangSmith sink: fake client, no external API call
# ---------------------------------------------------------

fake_langsmith = FakeLangSmithClient()

langsmith_sink = LangSmithSink(
    client=fake_langsmith,
    project_name="GraphRAG-V2-Offline-MultiSink-Test",
)


# ---------------------------------------------------------
# Multi-sink router
# ---------------------------------------------------------

router = TelemetrySinkRouter(
    sinks=[
        cloud_sink,
        langsmith_sink,
    ]
)


print("===== MULTI-SINK DELIVERY =====")

results = router.emit(canonical_event)

for result in results:
    print(
        f"SINK={result.sink} "
        f"SUCCESS={result.success} "
        f"ERROR_TYPE={result.error_type}"
    )


# ---------------------------------------------------------
# Validate CloudWatch output
# ---------------------------------------------------------

cloud_raw = cloud_buffer.getvalue().strip()

if not cloud_raw:
    raise AssertionError("CLOUDWATCH_OUTPUT_EMPTY")

cloud_event = json.loads(cloud_raw)

print("")
print("===== CLOUDWATCH CAPTURE =====")
print("QUERY_ID=" + str(cloud_event.get("query_id")))
print("TRACE_ID=" + str(cloud_event.get("trace_id")))
print("EVENT_ID=" + str(cloud_event.get("event_id")))
print("PROVIDER=" + str(cloud_event.get("provider")))
print("ATTEMPT=" + str(cloud_event.get("attempt")))
print("FALLBACK_USED=" + str(cloud_event.get("fallback_used")))
print("RECOVERED=" + str(cloud_event.get("recovered")))
print("FINAL_PROVIDER=" + str(cloud_event.get("final_provider")))


# ---------------------------------------------------------
# Validate LangSmith capture
# ---------------------------------------------------------

if len(fake_langsmith.calls) != 1:
    raise AssertionError(
        f"LANGSMITH_CALL_COUNT_INVALID: {len(fake_langsmith.calls)}"
    )

lang_call = fake_langsmith.calls[0]

lang_inputs = lang_call.get("inputs", {})
lang_metadata = (
    lang_call
    .get("extra", {})
    .get("metadata", {})
)

print("")
print("===== LANGSMITH CAPTURE =====")
print("QUERY_ID=" + str(lang_inputs.get("query_id")))
print("TRACE_ID=" + str(lang_inputs.get("trace_id")))
print("EVENT_ID=" + str(lang_metadata.get("event_id")))
print("PROVIDER=" + str(lang_metadata.get("provider")))
print("ATTEMPT=" + str(lang_metadata.get("attempt")))
print("FALLBACK_USED=" + str(lang_metadata.get("fallback_used")))
print("RECOVERED=" + str(lang_metadata.get("recovered")))
print("FINAL_PROVIDER=" + str(lang_metadata.get("final_provider")))


# ---------------------------------------------------------
# Cross-sink correlation validation
# ---------------------------------------------------------

checks = {
    "query_id": (
        cloud_event.get("query_id"),
        lang_inputs.get("query_id"),
    ),
    "trace_id": (
        cloud_event.get("trace_id"),
        lang_inputs.get("trace_id"),
    ),
    "event_id": (
        cloud_event.get("event_id"),
        lang_metadata.get("event_id"),
    ),
    "provider": (
        cloud_event.get("provider"),
        lang_metadata.get("provider"),
    ),
    "attempt": (
        cloud_event.get("attempt"),
        lang_metadata.get("attempt"),
    ),
    "fallback_used": (
        cloud_event.get("fallback_used"),
        lang_metadata.get("fallback_used"),
    ),
    "recovered": (
        cloud_event.get("recovered"),
        lang_metadata.get("recovered"),
    ),
    "final_provider": (
        cloud_event.get("final_provider"),
        lang_metadata.get("final_provider"),
    ),
}


print("")
print("===== CROSS-SINK CORRELATION =====")

all_match = True

for field, (cloud_value, lang_value) in checks.items():

    match = cloud_value == lang_value

    print(
        f"{field.upper()} "
        f"CLOUDWATCH={cloud_value} "
        f"LANGSMITH={lang_value} "
        f"MATCH={match}"
    )

    if not match:
        all_match = False


if not all_match:
    raise AssertionError("CROSS_SINK_CORRELATION_FAILED")


# ---------------------------------------------------------
# Event immutability
# ---------------------------------------------------------

immutable = canonical_event == original_event

print("")
print("===== EVENT IMMUTABILITY =====")
print("ORIGINAL EVENT UNCHANGED=" + str(immutable))

if not immutable:
    raise AssertionError("CANONICAL_EVENT_MUTATED")


# ---------------------------------------------------------
# Final gate
# ---------------------------------------------------------

delivery_success = all(
    result.success
    for result in results
)

if not delivery_success:
    raise AssertionError("MULTI_SINK_DELIVERY_FAILED")


print("")
print("============================================================")
print("STEP V2-07E-02: PASS")
print("CLOUDWATCH DELIVERY: PASS")
print("LANGSMITH DELIVERY: PASS")
print("CROSS-SINK CORRELATION: PASS")
print("EVENT IMMUTABILITY: PASS")
print("REAL AWS CALL: NO")
print("REAL LANGSMITH API CALL: NO")
print("PROVIDER CALL: NO")
print("============================================================")