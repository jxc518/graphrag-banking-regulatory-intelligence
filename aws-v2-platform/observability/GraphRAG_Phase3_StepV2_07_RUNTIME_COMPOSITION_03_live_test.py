from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import sys
import time
from copy import deepcopy
from pathlib import Path
from uuid import uuid4


BASE = Path(__file__).resolve().parent
V2 = BASE.parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED: {path}"
        )

    module = importlib.util.module_from_spec(spec)

    # Required for dataclass/module metadata.
    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


# ============================================================
# REAL IMPLEMENTATION PATHS
# ============================================================

wrapper_path = (
    V2
    / "resilience"
    / "GraphRAG_Phase3_StepV2_06_PROVIDER_RESILIENCE_01_wrapper.py"
)

emitter_path = (
    BASE
    / "GraphRAG_Phase3_StepV2_06_RESILIENCE_OBSERVABILITY_02_event_emitter.py"
)

router_path = (
    BASE
    / "GraphRAG_Phase3_StepV2_06_OBSERVABILITY_SINKS_01_router.py"
)

cloudwatch_path = (
    BASE
    / "GraphRAG_Phase3_StepV2_06_OBSERVABILITY_SINKS_03_cloudwatch_json.py"
)

langsmith_path = (
    BASE
    / "GraphRAG_Phase3_StepV2_07_LANGSMITH_SINK_01_adapter.py"
)

composition_path = (
    BASE
    / "GraphRAG_Phase3_StepV2_07_RUNTIME_COMPOSITION_01_wiring.py"
)


# ============================================================
# LOAD REAL IMPLEMENTATION MODULES
# ============================================================

wrapper = load_module(
    "v2_06e_wrapper_07f",
    wrapper_path,
)

observability = load_module(
    "v2_06i_emitter_07f",
    emitter_path,
)

router_mod = load_module(
    "v2_router_07f_fix1",
    router_path,
)

cloud_mod = load_module(
    "v2_cloudwatch_07f_fix1",
    cloudwatch_path,
)

lang_mod = load_module(
    "v2_langsmith_07f_fix1",
    langsmith_path,
)

composition_mod = load_module(
    "v2_composition_07f_fix1",
    composition_path,
)


ProviderResilienceWrapper = (
    wrapper.ProviderResilienceWrapper
)

ProviderTimeoutError = (
    wrapper.ProviderTimeoutError
)

normalize_resilience_events = (
    observability.normalize_resilience_events
)

TelemetrySinkRouter = (
    router_mod.TelemetrySinkRouter
)

CloudWatchStructuredJsonSink = (
    cloud_mod.CloudWatchStructuredJsonSink
)

LangSmithSink = (
    lang_mod.LangSmithSink
)

ResilienceObservabilityComposition = (
    composition_mod.ResilienceObservabilityComposition
)


# ============================================================
# CONTROLLED PROVIDERS
# REAL RESILIENCE LOGIC / ZERO PROVIDER NETWORK CALLS
# ============================================================

primary_call_count = 0
fallback_call_count = 0


async def controlled_primary_failure():

    global primary_call_count
    primary_call_count += 1

    raise ProviderTimeoutError(
        "CONTROLLED_PRIMARY_TIMEOUT"
    )


async def controlled_fallback_success():

    global fallback_call_count
    fallback_call_count += 1

    return {
        "content": "CONTROLLED_FALLBACK_SUCCESS"
    }


# ============================================================
# FAKE LANGSMITH CLIENT
# REAL LANGSMITH SINK / ZERO LANGSMITH NETWORK CALLS
# ============================================================

class FakeLangSmithClient:

    def __init__(self):
        self.calls = []

    def create_run(self, **kwargs):
        self.calls.append(
            deepcopy(kwargs)
        )


async def main():

    print()
    print("=" * 64)
    print("STEP V2-07F-04B-FIX1")
    print("REAL RESILIENCE -> CANONICAL -> COMPOSITION -> MULTI-SINK")
    print("=" * 64)

    query_id = (
        "query-v2-07f-"
        + uuid4().hex[:12]
    )

    trace_id = (
        "trace-v2-07f-"
        + uuid4().hex[:12]
    )


    # ========================================================
    # A. REAL RESILIENCE IMPLEMENTATION
    # ========================================================

    resilience = ProviderResilienceWrapper(
        max_primary_retries=1,
        backoff_seconds=0.01,
    )

    start = time.perf_counter()

    result = await resilience.execute(
        primary_name="openai",
        primary_call=controlled_primary_failure,
        fallback_name="deepseek",
        fallback_call=controlled_fallback_success,
    )

    elapsed_ms = (
        time.perf_counter() - start
    ) * 1000.0

    print()
    print("===== A. REAL RESILIENCE RESULT =====")
    print("SUCCESS             :", result.success)
    print("PROVIDER USED       :", result.provider_used)
    print("FALLBACK USED       :", result.fallback_used)
    print("PRIMARY ATTEMPTS    :", result.primary_attempts)
    print("FALLBACK ATTEMPTS   :", result.fallback_attempts)
    print("PRIMARY CALL COUNT  :", primary_call_count)
    print("FALLBACK CALL COUNT :", fallback_call_count)


    # ========================================================
    # B. REAL CANONICAL NORMALIZATION
    # ========================================================

    normalized = normalize_resilience_events(
        result,
        query_id=query_id,
        trace_id=trace_id,
        service="multi-agent-graphrag",
        environment="local-v2-runtime-composition",
        primary_provider="openai",
        fallback_provider="deepseek",
        latency_ms=round(
            elapsed_ms,
            2,
        ),
        metadata={
            "step": "STEP V2-07F-04B-FIX1",
            "controlled_provider_calls": True,
            "runtime_composition_validation": True,
        },
    )

    source_snapshot = deepcopy(
        normalized
    )

    print()
    print("===== B. REAL CANONICAL EVENTS =====")
    print(
        "NORMALIZED EVENT COUNT :",
        len(normalized),
    )

    for event in normalized:
        print(
            "EVENT_ID=",
            event.get("event_id"),
            "| PROVIDER=",
            event.get("provider"),
            "| ATTEMPT=",
            event.get("attempt"),
            "| TYPE=",
            event.get("event_type"),
        )


    # ========================================================
    # C. REAL MULTI-SINK COMPONENTS
    # ========================================================

    cloud_stream = io.StringIO()

    cloud_sink = (
        CloudWatchStructuredJsonSink(
            stream=cloud_stream
        )
    )

    fake_langsmith = (
        FakeLangSmithClient()
    )

    langsmith_sink = LangSmithSink(
        client=fake_langsmith,
        project_name=(
            "GraphRAG-V2-07F-Offline"
        ),
    )

    router = TelemetrySinkRouter(
        sinks=[
            cloud_sink,
            langsmith_sink,
        ]
    )

    composition = (
        ResilienceObservabilityComposition(
            router=router
        )
    )

    summary = composition.deliver_events(
        normalized
    )


    # ========================================================
    # D. PARSE BOTH SINK OUTPUTS
    # ========================================================

    cloud_lines = [
        line
        for line
        in cloud_stream.getvalue().splitlines()
        if line.strip()
    ]

    cloud_events = [
        json.loads(line)
        for line in cloud_lines
    ]

    lang_runs = fake_langsmith.calls

    expected_deliveries = (
        len(normalized) * 2
    )

    delivery_math_pass = (
        summary.event_count
        == len(normalized)
        and summary.delivery_count
        == expected_deliveries
        and summary.failed_delivery_count
        == 0
        and len(cloud_events)
        == len(normalized)
        and len(lang_runs)
        == len(normalized)
    )

    print()
    print("===== C. MULTI-SINK DELIVERY =====")
    print(
        "EVENT COUNT         :",
        summary.event_count,
    )
    print(
        "EXPECTED DELIVERIES :",
        expected_deliveries,
    )
    print(
        "ACTUAL DELIVERIES   :",
        summary.delivery_count,
    )
    print(
        "FAILED DELIVERIES   :",
        summary.failed_delivery_count,
    )
    print(
        "CLOUDWATCH EVENTS   :",
        len(cloud_events),
    )
    print(
        "LANGSMITH RUNS      :",
        len(lang_runs),
    )
    print(
        "DELIVERY MATH       :",
        (
            "PASS"
            if delivery_math_pass
            else "FAIL"
        ),
    )


    # ========================================================
    # E. CROSS-SINK CORRELATION
    # ========================================================

    correlation_pass = True

    print()
    print("===== D. CROSS-SINK CORRELATION =====")

    for index, source_event in enumerate(
        normalized
    ):

        cloud_event = (
            cloud_events[index]
        )

        lang_run = (
            lang_runs[index]
        )

        lang_inputs = (
            lang_run.get(
                "inputs",
                {},
            )
        )

        lang_metadata = (
            lang_run
            .get("extra", {})
            .get("metadata", {})
        )

        query_match = (
            source_event.get("query_id")
            == cloud_event.get("query_id")
            == lang_inputs.get("query_id")
        )

        trace_match = (
            source_event.get("trace_id")
            == cloud_event.get("trace_id")
            == lang_inputs.get("trace_id")
        )

        event_match = (
            source_event.get("event_id")
            == cloud_event.get("event_id")
            == lang_metadata.get("event_id")
        )

        row_pass = (
            query_match
            and trace_match
            and event_match
        )

        correlation_pass = (
            correlation_pass
            and row_pass
        )

        print(
            source_event.get("event_id"),
            "QUERY_MATCH=",
            query_match,
            "TRACE_MATCH=",
            trace_match,
            "EVENT_MATCH=",
            event_match,
        )


    # ========================================================
    # F. RESILIENCE SIGNALS
    # ========================================================

    event_types = {
        str(event.get("event_type"))
        for event in normalized
    }

    retry_signal = any(
        "RETRY" in x.upper()
        for x in event_types
    )

    fallback_signal = any(
        "FALLBACK" in x.upper()
        for x in event_types
    )

    recovery_signal = any(
        (
            "RECOVER" in str(
                event.get("event_type")
            ).upper()
            or bool(
                event.get("recovered")
            )
        )
        for event in normalized
    )

    immutable_pass = (
        normalized
        == source_snapshot
    )

    runtime_pass = (
        bool(result.success)
        and bool(result.fallback_used)
        and delivery_math_pass
        and correlation_pass
        and immutable_pass
    )

    print()
    print("===== E. RESILIENCE TELEMETRY =====")
    print(
        "EVENT TYPES      :",
        sorted(event_types),
    )
    print(
        "RETRY SIGNAL     :",
        retry_signal,
    )
    print(
        "FALLBACK SIGNAL  :",
        fallback_signal,
    )
    print(
        "RECOVERY SIGNAL  :",
        recovery_signal,
    )

    print()
    print("===== F. IMMUTABILITY =====")
    print(
        "SOURCE EVENT IMMUTABILITY :",
        (
            "PASS"
            if immutable_pass
            else "FAIL"
        ),
    )


    # ========================================================
    # FINAL GATE
    # ========================================================

    print()
    print("=" * 64)

    if runtime_pass:

        print(
            "STEP V2-07F-04B-FIX1: PASS"
        )
        print(
            "REAL RESILIENCE IMPLEMENTATION: PASS"
        )
        print(
            "CANONICAL NORMALIZATION: PASS"
        )
        print(
            "RUNTIME COMPOSITION: PASS"
        )
        print(
            "MULTI-SINK DELIVERY: PASS"
        )
        print(
            "CROSS-SINK CORRELATION: PASS"
        )
        print(
            "SOURCE EVENT IMMUTABILITY: PASS"
        )

    else:

        print(
            "STEP V2-07F-04B-FIX1: BLOCKED"
        )

    print(
        "REAL AWS CALL: NO"
    )
    print(
        "REAL LANGSMITH API CALL: NO"
    )
    print(
        "REAL OPENAI CALL: NO"
    )
    print(
        "REAL DEEPSEEK CALL: NO"
    )

    print("=" * 64)

    if not runtime_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
