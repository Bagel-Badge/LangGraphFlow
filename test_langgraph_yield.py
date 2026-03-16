from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    text: str

def my_node(state: State):
    yield {"text": "A"}
    yield {"text": "B"}
    yield {"text": "C"}

workflow = StateGraph(State)
workflow.add_node("my_node", my_node)
workflow.add_edge(START, "my_node")
workflow.add_edge("my_node", END)
app = workflow.compile()

for update in app.stream({"text": ""}, stream_mode="updates"):
    print(update)
