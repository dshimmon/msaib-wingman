# Atlas Website & Course Cockpit MVP

<!-- wingman-mission-metadata
{
  "schema_version": 1,
  "id": "atlas/website-course-cockpit",
  "legacy_aliases": [],
  "title": "Atlas Website & Course Cockpit MVP",
  "call_sign": "ATLAS-WEB",
  "namespace": "atlas",
  "lifecycle": "active",
  "priority": "high",
  "portfolio_primary": false,
  "authorization_gate": "implementation, Crew Chief re-review, commit, push, and merge authorized by Maverick; mission completion remains a separate Maverick decision",
  "approval_evidence": [
    {
      "date": "2026-08-10",
      "authority": "Maverick",
      "scope": "Authorized implementation of the Atlas Website & Course Cockpit MVP for the August 23, 2026 class-start target, including the supplied Flight Cards presentation contract, an unavailable Practice Test seam, credential-free validation, and an audit-ready handoff; prohibited staging, commit, push, merge, deployment, migration, and live-data mutation."
    },
    {
      "date": "2026-08-10",
      "authority": "Maverick",
      "scope": "Approved the smallest necessary protected edit to src/wingman/shared/airframe_manifest.py for Atlas UI module registration."
    },
    {
      "date": "2026-08-10",
      "authority": "Maverick",
      "scope": "Declared Crew Chief available, authorized Crew Chief for this exact audit, and explicitly authorized the canonical fresh-session fallback required by the installed CLI."
    },
    {
      "date": "2026-08-11",
      "authority": "Maverick",
      "scope": "Accepted the disclosed equivalent-viewport limitation for the 200% zoom criterion and the corresponding narrowed verification claim; no direct actual-200%-browser-zoom pass is claimed."
    },
    {
      "date": "2026-08-11",
      "authority": "Maverick",
      "scope": "Authorized Codex to commit and push the Atlas Website mission implementation and merge it with main after required Crew Chief reconciliation."
    }
  ],
  "baseline_commit": "b1910d0c69a52d73ddde93cb9722f12540c5d1e7",
  "implementation_commits": [],
  "pushed": false,
  "merged": false,
  "official_decisions": [
    "docs/decisions/architecture/product-separation.md",
    "docs/decisions/architecture/source-traceability.md",
    "docs/decisions/governance/crew-chief-audit.md"
  ],
  "workstream": {
    "owner_session": "Codex Atlas Website implementation authorized by Maverick on 2026-08-10",
    "branch": "codex/atlas-website-course-cockpit (planned from origin/main at 09abc0ce50e4c86cd69da4608b6c86f1c744816e)",
    "worktree": "/private/tmp/atlas-crew-chief-corrected-audit-repo-20260811-01",
    "writable_scope": [
      "src/products/atlas/streamlit_app.py",
      "src/products/atlas/ui/",
      "src/wingman/shared/airframe_manifest.py",
      "tests/products/atlas/",
      "tests/wingman/test_product_contract.py",
      "docs/missions/atlas/website-course-cockpit/"
    ],
    "state": "implementation_complete_crew_chief_re_review_pending",
    "next_gate": "Crew Chief re-reviews the exact accepted working-tree package; Codex reconciles every result; authorized commit, push, and merge may then proceed."
  },
  "next_gate": "Crew Chief re-review and reconciliation, followed by the authorized commit, push, and merge; mission completion remains a separate Maverick decision.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "healthy"
}
-->

Lifecycle: **active**. Call sign: **ATLAS-WEB**.
Target: **August 23, 2026 class start**.

Maverick authorized a substantial improvement to the existing Atlas Streamlit
1.60 interface without replacing the front-end stack. The approved objective
is a coherent responsive shell, Course Cockpit, course and document pages, and
integrated access to the existing Chat, Library, Briefings, batch upload, and
Prompt Optimizer experiences.

## Approved implementation boundary

- Keep `src/products/atlas/streamlit_app.py` as a thin composition root and
  place Atlas-owned shell, navigation, page, adapter, state, and style modules
  under `src/products/atlas/ui/`.
- Build the Flight Cards presentation through a narrow Atlas UI adapter using
  the supplied Website contract. Do not read or write Ledger or raw source
  metadata directly, and do not edit or recreate Flight Cards lifecycle,
  generation, persistence, ingestion, or mutation logic.
- Preserve valid source access when a derived summary is missing, stale, or
  failed. Keep AI-generated and source-grounded disclosure visible.
- Preserve existing Chat evidence, Briefing evidence and persistence warning,
  Library/source management, batch upload/retry, and Prompt Optimizer behavior.
- Do not claim Chat or Briefing retrieval is course-restricted unless an owning
  service proves it.
- Provide safe bounded course/source deep links and loading, empty, degraded,
  success, and error states.
- Validate desktop, tablet, mobile, keyboard, focus, contrast, and 200% zoom
  behavior without brittle selectors for generated or hashed Streamlit classes.

## Dependency limits

The Flight Cards backend was not present in the approved implementation
baseline. The Website adapter and presentation may be implemented against the
approved contract, but live owning-service integration must not be claimed
until that backend exists.

No approved Practice Test owning service contract is visible. Only its
navigation/page seam and an honest unavailable state are authorized. Questions,
scoring, attempts, persistence, or other assessment behavior are excluded, and
full Practice Test acceptance remains blocked.

## Current gate

Implementation and credential-free verification are reported complete for the
authorized boundary. Maverick accepted the disclosed equivalent-viewport
limitation for the 200% zoom criterion; direct actual-200%-browser-zoom
verification is not claimed. Crew Chief must re-review the exact frozen
working-tree subject, and Codex must resolve, dispute with evidence, or
escalate every result. Maverick authorized commit, push, and merge after that
gate. Deployment and mission completion remain separate Maverick decisions.
