# PostgreSQL 17: pg_replication_slots

Source: PostgreSQL 17 Official Documentation
URL: https://www.postgresql.org/docs/17/view-pg-replication-slots.html
Documentation section: 52.19

## Purpose

The pg_replication_slots view lists all replication slots that currently exist on the database cluster, along with their current state.

Related documentation: Section 26.2.6 and Chapter 47.

## Diagnostic fields

### active

True if this slot is currently being streamed.

### restart_lsn

The address (LSN) of the oldest WAL that might still be required by the consumer of this slot. This WAL will not be automatically removed during checkpoints unless this LSN gets behind more than max_slot_wal_keep_size from the current LSN.

NULL if the LSN of this slot has never been reserved.

### wal_status

Availability of WAL files claimed by this slot.

- reserved: Claimed files are within max_wal_size.
- extended: max_wal_size is exceeded, but files are still retained by the replication slot or wal_keep_size.
- unreserved: The slot no longer retains the required WAL files, and some may be removed at the next checkpoint.
- lost: The slot is no longer usable.

### safe_wal_size

The number of bytes that can be written to WAL before this slot is in danger of entering the lost state.

NULL for lost slots, and when max_slot_wal_keep_size is -1.

### inactive_since

The time when the slot became inactive.

NULL if the slot is currently being streamed.

## Additional diagnostic fields

### slot_name

A unique, cluster-wide identifier for the replication slot.

### slot_type

The slot type: physical or logical.

### active_pid

The process ID of the session streaming data for this slot. NULL if inactive.

### xmin

The oldest transaction that this slot needs the database to retain. VACUUM cannot remove tuples deleted by later transactions.

### catalog_xmin

The oldest transaction affecting system catalogs that this slot needs the database to retain.

### invalidation_reason

The reason for slot invalidation, if applicable. Possible values include wal_removed, rows_removed, and wal_level_insufficient.

## Investigation guidance

An inactive slot with an old restart_lsn can indicate that a disconnected or stalled consumer is preventing WAL recycling.

Correlate slot state with pg_wal disk usage, WAL generation rate, consumer health, and PostgreSQL configuration before concluding that a slot is responsible for disk growth.

Do not automatically drop, recreate, or advance a replication slot. These actions can cause data loss or break replication. A qualified on-call engineer must decide on remediation.

## Citation

PostgreSQL 17 Documentation, Section 52.19:
https://www.postgresql.org/docs/17/view-pg-replication-slots.html
