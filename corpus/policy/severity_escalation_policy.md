# Severity and Escalation Policy (v1)

Policy ID: SEV-POLICY-v1. Applied by deterministic code, never by the model.

## Severity levels
- SEV1: Primary unavailable, or data loss risk, or disk >= 95% with no known cause.
- SEV2: Resource at or above threshold and still worsening on the primary (disk >= 85%, replication lag growing, connections near max), service still up.
- SEV3: Threshold breached on a replica or non-production, stable or slowly worsening.
- SEV4: Informational, no breach.

## Routing
- SEV1 -> incident-commander
- SEV2 -> page-secondary
- SEV3, SEV4 -> self-serve runbook

## Escalation to human (overrides routing)
Escalate instead of answering when any holds:
1. Two or more cause classes have similar evidence support.
2. The symptom is outside the corpus.
3. Verification of citations or semantic support fails.
4. Agent budgets (steps, tool calls, time) are exhausted.
5. The LLM provider is unavailable.

## Cause classes
saturation, contention, configuration, dependency_failure, data_volume
