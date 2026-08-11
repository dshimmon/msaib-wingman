# Ledger Transition Architecture

This record describes the published Wingman Core implementation. It does not
authorize a live transition or claim that the default/live Ledger changed.

## Physical versions

- Version 3 retains the historical `program` and `academic_year` source
  columns behind the private repository adapter.
- Version 4 removes those columns. Generic entity metadata remains the sole
  physical representation for product-owned source fields.
- Migrations 1–3 and their applied names remain immutable. A fresh empty
  database initializes at version 4; an existing version-3 database never
  advances automatically.
- The repository adapter detects exactly version 3 or version 4. A partial or
  ambiguous column shape fails closed.

## Safety boundary

```text
application connection lifetime
  -> canonical target identity
  -> cooperative shared lock
  -> recovery-state check
  -> strict released-schema readiness

maintenance operation
  -> exact manifest + single-use receipt
  -> bounded exclusive lock
  -> exact target/code/plan/inventory revalidation
  -> receipt consumption (no retry)
  -> checkpointed immutable backup
  -> migration or crash-safe restore
  -> semantic/byte postflight
  -> durable completed journal
```

All ordinary managed connections hold a target-specific shared lock until
close. Initialization, migration, backup, restore, rollback, and recovery hold
the exclusive lock from connection creation through close. Shared locks are
never upgraded in place: a maintenance caller that did not acquire exclusive
ownership from the outset fails before reading or changing schema state.
Initialization double-checks state only after acquiring that exclusive lock.

## Preservation model

Migration 4 permits exactly three differences:

1. removal of the two legacy source columns;
2. addition of missing metadata keys only when the corresponding legacy value
   is non-null; and
3. one appended Migration 4 history row.

The validator compares public `SourceRecord` values, all table values and
SQLite storage classes, IDs, current-version pointers, version histories,
unchanged raw metadata bytes, the explicit fallback set, integrity and foreign
keys, and caller-supplied non-Ledger file checksums.

## Recovery model

Restoration first validates a read-only backup candidate, then durably journals
each phase: prepared, staging validated, failed database preserved, candidate
installed, result validated, and completed. It hard-links the failed database
for preservation, atomically replaces the target pathname with the candidate,
then makes the now-independent failed inode read-only. An active journal blocks
application connections, including openers that were waiting for the shared
lock when recovery began. Recovery resumes from file state plus the last
durable phase; a committed WAL is checkpointed and its connection closed
before replacement. An interrupted migration restores the verified
pre-transition backup rather than retrying a consumed authorization.

## Honest limits

The lock is cooperative among Wingman connections. An unrelated process that
opens SQLite directly does not honor the sidecar lock; WAL checkpoint
quiescence detects active durable writers and fails the operation. The
authorization receipt is tamper-evident after Maverick's decision but does not
independently authenticate a human against a malicious process already running
as the same trusted operating-system account.
