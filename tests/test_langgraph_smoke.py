from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class SmokeState(TypedDict):
    message: str
    planning_complete: bool
    research_complete: bool


def planning_node(state: SmokeState):
    print("NODE EXECUTED: Planning Agent")

    return {
        "message": "Planning completed",
        "planning_complete": True,
    }


def research_node(state: SmokeState):
    print("NODE EXECUTED: Research Agent")

    assert state["planning_complete"] is True

    return {
        "message": "Research completed",
        "research_complete": True,
    }


builder = StateGraph(SmokeState)

builder.add_node("Planning Agent", planning_node)
builder.add_node("Research Agent", research_node)

builder.add_edge(START, "Planning Agent")
builder.add_edge("Planning Agent", "Research Agent")
builder.add_edge("Research Agent", END)

app = builder.compile()


initial_state = {
    "message": "Start",
    "planning_complete": False,
    "research_complete": False,
}

result = app.invoke(initial_state)


assert result["planning_complete"] is True
assert result["research_complete"] is True
assert result["message"] == "Research completed"


print("")
print("============================================")
print("LANGGRAPH STATEGRAPH SMOKE TEST: PASS")
print("============================================")
print("Planning Complete:", result["planning_complete"])
print("Research Complete:", result["research_complete"])
print("Final Message:", result["message"])
print("LLM CALLS: 0")
print("NETWORK CALLS: 0")
