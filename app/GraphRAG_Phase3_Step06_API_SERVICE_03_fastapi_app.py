"""
GraphRAG Phase 3
Step 06 - API Service
Artifact 03 - FastAPI App
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


HERE = Path(__file__).resolve().parent

FACADE_PATH = (
    HERE
    / "GraphRAG_Phase3_Step06_API_SERVICE_02_runtime_facade.py"
)


def load_facade():
    if not FACADE_PATH.exists():
        raise FileNotFoundError(
            f"Runtime facade not found: {FACADE_PATH}"
        )

    spec = importlib.util.spec_from_file_location(
        "phase3_runtime_facade",
        FACADE_PATH,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Unable to load runtime facade: {FACADE_PATH}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


facade = load_facade()


app = FastAPI(
    title="Governed Multi-Agent GraphRAG API",
    description=(
        "Phase 3 production-oriented API service for the governed "
        "LangGraph + GraphRAG runtime."
    ),
    version="1.0.0",
)


# class QueryRequest(BaseModel):
#     query: str = Field(
#         ...,
#         min_length=3,
#         max_length=2000,
#         description="Banking / regulatory GraphRAG question.",
#     )
    
class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Banking / regulatory GraphRAG question.",
    )

    provider: str = Field(
        default="openai",
        description=(
            "Runtime LLM provider. "
            "Supported values: openai, deepseek."
        ),
    )


class QueryResponse(BaseModel):
    run_id: str
    query: str | None = None
    # answer: str | None = None
    answer: Any | None = None

    final_status: str | None = None
    guard_status: str | None = None
    failure_type: str | None = None
    recovery_action: str | None = None

    retry_count: int = 0
    fail_closed_applied: bool = False

    judge_allowed: bool = False
    judge_verdict: str | None = None

    latency_seconds: float

    stage_history: list[Any] = []
    model_calls: list[Any] = []

    runtime_state: dict[str, Any]


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(
        content=r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Jingru's Multi-Agent GraphRAG</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    color: #172033;
    background:
        radial-gradient(circle at 75% 12%, rgba(69,122,255,.12), transparent 28%),
        linear-gradient(180deg,#fbfdff 0%,#f5f8fc 100%);
}

a {
    color: inherit;
    text-decoration: none;
}

.page {
    max-width: 1180px;
    margin: auto;
    padding: 0 28px 60px;
}

/* ---------------- NAV ---------------- */

nav {
    height: 76px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #e9edf4;
}

.brand {
    display: flex;
    align-items: center;
    gap: 11px;
    font-size: 17px;
    font-weight: 700;
}

.brand-mark {
    width: 34px;
    height: 34px;
    border-radius: 10px;
    background: linear-gradient(135deg,#3855ff,#7b9cff);
    display: grid;
    place-items: center;
    color: white;
    font-size: 17px;
    box-shadow: 0 6px 20px rgba(62,91,255,.23);
}

.identity {
    font-size: 14px;
    color: #596377;
    padding: 9px 14px;
    border: 1px solid #dde4ef;
    border-radius: 999px;
    background: rgba(255,255,255,.7);
}

/* ---------------- HERO ---------------- */

.hero {
    text-align: center;
    padding: 72px 20px 34px;
}

.live-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 7px 12px;
    border-radius: 999px;
    background: #edf8f1;
    color: #207a46;
    font-weight: 700;
    font-size: 12px;
    margin-bottom: 17px;
}

.live-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #2db66d;
}

.project-id {
    width: fit-content;
    margin: 0 auto 17px;
    padding: 7px 13px;
    border: 1px solid #dce3f2;
    border-radius: 999px;
    background: rgba(255,255,255,.75);
    color: #60719a;
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .4px;
}

h1 {
    margin: 0;
    font-size: clamp(42px,6vw,68px);
    line-height: 1.02;
    letter-spacing: -2.7px;
    background: linear-gradient(90deg,#202949,#405ed8,#718dff);
    -webkit-background-clip: text;
    color: transparent;
}

.hero h2 {
    margin: 15px 0 12px;
    font-size: clamp(24px,3vw,34px);
    letter-spacing: -.8px;
    color: #566381;
}

.hero-description {
    max-width: 690px;
    margin: 0 auto;
    color: #758096;
    line-height: 1.7;
    font-size: 16px;
}

/* ---------------- SEARCH ---------------- */

.search-card {
    max-width: 910px;
    margin: 22px auto 0;
    background: rgba(255,255,255,.92);
    border: 1px solid #e1e7f0;
    border-radius: 22px;
    box-shadow: 0 18px 55px rgba(35,50,90,.10);
    padding: 18px;
}

.search-row {
    display: flex;
    gap: 10px;
    align-items: stretch;
}

textarea {
    flex: 1;
    resize: vertical;
    min-height: 84px;
    border: none;
    outline: none;
    font: inherit;
    font-size: 15px;
    color: #27324a;
    background: transparent;
    padding: 13px;
    line-height: 1.5;
}

button.ask {
    font-size: 24px;
    font-weight: 500;
    line-height: 1;
    width: 56px;
    min-width: 56px;
    border: none;
    border-radius: 15px;
    cursor: pointer;
    color: white;
    font-size: 22px;
    background: linear-gradient(135deg,#3858ff,#6b82ff);
    box-shadow: 0 7px 18px rgba(63,85,240,.25);
}

button.ask:hover {
    transform: translateY(-1px);
}

.mode-row {
    display: flex;
    gap: 9px;
    flex-wrap: wrap;
    padding: 8px 10px 2px;
    border-top: 1px solid #edf0f5;
}

.mode {
    font-size: 12px;
    font-weight: 700;
    color: #526079;
    background: #f5f7fb;
    border: 1px solid #e1e6ef;
    border-radius: 999px;
    padding: 7px 11px;
}

.mode.active {
    color: #3151d5;
    border-color: #cfd9ff;
    background: #eef2ff;
}

.mode.experimental {
    color: #7a688f;
    background: #f7f3fa;
}

/* ---------------- RESULT ---------------- */

#result {
    display: block;
    max-width: 910px;
    margin: 18px auto 0;
    background: white;
    border: 1px solid #e1e6ef;
    border-radius: 19px;
    box-shadow: 0 12px 35px rgba(35,50,90,.07);
    padding: 23px;
}

.result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 13px;
}

.result-title {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1.25px;
    color: #8892a4;
    font-weight: 800;
}

.status {
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
}

.status.approved {
    background: #eaf8ef;
    color: #217647;
}

.status.escalated {
    background: #fff2e8;
    color: #a55217;
}

.answer {
    font-size: 23px;
    line-height: 1.45;
    color: #1b2845;
    font-weight: 650;
    margin: 10px 0 21px;
}

.meta-grid {
    display: grid;
    grid-template-columns: repeat(4,1fr);
    gap: 10px;
}

.meta {
    border: 1px solid #e8edf4;
    background: #f8fafc;
    border-radius: 12px;
    padding: 11px;
}

.meta-label {
    color: #8a94a6;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .8px;
}

.meta-value {
    color: #344159;
    font-weight: 700;
    font-size: 12px;
    margin-top: 5px;
}

/* ---------------- EXAMPLES ---------------- */

.examples {
    text-align: center;
    margin: 17px 0 54px;
}

.examples-label {
    color: #9199aa;
    font-size: 12px;
    margin-right: 8px;
}

.example-button {
    border: none;
    background: transparent;
    color: #526079;
    font-size: 12px;
    cursor: pointer;
    padding: 5px 7px;
}

.example-button:hover {
    color: #3858dd;
}

/* ---------------- SECTIONS ---------------- */

.section-title {
    text-align: center;
    margin: 55px 0 24px;
}

.section-title h3 {
    margin: 0 0 7px;
    font-size: 26px;
    letter-spacing: -.7px;
}

.section-title p {
    color: #8a93a5;
    margin: 0;
    font-size: 14px;
}

.pipeline {
    display: grid;
    grid-template-columns: repeat(7,1fr);
    gap: 7px;
    align-items: center;
}

.pipe-node {
    min-height: 99px;
    padding: 13px 8px;
    background: white;
    border: 1px solid #e3e9f1;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 7px 20px rgba(35,50,90,.05);
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.pipe-icon {
    font-size: 22px;
    margin-bottom: 6px;
}

.pipe-name {
    font-size: 11px;
    font-weight: 800;
}

.pipe-sub {
    margin-top: 4px;
    font-size: 9px;
    color: #929bae;
}

.arrow {
    text-align: center;
    color: #9ba5b8;
}

.architecture {
    margin-top: 46px;
    display: grid;
    grid-template-columns: repeat(4,1fr);
    gap: 13px;
}

.arch-card {
    background: white;
    border: 1px solid #e3e9f1;
    border-radius: 15px;
    padding: 18px;
}

.arch-label {
    color: #8b95a7;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .8px;
}

.arch-value {
    margin-top: 7px;
    font-size: 15px;
    font-weight: 800;
}

.arch-detail {
    margin-top: 5px;
    font-size: 11px;
    color: #8993a5;
}

/* ---------------- STATUS ---------------- */

.system {
    margin-top: 45px;
    background: white;
    border: 1px solid #e3e9f1;
    border-radius: 18px;
    padding: 22px;
}

.system-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.system-head h3 {
    margin: 0;
    font-size: 18px;
}

.operational {
    color: #23804b;
    background: #edf8f1;
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 800;
}

.status-grid {
    margin-top: 17px;
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 11px;
}

.status-item {
    background: #f8fafc;
    border: 1px solid #edf0f4;
    border-radius: 12px;
    padding: 12px 13px;
    font-size: 12px;
}

.status-item strong {
    display: block;
    margin-bottom: 3px;
}

.status-item span {
    color: #778297;
}

/* ---------------- FOOTER ---------------- */

footer {
    text-align: center;
    color: #9aa3b3;
    font-size: 11px;
    margin-top: 44px;
}

/* ---------------- RESPONSIVE ---------------- */

@media(max-width:850px) {

    .pipeline {
        grid-template-columns: 1fr;
    }

    .arrow {
        transform: rotate(90deg);
    }

    .architecture,
    .meta-grid,
    .status-grid {
        grid-template-columns: 1fr 1fr;
    }
}

@media(max-width:600px) {

    nav {
        height: auto;
        padding: 17px 0;
        align-items: flex-start;
        gap: 12px;
    }

    .identity {
        font-size: 11px;
    }

    .hero {
        padding-top: 50px;
    }

    .architecture,
    .meta-grid,
    .status-grid {
        grid-template-columns: 1fr;
    }
}


.ask-arrow::before {
    content: "\2192";
    display: inline-block;
    font-size: 30px;
    font-weight: 400;
    line-height: 1;
    color: white;
    transform: translateY(-1px);
}

.provider-strategy {
    margin-top: 14px;
    padding-top: 13px;
    border-top: 1px solid #edf1f7;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.provider-label {
    margin-right: 3px;
    color: #8a96ad;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .6px;
    text-transform: uppercase;
}

.provider-chip {
    padding: 6px 10px;
    border: 1px solid #e0e6f0;
    border-radius: 999px;
    background: #f8f9fc;
    color: #65718a;
    font-size: 11px;
    font-weight: 700;
}

.provider-chip.openai {
    color: #344767;
}

.provider-chip.deepseek {
    color: #395bd8;
}

.provider-chip.active {
    border-color: #cbd8ff;
    background: #eef3ff;
    color: #3156d8;
    box-shadow: 0 3px 10px rgba(64, 96, 220, .08);
}

.provider-active-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    margin-right: 5px;
    border-radius: 50%;
    background: #2db66d;
}

.provider-detail {
    flex-basis: 100%;
    margin-top: 1px;
    color: #8b96aa;
    font-size: 10px;
}
</style>
</head>

<body>

<div class="page">

<nav>
    <div class="brand">
        <div class="brand-mark">G</div>
        <div>Jingru's Multi-Agent GraphRAG</div>
    </div>

    <div class="identity">
        Jingru Chen &nbsp;|&nbsp; AI &amp; Model Risk
    </div>
</nav>


<section class="hero">

    <div class="live-badge">
        <span class="live-dot"></span>
        Live on AWS
    </div>

    <div class="project-id">
        jingru.ai.multiagent.graphrag
    </div>

    <h1>Multi-Agent GraphRAG</h1>

    <h2>From Questions to Trusted Answers</h2>

    <p class="hero-description">
        Governed retrieval and multi-agent reasoning across Federal Reserve
        supervisory guidance and major U.S. bank financial disclosures.
    </p>


    <div class="search-card">

        <div class="search-row">

            <textarea
                id="question"
                placeholder="Ask about Fed SR Letters (SR 11-7, SR 21-8, SR 26-2) or 5 major U.S. banks (JPMC, WFC, BAC, Citi, Capital One)..."
            ></textarea>

            <button
                class="ask"
                id="askButton"
                onclick="submitQuery()"
                title="Ask GraphRAG"
            ><span class="ask-arrow"></span></button>

        </div>

        <div class="mode-row">

            <span
                id="localMode"
                class="mode active"
                onclick="setSearchMode('local')"
                style="cursor: pointer;"
            >
                Local Search
            </span>

            <span
                id="globalMode"
                class="mode experimental"
                onclick="setSearchMode('global')"
                style="cursor: pointer;"
            >
                Global Search - Experimental
            </span>

        </div>
        
<div class="provider-strategy">

    <span class="provider-label">
        Runtime Provider
    </span>

    <label class="provider-chip openai">
        <input
            type="radio"
            name="provider"
            value="openai"
            checked
            onchange="setProvider('openai')"
        >
        OpenAI GPT-4.1
    </label>

    <label class="provider-chip deepseek">
        <input
            type="radio"
            name="provider"
            value="deepseek"
            onchange="setProvider('deepseek')"
        >
        DeepSeek V4 Flash
    </label>

    <span class="provider-chip active">
        <span class="provider-active-dot"></span>
        Dual-Provider Enabled
    </span>

    <div class="provider-detail" id="providerDetail">
        Selected Provider: OpenAI GPT-4.1
        | Planning + Research + Judge
        | Deterministic Guardrails remain provider-independent
    </div>

</div>


<div style="
    margin-top: 16px;
    padding: 14px 16px;
    background: #f7f9ff;
    border: 1px solid #e2e7f5;
    border-radius: 12px;
    font-size: 13px;
    line-height: 1.55;
    color: #56627a;
">

    <strong style="color:#263552;">
        Demo Scope — Curated 23-Document Banking & Regulatory Corpus
    </strong>

    <div style="margin-top:6px;">
        This governed Multi-Agent GraphRAG prototype is grounded in
        23 public banking and regulatory documents covering
        JPMorgan Chase, Bank of America, Citigroup, Wells Fargo,
        Capital One, and Federal Reserve model-risk guidance.
        Financial-disclosure coverage is primarily 2025 Q3–2026 Q2.
    </div>

    <div style="margin-top:6px;">
        <strong>Best results:</strong>
        use the suggested questions or ask questions within the indexed corpus.
        Out-of-scope or insufficiently supported questions may return
        <strong>Pending Review</strong> or an insufficient-evidence result
        rather than an unsupported answer.
    </div>

</div>

    </div>

</section>


<section id="result">

    <div class="result-header">

        <div class="result-title">
            Governed Answer
        </div>

        <div id="statusBadge" class="status">
        </div>

    </div>

    <div id="answerText" class="answer">
        Run a Local Search to see the governed answer and governance results.
    </div>

    <div class="meta-grid">

        <div class="meta">
            <div class="meta-label">Guardrail</div>
            <div id="guardValue" class="meta-value">N/A</div>
        </div>

        <div class="meta">
            <div class="meta-label">Research</div>
            <div id="researchValue" class="meta-value">N/A</div>
        </div>

        <div class="meta">
            <div class="meta-label">Judge</div>
            <div id="judgeValue" class="meta-value">N/A</div>
        </div>

        <div class="meta">
            <div class="meta-label">Recovery</div>
            <div id="recoveryValue" class="meta-value">N/A</div>
        </div>

    </div>

</section>


<div class="examples">

    <span class="examples-label">
        Try:
    </span>

    <button class="example-button"
        onclick="useExample(`What was Wells Fargo's provision for credit losses for loans for the quarter ended June 30, 2026?`)">
        Wells Fargo credit-loss provision
    </button><span class="example-separator">|</span><button class="example-button"
        onclick="useExample(`What does SR Letter 11-7 say about model validation?`)">
        SR 11-7 model validation
    </button><span class="example-separator">|</span><button class="example-button"
        onclick="useExample(`What was Wells Fargo's net income in 2026?`)">
        Wells Fargo 2026 net income
    </button>

</div>


<div class="section-title">

    <h3>How It Works</h3>

    <p>
        Specialized agents collaborate through a governed GraphRAG workflow.
    </p>

</div>


<div class="pipeline">

    <div class="pipe-node">
        <div class="pipe-icon">1</div><div class="pipe-name">Your Question</div>
        <div class="pipe-sub">User query</div>
    </div>

    <div class="arrow">-&gt;</div>

    <div class="pipe-node">
        <div class="pipe-icon">2</div><div class="pipe-name">Planning Agent</div>
        <div class="pipe-sub">OpenAI GPT-4.1</div>
    </div>

    <div class="arrow">-&gt;</div>

    <div class="pipe-node">
        <div class="pipe-icon">3</div><div class="pipe-name">GraphRAG</div>
        <div class="pipe-sub">Evidence context</div>
    </div>

    <div class="arrow">-&gt;</div>

    <div class="pipe-node">
        <div class="pipe-icon">4</div><div class="pipe-name">Research Agent</div>
        <div class="pipe-sub">OpenAI GPT-4.1 - Primary</div>
    </div>

</div>


<div class="pipeline" style="margin-top:10px">

    <div class="pipe-node">
        <div class="pipe-icon">5</div><div class="pipe-name">Guardrails</div>
        <div class="pipe-sub">Evidence validation</div>
    </div>

    <div class="arrow">-&gt;</div>

    <div class="pipe-node">
        <div class="pipe-icon">6</div><div class="pipe-name">LLM Judge</div>
        <div class="pipe-sub">OpenAI GPT-4.1</div>
    </div>

    <div class="arrow">-&gt;</div>

    <div class="pipe-node">
        <div class="pipe-icon">7</div><div class="pipe-name">Governed Answer</div>
        <div class="pipe-sub">Approved or escalated</div>
    </div>

    <div></div>
    <div></div>

</div>


<div class="architecture">

    <div class="arch-card">
        <div class="arch-label">Planning Agent</div>
        <div class="arch-value">OpenAI GPT-4.1</div>
        <div class="arch-detail">
            Query planning and reasoning
        </div>
    </div>

    <div class="arch-card">
        <div class="arch-label">Research Agent</div>
        <div class="arch-value">OpenAI GPT-4.1 - Primary</div>
        <div class="arch-detail">
            Evidence-grounded research
        </div>
    </div>

    <div class="arch-card">
        <div class="arch-label">Guardrails</div>
        <div class="arch-value">Evidence Validation</div>
        <div class="arch-detail">
            Deterministic governance checks
        </div>
    </div>

    <div class="arch-card">
        <div class="arch-label">LLM Judge</div>
        <div class="arch-value">OpenAI GPT-4.1</div>
        <div class="arch-detail">
            Final governed review
        </div>
    </div>

</div>


<div class="system">

    <div class="system-head">

        <h3>Live System Status</h3>

        <div class="operational">
            AWS Deployed
        </div>

    </div>


    <div class="status-grid">

        <div class="status-item">
            <strong>AWS ECS</strong>
            <span>Live</span>
        </div>

        <div class="status-item">
            <strong>GraphRAG</strong>
            <span>Indexed evidence corpus</span>
        </div>

        <div class="status-item">
            <strong>Planning</strong>
            <span>OpenAI GPT-4.1</span>
        </div>

        <div class="status-item">
            <strong>Research</strong>
            <span>OpenAI GPT-4.1 - Primary</span>
        </div>

        <div class="status-item">
            <strong>Guardrails</strong>
            <span>Active</span>
        </div>

        <div class="status-item">
            <strong>Governance</strong>
            <span>Approve / Escalate</span>
        </div>

    </div>

</div>


<footer>
    Governed Multi-Agent GraphRAG | AWS ECS | LangGraph | OpenAI | DeepSeek
</footer>

</div>


<script>

let selectedProvider = "openai";

function setProvider(provider) {

    selectedProvider = provider;

    const detail =
        document.getElementById("providerDetail");

    if (provider === "deepseek") {
        detail.innerText =
            "Selected Provider: DeepSeek V4 Flash | Planning + Research + Judge | Deterministic Guardrails remain provider-independent";
    }
    else {
        detail.innerText =
            "Selected Provider: OpenAI GPT-4.1 | Planning + Research + Judge | Deterministic Guardrails remain provider-independent";
    }
}

function formatGovernedAnswer(answer) {

    if (!answer) {
        return null;
    }

    if (typeof answer === "string") {
        return answer;
    }

    if (answer.rows && Array.isArray(answer.rows)) {

        return answer.rows.map((row) => {

            const bank =
                row.bank || "Bank";

            const metric =
                row.metric || "Metric";

            const period =
                row.period || "N/A";

            const value =
                row.value ?? "N/A";

            const unit =
                row.unit || "";

            const scope =
                row.scope || "";

            const status =
                row.status || "";

            const evidenceCount =
                Array.isArray(row.evidence)
                ? row.evidence.length
                : 0;

            return [
                bank,
                "",
                `Metric: ${metric}`,
                `Period: ${period}`,
                `Value: ${value}${unit ? " " + unit : ""}`,
                scope ? `Scope: ${scope}` : "",
                status ? `Evidence Status: ${status}` : "",
                `Supporting Evidence: ${evidenceCount} span${evidenceCount === 1 ? "" : "s"}`
            ]
            .filter(Boolean)
            .join("\n");

        }).join("\n\n------------------------------\n\n");
    }

    return JSON.stringify(answer, null, 2);
}

function useExample(question) {

    document.getElementById("question").value = question;

}


function providerForStage(modelCalls, stageName) {

    if (!Array.isArray(modelCalls)) {
        return "N/A";
    }

    const call = modelCalls.find(
        x => x.stage === stageName
    );

    if (!call) {
        return "N/A";
    }

    const provider = call.provider || "";
    const model = call.returned_model || "";

    if (provider && model) {
        return `${provider} | ${model}`;
    }

    return provider || model || "N/A";
}


let searchMode = "local";


function setSearchMode(mode) {

    searchMode =
        mode === "global"
        ? "global"
        : "local";

    const localMode =
        document.getElementById("localMode");

    const globalMode =
        document.getElementById("globalMode");

    if (searchMode === "local") {

        localMode.className =
            "mode active";

        globalMode.className =
            "mode experimental";

    }
    else {

        localMode.className =
            "mode";

        globalMode.className =
            "mode experimental active";

    }
}


async function submitQuery() {

    const question =
        document.getElementById("question").value.trim();

    if (!question) {
        return;
    }

    const button =
        document.getElementById("askButton");

    const result =
        document.getElementById("result");

    const answerText =
        document.getElementById("answerText");

    button.disabled = true;
    button.innerHTML = '<span class="ask-arrow"></span>';

    result.style.display = "block";

    answerText.innerText =
        searchMode === "global"
        ? "Running experimental GraphRAG Global Search..."
        : "Running governed multi-agent GraphRAG...";

    document.getElementById("guardValue").innerText = "-";
    document.getElementById("researchValue").innerText = "-";
    document.getElementById("judgeValue").innerText = "-";
    document.getElementById("recoveryValue").innerText = "-";

    try {

        const endpoint =
            searchMode === "global"
            ? "/global-query"
            : "/query";

        const response = await fetch(
            endpoint,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                
                body: JSON.stringify({
                    query: question,
                    provider: selectedProvider
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {

            const detail =
                typeof data.detail === "string"
                ? data.detail
                : (
                    data.detail
                    ? JSON.stringify(data.detail)
                    : `HTTP ${response.status}`
                );

            throw new Error(detail);
        }


        // ----------------------------------------------------
        // GLOBAL SEARCH - EXPERIMENTAL RESPONSE
        // ----------------------------------------------------

        if (searchMode === "global") {

            const badge =
                document.getElementById("statusBadge");

            badge.innerText =
                "EXPERIMENTAL";

            badge.className =
                "status escalated";

            answerText.innerText =
                data.answer ||
                "No Global Search answer was returned.";

            document.getElementById(
                "guardValue"
            ).innerText =
                "N/A - Experimental";

            document.getElementById(
                "researchValue"
            ).innerText =
                "GraphRAG Global Search";

            document.getElementById(
                "judgeValue"
            ).innerText =
                "N/A - Experimental";

            document.getElementById(
                "recoveryValue"
            ).innerText =
                "N/A";

            result.scrollIntoView({
                behavior: "smooth",
                block: "nearest"
            });

            return;
        }


        // ----------------------------------------------------
        // LOCAL SEARCH - EXISTING GOVERNED PATH
        // ----------------------------------------------------

        const status =
            data.final_status || "UNKNOWN";

        const badge =
            document.getElementById("statusBadge");

        badge.innerText = status;

        badge.className =
            "status " +
            (
                status === "APPROVED"
                ? "approved"
                : "escalated"
            );

            
        const formattedAnswer =
            formatGovernedAnswer(data.answer);

        answerText.innerText =
            formattedAnswer ||
            (
                status === "ESCALATED"
                ? "The system escalated this query because the governed evidence requirements were not satisfied."
                : status === "PENDING_REVIEW"
                ? "The answer requires additional evidence review before approval."
                : "No governed answer was returned."
            );

        document.getElementById("guardValue").innerText =
            data.guard_status || "N/A";

        document.getElementById("researchValue").innerText =
            providerForStage(
                data.model_calls,
                "research_matrix_attempt_0"
            );

        document.getElementById("judgeValue").innerText =
            data.judge_verdict
            ? `${selectedProvider === "deepseek" ? "DeepSeek" : "OpenAI"} | ${data.judge_verdict}`
            : (
                data.judge_allowed === false
                ? "Not reached"
                : "N/A"
            );

        document.getElementById("recoveryValue").innerText =
            data.recovery_action || "N/A";

        result.scrollIntoView({
            behavior: "smooth",
            block: "nearest"
        });

    }
    catch (error) {

        const badge =
            document.getElementById("statusBadge");

        badge.innerText = "ERROR";
        badge.className = "status escalated";

        answerText.innerText =
            `Request failed: ${error.message}`;

    }
    finally {

        button.disabled = false;
        button.innerHTML = '<span class="ask-arrow"></span>';

    }
}


document
    .getElementById("question")
    .addEventListener(
        "keydown",
        function(event) {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {
                event.preventDefault();
                submitQuery();
            }

        }
    );

</script>

</body>
</html>
"""
    )


@app.get("/health")
async def health():
    info = facade.runtime_info()

    return {
        "status": "healthy",
        **info,
    }


@app.post(
    "/query",
    response_model=QueryResponse,
)
async def query_graph(
    request: QueryRequest,
):
    """
    Execute one governed GraphRAG query.

    Important:
    APPROVED, ESCALATED, and PENDING_REVIEW are valid
    governance/business outcomes and therefore return HTTP 200.

    Infrastructure/runtime failures return HTTP 500.
    """

    try:
        # result = await facade.run_governed_query(
        #     request.query
        # )
        
        result = await facade.run_governed_query(
            request.query,
            request.provider,
        )

        # runtime_state = result.get("runtime_state") or {}
        # governed_rows = runtime_state.get("governed_rows") or []

        # answer = None

        # if (
        #     result.get("final_status") == "APPROVED"
        #     and governed_rows
        # ):
        #     row = governed_rows[0]

        #     bank = row.get("bank")
        #     metric = row.get("metric")
        #     period = row.get("period")
        #     value = row.get("value")
        #     unit = row.get("unit")

        #     if all([bank, metric, period, value, unit]):
        #         display_value = str(value)

        #         unit_text = str(unit).strip().lower()

        #         if "million" in unit_text:
        #             display_value = f"${display_value} million"
        #         elif "billion" in unit_text:
        #             display_value = f"${display_value} billion"
        #         else:
        #             display_value = f"{display_value} {unit}"

        #         answer = (
        #             f"{bank}'s {metric} for {period} was "
        #             f"{display_value}."
        #         )

        # result["answer"] = answer

        return QueryResponse(**result)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "runtime_failure",
                "message": str(exc),
            },
        ) from exc

# ============================================================
# GLOBAL SEARCH - EXPERIMENTAL
# ============================================================
#
# This endpoint is intentionally separate from /query.
#
# /query:
#     governed Local Search through the existing LangGraph runtime
#
# /global-query:
#     experimental Microsoft GraphRAG Global Search
#
# V1 does not claim that Global Search passes through the same
# governed LangGraph decision pipeline as Local Search.
# ============================================================


@app.post("/global-query")
async def global_query(request: QueryRequest):

    import time as _time
    from fastapi import HTTPException as _HTTPException

    from GraphRAG_Phase3_Step06_API_SERVICE_16_global_search_adapter import (
        run_global_query,
    )

    started = _time.perf_counter()

    try:

        answer = await run_global_query(
            request.query
        )

        latency_seconds = (
            _time.perf_counter() - started
        )

        return {
            "search_method": "global",
            "status": "experimental",
            "query": request.query,
            "answer": answer,
            "latency_seconds": round(
                latency_seconds,
                4,
            ),
        }

    except ValueError as exc:

        raise _HTTPException(
            status_code=422,
            detail={
                "error": "invalid_global_query",
                "message": str(exc),
            },
        ) from exc

    except Exception as exc:

        raise _HTTPException(
            status_code=500,
            detail={
                "error": "global_search_runtime_failure",
                "message": str(exc),
            },
        ) from exc


