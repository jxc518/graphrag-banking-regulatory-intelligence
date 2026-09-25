"""
GraphRAG Phase 3
Step 06 — API Service
Artifact 02 — Runtime Facade

Purpose
-------
Expose the CLOSED_PASS Phase 3 governed LangGraph runtime through a
small reusable Python interface suitable for FastAPI, tests, Docker,
and later AWS deployment.

Important
---------
This module does NOT reimplement governance policy.
It does NOT execute legacy Phase 2 run_live().
It delegates orchestration to the existing Phase 3 LangGraph runtime.
"""

from __future__ import annotations

import importlib.util
import sys
import time
import uuid
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent

RUNTIME_PATH = (
    HERE
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_08_governed_live_graph.py"
)


def load_runtime_module():
    """
    Load the CLOSED_PASS governed LangGraph runtime without calling
    its script-level main().
    """

    if not RUNTIME_PATH.exists():
        raise FileNotFoundError(
            f"Governed runtime not found: {RUNTIME_PATH}"
        )

    spec = importlib.util.spec_from_file_location(
        "phase3_governed_live_runtime",
        RUNTIME_PATH,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Unable to load runtime module: {RUNTIME_PATH}"
        )

    app_dir = str(HERE)

    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    module = importlib.util.module_from_spec(spec)

    # Register dynamic module before execution so sibling imports and
    # runtime type introspection see a normal Python module context.
    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    if not hasattr(module, "build_governed_graph"):
        raise AttributeError(
            "Runtime module does not expose build_governed_graph()."
        )

    return module


def build_initial_state(
    query: str,
    provider: str = "openai", ) -> dict[str, Any]:
    """
    Build the request-local initial state for the governed runtime.
    """

    cleaned_query = query.strip()
    cleaned_provider = provider.strip().lower()

    if not cleaned_query:
        raise ValueError("query must not be empty")

    if cleaned_provider not in {"openai", "deepseek"}:
        raise ValueError(
            "provider must be 'openai' or 'deepseek'"
        )

    return {
        "query": cleaned_query,
        "provider": cleaned_provider,
        "model_calls": [],
        "stage_history": [],
        "retry_count": 0,
        "fail_closed_applied": False,
        "judge_allowed": False,
    }


def _json_safe(value: Any) -> Any:
    """
    Convert common runtime objects into API-friendly values.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(k): _json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            _json_safe(v)
            for v in value
        ]

    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump())
        except Exception:
            pass

    return str(value)


def normalize_result(
    result: dict[str, Any],
    *,
    run_id: str,
    latency_seconds: float,
) -> dict[str, Any]:
    """
    Convert LangGraph state into a stable service-facing response.

    The full runtime state is preserved under runtime_state during
    Phase 3 integration so we can validate the API without losing
    governance evidence.
    """

    return {
        "run_id": run_id,
        "query": result.get("query"),
        "final_status": result.get("final_status"),
        "guard_status": result.get("guard_status"),
        "failure_type": result.get("failure_type"),
        "recovery_action": result.get("recovery_action"),
        "retry_count": result.get("retry_count", 0),
        "fail_closed_applied": result.get(
            "fail_closed_applied",
            False,
        ),
        "judge_allowed": result.get(
            "judge_allowed",
            False,
        ),
        "judge_verdict": result.get("judge_verdict"),
    
        "answer": _json_safe(
            result.get("governed_matrix")
        ),
        "governed_matrix": _json_safe(
            result.get("governed_matrix")
        ),
        "governed_rows": _json_safe(
            result.get("governed_rows")
        ),
        "judge_review": _json_safe(
            result.get("judge_review")
        ),
        "judge_contract_status": result.get(
            "judge_contract_status"
        ),
        "field_evidence_mismatches": _json_safe(
            result.get(
                "field_evidence_mismatches",
                [],
            )
        ),
        "evidence_insufficiency": _json_safe(
            result.get(
                "evidence_insufficiency",
                [],
            )
        ),    
    
        "stage_history": _json_safe(
            result.get("stage_history", [])
        ),
        "model_calls": _json_safe(
            result.get("model_calls", [])
        ),
        "latency_seconds": round(
            latency_seconds,
            3,
        ),
        "runtime_state": _json_safe(result),
    }
    
async def run_governed_query(
    query: str,
    provider: str = "openai",
) -> dict[str, Any]:
    
    """
    Execute one query through the CLOSED_PASS governed LangGraph runtime.

    Governance outcomes such as ESCALATED or PENDING_REVIEW are returned
    normally. They are business/governance outcomes, not Python errors.
    """

    run_id = str(uuid.uuid4())

    runtime = load_runtime_module()

    # ------------------------------------------------------------
    # STEP06 SERVING COMPATIBILITY
    # Normalize the observed single-bank planner vocabulary:
    #
    #     use_existing + requests=[]  ->  answer
    #
    # This adapter is installed at the serving boundary before
    # LangGraph compilation. Step04 and frozen Phase2 are unchanged.
    # ------------------------------------------------------------
    from GraphRAG_Phase3_Step06_API_SERVICE_05_single_bank_adapter import (
        install as install_single_bank_adapter,
    )

    runtime = install_single_bank_adapter(
        runtime
    )

    # ------------------------------------------------------------
    # STEP06 REQUEST-LOCAL QUERY SCOPE
    # Restrict banks/evidence for this request before LangGraph compile.
    # Step04 and frozen Phase2 remain unchanged.
    # ------------------------------------------------------------
    from GraphRAG_Phase3_Step06_API_SERVICE_06_query_scope import (
        install as install_query_scope,
    )

    runtime = install_query_scope(
        runtime
    )

    # ------------------------------------------------------------
    # STEP06 REQUEST-SCOPED MATRIX CONTRACT
    # Generalize the frozen five-bank matrix cardinality contract
    # to the request-local bank scope while preserving all
    # evidence, provenance, quote, period, unit, and scope checks.
    # Installed before LangGraph compilation.
    # ------------------------------------------------------------
    from GraphRAG_Phase3_Step06_API_SERVICE_15_scope_contract_adapter import (
        install as install_scope_contract,
    )

    runtime = install_scope_contract(
        runtime
    )

    graph = runtime.build_governed_graph()

    # initial_state = build_initial_state(query)
    
    initial_state = build_initial_state(    query,    provider, )

    started = time.perf_counter()

    result = await graph.ainvoke(
        initial_state
    )

    latency_seconds = (
        time.perf_counter()
        - started
    )

    return normalize_result(
        result,
        run_id=run_id,
        latency_seconds=latency_seconds,
    )


def runtime_info() -> dict[str, Any]:
    """
    Lightweight metadata for health/readiness checks.

    This function does not invoke the graph.
    """

    return {
        "service": "Governed Multi-Agent GraphRAG",
        "phase": "Phase 3",
        "orchestrator": "LangGraph",
        "migration_status": "CLOSED_PASS",
        "runtime_module": RUNTIME_PATH.name,
        "legacy_run_live_used": False,
    }


if __name__ == "__main__":
    print("Runtime Facade import smoke test")
    print(runtime_info())
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")

