# ARCH-004 — Compatibility Facades

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "ARCH-004",
  "title": "Compatibility Facades",
  "namespaces": ["wingman-os", "atlas"],
  "status": "accepted",
  "date": "2026-08-07",
  "authority": "Maverick",
  "scope": "Supported historical imports and entry points during package separation",
  "approval_evidence": "governance/repository-architecture mission brief",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

Supported historical imports and entry points remain through thin facades while
canonical implementation moves into namespaced packages. Each facade has one
canonical target, owner, reason, supported callers, and objective removal
condition in the compatibility register.

New internal code and tests use canonical imports. A facade may be removed only
after a caller inventory proves no supported caller remains and Maverick
approves the compatibility change.
