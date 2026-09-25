from __future__ import annotations

from math import ceil
from typing import Any, Dict, Iterable, List, Optional


def _rate(
    numerator: int,
    denominator: int,
) -> Optional[float]:
    if denominator == 0:
        return None

    return round(
        numerator / denominator,
        6,
    )


def _percentile_nearest_rank(
    values: List[float],
    percentile: float,
) -> Optional[float]:
    if not values:
        return None

    ordered = sorted(values)

    rank = ceil(
        percentile * len(ordered)
    )

    index = max(
        0,
        min(rank - 1, len(ordered) - 1),
    )

    return ordered[index]


def calculate_governance_metrics(
    records: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:

    rows = list(records)

    total_queries = len(rows)

    guardrail_evaluated = [
        r for r in rows
        if r.get("guardrail_pass") is not None
    ]

    guardrail_passed = [
        r for r in guardrail_evaluated
        if r.get("guardrail_pass") is True
    ]

    retried = [
        r for r in rows
        if r.get("retry_used") is True
    ]

    retry_recovered = [
        r for r in retried
        if r.get("retry_recovered") is True
    ]

    escalated = [
        r for r in rows
        if r.get("escalated") is True
    ]

    evidence_evaluated = [
        r for r in rows
        if r.get("evidence_required") is True
    ]

    missing_evidence = [
        r for r in evidence_evaluated
        if r.get("missing_evidence") is True
    ]

    provenance_evaluated = [
        r for r in rows
        if r.get("provenance_evaluated") is True
    ]

    provenance_failed = [
        r for r in provenance_evaluated
        if r.get("provenance_failed") is True
    ]

    span_evaluated = [
        r for r in rows
        if r.get("span_evaluated") is True
    ]

    unknown_span = [
        r for r in span_evaluated
        if r.get("unknown_span") is True
    ]

    schema_evaluated = [
        r for r in rows
        if r.get("provider_schema_evaluated") is True
    ]

    schema_failed = [
        r for r in schema_evaluated
        if r.get("provider_schema_failed") is True
    ]

    judge_executed = [
        r for r in rows
        if r.get("judge_executed") is True
    ]

    judge_rejected = [
        r for r in judge_executed
        if r.get("judge_rejected") is True
    ]

    evaluation_valid = [
        r for r in rows
        if r.get("evaluation_known_valid") is True
    ]

    false_positive_guardrail = [
        r for r in evaluation_valid
        if r.get("guardrail_pass") is False
    ]

    latencies = [
        float(r["latency_ms"])
        for r in rows
        if r.get("latency_ms") is not None
    ]

    return {
        "query_count": total_queries,

        "guardrail_pass_rate": _rate(
            len(guardrail_passed),
            len(guardrail_evaluated),
        ),

        "retry_rate": _rate(
            len(retried),
            total_queries,
        ),

        "retry_recovery_rate": _rate(
            len(retry_recovered),
            len(retried),
        ),

        "escalation_rate": _rate(
            len(escalated),
            total_queries,
        ),

        "missing_evidence_rate": _rate(
            len(missing_evidence),
            len(evidence_evaluated),
        ),

        "citation_mismatch_rate": None,

        "provenance_failure_rate": _rate(
            len(provenance_failed),
            len(provenance_evaluated),
        ),

        "unknown_span_rate": _rate(
            len(unknown_span),
            len(span_evaluated),
        ),

        "provider_schema_failure_rate": _rate(
            len(schema_failed),
            len(schema_evaluated),
        ),

        "judge_rejection_rate": _rate(
            len(judge_rejected),
            len(judge_executed),
        ),

        "false_positive_guardrail_rate": _rate(
            len(false_positive_guardrail),
            len(evaluation_valid),
        ),

        "p95_latency_ms": _percentile_nearest_rank(
            latencies,
            0.95,
        ),

        "cost_per_governed_query": None,

        "signal_status": {
            "citation_mismatch_rate":
                "SIGNAL_REQUIRED",

            "cost_per_governed_query":
                "SIGNAL_REQUIRED",
        },
    }