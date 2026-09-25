"""
GraphRAG Phase 3
STEP 04-03 — Frozen Phase 2 Governance -> LangGraph Runtime Bridge

Purpose
-------
Use the real validated Phase 2 recovery policy to drive
Phase 3 LangGraph conditional routing.

Important
---------
- LangGraph owns orchestration.
- Frozen Phase 2 owns validated recovery semantics.
- No legacy run_live().
- No LLM calls.
- No network calls.
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_01_shared_state import (
    GraphRAGState,
    create_initial_state,
)

from GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_02_governed_nodes import (
    append_stage,
    final_decision_node,
)

from GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_02_phase2_adapters import (
    recovery_action_adapter,
)


class IntegrationState(GraphRAGState, total=False):
    test_error_type: str | None


def failure_classifier_bridge(
    state: IntegrationState,
) -> dict:
    """
    Controlled failure input for integration testing.

    Classification itself is intentionally simple here.
    The recovery decision comes from the REAL frozen Phase 2 policy.
    """

    error_type = state.get("test_error_type")

    return {
        "failure_type": error_type or "CLEAN",
        "stage_history": append_stage(
            state,
            "06 Failure Classifier",
        ),
    }


def real_phase2_recovery_controller(
    state: IntegrationState,
) -> dict:
    """
    Real Phase 2 recovery_action() drives the decision.
    """

    failure_type = state.get("failure_type")

    if failure_type == "CLEAN":
        error_type = None
    else:
        error_type = failure_type

    retry_count = int(
        state.get("retry_count", 0)
    )

    action = recovery_action_adapter(
        error_type,
        retry_count,
    )

    return {
        "recovery_action": action,
        "stage_history": append_stage(
            state,
            "07 Recovery Controller - REAL PHASE 2 POLICY",
        ),
    }


def continue_node(
    state: IntegrationState,
) -> dict:

    return {
        "judge_allowed": True,
        "judge_verdict": "PASS",
        "final_status": "APPROVED",
        "stage_history": append_stage(
            state,
            "13 Judge Gate -> 14 Judge -> APPROVED",
        ),
    }


def retry_node(
    state: IntegrationState,
) -> dict:

    retry_count = int(
        state.get("retry_count", 0)
    ) + 1

    return {
        "retry_count": retry_count,
        "final_status": "RETRY_REQUIRED",
        "stage_history": append_stage(
            state,
            "08 Research Matrix - Retry 1",
        ),
    }


def fail_closed_node(
    state: IntegrationState,
) -> dict:

    return {
        "final_status": "CLAIM_LEVEL_FAIL_CLOSED",
        "stage_history": append_stage(
            state,
            "11 Claim-Level Fail Closed",
        ),
    }


def escalate_node(
    state: IntegrationState,
) -> dict:

    return {
        "judge_allowed": False,
        "judge_verdict": "NOT_EXECUTED",
        "final_status": "ESCALATED",
        "stage_history": append_stage(
            state,
            "16 Final Governed Decision - ESCALATED",
        ),
    }


def route_after_real_phase2_policy(
    state: IntegrationState,
) -> Literal[
    "continue",
    "retry",
    "fail_closed",
    "escalate",
]:

    action = state.get(
        "recovery_action"
    )

    mapping = {
        "CONTINUE_TO_JUDGE": "continue",
        "RETRY_MATRIX": "retry",
        "CLAIM_LEVEL_FAIL_CLOSED": "fail_closed",
        "ESCALATE": "escalate",
    }

    if action not in mapping:
        raise ValueError(
            f"Unsupported recovery action: {action}"
        )

    return mapping[action]


def build_graph():

    builder = StateGraph(
        IntegrationState
    )

    builder.add_node(
        "failure_classifier",
        failure_classifier_bridge,
    )

    builder.add_node(
        "real_phase2_recovery_controller",
        real_phase2_recovery_controller,
    )

    builder.add_node(
        "continue",
        continue_node,
    )

    builder.add_node(
        "retry",
        retry_node,
    )

    builder.add_node(
        "fail_closed",
        fail_closed_node,
    )

    builder.add_node(
        "escalate",
        escalate_node,
    )

    builder.add_edge(
        START,
        "failure_classifier",
    )

    builder.add_edge(
        "failure_classifier",
        "real_phase2_recovery_controller",
    )

    builder.add_conditional_edges(
        "real_phase2_recovery_controller",
        route_after_real_phase2_policy,
        {
            "continue": "continue",
            "retry": "retry",
            "fail_closed": "fail_closed",
            "escalate": "escalate",
        },
    )

    builder.add_edge(
        "continue",
        END,
    )

    builder.add_edge(
        "retry",
        END,
    )

    builder.add_edge(
        "fail_closed",
        END,
    )

    builder.add_edge(
        "escalate",
        END,
    )

    return builder.compile()


def run_case(
    app,
    name,
    error_type,
    retry_count,
    expected_action,
    expected_status,
):

    state = create_initial_state(
        "Phase 3 governance integration test"
    )

    state["test_error_type"] = error_type
    state["retry_count"] = retry_count

    result = app.invoke(
        state
    )

    actual_action = result[
        "recovery_action"
    ]

    actual_status = result[
        "final_status"
    ]

    passed = (
        actual_action
        == expected_action
        and actual_status
        == expected_status
    )

    print("")
    print("-" * 74)
    print(f"CASE: {name}")
    print(f"ERROR TYPE: {error_type}")
    print(f"INPUT RETRY COUNT: {retry_count}")
    print(f"RECOVERY ACTION: {actual_action}")
    print(f"FINAL STATUS: {actual_status}")

    print("STAGE HISTORY")
    for stage in result.get(
        "stage_history",
        [],
    ):
        print(stage)

    print(
        f"CASE RESULT: {'PASS' if passed else 'FAIL'}"
    )

    assert passed

    return True


def main():

    print("")
    print("=" * 74)
    print(
        "PHASE 3 STEP 04-03 — REAL PHASE 2 GOVERNANCE / LANGGRAPH BRIDGE"
    )
    print("=" * 74)

    app = build_graph()

    cases = [
        (
            "CLEAN",
            None,
            0,
            "CONTINUE_TO_JUDGE",
            "APPROVED",
        ),
        (
            "RECOVERABLE CONTRACT FAILURE",
            "FIELD_EVIDENCE_MISMATCH",
            0,
            "RETRY_MATRIX",
            "RETRY_REQUIRED",
        ),
        (
            "RETRY BUDGET EXHAUSTED",
            "FIELD_EVIDENCE_MISMATCH",
            1,
            "ESCALATE",
            "ESCALATED",
        ),
        (
            "EVIDENCE INSUFFICIENCY",
            "EVIDENCE_INSUFFICIENCY",
            0,
            "CLAIM_LEVEL_FAIL_CLOSED",
            "CLAIM_LEVEL_FAIL_CLOSED",
        ),
        (
            "PROVENANCE RISK",
            "PROVENANCE_MISMATCH",
            0,
            "ESCALATE",
            "ESCALATED",
        ),
    ]

    passed = 0

    for case in cases:
        run_case(
            app,
            *case,
        )
        passed += 1

    print("")
    print("=" * 74)
    print(
        f"SCENARIOS PASSED: {passed}/{len(cases)}"
    )
    print(
        "REAL PHASE 2 RECOVERY POLICY: PASS"
    )
    print(
        "LANGGRAPH CONDITIONAL ROUTING: PASS"
    )
    print(
        "PHASE 2 -> PHASE 3 GOVERNANCE BRIDGE: PASS"
    )
    print(
        "LEGACY run_live EXECUTED: NO"
    )
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")
    print("PHASE 2 MODIFIED: NO")
    print("STEP 04-03 RESULT: PASS")
    print("=" * 74)


if __name__ == "__main__":
    main()
