from typing import Dict, Any


# ============================================================
# PHASE 3 STEP 03-02
# Governed Workflow Node Definitions
# ============================================================


def append_stage(state: Dict[str, Any], stage_name: str) -> list[str]:
    """
    Return a new stage-history list without mutating the
    incoming state object directly.
    """
    history = list(state.get("stage_history", []))
    history.append(stage_name)
    return history


# ------------------------------------------------------------
# 01. PLANNING AGENT
# ------------------------------------------------------------
def planning_node(state):
    return {
        "research_plan": "SIMULATED_RESEARCH_PLAN",
        "stage_history": append_stage(state, "01 Research Plan"),
    }


# ------------------------------------------------------------
# 02. PLAN GUARDRAIL
# ------------------------------------------------------------
def plan_guardrail_node(state):
    return {
        "stage_history": append_stage(state, "02 Plan Guardrail"),
    }


# ------------------------------------------------------------
# 03. RETRIEVAL
# ------------------------------------------------------------
def retrieval_node(state):
    return {
        "retrieved_evidence": [
            {
                "evidence_id": "SIM_SPAN_001",
                "source": "SIMULATED_SOURCE",
            }
        ],
        "stage_history": append_stage(
            state,
            "03 Document-Scoped Retrieval",
        ),
    }


# ------------------------------------------------------------
# 04. RESEARCH AGENT
# ------------------------------------------------------------
def research_node(state):
    return {
        "research_matrix": [
            {
                "entity": "SIMULATED_BANK",
                "evidence_id": "SIM_SPAN_001",
            }
        ],
        "stage_history": append_stage(
            state,
            "04 Research Matrix - Attempt 0",
        ),
    }


# ------------------------------------------------------------
# 05. DETERMINISTIC GUARD
# ------------------------------------------------------------
def deterministic_guard_node(state):
    return {
        "guard_status": "PASS",
        "stage_history": append_stage(
            state,
            "05 Deterministic Guard",
        ),
    }


# ------------------------------------------------------------
# 06. FAILURE CLASSIFIER
# ------------------------------------------------------------
def failure_classifier_node(state):
    return {
        "failure_type": "CLEAN",
        "stage_history": append_stage(
            state,
            "06 Failure Classifier",
        ),
    }


# ------------------------------------------------------------
# 07. RECOVERY CONTROLLER
# ------------------------------------------------------------
def recovery_controller_node(state):
    return {
        "recovery_action": "CONTINUE_TO_JUDGE",
        "stage_history": append_stage(
            state,
            "07 Recovery Controller",
        ),
    }


# ------------------------------------------------------------
# 11. CLAIM-LEVEL FAIL CLOSED
# ------------------------------------------------------------
def claim_level_fail_closed_node(state):
    return {
        "stage_history": append_stage(
            state,
            "11 Claim-Level Fail Closed",
        ),
    }


# ------------------------------------------------------------
# 13. JUDGE GATE
# ------------------------------------------------------------
def judge_gate_node(state):
    allowed = (
        state.get("guard_status") == "PASS"
        and state.get("recovery_action") == "CONTINUE_TO_JUDGE"
    )

    return {
        "judge_allowed": allowed,
        "stage_history": append_stage(
            state,
            "13 Judge Gate",
        ),
    }


# ------------------------------------------------------------
# 14. JUDGE AGENT
# ------------------------------------------------------------
def judge_node(state):
    verdict = (
        "PASS"
        if state.get("judge_allowed")
        else "NOT_EXECUTED"
    )

    return {
        "judge_verdict": verdict,
        "stage_history": append_stage(
            state,
            "14 LLM Judge Review",
        ),
    }


# ------------------------------------------------------------
# 15. JUDGE CONTRACT GUARDRAIL
# ------------------------------------------------------------
def judge_contract_guardrail_node(state):
    return {
        "stage_history": append_stage(
            state,
            "15 Judge Contract Guardrail",
        ),
    }


# ------------------------------------------------------------
# 16. FINAL GOVERNED DECISION
# ------------------------------------------------------------
def final_decision_node(state):

    if state.get("recovery_action") == "ESCALATE":
        final_status = "ESCALATED"

    elif state.get("judge_verdict") == "PASS":
        final_status = "APPROVED"

    elif state.get("judge_verdict") == "REVISE":
        final_status = "PENDING_REVIEW"

    elif state.get("recovery_action") == "CLAIM_LEVEL_FAIL_CLOSED":
        final_status = "FAIL_CLOSED"

    else:
        final_status = "PENDING_REVIEW"

    return {
        "final_status": final_status,
        "stage_history": append_stage(
            state,
            "16 Final Governed Decision",
        ),
    }


# ============================================================
# LOCAL NODE CONTRACT VALIDATION
# ============================================================

if __name__ == "__main__":

    test_state = {
        "query": "Test query",
        "research_plan": "",
        "retrieved_evidence": [],
        "research_matrix": [],
        "guard_status": "NOT_EVALUATED",
        "failure_type": "NOT_CLASSIFIED",
        "retry_count": 0,
        "recovery_action": "NOT_DECIDED",
        "judge_allowed": False,
        "judge_verdict": "NOT_EVALUATED",
        "final_status": "IN_PROGRESS",
        "stage_history": [],
    }

    test_state.update(planning_node(test_state))
    test_state.update(plan_guardrail_node(test_state))
    test_state.update(retrieval_node(test_state))
    test_state.update(research_node(test_state))
    test_state.update(deterministic_guard_node(test_state))
    test_state.update(failure_classifier_node(test_state))
    test_state.update(recovery_controller_node(test_state))
    test_state.update(claim_level_fail_closed_node(test_state))
    test_state.update(judge_gate_node(test_state))
    test_state.update(judge_node(test_state))
    test_state.update(judge_contract_guardrail_node(test_state))
    test_state.update(final_decision_node(test_state))

    assert test_state["guard_status"] == "PASS"
    assert test_state["failure_type"] == "CLEAN"
    assert test_state["recovery_action"] == "CONTINUE_TO_JUDGE"
    assert test_state["judge_allowed"] is True
    assert test_state["judge_verdict"] == "PASS"
    assert test_state["final_status"] == "APPROVED"

    expected_stages = [
        "01 Research Plan",
        "02 Plan Guardrail",
        "03 Document-Scoped Retrieval",
        "04 Research Matrix - Attempt 0",
        "05 Deterministic Guard",
        "06 Failure Classifier",
        "07 Recovery Controller",
        "11 Claim-Level Fail Closed",
        "13 Judge Gate",
        "14 LLM Judge Review",
        "15 Judge Contract Guardrail",
        "16 Final Governed Decision",
    ]

    assert test_state["stage_history"] == expected_stages

    print("")
    print("============================================================")
    print("PHASE 3 STEP 03-02 — GOVERNED NODE CONTRACT")
    print("============================================================")

    for stage in test_state["stage_history"]:
        print(stage)

    print("")
    print("GUARD STATUS:", test_state["guard_status"])
    print("FAILURE TYPE:", test_state["failure_type"])
    print("RECOVERY ACTION:", test_state["recovery_action"])
    print("JUDGE ALLOWED:", test_state["judge_allowed"])
    print("JUDGE VERDICT:", test_state["judge_verdict"])
    print("FINAL STATUS:", test_state["final_status"])

    print("")
    print("GOVERNED NODE CONTRACT: PASS")
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")
    print("============================================================")
