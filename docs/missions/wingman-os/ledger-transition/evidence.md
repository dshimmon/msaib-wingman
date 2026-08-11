# Ledger Transition Engineering Evidence

This record preserves the original uncommitted engineering history and the
later audit, integration, publication, and completed machinery-mission
evidence. It is not a live-transition receipt or live-execution approval.
Current lifecycle and next-gate authority belongs to [`mission.md`](mission.md).

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

## Pre-integration engineering validation

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

The exact pre-integration source inventory, status, hashes, and deterministic
engineer freeze were preserved outside the implementation candidate to avoid
self-reference. The decisive Crew Chief reports and reconciliations are now
also preserved byte-for-byte under [`artifacts/`](artifacts/).

## Crew Chief disposition

Maverick approved the exact operationally rebound package and one canonical
read-only invocation. Crew Chief audit
`05f2d9fd8bdd1e480d490eea6587ca3daf2ab7334b67b44f1733a2d88fa1a60b`,
envelope `fccfeff8387a1e9f053a8fadc68ae625f4cce6789db4b12a0395ec45c2b37795`,
completed with schema-valid verdict `FAIL` and exactly one blocking medium
finding, `CC-0001`. The controller recorded identical repository state hash
`4a3824fe138af48efe2672e01384ee723100726eb008f8ef5aa05307944526dc`
before and after the review.

Codex accepted the finding, removed shared-to-exclusive lock conversion,
required maintenance connections to acquire exclusive ownership from
creation, and added a two-process regression proving rejected maintenance
callers retain their shared lifetime locks. The accepted reconciliation is
complete and approval-ready.

Maverick then approved one exact, read-only, no-retry follow-up invocation.
Crew Chief audit
`6396de29749f52ea9cd4b95b03f75bc35894c9dc1d520809c49633b61492d46c`,
envelope `09eb6eed68d95f32e530561cf8604f8c1e297e4ad7cb16d04ae0b7003e8df12a`,
returned `PASS` with zero findings. Follow-up reconciliation is complete and
`approval_ready: true`.

Those earlier immutable report and reconciliation artifacts remain committed
below as development history. Maverick subsequently superseded the original
no-staging clause for the exact corrected candidate and approved one decisive
read-only, no-retry follow-up invocation. It used audit
`4b2951304f67667fdb654a707caa75292f78a4e429c4ad4a4f60db514fef4669`
and envelope
`33398f0c7c08aef8eed909ca7914f84f2efab05c2ed2eba19c5399d414dd1b33`.
The result was `PASS` with zero findings, reconciliation complete, and
`approval_ready=true`. The final report hash is
`3b2a8320fa38d548495a09d9b563904f8fe99795ef39f08991e9a4b3c38606d3`,
the reconciliation package hash is
`01b49942772375aa93a285a5ce07adf895913c963f92c0bb72f1a97f57b67f58`,
and the audited staged patch SHA-256 is
`a4e0f0af65de8413c2e659dfe0167a047efe6bee3b182d01ddcd0df252b4a7c3`.

The final immutable report records `generated_at` as
`2026-08-11T12:00:00-03:00`, while its controller records `completed_at` as
`2026-08-11T03:50:48Z` and reconciliation records `generated_at` as
`2026-08-11T03:51:28Z`. This is a model-authored timestamp metadata
inconsistency, not a Ledger implementation finding or an indication of
artifact tampering; the immutable audit artifacts were not rewritten.

The decisive final payload, complete envelope, controller report bundle,
reconciliation, readable summary, checksum inventory, and sensitive-content
scan are durably preserved at
`/Users/davidshimmon/.codex/visualizations/2026/08/10/019fec4e-6d68-7910-ba7c-0a7a21472336/ledger-transition-crew-chief-final-4b295130`.
Its `SHA256SUMS` file has SHA-256
`049002db9f475aeec0bc4c407f5a15a8268dd64f9cf3ccf8f8f7cf040ecba0c9`
and verifies all 81 other files. The sensitive-content scan covered 79 copied
immutable artifacts and 2,402,315 bytes, returned `pass`, and found zero
high-confidence secret matches without opening a secret or live-data path.

The repository preserves the exact final-package copies and their SHA-256
digests:

- [initial report](artifacts/crew-chief-initial-report.json):
  `37a9a93c1458426a5a837aba10469fa8b6e2d507c79df20a3c36f597420f942f`;
- [initial reconciliation](artifacts/crew-chief-initial-reconciliation.json):
  `ef31160c8cedad439d1e347f7424f8716df6e422ccbd21d2fe3364ef3481896f`;
- [follow-up report](artifacts/crew-chief-followup-report.json):
  `0e9ab1fb5bdc32c9acbd574111e47363d922f10c482bbf7f94d37345ecf88ea0`;
  and
- [follow-up reconciliation](artifacts/crew-chief-followup-reconciliation.json):
  `2edec179ac0a0f23cdce515fb9aded94061a68ef5e2f1ba1e2cff196e2d8c2a0`.

## Integration and publication

The deterministic final implementation package had package/manifest SHA-256
`9724b48ed7122d7747401a46f75248625263aa38412114ffbe2dacdcb0a7e8e7`
and archive SHA-256
`bb9b0111fd8ec881932f0d3d7b6c823810fb15231405e0bf7554b6a3449e616f`.
Its sensitive-content scan and byte-for-byte reproduction passed.

The audited 31-file implementation was reconciled onto the then-current main
without absorbing the separate Flight Cards or Course Cockpit/UI hunks. Its
exact staged diff SHA-256 remained
`a4e0f0af65de8413c2e659dfe0167a047efe6bee3b182d01ddcd0df252b4a7c3`.
The implementation was committed as
`51fb750d2364a4e137ba7e42963a11b10fe4cdc0`, integrated through
`f4dd327cad0be5da8bead4df633d7308a1ec80fb`, and pushed to `main`.
Later Atlas closeout commits advance `main` without removing or changing any
of the 31 Ledger paths.

Final integrated validation recorded:

- Ledger transition safety matrix: **25/25 passed**;
- combined focused safety and regression suite: **146/146 passed**;
- complete combined repository suite: **473/473 passed**;
- governance, 20 JSON Schemas, 226 Python sources, changed-scope lint, and
  both whitespace checks: **passed**; and
- Crew Chief follow-up: **PASS**, zero findings, reconciliation complete and
  approval-ready.

The first remote refresh was sandbox-blocked and succeeded with approved
access. The first lint command mistakenly included Markdown files; the
corrected Python-only command passed. Neither rerun changed the Ledger
implementation or concealed a product failure.

No default/live Ledger, `data/**`, credential, live transition package,
receipt, backup, migration, restoration, recovery, or rollback was touched.
Live execution remains a separate exact-package Maverick gate.

## 2026-08-11 canonical-record reconciliation

Maverick authorized one documentation/governance-only reconciliation commit
covering the remaining Ledger Transition record gaps and explicitly excluded
`CURRENT_MISSION.md`. The reconciliation began from published `origin/main`
at `490b24f2809cd00c27d3822d0a7abac9fd773393` in the isolated branch
`codex/ledger-transition-record-reconciliation-20260811`.

The canonical mission record was added with lifecycle `draft`: engineering,
audit, merge, and publication facts are recorded, while mission completion
remains Maverick's separate gate. Root orientation, Wingman OS architecture,
DATA-001, the Vault, roadmap, documentation map, runbook, mission architecture,
decision, evidence, and generated mission index were reconciled. No production
source, test, live data, or `CURRENT_MISSION.md` content changed. Governance
generation preserved the excluded file's SHA-256 exactly as
`fa1439f743a69c1515d1cab900495939d368cae85525cfff3233067f6e77530d`.

Validation on the reconciled tree:

- repository governance validation: **passed**;
- repository-governance plus Ledger Transition focus: **57/57 passed** in
  14.648 seconds;
- complete eligible repository suite: **473/473 passed** in 170.421 seconds;
- all four preserved Crew Chief JSON artifacts parsed successfully and were
  byte-identical to the final audit package copies; and
- secret-shaped assignment scan of the new artifacts and `git diff --check`:
  **passed**. Expected policy words such as `credential` and `.env` appear
  only in statements documenting that those surfaces were not touched.

The first generation attempt used the system Python 3.9 and stopped before
output because `tomllib` was unavailable. The second used the bundled desktop
Python and stopped before output because `jsonschema` was unavailable. The
repository's validated Python 3.12 environment generated the views
successfully. Neither failed attempt changed a file.

## 2026-08-11 completed-mission gap closeout

After `196a1804d51992259018281286f5571db2b4d556` became canonical main,
Maverick approved only the remaining gaps. The closeout preserved all valid
concurrent documentation and the four committed audit artifacts, changed the
machinery mission lifecycle from `draft` to `completed`, added the decisive
final audit and historical journal, corrected the runbook's stale
`uncommitted diff` wording, recorded Atlas's final completion commit, and
re-derived generated governance views. The only Python changes select the
latest completed mission by the timestamp of each mission's final recorded
commit and add its regression test; no Ledger runtime or product code changed.

Final pre-publication validation on that gap-only subject:

- Ledger Transition safety matrix: **25/25 passed** in 9.526 seconds;
- repository governance tests: **33/33 passed** in 10.026 seconds;
- standalone `python -m tools.governance validate`: **passed**;
- complete credential-free offline repository suite: **474/474 passed** in
  198.179 seconds;
- all **20** JSON Schemas validated against Draft 2020-12;
- all **226** Python sources under `src`, `tests`, and `tools` compiled in
  memory;
- changed-Python Ruff and exact-hunk Black checks: **passed**;
- generated document/link hygiene, unstaged whitespace, and preservation of
  all four committed audit artifacts: **passed**; and
- the durable package's `SHA256SUMS` inventory reverified all 81 listed files.

The first isolated-worktree creation attempt was denied before any Git change
because repository metadata was outside the sandbox; the identical authorized
rerun succeeded. The first Ruff and Black commands used the repository test
environment, which does not install those tools; the exact reruns used the
available `/opt/anaconda3/bin/ruff` and `/opt/anaconda3/bin/black` executables.
The first Black repository range extended through line 580 and reported an
adjacent pre-existing formatting difference in `render_current_mission`; the
correct exact changed range, lines 545–571, passed, as did the changed test
range. No formatter rewrote a file, and no failed attempt concealed a test or
product failure.

The first staged whitespace check found two Markdown hard-break spaces in the
new journal header. Removing those presentation-only spaces and restaging the
journal made the exact rerun pass. The first restage attempt was denied before
an index change because the shared Git metadata lock was outside the sandbox;
the identical authorized restage and both whitespace checks passed.

No default/live Ledger, `data/**`, database, WAL/SHM, credential, receipt,
backup, migration, restoration, recovery, rollback, or production system was
read or operated on during closeout.
