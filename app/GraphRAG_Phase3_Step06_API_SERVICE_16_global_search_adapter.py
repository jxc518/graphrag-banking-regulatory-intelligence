"""
GraphRAG Phase 3
Step 06 - API Service
Artifact 16 - Global Search Adapter

Purpose:
Provide a small production-safe adapter around Microsoft GraphRAG
Global Search without changing the existing governed Local Search runtime.

V1 status:
Global Search is experimental and is not yet part of the governed
Local Search LangGraph decision pipeline.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from langsmith import traceable

from graphrag.cli.query import run_global_search


# ============================================================
# PORTABLE RUNTIME PATHS
# ============================================================

# AWS / Docker:
#   GRAPHRAG_PHASE2_RUNTIME_CONFIG=/opt/graphrag/runtime
#   GRAPHRAG_PHASE3_INDEX_OUTPUT=/opt/graphrag/index
#
# Local Windows:
#   Environment variables may be supplied explicitly.
#   If they are absent, resolve from the existing Phase 2 runtime_paths
#   module used by the validated Phase 3 trace runner.


def _resolve_paths() -> tuple[Path, Path]:

    runtime_env = os.getenv(
        "GRAPHRAG_PHASE2_RUNTIME_CONFIG"
    )

    index_env = os.getenv(
        "GRAPHRAG_PHASE3_INDEX_OUTPUT"
    )

    if runtime_env and index_env:
        graphrag_root = Path(runtime_env)
        frozen_index = Path(index_env)

        # In AWS/Linux, the Docker paths must be authoritative.
        # On local Windows, Linux-style environment values may remain
        # in the shell from deployment work. If those paths do not
        # exist locally, fall through to the validated Phase 2
        # runtime_paths resolver below.
        if os.name != "nt":
            return graphrag_root, frozen_index

        if graphrag_root.exists() and frozen_index.exists():
            return graphrag_root, frozen_index

    # --------------------------------------------------------
    # LOCAL WINDOWS FALLBACK
    # Use the Phase 3 deployment-packaged GraphRAG runtime/index
    # so local smoke testing matches the AWS deployment payload.
    # --------------------------------------------------------

    phase3_root = Path(__file__).resolve().parents[1]

    build_context = (
        phase3_root
        / "deployment"
        / "GraphRAG_Phase3_Step07_CONTAINER_DEPLOYMENT_10_build_context"
    )

    frozen_index = (
        build_context
        / "graphrag_index"
    )

    graphrag_root = (
        build_context
        / "graphrag_runtime"
    )

    return graphrag_root, frozen_index


# ============================================================
# PATH VALIDATION
# ============================================================

def runtime_info() -> dict[str, Any]:

    graphrag_root, frozen_index = _resolve_paths()

    return {
        "search_method": "global",
        "status": "experimental",
        "graphrag_root": str(graphrag_root),
        "frozen_index": str(frozen_index),
        "graphrag_root_exists": graphrag_root.exists(),
        "frozen_index_exists": frozen_index.exists(),
    }


# ============================================================
# SYNCHRONOUS GLOBAL SEARCH
# ============================================================

def run_global_query_sync(
    query: str,
) -> str:

    query = query.strip()

    if len(query) < 3:
        raise ValueError(
            "Global Search query must contain at least 3 characters."
        )

    graphrag_root, frozen_index = _resolve_paths()

    if not graphrag_root.exists():
        raise RuntimeError(
            f"GraphRAG root does not exist: {graphrag_root}"
        )

    if not frozen_index.exists():
        raise RuntimeError(
            f"GraphRAG index does not exist: {frozen_index}"
        )

    result = run_global_search(
        root_dir=graphrag_root,
        data_dir=frozen_index,
        query=query,
        response_type="Multiple Paragraphs",
        verbose=False,
        streaming=False,
        community_level=2,
        dynamic_community_selection=False,
    )

    if result is None:
        return ""

    # Microsoft GraphRAG Global Search may return:
    #     (answer, context_data)
    #
    # The public API should expose only the synthesized answer,
    # not the internal report/context DataFrames.
    if isinstance(result, tuple):
        if not result:
            return ""
        return str(result[0])

    return str(result)


# ============================================================
# ASYNC API-SAFE WRAPPER
# ============================================================

@traceable(
    name="Global-Search-Experimental",
    run_type="chain",
)
async def run_global_query(
    query: str,
) -> str:
    """
    Run blocking GraphRAG Global Search outside the FastAPI event loop.

    This wrapper does not itself make the result a governed answer.
    It exposes the existing GraphRAG Global Search capability for
    experimental V1 serving and later governance integration.
    """

    return await asyncio.to_thread(
        run_global_query_sync,
        query,
    )


if __name__ == "__main__":
    print("Global Search Adapter import smoke test")
    print(runtime_info())
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")
