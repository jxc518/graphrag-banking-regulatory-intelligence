import asyncio
import importlib.util
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parent

WRAPPER_FILE = (
    BASE
    / "GraphRAG_Phase3_StepV2_06_PROVIDER_RESILIENCE_01_wrapper.py"
)

spec = importlib.util.spec_from_file_location(
    "provider_resilience_wrapper",
    WRAPPER_FILE,
)

module = importlib.util.module_from_spec(spec)

# Register dynamic module before execution.
# dataclasses resolves cls.__module__ through sys.modules.
sys.modules[spec.name] = module

spec.loader.exec_module(module)


ProviderResilienceWrapper = module.ProviderResilienceWrapper
ProviderTimeoutError = module.ProviderTimeoutError
ProviderAuthenticationError = module.ProviderAuthenticationError


# ============================================================
# TEST HELPERS
# ============================================================

def assert_equal(actual, expected, message):

    if actual != expected:
        raise AssertionError(
            f"{message}: expected={expected!r}, actual={actual!r}"
        )


# ============================================================
# SCENARIO 1
# PRIMARY SUCCESS
# ============================================================

async def test_primary_success():

    calls = {"openai": 0}

    async def openai():

        calls["openai"] += 1

        return {
            "answer": "OPENAI_OK"
        }

    async def deepseek():

        raise AssertionError(
            "Fallback must not execute."
        )

    wrapper = ProviderResilienceWrapper(
        max_primary_retries=1,
        backoff_seconds=0,
    )

    result = await wrapper.execute(
        primary_name="openai",
        primary_call=openai,
        fallback_name="deepseek",
        fallback_call=deepseek,
    )

    assert_equal(result.success, True, "success")
    assert_equal(result.provider_used, "openai", "provider")
    assert_equal(result.fallback_used, False, "fallback")
    assert_equal(result.primary_attempts, 1, "primary attempts")
    assert_equal(calls["openai"], 1, "OpenAI calls")


# ============================================================
# SCENARIO 2
# TRANSIENT FAILURE -> RETRY -> PRIMARY SUCCESS
# ============================================================

async def test_retry_then_primary_success():

    calls = {"openai": 0}

    async def openai():

        calls["openai"] += 1

        if calls["openai"] == 1:
            raise ProviderTimeoutError(
                "simulated OpenAI timeout"
            )

        return {
            "answer": "OPENAI_RECOVERED"
        }

    async def deepseek():

        raise AssertionError(
            "Fallback must not execute."
        )

    wrapper = ProviderResilienceWrapper(
        max_primary_retries=1,
        backoff_seconds=0,
    )

    result = await wrapper.execute(
        primary_name="openai",
        primary_call=openai,
        fallback_name="deepseek",
        fallback_call=deepseek,
    )

    assert_equal(result.success, True, "success")
    assert_equal(result.provider_used, "openai", "provider")
    assert_equal(result.fallback_used, False, "fallback")
    assert_equal(result.primary_attempts, 2, "primary attempts")
    assert_equal(calls["openai"], 2, "OpenAI calls")


# ============================================================
# SCENARIO 3
# PRIMARY RETRY EXHAUSTED -> FALLBACK SUCCESS
# ============================================================

async def test_primary_failure_then_fallback():

    calls = {
        "openai": 0,
        "deepseek": 0,
    }

    async def openai():

        calls["openai"] += 1

        raise ProviderTimeoutError(
            "simulated persistent OpenAI timeout"
        )

    async def deepseek():

        calls["deepseek"] += 1

        return {
            "answer": "DEEPSEEK_OK"
        }

    wrapper = ProviderResilienceWrapper(
        max_primary_retries=1,
        backoff_seconds=0,
    )

    result = await wrapper.execute(
        primary_name="openai",
        primary_call=openai,
        fallback_name="deepseek",
        fallback_call=deepseek,
    )

    assert_equal(result.success, True, "success")
    assert_equal(result.provider_used, "deepseek", "provider")
    assert_equal(result.fallback_used, True, "fallback")
    assert_equal(result.primary_attempts, 2, "primary attempts")
    assert_equal(result.fallback_attempts, 1, "fallback attempts")
    assert_equal(calls["openai"], 2, "OpenAI calls")
    assert_equal(calls["deepseek"], 1, "DeepSeek calls")


# ============================================================
# SCENARIO 4
# NON-RETRYABLE FAILURE -> FAIL CLOSED
# ============================================================

async def test_non_retryable_failure():

    calls = {
        "openai": 0,
        "deepseek": 0,
    }

    async def openai():

        calls["openai"] += 1

        raise ProviderAuthenticationError(
            "simulated invalid OpenAI API key"
        )

    async def deepseek():

        calls["deepseek"] += 1

        return {
            "answer": "THIS_MUST_NOT_BE_USED"
        }

    wrapper = ProviderResilienceWrapper(
        max_primary_retries=1,
        backoff_seconds=0,
    )

    result = await wrapper.execute(
        primary_name="openai",
        primary_call=openai,
        fallback_name="deepseek",
        fallback_call=deepseek,
    )

    assert_equal(result.success, False, "success")
    assert_equal(result.provider_used, "openai", "provider")
    assert_equal(result.fallback_used, False, "fallback")
    assert_equal(result.primary_attempts, 1, "primary attempts")
    assert_equal(calls["openai"], 1, "OpenAI calls")
    assert_equal(calls["deepseek"], 0, "DeepSeek calls")


# ============================================================
# SCENARIO 5
# PRIMARY FAILS + FALLBACK FAILS -> FAIL CLOSED
# ============================================================

async def test_both_providers_fail():

    calls = {
        "openai": 0,
        "deepseek": 0,
    }

    async def openai():

        calls["openai"] += 1

        raise ProviderTimeoutError(
            "simulated OpenAI outage"
        )

    async def deepseek():

        calls["deepseek"] += 1

        raise ProviderTimeoutError(
            "simulated DeepSeek outage"
        )

    wrapper = ProviderResilienceWrapper(
        max_primary_retries=1,
        backoff_seconds=0,
    )

    result = await wrapper.execute(
        primary_name="openai",
        primary_call=openai,
        fallback_name="deepseek",
        fallback_call=deepseek,
    )

    assert_equal(result.success, False, "success")
    assert_equal(result.provider_used, "deepseek", "provider")
    assert_equal(result.fallback_used, True, "fallback")
    assert_equal(result.primary_attempts, 2, "primary attempts")
    assert_equal(result.fallback_attempts, 1, "fallback attempts")
    assert_equal(calls["openai"], 2, "OpenAI calls")
    assert_equal(calls["deepseek"], 1, "DeepSeek calls")


# ============================================================
# RUNNER
# ============================================================

async def main():

    tests = [
        (
            "01_PRIMARY_SUCCESS",
            test_primary_success,
        ),
        (
            "02_RETRY_PRIMARY_RECOVERY",
            test_retry_then_primary_success,
        ),
        (
            "03_FALLBACK_SUCCESS",
            test_primary_failure_then_fallback,
        ),
        (
            "04_NON_RETRYABLE_FAIL_CLOSED",
            test_non_retryable_failure,
        ),
        (
            "05_BOTH_PROVIDERS_FAIL_CLOSED",
            test_both_providers_fail,
        ),
    ]

    passed = 0

    print()
    print("=" * 72)
    print("STEP V2-06E - DETERMINISTIC PROVIDER RESILIENCE TEST")
    print("=" * 72)

    for name, test in tests:

        try:

            await test()

            passed += 1

            print(
                f"{name:<42} PASS"
            )

        except Exception as exc:

            print(
                f"{name:<42} FAIL"
            )

            print(
                f"    {type(exc).__name__}: {exc}"
            )

    print("-" * 72)

    print(
        f"PASSED : {passed}/{len(tests)}"
    )

    print(
        f"FAILED : {len(tests) - passed}/{len(tests)}"
    )

    if passed == len(tests):

        print(
            "STEP V2-06E RESULT : PASS"
        )

        print(
            "PROVIDER RETRY     : VALIDATED"
        )

        print(
            "PROVIDER FALLBACK  : VALIDATED"
        )

        print(
            "FAIL-CLOSED POLICY : VALIDATED"
        )

    else:

        print(
            "STEP V2-06E RESULT : FAIL"
        )

        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

