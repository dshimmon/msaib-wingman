# GOV-004 — Crew Chief Independent Audit Workflow

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "GOV-004",
  "title": "Crew Chief Independent Audit Workflow",
  "namespaces": ["governance", "operations"],
  "status": "accepted",
  "date": "2026-08-09",
  "authority": "Maverick",
  "scope": "Repository-scoped Crew Chief v1 audit envelopes, fresh read-only review, structured findings, and finding-by-finding reconciliation",
  "approval_evidence": "Maverick's 2026-08-09 CANOPY-7C2F-ATLAS Crew Chief implementation and single-local-commit authorization",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

Crew Chief is Wingman's repository-scoped independent audit role for the
governed Codex review loop. Codex freezes an approved mission, exact Git
subject, engineer report, test claims, and evidence into a deterministic,
expiring audit envelope. A fresh read-only reviewer produces canonical JSON
findings. Codex then resolves, disputes with exact counter-evidence, or
escalates every finding before delivering a validated decision package to
Goose and Maverick.

The project-scoped model-facing role has one canonical definition:
[`crew-chief.toml`](../../../.codex/agents/crew-chief.toml). The deterministic
controller and stable JSON Schemas live under
[`tools/crew_chief/`](../../../tools/crew_chief/). The operational procedure
is the canonical [Crew Chief runbook](../../runbooks/crew-chief.md).

Crew Chief is advisory and cannot mutate the repository, approve a lifecycle
gate, expand scope, or impersonate Goose or the Development Flightline Auditor.
It may review its initial implementation when that work is labeled honestly as
self-review; independent certification requires a genuinely separate reviewer.
The v1 controller uses external, single-workspace consumption markers rather
than a global audit database. Model audits require authorization and suitable
controls, but they are not restricted exclusively to formal handoffs or
categorically excluded from CI.

## Authorization trust boundary

Crew Chief v1 trusts Maverick's authenticated Mission Control interaction and
the local operating-system account as the external authorization boundary.
The package-bound receipt is created only after that external decision and is
a tamper-evident record of the exact package, schema, subject, scope, and
expiry. Its content-derived identifier does not independently authenticate
Maverick, prove human identity, or reject a forged receipt created by a
malicious process already operating as the trusted local account.

That same-account impersonation risk is explicit residual risk for Maverick's
acceptance or rejection. V1 does not introduce signing keys, Keychain
integration, remote identity services, or other cryptographic identity
infrastructure. A future stronger identity boundary requires separate
architecture and authorization.

## Bootstrap tooling

The ordinary-Codex bootstrap path remains available for separately authorized
review and preserves honest reviewer identity. It is not a mandatory closeout
gate. When used, the ordinary reviewer operates read-only, does not select Crew
Chief, and states, “This bootstrap audit is not a Crew Chief audit.” A Crew
Chief review of its own implementation is self-review and must not be labeled
independent certification.

The ordinary-bootstrap command is constructed internally from the same
canonical isolation contract as Crew Chief execution, without selecting the
Crew Chief agent. Preparation binds the resolved Codex executable and exact
command. Immediately before receipt consumption, execution re-detects the CLI,
verifies the executable binding, and recomputes and exactly compares every
required argument, disabled feature, frozen path, output path, and standard-
input marker. Any omission, addition, duplication, meaningful reordering, or
weakened control fails before process launch.

The shared isolation contract includes `--skip-git-repo-check`. Crew Chief
review workspaces are deliberately frozen external evidence directories, not
Git checkouts; this flag permits that intended subject shape without weakening
the read-only sandbox, approval denial, ignored configuration and rules,
disabled-capability inventory, schema binding, output binding, or standard-
input evidence contract. Capability detection requires the exact flag, and
normal and bootstrap execution reject a prepared command that omits, changes,
duplicates, adds, or meaningfully reorders any canonical control.

## Operational audit pools

One pool may prepare or run several independent Crew Chief subjects with a
bounded standard-library thread executor. Each manifest job names one absolute
audit envelope, one unique job ID, an optional unique external workspace, and
an optional per-job fresh-session fallback decision. The default concurrency
is two; operators may select one through four. Additional jobs remain queued.

The controller validates the complete manifest, every envelope and expiry,
repository bindings, external output paths, workspace uniqueness, and path
overlap before any job can launch. It then creates a separate frozen evidence
tree, prompt, schemas, invocation, output directory, and atomic consumption
marker for every job. One failed job does not cancel another, and there is no
automatic retry. Pool reports retain manifest order, record requested and
observed concurrency, per-job bindings, verdicts, errors, timestamps, and token
counts when exposed by the CLI, and fail overall when any job fails or blocks.
They do not combine or synthesize findings across subjects.

Concurrency controls latency, not cost. Every executed job remains a distinct
authenticated model invocation with its own token use, so total cost is
approximately additive. The default of two balances throughput against local
resource and service pressure; increasing it requires an operator decision and
does not expand audit authority. Pool execution is operational evidence, not
independent certification, approval, publication authority, or mission
completion.

This decision does not itself authorize publication or a live model audit.
