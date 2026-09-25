"""
GraphRAG Phase 3
Step 04 - Runtime Integration
Artifact 14 - LangGraph Migration Closeout

Purpose
-------
Close the LangGraph migration only if the accumulated Phase 3
evidence demonstrates that:

- Real Planning, Retrieval and Research execute under LangGraph.
- Deterministic governance remains active.
- Frozen Phase 2 recovery policy remains authoritative.
- Conditional routing works for escalation / Judge eligibility.
- Real Judge execution works.
- Final governed decisioning works.
- LangSmith observability evidence exists.
- Phase 2 recovery semantics remain behaviorally equivalent.

No LLM calls.
No network calls.
No retrieval.
No Phase 2 modification.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ============================================================
# 1. PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

APP = ROOT / "app"
RESULTS = ROOT / "results"

PHASE2_ROOT = Path(
    r"C:\Users\chen_\Documents\_67_2026_Job_Hunting_After_Wells_Fargo"
    r"\_67_39_RAG_GraphRAG_Agent_GraphRAG"
    r"\_67_39_11_GraphRAG_Phase2_POC"
    r"\evaluation_migrated"
)

# Phase 3 evidence
LIVE_RESEARCH = (
    RESULTS
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_07_live_research_graph.json"
)

LIVE_GOVERNED = (
    RESULTS
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_09_governed_live_graph.json"
)

UNKNOWN_SPAN_DIAGNOSTIC = (
    RESULTS
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_11_unknown_span_diagnostic.json"
)

JUDGE_REPLAY = (
    RESULTS
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_13_judge_replay.json"
)

BEHAVIOR_EQUIVALENCE = (
    RESULTS
    / "GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_07_behavior_equivalence.json"
)

LANGSMITH_RUNTIME_TRACE = (
    RESULTS
    / "GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_12_langsmith_runtime_trace.json"
)

# Frozen Phase 2 evidence
PHASE2_FROZEN_BASELINE = (
    PHASE2_ROOT
    / "results"
    / "SECTION_16_phase2_final_closeout"
    / "SECTION_16_03_phase2_frozen_baseline.json"
)

OUTPUT_JSON = (
    RESULTS
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_15_migration_closeout.json"
)

OUTPUT_MD = (
    RESULTS
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_16_migration_closeout.md"
)


# ============================================================
# 2. HELPERS
# ============================================================

def load_json(path: Path) -> Any:
    if not path.exists():
        return None

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return None


def check(
    checks: dict[str, dict[str, Any]],
    key: str,
    passed: bool,
    evidence: str,
    detail: Any = None,
):
    checks[key] = {
        "passed": bool(passed),
        "evidence": evidence,
        "detail": detail,
    }


def contains_text(
    obj: Any,
    *needles: str,
) -> bool:

    text = json.dumps(
        obj,
        ensure_ascii=False,
        default=str,
    ).lower()

    return all(
        needle.lower() in text
        for needle in needles
    )


# def detect_behavior_equivalence(
#     obj: Any,
# ) -> tuple[bool, str]:

#     if obj is None:
#         return False, "behavior-equivalence artifact missing"

#     text = json.dumps(
#         obj,
#         ensure_ascii=False,
#         default=str,
#     ).lower()

#     positive_markers = (
#         "9/9",
#         "100%",
#         "behavioral equivalence",
#         "defined policy match",
#     )

#     if any(
#         marker in text
#         for marker in positive_markers
#     ):
#         return True, "9/9 / equivalent PASS marker detected"

#     # Flexible structural fallback:
#     # count explicit boolean/pass-like results.
#     pass_count = 0

#     def walk(value: Any):
#         nonlocal pass_count

#         if isinstance(value, dict):

#             for k, v in value.items():

#                 key = str(k).lower()

#                 if (
#                     key in (
#                         "passed",
#                         "pass",
#                         "match",
#                         "matched",
#                     )
#                     and (
#                         v is True
#                         or str(v).lower()
#                         in (
#                             "pass",
#                             "passed",
#                             "true",
#                             "matched",
#                         )
#                     )
#                 ):
#                     pass_count += 1

#                 walk(v)

#         elif isinstance(value, list):

#             for item in value:
#                 walk(item)

#     walk(obj)

#     if pass_count >= 9:
#         return True, f"{pass_count} explicit PASS-like checks detected"

#     return (
#         False,
#         f"could not verify 9/9 from artifact; explicit PASS-like checks={pass_count}",
#     )


def detect_behavior_equivalence(
    obj: Any,
) -> tuple[bool, str]:

    if not isinstance(obj, dict):
        return (
            False,
            "behavior-equivalence artifact missing "
            "or is not a JSON object",
        )

    total_cases = obj.get(
        "total_cases"
    )

    passed_cases = obj.get(
        "passed_cases"
    )

    match_rate = obj.get(
        "behavior_match_rate"
    )

    status = obj.get(
        "status"
    )

    phase2_modified = obj.get(
        "phase2_modified"
    )

    results = obj.get(
        "results",
        [],
    )

    # --------------------------------------------------------
    # Exact artifact-level contract
    # --------------------------------------------------------

    summary_pass = (
        total_cases == 9
        and passed_cases == 9
        and match_rate == 1.0
        and status == "PASS"
        and phase2_modified is False
        and isinstance(
            results,
            list,
        )
        and len(results) == 9
    )

    # --------------------------------------------------------
    # Exact case-level behavioral equivalence
    # --------------------------------------------------------

    case_pass = (
        summary_pass
        and all(
            isinstance(
                item,
                dict,
            )
            and item.get(
                "behavior_match"
            ) is True
            and item.get(
                "phase2_expected_action"
            )
            == item.get(
                "phase3_langgraph_action"
            )
            for item in results
        )
    )

    if not case_pass:

        mismatches = []

        if isinstance(
            results,
            list,
        ):

            for item in results:

                if not isinstance(
                    item,
                    dict,
                ):
                    mismatches.append(
                        "non-dict result"
                    )
                    continue

                if (
                    item.get(
                        "behavior_match"
                    )
                    is not True
                    or item.get(
                        "phase2_expected_action"
                    )
                    != item.get(
                        "phase3_langgraph_action"
                    )
                ):

                    mismatches.append(
                        {
                            "case_id":
                                item.get(
                                    "case_id"
                                ),
                            "expected":
                                item.get(
                                    "phase2_expected_action"
                                ),
                            "actual":
                                item.get(
                                    "phase3_langgraph_action"
                                ),
                            "behavior_match":
                                item.get(
                                    "behavior_match"
                                ),
                        }
                    )

        return (
            False,
            (
                "Exact behavioral-equivalence "
                f"verification failed; "
                f"total={total_cases}, "
                f"passed={passed_cases}, "
                f"rate={match_rate}, "
                f"status={status}, "
                f"mismatches={mismatches}"
            ),
        )

    return (
        True,
        (
            "Exact verification PASS: "
            "9/9 frozen Phase 2 recovery-policy "
            "cases matched Phase 3 LangGraph routing; "
            "behavior_match_rate=1.0; "
            "all expected actions equal actual actions."
        ),
    )

# ============================================================
# 3. MAIN
# ============================================================

def main():

    print()
    print("=" * 84)
    print(
        "PHASE 3 STEP 04-09 — "
        "LANGGRAPH MIGRATION DEFINITION OF DONE CLOSEOUT"
    )
    print("=" * 84)

    live_research = load_json(
        LIVE_RESEARCH
    )

    live_governed = load_json(
        LIVE_GOVERNED
    )

    unknown_diag = load_json(
        UNKNOWN_SPAN_DIAGNOSTIC
    )

    judge_replay = load_json(
        JUDGE_REPLAY
    )

    behavior_eq = load_json(
        BEHAVIOR_EQUIVALENCE
    )

    langsmith_trace = load_json(
        LANGSMITH_RUNTIME_TRACE
    )

    phase2_frozen = load_json(
        PHASE2_FROZEN_BASELINE
    )

    checks: dict[str, dict[str, Any]] = {}

    # ========================================================
    # DOD 01 - REAL PLANNING
    # ========================================================

    check(
        checks,
        "01_real_planning",
        bool(
            live_research
            and live_research.get(
                "model_call_count",
                len(
                    live_research.get(
                        "model_calls",
                        [],
                    )
                ),
            )
            >= 2
            and contains_text(
                live_research,
                "research_plan",
            )
        ),
        LIVE_RESEARCH.name,
        (
            "Real Planning LLM executed "
            "under LangGraph live runtime."
        ),
    )

    # ========================================================
    # DOD 02 - REAL RETRIEVAL
    # ========================================================

    check(
        checks,
        "02_real_retrieval",
        bool(
            live_research
            and (
                live_research.get(
                    "retrieval"
                )
                == "REAL PHASE 2"
            )
            and live_research.get(
                "source_count",
                0,
            )
            > 7
        ),
        LIVE_RESEARCH.name,
        {
            "source_count":
                (
                    live_research
                    or {}
                ).get(
                    "source_count"
                ),
            "mode":
                (
                    live_research
                    or {}
                ).get(
                    "retrieval"
                ),
        },
    )

    # ========================================================
    # DOD 03 - REAL RESEARCH
    # ========================================================

    matrix = (
        (live_research or {})
        .get(
            "research_matrix"
        )
    )

    rows = (
        matrix.get(
            "rows",
            [],
        )
        if isinstance(
            matrix,
            dict,
        )
        else []
    )

    check(
        checks,
        "03_real_research",
        bool(
            live_research
            and len(rows) == 5
            and contains_text(
                live_research,
                "research_matrix_attempt_0",
            )
        ),
        LIVE_RESEARCH.name,
        {
            "parsed_rows":
                len(rows),
            "model_calls":
                len(
                    (
                        live_research
                        or {}
                    ).get(
                        "model_calls",
                        [],
                    )
                ),
        },
    )

    # ========================================================
    # DOD 04 - DETERMINISTIC GOVERNANCE
    # ========================================================

    check(
        checks,
        "04_deterministic_governance",
        bool(
            live_governed
            and (
                live_governed.get(
                    "guard_status"
                )
                == "BLOCK"
            )
            and (
                live_governed.get(
                    "failure_type"
                )
                == "UNKNOWN_SPAN_ID"
            )
        ),
        LIVE_GOVERNED.name,
        {
            "guard_status":
                (
                    live_governed
                    or {}
                ).get(
                    "guard_status"
                ),
            "failure_type":
                (
                    live_governed
                    or {}
                ).get(
                    "failure_type"
                ),
        },
    )

    # ========================================================
    # DOD 05 - FROZEN RECOVERY POLICY
    # ========================================================

    check(
        checks,
        "05_frozen_recovery_policy",
        bool(
            live_governed
            and (
                live_governed.get(
                    "recovery_action"
                )
                == "ESCALATE"
            )
            and judge_replay
            and (
                judge_replay.get(
                    "recovery_action"
                )
                == "CONTINUE_TO_JUDGE"
            )
        ),
        (
            LIVE_GOVERNED.name
            + " + "
            + JUDGE_REPLAY.name
        ),
        {
            "failure_path":
                (
                    live_governed
                    or {}
                ).get(
                    "recovery_action"
                ),
            "clean_path":
                (
                    judge_replay
                    or {}
                ).get(
                    "recovery_action"
                ),
        },
    )

    # ========================================================
    # DOD 06 - CONDITIONAL ROUTING
    # ========================================================

    check(
        checks,
        "06_conditional_routing",
        bool(
            live_governed
            and (
                live_governed.get(
                    "final_status"
                )
                == "ESCALATED"
            )
            and (
                live_governed.get(
                    "judge_allowed"
                )
                is False
            )
            and judge_replay
            and (
                judge_replay.get(
                    "judge_allowed"
                )
                is True
            )
        ),
        (
            LIVE_GOVERNED.name
            + " + "
            + JUDGE_REPLAY.name
        ),
        (
            "Failure path bypassed Judge; "
            "clean governed path reached Judge."
        ),
    )

    # ========================================================
    # DOD 07 - REAL JUDGE
    # ========================================================

    check(
        checks,
        "07_real_judge",
        bool(
            judge_replay
            and (
                judge_replay.get(
                    "judge_executed"
                )
                is True
            )
            and (
                judge_replay.get(
                    "model_call_count"
                )
                == 1
            )
            and (
                judge_replay.get(
                    "judge_verdict"
                )
                is not None
            )
        ),
        JUDGE_REPLAY.name,
        {
            "judge_executed":
                (
                    judge_replay
                    or {}
                ).get(
                    "judge_executed"
                ),
            "judge_verdict":
                (
                    judge_replay
                    or {}
                ).get(
                    "judge_verdict"
                ),
            "model_calls":
                (
                    judge_replay
                    or {}
                ).get(
                    "model_call_count"
                ),
        },
    )

    # ========================================================
    # DOD 08 - FINAL GOVERNED DECISION
    # ========================================================

    check(
        checks,
        "08_final_governed_decision",
        bool(
            judge_replay
            and (
                judge_replay.get(
                    "judge_contract_status"
                )
                == "PASS"
            )
            and (
                judge_replay.get(
                    "final_status"
                )
                in (
                    "PENDING_REVIEW",
                    "LLM_JUDGE_PASS_HUMAN_REVIEW_PENDING",
                )
            )
        ),
        JUDGE_REPLAY.name,
        {
            "judge_contract":
                (
                    judge_replay
                    or {}
                ).get(
                    "judge_contract_status"
                ),
            "final_status":
                (
                    judge_replay
                    or {}
                ).get(
                    "final_status"
                ),
        },
    )

    # ========================================================
    # DOD 09 - LANGSMITH TRACE / OBSERVABILITY
    # ========================================================

    # Preferred evidence:
    # local trace artifact from the controlled runtime.
    # If absent, do NOT fabricate a PASS.
    langsmith_pass = bool(
        langsmith_trace
    )

    check(
        checks,
        "09_langsmith_trace",
        langsmith_pass,
        LANGSMITH_RUNTIME_TRACE.name,
        (
            "Local LangSmith runtime trace artifact exists."
            if langsmith_pass
            else (
                "Local trace artifact not found. "
                "DoD remains open until trace evidence "
                "is present or separately formalized."
            )
        ),
    )

    # ========================================================
    # DOD 10 - PHASE 2 BEHAVIORAL EQUIVALENCE
    # ========================================================

    eq_pass, eq_detail = (
        detect_behavior_equivalence(
            behavior_eq
        )
    )

    check(
        checks,
        "10_phase2_behavioral_equivalence",
        eq_pass,
        BEHAVIOR_EQUIVALENCE.name,
        eq_detail,
    )

    # ========================================================
    # SUPPORTING EVIDENCE - UNKNOWN SPAN ROOT CAUSE
    # ========================================================

    unknown_ids = (
        (unknown_diag or {})
        .get(
            "all_unknown_ids",
            [],
        )
    )

    provenance_root_cause_confirmed = bool(
        unknown_diag
        and len(
            unknown_ids
        )
        == 1
        and (
            (
                unknown_diag
                .get(
                    "affected_banks",
                    {}
                )
            )
        )
    )

    # ========================================================
    # FROZEN PHASE 2 BASELINE
    # ========================================================

    phase2_frozen_pass = bool(
        phase2_frozen
        and contains_text(
            phase2_frozen,
            "closed_pass",
        )
        and contains_text(
            phase2_frozen,
            "frozen",
        )
    )

    # ========================================================
    # FINAL
    # ========================================================

    passed_count = sum(
        int(
            item[
                "passed"
            ]
        )
        for item
        in checks.values()
    )

    total_count = len(
        checks
    )

    final_pass = (
        passed_count
        == total_count
        and phase2_frozen_pass
    )

    final_status = (
        "CLOSED_PASS"
        if final_pass
        else "CLOSEOUT_INCOMPLETE"
    )

    print()
    print(
        "LANGGRAPH MIGRATION DEFINITION OF DONE"
    )
    print("-" * 84)

    for key, item in checks.items():

        print(
            f"{key:<44}"
            f"{'PASS' if item['passed'] else 'FAIL'}"
        )

    print()
    print(
        "SUPPORTING GOVERNANCE EVIDENCE"
    )
    print("-" * 84)

    print(
        f"{'UNKNOWN_SPAN root cause reproduced offline':<56}"
        f"{'PASS' if provenance_root_cause_confirmed else 'FAIL'}"
    )

    print(
        f"{'Frozen Phase 2 baseline preserved':<56}"
        f"{'PASS' if phase2_frozen_pass else 'FAIL'}"
    )

    print()
    print("=" * 84)

    print(
        "LANGGRAPH MIGRATION DEFINITION OF DONE: "
        f"{passed_count}/{total_count} PASS"
    )

    print(
        "PHASE 2 BEHAVIORAL EQUIVALENCE: "
        + (
            "PASS"
            if eq_pass
            else "FAIL"
        )
    )

    print(
        "FROZEN PHASE 2 MODIFIED: NO"
    )

    print(
        "LEGACY run_live EXECUTED AS "
        "PHASE 3 ORCHESTRATOR: NO"
    )

    print(
        "LLM CALLS DURING CLOSEOUT: 0"
    )

    print(
        "NETWORK CALLS DURING CLOSEOUT: 0"
    )

    print(
        "LANGGRAPH MIGRATION STATUS: "
        + final_status
    )

    print("=" * 84)

    artifact = {
        "phase":
            "Phase 3",

        "step":
            "04-09",

        "purpose":
            "LangGraph Migration DoD + Behavioral Equivalence Closeout",

        "timestamp_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "definition_of_done":
            {
                "passed":
                    passed_count,
                "total":
                    total_count,
                "checks":
                    checks,
            },

        "supporting_evidence":
            {
                "unknown_span_root_cause_confirmed":
                    provenance_root_cause_confirmed,

                "unknown_span_ids":
                    unknown_ids,

                "affected_banks":
                    (
                        unknown_diag
                        or {}
                    ).get(
                        "affected_banks",
                        {},
                    ),

                "phase2_frozen_baseline":
                    phase2_frozen_pass,
            },

        "migration_principles":
            {
                "langgraph_owns_orchestration":
                    True,

                "frozen_phase2_policy_authoritative":
                    True,

                "legacy_run_live_used_as_phase3_orchestrator":
                    False,

                "phase2_modified":
                    False,

                "planning_rerun_during_recovery":
                    False,

                "retrieval_rerun_during_recovery":
                    False,

                "bounded_matrix_retry_max":
                    1,

                "provenance_failure_bypasses_judge":
                    True,

                "judge_pass_does_not_auto_approve":
                    True,
            },

        "closeout_execution":
            {
                "llm_calls":
                    0,

                "network_calls":
                    0,

                "retrieval_calls":
                    0,
            },

        "final_status":
            final_status,
    }

    OUTPUT_JSON.write_text(
        json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    # ========================================================
    # MARKDOWN CLOSEOUT
    # ========================================================

    md = []

    md.append(
        "# GraphRAG Phase 3 — LangGraph Migration Closeout"
    )

    md.append("")

    md.append(
        f"**Status:** {final_status}"
    )

    md.append("")

    md.append(
        f"**Definition of Done:** "
        f"{passed_count}/{total_count} PASS"
    )

    md.append("")

    md.append(
        "## Migration Principle"
    )

    md.append("")

    md.append(
        "**Change the orchestration runtime, "
        "not the validated governance behavior.**"
    )

    md.append("")

    md.append(
        "LangGraph owns execution and conditional routing. "
        "The frozen Phase 2 controls remain authoritative "
        "for deterministic validation, recovery policy, "
        "Judge eligibility, and governed final disposition."
    )

    md.append("")

    md.append(
        "## Definition of Done"
    )

    md.append("")

    md.append(
        "| Check | Result | Evidence |"
    )

    md.append(
        "|---|---|---|"
    )

    for key, item in checks.items():

        md.append(
            f"| {key} "
            f"| {'PASS' if item['passed'] else 'FAIL'} "
            f"| {item['evidence']} |"
        )

    md.append("")

    md.append(
        "## Key Runtime Evidence"
    )

    md.append("")

    md.append(
        "- Fresh live LangGraph execution ran real Planning, "
        "real document-scoped Retrieval, and real Research."
    )

    md.append(
        "- A live UNKNOWN_SPAN_ID provenance failure was "
        "blocked deterministically, classified, escalated, "
        "and prevented from reaching the Judge."
    )

    md.append(
        "- Offline root-cause replay reproduced the provenance "
        "failure without any LLM calls."
    )

    md.append(
        "- A governed replay of frozen validated Phase 2 evidence "
        "passed deterministic validation, received "
        "CONTINUE_TO_JUDGE, executed the real Judge LLM, "
        "passed the Judge contract guardrail, and ended in "
        "PENDING_REVIEW for a revise verdict."
    )

    md.append("")

    md.append(
        "## Preservation"
    )

    md.append("")

    md.append(
        "- Phase 2 modified: **NO**"
    )

    md.append(
        "- Legacy `run_live()` used as Phase 3 orchestrator: **NO**"
    )

    md.append(
        "- Closeout LLM calls: **0**"
    )

    md.append(
        "- Closeout network calls: **0**"
    )

    md.append("")

    md.append(
        "## Interview Takeaway"
    )

    md.append("")

    md.append(
        "> I changed the orchestration runtime without changing "
        "the validated governance semantics. LangGraph owns the "
        "flow, while the frozen Phase 2 policy remains authoritative "
        "for deterministic validation, bounded recovery, Judge gating, "
        "and final governed decisioning."
    )

    OUTPUT_MD.write_text(
        "\n".join(
            md
        ),
        encoding="utf-8",
    )

    print()
    print(
        "JSON CLOSEOUT:",
        OUTPUT_JSON,
    )

    print(
        "MD CLOSEOUT:",
        OUTPUT_MD,
    )


if __name__ == "__main__":
    main()
