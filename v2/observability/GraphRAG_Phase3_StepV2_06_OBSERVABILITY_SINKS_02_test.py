from pathlib import Path
from copy import deepcopy
import importlib.util
import json
import sys


router_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])


def load_module(
    name,
    path,
):

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
    "v2_sink_router",
    router_path,
)


MemorySink = router_module.MemorySink
FailingSink = router_module.FailingSink
TelemetrySinkRouter = (
    router_module.TelemetrySinkRouter
)

build_cloudwatch_payload = (
    router_module.build_cloudwatch_payload
)

build_langsmith_payload = (
    router_module.build_langsmith_payload
)


# ============================================================
# CANONICAL SAMPLE EVENT
# ============================================================

event = {

    "schema_version": "1.0",

    "event_id":
        "event-v2-f02-001",

    "timestamp_utc":
        "2026-09-16T17:00:00+00:00",

    "service":
        "GraphRAG-AWS-V2",

    "environment":
        "validation",

    "query_id":
        "query-v2-f02-001",

    "trace_id":
        "trace-v2-f02-001",

    "provider":
        "deepseek",

    "attempt":
        1,

    "event_type":
        "SUCCESS",

    "retryable":
        False,

    "fallback_used":
        True,

    "recovered":
        True,

    "error_type":
        None,

    "message":
        "Fallback recovery succeeded.",

    "latency_ms":
        1202.96,

    "success":
        True,

    "final_provider":
        "deepseek",
}


original_event = deepcopy(event)


print()
print("===== D1. PAYLOAD MAPPING =====")


cloudwatch_payload = (
    build_cloudwatch_payload(event)
)

langsmith_payload = (
    build_langsmith_payload(event)
)


cloudwatch_mapping_pass = all([

    cloudwatch_payload["event_type"]
        == "SUCCESS",

    cloudwatch_payload["provider"]
        == "deepseek",

    cloudwatch_payload["fallback_used"]
        is True,

    cloudwatch_payload["recovered"]
        is True,

    cloudwatch_payload["latency_ms"]
        == 1202.96,

])


langsmith_mapping_pass = all([

    langsmith_payload["name"]
        == "resilience.success",

    langsmith_payload["query_id"]
        == "query-v2-f02-001",

    langsmith_payload["trace_id"]
        == "trace-v2-f02-001",

    langsmith_payload["metadata"][
        "provider"
    ] == "deepseek",

    langsmith_payload["metadata"][
        "fallback_used"
    ] is True,

    langsmith_payload["metadata"][
        "recovered"
    ] is True,

])


print(
    "CLOUDWATCH MAPPING :",
    cloudwatch_mapping_pass
)

print(
    "LANGSMITH MAPPING  :",
    langsmith_mapping_pass
)


print()
print("===== D2. MULTI-SINK DELIVERY =====")


cloudwatch_sink = MemorySink(
    name="cloudwatch_test"
)

langsmith_sink = MemorySink(
    name="langsmith_test"
)


multi_router = TelemetrySinkRouter([
    cloudwatch_sink,
    langsmith_sink,
])


multi_results = (
    multi_router.emit(event)
)


multi_sink_pass = all([
    len(multi_results) == 2,
    all(r.success for r in multi_results),
    len(cloudwatch_sink.received) == 1,
    len(langsmith_sink.received) == 1,
])


print(
    "DELIVERY RESULTS :",
    [
        (r.sink, r.success)
        for r in multi_results
    ]
)

print(
    "MULTI-SINK PASS  :",
    multi_sink_pass
)


print()
print("===== D3. FAILURE ISOLATION =====")


first_sink = MemorySink(
    name="first_good_sink"
)

failure_sink = FailingSink()

last_sink = MemorySink(
    name="last_good_sink"
)


failure_router = TelemetrySinkRouter([
    first_sink,
    failure_sink,
    last_sink,
])


failure_results = (
    failure_router.emit(event)
)


failure_isolation_pass = all([

    len(failure_results) == 3,

    failure_results[0].success
        is True,

    failure_results[1].success
        is False,

    failure_results[2].success
        is True,

    failure_results[1].error_type
        == "RuntimeError",

    failure_results[1].message
        == "CONTROLLED_SINK_FAILURE",

    len(first_sink.received)
        == 1,

    len(last_sink.received)
        == 1,
])


print(
    "DELIVERY RESULTS :",
    [
        (
            r.sink,
            r.success,
            r.error_type,
        )
        for r in failure_results
    ]
)

print(
    "FAILURE ISOLATION:",
    failure_isolation_pass
)


print()
print("===== D4. CANONICAL EVENT IMMUTABILITY =====")


immutability_pass = (
    event == original_event
)


print(
    "ORIGINAL UNCHANGED:",
    immutability_pass
)


print()
print("===== D5. CORRELATION PRESERVATION =====")


correlation_pass = all([

    cloudwatch_payload["query_id"]
        == event["query_id"],

    cloudwatch_payload["trace_id"]
        == event["trace_id"],

    langsmith_payload["query_id"]
        == event["query_id"],

    langsmith_payload["trace_id"]
        == event["trace_id"],
])


print(
    "QUERY/TRACE PRESERVED:",
    correlation_pass
)


print()
print("===== D6. FINAL VALIDATION =====")


checks = {

    "cloudwatch_mapping":
        cloudwatch_mapping_pass,

    "langsmith_mapping":
        langsmith_mapping_pass,

    "multi_sink_delivery":
        multi_sink_pass,

    "failure_isolation":
        failure_isolation_pass,

    "canonical_event_immutability":
        immutability_pass,

    "correlation_preservation":
        correlation_pass,
}


for key, value in checks.items():

    print(
        f"{key.upper():32}: {value}"
    )


overall_pass = all(
    checks.values()
)


result = {

    "step":
        "STEP V2-06I-F-02",

    "checks":
        checks,

    "cloudwatch_payload":
        cloudwatch_payload,

    "langsmith_payload":
        langsmith_payload,

    "multi_sink_results": [
        {
            "sink": r.sink,
            "success": r.success,
            "error_type": r.error_type,
        }
        for r in multi_results
    ],

    "failure_isolation_results": [
        {
            "sink": r.sink,
            "success": r.success,
            "error_type": r.error_type,
            "message": r.message,
        }
        for r in failure_results
    ],

    "overall_pass":
        overall_pass,
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
        "STEP V2-06I-F-02: PASS"
    )

    print(
        "SINK ROUTING       : VALIDATED"
    )

    print(
        "PAYLOAD MAPPING    : VALIDATED"
    )

    print(
        "FAILURE ISOLATION  : VALIDATED"
    )

else:

    print(
        "STEP V2-06I-F-02: REVIEW REQUIRED"
    )

print("============================================================")


raise SystemExit(
    0 if overall_pass else 2
)
