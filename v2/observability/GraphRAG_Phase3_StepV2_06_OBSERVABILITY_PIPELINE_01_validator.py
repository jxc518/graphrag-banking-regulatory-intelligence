from pathlib import Path
import json
import sys
from collections import Counter


telemetry_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])


print()
print("===== STEP V2-06I-E-01 PYTHON VALIDATION =====")


# ============================================================
# 1. LOAD JSONL
# ============================================================

print()
print("===== B1. JSONL INGESTION =====")

raw_lines = [
    line.strip()
    for line in telemetry_path.read_text(
        encoding="utf-8-sig"
    ).splitlines()
    if line.strip()
]

events = []
parse_errors = []

for index, line in enumerate(raw_lines, start=1):

    try:
        events.append(
            json.loads(line)
        )

    except Exception as exc:

        parse_errors.append({
            "line": index,
            "error": str(exc),
        })


print("RAW LINE COUNT       :", len(raw_lines))
print("PARSED EVENT COUNT   :", len(events))
print("JSON PARSE ERRORS    :", len(parse_errors))
print(
    "JSON PARSE PASS      :",
    len(parse_errors) == 0
)


# ============================================================
# 2. REQUIRED FIELD VALIDATION
# ============================================================

print()
print("===== B2. CONTRACT FIELD VALIDATION =====")

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

for index, event in enumerate(events, start=1):

    missing = [
        field
        for field in required_fields
        if field not in event
    ]

    if missing:

        field_errors.append({
            "event": index,
            "missing": missing,
        })


print("REQUIRED FIELDS      :", len(required_fields))
print("FIELD ERROR COUNT    :", len(field_errors))
print(
    "FIELD CONTRACT PASS  :",
    len(field_errors) == 0
)


# ============================================================
# 3. SCHEMA CONSISTENCY
# ============================================================

print()
print("===== B3. SCHEMA CONSISTENCY =====")

schema_versions = {
    event.get("schema_version")
    for event in events
}

schema_pass = (
    len(schema_versions) == 1
    and None not in schema_versions
)

print(
    "SCHEMA VERSIONS      :",
    sorted(
        str(x)
        for x in schema_versions
    )
)

print(
    "SCHEMA CONSISTENT    :",
    schema_pass
)


# ============================================================
# 4. CORRELATION VALIDATION
# ============================================================

print()
print("===== B4. CORRELATION VALIDATION =====")

query_ids = {
    event.get("query_id")
    for event in events
}

trace_ids = {
    event.get("trace_id")
    for event in events
}

event_ids = [
    event.get("event_id")
    for event in events
]

query_pass = (
    len(query_ids) == 1
    and None not in query_ids
)

trace_pass = (
    len(trace_ids) == 1
    and None not in trace_ids
)

event_id_pass = (
    len(event_ids) == len(set(event_ids))
    and None not in event_ids
)


print("QUERY ID COUNT       :", len(query_ids))
print("TRACE ID COUNT       :", len(trace_ids))
print(
    "UNIQUE EVENT IDS     :",
    len(set(event_ids))
)

print("QUERY CORRELATION     :", query_pass)
print("TRACE CORRELATION     :", trace_pass)
print("EVENT ID UNIQUENESS   :", event_id_pass)


# ============================================================
# 5. EVENT ORDER VALIDATION
# ============================================================

print()
print("===== B5. EVENT ORDER VALIDATION =====")

actual_sequence = [
    event.get("event_type")
    for event in events
]

expected_sequence = [
    "ATTEMPT",
    "RETRYABLE_FAILURE",
    "BACKOFF",
    "ATTEMPT",
    "RETRYABLE_FAILURE",
    "FALLBACK_START",
    "SUCCESS",
]

sequence_pass = (
    actual_sequence == expected_sequence
)


print(
    "ACTUAL SEQUENCE      :",
    " -> ".join(actual_sequence)
)

print(
    "EXPECTED SEQUENCE    :",
    " -> ".join(expected_sequence)
)

print(
    "EVENT ORDER PASS      :",
    sequence_pass
)


# ============================================================
# 6. RESILIENCE SEMANTICS
# ============================================================

print()
print("===== B6. RESILIENCE SEMANTICS =====")

event_counts = Counter(
    event.get("event_type")
    for event in events
)

providers = Counter(
    event.get("provider")
    for event in events
)

retry_failures = [
    event
    for event in events
    if event.get("event_type")
        == "RETRYABLE_FAILURE"
]

fallback_events = [
    event
    for event in events
    if event.get("event_type")
        == "FALLBACK_START"
]

recovery_events = [
    event
    for event in events
    if event.get("recovered") is True
]


retry_pass = (
    len(retry_failures) == 2
    and all(
        event.get("provider") == "openai"
        for event in retry_failures
    )
    and all(
        event.get("retryable") is True
        for event in retry_failures
    )
)

fallback_pass = (
    len(fallback_events) == 1
    and fallback_events[0].get("provider")
        == "deepseek"
    and fallback_events[0].get("fallback_used")
        is True
)

recovery_pass = (
    len(recovery_events) == 1
    and recovery_events[0].get("provider")
        == "deepseek"
    and recovery_events[0].get("event_type")
        == "SUCCESS"
    and recovery_events[0].get("fallback_used")
        is True
)


print("RETRY FAILURES       :", len(retry_failures))
print("FALLBACK EVENTS      :", len(fallback_events))
print("RECOVERY EVENTS      :", len(recovery_events))

print("RETRY SEMANTICS      :", retry_pass)
print("FALLBACK SEMANTICS   :", fallback_pass)
print("RECOVERY SEMANTICS   :", recovery_pass)


# ============================================================
# 7. INCIDENT RECONSTRUCTION
# ============================================================

print()
print("===== B7. INCIDENT RECONSTRUCTION =====")

incident = {
    "query_id": (
        next(iter(query_ids))
        if query_pass
        else None
    ),

    "trace_id": (
        next(iter(trace_ids))
        if trace_pass
        else None
    ),

    "primary_provider": (
        events[0].get("provider")
        if events
        else None
    ),

    "final_provider": (
        recovery_events[0].get("provider")
        if recovery_pass
        else None
    ),

    "primary_retryable_failures":
        len(retry_failures),

    "fallback_triggered":
        len(fallback_events) > 0,

    "recovered":
        recovery_pass,

    "final_event": (
        events[-1].get("event_type")
        if events
        else None
    ),
}


incident_pass = (
    incident["primary_provider"]
        == "openai"
    and incident["final_provider"]
        == "deepseek"
    and incident["primary_retryable_failures"]
        == 2
    and incident["fallback_triggered"]
        is True
    and incident["recovered"]
        is True
    and incident["final_event"]
        == "SUCCESS"
)


for key, value in incident.items():

    print(
        f"{key.upper():28}: {value}"
    )


print(
    "INCIDENT RECONSTRUCTION:",
    incident_pass
)


# ============================================================
# 8. OBSERVABILITY METRICS
# ============================================================

print()
print("===== B8. DERIVED OBSERVABILITY METRICS =====")

metrics = {
    "event_count": len(events),

    "attempt_count":
        event_counts["ATTEMPT"],

    "retryable_failure_count":
        event_counts["RETRYABLE_FAILURE"],

    "backoff_count":
        event_counts["BACKOFF"],

    "fallback_count":
        event_counts["FALLBACK_START"],

    "success_count":
        event_counts["SUCCESS"],

    "recovery_count":
        len(recovery_events),

    "openai_event_count":
        providers["openai"],

    "deepseek_event_count":
        providers["deepseek"],
}


for key, value in metrics.items():

    print(
        f"{key.upper():28}: {value}"
    )


metrics_pass = (
    metrics["event_count"] == 7
    and metrics["attempt_count"] == 2
    and metrics["retryable_failure_count"] == 2
    and metrics["backoff_count"] == 1
    and metrics["fallback_count"] == 1
    and metrics["success_count"] == 1
    and metrics["recovery_count"] == 1
)


print(
    "METRICS DERIVATION PASS :",
    metrics_pass
)


# ============================================================
# FINAL VALIDATION
# ============================================================

final_checks = {

    "json_parse":
        len(parse_errors) == 0,

    "field_contract":
        len(field_errors) == 0,

    "schema_consistency":
        schema_pass,

    "query_correlation":
        query_pass,

    "trace_correlation":
        trace_pass,

    "event_id_uniqueness":
        event_id_pass,

    "event_order":
        sequence_pass,

    "retry_semantics":
        retry_pass,

    "fallback_semantics":
        fallback_pass,

    "recovery_semantics":
        recovery_pass,

    "incident_reconstruction":
        incident_pass,

    "metrics_derivation":
        metrics_pass,
}


overall_pass = all(
    final_checks.values()
)


result = {
    "step": "STEP V2-06I-E-01",
    "source_telemetry":
        str(telemetry_path),

    "event_count":
        len(events),

    "checks":
        final_checks,

    "incident":
        incident,

    "metrics":
        metrics,

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
        indent=2
    ),
    encoding="utf-8"
)


print()
print("===== B9. FINAL PIPELINE VALIDATION =====")

for key, value in final_checks.items():

    print(
        f"{key.upper():28}: {value}"
    )


print()
print(
    "OVERALL PIPELINE PASS :",
    overall_pass
)

print(
    "VALIDATION ARTIFACT   :",
    output_path
)


print()
print("============================================================")

if overall_pass:

    print(
        "STEP V2-06I-E-01: PASS"
    )

    print(
        "STANDARD TELEMETRY PIPELINE : VALIDATED"
    )

    print(
        "INCIDENT RECONSTRUCTION      : VALIDATED"
    )

    print(
        "METRICS DERIVATION           : VALIDATED"
    )

else:

    print(
        "STEP V2-06I-E-01: REVIEW REQUIRED"
    )

print("============================================================")


raise SystemExit(
    0 if overall_pass else 2
)
