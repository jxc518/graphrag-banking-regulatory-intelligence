from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent

ADAPTER_FILE = (
    HERE
    / "GraphRAG_Phase3_StepV2_06_PROVIDER_ADAPTER_01_adapters.py"
)


def load_adapter_module(path: pathlib.Path):

    spec = importlib.util.spec_from_file_location(
        "graphrag_v2_deepseek_adapter_live",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load adapter module")

    module = importlib.util.module_from_spec(spec)

    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


adapter_module = load_adapter_module(ADAPTER_FILE)


def _sync_deepseek_call(payload: Any):

    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing")

    model = os.getenv(
        "GRAPHRAG_V2_DEEPSEEK_SMOKE_MODEL",
        "deepseek-v4-flash",
    )

    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "This is a provider connectivity smoke test. "
                    "Return exactly the requested text."
                ),
            },
            {
                "role": "user",
                "content": payload["prompt"],
            },
        ],
        "temperature": 0,
        "stream": False,
    }

    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:

            raw = response.read().decode("utf-8")

            return json.loads(raw)

    except urllib.error.HTTPError as exc:

        # Attach status_code so the existing 06G classifier
        # can classify the real provider exception.
        exc.status_code = exc.code
        raise


async def live_deepseek_transport(payload: Any):

    return await asyncio.to_thread(
        _sync_deepseek_call,
        payload,
    )


def parse_live_deepseek_response(raw_response: Any) -> str:

    choices = raw_response.get(
        "choices",
        [],
    )

    if not choices:
        raise ValueError(
            "DeepSeek response contains no choices"
        )

    message = choices[0].get(
        "message",
        {},
    )

    content = message.get(
        "content",
    )

    if not content:
        raise ValueError(
            "DeepSeek response contains empty content"
        )

    return str(content).strip()


async def main():

    expected = "GRAPHRAG_V2_DEEPSEEK_LIVE_OK"

    model = os.getenv(
        "GRAPHRAG_V2_DEEPSEEK_SMOKE_MODEL",
        "deepseek-v4-flash",
    )

    print()
    print("=" * 72)
    print("REAL DEEPSEEK PROVIDER ADAPTER SMOKE")
    print("=" * 72)

    print("MODE                 : LOCAL")
    print("PROVIDER             : DEEPSEEK")
    print(f"MODEL                : {model}")
    print("REAL PROVIDER CALL   : YES")
    print("RETRY                : NONE")
    print("FALLBACK             : NONE")
    print("OPENAI               : NOT CALLED")
    print("AWS                  : NOT CALLED")

    adapter = adapter_module.DeepSeekAdapter(
        transport=live_deepseek_transport,
        response_parser=parse_live_deepseek_response,
    )

    request = adapter_module.ProviderAdapterRequest(
        provider="deepseek",
        payload={
            "prompt": (
                "Return exactly this text and nothing else: "
                + expected
            )
        },
        metadata={
            "step": "STEP V2-06H-C",
            "test_type": "real_provider_local_smoke",
        },
    )

    try:

        result = await adapter.execute(request)

    except adapter_module.AdapterTransportError as exc:

        print()
        print("===== PROVIDER FAILURE =====")
        print("LIVE CALL RESULT     : FAIL")
        print("ERROR CLASS          :", exc.__class__.__name__)
        print("ERROR CATEGORY       :", getattr(exc, "category", None))
        print("RETRYABLE            :", getattr(exc, "retryable", None))
        print("STATUS CODE          :", getattr(exc, "status_code", None))
        print("SECRET VALUE         : SUPPRESSED")

        raise SystemExit(2)

    except Exception as exc:

        print()
        print("===== UNCLASSIFIED FAILURE =====")
        print("LIVE CALL RESULT     : FAIL")
        print("ERROR CLASS          :", exc.__class__.__name__)
        print("ERROR MESSAGE        :", str(exc)[:500])
        print("SECRET VALUE         : SUPPRESSED")

        raise SystemExit(3)

    actual = str(result.content).strip()

    exact_match = actual == expected

    print()
    print("===== NORMALIZED RESULT =====")
    print("NORMALIZED PROVIDER  :", result.provider)
    print("NORMALIZED CONTENT   :", actual)
    print("EXPECTED CONTENT     :", expected)
    print("EXACT MATCH          :", exact_match)

    if result.provider != "deepseek" or not exact_match:

        print()
        print("STEP V2-06H-C RESULT : REVIEW REQUIRED")

        raise SystemExit(4)

    print()
    print("STEP V2-06H-C RESULT : PASS")
    print("REAL DEEPSEEK CALL    : VALIDATED")
    print("DEEPSEEK ADAPTER      : VALIDATED")
    print("NORMALIZATION         : VALIDATED")


if __name__ == "__main__":
    asyncio.run(main())
