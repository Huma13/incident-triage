import os

from agents.state import IncidentState
from retrieval.hybrid import hybrid_search
from retrieval.citation_verifier import verify_citation


def investigator_agent(state: IncidentState) -> dict:
    query = state.get("investigation_query", "").strip()

    if not query:
        raise RuntimeError("Investigation query is missing.")

    results = hybrid_search(query, top_k=5)

    verified = []
    rejected = []

    for item in results:
        check = verify_citation(
            source_id=item["source_id"],
            section=item["section"],
            evidence=item["text"],
        )

        evidence_item = {
            **item,
            "verification": check,
        }

        if check["valid"]:
            verified.append(evidence_item)
        else:
            rejected.append(evidence_item)

    # A citation being valid proves its source and excerpt exist.
    # It does not independently prove semantic support.
    evidence_verified = bool(verified) and not rejected

    return {
        "retrieved_evidence": results,
        "verified_evidence": verified,
        "rejected_evidence": rejected,
        "evidence_verified": evidence_verified,
        "semantic_support_verified": False,
        "investigation_notes": (
            f"Retrieved {len(results)} chunks; "
            f"{len(verified)} citations verified; "
            f"{len(rejected)} rejected. "
            "Semantic support still requires independent checking."
        ),
        "tool_calls": state.get("tool_calls", 0) + 1,
        "graph_steps": state.get("graph_steps", 0) + 1,
    }
