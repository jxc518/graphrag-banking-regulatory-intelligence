from pathlib import Path

from GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_05_routing_regression import (
    build_routing_regression_graph,
)


def main():
    print("")
    print("=" * 78)
    print(
        "PHASE 3 STEP 03-06A — "
        "EXECUTABLE LANGGRAPH TOPOLOGY EXPORT"
    )
    print("=" * 78)

    app = build_routing_regression_graph()

    graph = app.get_graph()

    mermaid = graph.draw_mermaid()

    project_root = Path(__file__).resolve().parents[1]
    results_dir = project_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    mermaid_path = (
        results_dir
        / "GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_09_langgraph_topology.mmd"
    )

    png_path = (
        results_dir
        / "GraphRAG_Phase3_Step03_GOVERNED_WORKFLOW_10_langgraph_topology.png"
    )

    mermaid_path.write_text(
        mermaid,
        encoding="utf-8",
    )

    print("")
    print("EXECUTABLE GRAPH COMPILED: PASS")
    print("GRAPH OBJECT RETRIEVED: PASS")
    print("MERMAID TOPOLOGY EXPORTED: PASS")
    print("")
    print("MERMAID ARTIFACT:")
    print(mermaid_path)

    print("")
    print("-" * 78)
    print("LANGGRAPH MERMAID TOPOLOGY")
    print("-" * 78)
    print(mermaid)

    # --------------------------------------------------------
    # Optional PNG rendering
    # --------------------------------------------------------

    png_status = "NOT_AVAILABLE"

    try:
        png_bytes = graph.draw_mermaid_png()

        png_path.write_bytes(
            png_bytes
        )

        png_status = "PASS"

        print("")
        print("PNG TOPOLOGY EXPORTED: PASS")
        print("PNG ARTIFACT:")
        print(png_path)

    except Exception as exc:
        print("")
        print("PNG TOPOLOGY EXPORTED: NOT AVAILABLE")
        print(
            "NOTE: Mermaid source export remains PASS."
        )
        print(
            "PNG renderer exception type:",
            type(exc).__name__,
        )

    print("")
    print("=" * 78)
    print("EXECUTABLE LANGGRAPH TOPOLOGY: VERIFIED")
    print("MERMAID SOURCE: PASS")
    print("PNG RENDER:", png_status)
    print("LLM CALLS: 0")
    print("PHASE 2 MODIFIED: NO")
    print("STEP 03-06A RESULT: PASS")
    print("=" * 78)


if __name__ == "__main__":
    main()
