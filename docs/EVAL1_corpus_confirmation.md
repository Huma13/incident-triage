# Evaluation 1: Corpus Confirmation and Plan

Team: Huma (PES2UG24AM066), Neeraj (PES2UG24AM046), Jaswanth (PES2UG24AM068)
Course: UE24AM342AA5 | Project: Mini Project 08, Incident Triage and Runbook Assistant

## Corpus
- PostgreSQL 17 documentation (monitoring, WAL, replication chapters)
- Runbooks RB-001 (WAL retention / disk), RB-002 (replication lag), RB-003 (connection exhaustion)
- Severity and escalation policy SEV-POLICY-v1

## The section 4.1 case
Alert: "Disk usage on the primary is climbing steadily. Table and index sizes are not growing. On-call note: disk filling, cause unknown."

Why single-pass retrieval fails: a search for "disk usage" returns storage and table-maintenance pages. The cause (a replication slot retaining WAL) is in the replication chapter and is not mentioned in the alert.

### Passages the case depends on (PostgreSQL 17)
Exact section anchors to be verified against the downloaded docs before submission.

| ID | Source | What it says (paraphrased) |
|---|---|---|
| P1 | Replication Slots (streaming replication / warm standby chapter) | A slot makes the server retain WAL a consumer still needs, even when the consumer is disconnected. |
| P2 | pg_replication_slots view (postgresql.org/docs/17/view-pg-replication-slots.html) | active shows whether the slot is being streamed; restart_lsn is the oldest WAL the consumer may need; wal_status shows whether retained WAL exceeds max_wal_size. |
| P3 | Replication configuration, max_slot_wal_keep_size (postgresql.org/docs/17/runtime-config-replication.html) | At the default of -1, slots may retain unlimited WAL; a non-negative value caps retention at checkpoint time. |
| P4 | Runbook RB-001 | Confirmation steps and first response for WAL retention. |

### Test values
- disk_used_percent = 88.2, threshold 85.0, role primary
- Table and index size metrics flat
- Expected cause class: data_volume
- Expected hypothesis: replication_slot_retaining_wal
- Expected severity: SEV2, route page-secondary (disk >= 85%, primary, worsening)
- Version-specific response: mention max_slot_wal_keep_size (available since PG 13); for PG 17 also inactive_since column in pg_replication_slots

## Plan
Stages 0-8 as in the implementation guide. Priority this week: working end-to-end path, then the section 4.1 case, then verification and escalation, then evaluation.
