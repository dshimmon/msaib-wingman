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
