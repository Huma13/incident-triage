import json
import os

from agents.state import IncidentState


def triage_agent(state: IncidentState) -> dict:
    incident = state["incident"]
    alert = incident["alert"]

    labels = alert.get("labels", {})
    metrics = alert.get("metrics", [])

    incident_text = json.dumps(incident, indent=2)

    # Controlled test mode for deterministic evaluation.
    if os.getenv("USE_LLM_STUB", "false").lower() == "true":
        return {
            "initial_hypothesis": "replication_slot_retaining_wal",
            "cause_class": "data_volume",
            "triage_reasoning": (
                "Primary disk usage is elevated while table and "
                "index sizes remain stable. WAL retention by a "
                "replication slot is a plausible explanation."
            ),
            "investigation_query": (
                "PostgreSQL replication slots retaining WAL, "
                "restart_lsn, inactive slots and disk exhaustion"
            ),
            "graph_steps": state.get("graph_steps", 0) + 1,
        }

    # Real LLM configuration is required outside test mode.
    base_url = os.getenv("LLM_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL_ID")

    if not all([base_url, api_key, model]):
        raise RuntimeError("LLM configuration is incomplete.")

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=int(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
    )

    prompt = f"""
You are a PostgreSQL incident triage analyst.

Analyze this incident:
{incident_text}

Labels: {json.dumps(labels)}
Metrics: {json.dumps(metrics)}

Return ONLY valid JSON with these fields:
- initial_hypothesis: concise snake_case hypothesis
- cause_class: one of saturation, contention, configuration,
  dependency_failure, data_volume
- triage_reasoning: brief evidence-based explanation
- investigation_query: focused PostgreSQL documentation search

Do not invent evidence.
Do not assign severity or routing.
Do not recommend executing SQL or changing production systems.
"""

    response = llm.invoke(prompt)

    try:
        result = json.loads(response.content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Triage agent returned invalid JSON.") from exc

    allowed_classes = {
        "saturation",
        "contention",
        "configuration",
        "dependency_failure",
        "data_volume",
    }

    if result.get("cause_class") not in allowed_classes:
        raise RuntimeError("Triage agent returned an invalid cause class.")

    required_fields = [
        "initial_hypothesis",
        "triage_reasoning",
        "investigation_query",
    ]

    if any(not result.get(field) for field in required_fields):
        raise RuntimeError("Triage agent omitted a required field.")

    return {
        **result,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }
