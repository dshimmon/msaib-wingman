# GOV-004 — Crew Chief Independent Audit Workflow

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "GOV-004",
  "title": "Crew Chief Independent Audit Workflow",
  "namespaces": ["governance", "operations"],
  "status": "superseded",
  "date": "2026-08-09",
  "authority": "Maverick",
  "scope": "Repository-scoped Crew Chief v1 audit envelopes, fresh read-only review, structured findings, and finding-by-finding reconciliation",
  "approval_evidence": "Maverick's 2026-08-09 CANOPY-7C2F-ATLAS Crew Chief implementation and single-local-commit authorization",
  "supersedes": [],
  "superseded_by": "GOV-006"
}
-->

## Decision

> **Superseded on 2026-08-14 by GOV-006.** This record preserves the
> repository-scoped implementation decision as history. It is not an active
> runbook or a claim that Crew Chief is a Wingman OS capability or runtime
> component.

Crew Chief is Wingman's repository-scoped independent audit role for the
governed Codex review loop. Codex freezes bounded task authority and/or an
approved mission, the exact Git subject, engineer report, test claims, and
evidence into a deterministic, expiring audit envelope. A fresh read-only reviewer produces canonical JSON
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

Ordinary bounded tasks do not require a pre-existing mission record. Their
task-authority artifact is frozen and hashed through the existing evidence
envelope. Mission records remain optional for legacy and genuinely
mission-based work. Missing mission data is omitted rather than represented by
a placeholder or unrelated record, and every envelope requires at least one
real authority source.

A canonical zero-finding `PASS` produces a proposed closeout record only in the
external audit bundle. The proposal binds the exact candidate and verified
implementation evidence, is marked proposed and not landed, and claims no
approval, repository mutation, or completion. Its historical audit-evidence
section is separately hashed so LSO can validate and preserve it while adding
actual commit hashes, remote refs, landing result, timestamps, and completion
state. LSO, not Crew Chief, validates and lands that record with the unchanged
audited implementation under Maverick's later authorization. Any other verdict
produces the report and findings but no closeout proposal.

## Authorization provenance boundary

Maverick is the sole authorizing principal. Mission Control and direct Codex
invocation are execution routes and never independent sources of authority.
Every new package-bound receipt captures a trusted-local caller attestation
that Maverick made an external authorization decision, the asserted Maverick
principal identifier, the exact authorization-text binding, the bounded
invocation scope, the execution route, and the Codex executor. The same
asserted Maverick principal is recorded whether Codex was invoked directly or
dispatched through Mission Control.

The authorization-text binding comprises both SHA-256 and UTF-8 byte size.
For version 2, the trusted-local expectation supplies both values independently
of the receipt, and validation rejects a receipt if either differs even when
its content-derived receipt ID has been recomputed. Version-1 validation does
not retrofit that new field into historical artifacts.

Receipt creation requires action-specific explicit approval evidence and an
exact evidence reference; authentication alone is not approval. The writer
checks that the caller-attested principal is exactly Maverick, the attestation
classification is known, the action text and scope match, and Mission Control
appears only as dispatcher for that route. Missing, unknown, non-Maverick,
internally inconsistent, or insufficient context fails before receipt
creation. These checks do not prove who supplied the inputs. Human-readable
wording is derived from the structured attestation rather than used as the
durable authority record.

New receipts use the version-2 contract. Version-1 receipts and their exact
historical wording remain readable and are never migrated, normalized, or
re-rendered. A receipt is a tamper-evident binding of the asserted external
decision to the exact package, schema, subject, scope, route, executor, and
expiry; its content-derived identifier does not independently authenticate
Maverick, prove human identity, or prevent a false but internally consistent
attestation created by a process already operating as the trusted local
account.

That same-account impersonation risk is explicit residual risk for Maverick's
acceptance or rejection. This correction does not introduce signing keys,
Keychain integration, remote identity services, or other cryptographic
identity infrastructure. A future stronger identity boundary requires
separate architecture and authorization.

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
counts when exposed by the CLI. Operational states are distinct from audit
verdicts: a schema-valid `FAIL` or `BLOCKED` is a completed audit job, while
preparation, control, or runner failure makes the pool fail operationally.
Pool reports do not combine or synthesize findings across subjects.

Concurrency controls latency, not cost. Every executed job remains a distinct
authenticated model invocation with its own token use, so total cost is
approximately additive. The default of two balances throughput against local
resource and service pressure; increasing it requires an operator decision and
does not expand audit authority. Pool execution is operational evidence, not
independent certification, approval, publication authority, or mission
completion.

## External report retention

Normal and pool execution store each audit or pool report as a separate bundle
inside one explicitly marked external output root. The controller creates the
bundle before process launch and never keeps an append-only report-history
array. Automatic pruning occurs only after the new canonical report and run
record are written successfully; pool pruning additionally requires overall
operational success.

Retention defaults to 30 days and 100 completed report bundles, with explicit
CLI overrides for both limits. A bundle is eligible when either limit is
exceeded. Age is derived from validated completion metadata. Count pruning is
deterministic by completion time and report ID, retaining the newest bundles.
Queued, running, and currently written reports are never candidates.

The marked root, every metadata record, required completed artifacts, and the
whole tree are validated before any removal. Symlinks, ambiguous roots, path
escapes, repository-internal roots, duplicate identifiers, malformed metadata,
and incomplete completed bundles fail closed. Cleanup removes the complete
bundle and replaces one bounded `retention-state.json`; it does not preserve an
unbounded deletion log. A dry-run command reports the same candidate set with
no deletion or state mutation. This lifecycle deletion is not represented as
secure erasure.

This decision does not itself authorize publication or a live model audit.
