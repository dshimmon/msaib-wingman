# Wingman Vault

## Governed Capability and Lineage Register

**Version:** 1.0  
**Recovery date:** August 1, 2026  
**Status:** Approved by Maverick on August 1, 2026; committed as `726dbbe981364e3e58a6650d176d0b7edf436286`
**Authority:** Maverick retains final authority over scope, priority, promotion, implementation, approval, and completion.

---

## 1. Purpose

The Wingman Vault preserves approved future capabilities, promoted roadmap
items, deferred architectural obligations, active principles, and completed or
superseded records without confusing one lifecycle state for another.

Preservation is not implementation authorization. Priority does not permit a
capability to skip dependencies, evidence requirements, testing, human review,
or approval gates.

---

## 2. Governing Rules

1. Every preserved entry has a canonical name, definition, lifecycle state,
   priority, and provenance.
2. **Approved** means Maverick approved preservation of the concept. It does
   not mean its architecture, implementation, mission brief, or execution is
   approved.
3. **Required** means the capability is mandatory before the dependent
   workflow may be treated as complete. It does not authorize unbounded work.
4. **High priority** expresses strategic importance. Dependencies and mission
   gates still control sequence.
5. Promotion into a numbered mission requires Maverick's explicit approval of
   that mission's objective, scope, exclusions, constraints, deliverables,
   tests, and acceptance criteria.
6. Active capabilities, promoted roadmap work, deferred obligations, and
   completed infrastructure are recorded separately from future concepts.
7. Superseded entries remain historically visible. They are not silently
   deleted or presented as active commitments.
8. When records conflict, use the authority order defined by Mission Control:
   Maverick's current instruction, canonical repository records, Git and test
   evidence, Project files, conversations, then explicitly labeled inference.
9. No agent may promote, discard, merge, rename, or materially reinterpret a
   Vault entry without preserving provenance and surfacing the change for
   Maverick's approval.

---

## 3. Approved Future Concepts

### 3.1 Knowledge, provenance, and continuity

#### Evidence Graph — Contrail

**Status:** Approved future concept  
**Priority:** Approved; priority not separately assigned

Contrail is the long-term provenance model:

**Source → Evidence → Claim → Inference → Recommendation → Action**

It will preserve source traceback, calculations, agent and workflow
participation, material model or prompt versions, approvals, conflicts,
supersession, and downstream impact. It should answer which claims, reports,
decisions, actions, or missions must be reconsidered when evidence changes.
Ordinary retrieval should not require traversal of the entire graph.

#### Truth Clock

**Status:** Approved future concept  
**Priority:** Approved; priority not separately assigned

Truth Clock will distinguish event time, effective time, publication time,
ingestion time, observation time, supersession time, and expiration time. It
must support both current truth and reconstruction of what Wingman knew or
believed at an earlier time.

#### Persistent Cockpit

**Status:** Approved future concept  
**Priority:** Approved; priority not separately assigned

Persistent Cockpit will preserve conversations, briefings, drafts, product and
workspace context, preferences, active missions, recent activity, agent
workspaces, and the user's return position across sessions and devices.
Conversation may guide interpretation but never replaces fresh retrieval from
authorized sources for factual claims.

#### Ledger Black Box

**Status:** Approved future concept  
**Priority:** Approved; priority not separately assigned

Ledger Black Box will be an immutable event history for ingestions, revisions,
removals, agent actions, approvals, commits, and rollbacks. It supports audit,
replay, recovery, and historical reconstruction while remaining separate from
current-state stores optimized for retrieval.

### 3.2 Governance and agent organization

#### Rules of Engagement

**Status:** Approved future concept  
**Priority:** Approved; priority not separately assigned

Rules of Engagement will define and enforce agent identity, role, objective,
tools, permissions, budgets, evidence requirements, writable scope, prohibited
actions, approval gates, escalation rules, and stopping conditions. Prompts may
explain these rules; system controls must enforce material limits.

#### Chief of Staff

**Status:** Approved future concept  
**Priority:** High priority

The Chief of Staff will be Wingman's orchestrating agent. It receives
Maverick's objective, creates a mission plan, delegates bounded tasks, monitors
status and budgets, preserves provenance across handoffs, and escalates
reserved actions. It does not inherit Maverick's authority.

**Dependency:** Mission Control and Rules of Engagement must exist before the
Chief of Staff becomes operational.

#### Isolated Agent Workspaces

**Status:** Approved future concept  
**Priority:** High priority

Agents will investigate, calculate, draft, test, and prepare proposed changes
in private workspaces without directly mutating shared truth or protected code.
Isolation prevents file collisions but does not eliminate semantic merge risk.
Shared changes must pass through reviewable, controlled commit mechanisms.

### 3.3 Security and information stewardship

#### Secure Hangar

**Status:** Approved future concept  
**Priority:** Approved; priority not separately assigned

Secure Hangar will provide authentication, encryption, product and workspace
isolation, permissions, auditing, backup and recovery, retention, verified
deletion, export, and source-use restrictions. Security requirements must shape
the architecture before sensitive third-party information is accepted.

#### Source Rights Records

**Status:** Approved future concept  
**Priority:** High priority

A Source Rights Record will preserve ownership and permitted use for a source,
including the rights holder, granting authority, allowed and prohibited
purposes, sharing, training restrictions, retention, expiration, and deletion
requirements where applicable.

### 3.4 Storage and concurrency

#### Wingman Storage Port

**Status:** Approved future concept  
**Priority:** Approved; priority not separately assigned

Wingman Storage Port will separate logical data operations from physical
storage. JSON may remain the first adapter; PostgreSQL, vector storage, and
object storage may become later adapters without requiring product logic to be
rewritten around file paths, table names, or cloud providers.

#### Ledger Concurrency Hardening

**Status:** Approved future concept  
**Priority:** Approved; priority not separately assigned

Concurrency hardening will coordinate simultaneous work through isolated
workspaces, version checks, idempotency, conflict handling, queues, retry or
rebase paths, and later transactional database commits.

#### Fine-Grained Locking and Serialized Commits

**Status:** Approved future concept  
**Priority:** Approved; priority not separately assigned

Agents should work independently for most of a task. Wingman will lock only the
affected resources and serialize the brief moments when shared truth changes.
This capability is part of concurrency hardening and must include conflict
detection and safe escalation rather than silent overwrite.

#### Wingman VPS Infrastructure

**Status:** Approved future concept  
**Priority:** High priority

Wingman VPS Infrastructure will provide a persistent remote development and
operations environment beginning with Radar. It may include the repository,
isolated environments, managed persistence, background jobs, secrets, backups,
monitoring, GitHub integration, sandboxed Codex workspaces, and human approval
gates.

**Governing rule:** Persistence does not imply unrestricted autonomy.

### 3.5 Assurance extensions

#### Crew Chief

**Status:** Approved future capability  
**Priority:** High priority  
**Requirement:** Required

Crew Chief is the independent audit agent in the mandatory Codex review loop:

1. Codex completes its bounded work and produces an evidence-based report.
2. The system automatically sends that report and the required review evidence
   to Crew Chief.
3. Crew Chief independently audits scope compliance, architecture, code and
   Codex efficiency, tests, regressions, documentation, dependency effects,
   unrequested changes, and unsupported completion claims.
4. Crew Chief returns its findings to Codex.
5. Codex must resolve each finding, dispute it with evidence, or escalate it;
   Codex may not silently ignore the audit.
6. Codex produces a final reconciliation package containing the original
   report, Crew Chief findings, resolutions or disputes, remaining risks, and
   exact evidence for Goose and Maverick.

The audit handoff is mandatory. Crew Chief begins with advisory findings:
recommendations do not automatically mutate code, expand mission scope,
authorize commits, or overrule Maverick. Maverick may later approve defined
blocking rules through Rules of Engagement or constitutional assurance.

**Sequencing:** Crew Chief remains required, but it is not a prerequisite for
Mission 028. The Development Flightline Independent Auditor may audit Mission
028, but it is not Crew Chief and may not claim that a Crew Chief audit
occurred. Maverick will decide Crew Chief's exact roadmap placement after
Hardpoints and before the relevant Assurance mission. Crew Chief is not
automatically deferred until after Mission 037.

Crew Chief should measure mixed responsibilities, duplication, dependency
complexity, circular imports, repeated navigation, excessive context or tool
output, dead code, compatibility layers, slow or flaky tests, high-churn failure
hotspots, and likely refactor return. Its target is high cohesion, clear
ownership, minimal necessary context, low duplication, and measurable
maintainability. File length alone is not a refactoring rule.

#### Future Constitutional Assurance

**Status:** Approved future concept  
**Priority:** Approved; priority not separately assigned

Wingman may translate ratified principles into bounded assurance checks. Each
check must define the protected principle, observable boundary, false-confidence
risk, failure consequence, authority level, and Maverick-approved
interpretation. Ceremonial language must not be reduced to shallow keyword
checks. The test regime requires separate Maverick approval before becoming
authoritative.

### 3.6 Future products

#### Portfolio Wingman — Radar

**Status:** Approved future product  
**Priority:** Approved for preservation; implementation sequence remains
dependency-bound

Radar is a separate product built on Wingman OS. It must not be confused with
Atlas or coupled prematurely to Core. It will provide public-company discovery,
qualitative research, reproducible financial analysis, and complete sourced,
traceable investor reports with visible agent activity and human oversight.

Radar's planned agent team is:

- **Lead Wingman:** screens a defined universe, ranks candidates, explains why
  they surfaced, assigns deeper analysis, and assembles traceable results.
- **Research Wingman:** performs qualitative and source-focused investment
  research.
- **Financial Analysis Wingman:** performs structured financial analysis using
  reproducible Python calculations.

The stock-discovery layer will support configurable quantitative and
qualitative metrics, preserve exact values, dates, configurations, and data
sources, rank candidates, explain selection, and create structured handoffs.
Recovered screening modes are Quality Growth, Undervalued Compounders, AI
Infrastructure, Turnarounds, Small-Cap Breakouts, and Event-Driven
Opportunities. A reduction to approximately 10–20 candidates is preserved as a
design possibility, not a fixed requirement.

Radar and its agents may research, screen, calculate, rank, model, and
recommend. They may not execute or direct financial transactions without
Maverick's explicit approval.

#### Vector

**Status:** Approved future product  
**Definition:** Career Wingman.

#### Recon

**Status:** Approved future product  
**Definition:** General Research Wingman.

#### Forge

**Status:** Approved future product  
**Definition:** Consulting Wingman.

---

## 4. Active Capabilities and Principles

These entries are active and retain Vault lineage. They are not unimplemented
future concepts.

### Mission Control

**Status:** Created and active  
**Current embodiment:** Goose, serving Maverick in Wingman Mission Control

Mission Control is the project-management and governance layer for mission
planning, dependencies, status, checkpoints, approvals, continuity, audit, and
structured handoffs. The longer-term software control plane may add persistent
queues, agent assignment, pause, cancellation, retry, crash recovery, and
resource budgets. The current Goose role must not be misrepresented as proof
that every future runtime feature already exists.

### Canary System

**Status:** Active Mission Control safeguard  
**Canonical token:** `CANOPY-7C2F-ATLAS`

The Canary verifies identity, operating rules, mission state, and evidentiary
continuity at mission-critical gates.

### Source-Traceability Principle

**Status:** Active governing principle; approved lineage preserved

> Wingman summarizes information, but always preserves a path back to the source.

### Wingman Architecture Philosophy

**Status:** Approved for preservation; formal document remains to be ratified
and integrated

The Architecture Philosophy will capture durable engineering principles for
traceability, product neutrality, explicit boundaries, human authority,
reversible decisions, assurance, storage, concurrency, security, and governed
agents.

### Internal Identifiers and Display Names

**Status:** Active design principle; approved lineage preserved

Stable technical filenames and identifiers must remain separate from friendly
user-facing display names. Friendly metadata improves usability without
replacing durable identity.

---

## 5. Promoted Roadmap Items

Promotion records the destination and preserves Vault lineage. It does not
replace the requirement for a complete, approved mission brief.

| Capability | Destination | State |
|---|---|---|
| Wingman Assurance v1 | Mission 029 — Rangefinder | Planned direction |
| Retrieval Test Range | Mission 029 — Rangefinder | Planned component |
| Flight Recorder | Mission 029 — Rangefinder | Planned component |
| Error Log | Mission 029 — Rangefinder | Planned component |
| Efficiency Analysis | Mission 029 — Rangefinder | Planned component |
| Retrieval Scalability | Mission 030 direction | Exact brief must be selected from Rangefinder evidence |

Rangefinder must establish measurable quality, execution, failure, and
efficiency evidence before major retrieval scaling, storage migration,
persistent agents, or Radar.

---

## 6. Deferred Architectural Obligations

Mission 027 made these obligations canonical. They are mandatory prerequisites
for a future physical Ledger transition, not authorization to perform that
transition:

- exact-target migration authorization;
- cooperative and exclusive application locking;
- concurrent and multiprocess initialization control;
- WAL- and SHM-safe quiescence and backup identity;
- immutable backups and checksums;
- crash-safe restoration that preserves the failed database;
- schema and migration-history readiness;
- semantic and byte-preservation validation;
- disposable dry runs;
- tested rollback procedures;
- Assurance v1 and Crew Chief prerequisites; and
- a separate Maverick approval gate for live execution.

Additional deferred Airframe obligations:

- retire compatibility facades only after replacement contracts and callers are
  proven.

The final package-boundary obligation was fulfilled without a physical Ledger
transition by the active
[`governance/repository-architecture`](docs/missions/governance/repository-architecture/mission.md)
mission at implementation commit `b2a6177`. The compatibility-facade retirement
obligation remains deferred.

Until these prerequisites and approvals are satisfied, the live Ledger may not
be migrated beyond schema version 3.

---

## 7. Mission and Archive Boundary

The Vault is not an archive and does not own completed mission status.
Completed histories, commit evidence, and legacy aliases live in the
[authoritative mission index](docs/missions/README.md). Superseded planning
documents live under `docs/archive/` and remain noncanonical. The retained
historical journals have one compact
[archive index](docs/archive/mission-history/README.md).

Hardpoints fulfilled its promoted product-contract destination. Its outcome is
recorded in [`wingman-os/hardpoints`](docs/missions/wingman-os/hardpoints/mission.md)
rather than duplicated here. Future Product Contract changes still require a
separately approved mission.

---

## 8. Recovery Provenance and Decision Record

### Sources

1. Maverick's explicit approvals and classifications on August 1, 2026.
2. Canonical `Mission-027-Wingman-Defines-the-Boundary.md` supplied for this
   recovery.
3. Eight July 30–31 draft documents in
   `Wingman_Project_Context_Drafts.zip`, used as recovery evidence rather than
   independent proof of approval.
4. Transferred Project conversations and preserved Wingman Mission Control
   context.

### Maverick's August 1, 2026 Decisions

- Accepted every entry recovered under Confirmed Preservation.
- Approved Contrail, Truth Clock, Persistent Cockpit, Ledger Black Box, Rules
  of Engagement, Secure Hangar, Wingman Storage Port, Ledger concurrency
  hardening, fine-grained locking and serialized commits, future
  constitutional assurance, Vector, Recon, and Forge.
- Classified Mission Control as created.
- Approved and marked high priority: Chief of Staff, isolated agent workspaces,
  Source Rights Records, Wingman VPS Infrastructure, and Crew Chief.
- Marked Crew Chief **required**.
- Approved separation of future concepts, active capabilities, promoted
  roadmap items, deferred architectural obligations, and completed or
  superseded records.
- Clarified that Crew Chief exists to receive Codex's report automatically,
  audit it independently, and return its findings to Codex before the final
  evidence package proceeds.

### Recovery Integrity Note

No recovered candidate in this document remains silently tentative. No
approved concept has been promoted to implementation authorization. No active,
completed, deferred, or superseded item has been flattened into an ordinary
future-ideas list.

---

## 9. Boundary and Authority

Maverick approved the Vault on August 1, 2026, and it was committed as
`726dbbe981364e3e58a6650d176d0b7edf436286`. Root `AGENTS.md` was subsequently
committed as `7518bf717ce9974dcbb9d24fefe6a1b91bfee7b3`.

This document owns approved future capabilities, strategic ideas, and deferred
obligations. It does not own the current mission or next execution gate. Use
[`CURRENT_MISSION.md`](CURRENT_MISSION.md) for the generated entry point and
[`docs/roadmap.md`](docs/roadmap.md) for approved sequence. Crew Chief remains
required and unimplemented; no independent Crew Chief audit has occurred.
