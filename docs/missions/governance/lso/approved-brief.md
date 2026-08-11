# Landing Signal Officer v1 — Approved Implementation Brief

- **Canary:** `CANOPY-7C2F-ATLAS`
- **Authority:** Maverick
- **Authorization date:** August 11, 2026
- **Approved baseline:** `9c68ca8ef10a270358c510d1a333daf001d7caa1`
- **Implementation state:** authorized construction in an isolated worktree

## Objective

Build a deterministic Landing Signal Officer (LSO) that turns a final,
unchanged Crew Chief `PASS` into one exact closeout approval card and, only
after separate package-bound Maverick authorization, can commit the audited
implementation, fast-forward-publish it, generate and publish its completion
records, verify the remote state, and return one unambiguous completion report.

## Authorized engineering

- Implement versioned LSO evidence, plan, receipt, and execution-report
  contracts.
- Reuse Crew Chief's frozen audit and reconciliation evidence instead of
  creating a second review role.
- Require exact Git, file, test, mission, remote-target, and approval bindings.
- Implement single-use, no-automatic-retry conditional closeout execution.
- Test all repository-writing behavior only against disposable local Git
  repositories and bare remotes.
- Add governance records, operator documentation, deterministic tests, and CI
  coverage.
- Prepare but do not transmit an exact Crew Chief package for LSO itself.

## Explicit exclusions

- No Crew Chief model invocation during this build authorization.
- No staging, commit, push, merge, publication, or mission-completion claim for
  the real Wingman repository.
- No live Ledger, database, migration, deployment, production, credential, or
  `data/**` operation.
- No automatic approval, retry, force push, rebase, history rewrite, rollback,
  pull-request management, or broad agent orchestration.
- No global Codex hook installation. Hook activation remains an optional,
  separately reviewed deployment after the deterministic controller is proven.

## Acceptance criteria

LSO v1 must fail closed unless Crew Chief returned schema-valid `PASS` with
zero findings, reconciliation is complete and approval-ready, every required
validation passed, the audited working tree is byte-identical, `origin/main`
is still the frozen target, and an unexpired single-use receipt exactly binds
Maverick's required authorization text.

Disposable end-to-end tests must prove the two-commit closeout path, remote
verification, completion-record generation, no-retry consumption, drift and
target-advance rejection, audit-result rejection, and an honest `FAILED` or
`PARTIAL` report when any authorized action cannot complete.
