# GOV-006 — External Development-Operations Closeout

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "GOV-006",
  "title": "External Development-Operations Closeout",
  "namespaces": ["governance", "operations"],
  "status": "accepted",
  "date": "2026-08-14",
  "authority": "Maverick",
  "scope": "Repository-neutral independent-audit and exact-landing evidence contract performed by external capabilities",
  "approval_evidence": "Maverick's 2026-08-14 controlled clean-slate and development-operations extraction authority",
  "supersedes": ["GOV-004", "GOV-005"],
  "superseded_by": null
}
-->

## Decision

Wingman retains mandatory independent audit, exact candidate binding,
finding-by-finding reconciliation, action-specific landing authority, and
fail-closed landing verification. The agents and operational machinery that
perform those functions are external development operations, not Wingman OS
capabilities, product agents, runtime components, or repository-owned tools.

The canonical repository-owned requirements are defined by the
[External Development-Operations Closeout Contract](../../governance/external-closeout-contract.md).
External capabilities may satisfy that contract without being copied into the
repository or discovered through a user-specific filesystem path. When a
conforming capability is absent, the affected gate is blocked and disclosed;
self-certification and silent fallback are prohibited.

GOV-004 and GOV-005 remain as truthful records of the superseded
repository-scoped implementations. Their mission records, evidence, and
historical artifacts remain unchanged. Development Flightline remains governed
separately by OPS-001 because its Engineer isolation and controller controls
are not superseded by audit and landing capabilities.
