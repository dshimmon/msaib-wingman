# Crew Chief v1 Implementation Evidence

The adjacent [`mission.md`](mission.md) is the sole canonical and authoritative
current lifecycle record. This evidence package supports that record and does
not independently approve, publish, operationalize, or complete the mission.

## Authorized subject

- Worktree: `/Users/davidshimmon/.codex/worktrees/a83e/msaib-wingman`
- Branch: `codex/crew-chief-v1-build-20260809`
- Approved base and local `origin/main`:
  `b1910d0c69a52d73ddde93cb9722f12540c5d1e7`
- Authorization: Maverick's 2026-08-09 `CANOPY-7C2F-ATLAS` implementation and
  exactly-one-local-commit prompt.
- Exclusions preserved: no Radar work, no live or paid model audit, no secret
  or live-data access, no push, no merge, and no mission-complete claim.

## Implemented controls

- [Project-scoped agent](../../../../.codex/agents/crew-chief.toml) with model
  inheritance, high reasoning effort, read-only sandboxing, approval denial,
  complete role separation, review categories, verdict rules, and no network,
  credentials, tools that write, or subagents.
- [`tools/crew_chief/`](../../../../tools/crew_chief/) controller with canonical
  JSON hashing, injectable time, exact Git/evidence binding, external-only
  artifacts, path and secret controls, capability detection, atomic workspace
  consumption, mutation checks, stable schemas, and report reconciliation.
- [Canonical runbook](../../../runbooks/crew-chief.md) and
  [GOV-004](../../../decisions/governance/crew-chief-audit.md).
- Credential-free temporary-repository tests and CI integration that never
  invoke `codex exec` or a network client.

## 2026-08-09 bounded enforcement correction

Maverick authorized one bounded correction pass from the clean implementation
commit `82c5952e64eb8fe5638701fef1f9d289b7735d82` and exactly one new local
commit after validation. The correction remains inside Crew Chief's approved
read-only, advisory responsibility.

- Bootstrap finding `CC-0001` — **resolved in the correction candidate,
  pending fresh bootstrap re-audit.** Capability detection now accepts only a
  closed set of enabled feature names, explicitly disables every enabled known
  prohibited feature, and fails before model invocation on unknown enabled
  features, failed inventory, or malformed inventory evidence. `personality`
  is the sole enabled feature permitted to remain because it exposes no tool,
  network, application, or write capability.
- Mission Control concern: complete frozen implementation context — **resolved
  in the correction candidate.** Changed-file base, head, index, and worktree
  states are frozen as applicable into deduplicated content-addressed blobs
  with exact path, revision/state, presence, type, mode, size, encoding, line
  count, digest, and binding metadata. Complete changed head text, necessary
  base/deleted text, and deterministic binary payloads reach the standard-input
  review context under the existing strict 16 MiB encoded limit.
- Mission Control concern: selected risk-profile enforcement — **resolved in
  the correction candidate.** Report validation requires every canonical
  profile focus, rejects missing, duplicate, malformed, and unrecognized
  coverage, prevents narrow deep-profile reports, and preserves exempt
  justification and bound governance-evidence requirements.
- Mission Control concern: finding citation binding — **resolved in the
  correction candidate.** Source citations require an exact frozen path/state
  and in-bounds UTF-8 text lines; artifact citations require an exact verified
  manifest identifier/reference pair. Unfrozen paths, binary line citations,
  unknown artifacts, and invalid ranges fail.

The exact correction files are:

- `.codex/agents/crew-chief.toml`
- `docs/missions/governance/crew-chief/artifacts/implementation-test-claims.json`
- `docs/missions/governance/crew-chief/evidence.md`
- `docs/missions/governance/crew-chief/journal.md`
- `docs/runbooks/crew-chief.md`
- `tests/governance/test_crew_chief.py`
- `tools/crew_chief/controller.py`
- `tools/crew_chief/core.py`
- `tools/crew_chief/git_evidence.py`
- `tools/crew_chief/runner.py`
- `tools/crew_chief/schemas/finding-v1.schema.json`
- `tools/crew_chief/schemas/report-v1.schema.json`
- `tools/crew_chief/validation.py`

The agent definition changed only because the enforced report contract now
requires exact risk-focus declarations and source-state/artifact citations
from the model.

## Final validation

Exact final command results are recorded in
[`artifacts/implementation-test-claims.json`](artifacts/implementation-test-claims.json).
The correction pass recorded 64 focused Crew Chief tests, 92 combined Crew
Chief and repository-governance tests, 140 complete governance tests, and 369
complete credential-free repository tests, all passing with zero failures,
errors, or skips. Ruff passed the changed Python scope; repository governance,
all four Crew Chief JSON Schemas, and Git whitespace validation also passed.
One earlier focused development run had one failure and one error in new test
harness code; both assertions were corrected and the exact focused command was
rerun successfully. Exact commands, durations, results, and the disposition of
that development run are preserved in the adjacent claims artifact.

The original implementation build recorded `codex-cli 0.147.0-alpha.6.5`.
That probe supported ephemeral execution, ignored user config and rules,
strict configuration, structured output, explicit read-only sandboxing,
stable shell-tool disabling, and configuration-based approval denial. It did
not expose a supported
non-interactive custom-agent selector, so automation records and requires the
fresh-session fallback. No supported local custom-agent introspection command
was exposed; TOML parsing, current-schema governance checks, and official
documentation validate the project agent until later interactive acceptance.
The correction did not invoke the installed CLI or perform a live capability
probe. A new or unfamiliar enabled CLI feature intentionally blocks controlled
preparation until its safety is explicitly classified and tested.

## Independence and remaining gates

No Crew Chief or other live model review occurred during implementation or the
correction. The local candidate has only deterministic self-tests and Codex
self-review; the correction is not independently re-audited. Binary source is
frozen and base64-presented but intentionally cannot receive line citations;
the complete encoded payload remains capped at 16 MiB; and ignored-path
mutation detection retains the runbook's documented limitation. After the one
authorized local correction commit, Goose must independently verify the
evidence and perform a fresh bootstrap re-audit. Actual Crew Chief selection
and execution remain a later separately authorized controlled acceptance gate.

The implementation is not published, not operational, and not
mission-complete. Nothing in this evidence grants push, merge, or lifecycle
approval authority.

## 2026-08-09 acceptance-readiness closeout candidate

Maverick's bounded closeout authorization reconciles the original
implementation commit `82c5952e64eb8fe5638701fef1f9d289b7735d82` and bounded
correction commit `3e4edff5cc5e9b9810827331ca1024fd14c8f875` into the
canonical active mission. It authorizes readiness correction, a fresh
ordinary-Codex bootstrap review, exactly two controlled Crew Chief fixture
acceptance runs, up to two ordinary bootstrap attempts, and no more than six
new local commits. It does not authorize push, merge, publication, operational
status, or mission completion.

The live non-model probe found `codex-cli 0.147.0-alpha.6.5` with 38 enabled
features. The readiness correction explicitly classifies and disables all 38;
no feature is permitted to remain enabled. Capability validation now also
requires every command-line control actually used by the prepared argv,
rejects duplicate inventory rows, and rejects tampered prepared capabilities
before authentication or process invocation. The exact classifications and
effective controls are recorded in the runbook and adjacent test-claims JSON.
An installed-CLI integration test successfully prepared the external
read-only command and verified that no report or model run was produced.

The readiness validation passed 67 focused Crew Chief tests in 50.461 seconds,
95 combined Crew Chief and repository-governance tests in 54.405 seconds, 143
complete governance tests in 62.079 seconds, and 372 complete credential-free
repository tests in 67.775 seconds, with no failures, errors, or skips. Ruff,
repository governance, all four Crew Chief Schemas, and Git whitespace checks
also passed. Expected negative-path Flightline and Atlas diagnostics and bare
Streamlit warnings appeared during the green complete suite. The exact commands
and results are in
[`artifacts/implementation-test-claims.json`](artifacts/implementation-test-claims.json).

No model process ran during this readiness implementation. The exact local
readiness commit is `1cddd1d65156d69053b30564c00343b3843cbe66`. The next gate
is a fresh, isolated ordinary Codex bootstrap review. Controlled Crew Chief
fixture acceptance remains contingent on a successful bootstrap.

## 2026-08-09 service-schema compatibility correction

The first authenticated closeout bootstrap request reached the Codex service,
but service schema validation rejected the output schema before model
generation because the `statement` constant had no explicit `type`. The
request produced no report and no verdict. Zero bootstrap reviews and zero
controlled Crew Chief acceptance audits completed. This was a service
rejection, not an ordinary bootstrap review and not a Crew Chief audit.

Maverick then authorized one bounded local compatibility correction and one
local commit. The correction adds a canonical bootstrap report schema and a
shared deterministic projection/preflight used for both the exact bootstrap
payload and the exact bundled Crew Chief report payload. The projection types
every constant and enum, makes all service-facing objects strict with all
properties required, converts canonical optionals to nullable service fields,
uses supported nested `anyOf` alternatives, retains checked local references,
and omits unsupported generation-only constraints. Raw service output is
validated against that exact payload, deterministically normalized, and then
validated without exception against the complete canonical Crew Chief
contract and policy checks.

Credential-free regression coverage includes the original untyped
`statement` failure; string and boolean constants; typed property and array
item enums; strict nested objects; embedded findings; nullable optional fields;
source/artifact alternatives; canonical duplicate-scope and duplicate-finding
rejection; PASS, blocking, and nonblocking reports; final-payload binding; and
proof that compatibility failure prevents the process runner from being
called. No model or network request is used by these tests.

The final compatibility matrix validated all five canonical Crew Chief JSON
Schemas and both exact service-schema forms. It passed 74 focused Crew Chief
tests in 52.659 seconds, 102 combined Crew Chief/repository-governance tests in
58.615 seconds, 150 governance tests in 66.615 seconds, and 379 complete
repository tests in 73.161 seconds, with zero failures, errors, or skips in the
final runs. Expected negative-path Flightline and Atlas diagnostics and bare
Streamlit warnings appeared during the green broader suites. An initial
canonical-schema reporting one-liner had a shell-quoting `SyntaxError` before
validation and was corrected. The first combined run then exposed one stale
mission-state assertion; it was reconciled to the authorized new state, and
the exact command passed on rerun. Exact commands and both development-run
dispositions are preserved in the adjacent claims artifact.

The previous 767,450-byte package with SHA-256
`21acb4c941a200ff20d7c2d7a1037e7ce007a8d307e73cc581fcc799adb71d51`
and the consent tied to it are obsolete when this correction changes HEAD.
Closeout remains incomplete. A new package must be frozen from the clean
correction commit, verified, scanned for sensitive and unrelated content, and
reported with a new exact byte size and SHA-256 before Maverick can consider a
new transmission approval. No independent audit of this correction is
claimed.

## 2026-08-10 completed blocked bootstrap review

Maverick explicitly authorized one transmission of the 864,455-byte package
with SHA-256
`b34e22658096b48def0c576736b71d53f1a35af5de402d476c501ea51a00b3ea`
and the 1,631-byte service schema with SHA-256
`391637a4a121577b3f29805acdae0be68235f7b26980f45d14f4d27181129847`.
One fresh ordinary Codex bootstrap invocation was attempted and completed. It
returned schema-valid `BLOCKED`, with `BOOTSTRAP-001` and `BOOTSTRAP-002`, and
used 219,467 tokens. Its required identity statement was “This bootstrap audit
is not a Crew Chief audit.” It did not select Crew Chief, perform acceptance,
or certify the implementation.

The blocking verdict stopped the conditional acceptance sequence. Zero seeded
fixture audits and zero corrected-fixture re-audits were attempted. Git-visible
state hashes before and after the review were identical; the index and worktree
remained clean; there was no repository mutation, push, merge, publication, or
mission-completion declaration.

Durable review evidence is preserved under
[`artifacts/bootstrap-blocked-20260810/`](artifacts/bootstrap-blocked-20260810/):

- `bootstrap-report.json` preserves the complete structured JSON report in
  canonical newline-terminated repository form. The raw service artifact was
  4,563 bytes with SHA-256
  `b962b094acc8e03f68d309928332dbb64a8f06b2c6f0f05df050f1a6fc99f204`;
  the canonical repository form is 4,564 bytes with SHA-256
  `009e4165e9d89ee37a214271a01bc0a95c702a148d1787d25abd2a802eafde21`.
- `bootstrap-run-record.json` is the exact 3,297-byte run record with SHA-256
  `d631ec0c18fb04f65f8aa0f3d24e8378a4e646d3d525c2fb473edc3e8d070703`.
- `bootstrap-invocation.json` is the exact 4,250-byte prepared invocation with
  SHA-256
  `5eda5d04ded33a2536c507e6ed075df2fb369497bc1e130b26bdb0698a1a4b9a`.
- `bootstrap-cli-stdout.log` is the exact 4,564-byte stdout with SHA-256
  `009e4165e9d89ee37a214271a01bc0a95c702a148d1787d25abd2a802eafde21`.
- The large raw stderr is not committed. Its external review location is
  `/private/tmp/wingman-crew-chief-bootstrap-schema-20260809-3huM5F/review/output/bootstrap-cli-stderr.log`;
  it is 869,518 bytes with SHA-256
  `44b5031650cb35ffb3e4b5a705acc9e847862b2cbb5227bd8baad8b8a56909ee`.

## 2026-08-10 bootstrap-governance correction and dispositions

`BOOTSTRAP-001` exposed a circular evidence rule: inserting a later approval
into an already-built package would change the approved bytes. Maverick
authorized a separate receipt control, implemented at
`f34c7ad810a50b36be453493d17fee8ac4c3ea00`. The versioned receipt schema and
deterministic code bind Maverick identity, the complete authorization-text
hash, Canary, exact HEAD, package and schema bindings, audit and envelope IDs,
expiry, exact invocation counts, and the no-retry rule. Preparation preserves
the approved source bytes and visibly presents the validated receipt as a
separate frozen control in one immutable composite. Missing, malformed,
expired, altered, unauthorized, mismatched, or already consumed receipts fail
before the injected process runner wherever deterministically detectable.
This disposition is resolved in implementation and awaits fresh independent
bootstrap verification. No receipt was created for the next unknown package.

`BOOTSTRAP-002` is resolved in this evidence snapshot by adding both the
previously omitted compatibility implementation
`2a868bac1088bd6523048623032af6d277143858` and receipt-control implementation
`f34c7ad810a50b36be453493d17fee8ac4c3ea00` to the canonical
`implementation_commits` inventory. The machine-readable
[`reconciliation.json`](artifacts/bootstrap-blocked-20260810/reconciliation.json)
distinguishes that implementation head from this evidence-only reconciliation
snapshot. This snapshot is not implementation and is not falsely omitted from
the implementation inventory. Its final Git hash cannot be stored inside
itself; the next frozen audit envelope must bind it externally as
`subject.head`. This disposition also awaits fresh independent bootstrap
verification.

The receipt-correction validation loaded six canonical schemas and both exact
service projections; passed 82 focused Crew Chief tests in 59.814 seconds, 110
combined Crew Chief/repository-governance tests in 64.327 seconds, 158 complete
governance tests in 69.966 seconds, and 387 complete repository tests in 75.346
seconds, all with zero failures, errors, or skips. Ruff and repository
governance passed. Expected negative-path Flightline and Atlas diagnostics and
bare Streamlit warnings appeared during the green broader suites. No real
model or network service was invoked by correction tests.

These dispositions do not retroactively convert the `BLOCKED` report to a
passing verdict. A new package and a later package-bound receipt require new
Maverick approval. Crew Chief remains unaccepted, uncertified, unpublished,
non-operational, and not mission-complete.

## 2026-08-10 failed bootstrap review and bounded finding correction

The later compacted-package ordinary bootstrap review completed over reviewed
HEAD `e88f25579e2c976c50e3abf49118abadb118f5b9` and returned `FAIL` with
blocking findings `BOOTSTRAP-003` and `BOOTSTRAP-004`. The exact structured
report was 5,891 bytes with SHA-256
`c5a330475b0a698218fd81143c99444eba3fbf36a15a67acac753f024007b7bf`.
It reported 256,383 tokens, zero advisories, and no Crew Chief fixture audit.
The original report, validation, citation validation, invocation, run record,
stdout, and stderr bindings remain unchanged in external evidence and are
recorded in
[`artifacts/bootstrap-failed-20260810/disposition.json`](artifacts/bootstrap-failed-20260810/disposition.json).

Maverick authorized one bounded correction. `BOOTSTRAP-004` is resolved in the
correction candidate by eliminating caller-supplied bootstrap argv. The
bootstrap wrapper now detects and binds the approved executable, constructs
the ordinary-review command through the canonical isolation builder, and
records its exact contract. Immediately before receipt consumption and process
launch, it re-detects capabilities, verifies the executable bytes, reconstructs
the command, and requires exact equality. Tests reject every one-token omission
and altered executable, duplicate, added, meaningfully reordered, weakened
approval, sandbox, schema, output, workspace, color, disabled-capability, or
standard-input control. They also reject command-hash, capability-record, and
executable-file tampering before receipt consumption or runner invocation.

`BOOTSTRAP-003` is disputed with evidence rather than hidden or falsely marked
fixed. Crew Chief v1 deliberately trusts Maverick's authenticated Mission
Control interaction and the local operating-system account as the external
authorization boundary. The receipt is a tamper-evident, package-bound record
created after that external decision; it does not independently prove human
identity and cannot reject a forged matching receipt created by a malicious
process already operating inside the trusted local account. That same-account
impersonation risk is explicitly escalated to Maverick for acceptance or
rejection. No signing keys, Keychain integration, cryptographic identity, or
remote identity service was introduced.

Final code-path validation passed 13 focused bootstrap-authorization tests in
2.742 seconds, 87 complete Crew Chief tests in 51.508 seconds, 115 combined
Crew Chief/repository-governance tests in 56.397 seconds, 163 governance tests
in 61.714 seconds, and 392 complete repository tests in 68.689 seconds. Six
canonical JSON Schemas and both exact service-schema forms passed. Expected
negative-path diagnostics appeared in the green broader suites. Two setup
attempts are also preserved honestly: governance discovery first lacked its
offline dummy key (one import error), and repository discovery first lacked
the repository top-level flag (26 collection errors); the corrected commands
then passed. Exact commands and dispositions are in
[`correction-validation.json`](artifacts/bootstrap-failed-20260810/correction-validation.json).

Both the changed-file Ruff scope and the established Crew Chief/governance
Ruff scope passed. A repository-wide Ruff probe also surfaced 77 existing
findings only in unchanged, out-of-scope Atlas, Wingman, Flightline, and legacy
test files. Those unrelated baseline findings are preserved in the validation
record and were not modified under this bounded authorization. Repository
governance validation passed.

No receipt was created, no model or network service was invoked, no fixture
audit ran, and the original `FAIL` verdict remains unchanged. The correction
and evidence require one finding-focused independent re-audit before any
acceptance sequence can resume.

## 2026-08-10 Maverick closeout with accepted limitations

Maverick ended the correction and audit cycle and accepted Crew Chief v1 at
implementation commit `6658076e8c9440665245793621edf1e309bedfdf` without
claiming independent certification or successful acceptance audits. Maverick
explicitly accepted both the same-account impersonation risk documented for
`BOOTSTRAP-003` and the frozen-workspace launcher limitation exposed by
`FOCUSED-RUN-001`.

The focused ordinary-Codex re-audit was attempted once with zero automatic
retries. The local Codex preflight exited with return code 1 before a model
service request began because the frozen workspace was not a trusted Git
directory and the canonical command omitted `--skip-git-repo-check`. The
authorization receipt was consumed, no structured report was produced, and
model token consumption was zero. Neither the seeded-defect fixture nor the
corrected-fixture audit ran.

The exact failure evidence is preserved under
[`artifacts/focused-run-failed-20260810/`](artifacts/focused-run-failed-20260810/):

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `focused-failure-evidence.json` | 4,539 | `b3878267f6a99f5b1d253bc0a0c841985a1241723d2b90bf0915d877e3114dbc` |
| `authorization-receipt.json` | 1,000 | `da71546abd5a67d57a8bf1028f245d9ba532ccb3f205c0af6c9126e2a4a1217c` |
| `invocation.json` | 5,963 | `1ffbf8115bc754e00d639ffee3cdea3d8b6bb06ea5a8298a570fa82c52b68cd7` |
| `run-record.json` | 3,075 | `27ff74b22d2923a2a4f6ff21ec51870a3f6ef2037ad8afbe1a36e6a5c73b63c4` |
| `codex-stderr.log` | 76 | `dd701e712037bba81445e9a92376e3d3af69acac5f0187ec904e9ed3c401324d` |
| `provenance.json` | 3,057 | `cad4b86aaf1443d3d27965e3daa1047ecb73f21cc7e4e15f3eaf0cf8e02d43ac` |

The exact copied sources produced zero credential/secret scan matches. No
unrelated content was detected and no redaction was made. Absolute temporary
paths remain only inside exact historical artifacts and the provenance record;
they are not claims that those paths remain stable or available.

| Lifecycle distinction | Final recorded state |
|---|---|
| Implemented | Yes, at `6658076e8c9440665245793621edf1e309bedfdf` |
| Deterministic tests | Passed as previously recorded and revalidated during this closeout |
| Ordinary full bootstrap audit | Completed with `FAIL` |
| Focused re-audit | Not completed because of `FOCUSED-RUN-001` |
| Fixture acceptance audits | Not completed |
| Independently acceptance-certified | No |
| Maverick-approved with known limitations | Yes |
| Locally committed implementation | Yes |
| Mission complete by Maverick decision | Yes |
| Operational limitation | Frozen external review workspaces require an unresolved trusted-directory accommodation |

Bootstrap and focused-run history remains historical evidence, and bootstrap
tooling remains available without being a mandatory closeout gate. Crew Chief
is not described as fully acceptance-tested, independently certified, or
proven operational. Rangefinder and every successor remain inactive. The next
gate is Maverick's selection and authorization of a mission.

### Closeout validation

- `PYTHONPATH=src .../flightline-py312/bin/python -m tools.governance generate`
  regenerated the derived views successfully.
- `PYTHONPATH=src .../flightline-py312/bin/python -m unittest
  tests.governance.test_repository_governance` passed 32 tests in 4.608
  seconds after generation.
- `PYTHONPATH=src .../flightline-py312/bin/python -m unittest -q
  tests.governance.test_crew_chief` passed 87 tests in 57.198 seconds.
- The combined Crew Chief and repository-governance command passed 119 tests
  in 63.182 seconds.
- Governance discovery passed 167 tests in 69.322 seconds. Its
  `operator_cancelled` and `time_budget_exceeded` Flightline messages were
  expected negative-path evidence.
- Complete repository discovery passed 396 tests in 76.090 seconds. Expected
  diagnostic-failure fixtures, Flightline negative paths, and bare Streamlit
  warnings appeared without failures.
- Repository governance validation passed. All 11 repository JSON Schemas and
  all six preserved focused-run JSON records parsed or validated successfully.
- `/opt/anaconda3/bin/ruff check tools/governance/repository.py
  tests/governance/test_repository_governance.py` passed, and `git diff
  --check` reported no errors.

The first test attempt used the system Python 3.9 interpreter and stopped at
import because `tomllib` is unavailable there; no test body ran. The first
repository-governance run under Python 3.12 then reported only the three
expected stale generated views. Generation and the exact rerun passed.

## 2026-08-10 operational launcher and pool implementation evidence

Maverick authorized one bounded operational maintenance pass after Crew Chief
had already been merged to `origin/main` at repository base
`509506cddffba93b496a7d74f930fa04293f9fba`. The implementation used the clean
isolated branch `codex/crew-chief-operational-pool-20260810`; it did not touch
the protected original checkout or its ten unrelated tracked modifications.

The shared isolation command now requires `--skip-git-repo-check` immediately
after `codex exec`. That is the intended accommodation for frozen external
review workspaces, which are evidence directories rather than Git checkouts.
It does not weaken `--ephemeral`, ignored user configuration and rules, strict
configuration, approval denial, read-only sandboxing, exact schema/output/
workspace paths, explicit disabled capabilities, project-agent selection when
available, or the standard-input marker. Exact help-token detection rejects a
lookalike. Negative tests remove, duplicate, add, reorder, weaken, or replace
canonical command and executable controls and verify that the model-process
runner is never called.

The new standard-library concurrent orchestrator accepts a strict absolute-
path manifest and produces one immutable review workspace and evidence tree per
job. It prevalidates all jobs, current unexpired envelopes, Git bindings,
external paths, and workspace overlap before launch. Concurrency defaults to
two and is constrained to one through four. Additional work remains queued;
each worker is attempted once; one failure does not cancel another; report
records remain in manifest order. The canonical pool report binds the
manifest, invocations, reports, and run records and records execution modes,
statuses, verdicts, errors, timestamps, token counts when available, requested
and observed concurrency, totals, and zero retries. It never synthesizes
findings across subjects.

Deterministic validation evidence:

- `env PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src python -m
  unittest -q tests.governance.test_crew_chief
  tests.governance.test_crew_chief_pool
  tests.governance.test_repository_governance` passed 132 tests: 91 Crew Chief,
  nine pool, and 32 repository-governance tests.
- `env PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src python -m
  unittest discover -s tests/governance -p 'test_*.py'` passed 180 tests in
  134.660 seconds.
- The first full-repository command omitted unittest's required `-t .` and
  ended with 26 collection import errors before the affected module bodies
  ran. The corrected `env PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
  PYTHONPATH=src python -m unittest discover -s tests -t . -p 'test_*.py'`
  passed all 409 tests in 141.767 seconds.
- `python -m tools.governance generate` regenerated derived views, and
  `python -m tools.governance validate` passed.
- Canonical loading validated eight Crew Chief Schemas:
  `audit-envelope-v1`, `authorization-receipt-v1`, `bootstrap-report-v1`,
  `finding-v1`, `pool-manifest-v1`, `pool-report-v1`, `reconciliation-v1`, and
  `report-v1`.
- Ruff passed the complete changed Python scope. `git diff --check` passed.

Every deterministic model path used injected fake process runners. No model,
network service, or live pool was invoked. A successful implementation commit
does not yet prove operation, acceptance, or independent certification. The
only remaining authorized execution gate is one tiny synthetic single-job
smoke audit against the committed implementation, with zero retry.

## 2026-08-10 failed smoke and retention-correction evidence

The one authorized single-job smoke ran against implementation commit
`03984e04f2f6f45ce7316071a0c95ce3d880f2e9` using only a tiny synthetic
calculator repository, frozen Crew Chief controls, and required schemas. It
made exactly one authenticated invocation with zero retry. The generated
schema-shaped payload contained the required `FAIL`, high-severity blocking
finding `CC-0001`, exact source citation to the seeded subtraction defect, and
the frozen synthetic validation artifact. The subprocess then exited with
status 1 because its exact `--output-last-message` parent directory was absent:

```text
Failed to write last message file ".../review/output/crew-chief-report.json":
No such file or directory (os error 2)
```

The CLI reported 26,308 tokens. The consumption marker exists, but no official
report or run record exists and no retry occurred. The exact external evidence
bindings are preserved in
[`failure-evidence.json`](artifacts/operational-smoke-failed-20260810/failure-evidence.json):

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `envelope/audit-envelope.json` | 1,794 | `582a3307274f93c359decef6d74d420a1321eb1fdb35e0d3c0dfdb2702015952` |
| `review/invocation.json` | 4,455 | `4ede389195645d9a43ab7ae1d89e8a8f301c9542e04506ba480b20d3b871ce8f` |
| `review/.crew-chief-consumed.json` | 205 | `0c9b742d536d608e7a9d61fad8fbd27d2c56278ce29cdbf2cbb098bc4f14e375` |
| `review/output/codex-stderr.log` | 49,550 | `036098df016e8ddd3073124cc06686f221f68009cca492f303516789e47c2802` |

Maverick prohibited repeating that smoke and replaced it with the bounded
output-lifecycle and report-retention correction followed by one conditional
two-job concurrent synthetic pool acceptance run.

The correction creates each audit output bundle before process launch and
stores every audit and pool report separately. Completed-bundle retention
defaults to 30 days or 100 reports, whichever threshold is exceeded first.
Operators can set both values on normal and pool commands and can inspect exact
candidates through the deletion-free `retention --dry-run` command. Validated
completion metadata—not file modification time—determines age. Count removal
sorts oldest first by completion time and report ID. Cleanup removes the whole
bundle and replaces a single bounded state record without deletion history.

Queued, running, and currently written reports are ineligible. Cleanup is
confined to a canonically marked absolute external root and rejects Git-
internal roots, symlink components or tree entries, relative or ambiguous
paths, escapes, duplicate IDs, malformed metadata, inconsistent timestamps,
and missing completed artifacts before deleting anything. Normal execution
prunes only after the canonical report and run record succeed; pool execution
prunes only after every job completes operationally and the pool report is
written. Ordinary deletion is explicitly not represented as secure erasure.

The pool report now distinguishes operational `state` from audit `verdict`.
This preserves the acceptance contract: the seeded-defect job can complete
successfully with a valid blocking `FAIL`, the corrected job can complete with
`PASS` or `PASS_WITH_ADVISORIES`, and the pool can report operational success
only when both subprocess, validation, persistence, and aggregation paths
succeed. Preparation, control, runner, schema, or persistence failure remains
an operational pool failure with no retry.

Deterministic correction validation:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=src python -m
  unittest -q tests.governance.test_crew_chief
  tests.governance.test_crew_chief_pool
  tests.governance.test_crew_chief_retention
  tests.governance.test_repository_governance` passed 151 tests in 148.537
  seconds.
- Governance discovery passed 199 tests in 157.396 seconds.
- Complete repository discovery with `-s tests -t .` passed all 428 tests in
  166.865 seconds. Expected Flightline cancellation/time-budget messages,
  Atlas diagnostic-failure fixtures, and bare Streamlit warnings appeared
  without failures.
- Governance generation and validation passed. Canonical loading validated ten
  Crew Chief Schemas, including the new `retention-report-v1` and
  `retention-state-v1` contracts.
- Ruff passed the complete changed Python scope. The preserved failure JSON
  parsed, and working plus staged `git diff --check` passed.

No invocation beyond the failed historical smoke occurred during this
correction. No live pool, retry, commit, push, merge, publication, successor
activation, independent-certification claim, or operational claim occurred.
The user authorized an evidence-only acceptance commit only after a successful
two-job run; explicit authority for the intervening code-bearing correction
commit remains the next required gate.
