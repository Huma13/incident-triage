from langgraph.graph import END, START, StateGraph

from agents.state import IncidentState
from agents.triage import triage_agent
from agents.investigator import investigator_agent
from agents.evidence import evidence_verifier
from policies.engine import evaluate_policy


def policy_node(state: IncidentState) -> dict:
    incident = state["incident"]

    # Detect worsening disk usage from the incident description.
    summary = incident.get("alert", {}).get("summary", "").lower()

    worsening = any(
        word in summary
        for word in ("increasing", "rising", "worsening", "steadily")
    )

    result = evaluate_policy(
        incident=incident,
        cause_class=state.get("cause_class"),
        evidence_verified=state.get("evidence_verified", False),
        semantic_support_verified=state.get(
            "semantic_support_verified", False
        ),
        worsening=worsening,
        competing_cause_classes=len(
            state.get("competing_cause_classes", [])
        ) or 1,
        symptom_in_corpus=bool(state.get("verified_evidence")),
        service_available=state.get("service_available", True),
        data_loss_risk=state.get("data_loss_risk", False),
    )

    return {
        "policy_result": result,
        "status": result["status"],
        "graph_steps": state.get("graph_steps", 0) + 1,
    }


def build_graph():
    workflow = StateGraph(IncidentState)

    workflow.add_node("triage", triage_agent)
    workflow.add_node("investigation", investigator_agent)
    workflow.add_node("evidence_verification", evidence_verifier)
    workflow.add_node("policy", policy_node)

    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "investigation")
    workflow.add_edge("investigation", "evidence_verification")
    workflow.add_edge("evidence_verification", "policy")
    workflow.add_edge("policy", END)

    return workflow.compile()


incident_graph = build_graph()


def run_incident_triage(incident: dict, run_id: str = "") -> dict:
    initial_state: IncidentState = {
        "run_id": run_id,
        "incident": incident,
        "graph_steps": 0,
        "tool_calls": 0,
        "competing_cause_classes": [],
        "service_available": True,
        "data_loss_risk": False,
    }

    return incident_graph.invoke(initial_state)
