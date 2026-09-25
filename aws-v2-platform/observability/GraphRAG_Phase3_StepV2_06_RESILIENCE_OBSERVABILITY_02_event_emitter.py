from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import uuid


SCHEMA_VERSION = "1.0"

RETRYABLE_EVENT_TYPES = {
    "RETRYABLE_FAILURE",
}

FALLBACK_EVENT_TYPES = {
    "FALLBACK_START",
    "FALLBACK_FAILURE",
}

RECOVERY_EVENT_TYPES = {
    "SUCCESS",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_event_id() -> str:
    return str(uuid.uuid4())


def _event_value(event: Any, field: str, default=None):

    if is_dataclass(event):
        return getattr(event, field, default)

    if isinstance(event, dict):
        return event.get(field, default)

    return getattr(event, field, default)


def normalize_resilience_events(
    resilience_result: Any,
    *,
    query_id: str,
    trace_id: str,
    service: str = "multi-agent-graphrag",
    environment: str = "local-test",
    primary_provider: Optional[str] = None,
    fallback_provider: Optional[str] = None,
    latency_ms: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:

    """
    Convert existing 06E ResilienceResult.events into the
    canonical V2 resilience telemetry schema.

    This function does NOT modify 06E and performs no
    provider, AWS, LangSmith, or Databricks calls.
    """

    metadata = dict(metadata or {})

    events = list(
        getattr(resilience_result, "events", []) or []
    )

    final_provider = getattr(
        resilience_result,
        "provider_used",
        None,
    )

    overall_success = bool(
        getattr(
            resilience_result,
            "success",
            False,
        )
    )

    overall_fallback = bool(
        getattr(
            resilience_result,
            "fallback_used",
            False,
        )
    )

    primary_attempts = getattr(
        resilience_result,
        "primary_attempts",
        None,
    )

    fallback_attempts = getattr(
        resilience_result,
        "fallback_attempts",
        None,
    )

    normalized: List[Dict[str, Any]] = []

    fallback_started = False
    prior_failure_seen = False

    for raw_event in events:

        event_type = _event_value(
            raw_event,
            "event",
        )

        provider = _event_value(
            raw_event,
            "provider",
        )

        attempt = _event_value(
            raw_event,
            "attempt",
            0,
        )

        error_type = _event_value(
            raw_event,
            "error_type",
        )

        message = _event_value(
            raw_event,
            "message",
        )

        if event_type in {
            "RETRYABLE_FAILURE",
            "NON_RETRYABLE_FAILURE",
            "UNCLASSIFIED_FAILURE",
            "FALLBACK_FAILURE",
            "RETRY_BUDGET_EXHAUSTED_NO_FALLBACK",
        }:
            prior_failure_seen = True

        if event_type == "FALLBACK_START":
            fallback_started = True

        retryable = (
            event_type
            in RETRYABLE_EVENT_TYPES
        )

        fallback_used = (
            fallback_started
            or (
                overall_fallback
                and provider == fallback_provider
            )
        )

        recovered = (
            event_type == "SUCCESS"
            and prior_failure_seen
            and overall_success
        )

        record = {

            "schema_version": SCHEMA_VERSION,

            "event_id": _new_event_id(),

            "timestamp_utc": _utc_now(),

            "service": service,

            "environment": environment,

            "query_id": query_id,

            "trace_id": trace_id,

            "provider": provider,

            "attempt": int(attempt),

            "event_type": event_type,

            "retryable": retryable,

            "fallback_used": fallback_used,

            "recovered": recovered,

            "error_type": error_type,

            "message": message,

            "latency_ms": latency_ms,

            "primary_provider": primary_provider,

            "fallback_provider": fallback_provider,

            "primary_attempts": primary_attempts,

            "fallback_attempts": fallback_attempts,

            "final_provider": final_provider,

            "success": overall_success,

            "metadata": metadata,
        }

        normalized.append(record)

    return normalized


def validate_against_contract(
    events: Iterable[Dict[str, Any]],
    schema: Dict[str, Any],
) -> List[str]:

    """
    Lightweight contract validation against the canonical
    JSON schema artifact created in STEP V2-06I-B.
    """

    errors: List[str] = []

    required_fields = schema[
        "required_fields"
    ]

    allowed_events = set(
        schema["allowed_event_types"]
    )

    for index, event in enumerate(events):

        for field in required_fields:

            if field not in event:
                errors.append(
                    f"event[{index}] missing required field: {field}"
                )

        event_type = event.get(
            "event_type"
        )

        if event_type not in allowed_events:
            errors.append(
                f"event[{index}] invalid event_type: {event_type}"
            )

        attempt = event.get(
            "attempt"
        )

        if not isinstance(attempt, int):
            errors.append(
                f"event[{index}] attempt must be int"
            )

        for field in [
            "retryable",
            "fallback_used",
            "recovered",
        ]:

            if not isinstance(
                event.get(field),
                bool,
            ):
                errors.append(
                    f"event[{index}] {field} must be bool"
                )

    return errors


class JsonlResilienceEventEmitter:

    """
    Additive local structured-event sink.

    Later CloudWatch / LangSmith / Databricks exporters can
    consume the same canonical event dictionaries.
    """

    def __init__(
        self,
        output_path: Path | str,
    ) -> None:

        self.output_path = Path(
            output_path
        )

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def emit(
        self,
        events: Iterable[Dict[str, Any]],
    ) -> int:

        count = 0

        with self.output_path.open(
            "a",
            encoding="utf-8",
        ) as handle:

            for event in events:

                handle.write(
                    json.dumps(
                        event,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )

                count += 1

        return count
