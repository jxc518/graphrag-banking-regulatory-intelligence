from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol


# ============================================================
# SINK CONTRACT
# ============================================================

class TelemetrySink(Protocol):

    name: str

    def emit(
        self,
        event: Dict[str, Any],
    ) -> None:
        ...


# ============================================================
# CLOUDWATCH PAYLOAD MAPPER
# ============================================================

def build_cloudwatch_payload(
    event: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Operational view of canonical telemetry.

    No AWS API call occurs here.
    """

    fields = [
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
        "error_type",
        "message",
        "latency_ms",
        "success",
        "final_provider",
    ]

    return {
        key: deepcopy(event.get(key))
        for key in fields
        if key in event
    }


# ============================================================
# LANGSMITH PAYLOAD MAPPER
# ============================================================

def build_langsmith_payload(
    event: Dict[str, Any],
) -> Dict[str, Any]:

    """
    AI trace/correlation view of canonical telemetry.

    No LangSmith API call occurs here.
    """

    return {

        "name":
            f'resilience.{event["event_type"].lower()}',

        "query_id":
            event["query_id"],

        "trace_id":
            event["trace_id"],

        "metadata": {

            "schema_version":
                event["schema_version"],

            "event_id":
                event["event_id"],

            "provider":
                event["provider"],

            "attempt":
                event["attempt"],

            "event_type":
                event["event_type"],

            "retryable":
                event["retryable"],

            "fallback_used":
                event["fallback_used"],

            "recovered":
                event["recovered"],

            "error_type":
                event.get("error_type"),

            "latency_ms":
                event.get("latency_ms"),

            "final_provider":
                event.get("final_provider"),
        },
    }


# ============================================================
# MEMORY TEST SINK
# ============================================================

@dataclass
class MemorySink:

    name: str
    received: List[Dict[str, Any]] = field(
        default_factory=list
    )

    def emit(
        self,
        event: Dict[str, Any],
    ) -> None:

        self.received.append(
            deepcopy(event)
        )


# ============================================================
# INTENTIONAL FAILURE TEST SINK
# ============================================================

@dataclass
class FailingSink:

    name: str = "intentional_failure"

    def emit(
        self,
        event: Dict[str, Any],
    ) -> None:

        raise RuntimeError(
            "CONTROLLED_SINK_FAILURE"
        )


# ============================================================
# ROUTER RESULT
# ============================================================

@dataclass
class SinkDeliveryResult:

    sink: str
    success: bool
    error_type: str | None = None
    message: str | None = None


# ============================================================
# TELEMETRY SINK ROUTER
# ============================================================

class TelemetrySinkRouter:

    def __init__(
        self,
        sinks: List[TelemetrySink],
    ):

        self.sinks = list(sinks)


    def emit(
        self,
        event: Dict[str, Any],
    ) -> List[SinkDeliveryResult]:

        results = []

        for sink in self.sinks:

            try:

                # Each sink gets its own copy.
                # One sink must not mutate another sink's event.
                sink.emit(
                    deepcopy(event)
                )

                results.append(
                    SinkDeliveryResult(
                        sink=sink.name,
                        success=True,
                    )
                )

            except Exception as exc:

                # Sink failure is isolated.
                # It must not stop delivery to later sinks.
                results.append(
                    SinkDeliveryResult(
                        sink=sink.name,
                        success=False,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )

        return results
