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

When one batch identifies multiple courses, the preview exposes an editable
course ID and folder name for every file and invalidates confirmation whenever
either value changes. Re-uploading identical bytes never creates a second
source: Atlas applies compatible confirmed course metadata to the existing
active source instead. It fails visibly without reassignment when that source
already belongs to a different course, so conflicting course ownership must be
reviewed from the existing source before another import attempt.

Every successful Atlas upload also attempts an automatic, source-grounded
summary. For documents with enough source material, Atlas targets roughly
450–900 words (about one to two pages); short documents receive a proportional
summary rather than padded or invented content. The derived artifact is stored
beside the source-identified processed knowledge, and each course's virtual
`Summaries` folder gathers the saved summary for every assigned document.
Summary generation is deliberately non-destructive: a missing API
configuration, model failure, or invalid response leaves the uploaded original
and searchable knowledge intact, displays a safe failed state, and permits a
later retry from the document page. For both automatic generation and a manual
retry, Atlas records that an attempt began before calling the model, so even an
artifact-write failure remains a durable failed state in batch evidence and
the later Course Cockpit. Registry, current-file, and processed-knowledge
hashes mark summaries stale when either the underlying document or its
extracted evidence changes.
