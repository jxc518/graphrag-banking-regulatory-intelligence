from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional, Protocol


# ============================================================
# CLIENT CONTRACT
# ============================================================

class LangSmithClientProtocol(Protocol):

    def create_run(
        self,
        name: str,
        inputs: Dict[str, Any],
        run_type: str,
        **kwargs: Any,
    ) -> None:
        ...


# ============================================================
# LANGSMITH SINK
# ============================================================

class LangSmithSink:
    """
    Additive LangSmith observability sink.

    Design goals:
    - Accept the canonical V2 telemetry event.
    - Preserve query/trace correlation.
    - Keep LangSmith-specific logic outside the GraphRAG runtime.
    - Support dependency injection for offline testing.
    """

    name = "langsmith"

    def __init__(
        self,
        client: LangSmithClientProtocol,
        project_name: Optional[str] = None,
    ) -> None:

        self.client = client
        self.project_name = project_name


    def emit(
        self,
        event: Dict[str, Any],
    ) -> None:

        payload = self._build_payload(event)

        kwargs: Dict[str, Any] = {
            "name": payload["name"],
            "inputs": {
                "query_id": payload["query_id"],
                "trace_id": payload["trace_id"],
            },
            "run_type": "tool",
            "extra": {
                "metadata": deepcopy(payload["metadata"])
            },
        }

        if self.project_name:
            kwargs["project_name"] = self.project_name

        self.client.create_run(**kwargs)


    @staticmethod
    def _build_payload(
        event: Dict[str, Any],
    ) -> Dict[str, Any]:

        required = [
            "schema_version",
            "event_id",
            "query_id",
            "trace_id",
            "provider",
            "attempt",
            "event_type",
            "retryable",
            "fallback_used",
            "recovered",
        ]

        missing = [
            field
            for field in required
            if field not in event
        ]

        if missing:
            raise ValueError(
                "LANGSMITH_SINK_MISSING_FIELDS: "
                + ",".join(missing)
            )

        return {
            "name":
                f'resilience.{str(event["event_type"]).lower()}',

            "query_id":
                deepcopy(event["query_id"]),

            "trace_id":
                deepcopy(event["trace_id"]),

            "metadata": {
                "schema_version":
                    deepcopy(event["schema_version"]),

                "event_id":
                    deepcopy(event["event_id"]),

                "provider":
                    deepcopy(event["provider"]),

                "attempt":
                    deepcopy(event["attempt"]),

                "event_type":
                    deepcopy(event["event_type"]),

                "retryable":
                    deepcopy(event["retryable"]),

                "fallback_used":
                    deepcopy(event["fallback_used"]),

                "recovered":
                    deepcopy(event["recovered"]),

                "error_type":
                    deepcopy(event.get("error_type")),

                "latency_ms":
                    deepcopy(event.get("latency_ms")),

                "final_provider":
                    deepcopy(event.get("final_provider")),
            },
        }
