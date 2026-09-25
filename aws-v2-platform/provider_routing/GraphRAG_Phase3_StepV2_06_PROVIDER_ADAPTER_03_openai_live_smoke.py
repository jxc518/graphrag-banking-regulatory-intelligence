from __future__ import annotations

import asyncio
import importlib.util
import os
import pathlib
import sys
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent

ADAPTER_FILE = (
    HERE
    / "GraphRAG_Phase3_StepV2_06_PROVIDER_ADAPTER_01_adapters.py"
)


def load_adapter_module(path: pathlib.Path):

    spec = importlib.util.spec_from_file_location(
        "graphrag_v2_provider_adapters_live",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to load V2 provider adapter module"
        )

    module = importlib.util.module_from_spec(spec)

    # Required for dataclass resolution during dynamic import.
    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


adapter_module = load_adapter_module(
    ADAPTER_FILE
)


async def live_openai_transport(payload: Any):
    """
    One real OpenAI request.

    Deliberately:
      - no retry
      - no fallback
      - no DeepSeek
      - no AWS
    """

    from openai import AsyncOpenAI

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing"
        )

    model = os.getenv(
        "GRAPHRAG_V2_OPENAI_SMOKE_MODEL",
        "gpt-4.1",
    )

    client = AsyncOpenAI(
        api_key=api_key,
    )

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "This is a provider connectivity smoke test. "
                    "Return exactly the text requested by the user."
                ),
            },
            {
                "role": "user",
                "content": payload["prompt"],
            },
        ],
        temperature=0,
        max_tokens=30,
    )

    return response


def parse_live_openai_response(raw_response: Any) -> str:

    choices = getattr(
        raw_response,
        "choices",
        None,
    )

    if not choices:
        raise ValueError(
            "OpenAI response contains no choices"
        )

    first_choice = choices[0]

    message = getattr(
        first_choice,
        "message",
        None,
    )

    if message is None:
        raise ValueError(
            "OpenAI response contains no message"
        )

    content = getattr(
        message,
        "content",
        None,
    )

    if not content:
        raise ValueError(
            "OpenAI response contains empty content"
        )

    return str(content).strip()


async def main():

    expected = (
        "GRAPHRAG_V2_OPENAI_LIVE_OK"
    )

    model = os.getenv(
        "GRAPHRAG_V2_OPENAI_SMOKE_MODEL",
        "gpt-4.1",
    )

    print()
    print("=" * 72)
    print("REAL OPENAI PROVIDER ADAPTER SMOKE")
    print("=" * 72)

    print("MODE                 : LOCAL")
    print("PROVIDER             : OPENAI")
    print(f"MODEL                : {model}")
    print("REAL PROVIDER CALL   : YES")
    print("RETRY                : NONE")
    print("FALLBACK             : NONE")
    print("DEEPSEEK             : NOT CALLED")
    print("AWS                  : NOT CALLED")

    adapter = adapter_module.OpenAIAdapter(
        transport=live_openai_transport,
        response_parser=parse_live_openai_response,
    )

    request = adapter_module.ProviderAdapterRequest(
        provider="openai",
        payload={
            "prompt": (
                "Return exactly this text and nothing else: "
                + expected
            )
        },
        metadata={
            "step": "STEP V2-06H-B",
            "test_type": "real_provider_local_smoke",
        },
    )

    try:

        result = await adapter.execute(
            request
        )

    except adapter_module.AdapterTransportError as exc:

        print()
        print("===== PROVIDER FAILURE =====")
        print("LIVE CALL RESULT     : FAIL")
        print(
            "ERROR CLASS          :",
            exc.__class__.__name__,
        )

        print(
            "ERROR CATEGORY       :",
            getattr(exc, "category", None),
        )

        print(
            "RETRYABLE            :",
            getattr(exc, "retryable", None),
        )

        print(
            "STATUS CODE          :",
            getattr(exc, "status_code", None),
        )

        print("SECRET VALUE         : SUPPRESSED")

        raise SystemExit(2)

    except Exception as exc:

        print()
        print("===== UNCLASSIFIED FAILURE =====")
        print("LIVE CALL RESULT     : FAIL")
        print(
            "ERROR CLASS          :",
            exc.__class__.__name__,
        )
        print(
            "ERROR MESSAGE        :",
            str(exc)[:500],
        )
        print("SECRET VALUE         : SUPPRESSED")

        raise SystemExit(3)

    actual = str(
        result.content
    ).strip()

    exact_match = (
        actual == expected
    )

    print()
    print("===== NORMALIZED RESULT =====")

    print(
        "NORMALIZED PROVIDER  :",
        result.provider,
    )

    print(
        "NORMALIZED CONTENT   :",
        actual,
    )

    print(
        "EXPECTED CONTENT     :",
        expected,
    )

    print(
        "EXACT MATCH          :",
        exact_match,
    )

    if (
        result.provider != "openai"
        or not exact_match
    ):

        print()
        print(
            "STEP V2-06H-B RESULT : REVIEW REQUIRED"
        )

        raise SystemExit(4)

    print()
    print(
        "STEP V2-06H-B RESULT : PASS"
    )

    print(
        "REAL OPENAI CALL      : VALIDATED"
    )

    print(
        "OPENAI ADAPTER        : VALIDATED"
    )

    print(
        "NORMALIZATION         : VALIDATED"
    )


if __name__ == "__main__":
    asyncio.run(main())
