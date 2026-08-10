# GOV-002 — Approved Roadmap Sequencing

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "GOV-002",
  "title": "Approved Roadmap Sequencing",
  "namespaces": ["governance", "wingman-os", "radar"],
  "status": "accepted",
  "date": "2026-08-01",
  "authority": "Maverick",
  "scope": "Dependency order after Hardpoints and Crew Chief successor promotion",
  "approval_evidence": "Decision A in the archived pre-Mission-028 planning package; Maverick's 2026-08-08 approval of Crew Chief as the successor portfolio-primary planning mission",
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

The governing sequence is: separate, measure, scale, secure, govern, expand.
Hardpoints is completed. Rangefinder is the next established mission direction,
but it remains draft until a complete brief is approved. Retrieval Scalability
is the intended evidence-gated direction after Rangefinder. Missions 031–037
remain an approved provisional working sequence, not implementation authority.

Storage abstraction precedes physical migration. Assurance, continuity,
concurrency, and security precede governed in-product agents. Mission Control
and Rules of Engagement precede a future Chief of Staff. Portfolio
Wingman/Radar remains a separate future product attached through the product
contract. Crew Chief is not the Flightline Auditor and is not automatically
deferred until after Mission 037; Maverick will decide its exact placement
before the relevant Assurance mission.

## 2026-08-08 amendment — Crew Chief promotion

Maverick completed `governance/repository-architecture` and promoted
`governance/crew-chief` as the successor portfolio-primary planning mission,
after Repository Architecture and before the relevant Assurance mission. The
promotion approves planning only. Crew Chief implementation requires a
separate build prompt, and no Crew Chief operational capability or audit is
claimed by this amendment.

## 2026-08-09 amendment — Crew Chief implementation candidate

Maverick separately authorized Crew Chief v1 implementation, credential-free
validation, and exactly one local commit. The resulting candidate is locally
implemented and tested but remains active and portfolio-primary while it
awaits a fresh ordinary-Codex bootstrap audit. It is not published,
operational, independently audited, or mission-complete. A controlled real
Crew Chief acceptance run requires later separate authorization; Rangefinder
does not advance through this amendment.

## 2026-08-10 amendment — Crew Chief closeout and idle state

Maverick completed `governance/crew-chief` with its documented limitations and
did not activate Rangefinder or any successor. The repository is between
missions. The next gate is Maverick's selection and authorization of a mission.
