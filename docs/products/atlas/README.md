# Atlas

Atlas is the academic product currently composed on Wingman OS. Canonical
source lives under `src/products/atlas/`; canonical tests live under
`tests/products/atlas/`.

Atlas owns academic enrichment, retrieval interpretation, Briefing generation,
Library and intake policy, batch course-assignment policy, terminal and
Streamlit composition, and user-facing academic vocabulary. It uses neutral
Wingman Core and Shared mechanisms through Product Contract v1.

Current completed work includes Cockpit, Traceback, Intake, Library,
Continuity, Briefing, [bulk ingestion](../../missions/atlas/bulk-ingestion/mission.md),
and the [Website & Course Cockpit MVP](../../missions/atlas/website-course-cockpit/mission.md).
Mission state remains authoritative under `docs/missions/atlas/`.

Website syllabus intake performs a bounded, reviewable inspection of the
opening preview: at most 10 MiB, eight opening pages or units, 12,000
characters, and a three-second advisory processing budget. When it identifies
a syllabus and course identity, the upload preview proposes that course
assignment and folder name before any source mutation. The source-backed
Course Catalog then groups registered materials under the course name and the
Atlas-owned `syllabus`, `notes`, `lectures`, `homework`, and `other` folders.
These are metadata-backed virtual folders: uploaded originals remain in their
source-identified storage so traceback and source-management protections are
preserved.
