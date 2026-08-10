# ARCH-002 — Product Separation

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "ARCH-002",
  "title": "Product Separation",
  "namespaces": ["atlas", "radar", "wingman-os"],
  "status": "accepted",
  "date": "2026-08-07",
  "authority": "Maverick",
  "scope": "Physical and semantic separation of Wingman OS, Atlas, and Radar",
  "approval_evidence": "governance/repository-architecture mission brief",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

Wingman OS is the domain-neutral foundation. Atlas is its first product and
owns academic policy and composition. Portfolio Wingman and Radar are the same
future product, expressed as Portfolio Wingman/Radar. That product is separate
from Atlas and Wingman OS core and receives dedicated documentation, source,
and test namespaces without speculative production behavior.

Product-specific decisions use the global decision system with namespace tags.
Architecture documents may summarize this decision only by linking here; this
record controls if wording conflicts.
