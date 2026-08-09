# Wingman Roadmap

This roadmap contains only approved sequencing evidence. It does not authorize
implementation. [GOV-002](decisions/governance/roadmap-sequencing.md) is the
official decision; `WINGMAN_VAULT.md` preserves capability lineage and deferred
obligations.

| Direction | State | Dependency or gate |
|---|---|---|
| Hardpoints / Product Contract v1 | Completed at `2b3b9a6` | Later contract changes require a separate mission. |
| Repository Architecture | Completed and published at `cff8222f` | Later changes require a separately approved mission. |
| Crew Chief Independent Audit | Active portfolio-primary; implementation candidate locally committed | Fresh ordinary-Codex bootstrap audit, then separately authorized controlled Crew Chief acceptance; not operational or mission-complete. |
| Rangefinder / Wingman Assurance v1 | Established direction; no active brief | Maverick must approve the complete mission brief after Crew Chief's bootstrap and acceptance gates. |
| Retrieval Scalability | Intended evidence-gated direction | Scope must be selected from Rangefinder evidence. |
| Storage Port | Provisional working sequence | Requires a separate approved brief; no migration is implied. |
| Ledger Concurrency | Provisional working sequence | Follows stable storage interfaces. |
| Ledger Black Box | Provisional working sequence | Follows defined concurrency and accepted-transition semantics. |
| Contrail | Provisional working sequence | Follows durable transition history. |
| Truth Clock | Provisional working sequence | Follows a stable provenance graph. |
| Persistent Cockpit | Provisional working sequence | Follows temporal and supersession meaning. |
| Secure Hangar | Provisional formal trust boundary | Required before sensitive third-party material or governed product expansion. |

Crew Chief is required but is not the Development Flightline Independent
Auditor. On 2026-08-08 Maverick promoted it as the successor portfolio-primary
mission after Repository Architecture and before the relevant Assurance
mission. On 2026-08-09 Maverick authorized the v1 implementation and one local
commit. The candidate remains unpublished, non-operational, and awaiting its
independent bootstrap audit. Radar, governed agents, and Chief of Staff are not
numbered or authorized by this roadmap. Current lifecycle authority remains
[`governance/crew-chief/mission.md`](missions/governance/crew-chief/mission.md).
