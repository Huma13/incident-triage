# RB-001: Disk filling on primary, table and index sizes stable

Runbook ID: RB-001 | Applies to: PostgreSQL 17 | Cause class: data_volume

## Symptom
Disk usage on the primary rises steadily. Table and index sizes do not grow. On-call note says cause unknown.

## Likely cause
WAL (write-ahead log) retained in pg_wal because a replication slot is not advancing. A slot keeps WAL even when no consumer is connected.

## Confirmation
1. Look at pg_replication_slots: check active, restart_lsn, wal_status and safe_wal_size.
2. Find slots where active is false or restart_lsn is far behind the current WAL position.
3. Check pg_wal directory size on the primary.

## First response (propose only, on-call decides)
1. Identify the owner of the inactive slot (standby, logical subscriber, CDC tool).
2. If the consumer is recoverable, restore it so the slot advances.
3. If the consumer is gone permanently, the on-call may drop the slot, accepting that the consumer cannot resume.
4. Consider setting max_slot_wal_keep_size to bound future retention (PG 13+).

## Escalation
SEV1 if disk >= 95%. Otherwise per policy SEV-POLICY-v1.
