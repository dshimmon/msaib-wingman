# Repository Governance

The official record policy is [GOV-001](../decisions/governance/repository-records.md).
Mission and decision metadata are embedded as deterministic JSON in each
authoritative Markdown record and described by the Draft 2020-12 schemas in
this directory. Validation also reconciles recorded commits and publication
booleans against local Git objects, cached remote-tracking refs, and cached
`origin/main`; it performs no fetch or network mutation.

Run the documented local check from the repository root:

```bash
PYTHONPATH=src python3 -m tools.governance validate
```

Refresh generated entry points after authoritative metadata changes:

```bash
PYTHONPATH=src python3 -m tools.governance generate
```

Generated files are review aids. Their headers identify their authoritative
inputs, and validation fails if they are stale.

Completed mission directories may contain only the canonical `mission.md`
status record. Retained journals and snapshots live under `docs/archive/`,
where every file carries its own machine classification, visible warning, and
canonical replacement (or an explicit statement that none exists).
