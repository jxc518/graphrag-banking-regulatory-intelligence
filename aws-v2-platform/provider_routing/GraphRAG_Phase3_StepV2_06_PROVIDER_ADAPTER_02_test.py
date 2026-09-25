from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import sys


HERE = pathlib.Path(__file__).resolve().parent

ADAPTER_FILE = (
    HERE
    / "GraphRAG_Phase3_StepV2_06_PROVIDER_ADAPTER_01_adapters.py"
)


def load_module(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(
        "v2_provider_adapters",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to create adapter module spec")

    module = importlib.util.module_from_spec(spec)

    # Required for dataclass/type resolution during dynamic import.
    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


m = load_module(ADAPTER_FILE)


class FakeHTTPError(Exception):

    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


async def run_tests():

    results = []

    def record(name, passed, detail=""):
        results.append((name, passed, detail))

    # --------------------------------------------------------
    # 01. OpenAI normalized success
    # --------------------------------------------------------

    async def openai_success(payload):
        return {
            "choices": [
                {
                    "message": {
                        "content": "OPENAI_OK"
                    }
                }
            ]
        }

    openai = m.OpenAIAdapter(
        transport=openai_success,
        response_parser=m.parse_openai_like_response,
    )

    response = await openai.execute(
        m.ProviderAdapterRequest(
            provider="openai",
            payload={"messages": ["test"]},
        )
    )

    record(
        "01_OPENAI_NORMALIZED_SUCCESS",
        response.content == "OPENAI_OK"
        and response.provider == "openai"
        and response.metadata["retry_implemented_here"] is False
        and response.metadata["fallback_implemented_here"] is False,
    )

    # --------------------------------------------------------
    # 02. DeepSeek normalized success
    # --------------------------------------------------------

    async def deepseek_success(payload):
        return {
            "choices": [
                {
                    "message": {
                        "content": "DEEPSEEK_OK"
                    }
                }
            ]
        }

    deepseek = m.DeepSeekAdapter(
        transport=deepseek_success,
        response_parser=m.parse_deepseek_like_response,
    )

    response = await deepseek.execute(
        m.ProviderAdapterRequest(
            provider="deepseek",
            payload={"messages": ["test"]},
        )
    )

    record(
        "02_DEEPSEEK_NORMALIZED_SUCCESS",
        response.content == "DEEPSEEK_OK"
        and response.provider == "deepseek",
    )

    # --------------------------------------------------------
    # 03. Timeout classification
    # --------------------------------------------------------

    async def timeout_transport(payload):
        raise TimeoutError("provider timed out")

    adapter = m.OpenAIAdapter(
        transport=timeout_transport,
        response_parser=m.parse_openai_like_response,
    )

    try:
        await adapter.execute(
            m.ProviderAdapterRequest(
                provider="openai",
                payload={},
            )
        )

        record("03_TIMEOUT_CLASSIFICATION", False, "No exception")

    except m.AdapterTimeoutError as exc:
        record(
            "03_TIMEOUT_CLASSIFICATION",
            exc.retryable is True
            and exc.category == "timeout",
        )

    # --------------------------------------------------------
    # 04. 429 classification
    # --------------------------------------------------------

    async def rate_limit_transport(payload):
        raise FakeHTTPError("rate limited", 429)

    adapter = m.OpenAIAdapter(
        transport=rate_limit_transport,
        response_parser=m.parse_openai_like_response,
    )

    try:
        await adapter.execute(
            m.ProviderAdapterRequest(
                provider="openai",
                payload={},
            )
        )

        record("04_RATE_LIMIT_CLASSIFICATION", False, "No exception")

    except m.AdapterRateLimitError as exc:
        record(
            "04_RATE_LIMIT_CLASSIFICATION",
            exc.retryable is True
            and exc.status_code == 429,
        )

    # --------------------------------------------------------
    # 05. Authentication fail-closed classification
    # --------------------------------------------------------

    async def auth_transport(payload):
        raise FakeHTTPError("unauthorized", 401)

    adapter = m.OpenAIAdapter(
        transport=auth_transport,
        response_parser=m.parse_openai_like_response,
    )

    try:
        await adapter.execute(
            m.ProviderAdapterRequest(
                provider="openai",
                payload={},
            )
        )

        record(
            "05_AUTH_NON_RETRYABLE",
            False,
            "No exception",
        )

    except m.AdapterAuthenticationError as exc:
        record(
            "05_AUTH_NON_RETRYABLE",
            exc.retryable is False
            and exc.status_code == 401,
        )

    # --------------------------------------------------------
    # 06. HTTP 5xx retryable classification
    # --------------------------------------------------------

    async def server_transport(payload):
        raise FakeHTTPError("provider unavailable", 503)

    adapter = m.DeepSeekAdapter(
        transport=server_transport,
        response_parser=m.parse_deepseek_like_response,
    )

    try:
        await adapter.execute(
            m.ProviderAdapterRequest(
                provider="deepseek",
                payload={},
            )
        )

        record(
            "06_SERVER_ERROR_RETRYABLE",
            False,
            "No exception",
        )

    except m.AdapterServerError as exc:
        record(
            "06_SERVER_ERROR_RETRYABLE",
            exc.retryable is True
            and exc.status_code == 503,
        )

    # --------------------------------------------------------
    # 07. Unknown exception fails closed
    # --------------------------------------------------------

    async def unknown_transport(payload):
        raise RuntimeError("unexpected provider behavior")

    adapter = m.OpenAIAdapter(
        transport=unknown_transport,
        response_parser=m.parse_openai_like_response,
    )

    try:
        await adapter.execute(
            m.ProviderAdapterRequest(
                provider="openai",
                payload={},
            )
        )

        record(
            "07_UNKNOWN_FAIL_CLOSED",
            False,
            "No exception",
        )

    except m.AdapterUnknownError as exc:
        record(
            "07_UNKNOWN_FAIL_CLOSED",
            exc.retryable is False,
        )

    # --------------------------------------------------------
    # 08. Parsing failure fails closed
    # --------------------------------------------------------

    async def malformed_response(payload):
        return {
            "unexpected": "schema"
        }

    adapter = m.DeepSeekAdapter(
        transport=malformed_response,
        response_parser=m.parse_deepseek_like_response,
    )

    try:
        await adapter.execute(
            m.ProviderAdapterRequest(
                provider="deepseek",
                payload={},
            )
        )

        record(
            "08_PARSE_FAILURE_FAIL_CLOSED",
            False,
            "No exception",
        )

    except m.AdapterUnknownError as exc:
        record(
            "08_PARSE_FAILURE_FAIL_CLOSED",
            exc.retryable is False,
        )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    print()
    print("=" * 78)
    print("STEP V2-06G - DETERMINISTIC PROVIDER ADAPTER CONTRACT TEST")
    print("=" * 78)

    passed = 0

    for name, ok, detail in results:

        status = "PASS" if ok else "FAIL"

        print(f"{name:<48} {status}")

        if detail:
            print(f"    DETAIL: {detail}")

        if ok:
            passed += 1

    failed = len(results) - passed

    print("-" * 78)
    print(f"PASSED : {passed}/{len(results)}")
    print(f"FAILED : {failed}/{len(results)}")

    if failed:
        print("STEP V2-06G RESULT : FAIL")
        raise SystemExit(1)

    print("STEP V2-06G RESULT : PASS")
    print("OPENAI NORMALIZATION      : VALIDATED")
    print("DEEPSEEK NORMALIZATION    : VALIDATED")
    print("RETRYABLE CLASSIFICATION  : VALIDATED")
    print("NONRETRYABLE FAIL-CLOSED  : VALIDATED")
    print("ADAPTER RETRY             : NONE")
    print("ADAPTER FALLBACK          : NONE")


if __name__ == "__main__":
    asyncio.run(run_tests())
