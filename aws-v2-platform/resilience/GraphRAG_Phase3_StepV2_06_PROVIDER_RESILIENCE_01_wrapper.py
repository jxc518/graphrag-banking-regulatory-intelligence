from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional


ProviderCallable = Callable[[], Awaitable[Any]]


# ============================================================
# FAILURE TYPES
# ============================================================

class ProviderError(Exception):
    """Base provider transport error."""


class RetryableProviderError(ProviderError):
    """Transient failure that may succeed on retry."""


class ProviderTimeoutError(RetryableProviderError):
    pass


class ProviderRateLimitError(RetryableProviderError):
    pass


class ProviderConnectionError(RetryableProviderError):
    pass


class ProviderServerError(RetryableProviderError):
    pass


class NonRetryableProviderError(ProviderError):
    """Configuration/auth/request failure that should fail fast."""


class ProviderAuthenticationError(NonRetryableProviderError):
    pass


class ProviderBadRequestError(NonRetryableProviderError):
    pass


class ProviderConfigurationError(NonRetryableProviderError):
    pass


# ============================================================
# RESULT / EVENT CONTRACT
# ============================================================

@dataclass
class ResilienceEvent:
    provider: str
    attempt: int
    event: str
    error_type: Optional[str] = None
    message: Optional[str] = None


@dataclass
class ResilienceResult:
    success: bool
    provider_used: Optional[str]
    response: Any = None
    fallback_used: bool = False
    primary_attempts: int = 0
    fallback_attempts: int = 0
    final_error: Optional[str] = None
    events: List[ResilienceEvent] = field(default_factory=list)


# ============================================================
# PROVIDER RESILIENCE WRAPPER
# ============================================================

class ProviderResilienceWrapper:

    def __init__(
        self,
        max_primary_retries: int = 1,
        backoff_seconds: float = 1.0,
    ) -> None:

        if max_primary_retries < 0:
            raise ValueError("max_primary_retries must be >= 0")

        if backoff_seconds < 0:
            raise ValueError("backoff_seconds must be >= 0")

        self.max_primary_retries = max_primary_retries
        self.backoff_seconds = backoff_seconds


    async def execute(
        self,
        primary_name: str,
        primary_call: ProviderCallable,
        fallback_name: Optional[str] = None,
        fallback_call: Optional[ProviderCallable] = None,
    ) -> ResilienceResult:

        events: List[ResilienceEvent] = []

        total_primary_attempts = 1 + self.max_primary_retries

        # ----------------------------------------------------
        # PRIMARY PROVIDER
        # ----------------------------------------------------

        for attempt in range(1, total_primary_attempts + 1):

            events.append(
                ResilienceEvent(
                    provider=primary_name,
                    attempt=attempt,
                    event="ATTEMPT",
                )
            )

            try:

                response = await primary_call()

                events.append(
                    ResilienceEvent(
                        provider=primary_name,
                        attempt=attempt,
                        event="SUCCESS",
                    )
                )

                return ResilienceResult(
                    success=True,
                    provider_used=primary_name,
                    response=response,
                    fallback_used=False,
                    primary_attempts=attempt,
                    fallback_attempts=0,
                    events=events,
                )

            except NonRetryableProviderError as exc:

                events.append(
                    ResilienceEvent(
                        provider=primary_name,
                        attempt=attempt,
                        event="NON_RETRYABLE_FAILURE",
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )

                return ResilienceResult(
                    success=False,
                    provider_used=primary_name,
                    fallback_used=False,
                    primary_attempts=attempt,
                    fallback_attempts=0,
                    final_error=f"{type(exc).__name__}: {exc}",
                    events=events,
                )

            except RetryableProviderError as exc:

                events.append(
                    ResilienceEvent(
                        provider=primary_name,
                        attempt=attempt,
                        event="RETRYABLE_FAILURE",
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )

                if attempt < total_primary_attempts:

                    events.append(
                        ResilienceEvent(
                            provider=primary_name,
                            attempt=attempt,
                            event="BACKOFF",
                            message=str(self.backoff_seconds),
                        )
                    )

                    if self.backoff_seconds > 0:
                        await asyncio.sleep(self.backoff_seconds)

                    continue

                # Retry budget exhausted.
                break

            except Exception as exc:

                # Unknown exceptions fail closed.
                events.append(
                    ResilienceEvent(
                        provider=primary_name,
                        attempt=attempt,
                        event="UNCLASSIFIED_FAILURE",
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )

                return ResilienceResult(
                    success=False,
                    provider_used=primary_name,
                    fallback_used=False,
                    primary_attempts=attempt,
                    fallback_attempts=0,
                    final_error=f"{type(exc).__name__}: {exc}",
                    events=events,
                )


        # ----------------------------------------------------
        # FALLBACK PROVIDER
        # ----------------------------------------------------

        if fallback_call is None or fallback_name is None:

            events.append(
                ResilienceEvent(
                    provider=primary_name,
                    attempt=total_primary_attempts,
                    event="RETRY_BUDGET_EXHAUSTED_NO_FALLBACK",
                )
            )

            return ResilienceResult(
                success=False,
                provider_used=primary_name,
                fallback_used=False,
                primary_attempts=total_primary_attempts,
                fallback_attempts=0,
                final_error="Primary provider retry budget exhausted.",
                events=events,
            )


        events.append(
            ResilienceEvent(
                provider=fallback_name,
                attempt=1,
                event="FALLBACK_START",
            )
        )

        try:

            response = await fallback_call()

            events.append(
                ResilienceEvent(
                    provider=fallback_name,
                    attempt=1,
                    event="SUCCESS",
                )
            )

            return ResilienceResult(
                success=True,
                provider_used=fallback_name,
                response=response,
                fallback_used=True,
                primary_attempts=total_primary_attempts,
                fallback_attempts=1,
                events=events,
            )

        except Exception as exc:

            events.append(
                ResilienceEvent(
                    provider=fallback_name,
                    attempt=1,
                    event="FALLBACK_FAILURE",
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            )

            return ResilienceResult(
                success=False,
                provider_used=fallback_name,
                fallback_used=True,
                primary_attempts=total_primary_attempts,
                fallback_attempts=1,
                final_error=f"{type(exc).__name__}: {exc}",
                events=events,
            )


def result_to_dict(result: ResilienceResult) -> Dict[str, Any]:

    return {
        "success": result.success,
        "provider_used": result.provider_used,
        "response": result.response,
        "fallback_used": result.fallback_used,
        "primary_attempts": result.primary_attempts,
        "fallback_attempts": result.fallback_attempts,
        "final_error": result.final_error,
        "events": [
            {
                "provider": event.provider,
                "attempt": event.attempt,
                "event": event.event,
                "error_type": event.error_type,
                "message": event.message,
            }
            for event in result.events
        ],
    }
