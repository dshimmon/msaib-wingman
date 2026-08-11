# Ledger Transition Runbook

This runbook defines the reviewed procedure. It does not authorize using the
default or live Ledger. The mechanism is published, but until every live gate
is independently satisfied and Maverick approves one exact operation, use
temporary synthetic databases only and stop before creation of any live
receipt.

## 1. Preconditions

1. Repeat `CANOPY-7C2F-ATLAS` and verify Maverick's exact authority.
2. Verify the exact published code commit, reviewed commit range, any proposed
   post-publication candidate diff, Migration 4 plan digest, test evidence,
   and Crew Chief disposition. A dirty or substituted code state requires a
   new package.
3. Verify Assurance v1 and every DATA-001 live prerequisite.
4. Resolve the target to one absolute canonical regular file. Reject relative
   ambiguity, target symlinks, symlink aliases, an active recovery journal,
   abandoned transition artifacts, or a substituted backup destination.
5. Acquire the bounded exclusive lock. Reject active cooperative readers or
   writers.
6. Validate exact migration history, version-3 schema fingerprint, strict JSON
   metadata, integrity, and foreign keys.
7. Checkpoint and truncate WAL. Require a zero-page WAL result and bind the
   DB/WAL/SHM inventory plus the quiescent database checksum.

## 2. Disposable rehearsal

The dry run creates a new external workspace, copies the checkpointed source,
and writes only the clone:

```text
python -m wingman.core.ledger.transition_cli dry-run \
  --source /absolute/synthetic-ledger.sqlite3 \
  --workspace /absolute/new-disposable-workspace
```

The rehearsal must report unchanged source bytes, a valid version-4 clone,
and a passing preservation manifest. A no-write flag against a live target is
not an accepted rehearsal.

## 3. Freeze and approve an exact package

Build a version-1 manifest with the Canary, Maverick authority, exact code and
reviewed range, source inventory, diff identity, Migration 4 digest, canonical
target path and device/inode identity, schema fingerprint, DB/WAL/SHM
inventory, checksum, backup destination, internally constructed command, run
ID, expiry, operation, and no-retry state.

Report the exact manifest/package bytes and SHA-256 to Maverick. Stop. Do not
create a receipt until Maverick approves those exact bytes. Receipt creation
records that decision but does not independently authenticate Maverick. Any
changed byte, path, code state, schema state, inventory, command, expiry, or
operation invalidates the package and requires a new review.

## 4. Authorized execution

The only execution arguments are the exact manifest and receipt:

```text
python -m wingman.core.ledger.transition_cli execute \
  --manifest /absolute/reviewed-manifest.json \
  --receipt /absolute/approved-receipt.json
```

No caller-supplied SQL, migration number, target, backup substitution, retry,
or arbitrary command argument is accepted. Revalidate every binding under the
exclusive lock, then atomically consume the receipt before the first backup or
schema write.

Create the backup with exclusive creation, fsync, exact byte/checksum
verification, read-only validation, atomic non-overwriting publication, and a
separate immutable manifest. Never delete or overwrite a published backup.

Apply Migration 4 transactionally, run strict version-4 readiness, compare the
semantic and byte-preservation states, durably complete the journal, and retain
all evidence. Any unexplained difference is a failure.

## 5. Recovery and rollback

An active `.recovery.json` sidecar blocks normal application opens. Continue
the recorded operation without reusing or retrying its receipt:

```text
python -m wingman.core.ledger.transition_cli recover \
  --target /absolute/exact-ledger.sqlite3
```

Recovery validates the immutable backup, preserves the failed database,
installs the candidate atomically, fsyncs every transition, revalidates the
result, and archives the completed journal without overwriting evidence.

Rollback is a new exact-target `rollback` manifest and single-use receipt bound
to the selected immutable version-3 backup. It uses the same restoration
state machine and preserves the failed version-4 database.

## 6. Stop conditions

Stop on path ambiguity, symlink use, lock contention, an uncooperative active
writer, WAL pages remaining after truncation, history gaps/duplicates/future
versions/name mismatch, schema drift, invalid metadata, integrity or foreign
key failure, abandoned artifacts, active recovery, authorization mismatch,
expired/consumed receipt, backup corruption, unexplained data difference, or
incomplete recovery.
