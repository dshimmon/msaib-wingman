# Wingman Roadmap

This roadmap summarizes approved sequencing evidence. The actual scope of its
entries and linked approvals controls;
[GOV-002](decisions/governance/roadmap-sequencing.md) is the official
sequencing decision, and `WINGMAN_VAULT.md` preserves capability lineage and
deferred obligations.

| Direction | State | Dependency or gate |
|---|---|---|
| Hardpoints / Product Contract v1 | Completed at `2b3b9a6` | Later contract changes require a separate mission. |
| Repository Architecture | Completed and published at `cff8222f` | Later changes require a separately approved mission. |
| Crew Chief Independent Audit | Completed by Maverick with accepted limitations; locally committed | Deterministic tests passed; full bootstrap failed; focused re-audit and fixtures did not complete; no independent certification. |
| Rangefinder / Wingman Assurance v1 | Established direction; not active | Maverick must select and authorize a mission. |
| Retrieval Scalability | Intended evidence-gated direction | Scope must be selected from Rangefinder evidence. |
| Storage Port | Provisional working sequence | Requires a separate approved brief; no migration is implied. |
| Ledger Concurrency | Provisional working sequence | Follows stable storage interfaces. |
| Ledger Black Box | Provisional working sequence | Follows defined concurrency and accepted-transition semantics. |
| Contrail | Provisional working sequence | Follows durable transition history. |
| Truth Clock | Provisional working sequence | Follows a stable provenance graph. |
| Persistent Cockpit | Provisional working sequence | Follows temporal and supersession meaning. |
| Secure Hangar | Provisional formal trust boundary | Required before sensitive third-party material or governed product expansion. |

Crew Chief is not the Development Flightline Independent Auditor. On
2026-08-10 Maverick completed the mission while accepting the documented
same-account authorization risk and frozen-workspace launcher limitation. The
repository is now between missions; Rangefinder and every successor remain
inactive. Portfolio Wingman/Radar, governed agents, and Chief of Staff remain
future directions. Current lifecycle authority is
[`governance/crew-chief/mission.md`](missions/governance/crew-chief/mission.md).
