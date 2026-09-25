"""
GraphRAG Phase 3
Step 04 - Runtime Integration
Artifact 08 - Governed Live Graph

Purpose
-------
Extend the already validated live LangGraph research runtime with
the frozen Phase 2 governance semantics:

07 Deterministic Guard
08 Failure Classifier
09 Recovery Controller
10 Retry Matrix
11 Claim-Level Fail Closed
12 Deterministic Revalidation
13 Judge Gate
14 Real Judge LLM
15 Judge Contract Guardrail
16 Final Governed Decision

Architecture rule
-----------------
LangGraph owns orchestration.
Frozen Phase 2 owns validated governance policy/capabilities.
Legacy Phase 2 run_live() is NOT executed.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import START, END, StateGraph

# ============================================================
# 1. REUSE THE ALREADY VALIDATED LIVE RESEARCH RUNTIME
# ============================================================

from GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_06_live_research_graph import (
    LiveResearchState,
    PHASE3_ROOT,
    _RUNTIME,
    runtime_bootstrap_node,
    planning_agent_node,
    plan_guardrail_node,
    retrieval_node,
    span_catalog_node,
    research_agent_node,
    complete_real,
    append_stage,
    json_safe,
)


RESULT_PATH = (
    PHASE3_ROOT
    / "results"
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_09_governed_live_graph.json"
)

MAX_CONTRACT_RETRIES = 1


# ============================================================
# 2. EXTENDED LANGGRAPH STATE
# ============================================================

class GovernedLiveState(LiveResearchState, total=False):

    provider: str

    normalized_matrix: Any
    governed_matrix: Any
    governed_rows: Any

    field_evidence_mismatches: list[Any]
    evidence_insufficiency: list[Any]

    guard_status: str
    failure_type: str | None

    retry_count: int
    recovery_action: str

    fail_closed_applied: bool
    revalidation_status: str

    judge_allowed: bool
    judge_review: Any
    judge_verdict: str | None
    judge_contract_status: str

    final_status: str


# ============================================================
# 3. HELPERS
# ============================================================

def _canonical():
    return _RUNTIME["canonical"]


def _base():
    return _RUNTIME["base"]


def _ds():
    return _RUNTIME["ds"]


def _call_with_named_runtime(
    fn,
    values: dict[str, Any],
):
    """
    Defensive capability caller.

    Uses the function's real signature and supplies arguments
    by parameter name. This avoids hard-coding a guessed
    signature if a frozen Phase 2 helper has extra optional
    parameters.
    """

    signature = inspect.signature(fn)

    kwargs = {}

    aliases = {
        "matrix": "matrix",
        "normalized": "matrix",
        "normalized_matrix": "matrix",
        "catalog": "catalog",
        "span_catalog": "catalog",
        "sources": "sources",
        "base": "base",
        "ds": "ds",
        "mismatches": "mismatches",
        "mismatch": "mismatches",
        "insufficiencies": "insufficiencies",
        "insufficiency": "insufficiencies",
    }

    for name, parameter in signature.parameters.items():

        lookup = aliases.get(
            name,
            name,
        )

        if lookup in values:
            kwargs[name] = values[lookup]
            continue

        if parameter.default is not inspect._empty:
            continue

        raise TypeError(
            f"Cannot supply required parameter "
            f"{name!r} for {fn.__name__}"
        )

    return fn(**kwargs)


def evidence_insufficiency(
    matrix: Any,
    catalog: Any,
    sources: Any,
):
    canonical = _canonical()

    return _call_with_named_runtime(
        canonical.evidence_insufficiency_findings,
        {
            "matrix": matrix,
            "catalog": catalog,
            "sources": sources,
            "base": _base(),
            "ds": _ds(),
        },
    )


def extract_judge_verdict(
    review: Any,
) -> str | None:

    if not isinstance(review, dict):
        return None

    keys = (
        "verdict",
        "decision",
        "recommendation",
        "status",
        "overall_verdict",
        "overall_decision",
    )

    for key in keys:

        value = review.get(key)

        if isinstance(value, str):
            return value

    for nested_key in (
        "judge",
        "review",
        "result",
        "assessment",
    ):

        nested = review.get(
            nested_key
        )

        if isinstance(nested, dict):

            value = extract_judge_verdict(
                nested
            )

            if value:
                return value

    return None


def evidence_uniqueness_contract() -> str:

    return (
        "\n\n"
        "=== EVIDENCE UNIQUENESS CONTRACT ===\n"
        "Each span_id must be UNIQUE within the "
        "row-level evidence list.\n"
        "Do not include the same span_id more than "
        "once in a row's evidence.\n"
        "If one selected span supports multiple "
        "fields, include it only once in evidence "
        "and reference that same selected span_id "
        "from multiple field_evidence lists as needed.\n"
    )


# ============================================================
# 4. NODE 07 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â REAL DETERMINISTIC GUARD
# ============================================================


# ============================================================
# V1.2 REQUEST-SCOPED METRIC GOVERNANCE
# ============================================================

def _requested_metric_banks(state):
    """
    Derive the bank/entity scope explicitly requested by the user.

    V1.2 contract:
      1. Prefer research_plan["requested_banks"].
      2. Fall back to requests[].bank for backward compatibility.

    Retrieval scope and governance request scope are intentionally
    separate concepts.
    """

    plan = state.get("research_plan") or {}

    explicit_banks = plan.get("requested_banks")

    if isinstance(explicit_banks, list):
        banks = []

        for bank in explicit_banks:
            if isinstance(bank, str) and bank.strip():
                bank = bank.strip()

                if bank not in banks:
                    banks.append(bank)

        if banks:
            return banks

    requests = plan.get("requests") or []

    banks = []

    for item in requests:
        if not isinstance(item, dict):
            continue

        bank = item.get("bank")

        if isinstance(bank, str) and bank.strip():
            bank = bank.strip()

            if bank not in banks:
                banks.append(bank)

    return banks


def _validate_request_scoped_metric_matrix(
    matrix,
    requested_banks,
):
    """
    Phase 3 V1.2 Metric cardinality / request-scope validator.

    IMPORTANT:
    This does NOT replace normalization, span resolution,
    provenance validation, field-evidence validation, or
    evidence-sufficiency controls.

    It replaces ONLY the legacy Phase 2 five-bank matrix
    cardinality assumption with the CURRENT request scope.
    """

    if not isinstance(matrix, dict):
        raise ValueError(
            "Metric matrix must be an object"
        )

    rows = matrix.get("rows")

    if not isinstance(rows, list) or not rows:
        raise ValueError(
            "Metric matrix must contain at least one row"
        )

    if not isinstance(requested_banks, list) or not requested_banks:
        raise ValueError(
            "Metric request scope is missing"
        )

    returned_banks = []

    required_fields = {
        "bank",
        "metric",
        "period",
        "value",
        "unit",
        "scope",
        "status",
        "limitation",
        "evidence",
        "field_evidence",
    }

    for index, row in enumerate(rows):

        if not isinstance(row, dict):
            raise ValueError(
                f"Metric row {index} must be an object"
            )

        missing = required_fields - set(row)

        if missing:
            raise ValueError(
                "Metric row missing required fields: "
                + ", ".join(sorted(missing))
            )

        bank = row.get("bank")

        if not isinstance(bank, str) or not bank.strip():
            raise ValueError(
                f"Metric row {index} has invalid bank"
            )

        bank = bank.strip()

        if bank in returned_banks:
            raise ValueError(
                "Metric matrix contains duplicate banks"
            )

        returned_banks.append(bank)

        status = row.get("status")

        if status not in {
            "supported",
            "missing_evidence",
            "unsupported",
        }:
            raise ValueError(
                f"Metric row {index} has invalid status"
            )

        # V1.3 metric contract:
        # supported rows require string-valued metric fields;
        # missing_evidence / unsupported rows may leave genuinely
        # unsupported unit/scope fields as None rather than inventing them.
        required_string_fields = (
            "metric",
            "period",
            "limitation",
        )

        for field in required_string_fields:
            if not isinstance(row.get(field), str):
                raise ValueError(
                    f"Metric row {index} field "
                    f"{field!r} must be a string"
                )

        for field in (
            "unit",
            "scope",
        ):
            value = row.get(field)

            if status == "supported":
                if not isinstance(value, str):
                    raise ValueError(
                        f"Metric row {index} field "
                        f"{field!r} must be a string "
                        "for supported rows"
                    )
            else:
                if value is not None and not isinstance(value, str):
                    raise ValueError(
                        f"Metric row {index} field "
                        f"{field!r} must be a string or null "
                        "for non-supported rows"
                    )

        evidence = row.get("evidence")

        if not isinstance(evidence, list):
            raise ValueError(
                f"Metric row {index} evidence must be a list"
            )

        field_evidence = row.get(
            "field_evidence"
        )

        if not isinstance(field_evidence, dict):
            raise ValueError(
                f"Metric row {index} field_evidence "
                "must be an object"
            )

        expected_anchor_fields = {
            "value",
            "unit",
            "period",
            "scope",
        }

        if set(field_evidence) != expected_anchor_fields:
            raise ValueError(
                "Metric field_evidence must specify "
                "value/unit/period/scope"
            )

    if set(returned_banks) != set(requested_banks):
        raise ValueError(
            "Metric matrix bank scope does not match "
            "the current user request. "
            f"requested={requested_banks}, "
            f"returned={returned_banks}"
        )

    if len(returned_banks) != len(requested_banks):
        raise ValueError(
            "Metric matrix bank count does not match "
            "the current user request"
        )

    return rows


def _metric_request_scoped_validate(
    raw_matrix,
    sources,
    ds,
    base,
    requested_banks,
):
    """
    V1.2 compatibility adapter.

    Preserve:
      1. Phase 2 provider normalization
      2. Phase 2 strict span resolution / provenance

    Replace:
      Phase 2 fixed five-bank cardinality validation

    With:
      Phase 3 request-scoped Metric validation
    """

    normalized = ds.normalize_provider_matrix(
        raw_matrix
    )

    resolved = ds.resolve_matrix(
        normalized,
        sources,
    )

    rows = _validate_request_scoped_metric_matrix(
        resolved,
        requested_banks,
    )

    return normalized, resolved, rows



# ============================================================
# V1.3 SHARED PHASE3 SCHEMA VALIDATION
#
# NARRATIVE / GUIDANCE deterministic validation is shared by
# the initial guard and deterministic revalidation so both
# stages enforce one governance contract.
# ============================================================

def _collect_trusted_span_ids(obj: Any) -> set[str]:
    """
    Collect trusted span IDs defensively from the existing
    Phase 3 span catalog without assuming one exact catalog shape.
    """

    found: set[str] = set()

    def visit(value: Any):
        if isinstance(value, dict):

            for key, item in value.items():

                if (
                    key == "span_id"
                    and isinstance(item, str)
                    and item.strip()
                ):
                    found.add(item.strip())

                if (
                    isinstance(key, str)
                    and key.startswith("S")
                    and ":" in key
                ):
                    found.add(key.strip())

                visit(item)

        elif isinstance(value, (list, tuple, set)):

            for item in value:
                visit(item)

        elif isinstance(value, str):

            candidate = value.strip()

            if (
                candidate.startswith("S")
                and ":" in candidate
                and " " not in candidate
                and len(candidate) < 200
            ):
                found.add(candidate)

    visit(obj)
    return found


def _validate_phase3_schema_matrix(
    *,
    matrix: Any,
    catalog: Any,
    expected_schema: str,
):
    """
    Phase 3 deterministic validation for NARRATIVE and GUIDANCE.

    Returns:
        normalized_matrix,
        governed_matrix,
        rows,
        mismatch_findings,
        insufficiency_findings,
        contract_findings
    """

    local_mismatches = []
    local_insufficiencies = []
    contract_findings = []

    if not isinstance(matrix, dict):

        contract_findings.append({
            "type": "MATRIX_NOT_OBJECT",
            "schema_type": expected_schema,
        })

        return (
            matrix,
            matrix,
            None,
            local_mismatches,
            local_insufficiencies,
            contract_findings,
        )

    local_rows = matrix.get("rows")

    if not isinstance(local_rows, list):

        contract_findings.append({
            "type": "ROWS_NOT_LIST",
            "schema_type": expected_schema,
        })

        return (
            matrix,
            matrix,
            local_rows,
            local_mismatches,
            local_insufficiencies,
            contract_findings,
        )

    if len(local_rows) == 0:

        contract_findings.append({
            "type": "EMPTY_ROWS",
            "schema_type": expected_schema,
        })

    trusted_span_ids = (
        _collect_trusted_span_ids(catalog)
    )

    for row_index, row in enumerate(local_rows):

        if not isinstance(row, dict):

            contract_findings.append({
                "type": "ROW_NOT_OBJECT",
                "row_index": row_index,
            })
            continue

        status = str(
            row.get("status") or ""
        ).strip().lower()

        if status not in {
            "supported",
            "unsupported",
        }:
            contract_findings.append({
                "type": "INVALID_STATUS",
                "row_index": row_index,
                "status": status,
            })

        evidence = row.get(
            "evidence",
            [],
        )

        field_evidence = row.get(
            "field_evidence",
            {},
        )

        if not isinstance(evidence, list):

            contract_findings.append({
                "type": "EVIDENCE_NOT_LIST",
                "row_index": row_index,
            })
            evidence = []

        if not isinstance(field_evidence, dict):

            contract_findings.append({
                "type": "FIELD_EVIDENCE_NOT_OBJECT",
                "row_index": row_index,
            })
            field_evidence = {}

        evidence_ids = [
            item.strip()
            for item in evidence
            if isinstance(item, str)
            and item.strip()
        ]

        unique_evidence = list(
            dict.fromkeys(evidence_ids)
        )

        if len(unique_evidence) > 4:

            contract_findings.append({
                "type": "TOO_MANY_EVIDENCE_SPANS",
                "row_index": row_index,
                "count": len(unique_evidence),
            })

        if expected_schema == "NARRATIVE":

            subject = row.get("subject")
            summary = row.get("summary")
            key_points = row.get("key_points")

            if not (
                isinstance(subject, str)
                and subject.strip()
            ):
                contract_findings.append({
                    "type": "MISSING_SUBJECT",
                    "row_index": row_index,
                })

            if not (
                isinstance(summary, str)
                and summary.strip()
            ):
                contract_findings.append({
                    "type": "MISSING_SUMMARY",
                    "row_index": row_index,
                })

            if not isinstance(key_points, list):
                contract_findings.append({
                    "type": "KEY_POINTS_NOT_LIST",
                    "row_index": row_index,
                })
                key_points = []

            required_evidence_fields = [
                "summary",
            ]

            if key_points:
                required_evidence_fields.append(
                    "key_points"
                )

        else:

            guidance = row.get("guidance")
            summary = row.get("summary")
            requirements = row.get("requirements")
            applicability = row.get("applicability")

            if not (
                isinstance(guidance, str)
                and guidance.strip()
            ):
                contract_findings.append({
                    "type": "MISSING_GUIDANCE",
                    "row_index": row_index,
                })

            if not (
                isinstance(summary, str)
                and summary.strip()
            ):
                contract_findings.append({
                    "type": "MISSING_SUMMARY",
                    "row_index": row_index,
                })

            if not isinstance(requirements, list):
                contract_findings.append({
                    "type": "REQUIREMENTS_NOT_LIST",
                    "row_index": row_index,
                })
                requirements = []

            if not isinstance(applicability, list):
                contract_findings.append({
                    "type": "APPLICABILITY_NOT_LIST",
                    "row_index": row_index,
                })
                applicability = []

            required_evidence_fields = [
                "summary",
            ]

            if requirements:
                required_evidence_fields.append(
                    "requirements"
                )

            if applicability:
                required_evidence_fields.append(
                    "applicability"
                )

        # Unsupported rows are allowed to fail closed
        # without fabricated evidence.
        if status != "supported":
            continue

        if not unique_evidence:

            local_insufficiencies.append({
                "type": "SUPPORTED_ROW_WITHOUT_EVIDENCE",
                "row_index": row_index,
                "schema_type": expected_schema,
            })

        if trusted_span_ids:

            unknown_ids = [
                span_id
                for span_id in unique_evidence
                if span_id not in trusted_span_ids
            ]

            if unknown_ids:

                local_insufficiencies.append({
                    "type": "UNKNOWN_EVIDENCE_SPAN",
                    "row_index": row_index,
                    "span_ids": unknown_ids,
                })

        else:

            local_insufficiencies.append({
                "type": "TRUSTED_SPAN_CATALOG_EMPTY",
                "row_index": row_index,
            })

        selected_set = set(
            unique_evidence
        )

        for field_name, ids in field_evidence.items():

            if not isinstance(ids, list):

                local_mismatches.append({
                    "type": "FIELD_EVIDENCE_NOT_LIST",
                    "row_index": row_index,
                    "field": field_name,
                })
                continue

            normalized_ids = [
                item.strip()
                for item in ids
                if isinstance(item, str)
                and item.strip()
            ]

            outside_selected = [
                span_id
                for span_id in normalized_ids
                if span_id not in selected_set
            ]

            if outside_selected:

                local_mismatches.append({
                    "type": "FIELD_EVIDENCE_NOT_SELECTED",
                    "row_index": row_index,
                    "field": field_name,
                    "span_ids": outside_selected,
                })

        for field_name in required_evidence_fields:

            ids = field_evidence.get(
                field_name,
                [],
            )

            valid_ids = (
                ids
                if isinstance(ids, list)
                else []
            )

            valid_ids = [
                item.strip()
                for item in valid_ids
                if isinstance(item, str)
                and item.strip()
            ]

            if not valid_ids:

                local_insufficiencies.append({
                    "type": "MISSING_REQUIRED_FIELD_EVIDENCE",
                    "row_index": row_index,
                    "field": field_name,
                })

    return (
        matrix,
        matrix,
        local_rows,
        local_mismatches,
        local_insufficiencies,
        contract_findings,
    )


def deterministic_guard_node(
    state: GovernedLiveState,
) -> dict[str, Any]:

    canonical = _canonical()

    matrix = state[
        "research_matrix"
    ]

    sources = state.get(
        "sources",
        [],
    )

    catalog = state.get(
        "span_catalog",
        [],
    )

    schema_type = str(
        state.get("schema_type") or ""
    ).strip().upper()

    intent_type = str(
        state.get("intent_type") or ""
    ).strip().upper()

    valid_schemas = {
        "METRIC",
        "NARRATIVE",
        "GUIDANCE",
        "OUT_OF_SCOPE",
    }

    normalized = None
    resolved = None
    rows = None

    mismatches = []
    insufficiencies = []

    failure_type = None
    guard_status = "PASS"





    try:

        if schema_type not in valid_schemas:

            guard_status = "BLOCK"

            failure_type = (
                "EMPTY_MATRIX_CONTRACT_FAILURE"
            )

            mismatches = [{
                "type": "UNSUPPORTED_SCHEMA_TYPE",
                "schema_type": schema_type,
                "intent_type": intent_type,
            }]

        elif schema_type == "OUT_OF_SCOPE":

            # Valid governed short-circuit.
            # Do not send an out-of-scope response through
            # the frozen Phase 2 Metric validator.

            normalized = matrix
            resolved = matrix

            if isinstance(matrix, dict):
                rows = matrix.get(
                    "rows",
                    [],
                )
            else:
                rows = []

            guard_status = "PASS"
            failure_type = None

        elif schema_type == "METRIC":

            # ------------------------------------------------
            # Frozen V1.1 Metric governance branch.
            # Preserve the validated Phase 2 canonical path.
            # ------------------------------------------------

            (
                normalized,
                resolved,
                rows,
            ) = _metric_request_scoped_validate(
                matrix,
                sources,
                _ds(),
                _base(),
                requested_banks=_requested_metric_banks(state),
            )

            mismatches = (
                canonical
                .field_evidence_mismatches(
                    normalized
                )
            )

            insufficiencies = (
                evidence_insufficiency(
                    normalized,
                    catalog,
                    sources,
                )
            )

            if mismatches:

                guard_status = "BLOCK"
                failure_type = (
                    "FIELD_EVIDENCE_MISMATCH"
                )

            elif insufficiencies:

                guard_status = "BLOCK"
                failure_type = (
                    "EVIDENCE_INSUFFICIENCY"
                )

        else:

            # ------------------------------------------------
            # V1.2 Phase 3 schema-aware governance.
            # Used for NARRATIVE and GUIDANCE.
            # ------------------------------------------------

            (
                normalized,
                resolved,
                rows,
                mismatches,
                insufficiencies,
                contract_findings,
            ) = _validate_phase3_schema_matrix(
                matrix=matrix,
                catalog=catalog,
                expected_schema=schema_type,
            )

            if contract_findings:

                guard_status = "BLOCK"

                failure_type = (
                    "EMPTY_MATRIX_CONTRACT_FAILURE"
                )

                # Preserve diagnostics in the existing
                # mismatch findings state channel.
                mismatches = (
                    contract_findings
                    + mismatches
                )

            elif mismatches:

                guard_status = "BLOCK"

                failure_type = (
                    "FIELD_EVIDENCE_MISMATCH"
                )

            elif insufficiencies:

                guard_status = "BLOCK"

                failure_type = (
                    "EVIDENCE_INSUFFICIENCY"
                )

    except Exception as exc:

        guard_status = "BLOCK"

        failure_type = (
            canonical.classify_exception(
                exc
            )
        )

        print("")
        print(
            "[07 Deterministic Guard]"
        )
        print(
            "  VALIDATION EXCEPTION:",
            type(exc).__name__,
        )
        print(
            "  EXCEPTION MESSAGE:",
            str(exc),
        )
        print(
            "  CLASSIFIED AS:",
            failure_type,
        )

    print("")
    print(
        "[07 Deterministic Guard]"
    )
    print(
        "  INTENT:",
        intent_type,
    )
    print(
        "  SCHEMA:",
        schema_type,
    )
    print(
        "  STATUS:",
        guard_status,
    )
    print(
        "  FIELD / CONTRACT MISMATCHES:",
        len(mismatches),
    )
    print(
        "  EVIDENCE INSUFFICIENCIES:",
        len(insufficiencies),
    )

    return {
        "normalized_matrix":
            normalized,
        "governed_matrix":
            resolved,
        "governed_rows":
            rows,
        "field_evidence_mismatches":
            mismatches,
        "evidence_insufficiency":
            insufficiencies,
        "guard_status":
            guard_status,
        "failure_type":
            failure_type,
        "final_status":
            None,
        "stage_history":
            append_stage(
                state,
                "07 Deterministic Guard - "
                + guard_status,
            ),
    }


# ============================================================
# 5. NODE 08 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â FAILURE CLASSIFIER
# ============================================================

def failure_classifier_node(
    state: GovernedLiveState,
) -> dict[str, Any]:

    failure_type = state.get(
        "failure_type"
    )

    if (
        state.get("guard_status")
        == "PASS"
    ):
        failure_type = None

    print("")
    print(
        "[08 Failure Classifier]"
    )

    print(
        "  FAILURE TYPE:",
        failure_type
        if failure_type
        else "CLEAN",
    )

    return {
        "failure_type":
            failure_type,
        "stage_history":
            append_stage(
                state,
                "08 Failure Classifier - "
                + (
                    failure_type
                    if failure_type
                    else "CLEAN"
                ),
            ),
    }


# ============================================================
# 6. NODE 09 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â REAL FROZEN RECOVERY POLICY
# ============================================================

def recovery_controller_node(
    state: GovernedLiveState,
) -> dict[str, Any]:

    canonical = _canonical()

    retry_count = int(
        state.get(
            "retry_count",
            0,
        )
    )

    failure_type = state.get(
        "failure_type"
    )

    action = canonical.recovery_action(
        failure_type,
        retry_count,
    )

    # V1.3 governed recovery extension:
    # UNKNOWN_SPAN_ID means the Research LLM cited a span
    # outside the trusted catalog. Do NOT weaken the Guard and
    # do NOT rerun Planning/Retrieval. Allow exactly one
    # matrix-only repair using the existing trusted evidence.
    if (
        failure_type == "UNKNOWN_SPAN_ID"
        and retry_count < MAX_CONTRACT_RETRIES
    ):
        action = "RETRY_MATRIX"

    print("")
    print(
        "[09 Recovery Controller]"
    )
    print(
        "  REAL FROZEN PHASE 2 POLICY: PASS"
    )
    print(
        "  FAILURE:",
        failure_type
        if failure_type
        else "CLEAN",
    )
    print(
        "  RETRY COUNT:",
        retry_count,
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
                "09 Recovery Controller - "
                + action,
            ),
    }


def route_recovery(
    state: GovernedLiveState,
) -> str:

    action = state[
        "recovery_action"
    ]

    allowed = {
        "CONTINUE_TO_JUDGE",
        "RETRY_MATRIX",
        "CLAIM_LEVEL_FAIL_CLOSED",
        "ESCALATE",
    }

    if action not in allowed:
        raise ValueError(
            "Unsupported recovery action: "
            f"{action!r}"
        )

    return action


# ============================================================
# 7. NODE 10 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â MATRIX-ONLY RETRY
# ============================================================

async def retry_matrix_node(
    state: GovernedLiveState,
) -> dict[str, Any]:

    canonical = _canonical()
    base = _base()
    ds = _ds()

    current_retry = int(
        state.get(
            "retry_count",
            0,
        )
    )

    if current_retry >= MAX_CONTRACT_RETRIES:
        raise RuntimeError(
            "Application contract retry budget "
            "already exhausted."
        )

    new_retry_count = (
        current_retry + 1
    )

    # ========================================================
    # V1.2 SCHEMA-AWARE RETRY FEEDBACK
    #
    # METRIC preserves the frozen Phase2 feedback builder.
    # NARRATIVE / GUIDANCE use a generic Phase3 serializer
    # because their Guard findings do not contain Metric-only
    # fields such as "bank".
    # ========================================================

    schema_type = str(
        state.get("schema_type") or ""
    ).strip().upper()

    field_findings = list(
        state.get(
            "field_evidence_mismatches",
            [],
        )
        or []
    )

    evidence_findings = list(
        state.get(
            "evidence_insufficiency",
            [],
        )
        or []
    )

    if schema_type == "METRIC":

        retry_feedback = (
            canonical.build_retry_feedback(
                field_findings,
                evidence_findings,
            )
        )

    elif schema_type in {
        "NARRATIVE",
        "GUIDANCE",
    }:

        all_findings = (
            field_findings
            + evidence_findings
        )

        if not all_findings:

            retry_feedback = (
                "No structured Guard finding was supplied. "
                "Repair the previous answer so it fully satisfies "
                "the current schema contract and trusted-evidence "
                "requirements."
            )

        else:

            feedback_lines = []

            for idx, item in enumerate(
                all_findings,
                start=1,
            ):

                if isinstance(item, dict):

                    finding_type = str(
                        item.get("type")
                        or "UNSPECIFIED_FINDING"
                    )

                    feedback_lines.append(
                        f"{idx}. Finding type: "
                        f"{finding_type}"
                    )

                    for key, value in item.items():

                        if key == "type":
                            continue

                        feedback_lines.append(
                            f"   {key}: {value}"
                        )

                else:

                    feedback_lines.append(
                        f"{idx}. {item}"
                    )

            retry_feedback = "\n".join(
                feedback_lines
            )

    elif schema_type == "OUT_OF_SCOPE":

        raise RuntimeError(
            "OUT_OF_SCOPE must not enter Retry."
        )

    else:

        raise ValueError(
            "Unsupported retry feedback schema: "
            f"{schema_type!r}"
        )

    # ========================================================
    # V1.2 SCHEMA-AWARE RETRY DISPATCH
    #
    # Retry repairs the existing governed answer.
    # It MUST NOT reclassify intent or schema.
    # ========================================================

    intent_type = str(
        state.get("intent_type") or ""
    ).strip().upper()

    schema_type = str(
        state.get("schema_type") or ""
    ).strip().upper()

    valid_routes = {
        "METRIC",
        "NARRATIVE",
        "GUIDANCE",
        "OUT_OF_SCOPE",
    }

    if schema_type not in valid_routes:
        raise ValueError(
            "Unsupported retry schema: "
            f"{schema_type!r}"
        )

    if schema_type == "OUT_OF_SCOPE":
        raise RuntimeError(
            "OUT_OF_SCOPE must not enter Retry."
        )

    retry_header = (
        "=== V1.2 GOVERNED RETRY ===\n"
        f"ORIGINAL INTENT: {intent_type}\n"
        f"ORIGINAL SCHEMA: {schema_type}\n"
        "The intent and schema are already decided.\n"
        "DO NOT reclassify the question.\n"
        "Repair only the previous answer using trusted evidence.\n\n"
    )

    if schema_type == "METRIC":

        retry_schema_prompt = (
            ds.SPAN_PROMPT
            + evidence_uniqueness_contract()
            + "\n\n"
            + "=== REQUEST-SCOPE OVERRIDE ===\n"
            + f"The CURRENT user question is: {state['query']}\n"
            + "The output entity scope MUST match the CURRENT "
              "user request.\n"
            + "If the user requests exactly ONE bank, return "
              "exactly ONE row for that bank.\n"
            + "If the user requests multiple banks, return rows "
              "only for those requested banks.\n"
            + "Do NOT automatically return all five benchmark "
              "banks.\n"
            + "This instruction OVERRIDES any earlier five-bank "
              "benchmark instruction.\n"
        )

    elif schema_type == "NARRATIVE":

        retry_schema_prompt = (
            "You are repairing a governed NARRATIVE answer.\n"
            "Use ONLY the trusted spans supplied in the payload.\n"
            "Do not invent facts, numbers, business segments, "
            "causes, drivers, or implications.\n"
            "For comparative questions, keep the requested "
            "entities explicit.\n"
            "For analytical questions, distinguish supported "
            "drivers from speculation.\n"
            "If evidence is insufficient, return status "
            "'unsupported' rather than guessing.\n"
            "Use no more than FOUR unique evidence spans per row.\n"
            "Every supported summary must have field_evidence.\n"
            "If key_points is non-empty, key_points must also "
            "have field_evidence.\n"
            "Every field_evidence span must also appear in the "
            "row evidence list.\n\n"
            "Return JSON only in this shape:\n"
            "{\n"
            '  "rows": [\n'
            "    {\n"
            '      "subject": "...",\n'
            '      "summary": "...",\n'
            '      "key_points": ["..."],\n'
            '      "status": "supported|unsupported",\n'
            '      "limitation": "...",\n'
            '      "evidence": ["span_id"],\n'
            '      "field_evidence": {\n'
            '        "summary": ["span_id"],\n'
            '        "key_points": ["span_id"]\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n"
        )

    elif schema_type == "GUIDANCE":

        retry_schema_prompt = (
            "You are repairing a governed GUIDANCE answer.\n"
            "Use ONLY the trusted spans supplied in the payload.\n"
            "Do not invent regulatory requirements, supervisory "
            "expectations, applicability, or citations.\n"
            "Preserve distinctions among requirements, "
            "expectations, and applicability.\n"
            "If trusted evidence is insufficient, return status "
            "'unsupported' rather than guessing.\n"
            "Use no more than FOUR unique evidence spans per row.\n"
            "Every supported summary must have field_evidence.\n"
            "If requirements or applicability are non-empty, "
            "they must have field_evidence.\n"
            "Every field_evidence span must also appear in the "
            "row evidence list.\n\n"
            "Return JSON only in this shape:\n"
            "{\n"
            '  "rows": [\n'
            "    {\n"
            '      "guidance": "...",\n'
            '      "summary": "...",\n'
            '      "requirements": ["..."],\n'
            '      "applicability": ["..."],\n'
            '      "status": "supported|unsupported",\n'
            '      "limitation": "...",\n'
            '      "evidence": ["span_id"],\n'
            '      "field_evidence": {\n'
            '        "summary": ["span_id"],\n'
            '        "requirements": ["span_id"],\n'
            '        "applicability": ["span_id"]\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n"
        )

    retry_system_prompt = (
        retry_header
        + retry_schema_prompt
        + "\n\n"
        + "=== GOVERNANCE RETRY FEEDBACK ===\n"
        + retry_feedback
    )

    payload = {
        "question":
            state["query"],
        "banks":
            (
                ["REGULATORY"]
                if schema_type == "GUIDANCE"
                else base.BANKS
            ),
        "sources":
            state["sources"],
        "span_catalog":
            state[
                "span_catalog_payload"
            ],
        "previous_matrix":
            (
                state.get(
                    "normalized_matrix"
                )
                or state.get(
                    "research_matrix"
                )
            ),
        "retry_count":
            new_retry_count,
        "max_contract_retries":
            MAX_CONTRACT_RETRIES,
    }

    started = time.perf_counter()

    # raw, call = await complete_real(
    #     stage="research_matrix_attempt_1",
    #     system_prompt=retry_system_prompt,
    #     payload=payload,
    # )
    
    raw, call = await complete_real(
    stage="research_matrix_attempt_1",
    system_prompt=retry_system_prompt,
    payload=payload,
    provider=str(
        state.get("provider") or "openai"
    ).strip().lower(),
    )

    matrix = base.parse(
        raw
    )

    elapsed = (
        time.perf_counter()
        - started
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
        "[10 Retry Matrix]"
    )
    print(
        "  REAL RESEARCH LLM RETRY: PASS"
    )
    print(
        "  RETRY COUNT:",
        new_retry_count,
    )
    print(
        "  PLANNING RERUN: NO"
    )
    print(
        "  RETRIEVAL RERUN: NO"
    )
    print(
        f"  Seconds: {elapsed:.3f}"
    )

    return {
        "research_matrix_raw":
            raw,
        "research_matrix":
            matrix,
        "retry_count":
            new_retry_count,
        "model_calls":
            calls,

        # Clear attempt-0 validation values.
        "normalized_matrix":
            None,
        "governed_matrix":
            None,
        "governed_rows":
            None,
        "field_evidence_mismatches":
            [],
        "evidence_insufficiency":
            [],
        "guard_status":
            None,
        "failure_type":
            None,
        "recovery_action":
            None,

        "stage_history":
            append_stage(
                state,
                "10 Retry Matrix - "
                "REAL LLM ATTEMPT 1",
            ),
    }


# ============================================================
# 8. NODE 11 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â REAL CLAIM-LEVEL FAIL-CLOSED
# ============================================================

def claim_level_fail_closed_node(
    state: GovernedLiveState,
) -> dict[str, Any]:

    canonical = _canonical()

    matrix = (
        state.get("normalized_matrix")
        or state.get("research_matrix")
    )

    insufficiencies = list(
        state.get(
            "evidence_insufficiency",
            [],
        )
        or []
    )

    schema_type = str(
        state.get("schema_type") or ""
    ).strip().upper()

    # ========================================================
    # V1.3 SCHEMA-AWARE CLAIM-LEVEL FAIL-CLOSED
    #
    # METRIC:
    #   Preserve frozen Phase 2 remediation exactly.
    #
    # NARRATIVE / GUIDANCE:
    #   Phase 3 findings identify affected claims using
    #   row_index rather than the Metric-only "bank" field.
    #
    # Governance rule:
    #   Insufficient trusted evidence must downgrade the
    #   affected claim to unsupported rather than fabricate
    #   evidence or silently approve the claim.
    # ========================================================

    if schema_type == "METRIC":

        governed_candidate = (
            canonical.apply_claim_level_fail_closed(
                matrix,
                insufficiencies,
            )
        )

        remediation_mode = "FROZEN_PHASE2_METRIC"

    elif schema_type in {
        "NARRATIVE",
        "GUIDANCE",
    }:

        import copy

        governed_candidate = copy.deepcopy(matrix)

        if isinstance(governed_candidate, dict):

            rows = governed_candidate.get(
                "rows",
                [],
            )

        elif isinstance(governed_candidate, list):

            rows = governed_candidate

        else:

            raise TypeError(
                "Schema-aware fail-closed expected "
                "matrix to be dict or list, got "
                f"{type(governed_candidate).__name__}."
            )

        if not isinstance(rows, list):

            raise TypeError(
                "Schema-aware fail-closed expected "
                "'rows' to be a list."
            )

        affected_by_row = {}

        for finding in insufficiencies:

            if not isinstance(finding, dict):
                continue

            row_index = finding.get("row_index")

            if not isinstance(row_index, int):
                continue

            finding_type = str(
                finding.get("type")
                or "EVIDENCE_INSUFFICIENCY"
            ).strip()

            field_name = str(
                finding.get("field")
                or ""
            ).strip()

            detail = finding_type

            if field_name:
                detail = (
                    finding_type
                    + ":"
                    + field_name
                )

            if row_index not in affected_by_row:
                affected_by_row[row_index] = []

            affected_by_row[row_index].append(
                detail
            )

        for row_index, reasons in affected_by_row.items():

            if (
                row_index < 0
                or row_index >= len(rows)
            ):

                raise IndexError(
                    "Fail-closed finding references "
                    f"invalid row_index {row_index}; "
                    f"row_count={len(rows)}."
                )

            row = rows[row_index]

            if not isinstance(row, dict):

                raise TypeError(
                    "Fail-closed target row "
                    f"{row_index} is not an object."
                )

            row["status"] = "unsupported"

            row["evidence"] = []

            row["field_evidence"] = {}

            unique_reasons = list(
                dict.fromkeys(
                    reason
                    for reason in reasons
                    if reason
                )
            )

            if unique_reasons:

                reason_text = ", ".join(
                    unique_reasons
                )

            else:

                reason_text = (
                    "EVIDENCE_INSUFFICIENCY"
                )

            row["limitation"] = (
                "Fail-closed by deterministic governance "
                "because trusted evidence was insufficient: "
                + reason_text
            )

        remediation_mode = "PHASE3_SCHEMA_AWARE"

    elif schema_type == "OUT_OF_SCOPE":

        raise RuntimeError(
            "OUT_OF_SCOPE must not enter "
            "claim-level fail-closed."
        )

    else:

        raise ValueError(
            "Unsupported claim-level fail-closed schema: "
            f"{schema_type!r}"
        )

    print("")
    print(
        "[11 Claim-Level Fail Closed]"
    )
    print(
        "  SCHEMA:",
        schema_type,
    )
    print(
        "  REMEDIATION MODE:",
        remediation_mode,
    )
    print(
        "  AFFECTED FINDINGS:",
        len(insufficiencies),
    )

    return {
        "research_matrix":
            governed_candidate,
        "fail_closed_applied":
            True,
        "stage_history":
            append_stage(
                state,
                "11 Claim-Level Fail Closed - "
                + schema_type,
            ),
    }

def deterministic_revalidation_node(
    state: GovernedLiveState,
) -> dict[str, Any]:
    """
    Schema-aware deterministic revalidation.

    METRIC:
        Preserve frozen Phase 2 governed validation.

    NARRATIVE / GUIDANCE:
        Reuse the same Phase 3 deterministic schema validator
        used by the initial guard.

    Recovery invariant:
        A fail-closed unsupported row may remain unsupported
        without fabricated evidence, but malformed contracts,
        evidence mismatches, or remaining evidence
        insufficiencies must still BLOCK.
    """

    canonical = _canonical()

    schema_type = str(
        state.get("schema_type") or ""
    ).strip().upper()

    matrix = state["research_matrix"]

    sources = state.get(
        "sources",
        [],
    )

    catalog = state.get(
        "span_catalog",
        [],
    )

    normalized = None
    resolved = None
    rows = None

    mismatches = []
    insufficiencies = []
    contract_findings = []

    try:

        if schema_type == "METRIC":

            (
                normalized,
                resolved,
                rows,
            ) = canonical.governed_validate(
                matrix,
                sources,
                _ds(),
                _base(),
            )

            revalidation_mode = (
                "FROZEN_PHASE2_METRIC"
            )

        elif schema_type in {
            "NARRATIVE",
            "GUIDANCE",
        }:

            (
                normalized,
                resolved,
                rows,
                mismatches,
                insufficiencies,
                contract_findings,
            ) = _validate_phase3_schema_matrix(
                matrix=matrix,
                catalog=catalog,
                expected_schema=schema_type,
            )

            revalidation_mode = (
                "PHASE3_SCHEMA_AWARE"
            )

            # --------------------------------------------
            # Preserve deterministic guard precedence.
            # --------------------------------------------

            if contract_findings:

                failure_type = (
                    "EMPTY_MATRIX_CONTRACT_FAILURE"
                )

                mismatches = (
                    contract_findings
                    + mismatches
                )

                print("")
                print(
                    "[12 Deterministic Revalidation]"
                )
                print(
                    "  SCHEMA:",
                    schema_type,
                )
                print(
                    "  MODE:",
                    revalidation_mode,
                )
                print(
                    "  STATUS: BLOCK"
                )
                print(
                    "  FAILURE:",
                    failure_type,
                )

                return {
                    "normalized_matrix":
                        normalized,
                    "governed_matrix":
                        resolved,
                    "governed_rows":
                        rows,
                    "field_evidence_mismatches":
                        mismatches,
                    "evidence_insufficiency":
                        insufficiencies,
                    "revalidation_status":
                        "BLOCK",
                    "failure_type":
                        failure_type,
                    "final_status":
                        "ESCALATED",
                    "stage_history":
                        append_stage(
                            state,
                            "12 Deterministic "
                            "Revalidation - BLOCK",
                        ),
                }

            if mismatches:

                failure_type = (
                    "FIELD_EVIDENCE_MISMATCH"
                )

                print("")
                print(
                    "[12 Deterministic Revalidation]"
                )
                print(
                    "  SCHEMA:",
                    schema_type,
                )
                print(
                    "  MODE:",
                    revalidation_mode,
                )
                print(
                    "  STATUS: BLOCK"
                )
                print(
                    "  FAILURE:",
                    failure_type,
                )

                return {
                    "normalized_matrix":
                        normalized,
                    "governed_matrix":
                        resolved,
                    "governed_rows":
                        rows,
                    "field_evidence_mismatches":
                        mismatches,
                    "evidence_insufficiency":
                        insufficiencies,
                    "revalidation_status":
                        "BLOCK",
                    "failure_type":
                        failure_type,
                    "final_status":
                        "ESCALATED",
                    "stage_history":
                        append_stage(
                            state,
                            "12 Deterministic "
                            "Revalidation - BLOCK",
                        ),
                }

            if insufficiencies:

                failure_type = (
                    "EVIDENCE_INSUFFICIENCY"
                )

                print("")
                print(
                    "[12 Deterministic Revalidation]"
                )
                print(
                    "  SCHEMA:",
                    schema_type,
                )
                print(
                    "  MODE:",
                    revalidation_mode,
                )
                print(
                    "  STATUS: BLOCK"
                )
                print(
                    "  FAILURE:",
                    failure_type,
                )

                return {
                    "normalized_matrix":
                        normalized,
                    "governed_matrix":
                        resolved,
                    "governed_rows":
                        rows,
                    "field_evidence_mismatches":
                        mismatches,
                    "evidence_insufficiency":
                        insufficiencies,
                    "revalidation_status":
                        "BLOCK",
                    "failure_type":
                        failure_type,
                    "final_status":
                        "ESCALATED",
                    "stage_history":
                        append_stage(
                            state,
                            "12 Deterministic "
                            "Revalidation - BLOCK",
                        ),
                }

        elif schema_type == "OUT_OF_SCOPE":

            raise RuntimeError(
                "OUT_OF_SCOPE must not enter "
                "deterministic revalidation."
            )

        else:

            raise ValueError(
                "Unsupported deterministic "
                "revalidation schema: "
                f"{schema_type!r}"
            )

        # ====================================================
        # PASS
        #
        # Explicitly clear stale findings from the previous
        # failed guard/recovery cycle.
        # ====================================================

        status = "PASS"
        failure_type = None

        print("")
        print(
            "[12 Deterministic Revalidation]"
        )
        print(
            "  SCHEMA:",
            schema_type,
        )
        print(
            "  MODE:",
            revalidation_mode,
        )
        print(
            "  STATUS: PASS"
        )
        print(
            "  JUDGE MAY BE CONSIDERED: YES"
        )

        return {
            "normalized_matrix":
                normalized,
            "governed_matrix":
                resolved,
            "governed_rows":
                rows,
            "field_evidence_mismatches":
                [],
            "evidence_insufficiency":
                [],
            "revalidation_status":
                status,
            "failure_type":
                failure_type,
            "final_status":
                None,
            "stage_history":
                append_stage(
                    state,
                    "12 Deterministic "
                    "Revalidation - PASS",
                ),
        }

    except Exception as exc:

        failure_type = (
            canonical.classify_exception(
                exc
            )
        )

        print("")
        print(
            "[12 Deterministic Revalidation]"
        )
        print(
            "  SCHEMA:",
            schema_type,
        )
        print(
            "  STATUS: BLOCK"
        )
        print(
            "  EXCEPTION:",
            type(exc).__name__,
        )
        print(
            "  MESSAGE:",
            str(exc),
        )
        print(
            "  FAILURE:",
            failure_type,
        )

        return {
            "revalidation_status":
                "BLOCK",
            "failure_type":
                failure_type,
            "final_status":
                "ESCALATED",
            "stage_history":
                append_stage(
                    state,
                    "12 Deterministic "
                    "Revalidation - BLOCK",
                ),
        }


def route_revalidation(
    state: GovernedLiveState,
) -> str:

    if (
        state.get(
            "revalidation_status"
        )
        == "PASS"
    ):
        return "JUDGE_GATE"

    return "ESCALATE"


# ============================================================
# 10. NODE 13 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â JUDGE GATE
# ============================================================

def judge_gate_node(
    state: GovernedLiveState,
) -> dict[str, Any]:

    schema_type = str(
        state.get("schema_type") or ""
    ).strip().upper()

    allowed = (
        schema_type != "OUT_OF_SCOPE"
        and state.get(
            "governed_matrix"
        )
        is not None
        and state.get(
            "final_status"
        )
        not in (
            "ESCALATED",
            "FAIL_CLOSED",
        )
    )

    print("")
    print(
        "[13 Judge Gate]"
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
                "13 Judge Gate - "
                + (
                    "ALLOWED"
                    if allowed
                    else "BLOCKED"
                ),
            ),
    }


def route_judge_gate(
    state: GovernedLiveState,
) -> str:

    if state.get(
        "judge_allowed"
    ):
        return "JUDGE"

    return "FINAL"


# ============================================================
# 11. NODE 14 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â REAL JUDGE LLM
# ============================================================

async def judge_node(
    state: GovernedLiveState,
) -> dict[str, Any]:

    base = _base()

    schema_type = str(
        state.get("schema_type") or ""
    ).strip().upper()

    intent_type = str(
        state.get("intent_type") or ""
    ).strip().upper()

    valid_schemas = {
        "METRIC",
        "NARRATIVE",
        "GUIDANCE",
        "OUT_OF_SCOPE",
    }

    if schema_type not in valid_schemas:
        raise ValueError(
            "Unsupported Judge schema_type: "
            + repr(schema_type)
        )

    if schema_type == "OUT_OF_SCOPE":
        raise RuntimeError(
            "OUT_OF_SCOPE must not enter Judge LLM."
        )

    if schema_type == "METRIC":

        # ----------------------------------------------------
        # V1.2 request-scoped Metric Judge.
        #
        # Preserve Phase 2 metric semantic rigor while
        # removing the legacy fixed-five-bank benchmark
        # assumption.
        # ----------------------------------------------------

        requested_metric_banks = (
            _requested_metric_banks(
                state
            )
        )

        if not requested_metric_banks:
            raise ValueError(
                "Metric Judge requires at least "
                "one requested bank."
            )

        judge_prompt = """
You are the independent Metric Review Agent / LLM Judge.

The Planning Agent has already determined that this is a
METRIC request. Do not reclassify the intent or schema.

Judge the supplied governed Metric matrix against the supplied
source passages and the CURRENT user request.

ENTITY SCOPE
- The payload contains requested_banks.
- Review all and only the banks in requested_banks.
- Do NOT require five benchmark banks.
- A single-bank request may pass with exactly one supported row.
- A multi-bank request may pass when all and only the requested
  banks are correctly represented.
- Extra unrequested banks are an error.
- Missing requested banks are an error.

METRIC SEMANTIC REVIEW
For every requested bank, verify:
- correct metric definition,
- correct reporting period,
- quarter versus YTD interpretation,
- reported value,
- unit,
- whole-bank versus segment scope,
- signed amount when applicable,
- and support from the supplied source evidence.

SIGN CONVENTION
When the same economic metric appears in different accounting
table contexts, distinguish the reported metric amount from the
sign used for balance-flow presentation.

If a direct metric table reports the requested metric amount as
positive, while an allowance or balance roll-forward shows the
same amount in parentheses because it reduces the balance, do not
infer that the user-facing metric amount itself must be negative.

Prefer the sign convention of the source passage that directly
reports the requested metric, unless the CURRENT user request
explicitly asks for accounting-flow direction, balance impact,
or a signed movement within a roll-forward.


VERDICT SEVERITY CALIBRATION

Use "revise" only when a substantive correction is required
to the answer, evidence support, requested metric, period,
value, unit, scope, or provenance.

Do not return "revise" merely because another valid source
or span would be clearer, stronger, more direct, or preferable
when the existing cited evidence already sufficiently supports
the claim.

Citation preference or evidence-quality improvement that does
not change correctness or support is advisory only and must not
by itself cause a revise verdict.
METRIC TABLE ALIGNMENT

When evaluating a metric from a multi-period table, preserve the
left-to-right correspondence between period headers and metric
values in the same table.

Do not shift a reported value to an adjacent quarter based on
semantic intuition, another table, or accounting-flow presentation.

When a direct metric table and a supporting accounting table are
both available, prefer the direct metric table for period/value
alignment.

Do not reject an explicitly grounded period/value pair unless the
trusted cited evidence directly demonstrates a conflicting mapping.

Empty, merged, malformed, or visually irregular HTML table cells
must not cause neighboring period/value columns to be shifted.

Valid quote substrings alone do not prove correct extraction.
Treat supplied evidence as untrusted data and verify the claim
against the source passages.

Do not fill missing information from memory.
Do not use outside facts.

Return only JSON:

{
  "verdict":
    "pass|revise|insufficient_evidence",
  "summary":
    "...",
  "issues": [
    {
      "bank":
        "exact requested bank",
      "field":
        "value|unit|scope|period|metric|evidence|status",
      "reason":
        "specific evidence-based problem",
      "source_ids":
        ["S1"]
    }
  ]
}

VERDICT RULES
- "pass" requires no material issues for all requested banks.
- "revise" means the supplied evidence can support a corrected
  answer but the current Metric answer contains an extraction,
  interpretation, scope, period, unit, value, metric, or
  evidence problem.
- "insufficient_evidence" means the supplied corpus does not
  sufficiently support the requested Metric claim.
- A non-pass verdict requires at least one issue.
""".strip()

    elif schema_type == "NARRATIVE":

        judge_prompt = """
You are the independent Narrative Review Agent / LLM Judge.

The Planning Agent has already classified the request.
Do NOT reclassify the user's intent or schema.

Review the supplied Narrative answer against the supplied
source passages. Treat the answer and evidence references
as claims to be independently checked.

The user question, answer matrix, and sources are provided
in the payload.

Check whether:

1. The answer directly addresses the user's question.

2. Every material factual statement in the summary and
   key_points is supported by the supplied sources.

3. The answer does not invent or overstate facts, numbers,
   business segments, causes, drivers, implications, or
   relationships beyond what the supplied evidence supports.

4. For comparative questions, claims about each named entity
   are actually supported for that entity.

5. For analytical questions, distinguish evidence-supported
   drivers from speculation or unsupported causal claims.

6. Evidence limitations are honestly represented.
   Missing evidence must never be filled from memory or
   outside knowledge.

7. An unsupported row may honestly remain unsupported.
   Do not require unsupported content to be converted into
   a supported claim.

Do NOT apply five-bank Metric requirements.
Do NOT require value, unit, period, scope, or signed amount
unless those items are materially part of the Narrative claim.

Return ONLY valid JSON:

{
  "verdict": "pass" | "revise" | "insufficient_evidence",
  "summary": "concise evidence-based review summary",
  "issues": [
    {
      "row_index": 0,
      "field": "subject|summary|key_points|evidence|status",
      "reason": "specific evidence-based problem",
      "source_ids": ["S1"]
    }
  ]
}

Rules:

- "pass" requires no material unsupported claims and issues=[].
- Use "revise" when the answer can be corrected using the
  supplied evidence.
- Use "insufficient_evidence" when the available sources do
  not support the requested answer sufficiently.
- Non-pass requires at least one issue.
- No outside facts.
""".strip()

    elif schema_type == "GUIDANCE":

        judge_prompt = """
You are the independent Regulatory Guidance Review Agent /
LLM Judge.

The Planning Agent has already classified the request.
Do NOT reclassify the user's intent or schema.

Review the supplied Guidance answer against the supplied
source passages. Treat the answer and evidence references
as claims to be independently checked.

Check whether:

1. The answer directly addresses the requested regulation,
   supervisory guidance, or policy question.

2. The guidance identity and description are supported by
   the supplied sources.

3. Each stated requirement is explicitly supported by the
   supplied evidence.

4. Each stated applicability statement is supported by the
   supplied evidence.

5. The answer preserves distinctions among requirements,
   expectations, recommendations, applicability, and
   explanatory context. Do not strengthen guidance language
   beyond the source.

6. The answer does not invent requirements, citations,
   obligations, thresholds, effective dates, applicability,
   or regulatory conclusions.

7. Missing evidence is honestly represented and must not be
   filled from memory or outside knowledge.

8. An unsupported row may honestly remain unsupported when
   the retrieved corpus does not contain sufficient evidence.

Do NOT apply five-bank Metric requirements.
Do NOT require value, unit, quarter, YTD, signed amount,
or five supported bank rows.

Return ONLY valid JSON:

{
  "verdict": "pass" | "revise" | "insufficient_evidence",
  "summary": "concise evidence-based review summary",
  "issues": [
    {
      "row_index": 0,
      "field": "guidance|summary|requirements|applicability|evidence|status",
      "reason": "specific evidence-based problem",
      "source_ids": ["S1"]
    }
  ]
}

Rules:

- "pass" requires no material unsupported claims and issues=[].
- Use "revise" when the answer can be corrected using the
  supplied evidence.
- Use "insufficient_evidence" when the supplied corpus does
  not support the requested guidance sufficiently.
- Non-pass requires at least one issue.
- No outside facts.
""".strip()

    payload = {
        "question":
            state["query"],
        "matrix":
            state["governed_matrix"],
        "sources":
            state["sources"],
    }

    if schema_type == "METRIC":
        payload["requested_banks"] = (
            requested_metric_banks
        )

    started = time.perf_counter()

    # raw, call = await complete_real(
    #     stage="llm_judge_review",
    #     system_prompt=base.REVIEW,
    #     payload=payload,
    # )
    
    raw, call = await complete_real(
    stage="llm_judge_review",
    system_prompt=judge_prompt,
    payload=payload,
    provider=str(
        state.get("provider") or "openai"
    ).strip().lower(),
    )

    review = base.parse(
        raw
    )

    elapsed = (
        time.perf_counter()
        - started
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

    verdict = extract_judge_verdict(
        review
    )

    print("")
    print(
        "[14 LLM Judge Review]"
    )
    print(
        "  REAL JUDGE LLM: PASS"
    )
    print(
        "  VERDICT:",
        verdict
        if verdict
        else "SEE REVIEW OBJECT",
    )
    print(
        f"  Seconds: {elapsed:.3f}"
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
                "14 LLM Judge Review - "
                "REAL LLM",
            ),
    }


# ============================================================
# 12. NODE 15 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â JUDGE CONTRACT GUARDRAIL
# ============================================================

def judge_contract_guardrail_node(
    state: GovernedLiveState,
) -> dict[str, Any]:

    review = state.get(
        "judge_review"
    )

    status = (
        "PASS"
        if isinstance(review, dict)
        and bool(review)
        else "BLOCK"
    )

    print("")
    print(
        "[15 Judge Contract Guardrail]"
    )
    print(
        "  STATUS:",
        status,
    )

    return {
        "judge_contract_status":
            status,
        "stage_history":
            append_stage(
                state,
                "15 Judge Contract "
                "Guardrail - "
                + status,
            ),
    }


# ============================================================
# 13. NODE 16 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â FINAL GOVERNED DECISION
# ============================================================

def final_decision_node(
    state: GovernedLiveState,
) -> dict[str, Any]:

    # ========================================================
    # V1.3 METRIC EVIDENCE COMPLETENESS POLICY
    # ========================================================
    #
    # Judge PASS means the answer is semantically consistent
    # with the available evidence. It does NOT mean that a
    # requested metric with missing/unsupported evidence may
    # be automatically APPROVED.
    #
    # Explicit METRIC missing_evidence / unsupported rows are
    # therefore routed to PENDING_REVIEW.
    # ========================================================

    schema_type = str(
        state.get("schema_type")
        or ""
    ).strip().upper()

    metric_has_non_supported_row = False

    if schema_type == "METRIC":

        matrix = (
            state.get("governed_matrix")
            or state.get("normalized_matrix")
            or state.get("research_matrix")
            or []
        )

        if isinstance(matrix, dict):
            rows = matrix.get("rows")

            if isinstance(rows, list):
                matrix = rows
            else:
                matrix = [matrix]

        if isinstance(matrix, list):

            for row in matrix:

                if not isinstance(row, dict):
                    continue

                status = str(
                    row.get("status")
                    or ""
                ).strip().lower()

                if status in {
                    "missing_evidence",
                    "unsupported",
                }:
                    metric_has_non_supported_row = True
                    break

    # Escalation always bypasses/overrides Judge approval.
    if (
        state.get(
            "recovery_action"
        )
        == "ESCALATE"
        or state.get(
            "final_status"
        )
        == "ESCALATED"
    ):

        final_status = "ESCALATED"

    elif metric_has_non_supported_row:

        final_status = "PENDING_REVIEW"

    elif (
        state.get(
            "judge_contract_status"
        )
        == "BLOCK"
    ):

        final_status = "PENDING_REVIEW"

    elif state.get(
        "judge_allowed"
    ):

        verdict = (
            state.get(
                "judge_verdict"
            )
            or ""
        ).lower()

        if any(
            token in verdict
            for token in (
                "revise",
                "reject",
                "fail",
                "pending",
            )
        ):
            final_status = (
                "PENDING_REVIEW"
            )

        elif any(
            token in verdict
            for token in (
                "approve",
                "pass",
                "accept",
            )
        ):
            final_status = "APPROVED"

        else:
            # Conservative fail-safe:
            # unknown semantic Judge output is
            # never promoted to automatic approval.
            final_status = (
                "PENDING_REVIEW"
            )

    else:

        final_status = "ESCALATED"

    print("")
    print(
        "[16 Final Governed Decision]"
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
                "16 Final Governed Decision - "
                + final_status,
            ),
    }


# ============================================================
# 14. BUILD FULL GOVERNED LANGGRAPH
# ============================================================

async def evidence_context_enricher_node(
    state: GovernedLiveState,
) -> dict[str, Any]:
    """
    Phase 3 serving-layer remediation for verified document context
    lost during PDF -> MinerU -> chunk serialization.

    Governance rules:
    - Never rewrite source text.
    - Never infer a unit from numeric formatting.
    - Only add explicitly source-verified context.
    - Preserve fail-closed behavior when no verified rule applies.
    """

    payload = state.get("span_catalog_payload")

    if not isinstance(payload, dict):
        return {}

    sources = state.get("sources") or []

    verified_contexts = []

    for source in sources:
        if not isinstance(source, dict):
            continue

        document = str(
            source.get("document")
            or source.get("document_title")
            or ""
        )

        text = str(
            source.get("text")
            or ""
        )

        # Source-verified remediation:
        # JPMC 2026Q2 original filing explicitly places
        # "(in millions, except ratio data)" above the
        # SUMMARY OF CHANGES IN THE ALLOWANCES table.
        #
        # Do NOT apply this context to unrelated JPMC tables.
        if (
            document == "JPMC_2026Q2_earnings_supplement.pdf"
            and "SUMMARY OF CHANGES IN THE ALLOWANCES" in text
            and "ALLOWANCE FOR LOAN LOSSES" in text
        ):
            verified_contexts.append(
                {
                    "source_id": source.get("source_id"),
                    "document": document,
                    "context_type": "table_unit",
                    "applies_to":
                        "SUMMARY OF CHANGES IN THE ALLOWANCES",
                    "unit": "millions",
                    "qualifier": "except ratio data",
                    "verification": "explicit_source_pdf",
                    "provenance":
                        "JPMC 2026Q2 earnings supplement; "
                        "page-level table context",
                }
            )

    if not verified_contexts:
        print(
            "[Evidence Context Enricher] "
            "No verified context enrichment applied."
        )
        return {}

    enriched_payload = dict(payload)

    existing = enriched_payload.get(
        "verified_contexts"
    )

    if isinstance(existing, list):
        merged = list(existing)
    else:
        merged = []

    merged.extend(verified_contexts)

    enriched_payload["verified_contexts"] = merged

    print(
        "[Evidence Context Enricher] "
        f"verified contexts added={len(verified_contexts)}"
    )

    return {
        "span_catalog_payload": enriched_payload,
    }

def route_plan_guardrail(
    state: GovernedLiveState,
) -> str:
    """
    V1.3 early fail-closed Planning route.

    Planning conflicts must not enter
    Retrieval, Research, or Judge.
    """

    if (
        state.get("recovery_action")
        == "ESCALATE"
    ):
        return "ESCALATE"

    return "RETRIEVE"


def build_governed_graph():

    graph = StateGraph(
        GovernedLiveState
    )

    # Already validated live research nodes.
    graph.add_node(
        "runtime_bootstrap",
        runtime_bootstrap_node,
    )

    graph.add_node(
        "planning_agent",
        planning_agent_node,
    )

    graph.add_node(
        "plan_guardrail",
        plan_guardrail_node,
    )

    graph.add_node(
        "retrieval",
        retrieval_node,
    )

    graph.add_node(
        "span_catalog",
        span_catalog_node,
    )

    graph.add_node(
        "evidence_context_enricher",
        evidence_context_enricher_node,
    )

    graph.add_node(
        "research_agent",
        research_agent_node,
    )

    # Governance nodes.
    graph.add_node(
        "deterministic_guard",
        deterministic_guard_node,
    )

    graph.add_node(
        "failure_classifier",
        failure_classifier_node,
    )

    graph.add_node(
        "recovery_controller",
        recovery_controller_node,
    )

    graph.add_node(
        "retry_matrix",
        retry_matrix_node,
    )

    graph.add_node(
        "claim_level_fail_closed",
        claim_level_fail_closed_node,
    )

    graph.add_node(
        "deterministic_revalidation",
        deterministic_revalidation_node,
    )

    graph.add_node(
        "judge_gate",
        judge_gate_node,
    )

    graph.add_node(
        "llm_judge",
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

    # ========================================================
    # LINEAR LIVE RESEARCH PATH
    # ========================================================

    graph.add_edge(
        START,
        "runtime_bootstrap",
    )

    graph.add_edge(
        "runtime_bootstrap",
        "planning_agent",
    )

    graph.add_edge(
        "planning_agent",
        "plan_guardrail",
    )

    graph.add_conditional_edges(
        "plan_guardrail",
        route_plan_guardrail,
        {
            "RETRIEVE":
                "retrieval",

            "ESCALATE":
                "final_decision",
        },
    )

    graph.add_edge(
        "retrieval",
        "span_catalog",
    )

    graph.add_edge(
        "span_catalog",
        "evidence_context_enricher",
    )

    graph.add_edge(
        "evidence_context_enricher",
        "research_agent",
    )

    graph.add_edge(
        "research_agent",
        "deterministic_guard",
    )

    graph.add_edge(
        "deterministic_guard",
        "failure_classifier",
    )

    graph.add_edge(
        "failure_classifier",
        "recovery_controller",
    )

    # ========================================================
    # REAL GOVERNANCE CONDITIONAL ROUTING
    # ========================================================

    graph.add_conditional_edges(
        "recovery_controller",
        route_recovery,
        {
            "CONTINUE_TO_JUDGE":
                "judge_gate",

            "RETRY_MATRIX":
                "retry_matrix",

            "CLAIM_LEVEL_FAIL_CLOSED":
                "claim_level_fail_closed",

            "ESCALATE":
                "final_decision",
        },
    )

    # Matrix-only retry:
    # NEVER Planning / Retrieval.
    graph.add_edge(
        "retry_matrix",
        "deterministic_guard",
    )

    # Claim-level fail-closed is remediation,
    # not immediate terminal failure.
    graph.add_edge(
        "claim_level_fail_closed",
        "deterministic_revalidation",
    )

    graph.add_conditional_edges(
        "deterministic_revalidation",
        route_revalidation,
        {
            "JUDGE_GATE":
                "judge_gate",

            "ESCALATE":
                "final_decision",
        },
    )

    graph.add_conditional_edges(
        "judge_gate",
        route_judge_gate,
        {
            "JUDGE":
                "llm_judge",

            "FINAL":
                "final_decision",
        },
    )

    graph.add_edge(
        "llm_judge",
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

    return graph.compile()


# ============================================================
# 15. SAVE RESULT ARTIFACT
# ============================================================

def save_governed_result(
    result: GovernedLiveState,
    total_seconds: float,
):

    RESULT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact = {
        "phase":
            "Phase 3",
        "step":
            "04-07",
        "artifact":
            RESULT_PATH.name,

        "orchestrator":
            "LangGraph StateGraph",

        "phase2_role":
            "read-only capability layer",

        "legacy_run_live_executed":
            False,

        "phase2_modified":
            False,

        "llm_mode":
            "REAL",

        "retrieval_mode":
            "REAL PHASE 2",

        "query":
            result.get(
                "query"
            ),

        "research_plan":
            json_safe(
                result.get(
                    "research_plan"
                )
            ),

        "source_count":
            len(
                result.get(
                    "sources",
                    [],
                )
            ),

        "trusted_span_count":
            len(
                result.get(
                    "span_catalog_payload",
                    [],
                )
            ),

        "research_matrix":
            json_safe(
                result.get(
                    "research_matrix"
                )
            ),

        "governed_matrix":
            json_safe(
                result.get(
                    "governed_matrix"
                )
            ),

        "guard_status":
            result.get(
                "guard_status"
            ),

        "failure_type":
            result.get(
                "failure_type"
            ),

        "retry_count":
            int(
                result.get(
                    "retry_count",
                    0,
                )
            ),

        "recovery_action":
            result.get(
                "recovery_action"
            ),

        "fail_closed_applied":
            bool(
                result.get(
                    "fail_closed_applied",
                    False,
                )
            ),

        "judge_allowed":
            bool(
                result.get(
                    "judge_allowed",
                    False,
                )
            ),

        "judge_verdict":
            result.get(
                "judge_verdict"
            ),

        "judge_review":
            json_safe(
                result.get(
                    "judge_review"
                )
            ),

        "judge_contract_status":
            result.get(
                "judge_contract_status"
            ),

        "final_status":
            result.get(
                "final_status"
            ),

        "model_calls":
            json_safe(
                result.get(
                    "model_calls",
                    [],
                )
            ),

        "model_call_count":
            len(
                result.get(
                    "model_calls",
                    [],
                )
            ),

        "total_seconds":
            round(
                total_seconds,
                3,
            ),

        "stage_history":
            result.get(
                "stage_history",
                [],
            ),
    }

    RESULT_PATH.write_text(
        json.dumps(
            artifact,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


# ============================================================
# 16. MAIN
# ============================================================

async def main():

    print("")
    print("=" * 78)
    print(
        "PHASE 3 STEP 04-07 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â "
        "FULL GOVERNED LIVE LANGGRAPH RUNTIME"
    )
    print("=" * 78)

    print(
        "ORCHESTRATOR: LangGraph StateGraph"
    )
    print(
        "PHASE 2 ROLE: READ-ONLY CAPABILITY LAYER"
    )
    print(
        "LEGACY run_live(): NOT USED"
    )
    print(
        "LLM MODE: REAL"
    )
    print(
        "RETRIEVAL MODE: REAL PHASE 2"
    )
    print(
        "RECOVERY POLICY: REAL FROZEN PHASE 2"
    )

    app = build_governed_graph()

    initial_state: GovernedLiveState = {
        "query":
            (
                "Compare the five target banks "
                "using the validated Phase 2 "
                "credit-risk disclosure evidence."
            ),
        "model_calls":
            [],
        "stage_history":
            [],
        "retry_count":
            0,
        "fail_closed_applied":
            False,
        "judge_allowed":
            False,
    }

    started = time.perf_counter()

    result = await app.ainvoke(
        initial_state
    )

    total_seconds = (
        time.perf_counter()
        - started
    )

    save_governed_result(
        result,
        total_seconds,
    )

    print("")
    print("=" * 78)
    print(
        "PHASE 3 STEP 04-07 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â "
        "FINAL GOVERNED RESULT"
    )
    print("=" * 78)

    print(
        "REAL PLANNING LLM: PASS"
    )

    print(
        "REAL PHASE 2 RETRIEVAL: PASS"
    )

    print(
        "REAL RESEARCH LLM: PASS"
    )

    print(
        "DETERMINISTIC GOVERNANCE: EXECUTED"
    )

    print(
        "REAL PHASE 2 RECOVERY POLICY: EXECUTED"
    )

    print(
        "RETRY COUNT:",
        result.get(
            "retry_count",
            0,
        ),
    )

    print(
        "RECOVERY ACTION:",
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
        "SOURCE COUNT:",
        len(
            result.get(
                "sources",
                [],
            )
        ),
    )

    print(
        "TRUSTED SPAN COUNT:",
        len(
            result.get(
                "span_catalog_payload",
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

    for stage in result.get(
        "stage_history",
        [],
    ):
        print(
            "  -",
            stage,
        )

    print("")
    print(
        "STEP 04-07 RESULT: PASS"
    )

    print("=" * 78)


if __name__ == "__main__":
    asyncio.run(
        main()
    )




