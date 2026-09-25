from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, Iterable, List


def resilience_events_to_query_records(
    events: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Aggregate canonical resilience events to one record per query.

    This adapter does NOT own:
      - retry logic
      - fallback logic
      - provider execution
      - canonical event generation
      - guardrail logic
      - judge logic

    It only translates event-grain telemetry into query-grain
    governance metric records.
    """

    source_events = list(events)

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for event in source_events:
        query_id = event.get("query_id")

        if not query_id:
            raise ValueError(
                "QUERY_ADAPTER_MISSING_QUERY_ID"
            )

        grouped[str(query_id)].append(
            deepcopy(event)
        )

    records: List[Dict[str, Any]] = []

    for query_id, query_events in grouped.items():

        event_types = {
            str(event.get("event_type", "")).upper()
            for event in query_events
        }

        retry_used = (
            "RETRYABLE_FAILURE" in event_types
            or any(
                bool(event.get("retryable"))
                for event in query_events
            )
        )

        retry_recovered = (
            retry_used
            and any(
                bool(event.get("recovered"))
                for event in query_events
            )
        )

        fallback_used = any(
            bool(event.get("fallback_used"))
            for event in query_events
        )

        success_events = [
            event
            for event in query_events
            if str(
                event.get("event_type", "")
            ).upper() == "SUCCESS"
        ]

        terminal_event = (
            success_events[-1]
            if success_events
            else query_events[-1]
        )

        final_provider = terminal_event.get(
            "final_provider"
        )

        if final_provider is None:
            final_provider = terminal_event.get(
                "provider"
            )

        latency_values = [
            float(event["latency_ms"])
            for event in query_events
            if event.get("latency_ms") is not None
        ]

        # Canonical resilience events for one query may repeat
        # the same end-to-end latency. Do NOT sum event latency.
        latency_ms = (
            max(latency_values)
            if latency_values
            else None
        )

        provider_schema_failed = any(
            (
                "SCHEMA" in str(
                    event.get("error_type", "")
                ).upper()
                or "JSON" in str(
                    event.get("error_type", "")
                ).upper()
            )
            for event in query_events
        )

        record = {
            "query_id": query_id,

            # Resilience-derived governance fields
            "retry_used": retry_used,
            "retry_recovered": retry_recovered,
            "fallback_used": fallback_used,
            "final_provider": final_provider,
            "provider_schema_evaluated": True,
            "provider_schema_failed": provider_schema_failed,
            "latency_ms": latency_ms,

            # Diagnostic lineage
            "resilience_event_count": len(query_events),
            "resilience_event_types": sorted(event_types),

            # Guardrail / Judge fields intentionally not invented.
            # They will be populated by a separate governed-state mapping.
            "guardrail_pass": None,
            "escalated": False,

            "evidence_required": False,
            "missing_evidence": False,

            "provenance_evaluated": False,
            "provenance_failed": False,

            "span_evaluated": False,
            "unknown_span": False,

            "judge_executed": False,
            "judge_rejected": False,

            "evaluation_known_valid": False,
        }

        records.append(record)

    return records