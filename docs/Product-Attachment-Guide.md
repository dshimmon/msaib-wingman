# Product Attachment Guide

This guide describes the Product Contract v1 seam without defining any future
product's domain behavior.

## 1. Keep product meaning in the product layer

Create product-owned functions for record enrichment, retrieval interpretation,
and—only when the capability is needed—Briefing planning and generation. These
functions may depend on product modules. Core and Shared must not import them.

## 2. Declare the smallest complete v1 definition

Construct one frozen `ProductContract` with:

- exact `contract_version=1`;
- stable lower-case `product_key` and separate user-facing `product_name`;
- only current `ProductCapability` values the product really supports;
- at least one exact `RecordDeclaration` and its enrichment callback;
- only source-metadata fields with current UI or validation demand;
- one retrieval interpreter returning all four neutral plan fields;
- Briefing callbacks only when Briefing is declared;
- the bounded page, call-sign, terminal, workspace, and default-domain values
  used by current composition.

Do not add generic dictionaries of hooks, agent/tool placeholders, hidden
defaults, or dynamic imports.

## 3. Register explicitly at the product-owned outer boundary

Build `ProductRegistry((definition, ...))` from a reviewed tuple. Duplicate IDs
fail during registry construction. Unknown IDs fail through `require()` or
`create_context()`. Production registration must be a visible source edit; do
not scan a folder, inspect entry points, or auto-import third-party code.

## 4. Create a fresh context at each composition root

Call `registry.create_context(product_id)` and pass that immutable
`ProductContext` into shared orchestration. Do not set a mutable process-global
"active product" and do not put services or arbitrary dependencies into the
context.

## 5. Use the existing shared seams

- Ingestion calls `create_product_knowledge_objects()`, which supplies the
  product enricher to Core and validates emitted record shapes.
- Metadata intake calls `normalize_source_metadata()`, which validates reserved
  keys, applies the selected product's declared rules, and preserves other
  opaque metadata.
- Retrieval calls `retrieve_product_evidence()`, which asks product policy for
  a neutral plan and gives that plan to Core execution.
- Product-owned Chat, Briefing, Library, CLI, and UI services propagate the
  context; Core receives only the neutral values and callbacks it needs.

## 6. Prove isolation and production intent

Tests should create two definitions sequentially in one process and compare
IDs, display terms, capabilities, record declarations, metadata rules, and
defaults. Exercise both through the same Shared/Core operation using temporary
storage. Also prove that a test fixture is absent from the production registry.

## 7. Preserve traceability and compatibility

Keep source IDs, evidence references, source metadata, original paths/URLs, and
uploaded originals intact. If a supported import or patch surface still has
callers, retain a thin product-owned facade and record its owner, reason, and
objective removal condition in the compatibility register.
