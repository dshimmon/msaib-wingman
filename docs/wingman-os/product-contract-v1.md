# Product Contract v1

Product Contract v1 is the explicit boundary by which a product supplies
identity, capabilities, record declarations, metadata rules, retrieval and
Briefing policy, bounded UI terms, and defaults to Wingman OS.

The authoritative implementation is
`src/wingman/shared/product_contract.py`; shared application is in
`src/wingman/shared/product_runtime.py`. Atlas's first product definition and
closed production registry are in `src/products/atlas/product_config.py`.

## Invariants

- Version compatibility is exact at version `1`.
- Contracts and contexts are immutable and explicitly selected.
- A Product Context is not a service locator or mutable global selection.
- The production registry is a reviewed closed tuple; it performs no scanning
  or dynamic loading.
- Core receives only neutral values, callbacks, retrieval plans, record shapes,
  or opaque metadata.
- Product meaning and vocabulary remain in product packages.
- Source IDs, evidence locations, original paths, uploads, and provenance are
  preserved through every composition path.

Atlas implements the current Chat, ingestion, retrieval, Briefing, and Library
capabilities. Prompt Optimizer remains a neutral shell utility outside the
product capability list. Bulk ingestion uses Atlas's existing `course_id`
metadata declaration without changing the contract version.

The [product-attachment runbook](../runbooks/product-attachment.md) explains
the approved composition pattern. Compatibility is governed by
[ARCH-004](../decisions/architecture/compatibility-facades.md) and the
[compatibility register](../governance/compatibility-surfaces.md).
