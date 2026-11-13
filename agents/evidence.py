from agents.state import IncidentState


def evidence_verifier(state: IncidentState) -> dict:
    hypothesis = state.get("initial_hypothesis", "")
    cause_class = state.get("cause_class", "")

    evidence = state.get("verified_evidence", [])

    if not hypothesis or not cause_class or not evidence:
        return {
            "semantic_support_verified": False,
            "investigation_notes": (
                "Semantic verification failed: "
                "hypothesis, cause class, or verified evidence missing."
            ),
            "graph_steps": state.get("graph_steps", 0) + 1,
        }

    # Require direct support for the hypothesis in the
    # retrieved documentation, not merely a valid citation.
    hypothesis_terms = set(
        hypothesis.lower().replace("_", " ").split()
    )

    supported = False

    for item in evidence:
        text = item.get("text", "").lower()

        if (
            item.get("verification", {}).get("valid")
            and all(term in text for term in hypothesis_terms)
        ):
            supported = True
            break

    return {
        "semantic_support_verified": supported,
        "investigation_notes": (
            "Hypothesis terms found in verified documentation."
            if supported
            else "Retrieved documentation does not directly "
                 "support all hypothesis terms."
        ),
        "graph_steps": state.get("graph_steps", 0) + 1,
    }
