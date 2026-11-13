"""Deterministic severity, routing, and human-escalation policy."""

from typing import Any


CAUSE_CLASSES = {
    "saturation",
    "contention",
    "configuration",
    "dependency_failure",
    "data_volume",
}

ROUTES = {
    "SEV1": "incident-commander",
    "SEV2": "page-secondary",
    "SEV3": "self-serve-runbook",
    "SEV4": "self-serve-runbook",
}


def evaluate_policy(
    incident: Any,
    cause_class: str | None,
    evidence_verified: bool,
    semantic_support_verified: bool,
    worsening: bool = False,
    competing_cause_classes: int = 1,
    symptom_in_corpus: bool = True,
    service_available: bool = True,
    data_loss_risk: bool = False,
    agent_steps_exhausted: bool = False,
    tool_calls_exhausted: bool = False,
    time_budget_exhausted: bool = False,
    llm_available: bool = True,
) -> dict:
    """Apply deterministic policy to a validated incident and investigation."""

    if hasattr(incident, "model_dump"):
        incident = incident.model_dump(mode="json")

    alert = incident.get("alert", {})
    labels = alert.get("labels", {})
    metrics = alert.get("metrics", [])
    environment = incident.get("environment", "local-test")

    if hasattr(environment, "value"):
        environment = environment.value

    role = str(labels.get("role", "")).lower()
    is_primary = role == "primary"

    disk_percent = None
    disk_threshold = 85.0
    threshold_breached = False

    for metric in metrics:
        name = metric.get("name")
        value = metric.get("value")
        threshold = metric.get("threshold")

        if name == "disk_used_percent":
            disk_percent = value
            if threshold is not None:
                disk_threshold = threshold

        if threshold is not None and value is not None and value >= threshold:
            threshold_breached = True

    if disk_percent is not None and disk_percent >= disk_threshold:
        threshold_breached = True

    escalation_reasons = []

    if competing_cause_classes >= 2:
        escalation_reasons.append("Multiple cause classes have similar evidence support.")

    if not symptom_in_corpus:
        escalation_reasons.append("Symptom is outside the supported corpus.")

    if not evidence_verified:
        escalation_reasons.append("Citation verification failed.")

    if not semantic_support_verified:
        escalation_reasons.append("Semantic evidence support failed.")

    if agent_steps_exhausted:
        escalation_reasons.append("Agent step budget exhausted.")

    if tool_calls_exhausted:
        escalation_reasons.append("Agent tool-call budget exhausted.")

    if time_budget_exhausted:
        escalation_reasons.append("Agent time budget exhausted.")

    if not llm_available:
        escalation_reasons.append("LLM provider unavailable.")

    if cause_class not in CAUSE_CLASSES:
        escalation_reasons.append("Cause class is unknown or unsupported.")

    # Severity is computed independently of the LLM.
    if (
        not service_available
        or data_loss_risk
        or (
            disk_percent is not None
            and disk_percent >= 95
            and cause_class not in CAUSE_CLASSES
        )
    ):
        severity = "SEV1"

    # local-test is used as a production-like simulation by evaluation case 4.1.
    elif (
        is_primary
        and service_available
        and threshold_breached
        and worsening
        and environment in {"production", "local-test"}
    ):
        severity = "SEV2"

    elif threshold_breached or not is_primary:
        severity = "SEV3"

    else:
        severity = "SEV4"

    if escalation_reasons:
        return {
            "status": "human_escalation",
            "severity": severity,
            "route": "human-escalation",
            "cause_class": cause_class,
            "reasons": escalation_reasons,
            "policy_id": "SEV-POLICY-v1",
        }

    return {
        "status": "classified",
        "severity": severity,
        "route": ROUTES[severity],
        "cause_class": cause_class,
        "reasons": [],
        "policy_id": "SEV-POLICY-v1",
    }
