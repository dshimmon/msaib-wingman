# ARCH-001 — Wingman Airframe Boundaries

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "ARCH-001",
  "title": "Wingman Airframe Boundaries",
  "namespaces": ["wingman-os", "atlas", "radar"],
  "status": "accepted",
  "date": "2026-07-31",
  "authority": "Maverick",
  "scope": "Core, Shared Product Framework, and product dependency direction",
  "approval_evidence": "wingman-os/airframe and wingman-os/hardpoints mission records",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

Wingman Core owns domain-neutral mechanisms. The Shared Product Framework owns
product attachment contracts and reusable composition. Products own meaning,
policy, vocabulary, and application composition.

Core may depend only on Core. Shared may depend on Core and Shared. Products
may depend on Core, Shared, and their own modules. Core and Shared must not
import Atlas or Radar policy or branch on product identity.

Product Contract v1 is the current explicit attachment seam. Radar must attach
through that contract or a separately approved later version; it must not add
product-specific branches to Core. Prompt Optimizer remains product-neutral
Core functionality even when Atlas exposes it through its shell. Atlas owns
bulk-ingestion policy while neutral adapters, errors, discovery, and mechanics
remain in Wingman OS.

## Consequences

Canonical source paths are physically separated under `src/wingman/` and
`src/products/`. Compatibility facades may preserve historical imports, but
new internal code uses canonical package paths.
