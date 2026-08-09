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

## When Crew Chief is required

Use Crew Chief at the governed audit handoff for an implemented mission before
its next approval gate, unless Maverick approved and recorded the `exempt`
profile. Preparing an envelope is not an audit. Preparing a command is not an
audit. A valid report exists only after an explicitly authorized fresh review
returns schema-valid JSON bound to the exact envelope.

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
configuration, ignored repository rules, exact output capture, and explicit
feature-disable controls. It refuses automated execution if any required
control or the supported shell-tool disable feature is absent. Failed,
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
`--allow-fresh-session-fallback` decision. Actual execution requires a
separately authorized `--execute`; do not add it during preparation or CI.

Immediately before an authorized model process starts, the controller creates
an atomic consumption marker in that external review workspace. Reuse in the
same workspace fails closed. It verifies authentication without printing
authentication output, supplies a minimal environment, uses a subprocess argv
array rather than a shell string, captures redacted stderr, and compares the
Git-visible repository state before and after review. A changed state or
changed bound evidence invalidates the run.

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

Crew Chief cannot certify its initial implementation. The bootstrap handoff
must go to a fresh ordinary Codex reviewer that did not participate in the
build, operating read-only over the implementation commit and frozen evidence.
Its first report statement must be: “This bootstrap audit is not a Crew Chief
audit.” Do not select the Crew Chief agent for bootstrap. A controlled real
Crew Chief acceptance run is later and separately authorized.

CI runs only deterministic schema, controller, safety, reconciliation, and
governance tests with fake model-process runners. It never supplies
`--execute`, contacts a model, or incurs a paid audit. This prevents CI from
silently crossing the governed handoff or treating a model result as an
automatic authority.
