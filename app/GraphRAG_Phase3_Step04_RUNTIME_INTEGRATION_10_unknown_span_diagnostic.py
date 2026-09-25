"""
Phase 3 Step 04
Artifact 10 - Exact UNKNOWN_SPAN_ID diagnostic.

No LLM calls.
Uses the saved governed live-run research plan and matrix,
reconstructs the trusted retrieval/catalog deterministically,
and computes:

matrix referenced span IDs - trusted catalog span IDs
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any


PHASE3_ROOT = Path(__file__).resolve().parents[1]

PHASE2_ROOT = Path(
    r"C:\Users\chen_\Documents\_67_2026_Job_Hunting_After_Wells_Fargo"
    r"\_67_39_RAG_GraphRAG_Agent_GraphRAG"
    r"\_67_39_11_GraphRAG_Phase2_POC"
    r"\evaluation_migrated"
)

INPUT_PATH = (
    PHASE3_ROOT
    / "results"
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_09_governed_live_graph.json"
)

OUTPUT_PATH = (
    PHASE3_ROOT
    / "results"
    / "GraphRAG_Phase3_Step04_RUNTIME_INTEGRATION_11_unknown_span_diagnostic.json"
)

DEEPSEEK_MODULE = (
    "GraphRAG_Phase_02_Section_06_07_deepseek_span_guard"
)

if str(PHASE2_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE2_ROOT))


def collect_matrix_ids(matrix: Any) -> dict[str, Any]:

    rows = (
        matrix.get("rows", [])
        if isinstance(matrix, dict)
        else []
    )

    row_evidence_ids: set[str] = set()
    field_evidence_ids: set[str] = set()

    by_bank: dict[str, dict[str, list[str]]] = {}

    for row in rows:

        bank = str(row.get("bank", "UNKNOWN"))

        row_ids = [
            x
            for x in row.get("evidence", [])
            if isinstance(x, str)
        ]

        field_ids: list[str] = []

        field_evidence = row.get(
            "field_evidence",
            {},
        )

        if isinstance(field_evidence, dict):

            for _, values in field_evidence.items():

                if isinstance(values, list):

                    field_ids.extend(
                        x
                        for x in values
                        if isinstance(x, str)
                    )

        row_evidence_ids.update(row_ids)
        field_evidence_ids.update(field_ids)

        by_bank[bank] = {
            "row_evidence_ids":
                sorted(set(row_ids)),
            "field_evidence_ids":
                sorted(set(field_ids)),
        }

    return {
        "row_evidence_ids":
            sorted(row_evidence_ids),
        "field_evidence_ids":
            sorted(field_evidence_ids),
        "all_matrix_ids":
            sorted(
                row_evidence_ids
                | field_evidence_ids
            ),
        "by_bank":
            by_bank,
    }


def main():

    print("")
    print("=" * 76)
    print(
        "PHASE 3 STEP 04-07D — "
        "EXACT UNKNOWN_SPAN_ID DIAGNOSTIC"
    )
    print("=" * 76)

    saved = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    plan = saved["research_plan"]
    matrix = saved["research_matrix"]

    ds = importlib.import_module(
        DEEPSEEK_MODULE
    )

    (
        base,
        candidates,
        seed,
        scorer,
        _Client,
    ) = ds.load()

    # Reconstruct the same seed-source contract.
    sources = [
        base.source_record(
            row,
            i + 1,
        )
        for i, row in enumerate(
            seed.to_dict("records")
        )
    ]

    seed_count = len(sources)

    print(
        "SAVED PLAN ACTION:",
        plan.get("action"),
    )

    print(
        "SAVED PLAN REQUESTS:",
        len(
            plan.get(
                "requests",
                [],
            )
        ),
    )

    # IMPORTANT:
    # Reuse the saved plan.
    # No Planning LLM call.
    if plan.get("action") == "retrieve":

        base.retrieve(
            plan["requests"],
            candidates,
            sources,
            scorer,
        )

    print(
        "SEED SOURCE COUNT:",
        seed_count,
    )

    print(
        "SOURCE COUNT AFTER REPLAYED RETRIEVAL:",
        len(sources),
    )

    catalog = ds.make_catalog(
        sources
    )

    trusted_ids = set(
        str(x)
        for x in catalog.keys()
    )
        
    # ===== 在这里加入 similarity diagnostic =====

    import difflib

    target_unknown = "S2:c562e8d2314199054eb7"

    closest = difflib.get_close_matches(
        target_unknown,
        sorted(trusted_ids),
        n=10,
        cutoff=0.50,
    )

    print("")
    print("UNKNOWN SPAN:")
    print(" ", target_unknown)

    print("")
    print("CLOSEST TRUSTED SPAN IDS:")

    for sid in closest:
        ratio = difflib.SequenceMatcher(
            None,
            target_unknown,
            sid,
        ).ratio()

        print(
            f"  {ratio:.3f}  {sid}"
        )

    # ===== 原来的程序继续 =====

    matrix_refs = collect_matrix_ids(
        matrix
    )

    row_ids = set(
        matrix_refs[
            "row_evidence_ids"
        ]
    )

    field_ids = set(
        matrix_refs[
            "field_evidence_ids"
        ]
    )

    all_matrix_ids = set(
        matrix_refs[
            "all_matrix_ids"
        ]
    )

    unknown_row = (
        row_ids
        - trusted_ids
    )

    unknown_field = (
        field_ids
        - trusted_ids
    )

    unknown_all = (
        all_matrix_ids
        - trusted_ids
    )

    print("")
    print(
        "TRUSTED CATALOG IDS:",
        len(trusted_ids),
    )

    print(
        "MATRIX ROW-EVIDENCE IDS:",
        len(row_ids),
    )

    print(
        "MATRIX FIELD-EVIDENCE IDS:",
        len(field_ids),
    )

    print(
        "MATRIX UNIQUE IDS:",
        len(all_matrix_ids),
    )

    print("")
    print(
        "UNKNOWN ROW-EVIDENCE IDS:",
        len(unknown_row),
    )

    for sid in sorted(
        unknown_row
    ):
        print(
            "  ",
            sid,
        )

    print("")
    print(
        "UNKNOWN FIELD-EVIDENCE IDS:",
        len(unknown_field),
    )

    for sid in sorted(
        unknown_field
    ):
        print(
            "  ",
            sid,
        )

    print("")
    print(
        "ALL UNKNOWN IDS:",
        len(unknown_all),
    )

    for sid in sorted(
        unknown_all
    ):
        print(
            "  ",
            sid,
        )

    # Identify affected banks.
    affected_banks = {}

    for bank, refs in (
        matrix_refs[
            "by_bank"
        ].items()
    ):

        bank_row_unknown = sorted(
            set(
                refs[
                    "row_evidence_ids"
                ]
            )
            - trusted_ids
        )

        bank_field_unknown = sorted(
            set(
                refs[
                    "field_evidence_ids"
                ]
            )
            - trusted_ids
        )

        if (
            bank_row_unknown
            or bank_field_unknown
        ):

            affected_banks[bank] = {
                "unknown_row_ids":
                    bank_row_unknown,
                "unknown_field_ids":
                    bank_field_unknown,
            }

    print("")
    print(
        "AFFECTED BANKS:",
        len(affected_banks),
    )

    for bank, details in (
        affected_banks.items()
    ):

        print("")
        print(
            "BANK:",
            bank,
        )

        print(
            "  UNKNOWN ROW IDS:",
            details[
                "unknown_row_ids"
            ],
        )

        print(
            "  UNKNOWN FIELD IDS:",
            details[
                "unknown_field_ids"
            ],
        )

    result = {
        "saved_run_failure_type":
            saved.get(
                "failure_type"
            ),

        "saved_run_final_status":
            saved.get(
                "final_status"
            ),

        "seed_source_count":
            seed_count,

        "replayed_source_count":
            len(sources),

        "trusted_catalog_count":
            len(trusted_ids),

        "matrix_row_evidence_id_count":
            len(row_ids),

        "matrix_field_evidence_id_count":
            len(field_ids),

        "matrix_unique_id_count":
            len(all_matrix_ids),

        "unknown_row_ids":
            sorted(unknown_row),

        "unknown_field_ids":
            sorted(unknown_field),

        "all_unknown_ids":
            sorted(unknown_all),

        "affected_banks":
            affected_banks,

        "llm_calls":
            0,

        "network_calls":
            0,

        "planning_rerun":
            False,

        "research_rerun":
            False,

        "legacy_run_live_executed":
            False,

        "phase2_modified":
            False,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("")
    print("=" * 76)

    if unknown_all:

        print(
            "ROOT-CAUSE SIGNAL: "
            "MATRIX REFERENCES IDS OUTSIDE "
            "THE RECONSTRUCTED TRUSTED CATALOG"
        )

    else:

        print(
            "ROOT-CAUSE SIGNAL: "
            "ALL MATRIX IDS EXIST IN THE "
            "RECONSTRUCTED TRUSTED CATALOG"
        )

    print(
        "LLM CALLS: 0"
    )

    print(
        "PLANNING RERUN: NO"
    )

    print(
        "RESEARCH RERUN: NO"
    )

    print(
        "PHASE 2 MODIFIED: NO"
    )

    print(
        "RESULT ARTIFACT:",
        OUTPUT_PATH,
    )

    print(
        "STEP 04-07D: COMPLETE"
    )

    print("=" * 76)


if __name__ == "__main__":
    main()
