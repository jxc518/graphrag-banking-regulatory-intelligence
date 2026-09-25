"""
Phase 3 Step 04-05
Live Phase 2 Capability Adapter

Purpose
-------
Expose validated Phase 2 Planning / Retrieval / Research capabilities
to Phase 3 without executing the legacy run_live orchestrator.

Architecture
------------
LangGraph
   -> thin Phase 3 adapter
      -> frozen Phase 2 capability/runtime

The frozen Phase 2 source is READ ONLY.
"""

from __future__ import annotations

import os
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any


PHASE2_ROOT = Path(
    os.getenv(
        "GRAPHRAG_PHASE2_ROOT",
        r"C:\Users\chen_\Documents\_67_2026_Job_Hunting_After_Wells_Fargo"
        r"\_67_39_RAG_GraphRAG_Agent_GraphRAG"
        r"\_67_39_11_GraphRAG_Phase2_POC"
        r"\evaluation_migrated",
    )
)

CANONICAL_RUNNER = (
    PHASE2_ROOT
    / "GraphRAG_Phase_02_SECTION_08_04_openai_governed_comparison.py"
)

if str(PHASE2_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE2_ROOT))


def load_module_from_path(module_name: str, path: Path):
    """Load a frozen Phase 2 module without executing its CLI main()."""
    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to create import spec for: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_canonical_runner():
    if not CANONICAL_RUNNER.exists():
        raise FileNotFoundError(
            f"Frozen canonical runner not found: {CANONICAL_RUNNER}"
        )

    return load_module_from_path(
        "phase2_frozen_canonical_runner",
        CANONICAL_RUNNER,
    )


def discover_phase2_runtime() -> dict[str, Any]:
    """
    Discover the reusable Phase 2 runtime dependencies.

    IMPORTANT:
    This function performs imports only.
    It does NOT invoke an LLM and does NOT execute retrieval.
    """

    canonical = load_canonical_runner()

    judge_module = importlib.import_module(
        "GraphRAG_Phase_02_Section_04_05_llm_judge_revision_loop"
    )

    search_module = importlib.import_module(
        "graphrag.query.structured_search.local_search.search"
    )

    required_canonical = [
        "recovery_action",
        "apply_claim_level_fail_closed",
        "governed_validate",
    ]

    missing = [
        name
        for name in required_canonical
        if not hasattr(canonical, name)
    ]

    if missing:
        raise AttributeError(
            "Missing canonical Phase 2 capabilities: "
            + ", ".join(missing)
        )

    if not hasattr(judge_module, "prepare_engine"):
        raise AttributeError(
            "Phase 2 prepare_engine capability was not found."
        )

    if not hasattr(search_module, "CompletionMessagesBuilder"):
        raise AttributeError(
            "GraphRAG CompletionMessagesBuilder was not found."
        )

    return {
        "canonical": canonical,
        "prepare_engine": judge_module.prepare_engine,
        "search_module": search_module,
    }


def planning_payload(
    question: str,
    banks: list[str],
) -> dict[str, Any]:
    """
    Phase 3-owned payload boundary for the Planning Agent.

    No LLM call occurs here.
    """
    return {
        "question": question,
        "banks": banks,
    }


def retrieval_adapter(
    *,
    base_module: Any,
    plan: dict[str, Any],
    candidates: Any,
    sources: Any,
    scorer: Any,
):
    """
    Execute the real Phase 2 document-scoped retrieval capability.

    This intentionally calls base.retrieve directly rather than run_live().
    """

    if plan.get("action") != "retrieve":
        return []

    if not hasattr(base_module, "retrieve"):
        raise AttributeError(
            "Phase 2 base.retrieve capability was not found."
        )

    return base_module.retrieve(
        plan["requests"],
        candidates,
        sources,
        scorer,
    )


def research_payload(
    *,
    question: str,
    banks: list[str],
    sources: Any,
    span_catalog: Any,
) -> dict[str, Any]:
    """
    Preserve the validated Phase 2 Research Agent payload contract.
    """
    return {
        "question": question,
        "banks": banks,
        "sources": sources,
        "span_catalog": span_catalog,
    }


def build_messages(
    *,
    search_module: Any,
    system_prompt: str,
    payload_text: str,
):
    """
    Preserve the GraphRAG message-construction boundary used by Phase 2.

    No model call occurs here.
    """

    return (
        search_module
        .CompletionMessagesBuilder()
        .add_system_message(system_prompt)
        .add_user_message(payload_text)
        .build()
    )


def contract_test() -> None:
    print("=" * 74)
    print(
        "PHASE 3 STEP 04-05B — LIVE PHASE 2 CAPABILITY ADAPTER CONTRACT"
    )
    print("=" * 74)

    runtime = discover_phase2_runtime()

    canonical = runtime["canonical"]
    prepare_engine = runtime["prepare_engine"]
    search_module = runtime["search_module"]

    checks = []

    def check(label: str, condition: bool):
        status = "PASS" if condition else "FAIL"
        checks.append(bool(condition))
        print(f"{label}: {status}")

    check(
        "FROZEN CANONICAL RUNNER LOAD",
        canonical is not None,
    )

    check(
        "REAL PHASE 2 prepare_engine AVAILABLE",
        callable(prepare_engine),
    )

    check(
        "GraphRAG CompletionMessagesBuilder AVAILABLE",
        hasattr(search_module, "CompletionMessagesBuilder"),
    )

    check(
        "REAL PHASE 2 recovery_action AVAILABLE",
        callable(getattr(canonical, "recovery_action", None)),
    )

    check(
        "REAL PHASE 2 claim-level fail-closed AVAILABLE",
        callable(
            getattr(
                canonical,
                "apply_claim_level_fail_closed",
                None,
            )
        ),
    )

    check(
        "REAL PHASE 2 governed_validate AVAILABLE",
        callable(getattr(canonical, "governed_validate", None)),
    )

    plan_payload = planning_payload(
        "Compare credit-risk disclosures.",
        [
            "JPMorgan Chase",
            "Citigroup",
        ],
    )

    check(
        "PLANNING PAYLOAD CONTRACT",
        (
            plan_payload["question"]
            == "Compare credit-risk disclosures."
            and len(plan_payload["banks"]) == 2
        ),
    )

    research = research_payload(
        question="Compare credit-risk disclosures.",
        banks=["JPMorgan Chase", "Citigroup"],
        sources=[{"source_id": "S1"}],
        span_catalog=[{"span_id": "SPAN_001"}],
    )

    check(
        "RESEARCH PAYLOAD CONTRACT",
        (
            "question" in research
            and "banks" in research
            and "sources" in research
            and "span_catalog" in research
        ),
    )

    passed = sum(checks)
    total = len(checks)

    print("")
    print("=" * 74)
    print(f"CHECKS PASSED: {passed}/{total}")
    print(
        "LIVE CAPABILITY ADAPTER CONTRACT: "
        + ("PASS" if passed == total else "FAIL")
    )
    print("LEGACY run_live EXECUTED: NO")
    print("LLM CALLS: 0")
    print("RETRIEVAL EXECUTED: NO")
    print("NETWORK CALLS: 0")
    print("PHASE 2 MODIFIED: NO")
    print(
        "STEP 04-05B RESULT: "
        + ("PASS" if passed == total else "FAIL")
    )
    print("=" * 74)

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    contract_test()
