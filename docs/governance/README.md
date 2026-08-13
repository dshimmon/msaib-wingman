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
inputs, and validation fails if they are stale. `CURRENT_MISSION.md` reports
strategic mission and mission-workstream status only; ordinary implementation
permission comes from the operating instructions and a valid bounded task.

Mission journals and other documentation may summarize current state and be
maintained with authorized work. The canonical `mission.md` record controls if
a summary conflicts with mission metadata. Historical snapshots under
`docs/archive/` retain their machine classification and visible warning.
