"""Dograh's core idea in about 120 lines: a call flow is a graph, and every edge is
a tool the model can call. No API key, no Pipecat needed (standard library only).

What is copied from Dograh's design (api/services/workflow/workflow_graph.py and
pipecat_engine.py):
  - tool name = edge label, lower-cased, non-alphanumerics turned into "_"
  - tool description = the edge's condition text
  - duplicate tool names on one node are rejected
  - the same graph JSON shape the canvas saves (nodes with type/data, edges with data)
  - on a transition the engine swaps the system prompt and tool list BEFORE the
    tool result goes back, and emits a node-transition event for the UI
What is NOT copied: the real model, speech, interruptions, prompt caching, extraction.
The "model" here is a keyword matcher so the run is repeatable.

Run: python mini_workflow.py
"""
import copy
import json
import re

GRAPH = {
    "nodes": [
        {"id": "s", "type": "startCall", "data": {"name": "Greeting", "prompt": "Greet the caller. Ask what they need."}},
        {"id": "b", "type": "agentNode", "data": {"name": "Book", "prompt": "Collect a day and time for the appointment."}},
        {"id": "h", "type": "agentNode", "data": {"name": "Human", "prompt": "Offer to transfer to the front desk."}},
        {"id": "e", "type": "endCall", "data": {"name": "Goodbye", "prompt": "Confirm and say goodbye."}},
    ],
    "edges": [
        {"id": "s-b", "source": "s", "target": "b", "data": {"label": "Wants to book", "condition": "Caller wants an appointment"}},
        {"id": "s-h", "source": "s", "target": "h", "data": {"label": "Wants a person", "condition": "Caller asks for a human"}},
        {"id": "b-e", "source": "b", "target": "e", "data": {"label": "Slot chosen", "condition": "Caller gave a day and a time"}},
        {"id": "h-e", "source": "h", "target": "e", "data": {"label": "Handed off", "condition": "Caller agreed to the transfer"}},
    ],
}


def tool_name(label: str) -> str:  # same rule as Edge.get_function_name() in Dograh
    return re.sub(r"[^a-z0-9]", "_", label.lower())


def validate(graph):
    """Return errors shaped like Dograh's WorkflowError: kind, id, message."""
    errors = []
    starts = [n for n in graph["nodes"] if n["type"] == "startCall"]
    if len(starts) != 1:
        errors.append({"kind": "node", "id": None, "message": f"need exactly one startCall, found {len(starts)}"})
    for n in graph["nodes"]:
        if n["type"] in ("startCall", "agentNode", "endCall") and not n["data"].get("prompt"):
            errors.append({"kind": "node", "id": n["id"], "message": "Prompt is required"})
        names = [tool_name(e["data"]["label"]) for e in graph["edges"] if e["source"] == n["id"]]
        for dup in {x for x in names if names.count(x) > 1}:
            errors.append({"kind": "edge", "id": n["id"], "message": f"duplicate tool name '{dup}'"})
    return errors


class Engine:
    def __init__(self, graph):
        self.graph = copy.deepcopy(graph)  # Dograh pins the definition a run started with
        self.nodes = {n["id"]: n for n in self.graph["nodes"]}
        self.events = []
        self.current = None

    def tools_for(self, node_id):
        return [
            {"name": tool_name(e["data"]["label"]), "description": e["data"]["condition"], "to": e["target"]}
            for e in self.graph["edges"] if e["source"] == node_id
        ]

    def set_node(self, node_id):
        prev = self.current
        self.current = node_id
        node = self.nodes[node_id]
        self.system_prompt = node["data"]["prompt"]  # Dograh swaps this via LLM settings
        self.tools = self.tools_for(node_id)
        self.events.append({"type": "rtf-node-transition", "payload": {
            "node_id": node_id, "node_name": node["data"]["name"],
            "previous_node_id": prev, "previous_node_name": self.nodes[prev]["data"]["name"] if prev else None}})

    def call_tool(self, name):
        tool = next(t for t in self.tools if t["name"] == name)
        self.set_node(tool["to"])  # prompt + tools are replaced before the result returns
        return {"status": "done"}


def scripted_model(system_prompt, tools, heard):
    """Stand-in for the LLM: pick the first tool whose condition shares a keyword with what was heard."""
    for t in tools:
        if any(w in heard.lower() for w in re.findall(r"[a-z]{4,}", t["description"].lower())):
            return t["name"]
    return None


if __name__ == "__main__":
    print("validate(good graph):", validate(GRAPH))
    bad = copy.deepcopy(GRAPH)
    bad["edges"].append({"id": "s-b2", "source": "s", "target": "b", "data": {"label": "wants TO book", "condition": "x"}})
    print("validate(duplicate edge label):", validate(bad))

    eng = Engine(GRAPH)
    eng.set_node("s")
    for heard in ["hi, I want an appointment", "tuesday works, ten in the morning, what time slots exist? ten is fine", "thanks"]:
        print(f"\ncaller: {heard!r}")
        print(f"  node={eng.nodes[eng.current]['data']['name']}  tools={[t['name'] for t in eng.tools]}")
        choice = scripted_model(eng.system_prompt, eng.tools, heard)
        print(f"  model calls: {choice}")
        if choice:
            eng.call_tool(choice)
    print("\nevents a UI would receive:")
    for e in eng.events:
        print(" ", json.dumps(e))
