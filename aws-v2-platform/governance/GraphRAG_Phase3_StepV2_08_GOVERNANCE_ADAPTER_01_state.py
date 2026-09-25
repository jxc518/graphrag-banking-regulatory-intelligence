from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


def governed_state_to_metric_fields(
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    V2-only additive mapping.

    Authoritative mappings currently supported:
      - judge execution
      - judge rejection/revision
      - escalation

    Evidence/provenance/span fields intentionally remain
    unavailable until their authoritative contracts are
    separately proven.
    """

    source = deepcopy(state)

    verdict_raw = source.get(
        "judge_verdict",
        "NOT_EVALUATED",
    )

    verdict = str(
        verdict_raw or "NOT_EVALUATED"
    ).upper()

    final_status_raw = source.get(
        "final_status"
    )

    final_status = (
        str(final_status_raw).upper()
        if final_status_raw is not None
        else None
    )

    judge_executed = (
        verdict != "NOT_EVALUATED"
    )

    judge_rejected = (
        judge_executed
        and verdict == "REVISE"
    )

    escalated = (
        final_status == "ESCALATED"
    )

    return {
        "judge_executed":
            judge_executed,

        "judge_rejected":
            judge_rejected,

        "escalated":
            escalated,

        # Preserve diagnostic source fields.
        "judge_allowed":
            source.get("judge_allowed"),

        "judge_verdict":
            verdict,

        "final_status":
            final_status,

        # Not yet mapped.
        "evidence_required":
            None,

        "missing_evidence":
            None,

        "provenance_evaluated":
            None,

        "provenance_failed":
            None,

        "span_evaluated":
            None,

        "unknown_span":
            None,
    }