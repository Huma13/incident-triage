# PostgreSQL 17: Replication Slots and WAL Retention

Source: PostgreSQL 17 Official Documentation
URL: https://www.postgresql.org/docs/17/warm-standby.html
Documentation section: 26.2.6
Related section: 26.2.6.1

## How replication slots retain WAL

Replication slots provide an automated way to ensure that the primary server does not remove WAL segments until they have been received by all standbys.

Replication slots retain only the number of WAL segments known to be needed by their consumers.

## Disconnected standby behavior

Replication slots can continue retaining WAL even when a standby is disconnected.

This means an inactive or stalled replication consumer can prevent old WAL segments from being recycled.

## Disk exhaustion risk

PostgreSQL explicitly warns that replication slots can cause the server to retain so many WAL segments that they fill up the space allocated for pg_wal.

This can cause primary-server disk usage to increase even when table and index sizes remain stable.

## Configuration safeguard

The PostgreSQL configuration parameter max_slot_wal_keep_size can be used to limit the size of WAL files retained by replication slots.

Other WAL-retention mechanisms include wal_keep_size and WAL archiving through archive_command or archive_library.

## Investigation guidance

When primary disk usage increases while table and index sizes remain stable:

1. Inspect pg_replication_slots.
2. Identify inactive or stalled replication consumers.
3. Examine restart_lsn and wal_status.
4. Correlate slot state with pg_wal disk usage and WAL generation.
5. Check max_slot_wal_keep_size configuration.
6. Confirm the suspected cause before proposing remediation.

Do not automatically drop or advance replication slots. Remediation requires an on-call engineer to assess replication and recovery consequences.

## Citation

PostgreSQL 17 Documentation, Section 26.2.6:
https://www.postgresql.org/docs/17/warm-standby.html#STREAMING-REPLICATION-SLOTS
