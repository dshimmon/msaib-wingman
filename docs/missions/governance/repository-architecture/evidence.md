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

The third correction commit is the final correction-evidence record. Its hash
cannot self-identify inside that commit and belongs in the final operator
report.

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
- correction commits: two complete before the final correction-evidence commit;
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
