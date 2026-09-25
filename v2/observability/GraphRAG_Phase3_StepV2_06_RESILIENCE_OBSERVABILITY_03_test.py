import sys
import json
import tempfile
import importlib.util
from pathlib import Path


emitter_path = Path(sys.argv[1])
wrapper_path = Path(sys.argv[2])
schema_path = Path(sys.argv[3])


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


emitter_module = load_module(
    "v2_event_emitter",
    emitter_path,
)

wrapper_module = load_module(
    "v2_resilience_wrapper_for_obs",
    wrapper_path,
)


normalize_resilience_events = (
    emitter_module.normalize_resilience_events
)

validate_against_contract = (
    emitter_module.validate_against_contract
)

JsonlResilienceEventEmitter = (
    emitter_module.JsonlResilienceEventEmitter
)

ResilienceEvent = (
    wrapper_module.ResilienceEvent
)

ResilienceResult = (
    wrapper_module.ResilienceResult
)


schema = json.loads(
    schema_path.read_text(
        encoding="utf-8-sig"
    )
)


# ==========================================================
# REPRODUCE THE SUCCESSFUL 06H-D EVENT SEQUENCE
# ==========================================================

raw_events = [

    ResilienceEvent(
        provider="openai",
        attempt=1,
        event="ATTEMPT",
    ),

    ResilienceEvent(
        provider="openai",
        attempt=1,
        event="RETRYABLE_FAILURE",
        error_type="ProviderTimeoutError",
        message="Controlled timeout",
    ),

    ResilienceEvent(
        provider="openai",
        attempt=1,
        event="BACKOFF",
        message="0.25",
    ),

    ResilienceEvent(
        provider="openai",
        attempt=2,
        event="ATTEMPT",
    ),

    ResilienceEvent(
        provider="openai",
        attempt=2,
        event="RETRYABLE_FAILURE",
        error_type="ProviderTimeoutError",
        message="Controlled timeout",
    ),

    ResilienceEvent(
        provider="deepseek",
        attempt=1,
        event="FALLBACK_START",
    ),

    ResilienceEvent(
        provider="deepseek",
        attempt=1,
        event="SUCCESS",
    ),
]


result = ResilienceResult(

    success=True,

    provider_used="deepseek",

    response="GRAPHRAG_V2_FAILOVER_OK",

    fallback_used=True,

    primary_attempts=2,

    fallback_attempts=1,

    final_error=None,

    events=raw_events,
)


normalized = normalize_resilience_events(

    result,

    query_id="query-v2-06i-c-001",

    trace_id="trace-v2-06i-c-001",

    service="multi-agent-graphrag",

    environment="local-test",

    primary_provider="openai",

    fallback_provider="deepseek",

    latency_ms=250.0,

    metadata={
        "step": "STEP V2-06I-C",
        "controlled_failure": True,
    },
)


# ==========================================================
# VALIDATE
# ==========================================================

errors = validate_against_contract(
    normalized,
    schema,
)

event_types = [
    event["event_type"]
    for event in normalized
]

expected_event_types = [

    "ATTEMPT",

    "RETRYABLE_FAILURE",

    "BACKOFF",

    "ATTEMPT",

    "RETRYABLE_FAILURE",

    "FALLBACK_START",

    "SUCCESS",
]


print()
print("===== NORMALIZATION RESULT =====")

print(
    "RAW EVENT COUNT        :",
    len(raw_events),
)

print(
    "NORMALIZED EVENT COUNT :",
    len(normalized),
)

print(
    "EVENT ORDER PASS       :",
    event_types == expected_event_types,
)

print(
    "CONTRACT ERROR COUNT   :",
    len(errors),
)

print(
    "CONTRACT PASS          :",
    len(errors) == 0,
)


retry_events = [
    event
    for event in normalized
    if event["event_type"]
    == "RETRYABLE_FAILURE"
]

fallback_events = [
    event
    for event in normalized
    if event["event_type"]
    == "FALLBACK_START"
]

recovery_events = [
    event
    for event in normalized
    if event["recovered"]
]


print()
print("===== SEMANTIC VALIDATION =====")

print(
    "RETRY EVENT COUNT      :",
    len(retry_events),
)

print(
    "FALLBACK EVENT COUNT   :",
    len(fallback_events),
)

print(
    "RECOVERY EVENT COUNT   :",
    len(recovery_events),
)

print(
    "RETRYABLE FLAGS PASS   :",
    all(
        event["retryable"]
        for event in retry_events
    ),
)

print(
    "FALLBACK FLAG PASS     :",
    (
        len(fallback_events) == 1
        and fallback_events[0][
            "fallback_used"
        ]
    ),
)

print(
    "RECOVERY FLAG PASS     :",
    (
        len(recovery_events) == 1
        and recovery_events[0][
            "provider"
        ] == "deepseek"
        and recovery_events[0][
            "event_type"
        ] == "SUCCESS"
    ),
)


# ==========================================================
# JSONL EMITTER TEST
# ==========================================================

with tempfile.TemporaryDirectory() as temp_dir:

    output_path = (
        Path(temp_dir)
        / "resilience_events.jsonl"
    )

    emitter = JsonlResilienceEventEmitter(
        output_path
    )

    emitted_count = emitter.emit(
        normalized
    )

    lines = output_path.read_text(
        encoding="utf-8"
    ).splitlines()

    parsed = [
        json.loads(line)
        for line in lines
    ]

    print()
    print("===== JSONL EMITTER VALIDATION =====")

    print(
        "EMITTED COUNT          :",
        emitted_count,
    )

    print(
        "JSONL LINE COUNT       :",
        len(lines),
    )

    print(
        "JSON PARSE PASS        :",
        len(parsed)
        == len(normalized),
    )

    print(
        "QUERY ID PASS          :",
        all(
            event["query_id"]
            == "query-v2-06i-c-001"
            for event in parsed
        ),
    )

    print(
        "TRACE ID PASS          :",
        all(
            event["trace_id"]
            == "trace-v2-06i-c-001"
            for event in parsed
        ),
    )


# ==========================================================
# FINAL GATE
# ==========================================================

passed = all([

    len(normalized)
        == len(raw_events),

    event_types
        == expected_event_types,

    len(errors)
        == 0,

    len(retry_events)
        == 2,

    len(fallback_events)
        == 1,

    len(recovery_events)
        == 1,

    all(
        event["retryable"]
        for event in retry_events
    ),

    fallback_events[0][
        "fallback_used"
    ],

    recovery_events[0][
        "provider"
    ] == "deepseek",

    emitted_count
        == len(normalized),

    len(parsed)
        == len(normalized),
])


print()
print("============================================================")

if passed:

    print("STEP V2-06I-C: PASS")

    print(
        "EVENT NORMALIZER       : VALIDATED"
    )

    print(
        "SCHEMA CONTRACT        : VALIDATED"
    )

    print(
        "RETRY TELEMETRY        : VALIDATED"
    )

    print(
        "FALLBACK TELEMETRY     : VALIDATED"
    )

    print(
        "RECOVERY TELEMETRY     : VALIDATED"
    )

    print(
        "JSONL EMITTER          : VALIDATED"
    )

else:

    print(
        "STEP V2-06I-C: REVIEW REQUIRED"
    )

    for error in errors:
        print("ERROR:", error)


print("============================================================")

raise SystemExit(
    0 if passed else 2
)
