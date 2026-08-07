# Wingman Architecture Glossary

**Chunk:** The smallest self-contained unit of knowledge that another AI—or
another engineer—can understand without needing the original document.

**Product Contract:** The single typed, immutable, versioned declaration by
which a product supplies identity, current capabilities, schemas, metadata
rules, retrieval and Briefing policy, bounded UI vocabulary, and defaults to
Wingman OS.

**Product ID:** A stable internal machine identifier used for deterministic
registration and selection. It is distinct from the display name.

**Display name:** User-facing product text that may evolve without changing the
stable Product ID.

**Product Registry:** An immutable, explicit mapping of reviewed Product IDs to
validated Product Contracts. It rejects duplicates and unknown selections and
does not discover or load code.

**Product Context:** A frozen, scoped selection of one validated Product
Contract passed through product-owned and Shared composition. It is not a
global active-product variable or service locator.

**Capability:** A product-neutral identifier for behavior currently exposed by
Shared composition. V1 includes only Chat, ingestion, retrieval, Briefing, and
Library behavior already used by Atlas.

**Record declaration:** A product-owned record type and its exact fields,
validated after product enrichment before records continue through generic
mechanisms.

**Source-metadata extension:** A product-owned metadata key with its current UI
label and normalization rule. Framework source fields are reserved; unrelated
metadata remains opaque.

**Composition root:** A visible product-owned entrypoint that explicitly
selects a Product Contract, creates a Product Context, and supplies neutral
values or callbacks to Shared and Core.

**Compatibility facade:** A thin retained public import, call, CLI, or patch
surface that forwards to the current owner without duplicating product policy.
