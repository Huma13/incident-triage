from typing import Any, TypedDict


class IncidentState(TypedDict, total=False):
    # Original incident
    run_id: str
    incident: dict[str, Any]

    # Triage agent output
    initial_hypothesis: str
    cause_class: str
    triage_reasoning: str

    # Investigation agent output
    investigation_query: str
    retrieved_evidence: list[dict[str, Any]]
    verified_evidence: list[dict[str, Any]]
    rejected_evidence: list[dict[str, Any]]
    competing_cause_classes: list[str]

    # Verification
    evidence_verified: bool
    semantic_support_verified: bool
    investigation_notes: str

    # Operational signals
    worsening: bool
    service_available: bool
    data_loss_risk: bool

    # Execution budgets
    graph_steps: int
    tool_calls: int

    # Final result
    policy_result: dict[str, Any]
    status: str
    error: str
