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
| Repository-owned Crew Chief implementation | Historical mission completed with accepted limitations; repository execution superseded by GOV-006 | Mission records and evidence remain; independent audit is now supplied externally under the repository-neutral closeout contract. |
| Ledger Transition engineering | Completed, independently audited, merged, and published at `51fb750` | The default/live Ledger remains version 3; any physical transition remains separately gated by Assurance v1, DATA-001, an exact package and receipt, fresh independent review, and Maverick authorization. |
| Repository-owned LSO implementation | Historical implementation superseded by GOV-006 | Exact landing remains required and is now supplied externally under the repository-neutral closeout contract. |
| Rangefinder / Wingman Assurance v1 | Established direction; not active | Maverick must select and authorize a mission. |
| Retrieval Scalability | Intended evidence-gated direction | Scope must be selected from Rangefinder evidence. |
| Storage Port | Provisional working sequence | Requires a separate approved brief; no migration is implied. |
| Ledger Concurrency | Provisional working sequence | Follows stable storage interfaces. |
| Ledger Black Box | Provisional working sequence | Follows defined concurrency and accepted-transition semantics. |
| Contrail | Provisional working sequence | Follows durable transition history. |
| Truth Clock | Provisional working sequence | Follows a stable provenance graph. |
| Persistent Cockpit | Provisional working sequence | Follows temporal and supersession meaning. |
| Secure Hangar | Provisional formal trust boundary | Required before sensitive third-party material or governed product expansion. |

The 2026-08-10 Crew Chief and 2026-08-11 LSO records remain truthful historical
mission evidence. On 2026-08-14 GOV-006 removed their repository-owned
execution machinery while preserving mandatory independent audit and exact
landing as external development operations. Development Flightline remains a
separate Engineer isolation/controller capability. Rangefinder and every later
successor remain inactive. Portfolio Wingman/Radar, governed agents, and Chief
of Staff remain future directions.
