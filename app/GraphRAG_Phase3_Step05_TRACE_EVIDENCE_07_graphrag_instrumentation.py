from __future__ import annotations

import contextvars
import functools
from typing import Any

from langsmith import traceable

from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)


_INSTALLED = False

# Each concurrent Global Map coroutine keeps its own ContextVar value.
_map_batch_counter: contextvars.ContextVar[int] = contextvars.ContextVar(
    "graphrag_map_batch_counter",
    default=0,
)

# We need a simple global sequence generator only to assign display ids.
_next_map_batch_id = 0


def _allocate_map_batch_id() -> int:
    global _next_map_batch_id
    _next_map_batch_id += 1
    return _next_map_batch_id


def install_graphrag_tracing() -> dict[str, Any]:
    """
    Install read-only runtime observability wrappers around real GraphRAG methods.

    IMPORTANT:
    - Does NOT modify GraphRAG source files.
    - Does NOT alter prompts.
    - Does NOT alter retrieval.
    - Does NOT alter concurrency.
    - Does NOT alter model parameters.
    - Does NOT alter Phase 2 governance behavior.
    """
    global _INSTALLED

    if _INSTALLED:
        return {
            "installed": True,
            "already_installed": True,
            "source_modified": False,
        }

    # ------------------------------------------------------------------
    # Preserve originals
    # ------------------------------------------------------------------

    original_local_stream_search = LocalSearch.stream_search
    original_local_build_context = LocalSearchMixedContext.build_context

    original_global_stream_search = GlobalSearch.stream_search
    original_global_build_context = GlobalCommunityContext.build_context
    original_global_map_batch = GlobalSearch._map_response_single_batch
    original_global_reduce = GlobalSearch._stream_reduce_response

    # ------------------------------------------------------------------
    # LOCAL SEARCH
    # ------------------------------------------------------------------

    @functools.wraps(original_local_build_context)
    @traceable(
        name="GraphRAG Local — Build Context",
        run_type="chain",
        tags=["Phase3", "GraphRAG", "LocalSearch", "Context"],
    )
    def traced_local_build_context(self, *args, **kwargs):
        return original_local_build_context(self, *args, **kwargs)

    @functools.wraps(original_local_stream_search)
    async def traced_local_stream_search(self, *args, **kwargs):
        @traceable(
            name="GraphRAG Local Search",
            run_type="chain",
            tags=["Phase3", "GraphRAG", "LocalSearch"],
        )
        async def run_original():

            # ----------------------------------------------------------
            # Instrument the REAL Local Search model completion call.
            #
            # This wrapper is installed only for the duration of this
            # Local Search invocation and is restored afterward.
            # It changes observability only, not prompts, parameters,
            # retrieval, model selection, or returned content.
            # ----------------------------------------------------------

            original_completion_async = self.model.completion_async

            @functools.wraps(original_completion_async)
            @traceable(
                name="GraphRAG Local — LLM Answer Generation",
                run_type="llm",
                tags=[
                    "Phase3",
                    "GraphRAG",
                    "LocalSearch",
                    "LLM",
                    "AnswerGeneration",
                ],
                metadata={
                    "graphrag_stage": "local_answer_generation",
                    "instrumentation_only": True,
                },
            )
            async def traced_completion_async(*c_args, **c_kwargs):
                return await original_completion_async(
                    *c_args,
                    **c_kwargs,
                )

            self.model.completion_async = traced_completion_async

            try:
                chunks = []

                async for chunk in original_local_stream_search(
                    self,
                    *args,
                    **kwargs,
                ):
                    chunks.append(chunk)

                return chunks

            finally:
                self.model.completion_async = original_completion_async

        chunks = await run_original()

        for chunk in chunks:
            yield chunk

    # ------------------------------------------------------------------
    # GLOBAL SEARCH
    # ------------------------------------------------------------------

    @functools.wraps(original_global_build_context)
    @traceable(
        name="GraphRAG Global — Build Community Context",
        run_type="chain",
        tags=["Phase3", "GraphRAG", "GlobalSearch", "Context"],
    )
    async def traced_global_build_context(self, *args, **kwargs):
        return await original_global_build_context(self, *args, **kwargs)

    @functools.wraps(original_global_map_batch)
    async def traced_global_map_batch(self, *args, **kwargs):
        batch_id = _allocate_map_batch_id()

        traced_call = traceable(
            name=f"GraphRAG Global — Map Batch {batch_id:03d}",
            run_type="llm",
            tags=[
                "Phase3",
                "GraphRAG",
                "GlobalSearch",
                "Map",
                f"MapBatch-{batch_id:03d}",
            ],
            metadata={
                "graphrag_stage": "global_map",
                "map_batch_id": batch_id,
            },
        )(original_global_map_batch)

        token = _map_batch_counter.set(batch_id)

        try:
            return await traced_call(
                self,
                *args,
                **kwargs,
            )
        finally:
            _map_batch_counter.reset(token)

    @functools.wraps(original_global_reduce)
    async def traced_global_reduce(self, *args, **kwargs):
        @traceable(
            name="GraphRAG Global — Reduce Synthesis",
            run_type="llm",
            tags=[
                "Phase3",
                "GraphRAG",
                "GlobalSearch",
                "Reduce",
            ],
            metadata={
                "graphrag_stage": "global_reduce",
            },
        )
        async def consume_reduce():
            chunks = []

            async for chunk in original_global_reduce(
                self,
                *args,
                **kwargs,
            ):
                chunks.append(chunk)

            return chunks

        chunks = await consume_reduce()

        for chunk in chunks:
            yield chunk

    @functools.wraps(original_global_stream_search)
    async def traced_global_stream_search(self, *args, **kwargs):
        @traceable(
            name="GraphRAG Global Search",
            run_type="chain",
            tags=["Phase3", "GraphRAG", "GlobalSearch"],
        )
        async def run_original():
            chunks = []

            async for chunk in original_global_stream_search(
                self,
                *args,
                **kwargs,
            ):
                chunks.append(chunk)

            return chunks

        chunks = await run_original()

        for chunk in chunks:
            yield chunk

    # ------------------------------------------------------------------
    # Install monkey patches
    # ------------------------------------------------------------------

    LocalSearchMixedContext.build_context = traced_local_build_context
    LocalSearch.stream_search = traced_local_stream_search

    GlobalCommunityContext.build_context = traced_global_build_context
    GlobalSearch._map_response_single_batch = traced_global_map_batch
    GlobalSearch._stream_reduce_response = traced_global_reduce
    GlobalSearch.stream_search = traced_global_stream_search

    _INSTALLED = True

    return {
        "installed": True,
        "already_installed": False,
        "local_methods": [
            "LocalSearchMixedContext.build_context",
            "LocalSearch.stream_search",
        ],
        "global_methods": [
            "GlobalCommunityContext.build_context",
            "GlobalSearch.stream_search",
            "GlobalSearch._map_response_single_batch",
            "GlobalSearch._stream_reduce_response",
        ],
        "source_modified": False,
        "phase2_modified": False,
    }


if __name__ == "__main__":
    result = install_graphrag_tracing()

    print("=" * 70)
    print("STEP05-08A — GRAPHRAG INSTRUMENTATION INSTALL")
    print("=" * 70)

    for key, value in result.items():
        print(f"{key}: {value}")

    print("=" * 70)
    print("LLM CALLS: 0")
    print("NETWORK CALLS: 0")
    print("GRAPHRAG SOURCE MODIFIED: NO")
    print("PHASE 2 MODIFIED: NO")
    print("=" * 70)

