"""
Phase 3 Step06 â€” Query Scope Adapter

Serving-layer deterministic bank-scope resolution.

Design goals:
1. Do not modify frozen Phase 2.
2. Do not modify Step04 CLOSED_PASS runtime.
3. Do not mutate base.BANKS.
4. Resolve request scope deterministically.
5. Filter evidence using the canonical Phase 2 source["bank"] field.
"""

from __future__ import annotations

import re

from typing import Any


CANONICAL_BANKS = [
    "Wells Fargo",
    "JPMorgan Chase",
    "Citigroup",
    "Bank of America",
    "Capital One",
]


BANK_ALIASES = {
    "Wells Fargo": [
        "wells fargo",
        "wfc",
    ],
    "JPMorgan Chase": [
        "jpmorgan chase",
        "jpmorgan",
        "jp morgan",
        "jpm",
    ],
    "Citigroup": [
        "citigroup",
        "citibank",
        "citi",
    ],
    "Bank of America": [
        "bank of america",
        "bofa",
        "bac",
    ],
    "Capital One": [
        "capital one",
        "capitalone",
        "cof",
    ],
}


ALL_BANK_PHRASES = [
    "five target banks",
    "five banks",
    "all five banks",
    "all target banks",
]


def resolve_target_period(query: str) -> str | None:
    """
    Resolve an explicit quarterly period from the user query.

    Supported portfolio quarters:
    - 2026Q2 -> quarter ended June 30, 2026
    - 2026Q1 -> quarter ended March 31, 2026
    - 2025Q4 -> quarter ended December 31, 2025
    - 2025Q3 -> quarter ended September 30, 2025

    Also accepts forms such as:
    - "2026 Q1"
    - "2026Q2"
    - "Q4 2025"
    - "quarter ended March 31, 2026"

    Returns None when the query does not explicitly identify a quarter.
    """
    q = str(query or "").strip().lower()

    allowed_periods = {
        "2026Q2",
        "2026Q1",
        "2025Q4",
        "2025Q3",
    }

    # 2026Q1 / 2026 Q1 / 2026-Q1
    match = re.search(
        r"\b(20\d{2})\s*[- ]?\s*q([1-4])\b",
        q,
    )
    if match:
        period = f"{match.group(1)}Q{match.group(2)}"
        return period if period in allowed_periods else None

    # Q1 2026 / Q1-2026
    match = re.search(
        r"\bq([1-4])\s*[- ]?\s*(20\d{2})\b",
        q,
    )
    if match:
        period = f"{match.group(2)}Q{match.group(1)}"
        return period if period in allowed_periods else None

    # Quarter-end date wording
    year_match = re.search(r"\b(20\d{2})\b", q)
    if not year_match:
        return None

    year = year_match.group(1)

    if re.search(r"\b(?:march|mar)\s+31\b", q):
        period = f"{year}Q1"

    elif re.search(r"\b(?:june|jun)\s+30\b", q):
        period = f"{year}Q2"

    elif re.search(
        r"\b(?:september|sept|sep)\s+30\b",
        q,
    ):
        period = f"{year}Q3"

    elif re.search(
        r"\b(?:december|dec)\s+31\b",
        q,
    ):
        period = f"{year}Q4"

    else:
        return None

    return period if period in allowed_periods else None

def resolve_target_banks(query: str) -> list[str]:
    """
    Resolve explicit bank scope from the user query.

    If no supported bank is explicitly identified, return the canonical
    five-bank scope. This preserves the existing validated comparison
    behavior rather than guessing a narrower scope.
    """

    text = (query or "").lower()

    if any(phrase in text for phrase in ALL_BANK_PHRASES):
        return list(CANONICAL_BANKS)

    matched: list[str] = []

    for bank in CANONICAL_BANKS:
        aliases = BANK_ALIASES[bank]

        if any(alias in text for alias in aliases):
            matched.append(bank)

    return matched if matched else list(CANONICAL_BANKS)


def filter_sources(
    sources: list[dict[str, Any]],
    target_banks: list[str],
) -> list[dict[str, Any]]:
    """
    Filter canonical Phase 2 source records by their validated bank field.
    """

    allowed = set(target_banks)

    return [
        source
        for source in sources
        if source.get("bank") in allowed
    ]


def apply_query_scope(
    query: str,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Resolve query bank scope and return request-scoped sources.
    """

    target_banks = resolve_target_banks(query)
    scoped_sources = filter_sources(sources, target_banks)

    return {
        "target_banks": target_banks,
        "sources": scoped_sources,
        "source_count_before": len(sources),
        "source_count_after": len(scoped_sources),
    }


if __name__ == "__main__":

    test_sources = [
        {"source_id": "S1", "bank": "Wells Fargo"},
        {"source_id": "S2", "bank": "JPMorgan Chase"},
        {"source_id": "S3", "bank": "Citigroup"},
        {"source_id": "S4", "bank": "Bank of America"},
        {"source_id": "S5", "bank": "Capital One"},
    ]

    cases = [
        (
            "Wells Fargo 2026 Q2 net charge-offs",
            ["Wells Fargo"],
            1,
        ),
        (
            "Compare Wells Fargo and JPMorgan Chase",
            ["Wells Fargo", "JPMorgan Chase"],
            2,
        ),
        (
            "What did Citi report?",
            ["Citigroup"],
            1,
        ),
        (
            "Compare the five target banks",
            CANONICAL_BANKS,
            5,
        ),
        (
            "Compare credit-risk disclosures",
            CANONICAL_BANKS,
            5,
        ),
    ]

    passed = 0

    for i, (query, expected_banks, expected_count) in enumerate(cases, 1):

        result = apply_query_scope(
            query=query,
            sources=test_sources,
        )

        ok = (
            result["target_banks"] == expected_banks
            and result["source_count_after"] == expected_count
        )

        passed += int(ok)

        print(
            f"CASE {i}: "
            f"{'PASS' if ok else 'FAIL'} | "
            f"banks={result['target_banks']} | "
            f"sources={result['source_count_after']}"
        )

    print("")
    print("=" * 70)
    print(
        f"QUERY SCOPE UNIT SMOKE: "
        f"{passed}/{len(cases)} PASS"
    )
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")
    print("STEP04 MODIFIED: NO")
    print("PHASE 2 MODIFIED: NO")
    print("=" * 70)



# ============================================================
# RUNTIME INSTALLATION
# ============================================================

def install(runtime_module: Any) -> Any:
    """
    Install request-local query-scope behavior into the loaded
    Step04 runtime without modifying frozen Step04 source code.

    Scope is applied at two boundaries:
      1. bootstrap output sources
      2. real LLM payload banks/sources/span_catalog

    The installation is idempotent.
    """

    if getattr(
        runtime_module,
        "_step06_query_scope_adapter_installed",
        False,
    ):
        return runtime_module

    # original_bootstrap = runtime_module.runtime_bootstrap_node
    # original_complete_real = runtime_module.complete_real
    
    original_bootstrap = runtime_module.runtime_bootstrap_node

    # ------------------------------------------------------------
    # Resolve the canonical underlying complete_real function.
    #
    # Multiple dynamically loaded runtime modules can share the
    # same imported research_agent_node function globals.
    # A previous adapter installation may therefore have already
    # rebound complete_real to scoped_complete_real.
    #
    # Unwrap any prior query-scope wrappers so every new adapter
    # closes directly over the canonical Step04 complete_real,
    # never over another scoped_complete_real wrapper.
    # ------------------------------------------------------------

    original_complete_real = runtime_module.complete_real

    while (
        getattr(
            original_complete_real,
            "__name__",
            "",
        )
        == "scoped_complete_real"
    ):
        closure = getattr(
            original_complete_real,
            "__closure__",
            None,
        )

        freevars = getattr(
            original_complete_real.__code__,
            "co_freevars",
            (),
        )

        if not closure:
            break

        closure_map = {
            name: cell.cell_contents
            for name, cell in zip(
                freevars,
                closure,
            )
        }

        previous = closure_map.get(
            "original_complete_real"
        )

        if previous is None:
            break

        original_complete_real = previous

    async def scoped_runtime_bootstrap_node(state):

        update = await original_bootstrap(state)

        query = state.get("query", "")
        sources = update.get("sources", [])

        # scoped = apply_query_scope(
        #     query=query,
        #     sources=sources,
        # )

        # update["sources"] = scoped["sources"]
        # update["target_banks"] = scoped["target_banks"]
        
        scoped = apply_query_scope(
        query=query,
        sources=sources,
          )

        # ------------------------------------------------------------
        # Canonicalize request-local source IDs after scope filtering.
        #
        # Frozen Phase 2 retrieval allocates new source IDs using
        # len(sources) + 1. Query-scope filtering can preserve sparse
        # IDs such as S4 while reducing the list length to one source.
        # Without renumbering, retrieval can then create another S4,
        # corrupting span provenance through duplicate source identity.
        #
        # Copy each record so the frozen bootstrap source objects are
        # not mutated in place.
        # ------------------------------------------------------------

        canonical_sources = [
            dict(source)
            for source in scoped["sources"]
        ]

        for number, source in enumerate(
            canonical_sources,
            start=1,
        ):
            source["source_id"] = f"S{number}"

        update["sources"] = canonical_sources
        update["target_banks"] = scoped["target_banks"]

        print("")
        print("[Step06 Query Scope Adapter]")
        print(
            "  Target banks:",
            ", ".join(scoped["target_banks"]),
        )
        print(
            "  Sources:",
            f"{scoped['source_count_before']} "
            f"-> {scoped['source_count_after']}",
        )

        return update

    async def scoped_complete_real(
        *,
        stage,
        system_prompt,
        payload,
        provider="openai",
    ):

        scoped_payload = dict(payload)

        query = scoped_payload.get("question", "")
        sources = scoped_payload.get("sources", [])

        scoped = apply_query_scope(
            query=query,
            sources=sources,
        )

        scoped_payload["banks"] = scoped["target_banks"]

        if "sources" in scoped_payload:
            scoped_payload["sources"] = scoped["sources"]

        if "span_catalog" in scoped_payload:

            allowed = set(scoped["target_banks"])

            scoped_payload["span_catalog"] = [
                span
                for span in scoped_payload["span_catalog"]
                if span.get("bank") in allowed
            ]

        return await original_complete_real(
            stage=stage,
            system_prompt=system_prompt,
            payload=scoped_payload,
            provider=provider,
        )

    runtime_module.runtime_bootstrap_node = (
        scoped_runtime_bootstrap_node
    )

    runtime_module.complete_real = scoped_complete_real

    # ------------------------------------------------------------
    # Python module-binding fix
    #
    # research_agent_node was originally defined in the Step04
    # live-research module. Its function globals therefore resolve
    # complete_real from that original module namespace, not from
    # the dynamically loaded _08 runtime module.
    #
    # Rebind the ORIGINAL FUNCTION GLOBAL namespace in memory only.
    # No Step04 source file is modified.
    # ------------------------------------------------------------
    research_node = getattr(
        runtime_module,
        "research_agent_node",
        None,
    )

    research_globals = getattr(
        research_node,
        "__globals__",
        None,
    )

    if (
        research_globals is not None
        and "complete_real" in research_globals
    ):
        research_globals["complete_real"] = scoped_complete_real

    runtime_module._step06_query_scope_adapter_installed = True

    return runtime_module

