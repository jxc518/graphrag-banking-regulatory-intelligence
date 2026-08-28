# ============================================================
# GRAPHRAG PHASE 1 — BANKING REGULATORY INTELLIGENCE
# PROFESSIONAL UI DEVELOPMENT VERSION
# ============================================================

from pathlib import Path
import html
import time

import streamlit as st

from runtime_guardrails_phase_1 import (
    run_runtime_guardrailed_graphrag,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Banking Regulatory Intelligence | Jingru Chen",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONSTANTS
# ============================================================

APP_NAME = "Banking Regulatory Intelligence"
APP_PHASE = "GraphRAG Phase 1"
DEVELOPER_NAME = "Jingru Chen"
KNOWLEDGE_BASE_SIZE = 23

BASE_DIR = Path(__file__).resolve().parent
README_PATH = BASE_DIR / "README.md"


# ============================================================
# PROFESSIONAL UI THEME
# ============================================================

st.markdown(
    """
    <style>
    /* --------------------------------------------------------
       GLOBAL
       -------------------------------------------------------- */

    .stApp {
        background:
            radial-gradient(circle at 88% 4%, rgba(56, 116, 156, 0.08), transparent 23rem),
            radial-gradient(circle at 22% 0%, rgba(23, 63, 95, 0.05), transparent 18rem);
    }

    .block-container {
        max-width: 1320px;
        padding-top: 2.0rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        letter-spacing: -0.02em;
    }

    hr {
        border-color: rgba(125, 143, 163, 0.18);
    }

    /* --------------------------------------------------------
       HERO
       -------------------------------------------------------- */

    .hero-shell {
        position: relative;
        overflow: hidden;
        padding: 2.0rem 2.2rem 1.85rem 2.2rem;
        margin-bottom: 1.55rem;
        border: 1px solid rgba(180, 193, 207, 0.55);
        border-radius: 18px;
        background:
            linear-gradient(
                135deg,
                rgba(248, 251, 253, 0.96) 0%,
                rgba(241, 247, 251, 0.90) 100%
            );
        box-shadow: 0 12px 34px rgba(29, 53, 78, 0.06);
    }

    .hero-shell:after {
        content: "";
        position: absolute;
        width: 270px;
        height: 270px;
        right: -95px;
        top: -125px;
        border-radius: 50%;
        background: rgba(23, 63, 95, 0.055);
    }

    .eyebrow {
        position: relative;
        z-index: 1;
        margin-bottom: 0.65rem;
        font-size: 0.77rem;
        font-weight: 750;
        letter-spacing: 0.13em;
        text-transform: uppercase;
        color: #526d82;
    }

    .main-title {
        position: relative;
        z-index: 1;
        margin-bottom: 0.65rem;
        max-width: 900px;
        font-size: clamp(2.3rem, 4vw, 3.35rem);
        line-height: 1.05;
        font-weight: 780;
        letter-spacing: -0.045em;
        color: #102a43;
    }

    .subtitle {
        position: relative;
        z-index: 1;
        max-width: 900px;
        margin-bottom: 0.9rem;
        font-size: 1.08rem;
        line-height: 1.65;
        color: #4d6274;
    }

    .developer-line {
        position: relative;
        z-index: 1;
        margin-bottom: 1.25rem;
        font-size: 0.86rem;
        font-weight: 550;
        color: #728295;
    }

    .capability-row {
        position: relative;
        z-index: 1;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .capability-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.39rem 0.72rem;
        border: 1px solid #d7e0e8;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.78);
        font-size: 0.78rem;
        font-weight: 650;
        color: #36536b;
    }

    /* --------------------------------------------------------
       SECTION TYPOGRAPHY
       -------------------------------------------------------- */

    .section-kicker {
        margin-top: 1.4rem;
        margin-bottom: 0.18rem;
        font-size: 0.75rem;
        font-weight: 750;
        letter-spacing: 0.11em;
        text-transform: uppercase;
        color: #627d98;
    }

    .section-title {
        margin-bottom: 0.7rem;
        font-size: 1.44rem;
        font-weight: 750;
        color: #102a43;
    }

    .section-copy {
        margin-bottom: 0.9rem;
        max-width: 850px;
        color: #617489;
        line-height: 1.55;
        font-size: 0.93rem;
    }

    /* --------------------------------------------------------
       SEARCH WORKSPACE
       -------------------------------------------------------- */

    .workspace-shell {
        margin-top: 0.25rem;
        margin-bottom: 0.35rem;
        padding: 1.15rem 1.3rem 0.3rem 1.3rem;
        border: 1px solid #dfe7ee;
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.66);
        box-shadow: 0 8px 24px rgba(29, 53, 78, 0.035);
    }

    .mode-note {
        margin: 0.20rem 0 0.85rem 0;
        padding: 0.72rem 0.85rem;
        border-left: 3px solid #507ca1;
        border-radius: 6px;
        background: rgba(240, 246, 250, 0.76);
        color: #496276;
        font-size: 0.88rem;
        line-height: 1.45;
    }

    .global-note {
        border-left-color: #aa7a22;
        background: rgba(252, 248, 238, 0.82);
    }

    /* --------------------------------------------------------
       BUTTONS
       -------------------------------------------------------- */

    div.stButton > button[kind="primary"] {
        min-height: 3.05rem;
        border: 1px solid #173f5f;
        border-radius: 9px;
        background: #173f5f;
        box-shadow: 0 4px 12px rgba(23, 63, 95, 0.16);
        font-weight: 700;
        letter-spacing: 0.01em;
        transition: all 0.15s ease-in-out;
    }

    div.stButton > button[kind="primary"]:hover {
        border-color: #102f49;
        background: #102f49;
        box-shadow: 0 6px 16px rgba(23, 63, 95, 0.22);
        transform: translateY(-1px);
    }

    div.stButton > button:not([kind="primary"]) {
        border-radius: 8px;
    }

    /* --------------------------------------------------------
       INPUTS
       -------------------------------------------------------- */

    div[data-baseweb="textarea"] textarea {
        border-radius: 9px;
        line-height: 1.58;
    }

    div[data-baseweb="select"] > div {
        border-radius: 9px;
    }

    div[role="radiogroup"] {
        gap: 0.55rem;
    }

    /* --------------------------------------------------------
       METRIC CARDS
       -------------------------------------------------------- */

    div[data-testid="stMetric"] {
        min-height: 116px;
        padding: 1rem 1.05rem;
        border: 1px solid #e0e7ee;
        border-radius: 12px;
        background: rgba(250, 252, 253, 0.92);
        box-shadow: 0 5px 16px rgba(29, 53, 78, 0.035);
    }

    div[data-testid="stMetricLabel"] {
        font-weight: 650;
        color: #657a8d;
    }

    div[data-testid="stMetricValue"] {
        color: #173f5f;
    }

    /* --------------------------------------------------------
       RESULT / GOVERNANCE
       -------------------------------------------------------- */

    .result-heading {
        margin-top: 0.3rem;
        margin-bottom: 0.25rem;
        font-size: 1.55rem;
        font-weight: 760;
        color: #102a43;
    }

    .result-subheading {
        margin-bottom: 1rem;
        color: #6b7f91;
        font-size: 0.9rem;
    }

    .status-banner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin: 0.65rem 0 1.0rem 0;
        padding: 0.85rem 1rem;
        border: 1px solid;
        border-radius: 10px;
        font-size: 0.93rem;
        font-weight: 650;
    }

    .status-pass {
        border-color: #b9dec7;
        background: #eff9f2;
        color: #27613b;
    }

    .status-warn {
        border-color: #ead39a;
        background: #fff9e9;
        color: #815f10;
    }

    .status-block {
        border-color: #e5b9b9;
        background: #fff0f0;
        color: #873636;
    }

    .response-shell {
        margin-top: 0.9rem;
        margin-bottom: 1.1rem;
        padding: 0.35rem 0 0.2rem 0;
    }

    .governance-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 0.25rem 0 0.9rem 0;
    }

    .governance-chip {
        padding: 0.38rem 0.68rem;
        border: 1px solid #dce4ea;
        border-radius: 999px;
        background: #f8fafc;
        font-size: 0.78rem;
        font-weight: 650;
        color: #51687b;
    }

    .governance-pass {
        border-color: #b9dec7;
        background: #eff9f2;
        color: #27613b;
    }

    .governance-warn {
        border-color: #ead39a;
        background: #fff9e9;
        color: #815f10;
    }

    .governance-block {
        border-color: #e5b9b9;
        background: #fff0f0;
        color: #873636;
    }

    .governance-neutral {
        border-color: #dce4ea;
        background: #f8fafc;
        color: #51687b;
    }

    /* --------------------------------------------------------
       EXPANDERS
       -------------------------------------------------------- */

    div[data-testid="stExpander"] {
        overflow: hidden;
        border: 1px solid #e1e8ee;
        border-radius: 9px;
        background: rgba(255, 255, 255, 0.56);
    }

    /* --------------------------------------------------------
       SIDEBAR
       -------------------------------------------------------- */

    section[data-testid="stSidebar"] {
        border-right: 1px solid #e1e7ed;
        background: rgba(248, 250, 252, 0.98);
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.55rem;
    }

    .sidebar-brand {
        margin-bottom: 0.25rem;
        font-size: 1.12rem;
        line-height: 1.2;
        font-weight: 780;
        color: #102a43;
    }

    .sidebar-phase {
        margin-bottom: 0.85rem;
        font-size: 0.78rem;
        font-weight: 650;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #6f8191;
    }

    .sidebar-copy {
        margin-bottom: 0.45rem;
        color: #627488;
        font-size: 0.85rem;
        line-height: 1.48;
    }

    .sidebar-label {
        margin-top: 0.8rem;
        margin-bottom: 0.35rem;
        font-size: 0.71rem;
        font-weight: 760;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        color: #7b8d9d;
    }

    .sidebar-status {
        margin-bottom: 0.42rem;
        padding: 0.55rem 0.66rem;
        border: 1px solid #dfe7ed;
        border-radius: 8px;
        background: #ffffff;
        color: #4c6274;
        font-size: 0.80rem;
    }

    /* --------------------------------------------------------
       FOOTER
       -------------------------------------------------------- */

    .footer-note {
        padding-top: 0.35rem;
        text-align: center;
        color: #8190a0;
        font-size: 0.78rem;
        line-height: 1.5;
    }

    @media (max-width: 900px) {
        .hero-shell {
            padding: 1.45rem 1.3rem 1.35rem 1.3rem;
        }

        .main-title {
            font-size: 2.25rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def status_css_class(status: str) -> str:
    """Map guardrail status to a presentation class."""
    status = (status or "").upper()

    if status == "PASS":
        return "status-pass"

    if status == "WARN":
        return "status-warn"

    return "status-block"


def safe_status(stage_result) -> str:
    """Return a stable status string for a guardrail stage."""
    if stage_result is None:
        return "NOT RUN"

    return getattr(stage_result, "status", "UNKNOWN")


def governance_chip_class(stage_result) -> str:
    """Map a guardrail stage status to a semantic governance-chip class."""
    status = safe_status(stage_result).upper()

    if status == "PASS":
        return "governance-pass"

    if status == "WARN":
        return "governance-warn"

    if status == "BLOCK":
        return "governance-block"

    return "governance-neutral"


def render_stage(stage_name: str, stage_result) -> None:
    """Render one compact guardrail stage inside technical details."""
    if stage_result is None:
        st.markdown(f"**{stage_name}: NOT RUN**")
        return

    st.markdown(
        f"**{stage_name}: {getattr(stage_result, 'status', 'UNKNOWN')}**"
    )

    for reason in getattr(stage_result, "reasons", []) or []:
        st.caption(reason)



# ============================================================
# HIRING-MANAGER LANDING PAGE + LIVE DEMO
# ============================================================

st.markdown(
    """
    <style>
    /* --------------------------------------------------------
       HIRING-MANAGER LANDING LAYER
       -------------------------------------------------------- */

    .trust-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin: -0.45rem 0 1.15rem 0;
    }

    .trust-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.40rem 0.70rem;
        border: 1px solid #d9e3eb;
        border-radius: 999px;
        background: rgba(255,255,255,0.78);
        color: #526b7e;
        font-size: 0.78rem;
        font-weight: 650;
    }

    .landing-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1rem;
        margin: 0.5rem 0 1.35rem 0;
    }

    .landing-card {
        min-height: 250px;
        padding: 1.15rem 1.18rem;
        border: 1px solid #dfe7ee;
        border-radius: 14px;
        background: rgba(255,255,255,0.80);
        box-shadow: 0 8px 24px rgba(29,53,78,0.04);
    }

    .landing-card-kicker {
        margin-bottom: 0.65rem;
        font-size: 0.72rem;
        font-weight: 780;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: #6b8093;
    }

    .landing-card-title {
        margin-bottom: 0.62rem;
        font-size: 1.08rem;
        line-height: 1.35;
        font-weight: 760;
        color: #16344d;
    }

    .landing-card-copy {
        min-height: 86px;
        color: #607488;
        font-size: 0.88rem;
        line-height: 1.55;
    }

    .landing-metric-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.42rem;
        margin-top: 0.90rem;
    }

    .landing-metric {
        padding: 0.31rem 0.52rem;
        border: 1px solid #dce5ec;
        border-radius: 7px;
        background: #f7fafc;
        color: #486276;
        font-size: 0.75rem;
        font-weight: 650;
    }

    .landing-metric.pass {
        border-color: #b9dfca;
        background: #eef9f2;
        color: #16663a;
    }

    .landing-metric.warn {
        border-color: #edd397;
        background: #fff8e7;
        color: #8a5b00;
    }

    .landing-metric.block {
        border-color: #efb5b5;
        background: #fff0f0;
        color: #9f2f2f;
    }

    .architecture-shell {
        margin: 0.45rem 0 1.35rem 0;
        padding: 1.15rem 1.25rem;
        border: 1px solid #dfe7ee;
        border-radius: 14px;
        background: rgba(255,255,255,0.72);
    }

    .architecture-flow {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 0.7rem;
        align-items: stretch;
    }

    .architecture-step {
        padding: 0.82rem 0.72rem;
        border-radius: 10px;
        background: #f5f8fb;
        border: 1px solid #e0e7ee;
        text-align: center;
    }

    .architecture-step strong {
        display: block;
        color: #183a55;
        margin-bottom: 0.28rem;
        font-size: 0.84rem;
    }

    .architecture-step span {
        color: #6c7f90;
        font-size: 0.74rem;
        line-height: 1.35;
    }

    .proof-shell {
        margin: 0.45rem 0 1.25rem 0;
        padding: 1.05rem 1.2rem;
        border-left: 4px solid #173f5f;
        border-radius: 10px;
        background: rgba(242,247,251,0.90);
    }

    .proof-title {
        margin-bottom: 0.35rem;
        color: #153750;
        font-size: 0.98rem;
        font-weight: 760;
    }

    .proof-copy {
        color: #586f82;
        font-size: 0.88rem;
        line-height: 1.55;
    }

    .live-demo-note {
        margin: 0.25rem 0 1.15rem 0;
        padding: 0.85rem 0.95rem;
        border: 1px solid #dce6ee;
        border-radius: 10px;
        background: rgba(248,251,253,0.85);
        color: #536d81;
        font-size: 0.86rem;
        line-height: 1.5;
    }

    @media (max-width: 980px) {
        .landing-grid {
            grid-template-columns: 1fr;
        }

        .architecture-flow {
            grid-template-columns: 1fr;
        }

        .landing-card {
            min-height: auto;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION NAVIGATION
# ============================================================

def set_portfolio_view(view: str):
    """Update navigation before widgets are instantiated on rerun."""
    st.session_state["sidebar_portfolio_navigation"] = view


if "sidebar_portfolio_navigation" not in st.session_state:
    st.session_state["sidebar_portfolio_navigation"] = "Overview"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-brand">{APP_NAME}</div>
        <div class="sidebar-phase">{APP_PHASE}</div>
        <div class="sidebar-copy">
            A banking and regulatory intelligence proof-of-concept
            focused on evidence-grounded AI and runtime governance.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-label">Portfolio Navigation</div>',
        unsafe_allow_html=True,
    )

    sidebar_view = st.radio(
        "Portfolio Navigation",
        ["Overview", "Live Demo"],
        label_visibility="collapsed",
        key="sidebar_portfolio_navigation",
    )

    st.divider()

    st.markdown(
        '<div class="sidebar-label">System</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sidebar-status">● Knowledge Base &nbsp; {KNOWLEDGE_BASE_SIZE} documents</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-status">● Search &nbsp; Local + Global</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-status">● Guardrails &nbsp; Active</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown(
        '<div class="sidebar-label">Search Architecture</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**Local Search**")
    st.caption(
        "Focused evidence retrieval for institutions, regulatory topics, "
        "risk questions, and named entities."
    )

    st.markdown("**Global Search**")
    st.caption(
        "Cross-document and community-level synthesis. "
        "More compute-intensive than Local Search."
    )

    st.divider()

    st.markdown(
        '<div class="sidebar-label">Governance Controls</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Input security • scope validation • prompt-injection screening • "
        "citation validation • grounding • sensitive-data screening • "
        "output controls • audit logging"
    )

    st.divider()

    with st.expander("About This PoC", expanded=False):
        try:
            readme_content = README_PATH.read_text(encoding="utf-8")
            st.markdown(readme_content)
        except FileNotFoundError:
            st.warning("Project documentation is currently unavailable.")

    st.caption(
        "Designed for banking, risk, regulatory, compliance, "
        "and AI governance use cases."
    )


# ============================================================
# SHARED HERO
# ============================================================

hero_html = (
    f'<div class="hero-shell">'
    f'<div class="eyebrow">BANKING AI • GRAPHRAG • GOVERNANCE</div>'
    f'<div class="main-title">Banking Regulatory Intelligence</div>'
    f'<div class="subtitle">'
    f'An evidence-grounded AI research system for regulatory guidance and major U.S. bank disclosures — '
    f'combining Microsoft GraphRAG retrieval, citation validation, and runtime AI governance.'
    f'</div>'
    f'<div class="developer-line">{APP_PHASE} • Developed by {DEVELOPER_NAME}</div>'
    f'<div class="capability-row">'
    f'<span class="capability-pill">{KNOWLEDGE_BASE_SIZE}-Document Knowledge Base</span>'
    f'<span class="capability-pill">Local + Global Search</span>'
    f'<span class="capability-pill">Evidence Grounding</span>'
    f'<span class="capability-pill">Citation Validation</span>'
    f'<span class="capability-pill">Runtime Guardrails</span>'
    f'<span class="capability-pill">Audit Logging</span>'
    f'</div>'
    f'</div>'
)

st.markdown(hero_html, unsafe_allow_html=True)


# ============================================================
# OVERVIEW / LANDING PAGE
# ============================================================

if sidebar_view == "Overview":

    st.markdown(
        """
        <div class="trust-strip">
            <span class="trust-pill">No sign-in required</span>
            <span class="trust-pill">Public-source research corpus</span>
            <span class="trust-pill">Read-only portfolio demonstration</span>
            <span class="trust-pill">Guardrailed AI responses</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    intro_left, intro_right = st.columns([1.5, 1.0], gap="large")

    with intro_left:
        st.markdown(
            """
            <div class="section-kicker">What This Demonstrates</div>
            <div class="section-title">From regulatory documents to governed AI answers</div>
            <div class="section-copy">
                This Phase 1 proof-of-concept shows how a banking research workflow can connect
                knowledge-graph retrieval, cross-document synthesis, evidence tracing, and
                runtime controls in one auditable application.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with intro_right:
        st.markdown(
            """
            <div class="proof-shell">
                <div class="proof-title">Designed for a 30–60 second review</div>
                <div class="proof-copy">
                    Review validated examples first. Launch the interactive GraphRAG workspace
                    only if you want to explore the system directly.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    featured_html = (
        '<div class="section-kicker">Featured Results</div>'
        '<div class="section-title">Validated Phase 1 behaviors</div>'
        '<div class="section-copy">'
        'These examples summarize observed runs from the current proof-of-concept and show '
        'supported retrieval, safe failure, and long-form cross-document synthesis.'
        '</div>'
        '<div class="landing-grid">'
            '<div class="landing-card">'
                '<div class="landing-card-kicker">Supported Regulatory Research</div>'
                '<div class="landing-card-title">What is model risk management guidance?</div>'
                '<div class="landing-card-copy">'
                    'Focused Local Search returned an evidence-grounded regulatory explanation '
                    'with citations and all runtime controls passing.'
                '</div>'
                '<div class="landing-metric-row">'
                    '<span class="landing-metric pass">PASS</span>'
                    '<span class="landing-metric">Local Search</span>'
                    '<span class="landing-metric">18.3 sec</span>'
                    '<span class="landing-metric">48 evidence refs</span>'
                '</div>'
            '</div>'
            '<div class="landing-card">'
                '<div class="landing-card-kicker">Runtime AI Governance</div>'
                '<div class="landing-card-title">Prompt-injection attempt blocked before retrieval</div>'
                '<div class="landing-card-copy">'
                    'A request to bypass instructions and obtain customer account numbers was '
                    'blocked at Input Security. Downstream controls were correctly marked NOT RUN.'
                '</div>'
                '<div class="landing-metric-row">'
                    '<span class="landing-metric block">BLOCK</span>'
                    '<span class="landing-metric">Early termination</span>'
                    '<span class="landing-metric">0.0 sec</span>'
                    '<span class="landing-metric">0 evidence refs</span>'
                '</div>'
            '</div>'
            '<div class="landing-card">'
                '<div class="landing-card-kicker">Cross-Document Synthesis</div>'
                '<div class="landing-card-title">Model-risk principles across regulatory guidance</div>'
                '<div class="landing-card-copy">'
                    'Global Search completed a community-level synthesis with extensive evidence. '
                    'The measured latency also exposed a production optimization requirement.'
                '</div>'
                '<div class="landing-metric-row">'
                    '<span class="landing-metric warn">WARN</span>'
                    '<span class="landing-metric">Global Search</span>'
                    '<span class="landing-metric">3113.7 sec</span>'
                    '<span class="landing-metric">154 evidence refs</span>'
                '</div>'
            '</div>'
        '</div>'
    )
    st.markdown(featured_html, unsafe_allow_html=True)

    architecture_html = (
        '<div class="section-kicker">Architecture</div>'
        '<div class="section-title">Evidence before confidence</div>'
        '<div class="section-copy">'
        'The application treats retrieval and governance as one runtime workflow rather than '
        'presenting an unverified LLM answer.'
        '</div>'
        '<div class="architecture-shell">'
            '<div class="architecture-flow">'
                '<div class="architecture-step">'
                    '<strong>1. User Query</strong>'
                    '<span>Banking, risk, regulatory, or comparative research question</span>'
                '</div>'
                '<div class="architecture-step">'
                    '<strong>2. Input Guardrail</strong>'
                    '<span>Prompt-injection and unsafe-request screening</span>'
                '</div>'
                '<div class="architecture-step">'
                    '<strong>3. GraphRAG Retrieval</strong>'
                    '<span>Local focused retrieval or Global community synthesis</span>'
                '</div>'
                '<div class="architecture-step">'
                    '<strong>4. Evidence Validation</strong>'
                    '<span>Citation-to-evidence, grounding, and sensitive-data checks</span>'
                '</div>'
                '<div class="architecture-step">'
                    '<strong>5. Governed Output</strong>'
                    '<span>PASS, WARN, or BLOCK with audit-ready runtime trace</span>'
                '</div>'
            '</div>'
        '</div>'
    )
    st.markdown(architecture_html, unsafe_allow_html=True)

    value_left, value_right = st.columns(2, gap="large")

    with value_left:
        st.markdown(
            """
            <div class="section-kicker">Engineering Focus</div>
            <div class="section-title">What Phase 1 proves</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            - End-to-end Microsoft GraphRAG retrieval over banking and regulatory documents
            - Local and Global search paths with evidence references
            - Citation validation and grounding checks
            - Prompt-injection defense with early termination
            - Sensitive-data and output controls
            - Runtime decisioning and audit logging
            """
        )

    with value_right:
        st.markdown(
            """
            <div class="section-kicker">Known Findings</div>
            <div class="section-title">What Phase 1 intentionally exposes</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            - Regulatory identifier / alias discoverability gaps
            - Uneven retrieval in multi-entity comparative questions
            - Need for evidence-completeness checks before cross-bank ranking
            - High Global Search latency and the need for caching / asynchronous execution
            - Importance of distinguishing safe abstention from retrieval failure
            """
        )

    st.markdown(
        """
        <div class="live-demo-note">
            <strong>Interactive demo note.</strong>
            Local Search is the recommended live experience and typically completes much faster.
            Global Search is intentionally available for architecture validation, but measured Phase 1
            runs can take substantially longer because of community-level synthesis.
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 1.2, 1])

    with c2:
        st.button(
            "Launch Interactive GraphRAG Demo",
            type="primary",
            use_container_width=True,
            key="launch_live_demo",
            on_click=set_portfolio_view,
            args=("Live Demo",),
        )


# ============================================================
# LIVE DEMO
# ============================================================

else:

    top_left, top_right = st.columns([1.0, 4.0], gap="medium")

    with top_left:
        st.button(
            "← Overview",
            use_container_width=True,
            key="return_overview",
            on_click=set_portfolio_view,
            args=("Overview",),
        )

    with top_right:
        st.markdown(
            """
            <div class="live-demo-note">
                <strong>Live Research Workspace.</strong>
                Ask a question from the indexed banking and regulatory knowledge base.
                Local Search is recommended for interactive review; Global Search is substantially
                more compute-intensive and may take much longer.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ========================================================
    # SEARCH WORKSPACE
    # ========================================================

    st.markdown(
        """
        <div class="section-kicker">Research Workspace</div>
        <div class="section-title">Ask a banking or regulatory question</div>
        <div class="section-copy">
            Select the retrieval strategy that best matches the analytical task.
            Local Search is optimized for focused evidence; Global Search is designed
            for broader synthesis across the knowledge base.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_search, col_scope = st.columns([1.05, 2.25], gap="large")

    with col_search:
        search_method = st.radio(
            "Search Strategy",
            [
                "Local Search",
                "Global Search",
            ],
            index=0,
            horizontal=False,
            key="live_search_method",
        )

    with col_scope:
        if search_method == "Local Search":
            st.markdown(
                """
                <div class="mode-note">
                    <strong>Focused retrieval.</strong>
                    Best for named institutions, risk topics, regulatory guidance,
                    and questions that should be answered from targeted graph evidence.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="mode-note global-note">
                    <strong>Cross-document synthesis.</strong>
                    Best for themes, comparisons, and community-level analysis.
                    Global Search is substantially more compute-intensive and can
                    require considerably more time.
                </div>
                """,
                unsafe_allow_html=True,
            )

    method_map = {
        "Local Search": "local",
        "Global Search": "global",
    }

    selected_method = method_map[search_method]

    sample_questions = {
        "Select an example...": "",
        "Citigroup Overview":
            "What is Citigroup and what are its major business segments?",
        "Model Risk Management":
            "What is model risk management guidance?",
        "Credit Risk Comparison":
            "Compare credit risk disclosures across Citigroup and JPMorgan Chase.",
        "Capital & Regulatory Themes":
            "What are the major regulatory capital themes across the banks?",
        "Cross-Bank Q2 2026 Comparison":
            "Compare Wells Fargo, Citigroup, and Bank of America in Q2 2026 across revenue, "
            "net income, credit quality, capital, and loan performance. Which bank performed "
            "strongest overall based on the available evidence?",
    }

    selected_example = st.selectbox(
        "Example Research Questions",
        list(sample_questions.keys()),
        key="live_example_question",
    )

    default_query = sample_questions[selected_example]

    user_query = st.text_area(
        "Question",
        value=default_query,
        height=130,
        placeholder=(
            "Ask about banking institutions, credit risk, capital, "
            "regulatory guidance, model risk, or related topics..."
        ),
        key="live_user_query",
    )

    run_query = st.button(
        "Run Analysis",
        type="primary",
        use_container_width=True,
        key="live_run_analysis",
    )

    # ========================================================
    # EXECUTION
    # ========================================================

    if run_query:
        if not user_query.strip():
            st.warning("Please enter a question.")
            st.stop()

        progress_message = (
            "Running Local Search..."
            if selected_method == "local"
            else
            "Running Global Search. "
            "This broader analysis may take considerably longer..."
        )

        with st.spinner(progress_message):
            try:
                start = time.perf_counter()

                result = run_runtime_guardrailed_graphrag(
                    query=user_query,
                    method=selected_method,
                )

                ui_latency = time.perf_counter() - start

            except Exception as exc:
                st.error(
                    "The GraphRAG request could not be completed."
                )

                with st.expander("Technical Error Details"):
                    st.exception(exc)

                st.stop()

        final_status = result["final_result"].status
        status_class = status_css_class(final_status)

        citation_info = (
            result.get("citation_info")
            or {}
        )

        evidence_count = citation_info.get(
            "evidence_count",
            0,
        )

        st.divider()

        st.markdown(
            """
            <div class="section-kicker">Analysis Result</div>
            <div class="result-heading">Evidence-Grounded Intelligence</div>
            <div class="result-subheading">
                Retrieval output evaluated by the runtime guardrail pipeline.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="status-banner {status_class}">
                <span>Runtime Guardrail Decision</span>
                <span>{html.escape(str(final_status))}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4 = st.columns(4, gap="medium")

        m1.metric(
            "Search Mode",
            search_method,
        )

        m2.metric(
            "Guardrail Decision",
            final_status,
        )

        m3.metric(
            "Runtime Pipeline",
            f"{result['pipeline_latency_seconds']:.1f} sec",
        )

        m4.metric(
            "Evidence References",
            evidence_count,
        )

        st.markdown(
            """
            <div class="section-kicker">Executive Response</div>
            <div class="section-title">Evidence-Grounded Answer</div>
            """,
            unsafe_allow_html=True,
        )

        if (
            final_status != "BLOCK"
            and result.get("answer")
        ):
            st.markdown(
                '<div class="response-shell">',
                unsafe_allow_html=True,
            )

            st.markdown(result["answer"])

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        else:
            st.error(
                "The response was withheld by the runtime guardrail pipeline."
            )

        st.markdown(
            """
            <div class="section-kicker">Evidence & Governance</div>
            <div class="section-title">Runtime Control Summary</div>
            <div class="section-copy">
                The application evaluates retrieval evidence, citation support,
                grounding, sensitive-data exposure, and output-release controls
                before presenting the final response.
            </div>
            """,
            unsafe_allow_html=True,
        )

        stage_items = [
            (
                "Input Security",
                result.get("input_result"),
            ),
            (
                "Domain / Scope",
                result.get("scope_result"),
            ),
            (
                "Indirect Injection",
                result.get("indirect_injection_result"),
            ),
            (
                "Citation Validation",
                result.get("citation_validation_result"),
            ),
            (
                "Grounding",
                result.get("grounding_result"),
            ),
            (
                "Sensitive Data",
                result.get("sensitive_data_result"),
            ),
            (
                "Output Control",
                result.get("output_result"),
            ),
        ]

        chip_html = "".join(
            (
                f'<span class="governance-chip {governance_chip_class(stage_result)}">'
                f'{html.escape(stage_name)}: '
                f'{html.escape(safe_status(stage_result))}'
                "</span>"
            )
            for stage_name, stage_result in stage_items
        )

        st.markdown(
            f'<div class="governance-strip">{chip_html}</div>',
            unsafe_allow_html=True,
        )

        with st.expander(
            "Guardrail Decision Details",
            expanded=False,
        ):
            reasons = (
                getattr(
                    result["final_result"],
                    "reasons",
                    [],
                )
                or []
            )

            if reasons:
                for reason in reasons:
                    st.write("•", reason)
            else:
                st.caption(
                    "No additional final-decision reason was returned."
                )

        with st.expander(
            "Runtime Guardrail Control Matrix",
            expanded=False,
        ):
            for stage_name, stage_result in stage_items:
                render_stage(
                    stage_name,
                    stage_result,
                )

        if citation_info:
            with st.expander(
                "Citation & Evidence Trace",
                expanded=False,
            ):
                ev1, ev2, ev3 = st.columns(3)

                ev1.metric(
                    "Citations Present",
                    str(
                        citation_info.get(
                            "citations_present",
                            False,
                        )
                    ),
                )

                citation_types = citation_info.get(
                    "citation_types",
                    [],
                )

                if isinstance(citation_types, (list, tuple, set)):
                    citation_type_display = ", ".join(
                        str(item)
                        for item in citation_types
                    ) or "None"
                else:
                    citation_type_display = str(
                        citation_types or "None"
                    )

                ev2.metric(
                    "Citation Types",
                    citation_type_display,
                )

                ev3.metric(
                    "Evidence References",
                    evidence_count,
                )

                st.markdown("**Technical evidence details**")

                st.json(
                    citation_info.get(
                        "details",
                        {},
                    )
                )

        with st.expander(
            "Runtime Diagnostics",
            expanded=False,
        ):
            st.write(
                "**UI request elapsed time:**",
                f"{ui_latency:.1f} sec",
            )

            st.caption(
                "UI elapsed time is measured by the Streamlit application "
                "around the runtime guardrail call. The pipeline metric above "
                "is reported by the underlying runtime pipeline."
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    f"""
    <div class="footer-note">
        {APP_PHASE} • Banking Regulatory Intelligence • Evidence-Grounded AI Governance<br>
        Developed by {DEVELOPER_NAME}
    </div>
    """,
    unsafe_allow_html=True,
)
