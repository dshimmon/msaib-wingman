# Repository Governance

The official record policy is [GOV-001](../decisions/governance/repository-records.md).
Mission and decision metadata are embedded as deterministic JSON in each
authoritative Markdown record and described by the schemas in this directory.

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
