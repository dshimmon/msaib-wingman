# Fresh-Context 30-Second Usability Drill

## Reviewer input

Give an approved fresh-context reviewer only this repository path:

`/private/tmp/wingman-repository-architecture-20260807-01`

Start a 30-second timer. Do not provide the mission brief, file hints, answers,
or prior conversation. Ask the reviewer to report:

1. portfolio-primary mission ID and name;
2. lifecycle and authorization gate;
3. authoritative mission-record path;
4. last completed work and commit; and
5. exact next approval or execution gate.

Record elapsed time, paths opened in order, the verbatim answers, and a pass or
fail for each item. Reading `AGENTS.md` first is part of the supported workflow;
the reviewer should then reach the generated `CURRENT_MISSION.md` entry point.

## Expected authoritative answer

- Mission: `governance/repository-architecture` — Wingman Repository
  Architecture.
- Lifecycle: `active`.
- Authorization gate:
  `previous_independent_audit_failed_corrections_committed_fresh_audit_and_antecedent_disposition_required`.
- Record: `docs/missions/governance/repository-architecture/mission.md`.
- Last completed work: `atlas/bulk-ingestion` at `c88a226`.
- Next gate: a fresh independent read-only audit must pass on the correction
  commits; publication remains separately blocked until Maverick dispositions
  the eight antecedent commits.

## Status

Prepared on 2026-08-07. Not yet executed. Automated governance checks are not
a substitute for the fresh-context reviewer.
