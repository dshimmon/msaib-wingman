<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/atlas/website-course-cockpit/mission.md",
  "archived_from": "docs/missions/atlas/website-course-cockpit/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> lifecycle record is
> [`docs/missions/atlas/website-course-cockpit/mission.md`](../../../../missions/atlas/website-course-cockpit/mission.md).
> This journal preserves the implementation sequence and does not override
> current mission authority.

# Atlas Website & Course Cockpit MVP Journal

**Call sign:** ATLAS-WEB

**Target:** August 23, 2026 class start

**Final status:** Completed by Maverick on August 11, 2026, with disclosed
deployment and dependency limits

## Objective

Substantially improve the existing Atlas Streamlit interface without replacing
its front-end stack. The approved MVP needed a coherent responsive shell,
Course Cockpit, course and document pages, and integrated access to Chat,
Library, Briefings, batch upload, and Prompt Optimizer.

## Authorized boundaries

- Keep the Atlas Streamlit entry point as a thin composition root.
- Place Atlas-owned presentation, navigation, adapter, state, page, and style
  behavior under `src/products/atlas/ui/`.
- Use a narrow Atlas adapter for the approved Flight Cards Website contract;
  do not edit or recreate Flight Cards lifecycle, generation, persistence,
  ingestion, or mutation behavior.
- Preserve Chat evidence, Briefing evidence and persistence warnings, Library
  source management, upload/retry, and Prompt Optimizer behavior.
- Build only an honest unavailable Practice Test seam because no approved
  owning service contract existed.
- Preserve original-source access and disclose AI-derived/source-grounded
  summaries visibly.

## Implementation

The mission delivered:

- a persistent responsive Atlas shell and navigation;
- Course Cockpit cards for assigned courses and Unassigned materials;
- unified course pages for materials, summaries, Chat, Briefings, and the
  Practice Test seam;
- source-first document pages with status, course, provenance, summary state,
  evidence references, original-source access, and contract-allowed actions;
- bounded course/source deep links with safe recovery;
- preserved Library, source-management, upload/retry, Chat, Briefing, and
  Prompt Optimizer pathways; and
- focused unit and Streamlit AppTest coverage.

The smallest protected compatibility edit registered the new Atlas UI modules
in `src/wingman/shared/airframe_manifest.py`. No Ledger, migration, Flight
Cards-owned service, Practice Test service, compatibility facade, deployment,
or live-data behavior was changed.

## Reconciliation and validation

The implementation was reconciled onto corrected `origin/main` at
`09abc0ce50e4c86cd69da4608b6c86f1c744816e`. The accepted subject passed:

- 59 focused Atlas/UI tests;
- all 448 credential-free offline repository tests;
- compilation;
- affected-scope Ruff and Black checks;
- governance generation and validation; and
- staged and unstaged Git whitespace checks.

Isolated browser evidence covered 1440x900, 1024x768, 390x844, keyboard focus,
equivalent-viewport layout reflow, and a fresh zero-error console. The
available browser could not perform actual page-level 200% zoom. Crew Chief
identified that evidence distinction, and Maverick explicitly accepted the
equivalent-viewport limitation and narrowed claim. No direct
actual-200%-browser-zoom pass is claimed.

## Crew Chief review

The final fresh, read-only, deep-risk Crew Chief review used audit ID
`3ffedd2f90900436d20989836cc7cf6718fce9527308e78f92a4516faf8fc6bf`.
It returned `PASS` with zero findings. The canonical report validated,
reconciliation was complete and approval-ready, and repository state was
identical before and after review.

Crew Chief's model-authored `generated_at` timestamp was later than the
controller completion time. The immutable report remains preserved; this is a
metadata defect, not an Atlas finding or evidence-tampering indication.

## Publication

Codex created implementation commit
`05645d42f32ba8f16ea12df4756d36754a881cf7`, pushed
`codex/atlas-website-course-cockpit`, and fast-forwarded it into GitHub `main`
under Maverick's authorization. A second commit,
`7f957e79b6afc4eb3cc4e93e5c3efab45571e216`, recorded the actual audit and
merge state in canonical mission metadata and was also fast-forwarded into
`main`.

## Deployment and completion

On August 11, 2026, Maverick authorized deployment and declared the mission
complete. Repository inspection found no deployment workflow, hosting
manifest, production URL, cloud target, or credential contract. The only
documented runtime is local Streamlit. Codex therefore did not invent a
destination or claim a production deployment.

The mission is complete for its approved MVP boundary. A future external
deployment requires an identified target and production configuration. Live
Flight Cards integration and full Practice Test acceptance remain dependent on
their owning services and were not silently included in this completion.

The first 32-test repository-governance completion run found one stale test
expectation that named Crew Chief as the last completed mission. The test was
generalized to derive the newest completed mission from canonical metadata.
The exact 32-test rerun passed, as did repository governance validation, the
affected Ruff check, and Git whitespace validation. The installed Black
version would also reformat unrelated pre-existing lines in that governance
test module; Codex preserved those lines instead of broadening the completion
diff and does not claim a clean whole-file Black check for that one test file.

## Enduring lessons

- A product UI adapter should depend on an owning service contract rather than
  reading storage internals.
- Derived-summary failure must never hide a valid original source.
- Navigation can expose an honest seam without inventing missing domain
  behavior.
- Responsive viewport evidence and actual browser zoom evidence are distinct
  claims and should be labeled precisely.
- Git publication, external deployment, and mission completion are separate
  states and must be reported independently.
