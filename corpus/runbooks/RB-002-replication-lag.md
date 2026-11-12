# RB-002: Replication lag growing on standby

Runbook ID: RB-002 | Applies to: PostgreSQL 17 | Cause class: saturation

## Symptom
Standby replay lag or byte lag increases over time. Reads on the standby return stale data.

## Likely causes
Standby I/O or CPU saturation; long-running queries on standby conflicting with replay; network throughput limits; heavy write burst on primary.

## Confirmation
1. On primary, check pg_stat_replication: write_lag, flush_lag, replay_lag, state.
2. On standby, check pg_stat_activity for long queries and pg_stat_database_conflicts.
3. Check standby disk and CPU utilisation.

## First response
1. If conflicts with long queries, review hot_standby_feedback and max_standby_streaming_delay.
2. If saturation, reduce load on the standby or add capacity.
3. If the standby is disconnected, check network and primary_conninfo.

## Escalation
SEV2 if lag keeps growing on a synchronous standby. Otherwise per SEV-POLICY-v1.
