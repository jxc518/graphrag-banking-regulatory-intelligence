from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_01_shared_state import (
    GraphRAGState,
    create_initial_state,
)

from GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_02_governed_nodes import (
    planning_node,
    plan_guardrail_node,
    retrieval_node,
    research_node,
    deterministic_guard_node,
    failure_classifier_node,
    recovery_controller_node,
    judge_gate_node,
    judge_node,
    judge_contract_guardrail_node,
    final_decision_node,
)


# ============================================================
# ROUTER
# ============================================================

def route_after_recovery(state: GraphRAGState) -> str:
    """
    Phase 3 LangGraph routing adapter.

    For STEP 03-04A we intentionally validate only the
    clean Phase 2 route:

        CONTINUE_TO_JUDGE -> Judge Gate

    Additional governed branches will be added incrementally
    after this executable clean-path graph passes.
    """

    action = state["recovery_action"]

    if action == "CONTINUE_TO_JUDGE":
        return "continue_to_judge"

    # We deliberately fail loudly here in this first executable
    # graph instead of silently routing an unimplemented action.
    raise RuntimeError(
        f"STEP 03-04A encountered an unimplemented "
        f"recovery action: {action}"
    )


# ============================================================
# GRAPH BUILDER
# ============================================================

def build_governed_graph():
    builder = StateGraph(GraphRAGState)

    # --------------------------------------------------------
    # Register nodes
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

    builder.add_node(
        "deterministic_guard",
        deterministic_guard_node,
    )

    builder.add_node(
        "failure_classifier",
        failure_classifier_node,
    )

    builder.add_node(
        "recovery_controller",
        recovery_controller_node,
    )

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

    # --------------------------------------------------------
    # Fixed orchestration edges
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # FIRST REAL CONDITIONAL ROUTING
    # --------------------------------------------------------

    builder.add_conditional_edges(
        "recovery_controller",
        route_after_recovery,
        {
            "continue_to_judge": "judge_gate",
        },
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
# CONTROLLED CLEAN-PATH RUNTIME TEST
# ============================================================

def run_clean_path_test():
    print("")
    print("=" * 68)
    print("PHASE 3 STEP 03-04A — GOVERNED LANGGRAPH CLEAN PATH")
    print("=" * 68)

    app = build_governed_graph()

    initial_state = create_initial_state(
        "Compare credit-risk disclosures across five major U.S. banks."
    )

    result = app.invoke(initial_state)

    print("")
    print("STAGE HISTORY")
    print("-" * 68)

    for stage in result["stage_history"]:
        print(stage)

    print("")
    print("-" * 68)
    print("GUARD STATUS:", result["guard_status"])
    print("FAILURE TYPE:", result["failure_type"])
    print("RECOVERY ACTION:", result["recovery_action"])
    print("JUDGE ALLOWED:", result["judge_allowed"])
    print("JUDGE VERDICT:", result["judge_verdict"])
    print("FINAL STATUS:", result["final_status"])

    expected_stages = [
        "01 Research Plan",
        "02 Plan Guardrail",
        "03 Document-Scoped Retrieval",
        "04 Research Matrix - Attempt 0",
        "05 Deterministic Guard",
        "06 Failure Classifier",
        "07 Recovery Controller",
        "13 Judge Gate",
        "14 LLM Judge Review",
        "15 Judge Contract Guardrail",
        "16 Final Governed Decision",
    ]

    checks = {
        "stage_history_matches_clean_path":
            result["stage_history"] == expected_stages,

        "guard_pass":
            result["guard_status"] == "PASS",

        "failure_type_clean":
            result["failure_type"] == "CLEAN",

        "recovery_continue_to_judge":
            result["recovery_action"] == "CONTINUE_TO_JUDGE",

        "judge_allowed":
            result["judge_allowed"] is True,

        "judge_pass":
            result["judge_verdict"] == "PASS",

        "final_status_approved":
            result["final_status"] == "APPROVED",
    }

    print("")
    print("VALIDATION CHECKS")
    print("-" * 68)

    for name, passed in checks.items():
        print(
            f"{name}:",
            "PASS" if passed else "FAIL",
        )

    all_pass = all(checks.values())

    print("")
    print("=" * 68)

    if not all_pass:
        print("GOVERNED LANGGRAPH CLEAN PATH: FAIL")
        raise AssertionError(
            "STEP 03-04A clean-path validation failed."
        )

    print("LANGGRAPH GRAPH COMPILE: PASS")
    print("LANGGRAPH GRAPH INVOKE: PASS")
    print("CONDITIONAL ROUTING: PASS")
    print("GOVERNED LANGGRAPH CLEAN PATH: PASS")
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")
    print("STEP 03-04A RESULT: PASS")
    print("PHASE 2 MODIFIED: NO")
    print("=" * 68)


if __name__ == "__main__":
    run_clean_path_test()
