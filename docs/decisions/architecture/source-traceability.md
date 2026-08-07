# ARCH-003 — Source Traceability

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "ARCH-003",
  "title": "Source Traceability",
  "namespaces": ["wingman-os", "atlas", "radar"],
  "status": "accepted",
  "date": "2026-08-01",
  "authority": "Maverick",
  "scope": "Source preservation across all Wingman products and mechanisms",
  "approval_evidence": "WINGMAN_VAULT.md source-traceability principle",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

> Wingman summarizes information, but always preserves a path back to the source.

Source identifiers, exact evidence locations, original paths or URLs,
uploaded originals, provenance metadata, and source-management protections
must survive composition and repository changes. Products may interpret
evidence but may not sever its traceback. This obligation applies to current
Atlas behavior and every future product, including Radar.
