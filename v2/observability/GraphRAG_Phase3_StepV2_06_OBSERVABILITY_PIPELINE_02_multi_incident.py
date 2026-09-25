from pathlib import Path
from collections import Counter, defaultdict
import json
import sys
import uuid
from datetime import datetime, timezone


output_path = Path(sys.argv[1])


# ============================================================
# STANDARD EVENT FACTORY
# ============================================================

def make_event(
    query_id,
    trace_id,
    provider,
    attempt,
    event_type,
    retryable=False,
    fallback_used=False,
    recovered=False,
):

    return {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "service": "GraphRAG-AWS-V2",
        "environment": "validation",
        "query_id": query_id,
        "trace_id": trace_id,
        "provider": provider,
        "attempt": attempt,
        "event_type": event_type,
        "retryable": retryable,
        "fallback_used": fallback_used,
        "recovered": recovered,
    }


events = []


# ============================================================
# Q1 - PRIMARY SUCCESS
# ============================================================

events.extend([

    make_event(
        "Q1",
        "T1",
        "openai",
        1,
        "ATTEMPT",
    ),

    make_event(
        "Q1",
        "T1",
        "openai",
        1,
        "SUCCESS",
    ),
])


# ============================================================
# Q2 - RETRY RECOVERY ON PRIMARY
# ============================================================

events.extend([

    make_event(
        "Q2",
        "T2",
        "openai",
        1,
        "ATTEMPT",
    ),

    make_event(
        "Q2",
        "T2",
        "openai",
        1,
        "RETRYABLE_FAILURE",
        retryable=True,
    ),

    make_event(
        "Q2",
        "T2",
        "openai",
        1,
        "BACKOFF",
    ),

    make_event(
        "Q2",
        "T2",
        "openai",
        2,
        "ATTEMPT",
    ),

    make_event(
        "Q2",
        "T2",
        "openai",
        2,
        "SUCCESS",
        recovered=True,
    ),
])


# ============================================================
# Q3 - FALLBACK RECOVERY
# ============================================================

events.extend([

    make_event(
        "Q3",
        "T3",
        "openai",
        1,
        "ATTEMPT",
    ),

    make_event(
        "Q3",
        "T3",
        "openai",
        1,
        "RETRYABLE_FAILURE",
        retryable=True,
    ),

    make_event(
        "Q3",
        "T3",
        "openai",
        1,
        "BACKOFF",
    ),

    make_event(
        "Q3",
        "T3",
        "openai",
        2,
        "ATTEMPT",
    ),

    make_event(
        "Q3",
        "T3",
        "openai",
        2,
        "RETRYABLE_FAILURE",
        retryable=True,
    ),

    make_event(
        "Q3",
        "T3",
        "deepseek",
        1,
        "FALLBACK_START",
        fallback_used=True,
    ),

    make_event(
        "Q3",
        "T3",
        "deepseek",
        1,
        "SUCCESS",
        fallback_used=True,
        recovered=True,
    ),
])


# ============================================================
# Q4 - FALLBACK FAILURE / FAIL CLOSED
# ============================================================

events.extend([

    make_event(
        "Q4",
        "T4",
        "openai",
        1,
        "ATTEMPT",
    ),

    make_event(
        "Q4",
        "T4",
        "openai",
        1,
        "RETRYABLE_FAILURE",
        retryable=True,
    ),

    make_event(
        "Q4",
        "T4",
        "openai",
        1,
        "BACKOFF",
    ),

    make_event(
        "Q4",
        "T4",
        "openai",
        2,
        "ATTEMPT",
    ),

    make_event(
        "Q4",
        "T4",
        "openai",
        2,
        "RETRYABLE_FAILURE",
        retryable=True,
    ),

    make_event(
        "Q4",
        "T4",
        "deepseek",
        1,
        "FALLBACK_START",
        fallback_used=True,
    ),

    make_event(
        "Q4",
        "T4",
        "deepseek",
        1,
        "FALLBACK_FAILURE",
        fallback_used=True,
    ),
])


print()
print("===== C. DATASET SUMMARY =====")

print("TOTAL EVENTS       :", len(events))
print(
    "TOTAL QUERIES      :",
    len(set(e["query_id"] for e in events))
)
print(
    "TOTAL TRACES       :",
    len(set(e["trace_id"] for e in events))
)


# ============================================================
# GROUP EVENTS BY QUERY
# ============================================================

grouped = defaultdict(list)

for event in events:

    grouped[event["query_id"]].append(
        event
    )


# ============================================================
# INCIDENT CLASSIFICATION
# ============================================================

incident_rows = []

for query_id, query_events in sorted(
    grouped.items()
):

    event_types = [
        e["event_type"]
        for e in query_events
    ]

    retry_count = sum(
        1
        for e in query_events
        if e["event_type"]
            == "RETRYABLE_FAILURE"
    )

    fallback_triggered = any(
        e["event_type"]
            == "FALLBACK_START"
        for e in query_events
    )

    recovered = any(
        e["recovered"] is True
        for e in query_events
    )

    success = (
        query_events[-1]["event_type"]
            == "SUCCESS"
    )

    final_provider = (
        query_events[-1]["provider"]
    )

    if (
        success
        and retry_count == 0
        and not fallback_triggered
    ):

        outcome = "PRIMARY_SUCCESS"

    elif (
        success
        and retry_count > 0
        and not fallback_triggered
    ):

        outcome = "RETRY_RECOVERY"

    elif (
        success
        and fallback_triggered
    ):

        outcome = "FALLBACK_RECOVERY"

    else:

        outcome = "FAIL_CLOSED"


    incident_rows.append({
        "query_id": query_id,
        "trace_id":
            query_events[0]["trace_id"],
        "event_count":
            len(query_events),
        "retryable_failure_count":
            retry_count,
        "fallback_triggered":
            fallback_triggered,
        "recovered":
            recovered,
        "success":
            success,
        "final_provider":
            final_provider,
        "final_event":
            query_events[-1]["event_type"],
        "outcome":
            outcome,
    })


print()
print("===== D. INCIDENT CLASSIFICATION =====")

for row in incident_rows:

    print(
        row["query_id"],
        "|",
        row["outcome"],
        "| retries=",
        row["retryable_failure_count"],
        "| fallback=",
        row["fallback_triggered"],
        "| recovered=",
        row["recovered"],
        "| final_provider=",
        row["final_provider"],
    )


# ============================================================
# PORTFOLIO METRICS
# ============================================================

total_queries = len(incident_rows)

queries_with_retry = sum(
    row["retryable_failure_count"] > 0
    for row in incident_rows
)

queries_with_fallback = sum(
    row["fallback_triggered"]
    for row in incident_rows
)

recovered_queries = sum(
    row["recovered"]
    for row in incident_rows
)

successful_queries = sum(
    row["success"]
    for row in incident_rows
)

fail_closed_queries = sum(
    row["outcome"] == "FAIL_CLOSED"
    for row in incident_rows
)

retry_recovered_queries = sum(
    row["outcome"] == "RETRY_RECOVERY"
    for row in incident_rows
)

fallback_recovered_queries = sum(
    row["outcome"] == "FALLBACK_RECOVERY"
    for row in incident_rows
)


metrics = {

    "total_queries":
        total_queries,

    "successful_queries":
        successful_queries,

    "queries_with_retry":
        queries_with_retry,

    "queries_with_fallback":
        queries_with_fallback,

    "recovered_queries":
        recovered_queries,

    "retry_recovered_queries":
        retry_recovered_queries,

    "fallback_recovered_queries":
        fallback_recovered_queries,

    "fail_closed_queries":
        fail_closed_queries,

    "retry_rate":
        queries_with_retry / total_queries,

    "fallback_rate":
        queries_with_fallback / total_queries,

    "overall_recovery_rate":
        recovered_queries / total_queries,

    "retry_recovery_rate":
        retry_recovered_queries
        / queries_with_retry
        if queries_with_retry
        else 0,

    "fallback_recovery_rate":
        fallback_recovered_queries
        / queries_with_fallback
        if queries_with_fallback
        else 0,

    "success_rate":
        successful_queries / total_queries,

    "fail_closed_rate":
        fail_closed_queries / total_queries,
}


print()
print("===== E. DERIVED DASHBOARD METRICS =====")

for key, value in metrics.items():

    if isinstance(value, float):

        print(
            f"{key.upper():28}: {value:.2%}"
        )

    else:

        print(
            f"{key.upper():28}: {value}"
        )


# ============================================================
# EXPECTED VALUES
# ============================================================

expected = {

    "total_queries": 4,

    "successful_queries": 3,

    "queries_with_retry": 3,

    "queries_with_fallback": 2,

    "recovered_queries": 2,

    "retry_recovered_queries": 1,

    "fallback_recovered_queries": 1,

    "fail_closed_queries": 1,

    "retry_rate": 0.75,

    "fallback_rate": 0.50,

    "overall_recovery_rate": 0.50,

    "retry_recovery_rate":
        1 / 3,

    "fallback_recovery_rate":
        0.50,

    "success_rate":
        0.75,

    "fail_closed_rate":
        0.25,
}


metric_checks = {}

for key, expected_value in expected.items():

    actual = metrics[key]

    if isinstance(expected_value, float):

        metric_checks[key] = (
            abs(
                actual - expected_value
            ) < 1e-9
        )

    else:

        metric_checks[key] = (
            actual == expected_value
        )


# ============================================================
# INCIDENT EXPECTATIONS
# ============================================================

expected_outcomes = {
    "Q1": "PRIMARY_SUCCESS",
    "Q2": "RETRY_RECOVERY",
    "Q3": "FALLBACK_RECOVERY",
    "Q4": "FAIL_CLOSED",
}


incident_checks = {

    row["query_id"]:
        row["outcome"]
        == expected_outcomes[
            row["query_id"]
        ]

    for row in incident_rows
}


# ============================================================
# CORRELATION / UNIQUENESS
# ============================================================

event_ids = [
    e["event_id"]
    for e in events
]

event_id_pass = (
    len(event_ids)
    == len(set(event_ids))
)

trace_per_query_pass = all(

    len({
        e["trace_id"]
        for e in query_events
    }) == 1

    for query_events
    in grouped.values()
)


# ============================================================
# FINAL
# ============================================================

all_metrics_pass = all(
    metric_checks.values()
)

all_incidents_pass = all(
    incident_checks.values()
)

overall_pass = all([
    len(events) == 21,
    len(grouped) == 4,
    event_id_pass,
    trace_per_query_pass,
    all_metrics_pass,
    all_incidents_pass,
])


result = {

    "step":
        "STEP V2-06I-E-02",

    "event_count":
        len(events),

    "incident_count":
        len(incident_rows),

    "incidents":
        incident_rows,

    "metrics":
        metrics,

    "metric_checks":
        metric_checks,

    "incident_checks":
        incident_checks,

    "event_id_uniqueness":
        event_id_pass,

    "trace_per_query":
        trace_per_query_pass,

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
print("===== F. VALIDATION =====")

print(
    "EVENT ID UNIQUENESS :",
    event_id_pass
)

print(
    "TRACE PER QUERY     :",
    trace_per_query_pass
)

print(
    "INCIDENT CHECKS     :",
    all_incidents_pass
)

print(
    "METRIC CHECKS       :",
    all_metrics_pass
)

print(
    "OVERALL PASS        :",
    overall_pass
)

print(
    "OUTPUT FILE         :",
    output_path
)


print()
print("============================================================")

if overall_pass:

    print(
        "STEP V2-06I-E-02: PASS"
    )

    print(
        "MULTI-INCIDENT AGGREGATION : VALIDATED"
    )

    print(
        "DASHBOARD METRICS          : VALIDATED"
    )

    print(
        "FAIL-CLOSED VISIBILITY     : VALIDATED"
    )

else:

    print(
        "STEP V2-06I-E-02: REVIEW REQUIRED"
    )

print("============================================================")


raise SystemExit(
    0 if overall_pass else 2
)
