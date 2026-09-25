from __future__ import annotations

from copy import deepcopy
from io import StringIO
from pathlib import Path
import importlib.util
import json
import sys


router_path = Path(sys.argv[1])
sink_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])


def load_module(name, path):

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[name] = module

    spec.loader.exec_module(
        module
    )

    return module


router_module = load_module(
    "v2_sink_router_f03b",
    router_path,
)

sink_module = load_module(
    "v2_cloudwatch_sink_f03b",
    sink_path,
)


TelemetrySinkRouter = (
    router_module.TelemetrySinkRouter
)

MemorySink = (
    router_module.MemorySink
)

CloudWatchStructuredJsonSink = (
    sink_module.CloudWatchStructuredJsonSink
)


# ============================================================
# CANONICAL EVENTS
# ============================================================

events = [

    {
        "schema_version": "1.0",
        "event_id": "f03b-event-001",
        "timestamp_utc": "2026-09-16T20:00:00+00:00",
        "service": "GraphRAG-AWS-V2",
        "environment": "validation",
        "query_id": "query-f03b-001",
        "trace_id": "trace-f03b-001",
        "provider": "openai",
        "attempt": 1,
        "event_type": "RETRYABLE_FAILURE",
        "retryable": True,
        "fallback_used": False,
        "recovered": False,
        "error_type": "ProviderTimeoutError",
        "message": "Controlled primary timeout.",
        "latency_ms": 500.0,
        "success": False,
        "final_provider": None,
    },

    {
        "schema_version": "1.0",
        "event_id": "f03b-event-002",
        "timestamp_utc": "2026-09-16T20:00:01+00:00",
        "service": "GraphRAG-AWS-V2",
        "environment": "validation",
        "query_id": "query-f03b-001",
        "trace_id": "trace-f03b-001",
        "provider": "deepseek",
        "attempt": 1,
        "event_type": "FALLBACK_START",
        "retryable": False,
        "fallback_used": True,
        "recovered": False,
        "error_type": None,
        "message": "Fallback started.",
        "latency_ms": None,
        "success": False,
        "final_provider": None,
    },

    {
        "schema_version": "1.0",
        "event_id": "f03b-event-003",
        "timestamp_utc": "2026-09-16T20:00:02+00:00",
        "service": "GraphRAG-AWS-V2",
        "environment": "validation",
        "query_id": "query-f03b-001",
        "trace_id": "trace-f03b-001",
        "provider": "deepseek",
        "attempt": 1,
        "event_type": "SUCCESS",
        "retryable": False,
        "fallback_used": True,
        "recovered": True,
        "error_type": None,
        "message": "Fallback recovery succeeded.",
        "latency_ms": 1202.96,
        "success": True,
        "final_provider": "deepseek",
    },
]


original_events = deepcopy(events)


print()
print("===== D1. STRUCTURED JSON EMISSION =====")


buffer = StringIO()

cloudwatch_sink = (
    CloudWatchStructuredJsonSink(
        stream=buffer
    )
)

for event in events:
    cloudwatch_sink.emit(event)


raw_output = buffer.getvalue()

lines = raw_output.splitlines()


print(
    "EVENT COUNT     :",
    len(events)
)

print(
    "JSON LINE COUNT :",
    len(lines)
)


line_count_pass = (
    len(lines) == len(events)
)


print(
    "ONE EVENT / LINE:",
    line_count_pass
)


print()
print("===== D2. JSON PARSING =====")


parsed = []

parse_errors = []


for index, line in enumerate(
    lines,
    start=1,
):

    try:

        parsed.append(
            json.loads(line)
        )

    except Exception as exc:

        parse_errors.append({
            "line": index,
            "error_type":
                type(exc).__name__,
            "message":
                str(exc),
        })


json_parse_pass = (
    len(parse_errors) == 0
    and len(parsed) == len(events)
)


print(
    "PARSED EVENTS :",
    len(parsed)
)

print(
    "PARSE ERRORS  :",
    len(parse_errors)
)

print(
    "JSON PARSE PASS:",
    json_parse_pass
)


print()
print("===== D3. CANONICAL FIELD PRESERVATION =====")


required_fields = [
    "schema_version",
    "event_id",
    "timestamp_utc",
    "service",
    "environment",
    "query_id",
    "trace_id",
    "provider",
    "attempt",
    "event_type",
    "retryable",
    "fallback_used",
    "recovered",
]


field_errors = []


for index, record in enumerate(parsed):

    source = events[index]

    for field in required_fields:

        if record.get(field) != source.get(field):

            field_errors.append({
                "event_index": index,
                "field": field,
                "expected":
                    source.get(field),
                "actual":
                    record.get(field),
            })


field_preservation_pass = (
    len(field_errors) == 0
)


print(
    "FIELD ERRORS      :",
    len(field_errors)
)

print(
    "FIELD PRESERVATION:",
    field_preservation_pass
)


print()
print("===== D4. CLOUDWATCH CLASSIFICATION =====")


sink_classification_pass = all(
    record.get(
        "telemetry_sink"
    ) == "cloudwatch"
    for record in parsed
)


print(
    "SINK FIELD PASS:",
    sink_classification_pass
)


print()
print("===== D5. CORRELATION PRESERVATION =====")


query_ids = {
    record["query_id"]
    for record in parsed
}

trace_ids = {
    record["trace_id"]
    for record in parsed
}


correlation_pass = all([
    query_ids == {
        "query-f03b-001"
    },
    trace_ids == {
        "trace-f03b-001"
    },
])


print(
    "QUERY IDS :",
    query_ids
)

print(
    "TRACE IDS :",
    trace_ids
)

print(
    "CORRELATION PASS:",
    correlation_pass
)


print()
print("===== D6. EVENT SEMANTICS =====")


event_order = [
    record["event_type"]
    for record in parsed
]


expected_order = [
    "RETRYABLE_FAILURE",
    "FALLBACK_START",
    "SUCCESS",
]


event_semantics_pass = all([

    event_order
        == expected_order,

    parsed[0]["retryable"]
        is True,

    parsed[1]["fallback_used"]
        is True,

    parsed[2]["fallback_used"]
        is True,

    parsed[2]["recovered"]
        is True,

    parsed[2]["final_provider"]
        == "deepseek",
])


print(
    "EVENT ORDER:",
    event_order
)

print(
    "SEMANTICS PASS:",
    event_semantics_pass
)


print()
print("===== D7. CANONICAL IMMUTABILITY =====")


immutability_pass = (
    events == original_events
)


print(
    "ORIGINAL EVENTS UNCHANGED:",
    immutability_pass
)


print()
print("===== D8. ROUTER COMPATIBILITY =====")


router_buffer = StringIO()

router_cloudwatch_sink = (
    CloudWatchStructuredJsonSink(
        stream=router_buffer
    )
)

memory_sink = MemorySink(
    name="parallel_test_sink"
)


router = TelemetrySinkRouter([
    router_cloudwatch_sink,
    memory_sink,
])


router_results = (
    router.emit(events[2])
)


router_pass = all([

    len(router_results) == 2,

    router_results[0].success
        is True,

    router_results[1].success
        is True,

    len(
        router_buffer.getvalue().splitlines()
    ) == 1,

    len(memory_sink.received)
        == 1,
])


print(
    "ROUTER RESULTS:",
    [
        (
            r.sink,
            r.success,
            r.error_type,
        )
        for r in router_results
    ]
)

print(
    "ROUTER PASS:",
    router_pass
)


print()
print("===== D9. FINAL VALIDATION =====")


checks = {

    "one_event_per_line":
        line_count_pass,

    "json_parse":
        json_parse_pass,

    "canonical_field_preservation":
        field_preservation_pass,

    "cloudwatch_classification":
        sink_classification_pass,

    "correlation_preservation":
        correlation_pass,

    "event_semantics":
        event_semantics_pass,

    "canonical_immutability":
        immutability_pass,

    "router_compatibility":
        router_pass,
}


for key, value in checks.items():

    print(
        f"{key.upper():34}: {value}"
    )


overall_pass = all(
    checks.values()
)


result = {

    "step":
        "STEP V2-06I-F-03B",

    "checks":
        checks,

    "event_count":
        len(events),

    "json_line_count":
        len(lines),

    "parse_errors":
        parse_errors,

    "field_errors":
        field_errors,

    "event_order":
        event_order,

    "query_ids":
        sorted(query_ids),

    "trace_ids":
        sorted(trace_ids),

    "sample_cloudwatch_record":
        parsed[-1]
        if parsed
        else None,

    "overall_pass":
        overall_pass,

    "provider_call":
        False,

    "aws_mutation":
        False,

    "langsmith_call":
        False,

    "databricks_call":
        False,

    "v13_modified":
        False,
}


output_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

output_path.write_text(
    json.dumps(
        result,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print(
    "OVERALL PASS :",
    overall_pass
)

print(
    "OUTPUT FILE  :",
    output_path
)


print()
print("============================================================")

if overall_pass:

    print(
        "STEP V2-06I-F-03B: PASS"
    )

    print(
        "STRUCTURED JSON SINK : VALIDATED"
    )

    print(
        "ECS AWSLOGS COMPATIBLE: VALIDATED"
    )

else:

    print(
        "STEP V2-06I-F-03B: REVIEW REQUIRED"
    )

print("============================================================")


raise SystemExit(
    0 if overall_pass else 2
)
