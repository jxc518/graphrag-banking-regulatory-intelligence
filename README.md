# Banking Regulatory Intelligence - GraphRAG Phase 1

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
