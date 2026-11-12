# RB-003: Connections near max_connections

Runbook ID: RB-003 | Applies to: PostgreSQL 17 | Cause class: contention

## Symptom
Applications report "too many clients already". Connection count near max_connections. Latency spikes.

## Likely causes
Connection leak in an application; missing connection pooler; many idle-in-transaction sessions holding locks; sudden traffic increase.

## Confirmation
1. Count rows in pg_stat_activity grouped by state and application_name.
2. Look for idle in transaction sessions with old xact_start.
3. Check pg_locks for blocked sessions.

## First response
1. Identify the application with the most connections.
2. Introduce or tune a pooler.
3. Set idle_in_transaction_session_timeout to limit stuck sessions.
4. Do not raise max_connections blindly; memory use grows with it.

## Escalation
SEV2 if new connections are being refused on the primary. Otherwise per SEV-POLICY-v1.
