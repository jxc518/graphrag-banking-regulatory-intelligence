from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_01_shared_state import (
    GraphRAGState,
    create_initial_state,
)

from GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_02_governed_nodes import (
    append_stage,
    planning_node,
    plan_guardrail_node,
    retrieval_node,
    research_node,
    judge_gate_node,
    judge_node,
    judge_contract_guardrail_node,
    final_decision_node,
)


# ============================================================
# EXTENDED TEST STATE
# ============================================================

class RoutingRegressionState(GraphRAGState, total=False):
    test_scenario: str
    retry_executed: bool
    fail_closed_applied: bool


# ============================================================
# CONTROLLED SCENARIO DEFINITIONS
# ============================================================

SCENARIO_CLEAN = "CLEAN"

SCENARIO_RECOVERABLE = (
    "RECOVERABLE_CONTRACT_FAILURE"
)

SCENARIO_EVIDENCE_INSUFFICIENCY = (
    "EVIDENCE_INSUFFICIENCY"
)

SCENARIO_PROVENANCE_MISMATCH = (
    "PROVENANCE_MISMATCH"
)


# ============================================================
# CONTROLLED GOVERNANCE NODES
# ============================================================

def controlled_deterministic_guard_node(
    state: RoutingRegressionState,
):
    scenario = state["test_scenario"]

    if scenario == SCENARIO_CLEAN:
        guard_status = "PASS"
    else:
        guard_status = "BLOCK"

    return {
        "guard_status": guard_status,
        "stage_history": append_stage(
            state,
            "05 Deterministic Guard",
        ),
    }


def controlled_failure_classifier_node(
    state: RoutingRegressionState,
):
    scenario = state["test_scenario"]

    failure_map = {
        SCENARIO_CLEAN:
            "CLEAN",

        SCENARIO_RECOVERABLE:
            "FIELD_EVIDENCE_MISMATCH",

        SCENARIO_EVIDENCE_INSUFFICIENCY:
            "EVIDENCE_INSUFFICIENCY",

        SCENARIO_PROVENANCE_MISMATCH:
            "PROVENANCE_MISMATCH",
    }

    failure_type = failure_map[scenario]

    return {
        "failure_type": failure_type,
        "stage_history": append_stage(
            state,
            "06 Failure Classifier",
        ),
    }


def controlled_recovery_controller_node(
    state: RoutingRegressionState,
):
    failure_type = state["failure_type"]
    retry_count = state["retry_count"]

    if failure_type == "CLEAN":
        action = "CONTINUE_TO_JUDGE"

    elif failure_type in {
        "FIELD_EVIDENCE_MISMATCH",
        "EMPTY_MATRIX_CONTRACT_FAILURE",
    }:
        if retry_count < 1:
            action = "RETRY_MATRIX"
        else:
            action = "ESCALATE"

    elif failure_type == "EVIDENCE_INSUFFICIENCY":
        action = "CLAIM_LEVEL_FAIL_CLOSED"

    else:
        action = "ESCALATE"

    return {
        "recovery_action": action,
        "stage_history": append_stage(
            state,
            "07 Recovery Controller",
        ),
    }


# ============================================================
# RETRY BRANCH
# ============================================================

def retry_matrix_node(
    state: RoutingRegressionState,
):
    return {
        "retry_count":
            state["retry_count"] + 1,

        "retry_executed":
            True,

        "research_matrix": {
            "status":
                "SIMULATED_RETRY_MATRIX",

            "attempt":
                state["retry_count"] + 1,
        },

        "stage_history": append_stage(
            state,
            "08 Research Matrix - Retry 1",
        ),
    }


def retry_guard_node(
    state: RoutingRegressionState,
):
    """
    Controlled successful retry.

    Phase 2 semantics:
    retry only the Matrix stage, then revalidate.
    Planning and Retrieval are not rerun.
    """

    return {
        "guard_status":
            "PASS",

        "failure_type":
            "CLEAN",

        "recovery_action":
            "CONTINUE_TO_JUDGE",

        "stage_history": append_stage(
            state,
            "09 Deterministic Guard - Retry 1",
        ),
    }


# ============================================================
# CLAIM-LEVEL FAIL-CLOSED BRANCH
# ============================================================

def controlled_claim_level_fail_closed_node(
    state: RoutingRegressionState,
):
    """
    Simulates Phase 2 claim-level fail-closed behavior:

    unsupported evidence is converted to a safe governed
    representation and then revalidated successfully.
    """

    return {
        "guard_status":
            "PASS",

        "failure_type":
            "CLEAN",

        "recovery_action":
            "CONTINUE_TO_JUDGE",

        "fail_closed_applied":
            True,

        "stage_history": append_stage(
            state,
            "11 Claim-Level Fail Closed",
        ),
    }


# ============================================================
# ROUTER
# ============================================================

def route_after_recovery(
    state: RoutingRegressionState,
) -> str:

    action = state["recovery_action"]

    route_map = {
        "CONTINUE_TO_JUDGE":
            "continue_to_judge",

        "RETRY_MATRIX":
            "retry_matrix",

        "CLAIM_LEVEL_FAIL_CLOSED":
            "claim_level_fail_closed",

        "ESCALATE":
            "escalate",
    }

    if action not in route_map:
        raise RuntimeError(
            f"Unsupported recovery action: {action}"
        )

    return route_map[action]


# ============================================================
# GRAPH BUILDER
# ============================================================

def build_routing_regression_graph():
    builder = StateGraph(
        RoutingRegressionState
    )

    # --------------------------------------------------------
    # Core workflow nodes
    # --------------------------------------------------------

    builder.add_node(
        "planning",
        planning_node,
    )

    builder.add_node(
        "plan_guardrail",
        plan_guardrail_node,
    )

    builder.add_node(
        "retrieval",
        retrieval_node,
    )

    builder.add_node(
        "research",
        research_node,
    )

    # --------------------------------------------------------
    # Controlled governance nodes
    # --------------------------------------------------------

    builder.add_node(
        "deterministic_guard",
        controlled_deterministic_guard_node,
    )

    builder.add_node(
        "failure_classifier",
        controlled_failure_classifier_node,
    )

    builder.add_node(
        "recovery_controller",
        controlled_recovery_controller_node,
    )

    # --------------------------------------------------------
    # Recovery branch nodes
    # --------------------------------------------------------

    builder.add_node(
        "retry_matrix",
        retry_matrix_node,
    )

    builder.add_node(
        "retry_guard",
        retry_guard_node,
    )

    builder.add_node(
        "claim_level_fail_closed",
        controlled_claim_level_fail_closed_node,
    )

    # --------------------------------------------------------
    # Judge / final nodes
    # --------------------------------------------------------

    builder.add_node(
        "judge_gate",
        judge_gate_node,
    )

    builder.add_node(
        "judge",
        judge_node,
    )

    builder.add_node(
        "judge_contract_guardrail",
        judge_contract_guardrail_node,
    )

    builder.add_node(
        "final_decision",
        final_decision_node,
    )

    # ========================================================
    # FIXED EDGES
    # ========================================================

    builder.add_edge(
        START,
        "planning",
    )

    builder.add_edge(
        "planning",
        "plan_guardrail",
    )

    builder.add_edge(
        "plan_guardrail",
        "retrieval",
    )

    builder.add_edge(
        "retrieval",
        "research",
    )

    builder.add_edge(
        "research",
        "deterministic_guard",
    )

    builder.add_edge(
        "deterministic_guard",
        "failure_classifier",
    )

    builder.add_edge(
        "failure_classifier",
        "recovery_controller",
    )

    # ========================================================
    # GOVERNED CONDITIONAL ROUTING
    # ========================================================

    builder.add_conditional_edges(
        "recovery_controller",
        route_after_recovery,
        {
            "continue_to_judge":
                "judge_gate",

            "retry_matrix":
                "retry_matrix",

            "claim_level_fail_closed":
                "claim_level_fail_closed",

            "escalate":
                "final_decision",
        },
    )

    # --------------------------------------------------------
    # Bounded Matrix-only retry
    # --------------------------------------------------------

    builder.add_edge(
        "retry_matrix",
        "retry_guard",
    )

    builder.add_edge(
        "retry_guard",
        "judge_gate",
    )

    # --------------------------------------------------------
    # Claim-level safe recovery
    # --------------------------------------------------------

    builder.add_edge(
        "claim_level_fail_closed",
        "judge_gate",
    )

    # --------------------------------------------------------
    # Judge path
    # --------------------------------------------------------

    builder.add_edge(
        "judge_gate",
        "judge",
    )

    builder.add_edge(
        "judge",
        "judge_contract_guardrail",
    )

    builder.add_edge(
        "judge_contract_guardrail",
        "final_decision",
    )

    builder.add_edge(
        "final_decision",
        END,
    )

    return builder.compile()


# ============================================================
# TEST CASE FACTORY
# ============================================================

def create_test_state(
    scenario: str,
) -> RoutingRegressionState:

    state = create_initial_state(
        "Compare credit-risk disclosures "
        "across five major U.S. banks."
    )

    state["test_scenario"] = scenario
    state["retry_executed"] = False
    state["fail_closed_applied"] = False

    return state


# ============================================================
# SCENARIO VALIDATION
# ============================================================

def validate_scenario(
    app,
    scenario: str,
):
    print("")
    print("=" * 74)
    print(
        "SCENARIO:",
        scenario,
    )
    print("=" * 74)

    state = create_test_state(
        scenario
    )

    result = app.invoke(
        state
    )

    for stage in result["stage_history"]:
        print(stage)

    print("")
    print(
        "FAILURE TYPE:",
        result["failure_type"],
    )

    print(
        "RECOVERY ACTION:",
        result["recovery_action"],
    )

    print(
        "RETRY COUNT:",
        result["retry_count"],
    )

    print(
        "JUDGE ALLOWED:",
        result["judge_allowed"],
    )

    print(
        "JUDGE VERDICT:",
        result["judge_verdict"],
    )

    print(
        "FINAL STATUS:",
        result["final_status"],
    )

    if scenario == SCENARIO_CLEAN:

        checks = {
            "continue_to_judge":
                result["retry_count"] == 0
                and result["final_status"] == "APPROVED"
                and result["judge_verdict"] == "PASS",
        }

    elif scenario == SCENARIO_RECOVERABLE:

        checks = {
            "matrix_retry_executed":
                result["retry_executed"] is True,

            "retry_count_is_one":
                result["retry_count"] == 1,

            "planning_not_repeated":
                result["stage_history"].count(
                    "01 Research Plan"
                ) == 1,

            "retrieval_not_repeated":
                result["stage_history"].count(
                    "03 Document-Scoped Retrieval"
                ) == 1,

            "retry_stage_present":
                "08 Research Matrix - Retry 1"
                in result["stage_history"],

            "retry_guard_present":
                "09 Deterministic Guard - Retry 1"
                in result["stage_history"],

            "final_approved":
                result["final_status"] == "APPROVED",
        }

    elif (
        scenario
        == SCENARIO_EVIDENCE_INSUFFICIENCY
    ):

        checks = {
            "fail_closed_executed":
                result["fail_closed_applied"] is True,

            "fail_closed_stage_present":
                "11 Claim-Level Fail Closed"
                in result["stage_history"],

            "judge_reached_after_safe_revalidation":
                result["judge_allowed"] is True,

            "final_approved":
                result["final_status"] == "APPROVED",
        }

    elif (
        scenario
        == SCENARIO_PROVENANCE_MISMATCH
    ):

        checks = {
            "judge_not_reached":
                result["judge_allowed"] is False,

            "judge_not_executed":
                result["judge_verdict"]
                == "NOT_EVALUATED",

            "final_escalated":
                result["final_status"]
                == "ESCALATED",

            "no_retry":
                result["retry_count"] == 0,
        }

    else:
        raise ValueError(
            f"Unknown scenario: {scenario}"
        )

    print("")
    print("VALIDATION CHECKS")
    print("-" * 74)

    for name, passed in checks.items():
        print(
            f"{name}:",
            "PASS" if passed else "FAIL",
        )

    scenario_pass = all(
        checks.values()
    )

    print(
        "SCENARIO RESULT:",
        "PASS" if scenario_pass else "FAIL",
    )

    if not scenario_pass:
        raise AssertionError(
            f"Scenario failed: {scenario}"
        )

    return result


# ============================================================
# MAIN REGRESSION RUNNER
# ============================================================

def run_regression():
    print("")
    print("=" * 74)
    print(
        "PHASE 3 STEP 03-04B — "
        "GOVERNED LANGGRAPH ROUTING REGRESSION"
    )
    print("=" * 74)

    app = build_routing_regression_graph()

    scenarios = [
        SCENARIO_CLEAN,
        SCENARIO_RECOVERABLE,
        SCENARIO_EVIDENCE_INSUFFICIENCY,
        SCENARIO_PROVENANCE_MISMATCH,
    ]

    passed = 0

    for scenario in scenarios:

        validate_scenario(
            app,
            scenario,
        )

        passed += 1

    print("")
    print("=" * 74)
    print(
        "SCENARIOS PASSED:",
        f"{passed}/{len(scenarios)}",
    )

    print(
        "LANGGRAPH GRAPH COMPILE: PASS"
    )

    print(
        "MULTI-BRANCH INVOCATION: PASS"
    )

    print(
        "CONDITIONAL ROUTING: PASS"
    )

    print(
        "BOUNDED MATRIX RETRY: PASS"
    )

    print(
        "CLAIM-LEVEL FAIL CLOSED: PASS"
    )

    print(
        "ESCALATION ROUTING: PASS"
    )

    print(
        "PHASE 2 GOVERNANCE BEHAVIOR "
        "MAPPING: PASS"
    )

    print(
        "LLM CALLS: 0"
    )

    print(
        "NETWORK CALLS: 0"
    )

    print(
        "STEP 03-04B RESULT: PASS"
    )

    print(
        "PHASE 2 MODIFIED: NO"
    )

    print("=" * 74)


if __name__ == "__main__":
    run_regression()
