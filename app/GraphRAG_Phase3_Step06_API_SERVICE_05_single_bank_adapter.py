"""
GraphRAG Phase 3
Step 06 — API Service
Artifact 05 — Single-Bank Planning Compatibility Adapter

Purpose
-------
Normalize one observed planner vocabulary mismatch at the serving
boundary without modifying the frozen Step04 governed runtime.

Observed real planner behavior
------------------------------
For a supported single-bank question, the real Planning Agent emitted:

    action = "use_existing"
    requests = []

The planner reason stated that sufficient evidence already existed in
the trusted seed sources.

The validated LangGraph plan contract accepts:

    retrieve
    answer

Therefore the narrow semantic normalization is:

    use_existing + empty requests -> answer

No other unsupported action is normalized.
"""

from __future__ import annotations

from typing import Any


NORMALIZED_FROM = "use_existing"
NORMALIZED_TO = "answer"


def normalize_research_plan(
    plan: Any,
) -> tuple[Any, bool]:
    """
    Normalize only the observed, unambiguous planning vocabulary case.

    Returns
    -------
    (normalized_plan, adapter_applied)
    """

    if not isinstance(plan, dict):
        return plan, False

    action = plan.get("action")
    requests = plan.get("requests")

    if (
        action == NORMALIZED_FROM
        and isinstance(requests, list)
        and len(requests) == 0
    ):
        normalized = dict(plan)

        normalized["action"] = NORMALIZED_TO

        return normalized, True

    return plan, False


def install(runtime_module):
    """
    Install a narrow wrapper around the existing Step04 Planning Agent.

    The Step04 source file is NOT modified.

    The wrapper normalizes the returned planning update before the
    existing Plan Guardrail sees it.
    """

    if getattr(
        runtime_module,
        "_step06_single_bank_adapter_installed",
        False,
    ):
        return runtime_module

    if not hasattr(
        runtime_module,
        "planning_agent_node",
    ):
        raise AttributeError(
            "Runtime does not expose planning_agent_node."
        )

    original_planning_agent = (
        runtime_module.planning_agent_node
    )

    async def planning_agent_node_compat(
        state,
    ):
        update = await original_planning_agent(
            state
        )

        if not isinstance(update, dict):
            raise TypeError(
                "Planning Agent returned a non-dict update."
            )

        plan = update.get(
            "research_plan"
        )

        normalized_plan, applied = (
            normalize_research_plan(
                plan
            )
        )

        if applied:
            update = dict(update)

            update["research_plan"] = (
                normalized_plan
            )

            print("")
            print(
                "[Step06 Planning Compatibility Adapter]"
            )
            print(
                "  Planner action: use_existing"
            )
            print(
                "  Normalized action: answer"
            )
            print(
                "  Reason: existing trusted evidence "
                "available; retrieval not required"
            )

        return update

    runtime_module.planning_agent_node = (
        planning_agent_node_compat
    )

    runtime_module._step06_single_bank_adapter_installed = (
        True
    )

    return runtime_module


if __name__ == "__main__":

    # Pure deterministic smoke tests.
    cases = [
        (
            {
                "action": "use_existing",
                "requests": [],
            },
            "answer",
            True,
        ),
        (
            {
                "action": "retrieve",
                "requests": [{"bank": "Wells Fargo"}],
            },
            "retrieve",
            False,
        ),
        (
            {
                "action": "answer",
                "requests": [],
            },
            "answer",
            False,
        ),
        (
            {
                "action": "use_existing",
                "requests": [{"bank": "Wells Fargo"}],
            },
            "use_existing",
            False,
        ),
    ]

    passed = 0

    for index, (
        plan,
        expected_action,
        expected_applied,
    ) in enumerate(
        cases,
        start=1,
    ):

        result, applied = (
            normalize_research_plan(
                plan
            )
        )

        actual_action = (
            result.get("action")
        )

        ok = (
            actual_action
            == expected_action
            and applied
            == expected_applied
        )

        passed += int(ok)

        print(
            f"CASE {index}:",
            "PASS" if ok else "FAIL",
            "| action=",
            actual_action,
            "| adapter_applied=",
            applied,
        )

    print("")
    print(
        f"ADAPTER UNIT SMOKE: "
        f"{passed}/{len(cases)} PASS"
    )
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")
    print("STEP04 FILES MODIFIED: NO")
    print("PHASE 2 MODIFIED: NO")
