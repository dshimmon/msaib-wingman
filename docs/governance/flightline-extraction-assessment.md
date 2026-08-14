# Flightline Extraction Assessment

## Outcome

Published Development Flightline is retained unchanged. The external audit and
landing contract does not prove material equivalence to Flightline's Engineer
isolation/controller role, so removal or weakening would be a separate
architecture decision for Maverick.

## Unique controls and dependencies

The published controller under `tools/flightline/` combines controls not
provided by an audit report or exact landing plan:

- versioned authorization envelopes bound to Canary, baseline, role, paths,
  budgets, network policy, credential policy, and authority;
- exact writable-path isolation for an Engineer and read-only isolation for a
  fresh Auditor;
- foreground-checkout denial with only narrow Git-metadata access;
- explicit credential, protected-data, network, web, app, and multi-agent
  denial plus an allowlisted child environment;
- approval denial and command guards against shell composition, Git mutation,
  deletion, privilege changes, external tools, escalation, and out-of-scope
  patches;
- supervisor enforcement of elapsed-time, command, token, and changed-file
  budgets with preserved failure evidence;
- postflight protection of refs, index, config, remotes, `HEAD`, worktree
  state, file inventory, symlinks, size limits, and diff hygiene;
- controller-issued, expiring, single-use Auditor authorization bound to a
  frozen manifest, binary diff, evidence package, immutable non-Git snapshot,
  prompt, schemas, and model schema preflight; and
- startup-lifecycle and launch-preflight evidence that fails closed on drift.

Its operational dependencies include the dedicated Python runtime, installed
Codex CLI behavior, permission profiles and hooks, local sandbox validation,
Git worktree metadata, external temporary evidence roots, and the published
Flightline schemas and roles. These dependencies are isolated from Wingman OS
and product runtime code.

## Separate Maverick options

1. Retain Flightline and separately authorize its maintenance correction and
   fresh validation.
2. Commission an equivalence study against a replacement Engineer isolation
   controller, then decide whether a reversible retirement is possible.
3. Retire Flightline only under a later architecture decision that explicitly
   accepts or replaces every safety control above.

This task selects none of those options. The recovered unpublished schema
correction remains outside the active repository candidate in its durable
recovery capsule.
