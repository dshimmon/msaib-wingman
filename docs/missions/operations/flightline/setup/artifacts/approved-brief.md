# Historical Artifact — Development Flightline Setup Brief

> This approved setup brief is preserved inside its authoritative mission
> record. Its authorization and Mission 028 statements describe the 2026-08-01
> setup gate; they are not current status. See the parent
> [`mission.md`](../mission.md) for current state.

**Call sign:** Flightline
**Status:** Approved by Maverick for setup implementation and harmless safety validation
**Approval date:** August 1, 2026
**Mission 028 status:** Brief approved; implementation unauthorized
**Commit authority:** None

## Objective

Create and validate a deterministic development-plane Flightline that launches
one mutable Development Engineer in a bounded isolated worktree, freezes its
evidence, and hands the frozen result to a fresh, separate read-only Independent
Auditor. The setup must make material limits enforceable rather than depend on
prompt-only promises.

The Development Engineer and Independent Auditor are temporary Codex
development roles. They are not Wingman OS agents. The Independent Auditor is
not Crew Chief and cannot be represented as Crew Chief.

## Authorized baseline

- Repository: `/Users/davidshimmon/Developer/Wingman/msaib-wingman`
- Branch: `main`
- Baseline commit: `4cabb431829a29357c6ead8c00fd7539b7e91fa7`
- Cached upstream at authorization: `origin/main`, local ahead four and behind
  zero without fetching
- Mission 027 canonical closeout baseline: 167 passing tests, consisting of
  141 unchanged pre-Airframe tests and 26 additive Airframe tests
- Existing unrelated Finder metadata and Office lock-file changes must remain
  inventoried and untouched

The active full-suite count must be measured rather than assumed from the
Mission 027 historical baseline.

## Scope

The setup may:

- add the Flightline controller, command guard, immutable role definitions,
  authorization/report schemas, example setup envelope, and harmless local
  validation harness under `tools/flightline/`;
- add Flightline-focused tests and the Development Flightline operating guide;
- record the approved planning package and reconcile canonical Flightline and
  Crew Chief sequencing language;
- create a deterministic Python 3.12 development environment and proposed
  platform-specific dependency lock through a separately controlled setup
  step;
- write preflight, test, sandbox-validation, frozen-handoff, and postflight
  evidence only to declared disposable temporary locations; and
- inspect the repository, cached Git metadata, and canonical records needed to
  prove the setup boundaries.

## Explicit exclusions

The setup must not:

- implement Mission 028 — Hardpoints or any product-contract change;
- implement Crew Chief, any Wingman OS agent, Mission Control runtime, Radar,
  or another product;
- modify product code, live data, the live Ledger, migrations, requirements,
  or the existing dependency lock during evidence refresh;
- use credentials, live services, model calls, external applications, or
  network access during Engineer or Auditor execution;
- stage, commit, push, merge, fetch, rebase, tag, release, deploy, alter Git
  refs/configuration, or perform destructive cleanup; or
- treat setup validation, audit, or brief approval as Mission 028
  implementation authorization.

## Required controls

1. Every role run uses a versioned authorization envelope with exact identity,
   baseline, worktree, writable scope, protected paths, command prefixes,
   tools, budgets, temporary outputs, acceptance criteria, exclusions, stop
   conditions, and absent Git/destructive authorities.
2. Silence in the envelope is denial. Invalid or missing fields fail closed.
3. The foreground checkout and protected Git metadata are not writable by a
   role. Mutable work occurs only in the named isolated worktree.
4. One mutable Development Engineer owns one bounded mission worktree.
   Additional mutable Engineers require explicitly partitioned scopes and
   Maverick's authorization.
5. The Independent Auditor runs in a fresh, separate session, receives no
   production writable paths, and cannot repair the change it audits.
6. The child environment is allowlisted and strips credentials, tokens, proxy
   settings, credential-agent sockets, and other ambient secrets.
7. Network is off and permission escalation is denied. Commands and tools are
   allowlisted; Git mutation, destructive operations, external tools, shell
   bypasses, and out-of-scope patches fail closed.
8. Time, command, token, file-count, deletion, symlink, and untracked-evidence
   limits are supervised outside the agent process.
9. Timeout, invalid output, cancellation, and failure preserve logs and return
   a safe `BLOCKED` or `INCOMPLETE` state without automatic cleanup.
10. Postflight must prove unchanged foreground HEAD, refs, index, Git
    configuration, remotes, protected data, and unrelated changes before a
    frozen handoff is eligible for audit.
11. Only the controller may issue an Independent Auditor envelope. It must be
    `PREFLIGHTED`, bind the exact frozen manifest, diff, evidence package,
    audit snapshot, baseline, and output paths, expire within a bounded period,
    and be atomically single-use.
12. The controller must build the Auditor's read-only snapshot from the
    approved baseline and frozen diff without copying protected repository
    data. Engineer and Auditor guards must reject self-issuance and relaunch.

## Deliverables

- deterministic Flightline controller and fail-closed guard;
- immutable Development Engineer and Independent Auditor role definitions;
- versioned authorization-envelope, Engineer-report, and Auditor-report
  schemas;
- setup validation envelope and local negative-test harness;
- Development Flightline operating, emergency-stop, recovery, and cleanup
  documentation;
- focused tests for parsing, paths, symlinks, environment sanitization,
  subprocess supervision, cancellation, timeout, evidence recovery, freezing,
  and prohibited operations;
- deterministic dependency-lock proposal with recorded provenance and an
  already provisioned clean Python 3.12 environment;
- exact preflight, validation logs, file inventory, hashes, frozen diff,
  postflight, and Engineer report for a fresh Independent Auditor;
- controller-issued Auditor envelope, issuance record, protected audit
  snapshot, expiration, single-use claim, and exact operator launch procedure;
  and
- explicit disclosure that Crew Chief remains a separate required future
  Wingman Assurance capability whose roadmap placement Maverick will decide
  after Hardpoints and before the relevant Assurance mission.

## Required validation

- validate the authorization envelope and completion-report schemas;
- compile the Flightline Python modules;
- run the full repository test suite in the provisioned clean environment and
  report the exact discovered count;
- run the Flightline-focused tests separately and report their exact count;
- run harmless OS-sandbox negative tests covering scoped Engineer writes,
  denied broader writes, denied protected/credential reads, read-only Git
  metadata, denied foreground data, denied loopback networking, denied Auditor
  source writes, and permitted Auditor evidence writes;
- validate controller issuance, frozen-artifact and snapshot bindings,
  expiration, atomic single use, active Flightline environment variables, and
  rejection of Engineer/Auditor self-authorization;
- run offline dependency-consistency and requirements-satisfaction checks;
- run `git diff --check`; and
- compare preflight and postflight evidence for HEAD, refs, index, Git
  configuration, remotes, working-tree inventory, protected data, unrelated
  files, and the proposed dependency-lock hash.

## Acceptance criteria

1. Controller and guard enforce the approved role, path, command, environment,
   network, credential, budget, Git, and destructive-operation boundaries.
2. The controller cannot substitute prompt language for enforceable controls.
3. The Engineer can write only its exact worktree scope and temporary outputs;
   the Auditor has no production write scope.
4. Foreground checkout mutation, protected-path access, credential access,
   external networking, live-data writes, prohibited Git operations, symlink
   escapes, shell-parser bypasses, unauthorized subprocesses, and cleanup fail
   closed.
5. Cancellation, timeout, invalid output, and failures preserve recoverable
   evidence and never clean automatically.
6. The approved full and focused test suites, compilation, schema/envelope,
   offline dependency, sandbox, and diff checks pass with exact evidence.
7. The original 167-test Mission 027 baseline remains historically distinct
   from the post-setup full suite; additive Flightline tests are counted and
   attributable.
8. HEAD, refs, index, remotes, Git configuration, protected data, unrelated
   files, and the existing dependency lock remain unchanged during evidence
   refresh.
9. Documentation consistently states that the roles are development-plane
   Codex roles, the Independent Auditor is not Crew Chief, Crew Chief is not a
   Mission 028 prerequisite or automatically post-037, and Mission 028
   implementation remains unauthorized.
10. A complete frozen Engineer evidence package is ready for a fresh,
    independent Auditor without staging or committing any file.
11. Maverick can run one documented controller command to issue and one command
    to launch a fresh Auditor; the issued envelope cannot be widened, replayed,
    or used after expiry by either development role.

## Authorization limits and gates

Decisions A–D in `Wingman_Pre-Mission_028_Planning_Package.md` were approved by
Maverick on August 1, 2026. The original planning operation did not authorize
this setup; Maverick authorized the bounded Flightline setup separately
afterward.

That authorization ends at an uncommitted, frozen evidence package. A fresh
Independent Auditor must evaluate it. The Auditor cannot authorize a commit.
Commit, push, merge, mission launch, and mission completion remain separate
Maverick gates. Mission 028 implementation remains unauthorized.
