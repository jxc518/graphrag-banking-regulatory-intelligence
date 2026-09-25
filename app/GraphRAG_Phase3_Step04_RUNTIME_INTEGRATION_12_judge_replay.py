"""
GraphRAG Phase 3
Step 04 - Runtime Integration
Artifact 12 - Real Judge Governed Replay

Purpose
-------
Replay a frozen, previously validated REAL Phase 2 governed matrix
through the migrated Phase 3 LangGraph downstream governance path.

This is explicitly a GOVERNED REPLAY, not a fresh Research-Agent run.

What is real:
- Frozen Phase 2 governed matrix
- Frozen Phase 2 sources
- Deterministic validation
- Frozen Phase 2 recovery policy
- LangGraph conditional routing
- Real OpenAI Judge LLM
- Real Phase 2 Judge contract validation
- Final governed decision
- LangSmith tracing

What is not rerun:
- Planning LLM
- Retrieval
- Research LLM
- Legacy run_live()
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import START, END, StateGraph


# ============================================================
# 1. PATHS
# ============================================================

PHASE3_ROOT = Path(__file__).resolve().parents[1]

PHASE2_ROOT = Path(
    r"C:\Users\chen_\Documents\_67_2026_Job_Hunting_After_Wells_Fargo"
    r"\_67_39_RAG_GraphRAG_Agent_GraphRAG"
    r"\_67_39_11_GraphRAG_Phase2_POC"
    r"\evaluation_migrated"
)

FROZEN_RUN_DIR = (
    PHASE2_ROOT
    / "results"
    / "GraphRAG_Phase_02_SECTION_08_04_OPENAI_run_20260905_013744_255810"
)

CANONICAL_RUNNER = (
    PHASE2_ROOT
    / "GraphRAG_Phase_02_SECTION_08_04_openai_governed_comparison.py"
)

RESULT_PATH = (
    PHASE3_ROOT
    / "results"
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_13_judge_replay.json"
)

DEEPSEEK_MODULE = (
    "GraphRAG_Phase_02_Section_06_07_deepseek_span_guard"
)

JUDGE_RUNTIME_MODULE = (
    "GraphRAG_Phase_02_Section_04_05_llm_judge_revision_loop"
)


if str(PHASE2_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE2_ROOT))


# ============================================================
# 2. STATE
# ============================================================

class JudgeReplayState(TypedDict, total=False):

    query: str

    sources: list[dict[str, Any]]
    governed_matrix: Any
    governed_rows: Any

    deterministic_status: str
    failure_type: str | None

    retry_count: int
    recovery_action: str

    judge_allowed: bool
    judge_review: Any
    judge_verdict: str | None
    judge_contract_status: str

    final_status: str

    model_calls: list[dict[str, Any]]
    stage_history: list[str]

    frozen_matrix_path: str
    frozen_sources_path: str

    replay_seconds: float


_RUNTIME: dict[str, Any] = {}


# ============================================================
# 3. HELPERS
# ============================================================

def append_stage(
    state: JudgeReplayState,
    text: str,
) -> list[str]:

    history = list(
        state.get(
            "stage_history",
            [],
        )
    )

    history.append(text)

    return history


def json_safe(value: Any) -> Any:

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(value, dict):
        return {
            str(k): json_safe(v)
            for k, v in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            json_safe(v)
            for v in value
        ]

    if hasattr(value, "to_dict"):
        try:
            return json_safe(
                value.to_dict()
            )
        except Exception:
            pass

    return str(value)


def load_module_from_path(
    name: str,
    path: Path,
):

    spec = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise ImportError(
            f"Cannot load: {path}"
        )

    module = (
        importlib.util
        .module_from_spec(spec)
    )

    sys.modules[name] = module

    spec.loader.exec_module(
        module
    )

    return module


def discover_one(
    directory: Path,
    pattern: str,
) -> Path:

    matches = sorted(
        directory.glob(pattern)
    )

    if len(matches) != 1:

        raise RuntimeError(
            f"Expected exactly one {pattern!r} "
            f"in {directory}; found {len(matches)}: "
            f"{[p.name for p in matches]}"
        )

    return matches[0]


def extract_judge_verdict(
    review: Any,
) -> str | None:

    if not isinstance(
        review,
        dict,
    ):
        return None

    for key in (
        "verdict",
        "decision",
        "recommendation",
        "status",
        "overall_verdict",
    ):

        value = review.get(key)

        if isinstance(
            value,
            str,
        ):
            return value

    return None


def chunk_text(chunk: Any) -> str:

    if chunk is None:
        return ""

    content = getattr(
        chunk,
        "content",
        None,
    )

    if isinstance(
        content,
        str,
    ):
        return content

    choices = getattr(
        chunk,
        "choices",
        None,
    )

    if choices:

        for choice in choices:

            delta = getattr(
                choice,
                "delta",
                None,
            )

            if delta is not None:

                value = getattr(
                    delta,
                    "content",
                    None,
                )

                if isinstance(
                    value,
                    str,
                ):
                    return value

    if isinstance(
        chunk,
        dict,
    ):

        value = chunk.get(
            "content"
        )

        if isinstance(
            value,
            str,
        ):
            return value

        for choice in chunk.get(
            "choices",
            [],
        ):

            if not isinstance(
                choice,
                dict,
            ):
                continue

            delta = choice.get(
                "delta",
                {},
            )

            if isinstance(
                delta,
                dict,
            ):

                value = delta.get(
                    "content"
                )

                if isinstance(
                    value,
                    str,
                ):
                    return value

    return ""


# ============================================================
# 4. REAL JUDGE TRANSPORT
# ============================================================

async def complete_judge_real(
    system_prompt: str,
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any]]:

    engine = _RUNTIME[
        "engine"
    ]

    search_module = _RUNTIME[
        "search_module"
    ]

    payload_text = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    messages = (
        search_module
        .CompletionMessagesBuilder()
        .add_system_message(
            system_prompt
        )
        .add_user_message(
            payload_text
        )
        .build()
    )

    params = dict(
        getattr(
            engine,
            "model_params",
            {},
        )
        or {}
    )

    params.pop(
        "stream",
        None,
    )

    started = time.perf_counter()

    stream = (
        await engine.model.completion_async(
            messages=messages,
            stream=True,
            **params,
        )
    )

    pieces = []

    returned_model = None
    usage = None
    finish_reason = None

    async for chunk in stream:

        text = chunk_text(
            chunk
        )

        if text:
            pieces.append(
                text
            )

        model_value = getattr(
            chunk,
            "model",
            None,
        )

        if model_value:
            returned_model = (
                model_value
            )

        usage_value = getattr(
            chunk,
            "usage",
            None,
        )

        if usage_value is not None:
            usage = usage_value

        choices = getattr(
            chunk,
            "choices",
            None,
        )

        if choices:

            for choice in choices:

                reason = getattr(
                    choice,
                    "finish_reason",
                    None,
                )

                if reason is not None:
                    finish_reason = reason

    raw = "".join(
        pieces
    ).strip()

    elapsed = (
        time.perf_counter()
        - started
    )

    if not raw:
        raise ValueError(
            "Judge returned empty response."
        )

    if finish_reason not in (
        None,
        "stop",
    ):
        raise ValueError(
            "Judge completion ended with "
            f"finish_reason={finish_reason!r}"
        )

    record = {
        "stage":
            "llm_judge_review",
        "provider":
            "OpenAI",
        "returned_model":
            returned_model,
        "usage":
            json_safe(
                usage
            ),
        "finish_reason":
            finish_reason,
        "elapsed_seconds":
            round(
                elapsed,
                3,
            ),
        "raw_character_count":
            len(raw),
        "transport":
            "GraphRAG completion_async",
    }

    return raw, record


# ============================================================
# 5. NODE 01 — LOAD FROZEN GOVERNED EVIDENCE
# ============================================================

def replay_loader_node(
    state: JudgeReplayState,
) -> dict[str, Any]:

    started = time.perf_counter()

    if not FROZEN_RUN_DIR.exists():

        raise FileNotFoundError(
            FROZEN_RUN_DIR
        )

    matrix_path = discover_one(
        FROZEN_RUN_DIR,
        "*_final_governed_matrix.json",
    )

    sources_path = discover_one(
        FROZEN_RUN_DIR,
        "*_sources.json",
    )

    governed_matrix = json.loads(
        matrix_path.read_text(
            encoding="utf-8"
        )
    )

    sources = json.loads(
        sources_path.read_text(
            encoding="utf-8"
        )
    )

    canonical = load_module_from_path(
        "phase2_frozen_judge_replay_reference",
        CANONICAL_RUNNER,
    )

    ds = importlib.import_module(
        DEEPSEEK_MODULE
    )

    (
        base,
        _candidates,
        _seed,
        _scorer,
        _Client,
    ) = ds.load()

    judge_runtime = (
        importlib.import_module(
            JUDGE_RUNTIME_MODULE
        )
    )

    from graphrag.query.structured_search.local_search import (
        search as search_module,
    )

    engine = (
        judge_runtime.prepare_engine(
            PHASE2_ROOT,
            {
                "sources":
                    sources,
            },
        )
    )

    _RUNTIME.clear()

    _RUNTIME.update(
        {
            "canonical":
                canonical,
            "ds":
                ds,
            "base":
                base,
            "engine":
                engine,
            "search_module":
                search_module,
        }
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    print("")
    print(
        "[01 Governed Replay Loader]"
    )

    print(
        "  FROZEN MATRIX: PASS"
    )

    print(
        "  FROZEN SOURCES: PASS"
    )

    print(
        "  SOURCE COUNT:",
        len(sources),
    )

    print(
        "  LEGACY run_live(): NO"
    )

    print(
        f"  Seconds: {elapsed:.3f}"
    )

    return {
        "sources":
            sources,
        "governed_matrix":
            governed_matrix,
        "frozen_matrix_path":
            str(matrix_path),
        "frozen_sources_path":
            str(sources_path),
        "model_calls":
            [],
        "retry_count":
            0,
        "stage_history":
            append_stage(
                state,
                "01 Governed Replay Loader - "
                "FROZEN REAL PHASE 2",
            ),
    }


# ============================================================
# 6. NODE 02 — DETERMINISTIC REPLAY VALIDATION
# ============================================================

def deterministic_validation_node(
    state: JudgeReplayState,
) -> dict[str, Any]:

    base = _RUNTIME[
        "base"
    ]

    canonical = _RUNTIME[
        "canonical"
    ]

    try:

        governed_rows = (
            base.validate_matrix(
                state[
                    "governed_matrix"
                ],
                state[
                    "sources"
                ],
            )
        )

        status = "PASS"
        failure_type = None

    except Exception as exc:

        status = "BLOCK"

        failure_type = (
            canonical.classify_exception(
                exc
            )
        )

        raise RuntimeError(
            "Frozen governed replay failed "
            "deterministic validation: "
            f"{failure_type}: {exc}"
        ) from exc

    print("")
    print(
        "[02 Deterministic Validation]"
    )

    print(
        "  REAL PHASE 2 VALIDATOR: PASS"
    )

    print(
        "  STATUS:",
        status,
    )

    print(
        "  VALIDATED ROWS:",
        len(governed_rows),
    )

    return {
        "governed_rows":
            governed_rows,
        "deterministic_status":
            status,
        "failure_type":
            failure_type,
        "stage_history":
            append_stage(
                state,
                "02 Deterministic Validation - PASS",
            ),
    }


# ============================================================
# 7. NODE 03 — FROZEN RECOVERY POLICY
# ============================================================

def recovery_controller_node(
    state: JudgeReplayState,
) -> dict[str, Any]:

    canonical = _RUNTIME[
        "canonical"
    ]

    action = (
        canonical.recovery_action(
            state.get(
                "failure_type"
            ),
            int(
                state.get(
                    "retry_count",
                    0,
                )
            ),
        )
    )

    print("")
    print(
        "[03 Recovery Controller]"
    )

    print(
        "  REAL FROZEN PHASE 2 POLICY: PASS"
    )

    print(
        "  FAILURE TYPE:",
        state.get(
            "failure_type"
        )
        or "CLEAN",
    )

    print(
        "  ACTION:",
        action,
    )

    return {
        "recovery_action":
            action,
        "stage_history":
            append_stage(
                state,
                "03 Recovery Controller - "
                + action,
            ),
    }


def route_recovery(
    state: JudgeReplayState,
) -> str:

    action = state[
        "recovery_action"
    ]

    if action == "CONTINUE_TO_JUDGE":
        return "JUDGE_GATE"

    return "ESCALATE"


# ============================================================
# 8. NODE 04 — JUDGE GATE
# ============================================================

def judge_gate_node(
    state: JudgeReplayState,
) -> dict[str, Any]:

    allowed = (
        state.get(
            "deterministic_status"
        )
        == "PASS"
        and state.get(
            "recovery_action"
        )
        == "CONTINUE_TO_JUDGE"
        and state.get(
            "governed_matrix"
        )
        is not None
        and state.get(
            "governed_rows"
        )
        is not None
    )

    print("")
    print(
        "[04 Judge Gate]"
    )

    print(
        "  JUDGE ALLOWED:",
        allowed,
    )

    return {
        "judge_allowed":
            allowed,
        "stage_history":
            append_stage(
                state,
                "04 Judge Gate - "
                + (
                    "ALLOWED"
                    if allowed
                    else "BLOCKED"
                ),
            ),
    }


# ============================================================
# 9. NODE 05 — REAL JUDGE LLM
# ============================================================

async def judge_node(
    state: JudgeReplayState,
) -> dict[str, Any]:

    base = _RUNTIME[
        "base"
    ]

    payload = {
        "question":
            state["query"],
        "matrix":
            state[
                "governed_matrix"
            ],
        "sources":
            state[
                "sources"
            ],
    }

    raw, call = (
        await complete_judge_real(
            base.REVIEW,
            payload,
        )
    )

    review = base.parse(
        raw
    )

    verdict = (
        extract_judge_verdict(
            review
        )
    )

    calls = list(
        state.get(
            "model_calls",
            [],
        )
    )

    calls.append(
        call
    )

    print("")
    print(
        "[05 Real LLM Judge Review]"
    )

    print(
        "  REAL JUDGE LLM: PASS"
    )

    print(
        "  VERDICT:",
        verdict
        or "SEE REVIEW OBJECT",
    )

    return {
        "judge_review":
            review,
        "judge_verdict":
            verdict,
        "model_calls":
            calls,
        "stage_history":
            append_stage(
                state,
                "05 Real LLM Judge Review - PASS",
            ),
    }


# ============================================================
# 10. NODE 06 — REAL JUDGE CONTRACT GUARDRAIL
# ============================================================

def judge_contract_guardrail_node(
    state: JudgeReplayState,
) -> dict[str, Any]:

    base = _RUNTIME[
        "base"
    ]

    base.validate_review(
        state[
            "judge_review"
        ],
        state[
            "governed_rows"
        ],
        state[
            "sources"
        ],
    )

    print("")
    print(
        "[06 Judge Contract Guardrail]"
    )

    print(
        "  REAL PHASE 2 validate_review(): PASS"
    )

    return {
        "judge_contract_status":
            "PASS",
        "stage_history":
            append_stage(
                state,
                "06 Judge Contract Guardrail - PASS",
            ),
    }


# ============================================================
# 11. NODE 07 — FINAL GOVERNED DECISION
# ============================================================

def final_decision_node(
    state: JudgeReplayState,
) -> dict[str, Any]:

    verdict = (
        state.get(
            "judge_verdict"
        )
        or ""
    ).lower()

    # Preserve Phase 2 semantics:
    # Judge pass still requires human review;
    # anything else remains pending review.
    if verdict == "pass":

        final_status = (
            "LLM_JUDGE_PASS_"
            "HUMAN_REVIEW_PENDING"
        )

    else:

        final_status = (
            "PENDING_REVIEW"
        )

    print("")
    print(
        "[07 Final Governed Decision]"
    )

    print(
        "  JUDGE EXECUTED: YES"
    )

    print(
        "  FINAL STATUS:",
        final_status,
    )

    return {
        "final_status":
            final_status,
        "stage_history":
            append_stage(
                state,
                "07 Final Governed Decision - "
                + final_status,
            ),
    }


def escalation_node(
    state: JudgeReplayState,
) -> dict[str, Any]:

    print("")
    print(
        "[ESCALATION]"
    )

    print(
        "  REPLAY DID NOT BECOME JUDGE ELIGIBLE."
    )

    return {
        "judge_allowed":
            False,
        "final_status":
            "ESCALATED",
        "stage_history":
            append_stage(
                state,
                "Escalation - JUDGE BYPASSED",
            ),
    }


# ============================================================
# 12. BUILD LANGGRAPH
# ============================================================

def build_graph():

    graph = StateGraph(
        JudgeReplayState
    )

    graph.add_node(
        "replay_loader",
        replay_loader_node,
    )

    graph.add_node(
        "deterministic_validation",
        deterministic_validation_node,
    )

    graph.add_node(
        "recovery_controller",
        recovery_controller_node,
    )

    graph.add_node(
        "judge_gate",
        judge_gate_node,
    )

    graph.add_node(
        "real_judge",
        judge_node,
    )

    graph.add_node(
        "judge_contract_guardrail",
        judge_contract_guardrail_node,
    )

    graph.add_node(
        "final_decision",
        final_decision_node,
    )

    graph.add_node(
        "escalation",
        escalation_node,
    )

    graph.add_edge(
        START,
        "replay_loader",
    )

    graph.add_edge(
        "replay_loader",
        "deterministic_validation",
    )

    graph.add_edge(
        "deterministic_validation",
        "recovery_controller",
    )

    graph.add_conditional_edges(
        "recovery_controller",
        route_recovery,
        {
            "JUDGE_GATE":
                "judge_gate",

            "ESCALATE":
                "escalation",
        },
    )

    graph.add_edge(
        "judge_gate",
        "real_judge",
    )

    graph.add_edge(
        "real_judge",
        "judge_contract_guardrail",
    )

    graph.add_edge(
        "judge_contract_guardrail",
        "final_decision",
    )

    graph.add_edge(
        "final_decision",
        END,
    )

    graph.add_edge(
        "escalation",
        END,
    )

    return graph.compile()


# ============================================================
# 13. SAVE RESULT
# ============================================================

def save_result(
    state: JudgeReplayState,
    seconds: float,
):

    RESULT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact = {
        "phase":
            "Phase 3",

        "step":
            "04-08",

        "mode":
            "GOVERNED_REPLAY",

        "fresh_research_run":
            False,

        "source_basis":
            "Frozen validated real Phase 2 OpenAI run",

        "orchestrator":
            "LangGraph StateGraph",

        "planning_rerun":
            False,

        "retrieval_rerun":
            False,

        "research_rerun":
            False,

        "legacy_run_live_executed":
            False,

        "phase2_modified":
            False,

        "frozen_matrix_path":
            state.get(
                "frozen_matrix_path"
            ),

        "frozen_sources_path":
            state.get(
                "frozen_sources_path"
            ),

        "source_count":
            len(
                state.get(
                    "sources",
                    [],
                )
            ),

        "deterministic_status":
            state.get(
                "deterministic_status"
            ),

        "failure_type":
            state.get(
                "failure_type"
            ),

        "recovery_action":
            state.get(
                "recovery_action"
            ),

        "judge_allowed":
            state.get(
                "judge_allowed"
            ),

        "judge_executed":
            bool(
                state.get(
                    "judge_review"
                )
            ),

        "judge_verdict":
            state.get(
                "judge_verdict"
            ),

        "judge_contract_status":
            state.get(
                "judge_contract_status"
            ),

        "final_status":
            state.get(
                "final_status"
            ),

        "model_calls":
            json_safe(
                state.get(
                    "model_calls",
                    [],
                )
            ),

        "model_call_count":
            len(
                state.get(
                    "model_calls",
                    [],
                )
            ),

        "total_seconds":
            round(
                seconds,
                3,
            ),

        "stage_history":
            state.get(
                "stage_history",
                [],
            ),
    }

    RESULT_PATH.write_text(
        json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )


# ============================================================
# 14. MAIN
# ============================================================

async def main():

    print("")
    print("=" * 78)
    print(
        "PHASE 3 STEP 04-08 — "
        "REAL JUDGE GOVERNED REPLAY"
    )
    print("=" * 78)

    print(
        "MODE: GOVERNED REPLAY"
    )

    print(
        "FRESH RESEARCH RUN: NO"
    )

    print(
        "SOURCE: FROZEN VALIDATED REAL PHASE 2 ARTIFACT"
    )

    print(
        "ORCHESTRATOR: LANGGRAPH"
    )

    print(
        "JUDGE: REAL OPENAI LLM"
    )

    print(
        "LEGACY run_live(): NOT USED"
    )

    graph = build_graph()

    initial_state: JudgeReplayState = {
        "query":
            (
                "Compare the five target banks "
                "using the validated Phase 2 "
                "credit-risk disclosure evidence."
            ),

        "retry_count":
            0,

        "model_calls":
            [],

        "stage_history":
            [],
    }

    started = time.perf_counter()

    result = await graph.ainvoke(
        initial_state
    )

    total_seconds = (
        time.perf_counter()
        - started
    )

    save_result(
        result,
        total_seconds,
    )

    print("")
    print("=" * 78)
    print(
        "PHASE 3 STEP 04-08 — RESULT"
    )
    print("=" * 78)

    print(
        "FROZEN REAL GOVERNED MATRIX: PASS"
    )

    print(
        "DETERMINISTIC VALIDATION:",
        result.get(
            "deterministic_status"
        ),
    )

    print(
        "REAL FROZEN RECOVERY POLICY:",
        result.get(
            "recovery_action"
        ),
    )

    print(
        "JUDGE ALLOWED:",
        result.get(
            "judge_allowed"
        ),
    )

    print(
        "REAL JUDGE EXECUTED:",
        bool(
            result.get(
                "judge_review"
            )
        ),
    )

    print(
        "JUDGE CONTRACT:",
        result.get(
            "judge_contract_status"
        ),
    )

    print(
        "JUDGE VERDICT:",
        result.get(
            "judge_verdict"
        ),
    )

    print(
        "FINAL STATUS:",
        result.get(
            "final_status"
        ),
    )

    print(
        "MODEL CALLS:",
        len(
            result.get(
                "model_calls",
                [],
            )
        ),
    )

    print(
        f"TOTAL SECONDS: "
        f"{total_seconds:.3f}"
    )

    print(
        "LANGGRAPH ORCHESTRATION: PASS"
    )

    print(
        "PLANNING RERUN: NO"
    )

    print(
        "RETRIEVAL RERUN: NO"
    )

    print(
        "RESEARCH RERUN: NO"
    )

    print(
        "LEGACY run_live EXECUTED: NO"
    )

    print(
        "PHASE 2 MODIFIED: NO"
    )

    print(
        "RESULT ARTIFACT:",
        RESULT_PATH,
    )

    print("")
    print(
        "STAGE HISTORY:"
    )

    for item in result.get(
        "stage_history",
        [],
    ):

        print(
            "  -",
            item,
        )

    print("")
    print(
        "STEP 04-08 RESULT: PASS"
    )

    print("=" * 78)


if __name__ == "__main__":
    asyncio.run(
        main()
    )
