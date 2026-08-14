# External Development-Operations Closeout Contract

Wingman requires independent audit and exact landing controls, but does not
implement or own the agents that perform them. An external capability may
satisfy this contract without becoming a Wingman OS capability, product agent,
runtime dependency, repository plugin, or repository-scoped configuration.
The repository never loads an operator from a user home directory.

This contract keeps these states distinct: authorized, implemented, tested,
audited, reconciled, approved for a named mutation, committed, published,
merged, verified, bounded-task complete, and strategic-mission complete.
Evidence for one state never proves a later state.

## Independent audit gate

The implementer freezes the governing task authority, repository instructions,
baseline and candidate identity, complete staged and unstaged binary diffs,
authorized untracked inventory and hashes, file modes, validation evidence,
and relevant architecture or decision records. A fresh reviewer that did not
implement the candidate then:

1. verifies the frozen subject before and after review;
2. operates read-only against the implementation repository;
3. evaluates every acceptance criterion and reports exact validation results;
4. records concrete findings with severity, evidence, impact, and bounded
   remedy; and
5. returns an explicit verdict and states whether the review was independent.

Landing eligibility requires an independent `PASS` with zero findings, every
required criterion proven, complete finding reconciliation, current validation
bound to the same bytes, and an unchanged candidate. Self-review,
`PASS_WITH_ADVISORIES`, missing evidence, an ambiguous subject, or changed
bytes cannot satisfy the gate.

## Exact landing gate

A separate external landing operator prepares from the unchanged audited
candidate. Before any mutation it verifies the audit, reconciliation,
validation, exact authorized paths, branch and remote state, clean or explicitly
preserved index state, destination refs, fast-forward relationships, and the
action-specific authority for every requested mutation.

Preparation is non-mutating and identifies the exact ordered actions, commit
messages, source and destination refs, excluded work, stop behavior, and
success conditions. Stage, commit, push, merge, deployment, migration,
live-data mutation, cleanup, and completion declaration are separate actions;
none is inferred from another. Force operations, shared-history rewrites,
automatic retry after mutation, and protection overrides are prohibited.

Any drift invalidates the plan. A partial persistent mutation stops all further
action and requires a new diagnosis and authority; it is never success.

## Capability availability

Codex must disclose which external capability supplied each gate and preserve
its evidence. If no conforming independent reviewer or landing operator is
available, the corresponding gate is `BLOCKED`. Codex must not silently
self-certify, revive the removed repository machinery, or substitute manual
Git mutation. Installing, selecting, updating, or trusting an external
capability is managed outside this repository.

## Product and operations boundary

This contract governs repository closeout only. It does not change Wingman OS,
Atlas, Portfolio Wingman/Radar, Ledger, deployment, migration, or live-data
authority. Development Flightline remains a separate Engineer isolation and
controller capability under [OPS-001](../decisions/governance/development-flightline.md);
its non-equivalence and retained safety controls are recorded in the
[extraction assessment](flightline-extraction-assessment.md).
