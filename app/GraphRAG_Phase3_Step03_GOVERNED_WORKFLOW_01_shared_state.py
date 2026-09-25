from typing import TypedDict


class GraphRAGState(TypedDict):
    """
    Shared workflow state for the governed Multi-Agent GraphRAG runtime.

    Phase 3 migration principle:
    Change the orchestration implementation,
    not the validated Phase 2 governance behavior.
    """

    # ---------------------------------------------------------
    # 1. USER INPUT
    # ---------------------------------------------------------
    query: str

    # ---------------------------------------------------------
    # 2. PLANNING AGENT
    # ---------------------------------------------------------
    research_plan: str

    # ---------------------------------------------------------
    # 3. RETRIEVAL
    # ---------------------------------------------------------
    retrieved_evidence: list[dict]

    # ---------------------------------------------------------
    # 4. RESEARCH AGENT
    # ---------------------------------------------------------
    research_matrix: list[dict]

    # ---------------------------------------------------------
    # 5. DETERMINISTIC GOVERNANCE
    # ---------------------------------------------------------
    guard_status: str

    # ---------------------------------------------------------
    # 6. FAILURE CLASSIFICATION
    # ---------------------------------------------------------
    failure_type: str

    # ---------------------------------------------------------
    # 7. GOVERNED RECOVERY
    # ---------------------------------------------------------
    retry_count: int
    recovery_action: str

    # ---------------------------------------------------------
    # 8. JUDGE GATE
    # ---------------------------------------------------------
    judge_allowed: bool

    # ---------------------------------------------------------
    # 9. SEMANTIC JUDGE
    # ---------------------------------------------------------
    judge_verdict: str

    # ---------------------------------------------------------
    # 10. FINAL GOVERNED DECISION
    # ---------------------------------------------------------
    final_status: str

    # ---------------------------------------------------------
    # 11. AUDIT / OBSERVABILITY
    # ---------------------------------------------------------
    stage_history: list[str]


def create_initial_state(query: str) -> GraphRAGState:
    """
    Create a clean initial state for one governed GraphRAG run.
    """

    return GraphRAGState(
        query=query,
        research_plan="",
        retrieved_evidence=[],
        research_matrix=[],
        guard_status="NOT_EVALUATED",
        failure_type="NOT_CLASSIFIED",
        retry_count=0,
        recovery_action="NOT_DECIDED",
        judge_allowed=False,
        judge_verdict="NOT_EVALUATED",
        final_status="IN_PROGRESS",
        stage_history=[],
    )


if __name__ == "__main__":

    test_state = create_initial_state(
        "Compare credit-risk disclosures across five major U.S. banks."
    )

    assert test_state["query"] != ""
    assert test_state["retry_count"] == 0
    assert test_state["judge_allowed"] is False
    assert test_state["final_status"] == "IN_PROGRESS"
    assert test_state["stage_history"] == []

    print("")
    print("============================================================")
    print("PHASE 3 STEP 03-01 — SHARED STATE VALIDATION")
    print("============================================================")
    print("QUERY:", test_state["query"])
    print("GUARD STATUS:", test_state["guard_status"])
    print("FAILURE TYPE:", test_state["failure_type"])
    print("RETRY COUNT:", test_state["retry_count"])
    print("RECOVERY ACTION:", test_state["recovery_action"])
    print("JUDGE ALLOWED:", test_state["judge_allowed"])
    print("JUDGE VERDICT:", test_state["judge_verdict"])
    print("FINAL STATUS:", test_state["final_status"])
    print("STAGE HISTORY:", test_state["stage_history"])
    print("")
    print("SHARED STATE CONTRACT: PASS")
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")
    print("============================================================")
