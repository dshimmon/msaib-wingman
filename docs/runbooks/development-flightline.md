# Development Flightline

> **Capability health: maintenance pending.** The historical setup delivery is
> preserved at commit `ea9f3e0`, but its bounded correction remains uncommitted
> in the protected foreground checkout as of 2026-08-07. Do not launch a new
> Engineer or Auditor from this runbook until that correction is committed and
> independently verified. Current status is authoritative in
> [`operations/flightline/setup`](../missions/operations/flightline/setup/mission.md).

The implementation details below describe the committed `ea9f3e0` setup. Any
statement that Mission 028 had not begun is historical: Hardpoints was later
completed at `2b3b9a6`.

The Development Flightline is a deterministic development-plane control system
for launching one mutable Codex Development Engineer in an isolated worktree,
freezing its evidence, and handing the result to a fresh read-only Independent
Auditor. Neither role is a Wingman OS agent. The Independent Auditor may audit
Mission 028 but is not Crew Chief and must not be represented as Crew Chief.

## Authority boundary

Every run requires a versioned JSON authorization envelope. Version 1.1 makes
the Auditor envelope controller-issued rather than operator-authored. The
controller rejects an incorrect Canary, baseline, role, path, state, budget,
network policy, credential policy, or authority field. Silence is denial.

The controller has no command that stages, commits, pushes, merges, rebases,
tags, releases, deploys, cleans, or removes a worktree. A detached worktree may
be created only by the explicit `prepare-worktree` operation with its exact
confirmation phrase. Worktree removal remains a later Maverick-authorized
operation.

Every future mission still requires its own implementation prompt,
authorization envelope, verified current baseline, isolated worktree,
Engineer report, frozen evidence, fresh Independent Auditor session, and
Maverick review. Commit, push, and merge remain separate gates.

## Installed controls

The controller and schemas are under `tools/flightline/` and are kept outside
normal mission writable scopes.

1. Both roles inherit Codex's `:read-only` permission profile.
2. The Engineer receives `write` access only to exact envelope paths and
   declared temporary outputs.
3. The Auditor receives no production writes and can write only declared audit
   outputs.
4. The foreground checkout is denied, with a narrow read exception for Git
   metadata required by a detached worktree.
5. Credential and protected-data paths are explicitly denied, and the child
   process receives a minimal allowlisted environment with ambient tokens,
   passwords, API keys, and credential-agent sockets removed.
6. Network, web search, apps, Browser, Computer Use, Image Generation, and
   multi-agent operation are disabled.
7. Approval policy is `never`; a PermissionRequest hook always denies.
8. The PreToolUse guard rejects unapproved commands, shell control operators,
   Git mutations, deletes, moves, privilege changes, external tools, sandbox
   escalation, and out-of-scope patches.
9. The external supervisor enforces elapsed-time, command, token, and changed-
   file budgets and preserves JSONL, stderr, startup-lifecycle, and summary
   evidence on child-creation failure, startup rejection, timeout, invalid
   output, termination, or operator interruption.
10. Postflight freezing rejects changed security-relevant foreground refs,
    index, configuration, remotes, `HEAD`, or working-tree state; changed
    worktree `HEAD`;
    unauthorized paths; deletions; excess files; symbolic links; oversized
    untracked evidence; and diff-whitespace errors. The frozen binary diff
    includes tracked, staged, and untracked changes.
11. `preflight-auditor-schema` makes one non-authorized, no-tools model call
    against the canonical Auditor report schema. It preserves the model-service
    response evidence and issues or consumes no authorization. A current,
    model-accepted record is mandatory for issuance and launch.
12. `issue-auditor` verifies the Engineer envelope, the bound schema preflight,
    and frozen handoff,
    materializes a non-Git audit snapshot from the approved baseline plus the
    frozen diff, excludes repository-relative protected paths, and emits a
    `PREFLIGHTED` `independent-auditor` envelope.
13. The issued envelope is sealed by checksum to the frozen manifest, diff,
    complete evidence package, audit-snapshot manifest, controller-captured
    foreground preflight, controller-generated prompt, accepted report schema,
    and non-authorized schema-preflight record. It expires within 24 hours and
    is consumed through an atomic single-use record immediately before the
    child process starts.
14. The issuance and consumption records remain outside Engineer and Auditor
    writable paths. The guard blocks either role from invoking issuance,
    schema preflight, worktree preparation, or launch to authorize itself.
15. The intentionally non-Git Auditor snapshot is launched with Codex's
    narrowly scoped `--skip-git-repo-check` option. The Engineer launch does
    not receive that option, and Flightline does not add Git metadata to the
    frozen snapshot.

The installed CLI verified during setup is `codex-cli 0.146.0-alpha.9.2`.
Network access was not authorized, so the remote Codex manual was not refreshed.
The setup instead used the installed CLI help, generated local app-server
schemas, direct hook input/output schemas embedded in the installed binary, and
harmless `codex sandbox` negative tests. Current-session behavior controls if a
future manual differs.

## Files

- `flightline.py`: envelope validation, profile rendering, preflight,
  worktree preparation, evidence freezing, controller-side Auditor issuance,
  immutable audit-snapshot creation, and launch supervision.
- `guard.py`: fail-closed PreToolUse and PermissionRequest command hook.
- `roles/`: immutable Engineer and Auditor role definitions.
- `schemas/`: authorization, Engineer-report, and Auditor-report schemas.
- `examples/setup-validation-envelope.json`: the bounded setup/preflight
  envelope; it has no implementation prompt and therefore cannot launch work.
- `validate_setup.py`: local permission-profile and negative-test harness.

## One-time safety validation

Run validation only in a new explicit temporary directory. The harness preserves
its artifacts for review and never contacts an external host:

```text
.venv/flightline-py312/bin/python -m tools.flightline.validate_setup \
  --fixture-root /private/tmp/wingman-flightline-validation-<id> \
  --protected-probe /absolute/repository/.env
```

Expected checks include scoped Engineer write, denied worktree-root write,
denied secret read, readable-but-not-writable Git metadata, denied foreground
data, denied loopback socket, denied Auditor repository/source/Git writes,
denied Auditor credential and protected-data reads, denied Auditor network,
and allowed Auditor evidence write.

## Issue and launch a fresh Independent Auditor

Maverick or the authorized operator runs these controller commands outside any
Engineer or Auditor child session. The Auditor cannot create its own envelope.
Use a new `<audit-id>` for every attempt; partial or expired authorization
artifacts are preserved rather than overwritten.

1. From a controller-owned fresh temporary home with subscription
   authentication isolated from tool access, obtain model acceptance of the
   canonical schema. This command creates no authorization:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/flightline-py312/bin/python \
  -m tools.flightline.flightline preflight-auditor-schema \
  tools/flightline/examples/setup-validation-envelope.json \
  --output-root /private/tmp/wingman-flightline-schema-preflights/<audit-id>
```

   A successful record has state `MODEL_ACCEPTED`, zero command/tool events,
   and explicit `authorization_issued: false` and
   `authorization_consumed: false` fields. Any model, transport, schema, tool,
   or output failure stops the cycle without an authorization.

2. Confirm the refreshed frozen manifest and evidence-package paths from the
   Engineer report. Issue a one-hour, single-use authorization bound to the
   successful schema preflight:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/flightline-py312/bin/python \
  -m tools.flightline.flightline issue-auditor \
  tools/flightline/examples/setup-validation-envelope.json \
  --schema-preflight /private/tmp/wingman-flightline-schema-preflights/<audit-id>/schema-preflight.json \
  --frozen-manifest /private/tmp/<frozen-evidence>/frozen-manifest.json \
  --evidence-package /private/tmp/<frozen-evidence>/evidence-package.json \
  --audit-workspace /private/tmp/wingman-flightline-audits/<audit-id>/workspace \
  --audit-output /private/tmp/wingman-flightline-audits/<audit-id>/output \
  --authorization-root /private/tmp/wingman-flightline-authorizations/<audit-id> \
  --expires-in-seconds 3600 \
  --confirm ISSUE_FRESH_INDEPENDENT_AUDITOR
```

   Issuance fails unless the source envelope is an approved Engineer envelope,
   the foreground `HEAD` is the approved baseline, the evidence package binds
   the exact frozen manifest, every hash matches, all three output roots are
   new and disjoint, and the command is running through
   `.venv/flightline-py312`.

3. Validate the unexpired, unused controller record and render the exact
   profile if desired:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/flightline-py312/bin/python \
  -m tools.flightline.flightline validate \
  /private/tmp/wingman-flightline-authorizations/<audit-id>/auditor-envelope.json
```

4. Launch a brand-new Auditor. This atomically consumes the authorization;
   repeating the command fails closed:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/flightline-py312/bin/python \
  -m tools.flightline.flightline launch \
  /private/tmp/wingman-flightline-authorizations/<audit-id>/auditor-envelope.json
```

The child receives `WINGMAN_FLIGHTLINE_ENVELOPE`,
`WINGMAN_FLIGHTLINE_ROLE=independent-auditor`, the controller authorization
ID, frozen-manifest and evidence-package paths, the audit-output path, and the
exact Flightline Python runtime. The launch rechecks the foreground preflight,
every frozen binding, the complete audit-snapshot tree hash, expiry, and unused
state before creating the single-use record.

### Auditor startup lifecycle

The controller runs the child with the frozen audit snapshot as both the Codex
`-C` root and the operating-system working directory. It records that exact
directory and a position-preserving argv whose hook and permission-profile
payloads are redacted.

Every launch preserves four controller outputs: the JSONL event stream, full
stderr log, startup-lifecycle record, and supervisor summary. The startup record
begins at `CHILD_NOT_CREATED`, advances to `CHILD_CREATED` only after `Popen`
returns, and advances to `AUDITOR_ENVIRONMENT_ACTIVATED` only after the Codex
JSONL stream supplies a valid `thread.started` event with a thread ID. A normal
exit then records `COMPLETED`; an activated nonzero exit or controller stop
records `TERMINATED`. A child that exits without the activation event records
`STARTUP_REJECTED` and is never reported as active.

Startup failures populate a structured `stop_reason` containing a stable code,
phase, concise diagnostic, and full stderr-log path. Flightline relays the
concise diagnostic to foreground stderr while leaving the complete child log
unchanged. The model-level activation proof required by the Auditor report
remains a separate audit obligation; the controller handshake proves only that
the configured Codex child crossed its local startup boundary.

### Security-relevant Git references

Flightline canonicalizes every reference returned by `git show-ref` and
protects its individual name/object-ID binding plus a SHA-256 digest. The only
excluded namespace is `refs/codex/turn-diffs/`, which the Codex app uses for
ephemeral checkpoint and capture bookkeeping during normal development-plane
activity. No other `refs/codex/` reference is excluded.

The exclusion does not weaken the separate `HEAD`, current branch, upstream,
cached divergence, index, local Git configuration, remote-name, or porcelain
working-tree comparisons. Local branches, remote-tracking references, tags,
notes, stash refs, and every other non-turn-diff reference remain protected.
Frozen-manifest, frozen-diff, evidence-package, audit-snapshot, prompt, and
envelope checksums also remain mandatory.

Every Auditor launch attempt writes a controller-protected
`controller-launch-preflight.json` beside the issuance record before the
authorization is consumed. It records the authorization-time and launch-time
nested metadata, the exact mismatched fields, and individual changed
security-relevant refs. A mismatch remains `BLOCKED`; the record prevents reuse
of that attempt and the error reports its exact path.

## Per-mission sequence

1. Maverick approves the exact brief and envelope.
2. Validate the envelope and record the foreground preflight.
3. Create one detached worktree at the approved baseline using the exact
   `prepare-worktree` confirmation.
4. Update the envelope state to `PREFLIGHTED`; add the approved prompt and its
   SHA-256 checksum.
5. Launch the Engineer. Any new permission request fails closed.
6. Freeze the diff and evidence. The Engineer may no longer change them.
7. Run `preflight-auditor-schema` from the controller and preserve its
   non-authorized model-acceptance record.
8. Invoke `issue-auditor` from the controller with that record, the frozen
   manifest, and evidence package; never hand-author an Auditor envelope.
9. Validate and launch that fresh, expiring, single-use Auditor envelope.
10. Present reports to Maverick. No commit exists.
11. If Maverick approves an exact reviewed diff, use a fresh commit-only
   operation. Push and merge remain separately authorized.

## Emergency stop and recovery

Interrupt the controller process. It sends an interrupt, then terminates the
child if necessary, flushes the JSONL log, and records `BLOCKED` or
`INCOMPLETE`. It does not clean or delete the worktree. Inspect the event log,
working-tree status, controller launch-preflight comparison, security-relevant
foreground refs, index checksums, and preserved artifacts before deciding what
to do next.

Cleanup is never automatic. After Maverick explicitly authorizes cleanup,
verify the exact worktree with `git worktree list`, preserve any required diff
or untracked file hashes, and remove only that named disposable worktree. Never
use forced cleanup to conceal unresolved state.

## Known boundary

The local safety setup does not itself require external access. Every fresh
Auditor authorization additionally requires the isolated, non-authorized live
schema preflight described above. The first real mission launch must also
revalidate the installed CLI version, hook loading, exact permission profile,
baseline, and negative tests. A failure is `BLOCKED`, not a reason to bypass
hook trust, sandboxing, the schema gate, or the authorization envelope.
