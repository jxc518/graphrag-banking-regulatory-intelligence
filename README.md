# Governed Multi-Agent GraphRAG for Banking Regulatory Intelligence — Phase 2 (AWS V1)

A production-oriented AI engineering portfolio demonstrating the evolution from Microsoft GraphRAG retrieval into a governed LangGraph-based multi-agent architecture deployed on AWS for banking and regulatory intelligence.

## 🚀 Phase 2 (AWS V1) — Governed Multi-Agent GraphRAG

**Status:** DEPLOYED  
**Runtime:** LangGraph  
**Cloud:** AWS ECS  
**Primary LLM:** OpenAI GPT-4.1  
**Secondary Provider:** DeepSeek  
**Retrieval:** Microsoft GraphRAG  
**Governance:** Guardrails + LLM Judge + Recovery / Human Review

**Phase 2 status: COMPLETE (2026-09-07)**

### Live Application

**[Launch the AWS Governed Multi-Agent GraphRAG Demo](https://ji-6283b0637f924ce6848d5fc3fca854aa.ecs.us-east-1.on.aws)**  

**AWS Public Endpoint:** https://ji-6283b0637f924ce6848d5fc3fca854aa.ecs.us-east-1.on.aws

### What AWS V1 Demonstrates

- Governed LangGraph-based multi-agent orchestration.
- Microsoft GraphRAG integration for banking and regulatory intelligence.
- Specialized planning, research, evidence-validation, guardrail, judge,
  recovery, and human-review workflow.
- OpenAI GPT-4.1 primary model with DeepSeek secondary-provider architecture.
- Evidence-grounded answers with explicit governance decisions.
- Guardrail and independent LLM-judge evaluation.
- Retry, recovery, escalation, and human-review controls.
- Dockerized deployment through Amazon ECR and Amazon ECS.
- Public FastAPI-based recruiter-facing AWS application.
- Local Search validated end-to-end on AWS.
- GraphRAG Global Search validated for corpus-wide synthesis and exposed
  as an experimental capability in V1.

## AWS V1 Architecture

```text
Browser
  ↓
AWS Public Application
  ↓
FastAPI
  ↓
LangGraph Governed Multi-Agent Runtime
  ↓
Planner / Research / Evidence Validation
  ↓
Microsoft GraphRAG
  ↓
Local Search / Experimental Global Search
  ↓
OpenAI GPT-4.1 + DeepSeek Secondary Provider
  ↓
Guardrails
  ↓
LLM Judge
  ↓
Recovery / Escalation / Human Review
  ↓
Governed Answer
```


### LangGraph Governed Multi-Agent Workflow

The LangGraph runtime orchestrates planning, retrieval, research, deterministic guardrails, failure classification, recovery, retry/escalation, independent LLM judging, and final governed decisioning.

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
    __start__([<p>__start__</p>]):::first
    planning(planning)
    plan_guardrail(plan_guardrail)
    retrieval(retrieval)
    research(research)
    deterministic_guard(deterministic_guard)
    failure_classifier(failure_classifier)
    recovery_controller(recovery_controller)
    retry_matrix(retry_matrix)
    retry_guard(retry_guard)
    claim_level_fail_closed(claim_level_fail_closed)
    judge_gate(judge_gate)
    judge(judge)
    judge_contract_guardrail(judge_contract_guardrail)
    final_decision(final_decision)
    __end__([<p>__end__</p>]):::last

    __start__ --> planning;
    planning --> plan_guardrail;
    plan_guardrail --> retrieval;
    retrieval --> research;
    research --> deterministic_guard;
    deterministic_guard --> failure_classifier;
    failure_classifier --> recovery_controller;

    recovery_controller -.-> claim_level_fail_closed;
    recovery_controller -. &nbsp;continue_to_judge&nbsp; .-> judge_gate;
    recovery_controller -.-> retry_matrix;
    recovery_controller -. &nbsp;escalate&nbsp; .-> final_decision;

    claim_level_fail_closed --> judge_gate;
    retry_matrix --> retry_guard;
    retry_guard --> judge_gate;

    judge_gate --> judge;
    judge --> judge_contract_guardrail;
    judge_contract_guardrail --> final_decision;
    final_decision --> __end__;

    classDef default fill:#f2f0ff,line-height:1.2
    classDef first fill-opacity:0
    classDef last fill:#bfb6fc
```


---

# Banking Regulatory Intelligence - GraphRAG Phase 1

> **Phase 1 — Historical Foundation:** Original Microsoft GraphRAG proof-of-concept that established the retrieval, evidence-grounding, citation-validation, and guardrail foundation later extended into the governed multi-agent AWS architecture above.

A public portfolio proof-of-concept for evidence-grounded banking and regulatory research using Microsoft GraphRAG, citation validation, runtime guardrails, and auditable AI responses.

**Phase 1 status: COMPLETE (2026-08-28)**

Public demo: https://banking-graphrag-jingru.streamlit.app

## What Phase 1 Demonstrates

- 23-document public banking/regulatory knowledge base.
- Microsoft GraphRAG indexing with entities, relationships, communities, community reports, text units, and embeddings.
- Basic Search as a traditional RAG-style baseline.
- Local Search for focused graph-enhanced entity/context retrieval.
- Global Search for corpus-wide community-level synthesis.
- Evidence references, citation-to-evidence validation, grounding checks, runtime guardrails, and audit logging.
- Public Streamlit deployment with query-length, per-session, and Global Search cooldown controls.

## Runtime Architecture

`User Query -> Input Guardrail -> GraphRAG Retrieval -> Evidence Validation -> Governed Output`

Runtime controls include prompt-injection screening, domain/scope checks, indirect prompt-injection checks, citation validation, grounding, sensitive banking/PII checks, output controls, and audit logging. Outputs can be PASS, WARN, or BLOCK; WARN/BLOCK states are preserved rather than suppressed for presentation.

## Phase 1 Evidence

The screenshots below document representative observed behavior from the deployed GraphRAG Phase 1 system, including graph-enhanced retrieval, runtime governance behavior, and corpus-wide Global Search synthesis.

### 1. Local Search — Graph-Enhanced Retrieval

The following example demonstrates graph-enhanced focused retrieval for a model risk management question. The system returns evidence-grounded output and independently evaluates citation support through the runtime guardrail pipeline.

**Query**

![Local Search Query](docs/images/_01_local_search_1_A_query_20260828.png)

**Result**

![Local Search Result](docs/images/_01_local_search_1_B_results_20260828.png)

**Runtime Guardrail Evaluation**

![Local Search Guardrail](docs/images/_01_local_search_1_C_guardrail_20260828.png)

The observed run returned a WARN because the citation-validation layer identified cited claims that may not be fully supported by the associated evidence. The warning is intentionally preserved rather than suppressed.

### 2. Local Search — Runtime Governance / Prompt-Injection Scenario

This example demonstrates runtime behavior when the system receives a request attempting to override instructions and obtain customer account information.

**Query**

![Prompt Injection Query](docs/images/_02_local_search_2_A_prompt_injection_query_20260828.png)

**Result**

![Prompt Injection Result](docs/images/_02_local_search_2_B_prompt_injection_results_20260828.png)

**Runtime Guardrail Evaluation**

![Prompt Injection Guardrail](docs/images/_02_local_search_2_C_prompt_injection_guardrail_20260828.png)

The system did not disclose customer account information. The runtime governance layer also surfaced scope, evidence, grounding, citation, and output-control warnings rather than presenting the response as fully evidence-supported.

### 3. Global Search — Cross-Document Synthesis

The following example demonstrates corpus-wide community-level synthesis across major U.S. bank disclosures and regulatory guidance for model risk management.

**Query**

![Global Search Query](docs/images/_03_global_search_1_A_query_20260828.png)

**Result**

![Global Search Result](docs/images/_03_global_search_1_B_results_20260828.png)

**Runtime Guardrail Evaluation**

![Global Search Guardrail](docs/images/_03_global_search_1_C_guardrail_20260828.png)

The public Global Search completed successfully with broad evidence coverage. Citation validation independently flagged a subset of cited claims as potentially insufficiently supported, producing an intentional WARN rather than suppressing the governance signal.

## Final Public Benchmark

| Search mode | Runtime | Evidence references | Guardrail |
|---|---:|---:|---|
| Basic | 23.9 sec | 21 | PASS |
| Local | 25.6 sec | 55 | PASS |
| Global | 527.7 sec (~8.80 min) | 180 | WARN |

The Global benchmark used a cross-document model-risk-management comparison across major U.S. banks and regulatory guidance. The public Global run completed successfully, while citation validation independently flagged 8 of 36 parsed cited claims as potentially insufficiently supported. The WARN is intentional governance behavior.

## Global Search Optimization

Global Search latency was reduced from roughly 52 minutes to 8.6-8.8 minutes through:

1. Community-level tuning to level 1.
2. Dynamic community selection.
3. Query-time model throughput tuning to 60,000 TPM / 20 RPM.

The local optimized benchmark was 8.61 minutes; the public-cloud run was 527.7 seconds (~8.80 minutes), an approximately 83% reduction from the original run. The underlying indexed corpus was not changed. Phase 1 does not claim statistically equivalent quality across configurations; controlled quality/cost benchmarking belongs to Phase 2/V5.

## Public Cost and Abuse Controls

- Maximum query length: 500 characters.
- Basic/Local: maximum 10 successful runs per session.
- Global: maximum 2 successful runs per session.
- Global cooldown: 10 minutes.
- Failed backend executions do not consume the successful-run counters.

These are portfolio-PoC session controls, not a substitute for distributed production rate limiting or provider-side budget protection.

## Known Findings

- Regulatory identifier / alias discoverability gaps, including exact identifiers such as SR 11-7.
- Uneven retrieval coverage in multi-entity comparative questions.
- Need for evidence-completeness checks before cross-bank ranking.
- Global Search remains compute-intensive and would benefit from caching, precomputation, and asynchronous execution at production scale.
- Safe abstention must be distinguished from retrieval failure.
- Provider compatibility requires behavioral testing, not only API connectivity; alternate-provider experiments exposed structured-output and intermittent request/JSON failure modes.

## Phase 1 Evaluation Boundary

Phase 1 proves end-to-end viability and demonstrates representative retrieval, grounding, guardrail, deployment, latency, and engineering behavior. It is qualitative/demo-oriented. It does **not** claim that a retrieval mode, model provider, chunking strategy, threshold, or architecture is statistically optimal.

Systematic benchmark datasets, quantitative retrieval metrics, provider comparisons, failure-rate measurement, task-level routing, and controlled quality/cost experiments belong to Phase 2/V5.

## Technology

- Microsoft GraphRAG 3.1.1
- Python 3.11
- OpenAI GPT-4.1
- text-embedding-3-large
- Streamlit Community Cloud
- Pandas / PyArrow / LanceDB-backed GraphRAG artifacts

## Project Closure

GraphRAG Phase 1 was frozen as complete on 2026-08-28 after deployment, public Basic/Local/Global smoke tests, guardrail validation, Global Search optimization, Git final QC, and public visual QC.

The next workstream is **GraphRAG Phase 1 Interview Defense**: architecture, core code, retrieval trade-offs, guardrails, evaluation boundaries, debugging lessons, latency/cost optimization, and productionization. No additional Phase 1 feature development is planned unless a demonstrated defect requires correction.

## Developer :  Jingru Chen @ chen.jingru@gmail.com

GraphRAG Phase 1 — Banking & Regulatory Intelligence PoC
