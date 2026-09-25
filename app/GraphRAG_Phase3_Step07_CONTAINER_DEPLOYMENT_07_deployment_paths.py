from __future__ import annotations

import os
from pathlib import Path


INDEX_ENV = "GRAPHRAG_PHASE3_INDEX_OUTPUT"
CONFIG_ENV = "GRAPHRAG_PHASE2_RUNTIME_CONFIG"


def resolve_index_output(
    frozen_index_resolver=None,
) -> Path:
    """
    Resolve the persisted GraphRAG index for the current
    deployment environment.

    Priority:
      1. Phase 3 deployment environment override.
      2. Frozen Phase 2 resolver for backward-compatible
         local development behavior.
    """

    explicit = os.environ.get(INDEX_ENV)

    if explicit:
        path = Path(explicit).expanduser()

        if not path.exists():
            raise FileNotFoundError(
                f"{INDEX_ENV} does not exist: {path}"
            )

        return path.resolve()

    if frozen_index_resolver is None:
        raise RuntimeError(
            f"{INDEX_ENV} is not set and no frozen "
            "Phase 2 resolver was supplied."
        )

    path = Path(
        frozen_index_resolver()
    ).expanduser()

    if not path.exists():
        raise FileNotFoundError(
            f"Frozen GraphRAG index does not exist: {path}"
        )

    return path.resolve()


def resolve_runtime_config() -> Path:
    """
    Resolve GraphRAG runtime configuration.

    Docker/AWS should explicitly provide
    GRAPHRAG_PHASE2_RUNTIME_CONFIG.
    """

    explicit = os.environ.get(CONFIG_ENV)

    if not explicit:
        raise RuntimeError(
            f"{CONFIG_ENV} is not set."
        )

    path = Path(explicit).expanduser()

    settings = path / "settings.yaml"

    if not settings.exists():
        raise FileNotFoundError(
            f"settings.yaml not found under: {path}"
        )

    return path.resolve()


def deployment_info(
    frozen_index_resolver=None,
) -> dict[str, str]:
    index = resolve_index_output(
        frozen_index_resolver
    )

    config = resolve_runtime_config()

    return {
        "index_output": str(index),
        "runtime_config": str(config),
        "settings": str(config / "settings.yaml"),
    }
