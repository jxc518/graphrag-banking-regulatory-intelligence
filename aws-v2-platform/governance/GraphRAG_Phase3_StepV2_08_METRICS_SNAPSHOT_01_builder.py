from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


METRIC_DEFINITIONS = [
    {
        "metric": "Guardrail Pass Rate",
        "key": "guardrail_pass_rate",
        "classification": "DERIVABLE",
    },
    {
        "metric": "Retry Rate",
        "key": "retry_rate",
        "classification": "DERIVABLE",
    },
    {
        "metric": "Retry Recovery Rate",
        "key": "retry_recovery_rate",
        "classification": "DERIVABLE",
    },
    {
        "metric": "Escalation Rate",
        "key": "escalation_rate",
        "classification": "DERIVABLE",
    },
    {
        "metric": "Missing Evidence Rate",
        "key": "missing_evidence_rate",
        "classification": "DERIVABLE",
    },
    {
        "metric": "Citation Mismatch Rate",
        "key": "citation_mismatch_rate",
        "classification": "ADDITIVE_SIGNAL_REQUIRED",
    },
    {
        "metric": "Provenance Failure Rate",
        "key": "provenance_failure_rate",
        "classification": "DERIVABLE",
    },
    {
        "metric": "Unknown Span Rate",
        "key": "unknown_span_rate",
        "classification": "DERIVABLE",
    },
    {
        "metric": "Provider Schema Failure Rate",
        "key": "provider_schema_failure_rate",
        "classification": "DERIVABLE",
    },
    {
        "metric": "Judge Rejection Rate",
        "key": "judge_rejection_rate",
        "classification": "DERIVABLE",
    },
    {
        "metric": "False Positive Guardrail Rate",
        "key": "false_positive_guardrail_rate",
        "classification": "DERIVABLE_EVALUATION",
    },
    {
        "metric": "P95 Latency",
        "key": "p95_latency_ms",
        "classification": "DERIVABLE",
    },
    {
        "metric": "Cost per Governed Query",
        "key": "cost_per_governed_query",
        "classification": "ADDITIVE_SIGNAL_REQUIRED",
    },
]


def build_snapshot(
    metrics: Dict[str, Any],
    source_name: str,
) -> Dict[str, Any]:

    rows: List[Dict[str, Any]] = []

    for definition in METRIC_DEFINITIONS:

        key = definition["key"]
        value = metrics.get(key)

        if value is None:

            if (
                definition["classification"]
                == "ADDITIVE_SIGNAL_REQUIRED"
            ):
                status = "SIGNAL_REQUIRED"

            elif (
                definition["classification"]
                == "DERIVABLE_EVALUATION"
            ):
                status = "EVALUATION_DATA_REQUIRED"

            else:
                status = "NOT_AVAILABLE"

        else:
            status = "AVAILABLE"

        rows.append(
            {
                "metric":
                    definition["metric"],

                "metric_key":
                    key,

                "value":
                    value,

                "status":
                    status,

                "classification":
                    definition["classification"],

                "source":
                    source_name,
            }
        )

    return {
        "schema_version": "1.0",
        "generated_utc":
            datetime.now(timezone.utc).isoformat(),

        "metric_count":
            len(rows),

        "metrics":
            rows,
    }


def write_snapshot(
    snapshot: Dict[str, Any],
    json_path: Path,
    csv_path: Path,
) -> None:

    json_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path.write_text(
        json.dumps(
            snapshot,
            indent=2,
        ),
        encoding="utf-8",
    )

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "metric",
                "metric_key",
                "value",
                "status",
                "classification",
                "source",
            ],
        )

        writer.writeheader()

        for row in snapshot["metrics"]:
            writer.writerow(row)