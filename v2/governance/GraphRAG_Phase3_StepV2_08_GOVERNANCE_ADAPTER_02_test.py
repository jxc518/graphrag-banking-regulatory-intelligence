from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path


HERE = Path(__file__).resolve().parent

ADAPTER_FILE = (
    HERE
    / "GraphRAG_Phase3_StepV2_08_GOVERNANCE_ADAPTER_01_state.py"
)


def load_module(name, path):

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"CANNOT_LOAD_MODULE:{path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


mod = load_module(
    "v2_08_governance_adapter",
    ADAPTER_FILE,
)


cases = [

    # --------------------------------------------------------
    # 1. Judge executed and PASS
    # --------------------------------------------------------

    {
        "name": "APPROVED",
        "state": {
            "judge_allowed": True,
            "judge_verdict": "PASS",
            "final_status": "APPROVED",
        },
        "expected": {
            "judge_executed": True,
            "judge_rejected": False,
            "escalated": False,
        },
    },

    # --------------------------------------------------------
    # 2. Judge executed and asks for revision
    # --------------------------------------------------------

    {
        "name": "PENDING_REVIEW",
        "state": {
            "judge_allowed": True,
            "judge_verdict": "REVISE",
            "final_status": "PENDING_REVIEW",
        },
        "expected": {
            "judge_executed": True,
            "judge_rejected": True,
            "escalated": False,
        },
    },

    # --------------------------------------------------------
    # 3. Escalated before semantic Judge
    # --------------------------------------------------------

    {
        "name": "ESCALATED_NOT_EVALUATED",
        "state": {
            "judge_allowed": False,
            "judge_verdict": "NOT_EVALUATED",
            "final_status": "ESCALATED",
        },
        "expected": {
            "judge_executed": False,
            "judge_rejected": False,
            "escalated": True,
        },
    },

    # --------------------------------------------------------
    # 4. Initial / incomplete state
    # --------------------------------------------------------

    {
        "name": "NOT_EVALUATED",
        "state": {
            "judge_allowed": False,
            "judge_verdict": "NOT_EVALUATED",
            "final_status": None,
        },
        "expected": {
            "judge_executed": False,
            "judge_rejected": False,
            "escalated": False,
        },
    },
]


print("")
print("=" * 70)
print("STEP V2-08D-04C")
print("GOVERNED STATE -> METRIC FIELD ADAPTER")
print("=" * 70)

failed = []


for case in cases:

    original = deepcopy(
        case["state"]
    )

    result = (
        mod.governed_state_to_metric_fields(
            case["state"]
        )
    )

    print("")
    print(
        "===== CASE:",
        case["name"],
        "====="
    )

    print(
        "judge_allowed    :",
        result["judge_allowed"],
    )

    print(
        "judge_verdict    :",
        result["judge_verdict"],
    )

    print(
        "final_status     :",
        result["final_status"],
    )

    print(
        "judge_executed   :",
        result["judge_executed"],
    )

    print(
        "judge_rejected   :",
        result["judge_rejected"],
    )

    print(
        "escalated        :",
        result["escalated"],
    )

    for key, expected in (
        case["expected"].items()
    ):

        actual = result[key]

        passed = (
            actual == expected
        )

        print(
            f"{key:20}: "
            f"EXPECTED={expected} "
            f"ACTUAL={actual} "
            f"PASS={passed}"
        )

        if not passed:
            failed.append(
                f"{case['name']}:{key}"
            )

    immutable = (
        case["state"] == original
    )

    print(
        "SOURCE IMMUTABLE :",
        "PASS"
        if immutable
        else "FAIL",
    )

    if not immutable:
        failed.append(
            f"{case['name']}:IMMUTABILITY"
        )


print("")
print("===== UNPROVEN SIGNAL SAFETY =====")

probe = (
    mod.governed_state_to_metric_fields(
        {
            "judge_allowed": True,
            "judge_verdict": "PASS",
            "final_status": "APPROVED",
        }
    )
)

unproven_safe = all(
    probe[field] is None
    for field in [
        "evidence_required",
        "missing_evidence",
        "provenance_evaluated",
        "provenance_failed",
        "span_evaluated",
        "unknown_span",
    ]
)

print(
    "EVIDENCE NOT INVENTED   :",
    "PASS"
    if (
        probe["evidence_required"] is None
        and probe["missing_evidence"] is None
    )
    else "FAIL",
)

print(
    "PROVENANCE NOT INVENTED :",
    "PASS"
    if (
        probe["provenance_evaluated"] is None
        and probe["provenance_failed"] is None
    )
    else "FAIL",
)

print(
    "SPAN NOT INVENTED       :",
    "PASS"
    if (
        probe["span_evaluated"] is None
        and probe["unknown_span"] is None
    )
    else "FAIL",
)

if not unproven_safe:
    failed.append(
        "UNPROVEN_SIGNAL_SAFETY"
    )


print("")
print("===== FINAL GATE =====")

if not failed:

    print("STEP V2-08D-04C: PASS")
    print("JUDGE EXECUTION MAPPING: PASS")
    print("JUDGE REJECTION MAPPING: PASS")
    print("ESCALATION MAPPING: PASS")
    print("NOT_EVALUATED HANDLING: PASS")
    print("UNPROVEN SIGNAL SAFETY: PASS")
    print("SOURCE IMMUTABILITY: PASS")

else:

    print("STEP V2-08D-04C: BLOCKED")
    print("FAILED CHECKS:", failed)

    raise SystemExit(1)