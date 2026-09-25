from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from uuid import uuid4


def load_module(name: str, path: Path):

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module

    spec.loader.exec_module(module)

    return module


wrapper_path = Path(sys.argv[1])
adapter_path = Path(sys.argv[2])
emitter_path = Path(sys.argv[3])
schema_path  = Path(sys.argv[4])
output_path  = Path(sys.argv[5])


wrapper = load_module(
    "v2_06e_wrapper_live_obs",
    wrapper_path,
)

adapter = load_module(
    "v2_06g_adapter_live_obs",
    adapter_path,
)

observability = load_module(
    "v2_06i_event_emitter_live",
    emitter_path,
)


ProviderResilienceWrapper = wrapper.ProviderResilienceWrapper
ProviderTimeoutError = wrapper.ProviderTimeoutError

DeepSeekAdapter = adapter.DeepSeekAdapter
ProviderAdapterRequest = adapter.ProviderAdapterRequest

normalize_resilience_events = (
    observability.normalize_resilience_events
)

validate_against_contract = (
    observability.validate_against_contract
)

JsonlResilienceEventEmitter = (
    observability.JsonlResilienceEventEmitter
)


schema = json.loads(
    schema_path.read_text(
        encoding="utf-8-sig"
    )
)


deepseek_key = os.environ.get(
    "DEEPSEEK_API_KEY",
    "",
).strip()

if not deepseek_key:
    raise SystemExit(
        "DEEPSEEK_API_KEY missing"
    )


# ============================================================
# CONTROLLED PRIMARY FAILURE
# ============================================================

primary_call_count = 0
deepseek_call_count = 0


async def controlled_openai_failure():

    global primary_call_count

    primary_call_count += 1

    print(
        f"PRIMARY ATTEMPT {primary_call_count} "
        ": INJECTED ProviderTimeoutError"
    )

    raise ProviderTimeoutError(
        "Controlled OpenAI timeout for STEP V2-06I-D"
    )


# ============================================================
# REAL DEEPSEEK TRANSPORT
# ============================================================

async def deepseek_transport(payload):

    global deepseek_call_count

    deepseek_call_count += 1

    if deepseek_call_count > 1:
        raise RuntimeError(
            "Safety gate: DeepSeek called more than once"
        )

    print(
        "FALLBACK CALL          : REAL DEEPSEEK VIA 06G ADAPTER"
    )

    payload = dict(payload)

    body = json.dumps(
        payload
    ).encode("utf-8")

    http_request = urllib.request.Request(

        "https://api.deepseek.com/chat/completions",

        data=body,

        headers={
            "Authorization": f"Bearer {deepseek_key}",
            "Content-Type": "application/json",
        },

        method="POST",
    )

    def do_request():

        with urllib.request.urlopen(
            http_request,
            timeout=60,
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    return await asyncio.to_thread(
        do_request
    )


def deepseek_response_parser(raw):

    choices = raw.get(
        "choices",
        []
    )

    if not choices:
        raise ValueError(
            "DeepSeek response contains no choices"
        )

    message = choices[0].get(
        "message",
        {}
    )

    content = message.get(
        "content"
    )

    if not content:
        raise ValueError(
            "DeepSeek response contains no content"
        )

    return content.strip()


deepseek_adapter = DeepSeekAdapter(

    transport=deepseek_transport,

    response_parser=deepseek_response_parser,
)


async def real_deepseek_fallback():

    request = ProviderAdapterRequest(

        provider="deepseek",

        payload={
            "model": "deepseek-v4-flash",

            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Return exactly: "
                        "GRAPHRAG_V2_TELEMETRY_RECOVERY_OK"
                    ),
                }
            ],

            "temperature": 0,

            "max_tokens": 100,
        },

        metadata={
            "step": "STEP V2-06I-D"
        },
    )

    response = await deepseek_adapter.execute(
        request
    )

    return response.content


# ============================================================
# RUN REAL RESILIENCE FLOW
# ============================================================

async def main():

    query_id = (
        "query-v2-06i-d-"
        + uuid4().hex[:12]
    )

    trace_id = (
        "trace-v2-06i-d-"
        + uuid4().hex[:12]
    )

    resilience = ProviderResilienceWrapper(

        max_primary_retries=1,

        backoff_seconds=0.25,
    )

    print()
    print("===== C. LIVE RESILIENCE EXECUTION =====")

    start = time.perf_counter()

    result = await resilience.execute(

        primary_name="openai",

        primary_call=controlled_openai_failure,

        fallback_name="deepseek",

        fallback_call=real_deepseek_fallback,
    )

    elapsed_ms = (
        time.perf_counter() - start
    ) * 1000.0


    print()
    print("===== D. REAL 06E RESULT =====")

    print("SUCCESS               :", result.success)
    print("PROVIDER USED         :", result.provider_used)
    print("FALLBACK USED         :", result.fallback_used)
    print("PRIMARY ATTEMPTS      :", result.primary_attempts)
    print("FALLBACK ATTEMPTS     :", result.fallback_attempts)
    print("PRIMARY CALL COUNT    :", primary_call_count)
    print("DEEPSEEK CALL COUNT   :", deepseek_call_count)
    print("FINAL ERROR           :", result.final_error)
    print("FINAL CONTENT         :", result.response)
    print("TOTAL LATENCY MS      :", round(elapsed_ms, 2))


    print()
    print("===== E. REAL 06E EVENT TRACE =====")

    for event in result.events:

        print(
            f"PROVIDER={event.provider} | "
            f"ATTEMPT={event.attempt} | "
            f"EVENT={event.event} | "
            f"ERROR={event.error_type or '-'}"
        )


    # ========================================================
    # NORMALIZE THE REAL RESULT
    # ========================================================

    normalized = normalize_resilience_events(

        result,

        query_id=query_id,

        trace_id=trace_id,

        service="multi-agent-graphrag",

        environment="local-live-test",

        primary_provider="openai",

        fallback_provider="deepseek",

        latency_ms=round(
            elapsed_ms,
            2,
        ),

        metadata={
            "step": "STEP V2-06I-D",
            "controlled_primary_failure": True,
            "real_fallback_provider": True,
        },
    )


    contract_errors = validate_against_contract(

        normalized,

        schema,
    )


    print()
    print("===== F. STANDARD TELEMETRY RESULT =====")

    print(
        "RAW EVENT COUNT        :",
        len(result.events),
    )

    print(
        "TELEMETRY EVENT COUNT  :",
        len(normalized),
    )

    print(
        "CONTRACT ERROR COUNT   :",
        len(contract_errors),
    )

    print(
        "CONTRACT PASS          :",
        len(contract_errors) == 0,
    )


    for index, event in enumerate(
        normalized,
        start=1,
    ):

        print(
            f"{index:02d} | "
            f"{event['provider']} | "
            f"{event['event_type']} | "
            f"retryable={event['retryable']} | "
            f"fallback={event['fallback_used']} | "
            f"recovered={event['recovered']}"
        )


    # ========================================================
    # EMIT REAL TELEMETRY TO JSONL
    # ========================================================

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if output_path.exists():
        output_path.unlink()

    emitter = JsonlResilienceEventEmitter(
        output_path
    )

    emitted_count = emitter.emit(
        normalized
    )

    lines = output_path.read_text(
        encoding="utf-8"
    ).splitlines()

    parsed = [
        json.loads(line)
        for line in lines
    ]


    print()
    print("===== G. TELEMETRY EMISSION =====")

    print(
        "EMITTED COUNT          :",
        emitted_count,
    )

    print(
        "JSONL LINE COUNT       :",
        len(lines),
    )

    print(
        "JSON PARSE PASS        :",
        len(parsed) == len(normalized),
    )

    print(
        "QUERY ID               :",
        query_id,
    )

    print(
        "TRACE ID               :",
        trace_id,
    )

    print(
        "OUTPUT FILE            :",
        output_path,
    )


    # ========================================================
    # END-TO-END VALIDATION
    # ========================================================

    event_types = [
        event["event_type"]
        for event in normalized
    ]

    expected = [
        "ATTEMPT",
        "RETRYABLE_FAILURE",
        "BACKOFF",
        "ATTEMPT",
        "RETRYABLE_FAILURE",
        "FALLBACK_START",
        "SUCCESS",
    ]

    retry_events = [
        e for e in normalized
        if e["event_type"]
        == "RETRYABLE_FAILURE"
    ]

    fallback_events = [
        e for e in normalized
        if e["event_type"]
        == "FALLBACK_START"
    ]

    recovery_events = [
        e for e in normalized
        if e["recovered"]
    ]

    content_pass = (
        result.response
        == "GRAPHRAG_V2_TELEMETRY_RECOVERY_OK"
    )

    passed = all([

        result.success,

        result.provider_used
            == "deepseek",

        result.fallback_used,

        result.primary_attempts
            == 2,

        result.fallback_attempts
            == 1,

        primary_call_count
            == 2,

        deepseek_call_count
            == 1,

        content_pass,

        event_types
            == expected,

        len(contract_errors)
            == 0,

        len(normalized)
            == 7,

        len(retry_events)
            == 2,

        len(fallback_events)
            == 1,

        len(recovery_events)
            == 1,

        (
            len(recovery_events) == 1
            and recovery_events[0][
                "provider"
            ] == "deepseek"
        ),

        emitted_count
            == 7,

        len(parsed)
            == 7,
    ])


    print()
    print("===== H. END-TO-END VALIDATION =====")

    print("RESILIENCE PASS       :", result.success)
    print("RETRY PASS            :", result.primary_attempts == 2)
    print("FALLBACK PASS         :", result.fallback_used)
    print("REAL RECOVERY PASS    :", content_pass)
    print("EVENT ORDER PASS      :", event_types == expected)
    print("TELEMETRY CONTRACT    :", len(contract_errors) == 0)
    print("RETRY TELEMETRY       :", len(retry_events) == 2)
    print("FALLBACK TELEMETRY    :", len(fallback_events) == 1)
    print("RECOVERY TELEMETRY    :", len(recovery_events) == 1)
    print("JSONL EMISSION        :", emitted_count == 7)


    print()
    print("============================================================")

    if passed:

        print("STEP V2-06I-D: PASS")
        print("LIVE RESILIENCE RESULT     : VALIDATED")
        print("BOUNDED RETRY              : VALIDATED")
        print("AUTOMATIC FALLBACK         : VALIDATED")
        print("REAL DEEPSEEK RECOVERY     : VALIDATED")
        print("STANDARD TELEMETRY         : VALIDATED")
        print("RETRY TELEMETRY            : VALIDATED")
        print("FALLBACK TELEMETRY         : VALIDATED")
        print("RECOVERY TELEMETRY         : VALIDATED")
        print("JSONL EMISSION             : VALIDATED")

    else:

        print("STEP V2-06I-D: REVIEW REQUIRED")

        for error in contract_errors:
            print("CONTRACT ERROR:", error)

    print("============================================================")

    return 0 if passed else 2


raise SystemExit(
    asyncio.run(main())
)

