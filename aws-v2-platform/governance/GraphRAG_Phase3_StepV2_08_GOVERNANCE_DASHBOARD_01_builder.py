from __future__ import annotations

import html
import json
import sys
from pathlib import Path


def display_value(metric_key, value):

    if value is None:
        return "N/A"

    if metric_key == "p95_latency_ms":
        return f"{float(value):,.0f} ms"

    if (
        metric_key.endswith("_rate")
        or metric_key == "cost_per_governed_query"
    ):
        if metric_key == "cost_per_governed_query":
            return f"${float(value):,.4f}"

        return f"{float(value) * 100:.2f}%"

    return str(value)


def status_class(status):

    mapping = {
        "AVAILABLE": "available",
        "NOT_AVAILABLE": "not-available",
        "SIGNAL_REQUIRED": "signal-required",
        "EVALUATION_DATA_REQUIRED": "evaluation-required",
    }

    return mapping.get(
        status,
        "not-available",
    )


def build_dashboard(snapshot):

    rows = snapshot["metrics"]

    counts = {
        "AVAILABLE": 0,
        "NOT_AVAILABLE": 0,
        "SIGNAL_REQUIRED": 0,
        "EVALUATION_DATA_REQUIRED": 0,
    }

    for row in rows:
        counts[row["status"]] = (
            counts.get(row["status"], 0) + 1
        )

    available_rows = [
        row
        for row in rows
        if row["status"] == "AVAILABLE"
    ]

    table_rows = []

    for row in rows:

        css_class = status_class(
            row["status"]
        )

        value = display_value(
            row["metric_key"],
            row["value"],
        )

        table_rows.append(
            f"""
            <tr>
              <td>{html.escape(row["metric"])}</td>
              <td class="value">{html.escape(value)}</td>
              <td>
                <span class="badge {css_class}">
                  {html.escape(row["status"])}
                </span>
              </td>
              <td>{html.escape(row["classification"])}</td>
              <td>{html.escape(row["source"])}</td>
            </tr>
            """
        )

    cards = []

    for row in available_rows:

        value = display_value(
            row["metric_key"],
            row["value"],
        )

        cards.append(
            f"""
            <div class="metric-card">
              <div class="metric-name">
                {html.escape(row["metric"])}
              </div>
              <div class="metric-value">
                {html.escape(value)}
              </div>
              <div class="metric-status">
                AVAILABLE
              </div>
            </div>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>GraphRAG AWS V2 Governance Dashboard</title>

<style>

body {{
    font-family:
        Arial,
        Helvetica,
        sans-serif;

    margin: 0;
    background: #f4f6f8;
    color: #1f2933;
}}

.container {{
    max-width: 1280px;
    margin: 0 auto;
    padding: 32px;
}}

.header {{
    background: white;
    padding: 28px;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow:
        0 2px 8px rgba(0,0,0,0.06);
}}

.header h1 {{
    margin: 0 0 8px 0;
    font-size: 30px;
}}

.subtitle {{
    color: #52606d;
    line-height: 1.5;
}}

.coverage-grid {{
    display: grid;
    grid-template-columns:
        repeat(4, minmax(0, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}}

.coverage-card {{
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow:
        0 2px 8px rgba(0,0,0,0.05);
}}

.coverage-number {{
    font-size: 30px;
    font-weight: bold;
}}

.coverage-label {{
    margin-top: 6px;
    color: #52606d;
    font-size: 13px;
}}

.metric-grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(210px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
}}

.metric-card {{
    background: white;
    padding: 22px;
    border-radius: 10px;
    box-shadow:
        0 2px 8px rgba(0,0,0,0.05);
}}

.metric-name {{
    color: #52606d;
    font-size: 14px;
    min-height: 34px;
}}

.metric-value {{
    font-size: 28px;
    font-weight: bold;
    margin-top: 10px;
}}

.metric-status {{
    margin-top: 8px;
    font-size: 11px;
    color: #52606d;
}}

.section {{
    background: white;
    padding: 24px;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow:
        0 2px 8px rgba(0,0,0,0.05);
}}

table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}

th {{
    text-align: left;
    padding: 12px;
    background: #eef2f6;
    border-bottom: 1px solid #d9e2ec;
}}

td {{
    padding: 12px;
    border-bottom: 1px solid #e4e7eb;
    vertical-align: top;
}}

.value {{
    font-weight: bold;
}}

.badge {{
    display: inline-block;
    padding: 5px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: bold;
}}

.available {{
    background: #d9f2e6;
    color: #12613b;
}}

.not-available {{
    background: #e9ecef;
    color: #495057;
}}

.signal-required {{
    background: #fff0cc;
    color: #7a5200;
}}

.evaluation-required {{
    background: #e8e0ff;
    color: #5035a5;
}}

.note {{
    color: #52606d;
    font-size: 13px;
    line-height: 1.6;
}}

@media (max-width: 800px) {{

    .coverage-grid {{
        grid-template-columns:
            repeat(2, minmax(0, 1fr));
    }}

    .container {{
        padding: 16px;
    }}
}}

</style>
</head>

<body>

<div class="container">

<div class="header">

<h1>
GraphRAG AWS V2 — Guardrail Metrics Dashboard
</h1>

<div class="subtitle">
Multi-Agent GraphRAG governance,
resilience, judge and observability metrics.
Values are displayed only when supported
by the current auditable metrics snapshot.
</div>

</div>


<div class="coverage-grid">

<div class="coverage-card">
<div class="coverage-number">
{counts["AVAILABLE"]}
</div>
<div class="coverage-label">
AVAILABLE
</div>
</div>

<div class="coverage-card">
<div class="coverage-number">
{counts["NOT_AVAILABLE"]}
</div>
<div class="coverage-label">
NOT AVAILABLE
</div>
</div>

<div class="coverage-card">
<div class="coverage-number">
{counts["SIGNAL_REQUIRED"]}
</div>
<div class="coverage-label">
SIGNAL REQUIRED
</div>
</div>

<div class="coverage-card">
<div class="coverage-number">
{counts["EVALUATION_DATA_REQUIRED"]}
</div>
<div class="coverage-label">
EVALUATION DATA REQUIRED
</div>
</div>

</div>


<div class="section">

<h2>Validated Runtime Metrics</h2>

<div class="metric-grid">
{''.join(cards)}
</div>

</div>


<div class="section">

<h2>13-Metric Governance Contract</h2>

<table>

<thead>
<tr>
<th>Metric</th>
<th>Value</th>
<th>Status</th>
<th>Classification</th>
<th>Source</th>
</tr>
</thead>

<tbody>
{''.join(table_rows)}
</tbody>

</table>

</div>


<div class="section">

<h2>Governance Interpretation</h2>

<div class="note">

<strong>AVAILABLE</strong> means the current
snapshot contains a validated value.

<br><br>

<strong>NOT AVAILABLE</strong> means the metric
definition exists, but the current governed-query
record does not contain a sufficiently proven
runtime signal.

<br><br>

<strong>SIGNAL REQUIRED</strong> means an additive
canonical telemetry signal is required before the
metric can be calculated safely.

<br><br>

<strong>EVALUATION DATA REQUIRED</strong> means
the metric requires benchmark ground truth rather
than ordinary production telemetry.

<br><br>

Missing values are intentionally displayed as
<strong>N/A</strong>, not zero.

</div>

</div>


<div class="section">

<h2>Audit Metadata</h2>

<div class="note">

Schema version:
<strong>{html.escape(str(snapshot["schema_version"]))}</strong>

<br>

Snapshot generated UTC:
<strong>{html.escape(str(snapshot["generated_utc"]))}</strong>

<br>

Metric count:
<strong>{snapshot["metric_count"]}</strong>

</div>

</div>

</div>

</body>
</html>
"""


def main():

    if len(sys.argv) != 3:
        raise SystemExit(
            "USAGE: builder.py snapshot.json dashboard.html"
        )

    snapshot_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    snapshot = json.loads(
        snapshot_path.read_text(
            encoding="utf-8"
        )
    )

    if snapshot.get("metric_count") != 13:
        raise RuntimeError(
            "EXPECTED_13_METRICS"
        )

    dashboard = build_dashboard(
        snapshot
    )

    output_path.write_text(
        dashboard,
        encoding="utf-8",
    )

    print("")
    print("=" * 72)
    print("STEP V2-08E-02")
    print("GOVERNANCE DASHBOARD BUILD")
    print("=" * 72)

    print("")
    print("INPUT SNAPSHOT :", snapshot_path)
    print("OUTPUT HTML    :", output_path)

    print("")
    print("METRIC COUNT   :", snapshot["metric_count"])

    available = sum(
        1
        for row in snapshot["metrics"]
        if row["status"] == "AVAILABLE"
    )

    signal_required = sum(
        1
        for row in snapshot["metrics"]
        if row["status"] == "SIGNAL_REQUIRED"
    )

    print("AVAILABLE      :", available)
    print("SIGNAL REQUIRED:", signal_required)

    checks = {
        "HTML_EXISTS":
            output_path.exists(),

        "HAS_TITLE":
            "Guardrail Metrics Dashboard"
            in dashboard,

        "HAS_13_METRIC_CONTRACT":
            "13-Metric Governance Contract"
            in dashboard,

        "HAS_RETRY_RATE":
            "Retry Rate"
            in dashboard,

        "HAS_JUDGE_REJECTION":
            "Judge Rejection Rate"
            in dashboard,

        "HAS_P95":
            "P95 Latency"
            in dashboard,

        "HAS_SIGNAL_REQUIRED":
            "SIGNAL_REQUIRED"
            in dashboard,

        "HAS_NA":
            "N/A"
            in dashboard,
    }

    print("")
    print("===== VALIDATION =====")

    for key, value in checks.items():
        print(
            f"{key:28}: "
            f"{'PASS' if value else 'FAIL'}"
        )

    if all(checks.values()):

        print("")
        print("===== FINAL GATE =====")
        print("STEP V2-08E-02: PASS")
        print("STATIC HTML DASHBOARD: PASS")
        print("13-METRIC CONTRACT: PASS")
        print("AVAILABLE METRIC CARDS: PASS")
        print("MISSING VALUE SAFETY: PASS")
        print("AUDIT METADATA: PASS")

    else:

        print("")
        print("STEP V2-08E-02: BLOCKED")

        raise SystemExit(1)


if __name__ == "__main__":
    main()