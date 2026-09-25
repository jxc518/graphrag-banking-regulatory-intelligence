from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import TypedDict

from langgraph.graph import START, END, StateGraph


# ============================================================
# PATHS
# ============================================================

PHASE3_ROOT = Path(__file__).resolve().parents[1]

PHASE2_ROOT = Path(
    r"C:\Users\chen_\Documents"
    r"\_67_2026_Job_Hunting_After_Wells_Fargo"
    r"\_67_39_RAG_GraphRAG_Agent_GraphRAG"
    r"\_67_39_11_GraphRAG_Phase2_POC"
    r"\evaluation_migrated"
)

sys.path.insert(0, str(PHASE2_ROOT))

import GraphRAG_Phase_02_Section_01_00_runtime_paths as runtime_paths

FROZEN_INDEX = Path(runtime_paths.frozen_index())
GRAPHRAG_ROOT = FROZEN_INDEX.parent

RESULTS_DIR = PHASE3_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_PATH = (
    RESULTS_DIR
    / "GraphRAG_Phase3_Step05_TRACE_EVIDENCE_09_inprocess_trace_summary.json"
)

INSTRUMENTATION_PATH = (
    PHASE3_ROOT
    / "app"
    / "GraphRAG_Phase3_Step05_TRACE_EVIDENCE_07_graphrag_instrumentation.py"
)


# ============================================================
# LOAD PHASE 3 INSTRUMENTATION
# ============================================================

def load_instrumentation():
    spec = importlib.util.spec_from_file_location(
        "phase3_graphrag_instrumentation",
        INSTRUMENTATION_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Cannot load instrumentation: {INSTRUMENTATION_PATH}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


instrumentation = load_instrumentation()
INSTRUMENTATION_STATUS = instrumentation.install_graphrag_tracing()


# ============================================================
# GRAPHRAG PYTHON ENTRYPOINTS
# ============================================================

from graphrag.cli.query import run_local_search, run_global_search


# ============================================================
# AWS / LANGSMITH DEMO QUERY SET
# ============================================================

TRACE_CASES = {
    "1": {
        "trace_id": "TRACE-01",
        "trace_name": "P3_TRACE_01_LOCAL_WELLS_FARGO_NESTED",
        "method": "local",
        "query": (
            "What were Wells Fargo's 2026 Q2 net charge-offs, "
            "and what evidence supports the reported amount?"
        ),
        "output_file": (
            RESULTS_DIR
            / "GraphRAG_Phase3_Step05_TRACE_EVIDENCE_10_local_wells_fargo_nested.txt"
        ),
    },

    "2": {
        "trace_id": "TRACE-02",
        "trace_name": "P3_TRACE_02_LOCAL_WF_JPM_COMPARISON_NESTED",
        "method": "local",
        "query": (
            "Compare Wells Fargo and JPMorgan Chase on 2026 Q2 "
            "net charge-offs. What are the reported amounts, "
            "and what evidence supports each value?"
        ),
        "output_file": (
            RESULTS_DIR
            / "GraphRAG_Phase3_Step05_TRACE_EVIDENCE_11_local_wf_jpm_nested.txt"
        ),
    },

    "3": {
        "trace_id": "TRACE-03",
        "trace_name": "P3_TRACE_03_GLOBAL_FIVE_BANK_NESTED",
        "method": "global",
        "query": (
            "Compare the five target banks' 2026 Q2 net charge-offs. "
            "Identify the major differences and support the comparison "
            "with evidence from the indexed disclosures."
        ),
        "output_file": (
            RESULTS_DIR
            / "GraphRAG_Phase3_Step05_TRACE_EVIDENCE_12_global_five_bank_nested.txt"
        ),
    },
}


# ============================================================
# LANGGRAPH SHARED STATE
# ============================================================

class TraceState(TypedDict, total=False):
    trace_id: str
    trace_name: str
    method: str
    query: str

    graphrag_elapsed_seconds: float
    return_code: int
    status: str

    answer_preview: str
    error_preview: str
    stage_history: list[str]


# ============================================================
# NODE 1 — PREPARE
# ============================================================

def prepare_query_node(state: TraceState) -> TraceState:

    history = list(state.get("stage_history", []))
    history.append("01 Prepare Query")

    return {
        **state,
        "stage_history": history,
    }


# ============================================================
# IN-PROCESS GRAPHRAG EXECUTION
# ============================================================

def execute_graphrag(case: dict) -> str:

    method = case["method"]
    query = case["query"]

    common = {
        "root_dir": GRAPHRAG_ROOT,
        "data_dir": FROZEN_INDEX,
        "query": query,
        "response_type": "Multiple Paragraphs",
        "verbose": False,
        "streaming": False,
    }

    if method == "local":
        result = run_local_search(
            **common,
            community_level=2,
        )

    elif method == "global":
        result = run_global_search(
            **common,
            community_level=2,
            dynamic_community_selection=False,
        )

    else:
        raise ValueError(f"Unsupported method: {method}")

    if result is None:
        return ""

    return str(result)


# ============================================================
# NODE 2 — REAL IN-PROCESS GRAPHRAG SEARCH
# ============================================================

def graphrag_search_node(state: TraceState) -> TraceState:

    history = list(state.get("stage_history", []))

    history.append(
        "02 GraphRAG "
        + state["method"].upper()
        + " Search REAL IN-PROCESS"
    )

    case = next(
        item
        for item in TRACE_CASES.values()
        if item["trace_id"] == state["trace_id"]
    )

    print()
    print(">>> REAL IN-PROCESS GRAPHRAG SEARCH STARTED")
    print("METHOD:", state["method"].upper())
    print("QUERY :", state["query"])
    print()

    started = time.perf_counter()

    try:
        answer = execute_graphrag(case)
        elapsed = time.perf_counter() - started

        status = "PASS"
        return_code = 0
        error_preview = ""

    except Exception as exc:
        elapsed = time.perf_counter() - started

        status = "FAIL"
        return_code = 1
        answer = ""
        error_preview = (
            f"{type(exc).__name__}: {exc}"
        )

    full_output = (
        "TRACE NAME: "
        + state["trace_name"]
        + "\n"
        + "METHOD: "
        + state["method"].upper()
        + "\n"
        + "QUERY: "
        + state["query"]
        + "\n"
        + "EXECUTION_MODE: IN_PROCESS_PYTHON_API\n"
        + "INSTRUMENTATION: TRUE\n"
        + "ELAPSED_SECONDS: "
        + str(round(elapsed, 3))
        + "\n"
        + "RETURN_CODE: "
        + str(return_code)
        + "\n\n"
        + "================ ANSWER ================\n"
        + answer
        + "\n\n"
        + "================ ERROR =================\n"
        + error_preview
    )

    case["output_file"].write_text(
        full_output,
        encoding="utf-8",
    )

    print()
    print(">>> REAL IN-PROCESS GRAPHRAG SEARCH FINISHED")
    print("STATUS :", status)
    print("SECONDS:", round(elapsed, 3))

    if error_preview:
        print("ERROR  :", error_preview)

    print()

    return {
        **state,
        "graphrag_elapsed_seconds": round(elapsed, 3),
        "return_code": return_code,
        "status": status,
        "answer_preview": answer.strip()[:3000],
        "error_preview": error_preview[:1500],
        "stage_history": history,
    }


# ============================================================
# NODE 3 — FINALIZE
# ============================================================

def finalize_node(state: TraceState) -> TraceState:

    history = list(state.get("stage_history", []))

    history.append(
        "03 Finalize Trace " + state.get("status", "UNKNOWN")
    )

    return {
        **state,
        "stage_history": history,
    }


# ============================================================
# GRAPH
# ============================================================

def build_graph():

    builder = StateGraph(TraceState)

    builder.add_node(
        "01_prepare_query",
        prepare_query_node,
    )

    builder.add_node(
        "02_graphrag_search",
        graphrag_search_node,
    )

    builder.add_node(
        "03_finalize",
        finalize_node,
    )

    builder.add_edge(
        START,
        "01_prepare_query",
    )

    builder.add_edge(
        "01_prepare_query",
        "02_graphrag_search",
    )

    builder.add_edge(
        "02_graphrag_search",
        "03_finalize",
    )

    builder.add_edge(
        "03_finalize",
        END,
    )

    return builder.compile()


# ============================================================
# PREFLIGHT
# ============================================================

def preflight():

    checks = {
        "GraphRAG root": GRAPHRAG_ROOT.exists(),
        "Frozen index": FROZEN_INDEX.exists(),
        "settings.yaml": (GRAPHRAG_ROOT / "settings.yaml").exists(),
        "Instrumentation file": INSTRUMENTATION_PATH.exists(),
        "Instrumentation installed": bool(
            INSTRUMENTATION_STATUS.get("installed")
        ),
        "LangSmith tracing": (
            os.getenv("LANGSMITH_TRACING", "").lower()
            == "true"
        ),
        "LangSmith API key": bool(
            os.getenv("LANGSMITH_API_KEY")
        ),
    }

    print()
    print("=" * 88)
    print("PHASE 3 STEP05 — IN-PROCESS TRACE PREFLIGHT")
    print("=" * 88)

    print("GRAPHRAG ROOT :", GRAPHRAG_ROOT)
    print("FROZEN INDEX  :", FROZEN_INDEX)
    print(
        "LANGSMITH PROJECT:",
        os.getenv("LANGSMITH_PROJECT"),
    )

    print()

    for name, passed in checks.items():
        print(
            f"{name:<28}",
            "PASS" if passed else "FAIL",
        )

    if not all(checks.values()):
        print()
        print("PREFLIGHT: FAIL")
        print("No GraphRAG search executed.")
        sys.exit(1)

    print()
    print("PREFLIGHT: PASS")


# ============================================================
# RUN TRACE
# ============================================================

def run_case(graph, case: dict) -> dict:

    state: TraceState = {
        "trace_id": case["trace_id"],
        "trace_name": case["trace_name"],
        "method": case["method"],
        "query": case["query"],
        "stage_history": [],
    }

    print()
    print("=" * 88)
    print(case["trace_name"])
    print("=" * 88)

    overall_start = time.perf_counter()

    result = graph.invoke(
        state,
        config={
            "run_name": case["trace_name"],
            "tags": [
                "Phase3",
                "LangGraph",
                "GraphRAG",
                case["method"].upper(),
                "AWS_Demo_Query",
                "Nested_Observability",
            ],
            "metadata": {
                "phase": "Phase 3",
                "step": "Step05 TRACE_EVIDENCE",
                "demo_query": True,
                "graphrag_method": case["method"],
                "workload": "REAL",
                "execution_mode": "IN_PROCESS_PYTHON_API",
                "instrumentation": True,
                "phase2_modified": False,
            },
        },
    )

    total_elapsed = time.perf_counter() - overall_start

    summary = {
        "trace_id": case["trace_id"],
        "trace_name": case["trace_name"],
        "method": case["method"],
        "query": case["query"],
        "status": result.get("status"),
        "return_code": result.get("return_code"),
        "graphrag_elapsed_seconds": result.get(
            "graphrag_elapsed_seconds"
        ),
        "langgraph_elapsed_seconds": round(
            total_elapsed,
            3,
        ),
        "stage_history": result.get(
            "stage_history",
            [],
        ),
        "output_file": str(case["output_file"]),
        "execution_mode": "IN_PROCESS_PYTHON_API",
        "instrumentation": True,
        "phase2_modified": False,
    }

    print()
    print("TRACE STATUS      :", summary["status"])
    print(
        "GRAPHRAG SECONDS :",
        summary["graphrag_elapsed_seconds"],
    )
    print(
        "LANGGRAPH SECONDS:",
        summary["langgraph_elapsed_seconds"],
    )

    print()
    print("ANSWER PREVIEW")
    print("-" * 88)
    print(result.get("answer_preview", ""))

    if result.get("error_preview"):
        print()
        print("ERROR PREVIEW")
        print("-" * 88)
        print(result["error_preview"])

    return summary


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--trace",
        choices=["1", "2", "3", "all"],
        required=True,
    )

    args = parser.parse_args()

    preflight()

    graph = build_graph()

    if args.trace == "all":
        selected = list(TRACE_CASES.values())
    else:
        selected = [TRACE_CASES[args.trace]]

    summaries = []

    for case in selected:
        summaries.append(
            run_case(graph, case)
        )

    payload = {
        "phase": "Phase 3",
        "step": "Step05 TRACE_EVIDENCE",
        "execution_mode": "IN_PROCESS_PYTHON_API",
        "instrumentation": True,
        "langsmith_project": os.getenv(
            "LANGSMITH_PROJECT"
        ),
        "trace_count": len(summaries),
        "passed_trace_count": sum(
            1
            for x in summaries
            if x["status"] == "PASS"
        ),
        "phase2_modified": False,
        "traces": summaries,
    }

    SUMMARY_PATH.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 88)
    print("IN-PROCESS TRACE TEST COMPLETE")
    print("=" * 88)
    print(
        "PASSED:",
        payload["passed_trace_count"],
        "/",
        payload["trace_count"],
    )
    print("INSTRUMENTATION: TRUE")
    print("PHASE 2 MODIFIED: NO")
    print("SUMMARY:", SUMMARY_PATH)


if __name__ == "__main__":
    main()


