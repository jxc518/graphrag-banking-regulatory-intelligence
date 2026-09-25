from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Protocol


class EventSinkRouterProtocol(Protocol):

    def emit(self, event: Dict[str, Any]) -> Any:
        ...


@dataclass
class EventDeliverySummary:

    event_count: int
    delivery_count: int
    failed_delivery_count: int


class ResilienceObservabilityComposition:
    """
    Thin V2-only composition layer.

    Responsibility:
        normalized canonical resilience events
            -> multi-sink telemetry router

    This module intentionally does NOT own:
        - provider retry logic
        - fallback logic
        - event normalization
        - CloudWatch transport
        - LangSmith API behavior
    """

    def __init__(
        self,
        router: EventSinkRouterProtocol,
    ) -> None:

        self.router = router


    def deliver_events(
        self,
        events: Iterable[Dict[str, Any]],
    ) -> EventDeliverySummary:

        event_count = 0
        delivery_count = 0
        failed_delivery_count = 0

        for event in events:

            event_count += 1

            # Protect canonical event from downstream mutation.
            routed_event = deepcopy(event)

            results = self.router.emit(
                routed_event
            )

            if results is None:
                continue

            for result in results:

                delivery_count += 1

                if not getattr(
                    result,
                    "success",
                    False,
                ):
                    failed_delivery_count += 1

        return EventDeliverySummary(
            event_count=event_count,
            delivery_count=delivery_count,
            failed_delivery_count=failed_delivery_count,
        )