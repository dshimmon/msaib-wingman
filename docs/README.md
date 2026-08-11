# Wingman Documentation

Read [`AGENTS.md`](../AGENTS.md) first. It defines repository operating rules
and authority. Then use [`CURRENT_MISSION.md`](../CURRENT_MISSION.md) for the
generated portfolio entry point.

## Repository map

This is the single canonical human-readable filing map for the repository. It
shows ownership and where new files belong; it does not replace mission or
decision authority. Follow the
[current architecture](wingman-os/architecture.md) and
[Product Contract v1](wingman-os/product-contract-v1.md) for technical boundary
details rather than duplicating those contracts here.

### Repository-root entry points

- [`AGENTS.md`](../AGENTS.md) — operating instructions and authority order;
- [`CURRENT_MISSION.md`](../CURRENT_MISSION.md) — generated current-mission
  entry point;
- [`WINGMAN_VAULT.md`](../WINGMAN_VAULT.md) — approved future capabilities and
  deferred obligations; and
- [`README.md`](../README.md) — product orientation and supported commands.

### Annotated tree

```text
.codex/                                   # `.codex/` — repository-scoped Codex configuration
  agents/                                 # `.codex/agents/` — canonical project-scoped custom-agent definitions

src/                                      # `src/` — production source and historical import surfaces
  wingman/                                # `src/wingman/` — Wingman-owned production namespace
    core/                                 # `src/wingman/core/` — product-neutral Wingman mechanisms
      ledger/                             # `src/wingman/core/ledger/` — canonical Ledger implementation
    shared/                               # `src/wingman/shared/` — reusable product framework and contracts
  products/                               # `src/products/` — product-owned production namespaces
    atlas/                                # `src/products/atlas/` — Atlas-owned product behavior
    radar/                                # `src/products/radar/` — isolated Radar boundary; no product behavior yet
  *.py                                    # historical flat modules — compatibility façades only
  ledger/                                 # `src/ledger/` — historical package compatibility façades only

docs/                                     # `docs/` — documentation mirrors ownership and authority
  wingman-os/                             # `docs/wingman-os/` — current Wingman OS architecture and contracts
  products/                               # `docs/products/` — product documentation
    atlas/                                # `docs/products/atlas/` — current Atlas documentation
    radar/                                # `docs/products/radar/` — approved Radar boundary and planning
  governance/                             # `docs/governance/` — schemas, policy, and generated context
  missions/                               # `docs/missions/` — sole canonical mission status and evidence home
    wingman-os/                           # `docs/missions/wingman-os/` — Wingman OS mission records
    atlas/                                # `docs/missions/atlas/` — Atlas mission records
    operations/                           # `docs/missions/operations/` — operations mission records
    governance/                           # `docs/missions/governance/` — governance mission records
  decisions/                              # `docs/decisions/` — enduring decision records
    architecture/                         # `docs/decisions/architecture/` — accepted architecture decisions
    governance/                           # `docs/decisions/governance/` — accepted governance decisions
    security/                             # `docs/decisions/security/` — accepted security and data decisions
  runbooks/                               # `docs/runbooks/` — operational procedures
  archive/                                # `docs/archive/` — historical, superseded, and noncanonical material
  roadmap.md                              # `docs/roadmap.md` — approved future sequence and dependencies

tests/                                    # `tests/` — tests mirror production ownership
  wingman/                                # `tests/wingman/` — Core and Shared behavior
  products/                               # `tests/products/` — product-owned tests
    atlas/                                # `tests/products/atlas/` — Atlas behavior and composition
    radar/                                # `tests/products/radar/` — reserved Radar test boundary
  governance/                             # `tests/governance/` — architecture and filing-policy enforcement

tools/                                    # `tools/` — repository operations and governance tooling
  crew_chief/                             # `tools/crew_chief/` — deterministic independent-audit controller and schemas
  lso/                                    # `tools/lso/` — deterministic exact closeout controller and schemas
  flightline/                             # `tools/flightline/` — Development Flightline tooling
  governance/                             # `tools/governance/` — canonical-record and filing-policy enforcement

data/                                     # `data/` — runtime data, separate from source and documentation
```

Historical flat `src/` modules and `src/ledger/` are compatibility façades
only; no new implementation belongs there.

## Where new files belong

1. Product-neutral runtime logic → `src/wingman/core/`.
2. Reusable cross-product framework → `src/wingman/shared/`.
3. Atlas behavior → `src/products/atlas/`.
4. Radar behavior, when separately authorized → `src/products/radar/`.
5. Tests → the matching ownership path under `tests/`.
6. Mission status and evidence → `docs/missions/`.
7. Enduring decisions → `docs/decisions/`.
8. Operational procedures → `docs/runbooks/`.
9. Superseded historical material → `docs/archive/`.
10. Project-scoped custom-agent definitions → `.codex/agents/`.
11. Crew Chief controller logic and schemas → `tools/crew_chief/`.
12. LSO closeout controller logic and schemas → `tools/lso/`.
13. New logic must never be added to compatibility façades.

## Canonical homes

- [`missions/`](missions/) — mission authority, lifecycle, evidence, and next gates;
- [`decisions/`](decisions/) — enduring governance and architecture decisions;
- [`wingman-os/`](wingman-os/) — current Wingman OS documentation;
- [`products/atlas/`](products/atlas/) — current Atlas documentation;
- [`products/radar/`](products/radar/) — approved Portfolio Wingman/Radar
  boundary and planning;
- [`governance/`](governance/) — policy, schemas, compatibility, and generated context;
- [`runbooks/`](runbooks/) — operational procedures;
- [`archive/`](archive/) — superseded or noncanonical historical material; and
- [`roadmap.md`](roadmap.md) — approved future sequence and dependencies.

`.codex/agents/crew-chief.toml` is the single canonical model-facing home for
Crew Chief instructions. `docs/runbooks/crew-chief.md` owns its operator
procedure; neither location owns current mission lifecycle.

`tools/lso/` is the canonical deterministic closeout controller. Its operator
procedure is `docs/runbooks/lso.md`; the current mission record owns lifecycle.

`WINGMAN_VAULT.md` preserves approved future capabilities, strategic ideas,
deferred obligations, and the approval scope recorded by its entries.

The published [Ledger Transition mission](missions/wingman-os/ledger-transition/mission.md)
owns its implementation and audit record. The
[Ledger Transition runbook](runbooks/ledger-transition.md) owns the guarded
operator procedure; [DATA-001](decisions/security/ledger-and-data-safety.md)
owns the live-data authorization boundary.
