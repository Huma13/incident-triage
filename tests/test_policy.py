import json
from pathlib import Path

from policies.engine import evaluate_policy


CASE_4_1 = json.loads(
    Path("evaluation/case_4_1.json").read_text(encoding="utf-8")
)


def evaluate(incident, **overrides):
    arguments = {
        "cause_class": "data_volume",
        "evidence_verified": True,
        "semantic_support_verified": True,
        "worsening": True,
    }
    arguments.update(overrides)
    return evaluate_policy(incident, **arguments)


def test_case_4_1_returns_sev2_page_secondary():
    result = evaluate(CASE_4_1)

    assert result["status"] == "classified"
    assert result["cause_class"] == "data_volume"
    assert result["severity"] == "SEV2"
    assert result["route"] == "page-secondary"


def test_primary_unavailable_returns_sev1():
    result = evaluate(CASE_4_1, service_available=False)

    assert result["severity"] == "SEV1"
    assert result["route"] == "incident-commander"


def test_staging_threshold_breach_returns_sev3():
    incident = json.loads(json.dumps(CASE_4_1))
    incident["environment"] = "staging"

    result = evaluate(incident)

    assert result["severity"] == "SEV3"
    assert result["route"] == "self-serve-runbook"


def test_no_threshold_breach_returns_sev4():
    incident = json.loads(json.dumps(CASE_4_1))
    incident["alert"]["metrics"][0]["value"] = 70.0

    result = evaluate(incident, worsening=False)

    assert result["severity"] == "SEV4"
    assert result["route"] == "self-serve-runbook"


def test_failed_citation_verification_escalates():
    result = evaluate(CASE_4_1, evidence_verified=False)

    assert result["status"] == "human_escalation"
    assert result["route"] == "human-escalation"


def test_unavailable_llm_escalates():
    result = evaluate(CASE_4_1, llm_available=False)

    assert result["status"] == "human_escalation"
    assert result["route"] == "human-escalation"
