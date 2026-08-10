# Wingman OS Architecture

This document describes the current system.
[ARCH-001](../decisions/architecture/airframe-boundaries.md) and
[ARCH-002](../decisions/architecture/product-separation.md) are the official
decisions when wording conflicts.

## Physical ownership

```text
src/
  wingman/
    core/       domain-neutral mechanisms
    shared/     product contracts and reusable composition
  products/
    atlas/      academic policy and application composition
    radar/      Portfolio Wingman/Radar namespace; no production behavior

tests/
  wingman/      Core and Shared behavior
  products/
    atlas/      Atlas behavior and composition
    radar/      future Portfolio Wingman/Radar tests; currently namespace-only
  governance/   architecture and repository governance
```

`src/wingman/shared/airframe_manifest.py` is the machine-readable ownership
inventory. Governance and architecture tests compare it with the actual tree.
The canonical roots are `src/wingman/core/`, `src/wingman/shared/`,
`src/products/atlas/`, and `src/products/radar/`.

## Dependency direction

```text
Wingman Core <- Shared Product Framework <- Product composition
                         ^                    |
                         +-- Product Contract+
```

Core depends only on Core. Shared depends on Core and Shared. Atlas may depend
on Core, Shared, and Atlas. Portfolio Wingman/Radar must attach through the
product contract and must not introduce product branches into Core or Shared.

## Current seams

- Core creates, stores, indexes, and retrieves generic evidence and knowledge.
- Shared validates Product Contract v1, creates scoped Product Contexts, and
  passes neutral callbacks, plans, values, and opaque metadata into Core.
- Atlas owns academic enrichment, query interpretation, Briefing policy,
  source-management policy, batch policy, UI vocabulary, and composition.
- Prompt Optimizer is a product-neutral Core utility exposed through the Atlas
  shell as a global workspace.
- Atlas owns bulk-ingestion policy. CSV/text adapters, typed document errors,
  safe path discovery, and generic ingestion mechanics remain in Core.

## Ledger boundary

Ledger migrations remain exactly versions 1–3. The private source-repository
adapter translates the historical physical `program` and `academic_year`
columns to opaque metadata without changing precedence or mutating reads.
[DATA-001](../decisions/security/ledger-and-data-safety.md) controls every later
physical transition.

## Compatibility

Historical flat imports and entry points remain supported through registered
thin facades. New internal code uses canonical package imports. The complete
machine-readable inventory and removal conditions are described in the
[compatibility register](../governance/compatibility-surfaces.md).
