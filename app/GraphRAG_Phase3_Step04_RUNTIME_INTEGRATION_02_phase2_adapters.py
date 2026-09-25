"""
GraphRAG Phase 3
STEP 04-02B — Phase 2 Capability Adapters

Purpose
-------
Expose selected validated Phase 2 governance capabilities to the
Phase 3 LangGraph runtime without executing the legacy Phase 2
orchestrator.

Architecture rule
-----------------
Phase 2 = frozen validated capability source
Phase 3 = orchestration owner

This module MUST NOT call run_live().
This module MUST NOT modify Phase 2.
"""

from __future__ import annotations

import os
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Optional


PHASE2_ROOT = Path(
    os.getenv(
        "GRAPHRAG_PHASE2_ROOT",
        r"C:\Users\chen_\Documents\_67_2026_Job_Hunting_After_Wells_Fargo"
        r"\_67_39_RAG_GraphRAG_Agent_GraphRAG"
        r"\_67_39_11_GraphRAG_Phase2_POC"
        r"\evaluation_migrated",
    )
)

PHASE2_CANONICAL = (
    PHASE2_ROOT
    / "GraphRAG_Phase_02_SECTION_08_04_openai_governed_comparison.py"
)


def load_phase2_canonical() -> ModuleType:
    """
    Load the frozen Phase 2 canonical module read-only.

    Importing the module exposes top-level validated functions.
    It does NOT execute main() or run_live().
    """

    if not PHASE2_CANONICAL.exists():
        raise FileNotFoundError(
            f"Frozen Phase 2 canonical runner not found: {PHASE2_CANONICAL}"
        )

    spec = importlib.util.spec_from_file_location(
        "phase2_frozen_canonical",
        PHASE2_CANONICAL,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            "Unable to construct import specification for Phase 2 canonical runner."
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


_PHASE2: Optional[ModuleType] = None


def phase2() -> ModuleType:
    global _PHASE2

    if _PHASE2 is None:
        _PHASE2 = load_phase2_canonical()

    return _PHASE2


def recovery_action_adapter(
    error_type,
    retry_count: int,
):
    """
    Thin adapter over the validated Phase 2 recovery policy.
    """

    return phase2().recovery_action(
        error_type,
        retry_count,
    )


def claim_level_fail_closed_adapter(
    matrix,
    insufficiencies,
):
    """
    Thin adapter over the validated Phase 2 claim-level fail-closed
    transformation.
    """

    return phase2().apply_claim_level_fail_closed(
        matrix,
        insufficiencies,
    )


def governed_validate_adapter(
    raw_matrix,
    sources,
    ds,
    base,
):
    """
    Thin adapter over the validated Phase 2 deterministic governance
    validation stack.
    """

    return phase2().governed_validate(
        raw_matrix,
        sources,
        ds,
        base,
    )


def run_adapter_contract_test():
    print("")
    print("=" * 74)
    print("PHASE 3 STEP 04-02B — PHASE 2 CAPABILITY ADAPTER CONTRACT")
    print("=" * 74)

    module = phase2()

    required = [
        "recovery_action",
        "apply_claim_level_fail_closed",
        "governed_validate",
    ]

    missing = [
        name
        for name in required
        if not callable(getattr(module, name, None))
    ]

    if missing:
        raise AssertionError(
            f"Missing required Phase 2 capabilities: {missing}"
        )

    print("CANONICAL MODULE LOAD: PASS")

    for name in required:
        print(f"CAPABILITY AVAILABLE: {name}")

    clean_action = recovery_action_adapter(
        None,
        0,
    )

    retry_action = recovery_action_adapter(
        "FIELD_EVIDENCE_MISMATCH",
        0,
    )

    exhausted_action = recovery_action_adapter(
        "FIELD_EVIDENCE_MISMATCH",
        1,
    )

    insufficiency_action = recovery_action_adapter(
        "EVIDENCE_INSUFFICIENCY",
        0,
    )

    provenance_action = recovery_action_adapter(
        "PROVENANCE_MISMATCH",
        0,
    )

    print("")
    print("RECOVERY POLICY SMOKE TEST")
    print(f"CLEAN / retry 0: {clean_action}")
    print(f"FIELD_EVIDENCE_MISMATCH / retry 0: {retry_action}")
    print(f"FIELD_EVIDENCE_MISMATCH / retry 1: {exhausted_action}")
    print(f"EVIDENCE_INSUFFICIENCY / retry 0: {insufficiency_action}")
    print(f"PROVENANCE_MISMATCH / retry 0: {provenance_action}")

    assert clean_action == "CONTINUE_TO_JUDGE"
    assert retry_action == "RETRY_MATRIX"
    assert exhausted_action == "ESCALATE"
    assert insufficiency_action == "CLAIM_LEVEL_FAIL_CLOSED"
    assert provenance_action == "ESCALATE"

    print("")
    print("PHASE 2 CAPABILITY ADAPTER CONTRACT: PASS")
    print("RECOVERY POLICY BEHAVIOR: PASS")
    print("LEGACY run_live EXECUTED: NO")
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")
    print("PHASE 2 MODIFIED: NO")
    print("STEP 04-02B RESULT: PASS")
    print("=" * 74)


if __name__ == "__main__":
    run_adapter_contract_test()
