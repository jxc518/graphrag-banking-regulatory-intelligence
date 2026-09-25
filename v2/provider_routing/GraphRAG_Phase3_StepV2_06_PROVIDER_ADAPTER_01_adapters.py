from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional
import asyncio


# ============================================================
# NORMALIZED ADAPTER CONTRACT
# ============================================================

@dataclass
class ProviderAdapterRequest:
    provider: str
    payload: Any
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProviderAdapterResponse:
    provider: str
    content: Any
    raw_response: Any
    metadata: Dict[str, Any]


# ============================================================
# ADAPTER-LEVEL TRANSPORT ERRORS
#
# IMPORTANT:
# These errors describe WHAT happened at the provider boundary.
# They do NOT decide retry/fallback policy.
# ============================================================

class AdapterTransportError(Exception):
    retryable: bool = False
    category: str = "transport_error"

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        status_code: Optional[int] = None,
        original_exception: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.original_exception = original_exception


class AdapterTimeoutError(AdapterTransportError):
    retryable = True
    category = "timeout"


class AdapterConnectionError(AdapterTransportError):
    retryable = True
    category = "connection"


class AdapterRateLimitError(AdapterTransportError):
    retryable = True
    category = "rate_limit"


class AdapterServerError(AdapterTransportError):
    retryable = True
    category = "server_error"


class AdapterAuthenticationError(AdapterTransportError):
    retryable = False
    category = "authentication"


class AdapterBadRequestError(AdapterTransportError):
    retryable = False
    category = "bad_request"


class AdapterConfigurationError(AdapterTransportError):
    retryable = False
    category = "configuration"


class AdapterUnknownError(AdapterTransportError):
    retryable = False
    category = "unknown"


# ============================================================
# EXCEPTION CLASSIFICATION
#
# This function normalizes provider-specific exception SHAPE.
# It does not retry.
# It does not fallback.
# ============================================================

def _status_code_from_exception(exc: BaseException) -> Optional[int]:
    for attr in ("status_code", "status", "http_status"):
        value = getattr(exc, attr, None)

        if isinstance(value, int):
            return value

    response = getattr(exc, "response", None)

    if response is not None:
        value = getattr(response, "status_code", None)

        if isinstance(value, int):
            return value

    return None


def classify_transport_exception(
    provider: str,
    exc: BaseException,
) -> AdapterTransportError:

    status_code = _status_code_from_exception(exc)

    name = exc.__class__.__name__.lower()
    text = str(exc).lower()

    # Timeout
    if (
        isinstance(exc, (TimeoutError, asyncio.TimeoutError))
        or "timeout" in name
        or "timed out" in text
    ):
        return AdapterTimeoutError(
            str(exc),
            provider=provider,
            status_code=status_code,
            original_exception=exc,
        )

    # HTTP status classification
    if status_code == 429:
        return AdapterRateLimitError(
            str(exc),
            provider=provider,
            status_code=status_code,
            original_exception=exc,
        )

    if status_code in (401, 403):
        return AdapterAuthenticationError(
            str(exc),
            provider=provider,
            status_code=status_code,
            original_exception=exc,
        )

    if status_code is not None and 500 <= status_code <= 599:
        return AdapterServerError(
            str(exc),
            provider=provider,
            status_code=status_code,
            original_exception=exc,
        )

    if status_code is not None and 400 <= status_code <= 499:
        return AdapterBadRequestError(
            str(exc),
            provider=provider,
            status_code=status_code,
            original_exception=exc,
        )

    # Connection/network indicators
    if (
        isinstance(exc, ConnectionError)
        or "connection" in name
        or "connection" in text
        or "clientpayloaderror" in name
    ):
        return AdapterConnectionError(
            str(exc),
            provider=provider,
            status_code=status_code,
            original_exception=exc,
        )

    # Configuration indicators
    if (
        "api key" in text
        or "apikey" in text
        or "configuration" in text
        or "config" in name
    ):
        return AdapterConfigurationError(
            str(exc),
            provider=provider,
            status_code=status_code,
            original_exception=exc,
        )

    # Unknown = fail-closed classification
    return AdapterUnknownError(
        str(exc),
        provider=provider,
        status_code=status_code,
        original_exception=exc,
    )


# ============================================================
# BASE ADAPTER
# ============================================================

class BaseProviderAdapter:

    provider_name: str = "unknown"

    def __init__(
        self,
        transport: Callable[[Any], Awaitable[Any]],
        response_parser: Callable[[Any], Any],
    ) -> None:
        self.transport = transport
        self.response_parser = response_parser

    async def execute(
        self,
        request: ProviderAdapterRequest,
    ) -> ProviderAdapterResponse:

        try:
            raw_response = await self.transport(request.payload)

        except AdapterTransportError:
            raise

        except BaseException as exc:
            raise classify_transport_exception(
                self.provider_name,
                exc,
            ) from exc

        try:
            content = self.response_parser(raw_response)

        except BaseException as exc:
            # Parsing/schema failure is not blindly retryable.
            raise AdapterUnknownError(
                f"Response parsing failed: {exc}",
                provider=self.provider_name,
                original_exception=exc,
            ) from exc

        return ProviderAdapterResponse(
            provider=self.provider_name,
            content=content,
            raw_response=raw_response,
            metadata={
                "adapter": self.__class__.__name__,
                "retry_implemented_here": False,
                "fallback_implemented_here": False,
            },
        )


# ============================================================
# OPENAI ADAPTER
#
# Production transport target identified in STEP V2-06F:
# existing engine.model.completion_async(...)
# ============================================================

class OpenAIAdapter(BaseProviderAdapter):

    provider_name = "openai"


# ============================================================
# DEEPSEEK ADAPTER
#
# Production transport target identified in STEP V2-06F:
# existing DeepSeek /chat/completions path
# ============================================================

class DeepSeekAdapter(BaseProviderAdapter):

    provider_name = "deepseek"


# ============================================================
# SIMPLE NORMALIZED PARSERS
#
# These support deterministic contract testing.
# Real V1.3 response-specific parser wiring occurs only after
# the adapter contract passes this gate.
# ============================================================

def parse_openai_like_response(raw_response: Any) -> Any:

    # Dictionary-shaped normalized test response
    if isinstance(raw_response, dict):

        if "content" in raw_response:
            return raw_response["content"]

        choices = raw_response.get("choices")

        if choices:
            first = choices[0]

            if isinstance(first, dict):
                message = first.get("message", {})

                if isinstance(message, dict) and "content" in message:
                    return message["content"]

    # Object-shaped response
    choices = getattr(raw_response, "choices", None)

    if choices:
        first = choices[0]
        message = getattr(first, "message", None)

        if message is not None:
            content = getattr(message, "content", None)

            if content is not None:
                return content

    # Some existing GraphRAG transports may already return
    # normalized text/content.
    if isinstance(raw_response, str):
        return raw_response

    content = getattr(raw_response, "content", None)

    if content is not None:
        return content

    raise ValueError("Unable to extract OpenAI content")


def parse_deepseek_like_response(raw_response: Any) -> Any:

    if isinstance(raw_response, dict):

        if "content" in raw_response:
            return raw_response["content"]

        choices = raw_response.get("choices")

        if choices:
            first = choices[0]

            if isinstance(first, dict):
                message = first.get("message", {})

                if isinstance(message, dict) and "content" in message:
                    return message["content"]

    if isinstance(raw_response, str):
        return raw_response

    raise ValueError("Unable to extract DeepSeek content")
