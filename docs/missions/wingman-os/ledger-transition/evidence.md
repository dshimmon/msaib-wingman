# Ledger Transition Engineering Evidence

This is an in-progress uncommitted engineering record. It is not a Crew Chief
report, approval, publication record, live-transition receipt, or
mission-completion claim.

## Starting state

- Repository root:
  `/Users/davidshimmon/.codex/worktrees/c7b7/msaib-wingman`
- Approved baseline, initial HEAD, merge base, and `origin/main`:
  `b1910d0c69a52d73ddde93cb9722f12540c5d1e7`
- Initial branch/state: detached HEAD, no upstream, clean index and worktree.
- Concurrent worktree audit found no Ledger code, source-registry, Ledger test,
  or Ledger-specific documentation overlap. The dirty shared architecture
  summary in the Crew Chief worktree was explicitly excluded here.
- `data/**`, the default Ledger, `.env`, credentials, network services, and
  model services were not read or used.

## Development attempts and corrections

- First focused run: 50 tests attempted; 49 errors and one assertion failure
  because macOS temporary paths used the `/var` system alias. Ordinary
  connections now canonicalize it to `/private/var`; exact transition targets
  still reject caller-supplied aliases.
- Second focused run: 48 passed and two timed out because existing adapter
  tests held a shared connection while registry startup always requested an
  exclusive initialization lock. Ready-state registry access now stays shared;
  exclusive initialization is used only for missing schema or an actual
  legacy seed import.
- Existing Ledger/source-registry/version-3 adapter rerun: 50 passed.
- Initial synthetic transition run: 10 passed, two failed. DB/WAL/SHM evidence
  was corrected to treat SHM as ephemeral inventory, and backup schema
  validation now ignores the expected canonical-path difference.
- Synthetic transition rerun: 12 passed.
- Expanded synthetic transition suite: 21 passed, including real
  multiprocessing and every durable restoration boundary.
- Architecture boundary initial run: seven passed, one failed because the
  exact legacy-transition vocabulary inventory was intentionally incomplete.
  The semantic exception inventory was updated to the new narrow owners.
- Architecture boundary rerun: eight passed.
- A later real concurrent-initialization run exposed `database is locked`;
  increasing SQLite's busy timeout alone did not correct the race. Missing or
  zero-byte initialization was moved under the exclusive lock before the first
  SQLite open, and the multiprocessing rerun passed.
- A 166-test regression batch then had three failures: two version-3 fixtures
  implicitly expected the old latest migration, and the new decision record
  needed to defer lifecycle ownership to the canonical mission record. The
  fixtures now request version 3 explicitly; the affected 29-test rerun passed.
- The first complete-suite command omitted the repository top-level discovery
  argument. It ran 102 tests and ended with 28 collection/import errors,
  including a credential-sensitive import outside the suite's normal test
  package setup. No product code was changed for this harness error. The
  documented `-t .` rerun passed 327 tests in 23.833 seconds.
- Replacing exception injection with literal spawned-process termination found
  one genuine post-commit recovery failure: 22 of 23 tests passed, but closing
  the failed version-4 connection could replay its WAL into the newly installed
  version-3 pathname. Recovery now checkpoints and closes the failed database
  before replacement, atomically replaces the target while retaining a
  read-only failed database, and validates distinct single-link identities.
  The immediate 23-test rerun passed in 8.409 seconds; the final matrix adds a
  lock/recovery race regression and passed all 24 tests before independent
  review.
- Crew Chief audit `05f2d9fd8bdd1e480d490eea6587ca3daf2ab7334b67b44f1733a2d88fa1a60b`
  returned schema-valid `FAIL` with one blocking medium finding, `CC-0001`:
  in-place BSD `flock` conversion from shared to exclusive could lose the
  shared lock if concurrent maintenance conversion failed. Codex accepted the
  finding. Maintenance now requires a connection opened exclusively from the
  outset, and the conversion API was removed.
- The first post-finding 123-test regression run produced two errors because
  a legacy-adapter fixture retained its setup-only exclusive lock while later
  registry calls opened shared connections. The fixture now closes its
  exclusive initializer and reopens shared. The identical rerun passed all
  123 tests in 1.090 seconds.

## Final engineering validation

Maverick reconciled the two exact-file overlaps with Flight Cards on August
10, 2026. `src/wingman/shared/airframe_manifest.py` remains the global module
ownership inventory and `tests/products/atlas/test_ingestion_integration.py`
remains the Atlas-owned cross-layer integration test. The Ledger candidate
retains only its Core registration/rollback-window changes and explicit
version-3 fixture setup; it neither copies nor modifies the separate Flight
Cards hunks. The post-reconciliation reruns below bind this final candidate.

- Transition safety matrix — `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
  python -m unittest tests.wingman.test_ledger_transition`: **25 passed** in
  8.657 seconds. It uses synthetic temporary databases and real spawned
  processes, including termination at every durable restoration boundary,
  immediately after Migration 4 commits, and both release orders for two
  shared connections concurrently rejected from maintenance without losing
  their lifetime locks.
- Ledger, source-registry, version-3/version-4, Briefing, Airframe, Product
  Contract, compatibility-facade, and architecture regression command — the
  exact 12-module command recorded in the correction engineer report: **146
  passed** in 10.068 seconds. Expected mocked Briefing error logs appeared.
- Complete eligible offline suite — `PYTHONDONTWRITEBYTECODE=1
  PYTHONHASHSEED=0 python -m unittest discover -s tests -t . -p
  'test_*.py'`: **329 passed** in 40.258 seconds. Expected Flightline
  cancellation/time-budget diagnostics, mocked diagnostic traces, bare
  Streamlit warnings, and the optional PDF-layout suggestion appeared; none
  was a failure or skip.
- Five Ledger JSON Schemas passed Draft 2020-12 meta-schema validation.
- All 192 Python sources under `src`, `tests`, and `tools` compiled in-memory.
- `python -m tools.governance validate`: passed.
- Changed-scope `ruff check` with the repository's test-import `E402`
  convention excluded: passed.
- `git diff --check`: passed for every tracked change. The frozen package also
  inventories and hashes every untracked file byte.

No default/live Ledger, `data/**`, `.env`, credential, network/model service,
live authorization receipt, live backup, live restoration, or live migration
was used. All transition execution tests used disposable temporary roots.

The exact uncommitted source inventory, status, hashes, and deterministic
engineer freeze are external evidence artifacts so their digests do not become
self-referential repository changes.

## Crew Chief status

Maverick approved the exact operationally rebound package and one canonical
read-only invocation. Crew Chief audit `05f2d9fd8bdd1e480d490eea6587ca3daf2ab7334b67b44f1733a2d88fa1a60b`,
envelope `fccfeff8387a1e9f053a8fadc68ae625f4cce6789db4b12a0395ec45c2b37795`,
completed with schema-valid verdict `FAIL` and exactly one finding, `CC-0001`.
The controller recorded identical repository state hash
`4a3824fe138af48efe2672e01384ee723100726eb008f8ef5aa05307944526dc`
before and after the review. `CC-0001` is resolved in the current uncommitted
candidate as described above. A new deterministic package and separately
approved follow-up Crew Chief disposition remain required before a final
implementation report.
