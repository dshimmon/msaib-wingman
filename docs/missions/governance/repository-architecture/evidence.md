# Repository Architecture Evidence

This package records local implementation and validation evidence for the
active [`governance/repository-architecture`](mission.md) mission. It does not
claim independent review, publication, merge, or mission completion.

## Repository state

- Repository: `/Users/davidshimmon/Developer/Wingman/msaib-wingman`
- Isolated worktree: `/private/tmp/wingman-repository-architecture-20260807-01`
- Branch: `codex/governance-repository-architecture`
- Baseline: `c88a226ac13e69e235ed5df1347a3872e3330554`
- Upstream: none configured
- Remote: `origin` at `https://github.com/dshimmon/msaib-wingman.git`
- Live remote heads observed on 2026-08-07: only `main` at
  `e1570b0c0d759933eaa0d2d0b48839051337d441`

The foreground `codex/Audit` checkout and its 11 pre-existing tracked changes
remain protected. No foreground path is part of a mission commit.

## Bounded implementation commits

1. `a26ca3a` — Establish canonical repository governance records.
2. `1052f17` — Classify repository documentation and history.
3. `b2a6177` — Separate Wingman and product packages.
4. `99f0ef3` — Enforce repository governance in CI.
5. `bf73134` — Reconcile repository architecture evidence.

Independent-audit correction commits preserved after those five:

1. `60134f7` — Reconcile historical mission authority.
2. `0bc7be1` — Enforce repository record invariants.
3. `ea774b0` — Reconcile repository correction evidence.

The single authorized foreground-lineage follow-up commit is the next bounded
record. Its hash cannot self-identify inside that commit and belongs in the
final operator report.

## Validation evidence

The isolated pre-change baseline used:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

Result: **271 tests passed** in 6.15 seconds. The historical 276-test result is
not the baseline because it included uncommitted foreground Flightline work.

Final commands use the repository Python 3.12 environment, no real credential,
and `PYTHON_DOTENV_DISABLED=1` where product tests load configuration.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
OPENAI_API_KEY=repository-governance-offline-placeholder \
PYTHON_DOTENV_DISABLED=1 \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m unittest tests.governance.test_repository_governance
```

Result: **7 tests passed** in 0.835 seconds.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
OPENAI_API_KEY=repository-governance-offline-placeholder \
PYTHON_DOTENV_DISABLED=1 \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m unittest tests.governance.test_architecture_boundaries \
tests.wingman.test_product_contract \
tests.governance.test_compatibility_facades
```

Result: **33 tests passed** in 0.314 seconds.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
OPENAI_API_KEY=repository-governance-offline-placeholder \
PYTHON_DOTENV_DISABLED=1 \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m unittest tests.products.atlas.test_airframe_composition
```

Result: **12 tests passed** in 0.009 seconds, including terminal-default and
Streamlit batch-composition coverage.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
OPENAI_API_KEY=repository-governance-offline-placeholder \
PYTHON_DOTENV_DISABLED=1 \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m unittest tests.products.atlas.test_batch_ingestion \
tests.products.atlas.test_bulk_ingestion_cli \
tests.products.atlas.test_bulk_ingestion_scale \
tests.products.atlas.test_ingestion_atomicity \
tests.products.atlas.test_ingestion_integration \
tests.products.atlas.test_intake_service \
tests.products.atlas.test_retrieval_pipeline \
tests.products.atlas.test_library_management_service \
tests.wingman.test_library_service \
tests.products.atlas.test_briefing_generator \
tests.products.atlas.test_briefing_persistence \
tests.products.atlas.test_briefing_planner \
tests.products.atlas.test_briefing_service \
tests.products.atlas.test_prompt_optimizer
```

Result: **106 tests passed** in 3.838 seconds. Expected diagnostic-failure and
bare-Streamlit logs were emitted by negative-path tests; the suite was green.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
OPENAI_API_KEY=repository-governance-offline-placeholder \
PYTHON_DOTENV_DISABLED=1 \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m unittest discover -s tests -t . -p 'test_*.py'
```

Result: **282 tests passed** in 6.618 seconds after final reconciliation: 271
baseline tests plus four compatibility-facade tests and seven
repository-governance tests.

Additional results:

- `python -m compileall -q src tests` — passed.
- `python -m pip check` — `No broken requirements found` (with an unwritable
  user-cache warning only).
- `PYTHONPATH=src python -c 'from wingman.core.ledger.migrations import
  MIGRATIONS; print([migration.version for migration in MIGRATIONS])'` —
  `[1, 2, 3]`.
- `PYTHONPATH=src python -m tools.governance validate` — passed, including link,
  generated-file freshness, schema, mission, decision, compatibility, first-read,
  and repository-hygiene checks.
- `git diff --check` — passed before final reconciliation and must pass again on
  its exact staged diff.
- `ruff check tools/governance/repository.py
  tests/governance/test_repository_governance.py` — passed.
- `ruff check src tests tools` — 77 findings at both `c88a226` and the final
  implementation tree. This mission introduced no net Ruff finding; the
  inherited set consists primarily of test `E402` import placement and retained
  compatibility/public re-exports. No lint debt was silently suppressed or
  expanded into unrelated cleanup.

## Publication ancestry

Live `origin/main` does not contain these eight baseline ancestors, and the
canonical records do not prove publication authority for all of them:

1. `7c3402c` — Reconcile Mission 027 canonical records.
2. `726dbbe` — Add approved Wingman Vault.
3. `7518bf7` — Add repository-wide Codex instructions.
4. `4cabb43` — Reconcile Wingman Vault status.
5. `ea9f3e0` — Complete Development Flightline setup.
6. `2b3b9a6` — Establish Wingman product hardpoints.
7. `22b418b` — Complete Prompt Optimizer workflow.
8. `c88a226` — Add resilient bulk document ingestion.

Maverick must disposition publication of every commit in that list before this
branch is pushed or merged. No force-push, history rewrite, or bypass is an
acceptable substitute.

## Review and remaining gates

The prior independent repository-organization audit failed and its blocking
findings produced Maverick's correction brief. The
[30-second usability drill](usability-drill.md) remains prepared but has not
been rerun by a fresh-context reviewer. Therefore:

- Codex implementation and self-review: complete;
- local tests and governance validation: complete;
- original bounded commits: five complete;
- correction commits: three complete before the foreground-lineage follow-up;
- prior independent read-only audit: failed; corrections locally implemented;
- fresh-context usability drill: pending rerun;
- fresh independent read-only correction audit: pending;
- push: not performed;
- merge: not performed; and
- mission completion: not declared.

An approved fresh reviewer must now execute the usability drill and
independently audit `c88a226..HEAD`, the mission brief, this evidence,
governance output, and exact diff. Every finding must be resolved, disputed
with evidence, or escalated. Separately, Maverick must resolve the publication
ancestry before any push or merge.

## Independent-audit correction evidence

Maverick's dated GOV-003 ratification now supports all 30 missions classified
completed at correction start. Twenty-nine historical journals moved from
completed mission directories into `docs/archive/mission-history/`; Flightline
Setup had no journal. All archived bodies preserve their substantive starting
content: 17 are byte-exact below the new banner, and 12 only normalize a
previously missing final newline.

All 54 retained archive files now carry a machine classification, a visible
file-local noncanonical warning, and either a canonical replacement link or an
explicit no-replacement statement. `airframe-at-c88.md` explicitly identifies
itself as historical rather than current.

The machine-readable
[`foreground-preservation-manifest.json`](artifacts/foreground-preservation-manifest.json)
records all 11 protected versions. Eight pathnames changed disposition in the
correction tree (five moved, three deleted); three remain at the same path.
No exact foreground working-version SHA-256 appears in a tracked file at
comparison commit `0bc7be1`.

This is a post-hoc exact-byte comparison against the still-intact read-only
foreground checkout, anchored to the original aggregate binary-diff hash. No
immutable per-file preflight manifest existed, so the evidence does not claim
one.

### Correction validation

Relevant negative tests were run first:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
OPENAI_API_KEY=repository-governance-offline-placeholder \
PYTHON_DOTENV_DISABLED=1 \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m unittest tests.governance.test_repository_governance
```

Result: **20 tests passed** in 2.391 seconds. These include Bulk Ingestion and
Prompt Optimizer authority conflicts, a completed journal, malformed priority,
unexpected fields, malformed approval evidence, false publication claims, an
unreachable active commit, root escape, disguised facade implementation,
unlabeled archive, and preservation-manifest consistency.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m tools.governance validate
```

Result: passed. This performs Draft 2020-12 validation, GOV-003 inventory,
commit reachability, cached publication/merge evidence, completed-journal,
archive, status-authority, link, generated-view, compatibility AST, first-read,
schema, and hygiene checks without fetching.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
OPENAI_API_KEY=repository-governance-offline-placeholder \
PYTHON_DOTENV_DISABLED=1 \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m unittest tests.governance.test_architecture_boundaries \
tests.wingman.test_product_contract \
tests.governance.test_compatibility_facades
```

Result: **33 tests passed** in 0.308 seconds.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
OPENAI_API_KEY=repository-governance-offline-placeholder \
PYTHON_DOTENV_DISABLED=1 \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m unittest tests.products.atlas.test_airframe_composition
```

Result: **12 tests passed** in 0.009 seconds.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
OPENAI_API_KEY=repository-governance-offline-placeholder \
PYTHON_DOTENV_DISABLED=1 \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m unittest discover -s tests -t . -p 'test_*.py'
```

Result: **295 tests passed** in 8.636 seconds. Expected negative-path
Flightline/diagnostic logs, bare-Streamlit warnings, and the optional
`pymupdf_layout` suggestion appeared; there were no failures or skips.

Additional correction checks:

- `PYTHONPYCACHEPREFIX=/private/tmp/wingman-repository-correction-pycache-20260807
  python -m compileall -q src tests tools` — passed.
- `python -m pip check` — `No broken requirements found`; pip emitted only its
  unwritable user-cache warning.
- `ruff check tools/governance/repository.py
  tests/governance/test_repository_governance.py
  tests/governance/test_compatibility_facades.py` — passed.
- `git diff --check bf73134` — passed before the final correction commit and is
  repeated against the final HEAD during closeout.

No runtime, Product Contract, Ledger, Radar, or dependency file changed in the
correction commits.

## Foreground rename lineage follow-up

Maverick authorized exactly one additional local evidence-correction commit on
2026-08-07 after confirming that the manifest mapped `docs/Mission-brief.md`
to an unrelated archive file. The corrected mapping is:

`docs/Mission-brief.md` →
`docs/missions/operations/flightline/setup/artifacts/approved-brief.md`

The destination's SHA-256 at comparison commit `0bc7be1` is
`cb844e5c6f91efe5b256d4bf39a483713f963ab18f186ffe57decbeec58974eb`.
The separately added `docs/archive/governance/pre-mission-message.txt` is not
the Mission brief's Git successor.

### Five moved-path checks

`git diff --name-status --find-renames c88a226 0bc7be1` reports:

| Git | Source | Destination | Destination SHA-256 at `0bc7be1` |
|---|---|---|---|
| `R095` | `docs/Development-Flightline.md` | `docs/runbooks/development-flightline.md` | `8443320e69b8d735d2c712c9a19453b845f26c47ca557a566081c918fafd81aa` |
| `R096` | `docs/Mission-brief.md` | `docs/missions/operations/flightline/setup/artifacts/approved-brief.md` | `cb844e5c6f91efe5b256d4bf39a483713f963ab18f186ffe57decbeec58974eb` |
| `R098` | `docs/Wingman_Pre-Mission_028_Planning_Package.md` | `docs/archive/governance/pre-mission-028-planning-package.md` | `21c947f82a890323f346d4ade257dc8014d837bc71ce1c2bba727b6d10cf5a4c` |
| `R093` | `docs/architecture/Airframe.md` | `docs/archive/architecture/airframe-at-c88.md` | `b2f01fa6522e0b22eb7d1274bb98c87a90e4f9db200591ead2792e188855224e` |
| `R099` | `tests/test_flightline.py` | `tests/governance/test_flightline.py` | `8affa07ce6aec9ca49e1b1f5edff866c1ad9c0e4c03055528567e4c7f06590b1` |

Governance validation now derives the rename map from that exact Git range,
requires every manifest entry classified `moved` to declare Git's detected
destination, and computes the destination SHA-256 from the comparison-commit
blob. The existing exact foreground working-version exclusion assertions are
unchanged. A negative test substitutes the wrong but existing pre-mission
message and its correct hash; rejection proves that target existence and a
self-consistent declared hash are insufficient.

### Follow-up validation

The new negative test was run first:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src \
OPENAI_API_KEY=repository-governance-offline-placeholder \
PYTHON_DOTENV_DISABLED=1 \
/Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
-m unittest tests.governance.test_repository_governance.RepositoryGovernanceTests.test_wrong_existing_foreground_rename_target_is_rejected
```

Result: **1 test passed** in 0.331 seconds.

- Complete repository-governance suite: **21 tests passed** in 3.466 seconds.
- `python -m tools.governance validate`: passed.
- Architecture-boundary, Product Contract, and compatibility-facade suite:
  **33 tests passed** in 0.332 seconds.
- Complete repository suite: **296 tests passed** in 9.320 seconds. Expected
  negative-path Flightline/diagnostic logs, bare-Streamlit warnings, and the
  optional `pymupdf_layout` suggestion appeared; there were no failures or
  skips.
- `ruff check tools/governance/repository.py
  tests/governance/test_repository_governance.py`: passed. An initial attempt
  to invoke Ruff from `.venv/flightline-py312/bin/ruff` returned exit 127
  because that path does not exist; it performed no linting and the available
  repository command was then used successfully.
- `git diff --check ea774b0` is run before commit; the required
  `git diff --check ea774b0..HEAD` is repeated after the follow-up commit.

The mission remains active and awaiting fresh independent read-only audit.
Publication remains separately blocked pending Maverick's disposition of the
eight antecedent commits. This follow-up does not authorize push or merge.

## Repository-map finalization

Maverick first authorized a bounded, uncommitted repository-map improvement on
2026-08-07, then explicitly authorized finalization and one local commit of the
five map-related files without waiting for map review. The finalized map
expands `docs/README.md` in place as the single canonical human-readable filing
map; no competing map document was created. It preserves the first-read
directions and canonical-home links, adds the required annotated ownership tree
and placement rules, and links to the current architecture and Product
Contract instead of restating those technical contracts.

The governance validator now consumes one extensible inventory of canonical
files and directories. It requires every inventory path to be named verbatim
in `docs/README.md`, verifies the corresponding file or directory exists, and
requires the explicit warning that historical flat `src/` modules and
`src/ledger/` are compatibility facades where no new implementation belongs.
Negative tests remove a canonical map entry, introduce a mapped directory that
does not exist, and remove the compatibility-facade warning.

The finalization changes only:

- `docs/README.md`;
- `tools/governance/repository.py`;
- `tests/governance/test_repository_governance.py`;
- `docs/missions/governance/repository-architecture/journal.md`; and
- this evidence package.

No runtime, Product Contract, Ledger, Radar, dependency, or data file changed.
The work is implemented, validated, and authorized for exactly one local
commit of these five files. It is not included in the independent review of
committed HEAD `1250e8c`; map review and publication remain later gates.

### Repository-map finalization validation

- Map invariant plus the three required negative tests: **4 tests passed** in
  0.013 seconds.
- Repository-governance module: **25 tests passed** in 3.239 seconds.
- Complete governance test directory: **71 tests passed** in 5.417 seconds.
  Expected Flightline cancellation and time-budget negative-path messages
  appeared; there were no failures or skips.
- Documentation/link checks: **2 tests passed** in 0.059 seconds.
- `python -m tools.governance validate`: passed.
- Complete repository suite, using the repository-supported discovery root
  (`-s tests -t .`): **300 tests passed** in 9.099 seconds. Expected
  negative-path Flightline and diagnostic logs, bare-Streamlit warnings, and
  the optional `pymupdf_layout` suggestion appeared; there were no failures or
  skips.
- `ruff check tools/governance/repository.py
  tests/governance/test_repository_governance.py`: passed.
- `git diff --check 1250e8c`: passed against the finalized diff before staging;
  `git diff --cached --check` is repeated after staging.

Two intermediate command failures were corrected before the successful matrix:
the first four-test invocation found an indentation error in the newly wired
validator before test collection, and a complete-suite discovery command that
omitted the documented `-t .` produced 26 package-resolution import errors.
After the indentation fix and the supported discovery root were applied, the
results above passed.

Authorized commit message: `Document canonical repository filing map`.

The authorized local commit does not change the canonical mission gate: a
fresh independent read-only audit must pass on the committed correction state.
Maverick's map review remains later, and every publication, push, and merge
decision remains separate.

## Credential-free offline-suite audit correction

The 2026-08-08 independent audit passed the filing, map, lifecycle, lineage,
duplication, and governance criteria but failed the exact offline-suite command
documented in `README.md`. With `OPENAI_API_KEY` absent and dotenv loading
disabled, discovery ran 253 tests and reported seven import errors in 9.182
seconds. Each failing import reached `src/wingman/core/openai_client.py`, where
the production module constructs `OpenAI(api_key=os.getenv("OPENAI_API_KEY"))`
during import; the SDK rejects the resulting missing credential before the
affected tests can run.

Maverick first authorized a bounded implementation and validation correction
without commit, push, or merge authority, then authorized exactly one local
corrective commit on 2026-08-08 with subject
`Make offline test suite credential-free`. The correction remains test-only:

- `tests/__init__.py` uses `os.environ.setdefault` to establish the clearly
  fake value `wingman-offline-tests-no-credential` before test discovery
  imports modules that construct the shared client and disables dotenv loading
  by default;
- a caller-supplied environment value is never overwritten;
- `tests/governance/test_offline_suite.py` uses bounded subprocess imports to
  prove both the credential-absent case and caller-value preservation without
  recursively running the test suite;
- `README.md` keeps the advertised command unchanged and explains that the
  placeholder is test-only, nonsecret, and not an application default; and
- no production file under `src/` changed, no real credential was added or
  loaded, no test was weakened or bypassed, and the isolated import regression
  performs no API request.

The exact changed-file set is:

- `CURRENT_MISSION.md` (generated);
- `README.md`;
- `docs/governance/mission-control-context.md` (generated);
- `docs/missions/governance/repository-architecture/evidence.md`;
- `docs/missions/governance/repository-architecture/journal.md`;
- `docs/missions/governance/repository-architecture/mission.md`;
- `tests/__init__.py`; and
- `tests/governance/test_offline_suite.py`.

### Credential-free correction validation

- Exact credential-free suite — `env -u OPENAI_API_KEY
  PYTHON_DOTENV_DISABLED=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest
  discover -s tests -t . -p 'test_*.py'`: **302 tests passed** in 10.563
  seconds, with no failures or skips.
- Documented suite — `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover
  -s tests -t . -p 'test_*.py'`: **302 tests passed** in 10.563 seconds, with
  no failures or skips.
- Focused isolated regression — `env -u OPENAI_API_KEY
  PYTHON_DOTENV_DISABLED=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest
  tests.governance.test_offline_suite`: **2 tests passed** in 2.579 seconds.
- `PYTHONDONTWRITEBYTECODE=1 python -m tools.governance validate`: passed.
- `PYTHONDONTWRITEBYTECODE=1 python -m unittest
  tests.governance.test_repository_governance`: **25 tests passed** in 3.418
  seconds.
- `ruff check tests/__init__.py tests/governance/test_offline_suite.py`:
  passed.
- `git diff --check`: passed.

Expected Flightline cancellation/time-budget messages, mocked diagnostic
failure traces, bare-Streamlit warnings, and the optional `pymupdf_layout`
suggestion appeared in the successful full suites. They are exercised
negative-path output, not failures.

The commit containing this evidence locally commits the implemented and
validated correction on parent
`99accba8b3433b6f9485881f4033f507bd6ae3ef`; it cannot self-record its own
hash. The exact next gate is a fresh independent read-only audit of that
commit. Publication remains separately blocked pending Maverick's disposition
of the eight antecedent commits; push and merge are not authorized.

## Fresh audit, antecedent disposition, and publication closeout

On 2026-08-08 a fresh Codex session that had not implemented or committed the
credential-free correction performed the required independent read-only audit
at `6661712ca325d9fd47a9cf436fd3b11e04c53b62`. This was not a Crew Chief audit.
The audit returned `PASS — ELIGIBLE FOR MAVERICK'S PUBLICATION DECISION`.

The cold-start drill opened `AGENTS.md` and then `CURRENT_MISSION.md` and
identified the mission, lifecycle, authorization gate, official record, last
completed work, and next gate in 12 seconds. The audited worktree and index
were clean before and after validation. Independent results were:

- credential-free complete suite: **302 tests passed** in 11.062 seconds;
- repository governance validation: passed;
- repository-governance suite: **25 tests passed** in 3.346 seconds;
- focused offline regression: **2 tests passed** in 2.052 seconds;
- correction-file Ruff check: passed; and
- exact correction-range `git diff --check`: passed.

Maverick then explicitly approved all eight antecedent commits and authorized
publication of the audited repository-architecture history to `main`,
including exactly one bounded closeout commit. A non-force fast-forward
published `e1570b0..6661712` to `refs/heads/main`. The closeout updates only:

- this evidence package;
- the subsequently archived chronological journal;
- [`mission.md`](mission.md);
- [`usability-drill.md`](usability-drill.md); and
- five completed antecedent mission records whose publication booleans became
  true when `main` advanced; and
- generated mission and Mission Control views.

No runtime, test, product, data, dependency, or architecture implementation
file changes. The closeout commit cannot circularly record its own hash; the
final operator report must record that hash and the live remote result. The
mission remains active and published pending Maverick's separate completion
declaration and successor-mission decision.

## Mission completion and successor transition

On 2026-08-08 Maverick declared `governance/repository-architecture` complete
and authorized the records-only closeout, the minimal GOV-003 enforcement
correction needed for post-ratification completions, one local commit with
subject `Complete repository architecture mission`, and one non-force fast-
forward push of that commit to `main`.

The final independent technical result was **PASS**. The current-mission
discovery drill completed in **12 seconds**, and the independently executed
credential-free suite passed **302 tests** in 11.062 seconds. Publication commit
`cff8222fbe6092e0c145f7d8d7cabe8963cd66e6` was verified as both clean local
HEAD and live `origin/main` before this transition. The worktree and index were
clean, and the branch had no configured upstream.

The governance correction keeps GOV-003's dated ratification inventory fixed
at its original 30 historical missions while allowing later missions to become
completed under their own explicit authority. Focused tests prove both that a
later completed mission is not claimed by GOV-003 and that every mission GOV-
003 does claim must remain completed.

Closeout validation on the completed records and successor planning shell:

- exact credential-free complete suite: **304 tests passed** in 11.114
  seconds, with no failures or skips;
- repository governance validation: passed;
- repository-governance suite: **27 tests passed** in 3.692 seconds;
- focused GOV-003 completion-boundary tests: **2 tests passed** in 0.003
  seconds;
- focused Ruff on both changed governance Python files: passed; and
- working-tree `git diff --check`: passed.

Maverick approved `governance/crew-chief` as the successor portfolio-primary
planning mission. Crew Chief is not implemented or operational, and no Crew
Chief audit occurred during Repository Architecture because the capability did
not exist. Its implementation requires a separately authorized Crew Chief
build prompt. The commit containing this evidence cannot record its own hash;
later Repository Architecture changes require a separately approved mission.
