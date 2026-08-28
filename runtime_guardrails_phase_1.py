#------------------------------------------------------------------------------------
#
#  Code: runtime_guardrails_phase_1.py
#
#  Objective: Step 01 - 11 for GraphRAG - V4 POC - OpenAI 
#
#  Developer: Jingru Chen
#  Date:      2026-08-27
#
#-----------------------------------------------------------------------------------

# Priority     Next Step                                          Reason
# 1            Unified pipeline                                  Turn separate guardrail layers into one integrated runtime system
# 2            Real GraphRAG answer test                          Move from synthetic testing to real integration
# 3            Automatic citation detection                      Eliminate manually supplied citations_present=True
# 4            Out-of-scope / abstention                         Test hallucination-prevention behavior
# 5            Audit logging                                     Support banking governance, debugging, and monitoring
# 6            Long-query / malformed-query                      Test input robustness
# 7            Indirect prompt injection in retrieved text       Address RAG-specific retrieved-context risks
# 8            Citation mismatch                                 Detect citations that exist but do not support the claim
# 9            PII / sensitive banking data patterns             Strengthen financial-data governance
# 10           False-positive tests                              Ensure normal regulatory questions are not incorrectly blocked

# Step 11 — Runtime Guardrail Pipeline Integration
#
# Objective:
# Ensure that every real user query—whether from a notebook, API, or public
# website—passes through the same runtime guardrail pipeline rather than
# requiring Steps 1–10 to be executed manually and independently.
#
# The individual guardrail components already exist. Step 11 integrates
# them into one unified runtime pipeline.
#
# Target architecture:

# User Query
#    ↓
# [1] Input Guardrail
#    │ BLOCK → Do not run GraphRAG
#    ↓
# [2] Real GraphRAG Query
#    │ Failure → BLOCK
#    ↓
# [3] Citation Detection
#    ↓
# [4] Scope / Abstention
#    ↓
# [5] Indirect Injection Check
#    ↓
# [6] Citation-to-Evidence Validation
#    ↓
# [7] Grounding Guardrail
#    ↓
# [8] PII / Sensitive Banking Data
#    ↓
# [9] Output Guardrail
#    ↓
# [10] Final Decision
#    ↓
# [11] Audit Log
#    ↓
# Safe Answer / WARN / BLOCK


# Step 1: Establish a unified GuardrailResult format
#
# Create and run the first notebook cell to confirm there are no errors.
#
# Recommended function order

# 1. Imports
# 2. Constants / paths

# 3. GuardrailResult

# 4. input_guardrail

# 5. run_graphrag_query

# 6. domain_scope_check
# 7. out_of_scope_guardrail

# 8. grounding_guardrail

# 9. output_guardrail

# 10. detect_indirect_prompt_injection
# 11. indirect_prompt_injection_guardrail

# 12. detect_graphrag_citations

# 13. normalize_text
# 14. citation_support_check
# 15. extract_numbers
# 16. numeric_citation_check
# 17. parse_claims_with_citations
# 18. get_entity_evidence
# 19. get_report_evidence
# 19A. get_source_evidence()          ← NEW
# 19B. get_relationship_evidence()   ← NEW
# 20. evaluate_claim_support

# 21. detect_sensitive_banking_data
# 22. sensitive_banking_data_guardrail

# 23. load evidence parquet files
#     entities_df
#     reports_df

# 24. validate_real_graphrag_citations
# 25. citation_validation_guardrail

# 26. aggregate_guardrail_results

# 27. write_guardrail_audit_log

# 28. run_runtime_guardrailed_graphrag

# 29. print_runtime_guardrail_report

# ============================================================
# 01. IMPORTS
# ============================================================

import os
import re
import json
import time
import uuid
import subprocess
import pandas as pd

from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional


# ============================================================
# 02. CONFIGURATION / PATHS
# ============================================================

# ------------------------------------------------------------
# MODULE LOCATION
# ------------------------------------------------------------
# Directory containing runtime_guardrails_phase_1.py
#
# This makes paths portable for:
# - Local Windows development
# - Streamlit / public deployment
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent


# ------------------------------------------------------------
# GRAPHRAG ROOT
# ------------------------------------------------------------
#
# IMPORTANT:
# Use ONE GraphRAG root for both:
#
#   1. GraphRAG query execution
#   2. Citation evidence parquet loading
#
# Environment variable takes priority.
#
# For LOCAL development:
# set GRAPHRAG_ROOT_PATH to your real GraphRAG project root.
#
# For PUBLIC deployment:
# ./graphrag_project will be used unless the environment
# variable overrides it.
# ------------------------------------------------------------

# ============================================================
# GraphRAG project root configuration
# ============================================================

# Public/cloud deployment bundle stored inside this repository.
DEFAULT_GRAPHRAG_ROOT = BASE_DIR / "graphrag_project_online"

# Optional override for local development or alternate deployment.
# Example:
#   GRAPHRAG_ROOT_PATH=C:\path\to\your\graphrag_project
ENV_GRAPHRAG_ROOT = os.getenv("GRAPHRAG_ROOT_PATH")

if ENV_GRAPHRAG_ROOT:
    GRAPHRAG_ROOT = Path(
        ENV_GRAPHRAG_ROOT
    ).expanduser().resolve()
else:
    GRAPHRAG_ROOT = (
        DEFAULT_GRAPHRAG_ROOT
    ).resolve()


# ------------------------------------------------------------
# GRAPHRAG OUTPUT
# ------------------------------------------------------------
#
# IMPORTANT:
# Output MUST come from the SAME GraphRAG root used by query.
# ------------------------------------------------------------

GRAPHRAG_OUTPUT_DIR = (
    GRAPHRAG_ROOT
    / "output"
)


# ------------------------------------------------------------
# AUDIT LOG
# ------------------------------------------------------------

AUDIT_LOG_FILE = (
    BASE_DIR
    / "guardrail_audit_log.jsonl"
)


# ------------------------------------------------------------
# PATH QC
# ------------------------------------------------------------

def validate_runtime_paths():
    """
    Validate GraphRAG runtime paths before the application
    begins serving queries.
    """

    required_paths = {

        "GraphRAG root":
            GRAPHRAG_ROOT,

        "GraphRAG output":
            GRAPHRAG_OUTPUT_DIR,

        "Entities parquet":
            GRAPHRAG_OUTPUT_DIR
            / "entities.parquet",

        "Community reports parquet":
            GRAPHRAG_OUTPUT_DIR
            / "community_reports.parquet"
    }

    missing_paths = []

    for name, path in required_paths.items():

        if not path.exists():

            missing_paths.append(
                f"{name}: {path}"
            )


    if missing_paths:

        raise FileNotFoundError(
            "\nGraphRAG runtime path validation failed:\n"
            + "\n".join(
                f" - {x}"
                for x in missing_paths
            )
        )


    return True


# ============================================================
# 03. GUARDRAIL RESULT
# ============================================================

@dataclass
class GuardrailResult:

    stage: str

    status: str
    # PASS / WARN / BLOCK

    reasons: List[str]

    score: float = 0.0

    cleaned_text: Optional[str] = None


    def to_dict(self):

        return asdict(self)


# ============================================================
# OPTIONAL STANDALONE QC
# ============================================================
#
# This QC runs ONLY when this Python file is executed directly:
#
#     python runtime_guardrails_phase_1.py
#
# It will NOT run when Streamlit imports the module:
#
#     from runtime_guardrails_phase_1 import ...
#
# ============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "V4 GUARDRAIL — "
        "GuardrailResult QC"
    )

    print("=" * 70)


    try:

        test_result = GuardrailResult(

            stage="QC_TEST",

            status="PASS",

            reasons=[],

            score=1.0,

            cleaned_text="QC test"
        )


        print(
            "GuardrailResult class : LOADED"
        )

        print(
            "Dataclass test        : PASS"
        )

        print(
            "to_dict() test        :",
            test_result.to_dict()
        )

        print(
            "STEP 1 RESULT         : PASS"
        )


    except Exception as e:

        print(
            "GuardrailResult class : ERROR"
        )

        print(
            "STEP 1 RESULT         : FAIL"
        )

        print(
            "ERROR                 :",
            str(e)
        )


    print("=" * 70)
    


#-----------------------------04. input_guardrail----------------------------#
# ============================================================
# 04. INPUT GUARDRAIL
# ============================================================

# ------------------------------------------------------------
# DIRECT PROMPT-INJECTION PATTERNS
# ------------------------------------------------------------
INJECTION_PATTERNS = [

    # --------------------------------------------------------
    # Instruction override / bypass attempts
    # --------------------------------------------------------

    r"\bignore\s+(?:all|any|the|previous|prior|your)\s+instructions\b",

    r"\b(?:bypass|override|disregard|forget)\b"
    r".{0,40}"
    r"\b(?:all|any|the|previous|prior|system|developer|your)?\s*instructions\b",

    # --------------------------------------------------------
    # System / developer prompt extraction
    # --------------------------------------------------------

    r"\b(?:reveal|show|print|display|return|provide)\b"
    r".{0,40}"
    r"\b(?:system|developer)\s+(?:prompt|message|instructions)\b",

    # --------------------------------------------------------
    # Explicit role / instruction manipulation
    # --------------------------------------------------------

    r"\b(?:replace|change)\b"
    r".{0,30}"
    r"\b(?:system|developer)\s+instructions\b",
]


# ------------------------------------------------------------
# SECRET-EXTRACTION PATTERNS
# ------------------------------------------------------------
#
# IMPORTANT:
# Do NOT block a query merely because it mentions:
#
#   API key
#   password
#   token
#   credential
#
# Normal banking / cybersecurity questions may legitimately
# discuss those topics.
#
# We block when the query contains an extraction / disclosure
# intent together with a sensitive target.
# ------------------------------------------------------------

SECRET_EXTRACTION_PATTERNS = [

    r"\b(reveal|show|print|display|return|give|provide|expose|leak)\b"
    r".{0,50}"
    r"\b(api[\s_-]?key|openai[\s_-]?api[\s_-]?key)\b",

    r"\b(reveal|show|print|display|return|give|provide|expose|leak)\b"
    r".{0,50}"
    r"\b(password|passcode)\b",

    r"\b(reveal|show|print|display|return|give|provide|expose|leak)\b"
    r".{0,50}"
    r"\b(access[\s_-]?token|bearer[\s_-]?token|token)\b",

    r"\b(reveal|show|print|display|return|give|provide|expose|leak)\b"
    r".{0,50}"
    r"\b(secret|secret[\s_-]?key|credential|credentials)\b",

    r"\bwhat\s+is\b"
    r".{0,30}"
    r"\b(your|the)\b"
    r".{0,20}"
    r"\b(api[\s_-]?key|password|token|credential|secret)\b"
]


def input_guardrail(
    query: str
) -> GuardrailResult:

    reasons = []


    # --------------------------------------------------------
    # 1. EMPTY QUERY
    # --------------------------------------------------------

    if (
        query is None
        or not str(query).strip()
    ):

        return GuardrailResult(

            stage="input",

            status="BLOCK",

            reasons=[
                "Empty query"
            ],

            score=1.0
        )


    q = str(
        query
    ).strip()

    q_lower = q.lower()


    # --------------------------------------------------------
    # 2. EXCESSIVE LENGTH
    # --------------------------------------------------------

    if len(q) > 5000:

        reasons.append(
            "Query exceeds maximum allowed length"
        )


    # --------------------------------------------------------
    # 3. DIRECT PROMPT INJECTION
    # --------------------------------------------------------

    for pattern in INJECTION_PATTERNS:

        if re.search(
            pattern,
            q_lower,
            flags=re.IGNORECASE | re.DOTALL
        ):

            reasons.append(
                (
                    "Potential prompt injection detected: "
                    f"{pattern}"
                )
            )


    # --------------------------------------------------------
    # 4. SECRET / CREDENTIAL EXTRACTION
    # --------------------------------------------------------

    for pattern in SECRET_EXTRACTION_PATTERNS:

        if re.search(
            pattern,
            q_lower,
            flags=re.IGNORECASE | re.DOTALL
        ):

            reasons.append(
                (
                    "Potential secret-extraction request: "
                    f"{pattern}"
                )
            )


    # --------------------------------------------------------
    # 5. FINAL INPUT DECISION
    # --------------------------------------------------------

    if reasons:

        return GuardrailResult(

            stage="input",

            status="BLOCK",

            reasons=reasons,

            score=1.0
        )


    return GuardrailResult(

        stage="input",

        status="PASS",

        reasons=[],

        score=0.0,

        cleaned_text=q
    )   
     
    
#-----------------------------05. run_graphrag_query----------------------------#

# ============================================================
# STEP 2-A — REAL GRAPHRAG OUTPUT INTEGRATION
# ============================================================

# import subprocess
# import time


# ============================================================
# 05. RUN REAL GRAPHRAG QUERY
# ============================================================

def run_graphrag_query(
    query: str,
    method: str = "local"
):
    """
    Run a real GraphRAG CLI query and capture:
    - answer text
    - return code
    - stderr
    - latency

    Windows-safe decoding:
    GraphRAG CLI output may use Windows-1252 rather than UTF-8.
    Capture raw bytes first, then decode safely.
    """

    # --------------------------------------------------------
    # BUILD GRAPHRAG CLI COMMAND
    # --------------------------------------------------------

    cmd = [
        "graphrag",
        "query",
        "--root",
        str(GRAPHRAG_ROOT),
        "--method",
        method,
    ]

    # --------------------------------------------------------
    # GLOBAL SEARCH PERFORMANCE OPTIMIZATION
    # --------------------------------------------------------
    #
    # Phase 1 benchmark:
    #   Default community level 2 = 428 community reports.
    #
    # For Global Search:
    #   - use level 1
    #   - enable dynamic community selection
    #
    # Local / Basic / DRIFT searches remain unchanged.
    # --------------------------------------------------------

    if method.lower() == "global":

        cmd.extend([
            "--community-level",
            "1",
            "--dynamic-community-selection",
        ])

    # Query must remain the final positional CLI argument.
    cmd.append(query)

    start = time.perf_counter()

    # --------------------------------------------------------
    # CAPTURE RAW BYTES
    # --------------------------------------------------------

    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=False
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    # --------------------------------------------------------
    # SAFE WINDOWS DECODING
    # --------------------------------------------------------

    def decode_cli_output(
        raw_bytes
    ):

        if not raw_bytes:
            return ""

        # First try UTF-8
        try:

            return raw_bytes.decode(
                "utf-8"
            )

        except UnicodeDecodeError:

            pass

        # GraphRAG / Windows console output can contain
        # Windows-1252 curly quotes, apostrophes, etc.
        try:

            return raw_bytes.decode(
                "cp1252"
            )

        except UnicodeDecodeError:

            pass

        # Final fallback only
        return raw_bytes.decode(
            "utf-8",
            errors="replace"
        )

    stdout_text = decode_cli_output(
        completed.stdout
    )

    stderr_text = decode_cli_output(
        completed.stderr
    )

    return {

        "query":
            query,

        "method":
            method,

        "answer":
            stdout_text.strip(),

        "stderr":
            stderr_text.strip(),

        "return_code":
            completed.returncode,

        "latency_seconds":
            elapsed
    }

# One practical issue requires special attention:
#
# GraphRAG/LLMs may sometimes answer out-of-scope questions using pretrained
# knowledge, even when the indexed knowledge base does not contain supporting evidence.
#
# Therefore, Phase 1 should not rely solely on whether a citation exists.
#
# Add a domain-scope heuristic as an additional control.
#
# Example:


#-----------------------------06. domain_scope_check----------------------------#

# ============================================================
# DOMAIN SCOPE CHECK
# ============================================================

def domain_scope_check(query: str):

    if query is None:
        query = ""

    q = query.lower().strip()

    # Banking / financial institution terms
    banking_terms = [
        "bank",
        "banking",
        "citigroup",
        "citi",
        "jpmorgan",
        "jpmorgan chase",
        "wells fargo",
        "bank of america",
        "capital one",
        "credit risk",
        "loan",
        "lending",
        "deposit",
        "capital",
        "liquidity",
        "cet1",
        "stress testing",
        "ccar"
    ]

    # Regulatory agencies / authorities
    regulator_terms = [
        "federal reserve",
        "federal reserve board",
        "board of governors",
        "federal reserve system",
        "frb",
        "occ",
        "office of the comptroller of the currency",
        "fdic",
        "federal deposit insurance corporation",
        "cfpb",
        "consumer financial protection bureau",
        "sec",
        "securities and exchange commission"
    ]

    # Regulation / governance / model risk topics
    regulatory_terms = [
        "regulation",
        "regulatory",
        "supervision",
        "supervisory",
        "supervisory guidance",
        "model risk",
        "model validation",
        "model governance",
        "risk management",
        "capital adequacy",
        "liquidity risk",
        "credit risk",
        "operational risk",
        "market risk"
    ]

    # Regulatory document identifiers
    guidance_terms = [
        "sr 11-7",
        "sr11-7",
        "sr 21-8",
        "sr21-8",
        "sr 26-2",
        "sr26-2"
    ]

    all_terms = (
        banking_terms
        + regulator_terms
        + regulatory_terms
        + guidance_terms
    )

    matched_terms = [
        term
        for term in all_terms
        if term in q
    ]

    return {
        "in_scope": len(matched_terms) > 0,
        "matched_terms": matched_terms
    }
    
    
#-----------------------------07. out_of_scope_guardrail----------------------------#
def out_of_scope_guardrail(
    query,
    citation_info
):

    domain = domain_scope_check(query)

    reasons = []

    if not domain["in_scope"]:
        reasons.append(
            "Query appears outside the banking/regulatory domain."
        )

    if not citation_info["citations_present"]:
        reasons.append(
            "No supporting GraphRAG citation detected."
        )

    if reasons:
        return GuardrailResult(
            stage="scope",
            status="WARN",
            reasons=reasons,
            score=0.7
        )

    return GuardrailResult(
        stage="scope",
        status="PASS",
        reasons=["Query appears in scope and supported by evidence."],
        score=0.0
    )
    
    
#-----------------------------08. grounding_guardrail----------------------------#

# ============================================================
# STEP 4 — RETRIEVAL / GROUNDING GUARDRAIL
# ============================================================

def grounding_guardrail(
    query: str,
    answer: str,
    citations_present: bool,
    evidence_count: int,
    min_evidence_count: int = 1
) -> GuardrailResult:

    reasons = []

    # No answer returned
    if answer is None or not str(answer).strip():
        return GuardrailResult(
            stage="grounding",
            status="WARN",
            reasons=["No answer was returned."],
            score=1.0
        )

    # No citations/evidence references
    if not citations_present:
        reasons.append("No citations or evidence references were found.")

    # Too little retrieved evidence
    if evidence_count < min_evidence_count:
        reasons.append(
            f"Insufficient retrieved evidence: "
            f"{evidence_count} < {min_evidence_count}"
        )

    if reasons:
        return GuardrailResult(
            stage="grounding",
            status="WARN",
            reasons=reasons,
            score=0.7
        )

    return GuardrailResult(
        stage="grounding",
        status="PASS",
        reasons=["Answer has sufficient retrieved evidence."],
        score=0.0
    )
    

#-----------------------------09. output_guardrail ----------------------------#

# ============================================================
# 09. OUTPUT GUARDRAIL
# ============================================================


# ------------------------------------------------------------
# SECRET / SENSITIVE OUTPUT PATTERNS
# ------------------------------------------------------------

SENSITIVE_PATTERNS = [

    r"OPENAI_API_KEY",

    r"api[_ -]?key\s*[:=]",

    r"password\s*[:=]",

    r"secret\s*[:=]",

    r"access[_ -]?token\s*[:=]",

    r"bearer\s+[A-Za-z0-9\-_\.]+"
]


# ------------------------------------------------------------
# REGULATORY OVERSTATEMENT PATTERNS
# ------------------------------------------------------------

REGULATORY_OVERSTATEMENT_PATTERNS = [

    r"\bmust definitely\b",

    r"\bguaranteed to comply\b",

    r"\bfully compliant\b",

    r"\bno regulatory risk\b",

    r"\bwill certainly satisfy\b",

    r"\bregulator will approve\b"
]


# ------------------------------------------------------------
# HALLUCINATION / OVERCONFIDENCE PATTERNS
# ------------------------------------------------------------

HALLUCINATION_WARNING_PATTERNS = [

    r"\bI am certain\b",

    r"\bwithout any doubt\b",

    r"\bdefinitely\b",

    r"\bguaranteed\b"
]


# ------------------------------------------------------------
# OUTPUT GUARDRAIL
# ------------------------------------------------------------

def output_guardrail(
    query: str,
    answer: str,
    citations_present: bool,
    evidence_count: int,
    unsupported_claim_count: int = 0
) -> GuardrailResult:

    reasons = []


    # --------------------------------------------------------
    # 1. EMPTY OUTPUT
    # --------------------------------------------------------

    if (
        answer is None
        or not str(answer).strip()
    ):

        return GuardrailResult(

            stage="output",

            status="WARN",

            reasons=[
                "Empty answer returned."
            ],

            score=1.0
        )


    answer_text = str(
        answer
    ).strip()


    # --------------------------------------------------------
    # 2. SECRET / SENSITIVE OUTPUT
    # --------------------------------------------------------

    for pattern in SENSITIVE_PATTERNS:

        if re.search(
            pattern,
            answer_text,
            flags=re.IGNORECASE
        ):

            return GuardrailResult(

                stage="output",

                status="BLOCK",

                reasons=[
                    (
                        "Potential sensitive "
                        "information or secret "
                        "detected in output."
                    )
                ],

                score=1.0
            )


    # --------------------------------------------------------
    # 3. CITATION MISSING
    # --------------------------------------------------------

    if not citations_present:

        reasons.append(
            (
                "Answer does not contain "
                "citations or evidence references."
            )
        )


    # --------------------------------------------------------
    # 4. INSUFFICIENT EVIDENCE
    # --------------------------------------------------------

    if evidence_count <= 0:

        reasons.append(
            (
                "Answer has no supporting "
                "retrieved evidence."
            )
        )


    # --------------------------------------------------------
    # 5. UNSUPPORTED CLAIMS
    # --------------------------------------------------------

    if unsupported_claim_count > 0:

        reasons.append(

            f"{unsupported_claim_count} "
            "unsupported claim(s) detected."
        )


    # --------------------------------------------------------
    # 6. REGULATORY OVERSTATEMENT
    # --------------------------------------------------------

    for pattern in (
        REGULATORY_OVERSTATEMENT_PATTERNS
    ):

        if re.search(
            pattern,
            answer_text,
            flags=re.IGNORECASE
        ):

            reasons.append(
                (
                    "Potential regulatory "
                    "overstatement detected."
                )
            )

            break


    # --------------------------------------------------------
    # 7. HALLUCINATION / OVERCONFIDENCE
    # --------------------------------------------------------

    for pattern in (
        HALLUCINATION_WARNING_PATTERNS
    ):

        if re.search(
            pattern,
            answer_text,
            flags=re.IGNORECASE
        ):

            reasons.append(
                (
                    "Potential overconfident "
                    "or hallucination-prone "
                    "language detected."
                )
            )

            break


    # --------------------------------------------------------
    # FINAL DECISION
    # --------------------------------------------------------

    if reasons:

        return GuardrailResult(

            stage="output",

            status="WARN",

            reasons=reasons,

            score=0.7
        )


    return GuardrailResult(

        stage="output",

        status="PASS",

        reasons=[
            (
                "Output passed citation, "
                "grounding, sensitivity, "
                "and overstatement checks."
            )
        ],

        score=0.0
    )


#-----------------------------10. detect_indirect_prompt_injection----------------------------#
    
# ============================================================
# STEP 7 — INDIRECT PROMPT INJECTION GUARDRAIL
# Runtime-compatible version for Step 11
# ============================================================


INDIRECT_INJECTION_PATTERNS = {

    "ignore_previous_instructions":
        r"\bignore\s+(all\s+)?(previous|prior|earlier)\s+instructions\b",

    "ignore_system_prompt":
        r"\bignore\s+(the\s+)?system\s+prompt\b",

    "override_instructions":
        r"\b(override|replace|disregard)\s+(the\s+)?"
        r"(system|developer|user)\s+instructions\b",

    "follow_new_instructions":
        r"\bfollow\s+(these|the following|my)\s+instructions\b",

    "reveal_system_prompt":
        r"\b(reveal|show|print|display|return)\s+"
        r"(the\s+)?system\s+prompt\b",

    "secret_extraction":
        r"\b(reveal|show|print|return|expose)\b"
        r".{0,40}"
        r"\b(api[\s_-]?key|password|secret|token|credential)\b",

    "role_manipulation":
        r"\b(you are now|act as|pretend to be)\b",

    "data_exfiltration":
        r"\b(send|upload|transmit|email|post)\b"
        r".{0,60}"
        r"\b(data|documents|context|credentials|secrets)\b"
}


def detect_indirect_prompt_injection(
    text: str
):
    """
    Detect suspicious instructions embedded in
    retrieved/generated RAG content.
    """

    if text is None:
        text = ""

    text = str(text)

    matched_attack_types = []

    for attack_type, pattern in (
        INDIRECT_INJECTION_PATTERNS.items()
    ):

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.DOTALL
        ):
            matched_attack_types.append(
                attack_type
            )

    return {
        "indirect_injection_detected":
            len(matched_attack_types) > 0,

        "matched_attack_types":
            matched_attack_types,

        "match_count":
            len(matched_attack_types)
    }
    
    
#-----------------------------11. indirect_prompt_injection_guardrail----------------------------#

def indirect_prompt_injection_guardrail(
    text: str
) -> GuardrailResult:
    """
    Convert indirect-injection detection into
    the common GuardrailResult format.
    """

    detection = (
        detect_indirect_prompt_injection(
            text
        )
    )

    if detection[
        "indirect_injection_detected"
    ]:

        return GuardrailResult(
            stage="indirect_injection",
            status="BLOCK",
            reasons=[
                (
                    "Potential indirect prompt injection "
                    "detected in retrieved/generated content: "
                    + ", ".join(
                        detection[
                            "matched_attack_types"
                        ]
                    )
                )
            ],
            score=1.0
        )

    return GuardrailResult(
        stage="indirect_injection",
        status="PASS",
        reasons=[
            "No indirect prompt injection detected."
        ],
        score=0.0
    )
    
    
#-----------------------------12. detect_graphrag_citations----------------------------#

# ============================================================
# STEP 8 — AUTOMATIC CITATION DETECTION
# ============================================================

CITATION_PATTERNS = {
    "entities": r"Entities\s*\(([^)]*)\)",
    "reports": r"Reports\s*\(([^)]*)\)",
    "sources": r"Sources\s*\(([^)]*)\)",
    "relationships": r"Relationships\s*\(([^)]*)\)",
}


def detect_graphrag_citations(answer: str):

    if answer is None:
        answer = ""

    result = {
        "citations_present": False,
        "citation_types": [],
        "evidence_count": 0,
        "details": {}
    }

    for citation_type, pattern in CITATION_PATTERNS.items():

        matches = re.findall(
            pattern,
            answer,
            flags=re.IGNORECASE
        )

        if not matches:
            continue

        result["citation_types"].append(citation_type)

        ids = []

        for match in matches:

            # Split things like:
            # "1521, 1568"
            # or "3"
            parts = [
                x.strip()
                for x in match.split(",")
                if x.strip()
            ]

            ids.extend(parts)

        result["details"][citation_type] = ids
        result["evidence_count"] += len(ids)

    result["citations_present"] = (
        len(result["citation_types"]) > 0
    )

    return result


#-----------------------------13. normalize_text----------------------------#

# ============================================================
# STEP 8 — CITATION MISMATCH / CLAIM SUPPORT CHECK
# ============================================================

# from dataclasses import dataclass
# from typing import List


def normalize_text(text: str) -> str:
    if text is None:
        return ""
    return " ".join(str(text).lower().split())


#---------------------------14. citation_support_check------------------------------#

def citation_support_check(
    claim: str,
    evidence_text: str,
    required_keywords=None,
):
    """
    Simple V4 rule-based support check.

    Returns whether the cited evidence contains enough
    information to plausibly support the claim.
    """

    claim_n = normalize_text(claim)
    evidence_n = normalize_text(evidence_text)

    if required_keywords is None:
        # Simple keyword extraction:
        # keep reasonably meaningful words from claim
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were",
            "of", "to", "in", "for", "and", "or", "on",
            "with", "that", "this", "has", "have", "had",
            "by", "as", "at", "from"
        }

        claim_words = [
            w.strip(".,;:()[]{}")
            for w in claim_n.split()
            if len(w) >= 4
            and w not in stopwords
        ]

        required_keywords = list(dict.fromkeys(claim_words))

    matched_keywords = [
        kw
        for kw in required_keywords
        if kw in evidence_n
    ]

    total = len(required_keywords)

    support_ratio = (
        len(matched_keywords) / total
        if total > 0
        else 0.0
    )

    return {
        "supported": support_ratio >= 0.5,
        "support_ratio": support_ratio,
        "matched_keywords": matched_keywords,
        "required_keywords": required_keywords
    }
    
    
#-----------------------------15. extract_numbers----------------------------#

def extract_numbers(text: str):
    if text is None:
        return []

    text = str(text)

    # --------------------------------------------------------
    # Ignore structural enumeration markers.
    #
    # Examples intentionally excluded:
    # (1) first reason
    # (2) second reason
    # 1. first item
    # 2. second item
    #
    # These are formatting / list markers rather than
    # substantive numeric claims.
    # --------------------------------------------------------

    cleaned_text = re.sub(
        r"(?<!\w)\(\d+\)(?=\s)",
        " ",
        text
    )

    cleaned_text = re.sub(
        r"(?m)^\s*\d+\.\s+",
        " ",
        cleaned_text
    )

    # --------------------------------------------------------
    # Extract substantive numeric values.
    # --------------------------------------------------------

    return re.findall(
        r"\b\d+(?:\.\d+)?%?\b",
        cleaned_text
    )

#-----------------------------16. numeric_citation_check----------------------------#

# For numeric claims, I strongly recommend an additional check because numbers are especially important in banking.

def numeric_citation_check(
    claim: str,
    evidence_text: str
):
    claim_numbers = extract_numbers(claim)
    evidence_numbers = extract_numbers(evidence_text)

    missing_numbers = [
        n
        for n in claim_numbers
        if n not in evidence_numbers
    ]

    return {
        "claim_numbers": claim_numbers,
        "evidence_numbers": evidence_numbers,
        "missing_numbers": missing_numbers,
        "numeric_support": len(missing_numbers) == 0
    }
    

#-----------------------------17. parse_claims_with_citations----------------------------#

# ============================================================
# 17. PARSE CLAIMS WITH CITATIONS
# ============================================================

def parse_claims_with_citations(
    answer
):

    # --------------------------------------------------------
    # EMPTY ANSWER
    # --------------------------------------------------------

    if (
        answer is None
        or not str(answer).strip()
    ):

        return []


    answer_text = str(
        answer
    )


    # --------------------------------------------------------
    # CLAIM + [Data: ...] PATTERN
    # --------------------------------------------------------
    #
    # Examples:
    #
    # [Data: Entities (1521, 1568); Reports (3)]
    #
    # [Data: Entities (3306, 3356);
    #        Sources (1418, 1446);
    #        Relationships (15035, 15063)]
    #
    # Each regex match represents one claim/citation pair.
    # --------------------------------------------------------

    pattern = re.compile(

        r"""
        (?P<claim>
            .*?
        )
        \[
        \s*
        Data:
        \s*
        (?P<citation>
            .*?
        )
        \]
        """,

        flags=(
            re.IGNORECASE
            | re.DOTALL
            | re.VERBOSE
        )
    )


    results = []


    # --------------------------------------------------------
    # HELPER — PARSE IDS FROM ONE CITATION TYPE
    # --------------------------------------------------------

    def parse_ids(
        citation_text,
        citation_label
    ):

        citation_match = re.search(

            rf"{citation_label}\s*\(([^)]*)\)",

            citation_text,

            flags=re.IGNORECASE
        )


        if not citation_match:

            return []


        raw_ids = [

            x.strip()

            for x in (
                citation_match
                .group(1)
                .split(",")
            )

            if x.strip()
        ]


        # ----------------------------------------------------
        # FILTER NON-ID MARKERS
        # ----------------------------------------------------
        #
        # GraphRAG can emit:
        #
        # +more
        #
        # which is not a real evidence ID.
        # ----------------------------------------------------

        cleaned_ids = [

            x

            for x in raw_ids

            if x.lower() not in {
                "+more",
                "more"
            }
        ]


        return cleaned_ids


    # --------------------------------------------------------
    # PARSE EACH CLAIM / CITATION PAIR
    # --------------------------------------------------------

    for match in pattern.finditer(
        answer_text
    ):

        claim = (
            match.group(
                "claim"
            )
        )


        citation_text = (
            match.group(
                "citation"
            )
        )


        # ----------------------------------------------------
        # CLEAN CLAIM
        # ----------------------------------------------------

        clean_claim = " ".join(
            claim.split()
        )


        if not clean_claim:

            continue


        # ----------------------------------------------------
        # ENTITY IDS
        # ----------------------------------------------------

        entity_ids = parse_ids(
            citation_text,
            "Entities"
        )


        # ----------------------------------------------------
        # REPORT IDS
        # ----------------------------------------------------

        report_ids = parse_ids(
            citation_text,
            "Reports"
        )


        # ----------------------------------------------------
        # SOURCE IDS
        # ----------------------------------------------------

        source_ids = parse_ids(
            citation_text,
            "Sources"
        )


        # ----------------------------------------------------
        # RELATIONSHIP IDS
        # ----------------------------------------------------

        relationship_ids = parse_ids(
            citation_text,
            "Relationships"
        )


        # ----------------------------------------------------
        # STORE PARSED CLAIM
        # ----------------------------------------------------

        results.append({

            "claim":
                clean_claim,

            "entity_ids":
                entity_ids,

            "report_ids":
                report_ids,

            "source_ids":
                source_ids,

            "relationship_ids":
                relationship_ids

        })


    return results


#-----------------------------18. get_entity_evidence----------------------------#

# Key step: automatically retrieve the actual evidence associated with each citation ID.

# ============================================================
# HELPER 4 — FIND ENTITY EVIDENCE
# ============================================================

def get_entity_evidence(
    entity_ids,
    entities_df
):

    evidence = []

    if not entity_ids:
        return evidence

    for entity_id in entity_ids:

        try:
            entity_id_int = int(entity_id)
        except (TypeError, ValueError):
            continue

        matches = entities_df[
            entities_df["human_readable_id"]
            == entity_id_int
        ]

        for _, row in matches.iterrows():

            evidence.append({
                "source_type": "entity",
                "citation_id": entity_id,
                "title": row.get(
                    "title",
                    ""
                ),
                "text": row.get(
                    "description",
                    ""
                )
            })

    return evidence

# Reports require slightly more flexible handling because GraphRAG versions may use
# different column names. The implementation therefore detects the appropriate ID field automatically.

#-----------------------------19. get_report_evidence----------------------------#

# ============================================================
# HELPER 5 — FIND REPORT EVIDENCE
# ============================================================

def get_report_evidence(
    report_ids,
    reports_df
):

    evidence = []

    if not report_ids:
        return evidence

    # Find likely report ID column
    candidate_id_columns = [
        "human_readable_id",
        "community",
        "community_id",
        "id"
    ]

    id_column = None

    for col in candidate_id_columns:

        if col in reports_df.columns:
            id_column = col
            break

    if id_column is None:
        return evidence

    # Find likely report text column
    candidate_text_columns = [
        "full_content",
        "summary",
        "description",
        "content",
        "title"
    ]

    text_column = None

    for col in candidate_text_columns:

        if col in reports_df.columns:
            text_column = col
            break

    if text_column is None:
        return evidence

    for report_id in report_ids:

        matches = reports_df[
            reports_df[id_column]
            .astype(str)
            == str(report_id)
        ]

        for _, row in matches.iterrows():

            evidence.append({
                "source_type": "report",
                "citation_id": report_id,
                "title": row.get(
                    "title",
                    ""
                ),
                "text": row.get(
                    text_column,
                    ""
                )
            })

    return evidence



# ============================================================
# 19A. GET SOURCE / TEXT-UNIT EVIDENCE
# ============================================================

def get_source_evidence(
    source_ids,
    text_units_df
):
    """
    Retrieve GraphRAG source evidence from text_units.parquet.

    GraphRAG citations such as:

        Sources (1418, 1446)

    are mapped to rows in text_units_df.

    The function dynamically identifies:
    - a usable source ID column
    - a usable source text column
    """

    evidence = []

    if not source_ids:
        return evidence


    # --------------------------------------------------------
    # FIND SOURCE ID COLUMN
    # --------------------------------------------------------

    candidate_id_columns = [
        "human_readable_id",
        "id"
    ]

    id_column = None

    for column in candidate_id_columns:

        if column in text_units_df.columns:

            id_column = column
            break


    if id_column is None:

        return evidence


    # --------------------------------------------------------
    # FIND SOURCE TEXT COLUMN
    # --------------------------------------------------------

    candidate_text_columns = [
        "text",
        "content",
        "description"
    ]

    text_column = None

    for column in candidate_text_columns:

        if column in text_units_df.columns:

            text_column = column
            break


    if text_column is None:

        return evidence


    # --------------------------------------------------------
    # RETRIEVE SOURCE EVIDENCE
    # --------------------------------------------------------

    for source_id in source_ids:

        # Ignore GraphRAG display markers
        if str(source_id).strip().lower() in {
            "+more",
            "more",
            ""
        }:

            continue


        matches = text_units_df[
            text_units_df[id_column]
            .astype(str)
            == str(source_id)
        ]


        for _, row in matches.iterrows():

            evidence.append({

                "source_type":
                    "source",

                "citation_id":
                    str(source_id),

                "title":
                    row.get(
                        "title",
                        ""
                    ),

                "text":
                    row.get(
                        text_column,
                        ""
                    )

            })


    return evidence



# ============================================================
# 19B. GET RELATIONSHIP EVIDENCE
# ============================================================

def get_relationship_evidence(
    relationship_ids,
    relationships_df
):
    """
    Retrieve GraphRAG relationship evidence from
    relationships.parquet.

    GraphRAG citations such as:

        Relationships (15035, 15063)

    are mapped to rows in relationships_df.

    The function dynamically identifies:
    - a usable relationship ID column
    - a usable relationship description/text column
    """

    evidence = []

    if not relationship_ids:
        return evidence


    # --------------------------------------------------------
    # FIND RELATIONSHIP ID COLUMN
    # --------------------------------------------------------

    candidate_id_columns = [
        "human_readable_id",
        "id"
    ]

    id_column = None

    for column in candidate_id_columns:

        if column in relationships_df.columns:

            id_column = column
            break


    if id_column is None:

        return evidence


    # --------------------------------------------------------
    # FIND RELATIONSHIP TEXT COLUMN
    # --------------------------------------------------------

    candidate_text_columns = [
        "description",
        "text"
    ]

    text_column = None

    for column in candidate_text_columns:

        if column in relationships_df.columns:

            text_column = column
            break


    if text_column is None:

        return evidence


    # --------------------------------------------------------
    # RETRIEVE RELATIONSHIP EVIDENCE
    # --------------------------------------------------------

    for relationship_id in relationship_ids:

        # Ignore GraphRAG display markers
        if str(relationship_id).strip().lower() in {
            "+more",
            "more",
            ""
        }:

            continue


        matches = relationships_df[
            relationships_df[id_column]
            .astype(str)
            == str(relationship_id)
        ]


        for _, row in matches.iterrows():

            source_entity = row.get(
                "source",
                ""
            )

            target_entity = row.get(
                "target",
                ""
            )

            relationship_title = ""

            if source_entity or target_entity:

                relationship_title = (
                    f"{source_entity} → {target_entity}"
                )


            evidence.append({

                "source_type":
                    "relationship",

                "citation_id":
                    str(
                        relationship_id
                    ),

                "title":
                    relationship_title,

                "text":
                    row.get(
                        text_column,
                        ""
                    )

            })


    return evidence


#-----------------------------20. evaluate_claim_support----------------------------#

# Evidence support check。

# ============================================================
# HELPER 6 — CLAIM VS EVIDENCE SUPPORT
# ============================================================

def evaluate_claim_support(
    claim,
    evidence_items
):

    if not evidence_items:

        return {
            "supported": False,
            "support_ratio": 0.0,
            "numeric_support": False,
            "missing_numbers":
                extract_numbers(claim)
        }

    combined_evidence = " ".join(
        str(x["text"])
        for x in evidence_items
    )

    claim_n = normalize_text(claim)
    evidence_n = normalize_text(
        combined_evidence
    )
    
    stopwords = {
    "the", "and", "that",
    "this", "with", "from",
    "into", "have", "has",
    "was", "were", "are",
    "for", "its", "their",
    "about", "which",
    "also", "through"
    }

    claim_words = [
        w.strip(
            ".,;:()[]{}\"'"
        )
        for w in claim_n.split()
        if len(w) >= 5
        and w not in stopwords
    ]

    claim_words = list(
        dict.fromkeys(
            claim_words
        )
    )

    matched_words = [
        word
        for word in claim_words
        if word in evidence_n
    ]
    
    unmatched_words = [
        word
        for word in claim_words
        if word not in evidence_n ]

    support_ratio = (
        len(matched_words)
        / len(claim_words)
        if claim_words
        else 0.0
    )

    claim_numbers = extract_numbers(
        claim
    )

    evidence_numbers = extract_numbers(
        combined_evidence
    )

    missing_numbers = [
        n
        for n in claim_numbers
        if n not in evidence_numbers
    ]

    numeric_support = (
        len(missing_numbers) == 0
    )

    # V4 heuristic
    # Phase 1 citation-support heuristic
    support_threshold = 0.35

    supported = (
        support_ratio >= support_threshold
        and numeric_support
    )
    
    return {
        "supported":
            supported,

        "support_ratio":
            round(
                support_ratio,
                3
            ),

        "support_threshold":
            support_threshold,

        "matched_keywords":
            matched_words,

        "unmatched_keywords":
            unmatched_words,

        "claim_numbers":
            claim_numbers,

        "missing_numbers":
            missing_numbers,

        "numeric_support":
            numeric_support
    }


#-----------------------------21. detect_sensitive_banking_data----------------------------#

# ============================================================
# STEP 9 — PII / SENSITIVE BANKING DATA DETECTION
# ============================================================

SENSITIVE_BANKING_PATTERNS = {

    # --------------------------------------------------------
    # IDENTITY / PII
    # --------------------------------------------------------
    "ssn":
        r"\b\d{3}-\d{2}-\d{4}\b",

    "email":
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",

    "phone_number":
        r"\b(?:\+1[-.\s]?)?"
        r"(?:\(?\d{3}\)?[-.\s]?)"
        r"\d{3}[-.\s]?\d{4}\b",

    "date_of_birth":
        r"\b(?:DOB|Date of Birth)\s*[:\-]?\s*"
        r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",

    # --------------------------------------------------------
    # BANKING DATA
    # --------------------------------------------------------
    "bank_account_number":
        r"\b(?:account|acct)\s*(?:number|no\.?|#)?\s*[:\-]?\s*"
        r"\d{6,17}\b",

    "routing_number":
        r"\b(?:routing|ABA)\s*(?:number|no\.?|#)?\s*[:\-]?\s*"
        r"\d{9}\b",

    "credit_card_number":
        r"\b(?:\d[ -]*?){13,19}\b",

    "customer_id":
        r"\b(?:customer|client|cust)\s*(?:id|identifier)\s*"
        r"[:\-]?\s*[A-Za-z0-9_-]{5,30}\b",

    # --------------------------------------------------------
    # SECURITY / SECRET DATA
    # --------------------------------------------------------
    "api_key":
        r"\b(?:api[_ -]?key|openai[_ -]?api[_ -]?key)\b"
        r"\s*[:=]\s*[A-Za-z0-9_\-]{8,}",

    "password":
        r"\bpassword\b\s*[:=]\s*\S+",

    "access_token":
        r"\b(?:access[_ -]?token|bearer[_ -]?token|token)\b"
        r"\s*[:=]\s*[A-Za-z0-9._\-]{8,}",

    "secret":
        r"\bsecret\b\s*[:=]\s*\S+",
}

# ============================================================
# DETECTOR
# ============================================================

def detect_sensitive_banking_data(text: str):

    if text is None:
        text = ""

    matches = {}

    for data_type, pattern in SENSITIVE_BANKING_PATTERNS.items():

        found = re.findall(
            pattern,
            str(text),
            flags=re.IGNORECASE
        )

        if found:
            matches[data_type] = found

    return {
        "sensitive_data_detected": len(matches) > 0,
        "detected_types": list(matches.keys()),
        "match_count": sum(
            len(v)
            for v in matches.values()
        ),
        "details": matches
    }
    

#-----------------------------22. sensitive_banking_data_guardrail----------------------------#

# ============================================================
# STEP 9 GUARDRAIL
# ============================================================

def sensitive_banking_data_guardrail(
    text: str
) -> GuardrailResult:

    detection = detect_sensitive_banking_data(
        text
    )

    if detection["sensitive_data_detected"]:

        return GuardrailResult(
            stage="sensitive_banking_data",
            status="BLOCK",
            reasons=[
                "Potential PII or sensitive banking data detected: "
                + ", ".join(
                    detection["detected_types"]
                )
            ],
            score=1.0
        )

    return GuardrailResult(
        stage="sensitive_banking_data",
        status="PASS",
        reasons=[
            "No PII or sensitive banking data detected."
        ],
        score=0.0
    )


#-----------------------------23. load evidence parquet file----------------------------#
    # entities_df
    # reports_df
    
# ============================================================
# 23. LOAD CITATION EVIDENCE DATA
# ============================================================

def load_graphrag_evidence_tables():
    """
    Load GraphRAG evidence tables used by citation-support
    validation.

    The following GraphRAG citation types are supported:

    - Entities       -> entities.parquet
    - Reports        -> community_reports.parquet
    - Sources        -> text_units.parquet
    - Relationships  -> relationships.parquet

    All evidence tables must come from the SAME GraphRAG root
    used by run_graphrag_query().
    """

    # --------------------------------------------------------
    # VALIDATE CORE RUNTIME PATHS
    # --------------------------------------------------------

    validate_runtime_paths()


    # --------------------------------------------------------
    # DEFINE EVIDENCE FILE PATHS
    # --------------------------------------------------------

    entities_path = (
        GRAPHRAG_OUTPUT_DIR
        / "entities.parquet"
    )

    reports_path = (
        GRAPHRAG_OUTPUT_DIR
        / "community_reports.parquet"
    )

    text_units_path = (
        GRAPHRAG_OUTPUT_DIR
        / "text_units.parquet"
    )

    relationships_path = (
        GRAPHRAG_OUTPUT_DIR
        / "relationships.parquet"
    )


    # --------------------------------------------------------
    # VALIDATE ADDITIONAL FILES
    # --------------------------------------------------------

    additional_required_files = {

        "Text units parquet":
            text_units_path,

        "Relationships parquet":
            relationships_path
    }


    missing_files = []

    for name, path in additional_required_files.items():

        if not path.exists():

            missing_files.append(
                f"{name}: {path}"
            )


    if missing_files:

        raise FileNotFoundError(
            "\nCitation evidence files are missing:\n"
            + "\n".join(
                f" - {x}"
                for x in missing_files
            )
        )


    # --------------------------------------------------------
    # LOAD ENTITY TABLE
    # --------------------------------------------------------

    entities = pd.read_parquet(
        entities_path
    )


    # --------------------------------------------------------
    # LOAD COMMUNITY REPORT TABLE
    # --------------------------------------------------------

    reports = pd.read_parquet(
        reports_path
    )


    # --------------------------------------------------------
    # LOAD TEXT UNIT / SOURCE TABLE
    # --------------------------------------------------------

    text_units = pd.read_parquet(
        text_units_path
    )


    # --------------------------------------------------------
    # LOAD RELATIONSHIP TABLE
    # --------------------------------------------------------

    relationships = pd.read_parquet(
        relationships_path
    )


    # ========================================================
    # ENTITY SCHEMA VALIDATION
    # ========================================================

    if (
        "human_readable_id"
        not in entities.columns
    ):

        raise ValueError(
            (
                "entities.parquet does not contain "
                "'human_readable_id'. "
                "Citation validation cannot continue."
            )
        )


    entity_required_text_columns = [
        "title",
        "description"
    ]


    for column in entity_required_text_columns:

        if column not in entities.columns:

            raise ValueError(
                (
                    "entities.parquet is missing "
                    f"required column: {column}"
                )
            )


    # ========================================================
    # REPORT SCHEMA VALIDATION
    # ========================================================

    report_id_candidates = [
        "human_readable_id",
        "community",
        "community_id",
        "id"
    ]


    if not any(
        column in reports.columns
        for column in report_id_candidates
    ):

        raise ValueError(
            (
                "community_reports.parquet does "
                "not contain a recognized report "
                "ID column."
            )
        )


    report_text_candidates = [
        "full_content",
        "summary",
        "description",
        "content",
        "title"
    ]


    if not any(
        column in reports.columns
        for column in report_text_candidates
    ):

        raise ValueError(
            (
                "community_reports.parquet does "
                "not contain a recognized report "
                "text column."
            )
        )


    # ========================================================
    # TEXT UNIT / SOURCE SCHEMA VALIDATION
    # ========================================================

    source_id_candidates = [
        "human_readable_id",
        "id"
    ]


    if not any(
        column in text_units.columns
        for column in source_id_candidates
    ):

        raise ValueError(
            (
                "text_units.parquet does not contain "
                "a recognized source ID column."
            )
        )


    source_text_candidates = [
        "text",
        "content",
        "description"
    ]


    if not any(
        column in text_units.columns
        for column in source_text_candidates
    ):

        raise ValueError(
            (
                "text_units.parquet does not contain "
                "a recognized source text column."
            )
        )


    # ========================================================
    # RELATIONSHIP SCHEMA VALIDATION
    # ========================================================

    relationship_id_candidates = [
        "human_readable_id",
        "id"
    ]


    if not any(
        column in relationships.columns
        for column in relationship_id_candidates
    ):

        raise ValueError(
            (
                "relationships.parquet does not contain "
                "a recognized relationship ID column."
            )
        )


    relationship_text_candidates = [
        "description",
        "text"
    ]


    if not any(
        column in relationships.columns
        for column in relationship_text_candidates
    ):

        raise ValueError(
            (
                "relationships.parquet does not contain "
                "a recognized relationship text column."
            )
        )


    # --------------------------------------------------------
    # RETURN ALL EVIDENCE TABLES
    # --------------------------------------------------------

    return (
        entities,
        reports,
        text_units,
        relationships
    )


# ============================================================
# INITIALIZE EVIDENCE TABLES
# ============================================================

(
    entities_df,
    reports_df,
    text_units_df,
    relationships_df
) = load_graphrag_evidence_tables()


    

#-----------------------------24. validate_real_graphrag_citations----------------------------#
    
# Integrate all runtime guardrail stages into a single pipeline.

# ============================================================
# MAIN FUNCTION
# REAL GRAPHRAG CITATION VALIDATION
# ============================================================

# ============================================================
# 24. VALIDATE REAL GRAPHRAG CITATIONS
# ============================================================

def validate_real_graphrag_citations(
    answer
):

    # --------------------------------------------------------
    # 1. PARSE CLAIMS + CITATIONS
    # --------------------------------------------------------

    claims = parse_claims_with_citations(
        answer
    )


    # --------------------------------------------------------
    # 2. NO PARSEABLE CITED CLAIMS
    # --------------------------------------------------------
    #
    # Zero parsed claims must NOT be treated as PASS.
    #
    # If nothing can be parsed, citation support cannot
    # actually be validated.
    # --------------------------------------------------------

    if len(claims) == 0:

        return {

            "overall_status":
                "WARN",

            "claims_checked":
                0,

            "claims_passed":
                0,

            "claims_warned":
                0,

            "validation_reason":
                (
                    "No parseable GraphRAG cited claims "
                    "were found. Citation support could "
                    "not be validated."
                ),

            "details":
                []
        }


    # --------------------------------------------------------
    # 3. VALIDATE EACH CLAIM
    # --------------------------------------------------------

    results = []


    for i, item in enumerate(
        claims,
        start=1
    ):


        # ====================================================
        # ENTITY EVIDENCE
        # ====================================================

        entity_evidence = (
            get_entity_evidence(

                item.get(
                    "entity_ids",
                    []
                ),

                entities_df
            )
        )


        # ====================================================
        # REPORT EVIDENCE
        # ====================================================

        report_evidence = (
            get_report_evidence(

                item.get(
                    "report_ids",
                    []
                ),

                reports_df
            )
        )


        # ====================================================
        # SOURCE / TEXT-UNIT EVIDENCE
        # ====================================================

        source_evidence = (
            get_source_evidence(

                item.get(
                    "source_ids",
                    []
                ),

                text_units_df
            )
        )


        # ====================================================
        # RELATIONSHIP EVIDENCE
        # ====================================================

        relationship_evidence = (
            get_relationship_evidence(

                item.get(
                    "relationship_ids",
                    []
                ),

                relationships_df
            )
        )


        # ====================================================
        # COMBINE ALL CITED EVIDENCE
        # ====================================================

        evidence_items = (

            entity_evidence

            + report_evidence

            + source_evidence

            + relationship_evidence
        )


        # ====================================================
        # CLAIM SUPPORT VALIDATION
        # ====================================================

        support = (
            evaluate_claim_support(

                item[
                    "claim"
                ],

                evidence_items
            )
        )


        # ====================================================
        # CLAIM STATUS
        # ====================================================

        status = (

            "PASS"

            if support[
                "supported"
            ]

            else "WARN"
        )


        # ====================================================
        # STORE CLAIM VALIDATION RESULT
        # ====================================================

        results.append({

            # ------------------------------------------------
            # CLAIM IDENTIFICATION
            # ------------------------------------------------

            "claim_number":
                i,

            "claim":
                item[
                    "claim"
                ],


            # ------------------------------------------------
            # CITATION IDS
            # ------------------------------------------------

            "entity_ids":
                item.get(
                    "entity_ids",
                    []
                ),

            "report_ids":
                item.get(
                    "report_ids",
                    []
                ),

            "source_ids":
                item.get(
                    "source_ids",
                    []
                ),

            "relationship_ids":
                item.get(
                    "relationship_ids",
                    []
                ),


            # ------------------------------------------------
            # EVIDENCE COUNTS BY TYPE
            # ------------------------------------------------

            "entity_evidence_count":
                len(
                    entity_evidence
                ),

            "report_evidence_count":
                len(
                    report_evidence
                ),

            "source_evidence_count":
                len(
                    source_evidence
                ),

            "relationship_evidence_count":
                len(
                    relationship_evidence
                ),


            # ------------------------------------------------
            # TOTAL EVIDENCE
            # ------------------------------------------------

            "evidence_count":
                len(
                    evidence_items
                ),


            # ------------------------------------------------
            # SUPPORT METRICS
            # ------------------------------------------------
            
            "support_ratio":
                support[
                    "support_ratio"
                ],

            "support_threshold":
                support.get(
                    "support_threshold",
                    0.35
                ),

            "numeric_support":
                support[
                    "numeric_support"
                ],

            "missing_numbers":
                support[
                    "missing_numbers"
                ],

            "matched_keywords":
                support.get(
                    "matched_keywords",
                    []
                ),

            "unmatched_keywords":
                support.get(
                    "unmatched_keywords",
                    []
                ),


            # ------------------------------------------------
            # FINAL CLAIM STATUS
            # ------------------------------------------------

            "status":
                status,


            # ------------------------------------------------
            # RAW SUPPORTING EVIDENCE
            # ------------------------------------------------

            "evidence":
                evidence_items
        })


    # --------------------------------------------------------
    # 4. SUMMARY COUNTS
    # --------------------------------------------------------

    warn_count = sum(

        1

        for result in results

        if result[
            "status"
        ] == "WARN"
    )


    pass_count = (

        len(results)

        - warn_count
    )


    # --------------------------------------------------------
    # 5. OVERALL CITATION-VALIDATION STATUS
    # --------------------------------------------------------

    if warn_count == 0:

        overall_status = "PASS"

        validation_reason = (
            (
                f"All {len(results)} parsed cited claim(s) "
                "passed citation-support validation."
            )
        )


    else:

        overall_status = "WARN"

        validation_reason = (
            (
                f"{warn_count} of {len(results)} parsed "
                "cited claim(s) may not be fully supported "
                "by the cited evidence."
            )
        )


    # --------------------------------------------------------
    # 6. TOTAL EVIDENCE COVERAGE
    # --------------------------------------------------------

    total_entity_evidence = sum(

        result[
            "entity_evidence_count"
        ]

        for result in results
    )


    total_report_evidence = sum(

        result[
            "report_evidence_count"
        ]

        for result in results
    )


    total_source_evidence = sum(

        result[
            "source_evidence_count"
        ]

        for result in results
    )


    total_relationship_evidence = sum(

        result[
            "relationship_evidence_count"
        ]

        for result in results
    )


    total_evidence = (

        total_entity_evidence

        + total_report_evidence

        + total_source_evidence

        + total_relationship_evidence
    )


    # --------------------------------------------------------
    # 7. RETURN VALIDATION RESULT
    # --------------------------------------------------------

    return {

        "overall_status":
            overall_status,

        "claims_checked":
            len(
                results
            ),

        "claims_passed":
            pass_count,

        "claims_warned":
            warn_count,

        "validation_reason":
            validation_reason,


        # ----------------------------------------------------
        # EVIDENCE COVERAGE SUMMARY
        # ----------------------------------------------------

        "evidence_summary": {

            "entity_evidence_count":
                total_entity_evidence,

            "report_evidence_count":
                total_report_evidence,

            "source_evidence_count":
                total_source_evidence,

            "relationship_evidence_count":
                total_relationship_evidence,

            "total_evidence_count":
                total_evidence
        },


        # ----------------------------------------------------
        # CLAIM-BY-CLAIM DETAILS
        # ----------------------------------------------------

        "details":
            results
    }

    
#-----------------------------25. citation_validation_guardrail----------------------------#
# ============================================================
# 25. CITATION VALIDATION GUARDRAIL
# ============================================================
    
### Step 11 — Runtime Guardrail Pipeline Integration

# Step 11A — Build a Citation Validation → GuardrailResult adapter
#
# validate_real_graphrag_citations() currently returns a dictionary, while most
# other guardrail components return GuardrailResult objects.
#
# Normalize the citation-validation output into the common GuardrailResult format.

# ============================================================
# STEP 11A — CITATION VALIDATION ADAPTER
# ============================================================


def citation_validation_guardrail(
    answer: str
) -> GuardrailResult:

    validation = (
        validate_real_graphrag_citations(
            answer
        )
    )

    validation_reason = (
        validation.get(
            "validation_reason",
            "Citation-support validation completed."
        )
    )

    if (
        validation["overall_status"]
        == "PASS"
    ):

        return GuardrailResult(

            stage=
                "citation_validation",

            status=
                "PASS",

            reasons=[
                validation_reason
            ],

            score=
                0.0
        )

    return GuardrailResult(

        stage=
            "citation_validation",

        status=
            "WARN",

        reasons=[
            validation_reason
        ],

        score=
            0.8
    )    
    

#-----------------------------26. aggregate_guardrail_results----------------------------#

# Step 11B — Final decision aggregator

# Aggregate results from all guardrail stages into one unified runtime decision.

# ============================================================
# STEP 11B — FINAL DECISION AGGREGATOR
# ============================================================

def aggregate_guardrail_results(
    stage_results
):

    valid_results = [
        r
        for r in stage_results
        if r is not None
    ]

    statuses = [
        r.status
        for r in valid_results
    ]

    reasons = []

    for result in valid_results:

        for reason in result.reasons:
            reasons.append(
                f"{result.stage}: {reason}"
            )

    if "BLOCK" in statuses:

        final_status = "BLOCK"
        final_score = 1.0

    elif "WARN" in statuses:

        final_status = "WARN"
        final_score = 0.7

    else:

        final_status = "PASS"
        final_score = 0.0

    return GuardrailResult(
        stage="FINAL",
        status=final_status,
        reasons=reasons,
        score=final_score
    )
    
    

# -----------------------------27. write_guardrail_audit_log----------------------------#

# ============================================================
# STEP 11 — COMPLETE GUARDRAIL AUDIT LOGGING
# ============================================================

def write_guardrail_audit_log(
    query,
    graphrag_result,

    citation_info=None,

    input_result=None,
    scope_result=None,
    indirect_injection_result=None,
    citation_validation_result=None,
    grounding_result=None,
    sensitive_data_result=None,
    output_result=None,
    final_result=None,

    log_file=AUDIT_LOG_FILE
):
    """
    Write one complete GraphRAG runtime Guardrail audit record
    as one JSON line.

    The audit record captures:
    - User query
    - GraphRAG execution information
    - Citation information
    - All runtime Guardrail stages
    - Final Guardrail decision
    """

    def result_to_dict(result):
        """
        Safely convert GuardrailResult to dictionary.
        """
        if result is None:
            return None

        return result.to_dict()


    audit_record = {

        # ----------------------------------------------------
        # AUDIT METADATA
        # ----------------------------------------------------
        "audit_id": str(uuid.uuid4()),

        "timestamp_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),


        # ----------------------------------------------------
        # USER QUERY
        # ----------------------------------------------------
        "query": query,


        # ----------------------------------------------------
        # GRAPHRAG EXECUTION
        # ----------------------------------------------------
        "graphrag": {

            "method":
                graphrag_result.get(
                    "method"
                ),

            "return_code":
                graphrag_result.get(
                    "return_code"
                ),

            "latency_seconds":
                graphrag_result.get(
                    "latency_seconds"
                ),

            "stderr":
                graphrag_result.get(
                    "stderr"
                ),

            "answer_length":
                len(
                    graphrag_result.get(
                        "answer",
                        ""
                    )
                )
        },


        # ----------------------------------------------------
        # CITATION DETECTION
        # ----------------------------------------------------
        "citation": (
            citation_info
            if citation_info is not None
            else {}
        ),


        # ----------------------------------------------------
        # ALL RUNTIME GUARDRAIL STAGES
        # ----------------------------------------------------
        "guardrail_stages": {

            "input":
                result_to_dict(
                    input_result
                ),

            "scope":
                result_to_dict(
                    scope_result
                ),

            "indirect_injection":
                result_to_dict(
                    indirect_injection_result
                ),

            "citation_validation":
                result_to_dict(
                    citation_validation_result
                ),

            "grounding":
                result_to_dict(
                    grounding_result
                ),

            "sensitive_data":
                result_to_dict(
                    sensitive_data_result
                ),

            "output":
                result_to_dict(
                    output_result
                )
        },


        # ----------------------------------------------------
        # FINAL GUARDRAIL DECISION
        # ----------------------------------------------------
        "final":
            result_to_dict(
                final_result
            )
    }


    # --------------------------------------------------------
    # WRITE JSONL AUDIT RECORD
    # --------------------------------------------------------
    with open(
        log_file,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            json.dumps(
                audit_record,
                ensure_ascii=False
            )
            + "\n"
        )


    return audit_record

    
#-----------------------------28. run_runtime_guardrailed_graphrag----------------------------#
# -----------------------------28. run_runtime_guardrailed_graphrag----------------------------#

# ============================================================
# STEP 11C — RUNTIME GUARDED GRAPHRAG PIPELINE
# ============================================================

def run_runtime_guardrailed_graphrag(
    query: str,
    method: str = "local"
):

    pipeline_start = time.perf_counter()

    # ========================================================
    # STAGE 1 — INPUT GUARDRAIL
    # ========================================================

    input_result = input_guardrail(
        query
    )

    # --------------------------------------------------------
    # BLOCK BEFORE GRAPHRAG EXECUTION
    # --------------------------------------------------------

    if input_result.status == "BLOCK":

        final_result = GuardrailResult(
            stage="FINAL",
            status="BLOCK",
            reasons=[
                "Request blocked by input guardrail before GraphRAG execution."
            ] + input_result.reasons,
            score=1.0
        )

        # ----------------------------------------------------
        # WRITE AUDIT LOG EVEN WHEN INPUT IS BLOCKED
        # ----------------------------------------------------

        blocked_graphrag_result = {
            "method": method,
            "return_code": None,
            "latency_seconds": 0.0,
            "stderr": "",
            "answer": ""
        }

        audit_record = write_guardrail_audit_log(

            query=query,

            graphrag_result=
                blocked_graphrag_result,

            citation_info=
                None,

            input_result=
                input_result,

            scope_result=
                None,

            indirect_injection_result=
                None,

            citation_validation_result=
                None,

            grounding_result=
                None,

            sensitive_data_result=
                None,

            output_result=
                None,

            final_result=
                final_result
        )

        return {

            "query":
                query,

            "method":
                method,

            "answer":
                None,

            "input_result":
                input_result,

            "graphrag_result":
                None,

            "citation_info":
                None,

            "scope_result":
                None,

            "indirect_injection_result":
                None,

            "citation_validation_result":
                None,

            "citation_validation_raw":
                None,

            "grounding_result":
                None,

            "sensitive_data_result":
                None,

            "output_result":
                None,

            "final_result":
                final_result,

            "pipeline_latency_seconds":
                time.perf_counter()
                - pipeline_start,

            "audit_record":
                audit_record
        }


    # ========================================================
    # STAGE 2 — REAL GRAPHRAG QUERY
    # ========================================================

    graphrag_result = run_graphrag_query(
        query=query,
        method=method
    )


    # --------------------------------------------------------
    # GRAPHRAG EXECUTION FAILURE
    # --------------------------------------------------------

    if graphrag_result["return_code"] != 0:

        final_result = GuardrailResult(
            stage="FINAL",
            status="BLOCK",
            reasons=[
                "GraphRAG query execution failed."
            ],
            score=1.0
        )

        # ----------------------------------------------------
        # WRITE AUDIT LOG EVEN WHEN GRAPHRAG FAILS
        # ----------------------------------------------------

        audit_record = write_guardrail_audit_log(

            query=query,

            graphrag_result=
                graphrag_result,

            citation_info=
                None,

            input_result=
                input_result,

            scope_result=
                None,

            indirect_injection_result=
                None,

            citation_validation_result=
                None,

            grounding_result=
                None,

            sensitive_data_result=
                None,

            output_result=
                None,

            final_result=
                final_result
        )

        return {

            "query":
                query,

            "method":
                method,

            "answer":
                None,

            "input_result":
                input_result,

            "graphrag_result":
                graphrag_result,

            "citation_info":
                None,

            "scope_result":
                None,

            "indirect_injection_result":
                None,

            "citation_validation_result":
                None,

            "citation_validation_raw":
                None,

            "grounding_result":
                None,

            "sensitive_data_result":
                None,

            "output_result":
                None,

            "final_result":
                final_result,

            "pipeline_latency_seconds":
                time.perf_counter()
                - pipeline_start,

            "audit_record":
                audit_record
        }


    answer = graphrag_result["answer"]


    # ========================================================
    # STAGE 3 — AUTOMATIC CITATION DETECTION
    # ========================================================

    citation_info = detect_graphrag_citations(
        answer
    )


    # ========================================================
    # STAGE 4 — DOMAIN / SCOPE GUARDRAIL
    # ========================================================

    scope_result = out_of_scope_guardrail(
        query=query,
        citation_info=citation_info
    )


    # ========================================================
    # STAGE 5 — INDIRECT PROMPT INJECTION
    # ========================================================

    indirect_injection_result = (
        indirect_prompt_injection_guardrail(
            answer
        )
    )


    # ========================================================
    # STAGE 6 — CITATION SUPPORT / MISMATCH
    # ========================================================

    citation_validation_result = (
        citation_validation_guardrail(
            answer
        )
    )


    # ========================================================
    # STAGE 7 — GROUNDING
    # ========================================================

    grounding_result = grounding_guardrail(

        query=query,

        answer=answer,

        citations_present=
            citation_info[
                "citations_present"
            ],

        evidence_count=
            citation_info[
                "evidence_count"
            ],

        min_evidence_count=1
    )


    # ========================================================
    # STAGE 8 — PII / SENSITIVE BANKING DATA
    # ========================================================

    sensitive_data_result = (
        sensitive_banking_data_guardrail(
            answer
        )
    )


    # ========================================================
    # STAGE 9 — OUTPUT GUARDRAIL
    # ========================================================

    citation_validation_raw = (
        validate_real_graphrag_citations(
            answer
        )
    )

    claims_warned = (
        citation_validation_raw[
            "claims_warned"
        ]
    )


    output_result = output_guardrail(

        query=query,

        answer=answer,

        citations_present=
            citation_info[
                "citations_present"
            ],

        evidence_count=
            citation_info[
                "evidence_count"
            ],

        unsupported_claim_count=
            claims_warned
    )


    # ========================================================
    # STAGE 10 — FINAL DECISION
    # ========================================================

    stage_results = [

        input_result,

        scope_result,

        indirect_injection_result,

        citation_validation_result,

        grounding_result,

        sensitive_data_result,

        output_result
    ]


    final_result = (
        aggregate_guardrail_results(
            stage_results
        )
    )


    # ========================================================
    # TOTAL LATENCY
    # ========================================================

    total_latency = (
        time.perf_counter()
        - pipeline_start
    )


    # ========================================================
    # STAGE 11 — COMPLETE AUDIT LOG
    # ========================================================

    audit_record = write_guardrail_audit_log(

        query=query,

        graphrag_result=
            graphrag_result,

        citation_info=
            citation_info,

        input_result=
            input_result,

        scope_result=
            scope_result,

        indirect_injection_result=
            indirect_injection_result,

        citation_validation_result=
            citation_validation_result,

        grounding_result=
            grounding_result,

        sensitive_data_result=
            sensitive_data_result,

        output_result=
            output_result,

        final_result=
            final_result
    )


    # ========================================================
    # RETURN COMPLETE RUNTIME RESULT
    # ========================================================

    return {

        "query":
            query,

        "method":
            method,

        "answer":
            answer,

        "input_result":
            input_result,

        "graphrag_result":
            graphrag_result,

        "citation_info":
            citation_info,

        "scope_result":
            scope_result,

        "indirect_injection_result":
            indirect_injection_result,

        "citation_validation_result":
            citation_validation_result,

        "citation_validation_raw":
            citation_validation_raw,

        "grounding_result":
            grounding_result,

        "sensitive_data_result":
            sensitive_data_result,

        "output_result":
            output_result,

        "final_result":
            final_result,

        "pipeline_latency_seconds":
            total_latency,

        "audit_record":
            audit_record
    }
    
    
    
#-----------------------------29. print_runtime_guardrail_report----------------------------#

    
# ============================================================
# STEP 11D — PROFESSIONAL RUNTIME REPORT
# ============================================================

def print_runtime_guardrail_report(
    result,
    show_answer=True
):

    width = 105

    print(
        "\n"
        + "=" * width
    )

    print(
        " Banking and Regulatory Compliance GraphRAG PoC — "
        "RUNTIME GUARDRAIL PIPELINE"
    )

    print(
        "=" * width
    )

    print(
        f"Query        : "
        f"{result['query']}"
    )

    print(
        f"Method       : "
        f"{result['method']}"
    )

    print(
        f"Final Status : "
        f"{result['final_result'].status}"
    )

    print(
        f"Total Latency: "
        f"{result['pipeline_latency_seconds']:.2f} sec"
    )

    print(
        "-" * width
    )

    stages = [

        (
            "Input",
            result.get(
                "input_result"
            )
        ),

        (
            "Scope",
            result.get(
                "scope_result"
            )
        ),

        (
            "Indirect Injection",
            result.get(
                "indirect_injection_result"
            )
        ),

        (
            "Citation Support",
            result.get(
                "citation_validation_result"
            )
        ),

        (
            "Grounding",
            result.get(
                "grounding_result"
            )
        ),

        (
            "Sensitive Data",
            result.get(
                "sensitive_data_result"
            )
        ),

        (
            "Output",
            result.get(
                "output_result"
            )
        )
    ]

    print(
        f"{'CONTROL':<28}"
        f"{'STATUS':<12}"
        f"DECISION"
    )

    print(
        "-" * width
    )

    for name, stage in stages:

        if stage is None:

            print(
                f"{name:<28}"
                f"{'NOT RUN':<12}"
                f"-"
            )

            continue

        reason = (
            stage.reasons[0]
            if stage.reasons
            else ""
        )

        print(
            f"{name:<28}"
            f"{stage.status:<12}"
            f"{reason}"
        )


    print(
        "-" * width
    )

    print(
        "FINAL DECISION"
    )

    for reason in (
        result[
            "final_result"
        ].reasons
    ):

        print(
            "  -",
            reason
        )


    if (
        show_answer
        and result.get(
            "answer"
        )
    ):

        print(
            "\n"
            + "-" * width
        )

        print(
            "GRAPHRAG ANSWER"
        )

        print(
            "-" * width
        )

        print(
            result[
                "answer"
            ]
        )


    print(
        "=" * width
    )
    
    

