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

The final reconciliation record is intentionally a fifth bounded commit. Its
hash cannot self-identify inside that commit and belongs in the final operator
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

The [30-second usability drill](usability-drill.md) is prepared but has not
been executed by a fresh-context reviewer. The Development Flightline is in
maintenance-pending state, and no other approved independent-review mechanism
was available in this session. Therefore:

- Codex implementation and self-review: complete;
- local tests and governance validation: complete;
- bounded commits: four complete before this reconciliation commit;
- fresh-context usability drill: pending;
- independent read-only audit: pending; no findings exist yet;
- push: not performed;
- merge: not performed; and
- mission completion: not declared.

After Maverick resolves the publication ancestry, an approved fresh reviewer
must execute the usability drill and independently audit `c88a226..HEAD`, the
mission brief, this evidence, governance output, and exact diff. Every finding
must be resolved, disputed with evidence, or escalated before merge.
