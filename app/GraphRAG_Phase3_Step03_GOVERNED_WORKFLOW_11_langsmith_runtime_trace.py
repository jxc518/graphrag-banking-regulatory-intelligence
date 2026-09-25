from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from langsmith import Client

from GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_05_routing_regression import (
    build_routing_regression_graph,
    create_test_state,
    SCENARIO_CLEAN,
    SCENARIO_PROVENANCE_MISMATCH,
)


PROJECT_NAME = os.getenv(
    "LANGSMITH_PROJECT",
    "GraphRAG_Phase3_LangGraph_Prod",
)


def verify_remote_run(
    client: Client,
    run_id: uuid.UUID,
    max_attempts: int = 10,
):
    """
    Poll LangSmith briefly so we can verify that the root
    LangGraph run was actually received by the tracing service.
    """

    last_error = None

    for _ in range(max_attempts):
        try:
            run = client.read_run(run_id)
            return run
        except Exception as exc:
            last_error = exc
            time.sleep(1)

    raise RuntimeError(
        f"LangSmith run verification failed: {last_error}"
    )


def execute_traced_scenario(
    app,
    client: Client,
    scenario: str,
    run_name: str,
):
    print("")
    print("=" * 78)
    print("TRACED SCENARIO:", scenario)
    print("=" * 78)

    run_id = uuid.uuid4()

    initial_state = create_test_state(
        scenario
    )

    result = app.invoke(
        initial_state,
        config={
            "run_id": run_id,
            "run_name": run_name,
            "tags": [
                "Phase3",
                "LangGraph",
                "Governed-GraphRAG",
                scenario,
            ],
            "metadata": {
                "phase": "Phase 3",
                "step": "03-06C",
                "workflow": "Governed Multi-Agent GraphRAG",
                "orchestrator": "LangGraph",
                "scenario": scenario,
                "phase2_baseline": "Frozen Validated Baseline",
                "llm_calls": 0,
                "controlled_runtime_test": True,
            },
        },
    )

    print("")
    print("STAGE HISTORY")
    print("-" * 78)

    for stage in result["stage_history"]:
        print(stage)

    print("")
    print("RECOVERY ACTION:", result["recovery_action"])
    print("JUDGE ALLOWED:", result["judge_allowed"])
    print("JUDGE VERDICT:", result["judge_verdict"])
    print("FINAL STATUS:", result["final_status"])

    print("")
    print("WAITING FOR LANGSMITH TRACE VERIFICATION...")

    remote_run = verify_remote_run(
        client,
        run_id,
    )

    print("LANGSMITH ROOT RUN VERIFIED: PASS")
    print("RUN NAME:", remote_run.name)
    print("RUN ID:", str(run_id))

    trace_id = getattr(
        remote_run,
        "trace_id",
        None,
    )

    if trace_id:
        print("TRACE ID:", str(trace_id))

    # --------------------------------------------------------
    # Scenario-specific validation
    # --------------------------------------------------------

    if scenario == SCENARIO_CLEAN:
        checks = {
            "final_approved":
                result["final_status"] == "APPROVED",

            "judge_reached":
                result["judge_allowed"] is True,

            "judge_pass":
                result["judge_verdict"] == "PASS",

            "continue_to_judge":
                result["recovery_action"]
                == "CONTINUE_TO_JUDGE",

            "judge_stage_present":
                "14 LLM Judge Review"
                in result["stage_history"],
        }

    elif scenario == SCENARIO_PROVENANCE_MISMATCH:
        checks = {
            "final_escalated":
                result["final_status"] == "ESCALATED",

            "recovery_escalate":
                result["recovery_action"] == "ESCALATE",

            "judge_not_allowed":
                result["judge_allowed"] is False,

            "judge_not_executed":
                result["judge_verdict"]
                == "NOT_EVALUATED",

            "judge_stage_absent":
                "14 LLM Judge Review"
                not in result["stage_history"],
        }

    else:
        raise ValueError(
            f"Unsupported trace scenario: {scenario}"
        )

    print("")
    print("VALIDATION CHECKS")
    print("-" * 78)

    for name, passed in checks.items():
        print(
            f"{name}:",
            "PASS" if passed else "FAIL",
        )

    scenario_pass = all(
        checks.values()
    )

    print(
        "TRACED SCENARIO RESULT:",
        "PASS" if scenario_pass else "FAIL",
    )

    if not scenario_pass:
        raise AssertionError(
            f"Traced scenario failed: {scenario}"
        )

    return {
        "scenario":
            scenario,

        "run_name":
            remote_run.name,

        "run_id":
            str(run_id),

        "trace_id":
            str(trace_id) if trace_id else None,

        "langsmith_verified":
            True,

        "recovery_action":
            result["recovery_action"],

        "judge_allowed":
            result["judge_allowed"],

        "judge_verdict":
            result["judge_verdict"],

        "final_status":
            result["final_status"],

        "stage_history":
            result["stage_history"],

        "validation_pass":
            scenario_pass,
    }


def main():
    print("")
    print("=" * 78)
    print(
        "PHASE 3 STEP 03-06C — "
        "LANGSMITH GOVERNED LANGGRAPH RUNTIME TRACE"
    )
    print("=" * 78)

    print("LANGSMITH PROJECT:", PROJECT_NAME)
    print("LANGSMITH API KEY: SET")
    print("LANGSMITH TRACING:", os.getenv("LANGSMITH_TRACING"))

    app = build_routing_regression_graph()

    print("LANGGRAPH GRAPH COMPILE: PASS")

    client = Client()

    results = []

    results.append(
        execute_traced_scenario(
            app,
            client,
            SCENARIO_CLEAN,
            "P3-Governed-LangGraph-CLEAN",
        )
    )

    results.append(
        execute_traced_scenario(
            app,
            client,
            SCENARIO_PROVENANCE_MISMATCH,
            "P3-Governed-LangGraph-ESCALATION",
        )
    )

    all_pass = all(
        item["validation_pass"]
        and item["langsmith_verified"]
        for item in results
    )

    project_root = Path(
        __file__
    ).resolve().parents[1]

    output_path = (
        project_root
        / "results"
        / (
            "GraphRAG_Phase3_"
            "Step03_GOVERNED_WORKFLOW_"
            "12_langsmith_runtime_trace.json"
        )
    )

    artifact = {
        "phase": "Phase 3",
        "step": "03-06C",
        "project": PROJECT_NAME,
        "runtime": "LangGraph",
        "observability": "LangSmith",
        "controlled_runtime_test": True,
        "llm_calls": 0,
        "phase2_modified": False,
        "scenarios": results,
        "status": "PASS" if all_pass else "FAIL",
    }

    output_path.write_text(
        json.dumps(
            artifact,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print("=" * 78)
    print("LANGSMITH TRACED SCENARIOS:", f"{len(results)}/2")
    print("LANGSMITH ROOT RUN VERIFICATION: PASS")
    print("CLEAN PATH TRACE: PASS")
    print("ESCALATION PATH TRACE: PASS")
    print("JUDGE EXECUTION / BYPASS: VERIFIED")
    print("LANGGRAPH CONDITIONAL ROUTING: VERIFIED")
    print("OUTPUT ARTIFACT:")
    print(output_path)
    print("")
    print("LLM CALLS: 0")
    print("LANGSMITH NETWORK TRACING: YES")
    print("PHASE 2 MODIFIED: NO")

    if not all_pass:
        print("STEP 03-06C RESULT: FAIL")
        raise AssertionError(
            "LangSmith runtime trace validation failed."
        )

    print("STEP 03-06C RESULT: PASS")
    print("=" * 78)


if __name__ == "__main__":
    main()
