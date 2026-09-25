from __future__ import annotations

import json
import sys
from copy import deepcopy
from typing import Any, Dict, TextIO


# ============================================================
# CLOUDWATCH STRUCTURED JSON SINK
# ============================================================

class CloudWatchStructuredJsonSink:

    """
    Additive structured-log sink.

    IMPORTANT:
    - Does NOT call boto3.
    - Does NOT call CloudWatch API.
    - Does NOT modify ECS.
    - Writes one canonical telemetry event as one JSON line.
    - ECS awslogs can transport stdout to CloudWatch Logs.
    """

    name = "cloudwatch_structured_json"

    def __init__(
        self,
        stream: TextIO | None = None,
    ):

        self.stream = (
            stream
            if stream is not None
            else sys.stdout
        )


    def emit(
        self,
        event: Dict[str, Any],
    ) -> None:

        record = deepcopy(event)

        # Add only sink-level classification.
        # Do not mutate caller's canonical event.
        record["telemetry_sink"] = "cloudwatch"

        line = json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )

        # Exactly one JSON event per line.
        self.stream.write(
            line + "\n"
        )

        self.stream.flush()
