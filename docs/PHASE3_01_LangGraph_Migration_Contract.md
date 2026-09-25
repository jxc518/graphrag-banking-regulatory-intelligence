# Phase 3 — LangGraph Migration Contract

## Source Baseline

Phase 2 / V5 Frozen Validated Baseline — 2026-09-04

Status:

- CLOSED_PASS
- Definition of Done: 8/8 PASS
- Freeze Status: FROZEN_PASS

Canonical orchestration reference:

GraphRAG_Phase_02_SECTION_08_04_openai_governed_comparison.py

The Phase 2 baseline is READ ONLY.


## Migration Objective

Migrate the validated Phase 2 custom Python governed orchestrator
to an explicit LangGraph runtime while preserving validated
governance semantics.

Primary principle:

**Change the orchestration implementation, not the governance behavior.**


## Runtime Mapping

| Phase 2 Validated Component | Phase 3 LangGraph Component |
|---|---|
| Research Plan / Planning Agent | planning_agent_node |
| Plan Guardrail | plan_guardrail_node |
| Document-Scoped Retrieval | retrieval_node |
| Research Matrix / Research Agent | research_agent_node |
| Deterministic Guard | deterministic_guard_node |
| Failure Classifier | failure_classifier_node |
| Recovery Controller | recovery_router |
| Claim-Level Fail Closed | claim_level_fail_closed_node |
| Judge Gate | judge_gate_node |
| LLM Judge Review / Judge Agent | judge_agent_node |
| Judge Contract Guardrail | judge_contract_guardrail_node |
| Final Governed Decision | final_decision_node |


## Conditional Routing Contract

The following Phase 2 recovery actions must retain their
validated semantics:

CONTINUE_TO_JUDGE
    -> Judge Gate

RETRY_MATRIX
    -> Research Agent retry path

CLAIM_LEVEL_FAIL_CLOSED
    -> Claim-Level Fail Closed

ESCALATE
    -> Governed escalation path


## Bounded Recovery Contract

Maximum application-level contract retry:

1

A contract retry reruns the Research Matrix stage only.

Research Plan must NOT be rerun during contract recovery.

Retrieval must NOT be rerun during contract recovery.

Blind or unbounded retry is prohibited.


## Agent Contract

Phase 3 preserves three specialized LLM agent roles:

1. Planning Agent
2. Research / Evidence Synthesis Agent
3. Judge Agent

Governance components are NOT reclassified as LLM agents.


## Governance Contract

LangGraph migration must preserve:

- deterministic validation before semantic judging
- trusted evidence identifiers
- provenance validation
- field-to-evidence validation
- duplicate-span validation
- cross-bank evidence controls
- bounded recovery
- claim-level fail closed
- governed escalation
- Judge gating
- final governed decisioning


## Provider Contract

Validated providers remain:

- OpenAI
- DeepSeek

Provider adapters perform representation normalization only.

Provider adapters must NOT perform semantic repair.

Downstream governance remains provider-neutral.


## Observability Contract

LangSmith remains the trace-level observability layer.

Phase 3 LangGraph nodes should expose human-readable
runtime stage names that correspond to the validated
Phase 2 governance stages.


## Evidence Preservation Contract

Phase 2 frozen artifacts must not be overwritten,
renamed, or regenerated solely for the LangGraph migration.

All Phase 3 migration results must be written under:

GraphRAG_Phase3_LangGraph_Prod


## Migration Acceptance Criteria

The LangGraph migration is accepted only when:

1. The graph compiles successfully.
2. The executable topology can be rendered.
3. All three specialized agents are represented.
4. Conditional recovery routing is represented.
5. RETRY_MATRIX remains bounded to one application retry.
6. CLAIM_LEVEL_FAIL_CLOSED remains available.
7. ESCALATE remains available.
8. CONTINUE_TO_JUDGE reaches Judge Gate.
9. Deterministic controls remain before semantic Judge review.
10. Phase 2 governance regression behavior remains preserved.
11. LangSmith tracing remains operational.
12. Phase 2 frozen evidence remains unchanged.


## Non-Claims

Phase 2 did NOT use LangGraph runtime.

Phase 3 migration does not retroactively make Phase 2
a LangGraph implementation.

Three specialized agents do not imply exactly three
model calls.

A deterministic Guard PASS does not imply semantic
Judge approval.

A pending_review outcome is a valid governed outcome.


## Interview Summary

"I froze the validated Phase 2 baseline before changing the
workflow runtime. I then mapped the custom Python governed
state machine into LangGraph nodes, shared state, and
conditional transitions while preserving the validated
governance semantics."
