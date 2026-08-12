# Crew Chief Independent Audit

The sole canonical current lifecycle record is
[`governance/crew-chief/mission.md`](../missions/governance/crew-chief/mission.md);
this runbook defines procedure and does not claim mission status. Crew Chief's
single canonical model-facing instruction file is
[`crew-chief.toml`](../../.codex/agents/crew-chief.toml). Do not duplicate or
silently amend those instructions in an operator prompt.

Crew Chief implements this governed handoff:

> Codex implementation report → frozen audit envelope → fresh read-only
> reviewer → structured findings → Codex reconciliation → validated decision
> package → Goose and Maverick decision

## When Crew Chief is authorized

Use Crew Chief when the task, mission, or Maverick's instruction authorizes an
audit. Bootstrap tooling is available but is not a universal closeout gate.
Preparing an envelope is not an audit. Preparing a command is not an audit. A
valid report exists only after an explicitly authorized review returns
schema-valid JSON bound to the exact envelope.

Select one risk profile:

- `standard` — ordinary bounded implementation;
- `deep` — architecture, security, data, dependencies, public contracts,
  migrations, or other high-risk behavior; or
- `exempt` — generated or status-only changes with a recorded justification
  and deterministic governance-validation evidence.

An exemption bypasses a model review only for the exact approved subject. It
does not imply approval, publication, or mission completion.

## Prepare and freeze evidence

Start from a verified repository root. Confirm the approved mission, exact base
and head, branch, status, scope, engineer report, evidence artifacts, and test
claims. Inputs must be regular files and must not expose credentials, `.env`
files, keys, tokens, or live data. Use a new external destination; the
controller refuses repository-internal audit outputs and existing targets.

For a committed range:

```text
PYTHONDONTWRITEBYTECODE=1 python -m tools.crew_chief prepare \
  --repository /absolute/repository \
  --mission-record /absolute/repository/docs/missions/<mission>/mission.md \
  --base <approved-base> \
  --head <implementation-head> \
  --engineer-report /absolute/external/engineer-report.json \
  --evidence /absolute/external/validation.log \
  --test-claims /absolute/external/test-claims.json \
  --profile standard \
  --output-root /private/tmp/wingman-crew-chief-envelope-<audit-id>
```

For staged, unstaged, or untracked work, set `--base` and `--head` to the
intended committed range, add `--include-working-tree`, and repeat
`--allow-untracked <repository-relative-path>` for every untracked file. The
allowlist must equal the observed untracked inventory exactly. The controller
captures binary full-index diffs, file type, mode, and base, head, index, and
worktree SHA-256 values as applicable. It also freezes content-addressed,
deduplicated source bytes for every available changed-file state. The manifest
records the exact repository path, revision or state, presence, file type,
mode, size, encoding, line count when textual, digest, and frozen binding. This
provides complete head text for every changed regular text file, base text for
modified or deleted files, and exact index and worktree content when those
states are in scope. Binary bytes are bound deterministically and labeled for
base64 presentation rather than decoded as text.

The envelope binds the canonical repository identity, resolved path, mission
hash, Git state, subject inventory, evidence, risk profile, deterministic
manifest, identifiers, and a maximum 24-hour expiry. Hashing uses canonical
UTF-8 JSON with sorted keys and compact separators. Reverification rejects
changed or missing evidence, Git drift, path escape, unbound files, secret or
live-data paths, and expiry.

## Prepare or run a fresh review

Command preparation is safe and does not invoke a model:

```text
PYTHONDONTWRITEBYTECODE=1 python -m tools.crew_chief run \
  /private/tmp/wingman-crew-chief-envelope-<audit-id>/audit-envelope.json \
  --workspace /private/tmp/wingman-crew-chief-review-<audit-id>
```

The controller feature-detects the installed Codex CLI with version, `exec
--help`, and `features list`. It requires ephemeral execution, explicit
read-only sandboxing, approval denial, structured output, ignored user
configuration, ignored repository rules, `--skip-git-repo-check` for the
intentionally non-Git frozen workspace, exact output capture, and explicit
feature-disable controls. It refuses automated execution if any required
control or the supported shell-tool disable feature is absent. The exact flag
must be present; a lookalike flag does not satisfy detection. Failed,
malformed, or duplicate feature evidence fails closed.

The 2026-08-09 acceptance probe of `codex-cli 0.147.0-alpha.6.5` classified all
38 enabled features as prohibited for the review process:

- tool, application, network, or external-capability surfaces: `apps`,
  `auth_elicitation`, `browser_use`, `browser_use_external`,
  `browser_use_full_cdp_access`, `code_mode_host`, `computer_use`, `hooks`,
  `image_generation`, `in_app_browser`, `multi_agent`, `plugin_sharing`,
  `plugins`, `remote_plugin`, `shell_snapshot`, `shell_tool`,
  `skill_mcp_dependency_install`, `skill_search`,
  `tool_call_mcp_elicitation`, `tool_search_always_defer_mcp_tools`,
  `tool_suggest`, `unified_exec`, and `workspace_dependencies`;
- workflow, approval, identity, or inherited-context surfaces:
  `collaboration_modes`, `fast_mode`, `goals`, `guardian_approval`,
  `mentions_v2`, `personality`, and `steer`;
- transport, storage, UI, or runtime features lacking affirmative isolation
  evidence: `enable_request_compression`, `in_app_updates`, `item_ids`,
  `remote_compaction_v2`, `resize_all_images`, `sqlite`,
  `terminal_resize_reflow`, and `tui_app_server`.

The permitted-remain-enabled set is therefore empty. The controller accepts a
known prohibited enabled name only because the final argv explicitly disables
it. Any unfamiliar enabled feature stops preparation before model invocation;
names are never inferred safe. This deliberately conservative classification
may be relaxed only by a later evidence-backed change proving that a feature
cannot expose a model-facing tool, network path, external application,
credential, writable capability, approval path, or inherited mutable context.
The controller records the CLI version, exact capabilities, argv array,
selection mode, and any limitation.

Before any `codex exec` process can start, the runner constructs the exact
service-facing schema payload and validates that payload offline. Canonical
schemas remain the full post-generation contract. The service projection adds
explicit matching types to constants and enums, requires every property on
every object, represents canonical optional fields as required nullable
fields, replaces nested `oneOf` alternatives with `anyOf`, retains only
resolving local references, and projects away unsupported generation-time
keywords such as `uniqueItems`. The offline preflight rejects malformed
schemas, non-local or unresolved references, unsupported keywords, untyped or
mismatched constants and enums, incomplete object requirements, and any object
without `additionalProperties: false`.

The exact checked projection is written to
`schemas/crew-chief-report.schema.json`, bound into the invocation record, and
passed unchanged to `--output-schema`. The full bundled canonical report is
bound separately. After generation, the raw service-shaped result is validated
against the checked projection and preserved as
`reports/<report-id>/crew-chief-service-report.json`; deterministic
normalization removes only nullable placeholders for canonical optional
fields. The normalized report and run record are written separately in that
same bundle. The output bundle is created before process launch so the exact
`--output-last-message` destination always has an existing parent directory.
The normalized report must then pass the full canonical schema and all
evidence, verdict, risk-focus, citation, finding-uniqueness, and authority
checks. Projection therefore does not replace or weaken canonical validation.

Because the shell tool is disabled, the controller deterministically embeds
the complete frozen evidence set in standard input. Each block names its exact
frozen path, size, encoding, and SHA-256 digest. UTF-8 files without NUL bytes
remain text; other regular files are base64-labeled. The payload includes the
frozen mission record, complete changed-source context, engineer report, test
claims, diffs, authorized evidence artifacts, controls, envelope, and manifest.
Encoded evidence is limited to 16 MiB for v1 and an oversized envelope fails
before any model invocation. The
external read-only artifact tree remains available for operator evidence and
exact artifact references, not as a substitute for the standard-input review
payload.

If the CLI exposes a supported non-interactive custom-agent selector, the
command selects `crew_chief`. If it does not, the controller does not invent
one: it prepares a fresh-session fallback whose prompt points to the frozen
agent file. Executing that fallback additionally requires an explicit
`--allow-fresh-session-fallback` decision. Actual execution requires an
authorized `--execute`; preparation alone never implies execution authority.

Immediately before an authorized model process starts, the controller creates
an atomic consumption marker in that external review workspace. Reuse in the
same workspace fails closed. It verifies authentication without printing
authentication output, supplies a minimal environment, uses a subprocess argv
array rather than a shell string, captures redacted stderr, and compares the
Git-visible repository state before and after review. A changed state or
changed bound evidence invalidates the run.

## Prepare or run an independent audit pool

Use a pool only when the authorization names every audit subject. The manifest
is strict JSON. Each envelope and optional workspace must be an absolute path;
job IDs must be unique and safe as directory names. Omitting `workspace`
selects the deterministic `<output-root>/<job-id>` path. The fallback decision
is scoped to the named job and defaults to false.

```json
{
  "schema_version": "1.0",
  "jobs": [
    {
      "job_id": "atlas-intake",
      "audit_envelope": "/private/tmp/atlas-intake/audit-envelope.json"
    },
    {
      "job_id": "wingman-ledger",
      "audit_envelope": "/private/tmp/wingman-ledger/audit-envelope.json",
      "workspace": "/private/tmp/crew-chief-ledger-review",
      "allow_fresh_session_fallback": true
    }
  ]
}
```

Preparation creates isolated, non-Git review workspaces and the canonical pool
report without invoking a model:

```text
PYTHONDONTWRITEBYTECODE=1 python -m tools.crew_chief pool \
  /absolute/jobs.json \
  --output-root /private/tmp/crew-chief-pool-<run-id> \
  --max-concurrency 2
```

Execution requires the additional authorization represented by `--execute`:

```text
PYTHONDONTWRITEBYTECODE=1 python -m tools.crew_chief pool \
  /absolute/jobs.json \
  --output-root /private/tmp/crew-chief-pool-<run-id> \
  --max-concurrency 2 \
  --execute
```

Concurrency defaults to two and must be between one and four. Excess jobs wait
in the executor queue. Before any job launches, the pool validates the entire
manifest, every current unexpired envelope, all Git bindings, the external
output root, every workspace, and every workspace overlap. Structural failure
therefore launches zero jobs. Preparation failure also stops the launch phase.

Once launched, jobs are fail-independent: an operationally failed, malformed,
or timed-out job is recorded without cancelling the others. A schema-valid
`FAIL` or `BLOCKED` verdict is a completed audit job, not a runner failure.
Each job is attempted once. There is no retry loop. Every job has separate
frozen inputs, canonical agent copy, schemas, prompt, invocation, output,
diagnostics, run record, and consumption marker. Findings are never
synthesized across jobs, and report entries stay in input order even when
completion order differs.

`pool-report.json` records requested and effective concurrency, maximum
observed concurrency, zero retries, totals, per-job audit and envelope IDs,
execution modes, statuses, verdicts, artifact bindings, categorized errors,
start and completion times, and token counts when the installed CLI reports
them. The CLI exits nonzero for preparation, control, or runner failure. A
valid `FAIL` or `BLOCKED` remains a completed job and does not convert
operational success into runner failure; its findings still require the normal
reconciliation or escalation.

Every executed pool job is a separate authenticated model invocation. Token
use and cost are additive; increasing concurrency reduces waiting time but
does not reduce work or grant more authority. The default of two is the normal
operating balance. Pool evidence proves only the recorded executions. It is
not independent certification, Maverick approval, publication authority, or
mission completion.

## Bound external report retention

Crew Chief stores every audit and pool report as a separate bundle under the
explicit external output root. It does not append reports to a growing JSON
history. Automatic cleanup runs only after a completed audit has both its
canonical report and run record, or after an operationally successful pool has
written all completed job artifacts and its pool report.

The defaults are 30 days and at most 100 completed report bundles. A completed
bundle is eligible when either limit is exceeded. Age comes only from the
validated completion timestamp in `retention-report.json`, never filesystem
modification time. Count cleanup retains the newest completion times and uses
report ID as the deterministic tie-breaker. Queued and running bundles are
never eligible.

Configure either normal or pool execution explicitly when different limits
are required:

```text
PYTHONDONTWRITEBYTECODE=1 python -m tools.crew_chief run \
  /private/tmp/<envelope>/audit-envelope.json \
  --workspace /private/tmp/crew-chief-review-<audit-id> \
  --retention-days 14 \
  --max-retained-reports 50 \
  --execute

PYTHONDONTWRITEBYTECODE=1 python -m tools.crew_chief pool \
  /absolute/jobs.json \
  --output-root /private/tmp/crew-chief-pool-<run-id> \
  --retention-days 30 \
  --max-retained-reports 100 \
  --execute
```

Inspect cleanup without deleting anything:

```text
PYTHONDONTWRITEBYTECODE=1 python -m tools.crew_chief retention \
  /private/tmp/crew-chief-pool-<run-id> \
  --retention-days 30 \
  --max-retained-reports 100 \
  --dry-run
```

Cleanup validates the exact marked output root, every bundle and completion
record, and the complete tree before deleting anything. Symlinks, relative or
ambiguous roots, path escapes, repository-internal roots, duplicate IDs,
malformed metadata, missing completed artifacts, or future timestamps fail
closed. An expired bundle is removed as a unit so its canonical JSON, service
output, stderr, run record, and temporary output do not diverge. The bounded
`retention-state.json` contains only the active limits, retained completed
count, last cleanup time, and number removed by that cleanup; it has no
deletion history.

Ordinary deletion is lifecycle cleanup, not guaranteed secure erasure. Use an
approved storage and media sanitization procedure when secure erasure is a
separate requirement.

## Canonical schema inventory

Crew Chief freezes and validates these versioned contracts from the one
canonical directory `tools/crew_chief/schemas/`:

- `audit-envelope-v1.schema.json`
- `authorization-receipt-v1.schema.json`
- `authorization-receipt-v2.schema.json`
- `bootstrap-report-v1.schema.json`
- `finding-v1.schema.json`
- `pool-manifest-v1.schema.json`
- `pool-report-v1.schema.json`
- `reconciliation-v1.schema.json`
- `report-v1.schema.json`
- `retention-report-v1.schema.json`
- `retention-state-v1.schema.json`

The pool manifest and report schemas govern orchestration only. Every model
result still validates against the canonical per-audit report and finding
contracts; the pool does not replace them with a combined finding schema.

## Findings and reconciliation

The canonical report is JSON conforming to
[`report-v1.schema.json`](../../tools/crew_chief/schemas/report-v1.schema.json).
`PASS` requires no findings. `PASS_WITH_ADVISORIES` permits only non-blocking
`low` or `advisory` findings. Any `critical`, `high`, `medium`, or otherwise
blocking finding requires `FAIL`. Missing controls or evidence requires
`BLOCKED`. File length alone is not a finding.

The report's `audit_scope` must contain every exact `required_focus` value from
the frozen risk profile. Duplicate, malformed, unrecognized, or missing
coverage is invalid; a `deep` report therefore cannot validate with a narrow
scope. An `exempt` report still requires its recorded justification, bound
governance-validation evidence, and all exempt-profile focus values.

Every finding citation is checked against a catalog constructed only after all
frozen bindings verify. Source citations use an exact changed repository path
and exact `base`, `head`, `index`, or `worktree` state. Line ranges are valid
only for frozen regular or executable UTF-8 text and must fit its bound line
count. Artifact citations use exact manifest identifier/reference pairs:
`mission_record`, `engineer_report`, `test_claims`, `diff:<name>`,
`evidence:<number>`, or a frozen `control:*` identifier. Unfrozen paths,
unknown artifacts, binary line citations, and out-of-bounds lines are invalid.

Validate a report and optionally generate a labeled non-canonical Markdown
view outside the repository:

```text
python -m tools.crew_chief validate-report \
  /private/tmp/<envelope>/audit-envelope.json \
  /private/tmp/<review>/output/crew-chief-report.json \
  --markdown-output /private/tmp/<review>/output/crew-chief-report.md
```

Codex must give every finding exactly one disposition: `resolved`,
`disputed_with_evidence`, or `escalated_to_maverick`. Resolution needs
correction evidence and validation results. A dispute needs exact
counter-evidence and reasoning. Escalation needs the unresolved issue, impact,
and decision requested.

```text
python -m tools.crew_chief reconcile \
  /private/tmp/<envelope>/audit-envelope.json \
  /private/tmp/<review>/output/crew-chief-report.json \
  /private/tmp/<review>/output/dispositions.json \
  --output /private/tmp/<review>/output/reconciliation.json \
  --markdown-output /private/tmp/<review>/output/reconciliation.md
```

`reconciliation_complete` means every finding has one valid disposition.
`approval_ready` additionally means every blocking finding is resolved. A
disputed or escalated blocking finding is deliverable to Maverick but is not
approval-ready. Deliver the envelope, canonical report, reconciliation, exact
evidence, remaining risks, and CLI/run record to Goose and Maverick.

## Failure and recovery

Preserve failed, expired, or partially prepared external artifacts for
diagnosis. Do not repair an envelope, reuse a consumed workspace, weaken
controls, or rewrite evidence. Correct the underlying repository or evidence,
rerun validation, and prepare a new envelope and workspace with a new expiry.
Missing Codex, missing authentication, an unsupported required flag, invalid
JSON, process timeout, or detected mutation fails clearly without a success
claim.

An authenticated bootstrap request on 2026-08-09 was rejected by Codex service
schema validation before model generation because the service-facing
`statement` constant lacked an explicit type. No bootstrap report or verdict
was generated, and no Crew Chief acceptance audit ran. Any package whose HEAD
or schema changes after approval is obsolete and requires a newly frozen
package, a new exact byte size and SHA-256, a fresh sensitive-content scan, and
new explicit Maverick transmission approval.

The mutation comparison covers Git-visible files and explicitly bound
evidence. It intentionally does not open ignored secret paths merely to hash
them. Operating-system and Codex read-only sandboxing is therefore the primary
write protection; ignored-path mutation detection is not claimed. Codex
service authentication is inherently required for an authorized live run, but
authentication stores are neither copied into the evidence nor exposed to the
review prompt.

## Role separation and bootstrap

- Crew Chief independently evaluates frozen mission implementation evidence
  and returns advisory findings.
- Goose/Mission Control plans and audits mission evidence for Maverick; it is
  not Crew Chief and cannot transfer Maverick's authority.
- The Development Flightline Independent Auditor verifies a Flightline
  engineering handoff. It is a separate role and must not claim a Crew Chief
  audit.
- Maverick retains final authority over scope, findings policy, commits,
  publication, gates, and mission completion.

Crew Chief may review its initial implementation when the result is labeled
self-review. Independent certification requires a genuinely separate reviewer.
When the ordinary bootstrap path is authorized, it goes to an ordinary Codex
reviewer operating read-only over the implementation commit and frozen
evidence. Its first report statement must be: “This bootstrap audit is not a
Crew Chief audit.” Do not select the Crew Chief agent for bootstrap.

The canonical bootstrap contract is
[`bootstrap-report-v1.schema.json`](../../tools/crew_chief/schemas/bootstrap-report-v1.schema.json).
Bind its audit ID, envelope ID, and reviewed commit to the exact frozen subject,
project it with the same service-schema compatibility code, validate the exact
final payload offline, and pass only that checked payload to `--output-schema`.

### Package-bound bootstrap authorization

Build and scan the implementation-review package before asking Maverick to
approve it. Approval of those exact bytes is then recorded in a separate
[`authorization-receipt-v2.schema.json`](../../tools/crew_chief/schemas/authorization-receipt-v2.schema.json)
artifact. Never insert the receipt into the already-approved package or schema.
Receipt creation records Maverick's explicit instruction; it does not create,
infer, authenticate, or transfer authority. The trusted local caller must
supply an explicit `AuthorizationContext` attesting to Maverick's external
decision, the asserted principal identifier, evidence type and reference, the
action-specific explicit-approval classification, the direct-Codex or
Mission-Control execution route, and the Codex executor. The writer validates
these values for internal consistency but does not independently verify their
human origin. No field defaults to Mission Control, and valid version-2 records
can show Mission Control only as dispatcher. Live conversation text is not an
invocation control until its complete UTF-8 content hash is bound in a
validated receipt.

The receipt binds the caller-attested Maverick principal and evidence,
execution route, dispatcher when present, Codex executor, derived
human-readable statement, Canary, subject HEAD, package and service-schema byte
sizes and SHA-256 values, audit and envelope IDs, package expiry, exact
invocation counts, the no-automatic-retry rule, and the complete
authorization-text hash and UTF-8 byte size. For new version-2 receipts, both
values must come from the trusted-boundary `AuthorizationExpectation`; the
validator compares the receipt to those independently supplied values rather
than deriving either expectation from the receipt. Its content-derived receipt
ID, schema, subject, scope, provenance, and expiration must validate before a
model process can start.
Missing, malformed, expired, already consumed, altered, or mismatched receipt
evidence fails closed. The receipt is tamper-evident after the external
decision; it does not independently prove human identity or prevent a false but
internally consistent approval attestation created by a process already
trusted as the same local account. That residual risk requires Maverick's
explicit acceptance or rejection. One receipt records exactly one ordinary
bootstrap invocation and no automatic retry; conditional fixture-audit counts
are recorded but remain gated on a successful bootstrap verdict.

Version-1 receipts remain readable with their exact historical fields and
wording. Never rewrite, normalize, or re-render them as version 2. All newly
created receipts use version 2. Legacy serialized authorization expectations
without a text-size field remain readable only for version-1 validation; a
version-2 receipt requires a positive independently supplied expected size.

Use `tools.crew_chief.bootstrap_authorization` to record a later explicit
approval, prepare a fresh external invocation workspace, and execute only when
that later authorization includes invocation. Preparation copies the exact
package, schema, and receipt into frozen paths, verifies the original bindings
again, detects and binds the resolved Codex executable, and internally
constructs the ordinary-bootstrap command from the canonical isolation
contract. Callers cannot supply an argv. The command enforces ephemeral
execution, ignored user configuration and repository rules, strict
configuration, approval denial, read-only sandboxing, the exact frozen schema
and output paths, the frozen workspace, all required disabled capabilities,
ordinary-reviewer selection without Crew Chief, and the standard-input marker.

Execution re-detects capabilities, revalidates the bound executable, and
recomputes and exactly compares the complete command immediately before
receipt consumption. Any altered executable or omitted, duplicated, added,
meaningfully reordered, or weakened control fails before the runner is called.
Preparation also constructs one immutable composite standard-input payload.
The payload presents the receipt first as a clearly delimited frozen invocation
control and then presents the unchanged approved package. The invocation and
run record bind the absolute source-receipt path, exact size and SHA-256, its
frozen copy, executable contract, and composite payload. An atomic receipt-ID
consumption marker then prevents reuse from another workspace.

A valid receipt supersedes only the older package snapshot's statement that
exact-package approval was still pending when the package was built. It does
not supersede the package's implementation evidence, expand review scope, or
authorize fixture audits, retries, repository changes, publication, or mission
completion. A new or changed package requires a new reported binding, new
Maverick approval, and a new receipt. Do not create a receipt while the future
package size or hash is unknown.

Bootstrap evidence uses a non-self-referential commit policy. The canonical
`implementation_commits` inventory lists code-bearing implementation commits,
including the implementation head. A later evidence-only reconciliation
snapshot is not an omitted implementation commit: its exact final hash cannot
be stored inside itself and is instead bound as the audit envelope's subject
HEAD. Bootstrap instructions and mission metadata must identify both roles so
the ordinary reviewer checks the implementation inventory and the external
evidence-snapshot binding without demanding impossible commit self-reference.

The current CI configuration runs deterministic schema, controller, safety,
reconciliation, and governance tests with fake model-process runners. This
repository change adds no CI model job, credentials, or network access. A
future model-backed CI audit would require its own explicit authorization and
security configuration, and its result would not become automatic authority.
