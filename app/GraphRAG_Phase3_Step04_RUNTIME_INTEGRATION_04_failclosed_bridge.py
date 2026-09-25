from __future__ import annotations

from typing import Any, TypedDict
import copy

from langgraph.graph import StateGraph, START, END

from GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_02_phase2_adapters import (
    recovery_action_adapter,
    claim_level_fail_closed_adapter,
)


class BridgeState(TypedDict, total=False):
    matrix: dict[str, Any]
    insufficiencies: list[dict[str, Any]]
    failure_type: str | None
    retry_count: int
    recovery_action: str | None
    governed_candidate: dict[str, Any] | None
    revalidation_status: str | None
    judge_allowed: bool
    final_status: str | None
    stage_history: list[str]


def add_stage(state: BridgeState, label: str) -> list[str]:
    history = list(state.get("stage_history", []))
    history.append(label)
    return history


def recovery_controller(state: BridgeState) -> dict[str, Any]:
    error_type = state.get("failure_type")
    retry_count = int(state.get("retry_count", 0))

    action = recovery_action_adapter(
        error_type,
        retry_count,
    )

    return {
        "recovery_action": action,
        "stage_history": add_stage(
            state,
            "07 Recovery Controller - REAL PHASE 2 POLICY",
        ),
    }


def route_recovery(state: BridgeState) -> str:
    return str(state.get("recovery_action"))


def claim_level_fail_closed_node(
    state: BridgeState,
) -> dict[str, Any]:

    governed_candidate = claim_level_fail_closed_adapter(
        state["matrix"],
        state["insufficiencies"],
    )

    return {
        "governed_candidate": governed_candidate,
        "stage_history": add_stage(
            state,
            "11 Claim-Level Fail Closed - REAL PHASE 2",
        ),
    }


def deterministic_revalidation_node(
    state: BridgeState,
) -> dict[str, Any]:
    """
    Contract-level revalidation check for this migration bridge.

    The real Phase 2 apply_claim_level_fail_closed() has already performed
    the governance transformation. Here we verify the resulting canonical
    fail-closed invariants before allowing Judge Gate.

    Full sources/ds/base governed_validate() execution will be wired when
    the real retrieval/runtime context is attached in the next integration
    stage.
    """

    candidate = state.get("governed_candidate") or {}

    affected = {
        item["bank"]
        for item in state.get("insufficiencies", [])
    }

    rows = candidate.get("rows", [])

    safe = True

    for row in rows:
        if row.get("bank") not in affected:
            continue

        if row.get("status") != "missing_evidence":
            safe = False

        if row.get("value") is not None:
            safe = False

        if row.get("unit") is not None:
            safe = False

        if row.get("scope") is not None:
            safe = False

        field_evidence = row.get("field_evidence", {})

        for field in ("value", "unit", "period", "scope"):
            if field_evidence.get(field) != []:
                safe = False

    return {
        "revalidation_status": (
            "PASS"
            if safe
            else "BLOCK"
        ),
        "judge_allowed": safe,
        "stage_history": add_stage(
            state,
            "12 Deterministic Revalidation - FAIL-CLOSED INVARIANTS",
        ),
    }


def route_after_revalidation(state: BridgeState) -> str:
    if state.get("revalidation_status") == "PASS":
        return "JUDGE"
    return "ESCALATE"


def judge_gate_node(state: BridgeState) -> dict[str, Any]:
    return {
        "final_status": "APPROVED_FOR_JUDGE",
        "stage_history": add_stage(
            state,
            "13 Judge Gate - ALLOWED",
        ),
    }


def escalate_node(state: BridgeState) -> dict[str, Any]:
    return {
        "judge_allowed": False,
        "final_status": "ESCALATED",
        "stage_history": add_stage(
            state,
            "16 Final Governed Decision - ESCALATED",
        ),
    }


def retry_node(state: BridgeState) -> dict[str, Any]:
    return {
        "final_status": "RETRY_REQUIRED",
        "stage_history": add_stage(
            state,
            "08 Research Matrix - Retry Required",
        ),
    }


def continue_node(state: BridgeState) -> dict[str, Any]:
    return {
        "judge_allowed": True,
        "final_status": "APPROVED_FOR_JUDGE",
        "stage_history": add_stage(
            state,
            "13 Judge Gate - CLEAN",
        ),
    }


builder = StateGraph(BridgeState)

builder.add_node("recovery_controller", recovery_controller)
builder.add_node(
    "claim_level_fail_closed",
    claim_level_fail_closed_node,
)
builder.add_node(
    "deterministic_revalidation",
    deterministic_revalidation_node,
)
builder.add_node("judge_gate", judge_gate_node)
builder.add_node("escalate", escalate_node)
builder.add_node("retry_matrix", retry_node)
builder.add_node("continue_to_judge", continue_node)

builder.add_edge(START, "recovery_controller")

builder.add_conditional_edges(
    "recovery_controller",
    route_recovery,
    {
        "CONTINUE_TO_JUDGE": "continue_to_judge",
        "RETRY_MATRIX": "retry_matrix",
        "CLAIM_LEVEL_FAIL_CLOSED": "claim_level_fail_closed",
        "ESCALATE": "escalate",
    },
)

builder.add_edge(
    "claim_level_fail_closed",
    "deterministic_revalidation",
)

builder.add_conditional_edges(
    "deterministic_revalidation",
    route_after_revalidation,
    {
        "JUDGE": "judge_gate",
        "ESCALATE": "escalate",
    },
)

builder.add_edge("judge_gate", END)
builder.add_edge("escalate", END)
builder.add_edge("retry_matrix", END)
builder.add_edge("continue_to_judge", END)

graph = builder.compile()


def build_evidence_insufficiency_case() -> BridgeState:

    matrix = {
        "rows": [
            {
                "bank": "JPMorgan Chase",
                "status": "supported",
                "value": 2366,
                "unit": "USD million",
                "period": "Q2 2026",
                "scope": "net charge-offs",
                "limitation": None,
                "field_evidence": {
                    "value": ["SPAN_JPMC_001"],
                    "unit": ["SPAN_JPMC_001"],
                    "period": ["SPAN_JPMC_001"],
                    "scope": ["SPAN_JPMC_001"],
                },
            },
            {
                "bank": "Citigroup",
                "status": "supported",
                "value": 2100,
                "unit": "USD million",
                "period": "Q2 2026",
                "scope": "net charge-offs",
                "limitation": None,
                "field_evidence": {
                    "value": ["SPAN_CITI_001"],
                    "unit": ["SPAN_CITI_001"],
                    "period": ["SPAN_CITI_001"],
                    "scope": ["SPAN_CITI_001"],
                },
            },
        ]
    }

    insufficiencies = [
        {
            "bank": "JPMorgan Chase",
            "field": "unit",
            "reason": "Required explicit unit evidence is absent.",
        }
    ]

    return {
        "matrix": matrix,
        "insufficiencies": insufficiencies,
        "failure_type": "EVIDENCE_INSUFFICIENCY",
        "retry_count": 0,
        "stage_history": [],
    }


def main() -> None:

    print("=" * 74)
    print(
        "PHASE 3 STEP 04-04 — REAL CLAIM-LEVEL FAIL-CLOSED / LANGGRAPH BRIDGE"
    )
    print("=" * 74)

    initial = build_evidence_insufficiency_case()

    result = graph.invoke(initial)

    candidate = result["governed_candidate"]
    rows = candidate["rows"]

    jpm = next(
        row
        for row in rows
        if row["bank"] == "JPMorgan Chase"
    )

    citi = next(
        row
        for row in rows
        if row["bank"] == "Citigroup"
    )

    checks = {
        "REAL PHASE 2 RECOVERY ACTION":
            result["recovery_action"]
            == "CLAIM_LEVEL_FAIL_CLOSED",

        "AFFECTED CLAIM STATUS":
            jpm["status"]
            == "missing_evidence",

        "AFFECTED CLAIM VALUE CLEARED":
            jpm["value"] is None,

        "AFFECTED CLAIM UNIT CLEARED":
            jpm["unit"] is None,

        "AFFECTED CLAIM SCOPE CLEARED":
            jpm["scope"] is None,

        "AFFECTED FIELD EVIDENCE CLEARED":
            all(
                jpm["field_evidence"][field] == []
                for field in (
                    "value",
                    "unit",
                    "period",
                    "scope",
                )
            ),

        "UNAFFECTED CLAIM PRESERVED":
            citi["status"] == "supported"
            and citi["value"] == 2100,

        "REVALIDATION":
            result["revalidation_status"]
            == "PASS",

        "JUDGE GATE":
            result["judge_allowed"] is True,

        "FINAL STATUS":
            result["final_status"]
            == "APPROVED_FOR_JUDGE",
    }

    print()
    print("RECOVERY ACTION:", result["recovery_action"])
    print(
        "REVALIDATION STATUS:",
        result["revalidation_status"],
    )
    print(
        "JUDGE ALLOWED:",
        result["judge_allowed"],
    )
    print(
        "FINAL STATUS:",
        result["final_status"],
    )

    print()
    print("AFFECTED CLAIM AFTER REAL PHASE 2 FAIL-CLOSED")
    print("BANK:", jpm["bank"])
    print("STATUS:", jpm["status"])
    print("VALUE:", jpm["value"])
    print("UNIT:", jpm["unit"])
    print("SCOPE:", jpm["scope"])
    print(
        "FIELD EVIDENCE:",
        jpm["field_evidence"],
    )

    print()
    print("UNAFFECTED CLAIM")
    print("BANK:", citi["bank"])
    print("STATUS:", citi["status"])
    print("VALUE:", citi["value"])

    print()
    print("STAGE HISTORY")

    for stage in result["stage_history"]:
        print(stage)

    print()
    print("VALIDATION CHECKS")

    for name, passed in checks.items():
        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    passed_count = sum(checks.values())
    total_count = len(checks)

    print()
    print("=" * 74)
    print(
        f"CHECKS PASSED: "
        f"{passed_count}/{total_count}"
    )
    print(
        "REAL PHASE 2 RECOVERY POLICY:",
        "PASS"
        if checks["REAL PHASE 2 RECOVERY ACTION"]
        else "FAIL",
    )
    print(
        "REAL PHASE 2 CLAIM-LEVEL FAIL-CLOSED:",
        "PASS"
        if all(
            [
                checks["AFFECTED CLAIM STATUS"],
                checks["AFFECTED CLAIM VALUE CLEARED"],
                checks["AFFECTED CLAIM UNIT CLEARED"],
                checks["AFFECTED CLAIM SCOPE CLEARED"],
                checks["AFFECTED FIELD EVIDENCE CLEARED"],
                checks["UNAFFECTED CLAIM PRESERVED"],
            ]
        )
        else "FAIL",
    )
    print(
        "LANGGRAPH REVALIDATION ROUTING:",
        "PASS"
        if (
            checks["REVALIDATION"]
            and checks["JUDGE GATE"]
        )
        else "FAIL",
    )
    print("LEGACY run_live EXECUTED: NO")
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")
    print("PHASE 2 MODIFIED: NO")
    print(
        "STEP 04-04 RESULT:",
        "PASS"
        if passed_count == total_count
        else "FAIL",
    )
    print("=" * 74)


if __name__ == "__main__":
    main()
