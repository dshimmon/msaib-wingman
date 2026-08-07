<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/atlas/library/mission.md",
  "archived_from": "docs/missions/atlas/library/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> mission record is [`docs/missions/atlas/library/mission.md`](../../../../missions/atlas/library/mission.md).
> Every lifecycle, approval, commit, publication, and next-gate claim in
> the preserved body below is time-bound historical evidence and is not
> authoritative current status.

# Mission 023 — Atlas Manages Its Knowledge

**Mission Call Sign:** Library

**Status:** ✅ Complete

---

## Objective

Give Academic Wingman — Atlas a visible and trustworthy home for every registered knowledge source.

Mission 023 introduced an Atlas Library that displays source metadata, ingestion health, knowledge counts, semantic-index status, and original-file access.

The mission also added transactional source reprocessing and safe uploaded-source removal while protecting repository-managed sources.

---

## Deliverables

* Created `src/library_service.py`.
* Added a unified inventory of every registered Atlas source.
* Combined information from:

  * The source registry
  * Processed knowledge JSON
  * Original source files
  * The embedding index
* Added Library source metrics:

  * Knowledge-object count
  * Unique concept count
  * Structured-record count
  * Embedding count
* Added source-health states:

  * Ready
  * Partially indexed
  * Needs processing
  * Original unavailable
* Added source ownership through:

  * `source_kind = repository`
  * `source_kind = upload`
* Defaulted missing source ownership safely to `repository`.
* Added management permissions:

  * `can_reprocess`
  * `can_remove`
* Protected repository-managed sources from browser deletion.
* Added the Atlas Library workspace to `src/streamlit_app.py`.
* Preserved the existing Atlas Chat workspace.
* Added Library-wide summary metrics.
* Added expandable source cards.
* Added source metadata and original-file access.
* Added source health messaging.
* Added the Reprocess Source control.
* Added uploaded-source removal with explicit `REMOVE` confirmation.
* Created `src/library_management_service.py`.
* Added safe source reprocessing.
* Preserved stable source IDs during reprocessing.
* Removed stale embeddings before rebuilding a source.
* Removed stale concept occurrences before rebuilding a source.
* Refreshed the content hash after successful reprocessing.
* Added a UTC reprocessing timestamp.
* Added complete reprocessing rollback across:

  * Source registry
  * Embedding index
  * Concept registry
  * Processed knowledge JSON
* Added safe uploaded-source removal.
* Restricted removal to uploaded sources.
* Restricted filesystem deletion to the configured uploads directory.
* Added path traversal protection.
* Added symbolic-link protection.
* Added regular-file rejection when a source directory is expected.
* Added atomic tombstone renaming before deletion.
* Added registry rollback when source removal fails.
* Added nonfatal warnings when final tombstone cleanup fails.
* Removed concept entries when no occurrences remain.
* Preserved concepts shared by other sources.
* Preserved embeddings belonging to similarly named sources.
* Converted concept-registry and embedding-index persistence to atomic file replacement.
* Removed the stale module-level concept-registry cache.
* Reloaded the concept registry whenever concepts are registered.
* Added `source_kind` metadata during document intake.
* Added isolated Library inventory tests.
* Added isolated Library management and rollback tests.
* Confirmed the Atlas Library correctly displayed:

  * MSAIB Onboarding 2026
  * Ready status
  * 23 knowledge units
  * 21 concepts
  * 35 structured records
  * 23 embeddings
* Validated the complete Project Tempest management cycle:

  * Upload
  * Library display
  * Reprocess
  * Retrieval
  * Removal
  * Knowledge absence after removal
* Confirmed the repository-managed onboarding source could not be removed.
* Preserved the live retrieval baseline:

  * 7 passed
  * 0 failed
* Reached a total of 65 passing isolated unit tests.
* Updated:

  * `docs/architecture/Current-Architecture.txt`
  * `docs/architecture/Mission-023-Architecture.txt`

---

## Engineering Concepts

* Knowledge inventories
* Source-health monitoring
* Persistent metadata
* Source ownership
* Permission boundaries
* Transactional workflows
* Rollback
* Atomic writes
* Tombstone deletion
* Path traversal protection
* Symbolic-link protection
* Stable identifiers
* Reprocessing
* Stale-data cleanup
* Orphan prevention
* Shared-concept preservation
* Exact-prefix matching
* Destructive-action confirmation
* Failure recovery
* Local filesystem safety
* Agent-assisted implementation
* Human review of destructive operations

---

## Key Lessons

* Uploading knowledge and managing knowledge are separate product responsibilities.
* A knowledge system should make its current state visible to the user.
* Source health must be calculated from real storage rather than assumed.
* The source registry identifies a document but does not alone prove that its knowledge is usable.
* Original files, processed knowledge, concepts, records, and embeddings must remain consistent.
* Reprocessing must remove stale derived data before rebuilding it.
* Reprocessing should preserve stable source identity.
* A source content hash must be refreshed when the source is rebuilt.
* Cached persistent state can resurrect deleted information in a long-running process.
* Persistent registries should be loaded fresh when correctness depends on their current state.
* Destructive actions should not live directly inside interface code.
* Repository-managed sources and user-uploaded sources require different permissions.
* Missing ownership metadata should default to the safest interpretation.
* Filesystem deletion should be constrained to a known root directory.
* Path resolution alone is insufficient without symbolic-link and exact-name checks.
* Renaming data to a tombstone before deletion creates a rollback opportunity.
* Multi-file transactions require explicit snapshots and restoration because the filesystem does not provide one cross-file transaction.
* Rollback failures must be reported clearly rather than hidden.
* Shared concepts must survive when one contributing source is removed.
* Visible chat history is different from active searchable knowledge.
* A removed source may remain visible in an old conversation while no longer being retrievable.
* Destructive capabilities deserve deeper testing and higher reasoning effort than ordinary UI changes.

---

## Interview Takeaway

Explain how Atlas safely manages documents after they have been uploaded.

Atlas maintains a Library service that combines source metadata, processed knowledge, original-file availability, structured records, concepts, and semantic embeddings.

Each source receives a health status based on whether its original document exists, whether processed knowledge exists, and whether every knowledge object has an embedding.

Atlas distinguishes repository-managed sources from user uploads.

Repository sources are protected from deletion.

Uploaded sources can be reprocessed or removed.

Reprocessing preserves the stable source ID, removes stale concepts and embeddings, rebuilds knowledge from the original file, refreshes the content hash, and restores the previous state if anything fails.

Removal first renames the uploaded source directory to a tombstone. Atlas then removes the source from its registries and deletes the tombstone only after persistence succeeds. If persistence fails, the registries and source directory are restored.

---

## Architectural Decision

**Decision:** Introduce a dedicated Library service and a transactional management service instead of placing storage inspection and deletion logic directly inside Streamlit.

**Why we made it:**

The user interface should display and request actions.

It should not coordinate destructive changes across several persistent stores.

A registered Atlas source can affect:

* The original file
* Processed knowledge JSON
* The source registry
* The embedding index
* The concept registry

Reprocessing or removing only some of these would leave Atlas inconsistent.

The Library service therefore provides a read-only inventory and health model.

The Library management service coordinates state changes, snapshots previous data, validates ownership and paths, and restores state when operations fail.

**Alternatives considered:**

* Display only filenames from the uploads folder.
* Scan document folders without using the source registry.
* Put removal logic directly inside the Streamlit button.
* Allow all registered sources to be deleted.
* Infer ownership from file paths.
* Delete uploaded folders before updating registries.
* Leave stale embeddings after reprocessing.
* Leave old concept occurrences after reprocessing.
* Rely on filenames as permanent identities.
* Ignore partial failure because Atlas is currently local.
* Remove source folders using the metadata `original_path`.
* Add management controls without automated rollback tests.

**Tradeoffs:**

The rollback mechanism coordinates several atomic files but is not one true cross-file transaction.

No process-level locking prevents two management operations from running simultaneously.

A failed final tombstone cleanup can leave a hidden directory that requires later cleanup.

Repository sources can be reprocessed but cannot be removed through Atlas.

Visible chat history is not rewritten after source removal.

Library controls currently use the functional Streamlit interface rather than a polished production design.

However, the architecture prioritizes data integrity and clear permission boundaries before visual polish.

---

## Goose's Notes

Mission 023 transformed Atlas from a question-answer interface into a visible knowledge system.

Before Library, uploaded documents became searchable but disappeared into the internal storage architecture.

After Library, Atlas can show:

```text
Source
Status
Knowledge Units
Concepts
Structured Records
Embeddings
Original File
```

The onboarding presentation appeared as:

```text
MSAIB Onboarding 2026
Status: Ready
Knowledge Units: 23
Concepts: 21
Structured Records: 35
Embeddings: 23
```

The Project Tempest test proved the complete management cycle:

```text
Upload
    |
    v
Ready in Library
    |
    v
Reprocess
    |
    v
Still Searchable
    |
    v
Remove with Confirmation
    |
    v
Removed from Library
    |
    v
No Longer Retrievable
```

The repository-managed onboarding source showed Reprocess but remained protected from removal.

This mission also reinforced a product principle:

> Users should be able to see, understand, rebuild, and safely remove the knowledge they have entrusted to Wingman.

---

## Mission Debrief

### What We Built

Atlas now has:

* A Chat workspace
* A Library workspace
* A complete registered-source inventory
* Source-health status
* Knowledge-unit counts
* Concept counts
* Structured-record counts
* Embedding counts
* Original-document access
* Repository and upload ownership
* Protected repository sources
* Reprocessing controls
* Uploaded-source removal
* Explicit removal confirmation
* Transactional rollback
* Atomic registry persistence
* Tombstone deletion
* Content-hash refreshing
* Stale concept cleanup
* Stale embedding cleanup
* Shared-concept preservation
* Path and symlink safety
* Sixty-five passing isolated tests
* Seven passing live retrieval tests

### Biggest Lesson

A knowledge system is not trustworthy merely because it can ingest information.

It must also be able to explain what it knows, detect whether that knowledge is healthy, rebuild derived state, and remove user-owned knowledge without corrupting unrelated sources.

### Architecture Impact

Before Mission 023:

```text
Upload
    |
    v
Processed Knowledge
    |
    v
Retrieval
```

After Mission 023:

```text
Registered Source
        |
        v
Library Inventory
        |
        +-- Identity
        +-- Health
        +-- Counts
        +-- Original File
        |
        v
Management Service
        |
        +-- Reprocess
        +-- Remove Upload
        +-- Protect Repository
        |
        v
Consistent Persistent State
```

### Validated Library Tests

**Library Inventory**

Result:

Passed.

Atlas displayed the onboarding presentation with accurate source, knowledge, concept, record, and embedding counts.

---

**Repository Protection**

Source:

`MSAIB Onboarding 2026`

Result:

Passed.

Reprocessing was available.

Removal was prohibited.

---

**Uploaded-Source Reprocessing**

Source:

`Project Tempest`

Result:

Passed.

The source retained its identity and remained retrievable after rebuilding.

---

**Uploaded-Source Removal**

Source:

`Project Tempest`

Result:

Passed.

The source disappeared from the Library.

Its files and derived knowledge were removed.

Atlas no longer retrieved its launch date.

---

**Testing Baseline**

```text
Isolated unit tests:
65 passed

Live retrieval tests:
7 passed
0 failed
```

### Accepted Limitations

* Library storage remains local.
* There is no user authentication or per-user ownership.
* Simultaneous Library operations are not locked.
* Hidden tombstones may remain if final cleanup fails.
* Chat history is not rewritten after source removal.
* Source metadata editing is not yet available.
* The Library does not preview processed knowledge units.
* Source filtering, search, and sorting controls are limited.
* Reprocessing progress is displayed only through a spinner.
* Success messages disappear quickly after Streamlit reruns.
* The Library has not yet been moved to a polished production website.
* Cloud storage and deployment-safe persistence are not implemented.

These limitations are appropriate for the first safe knowledge-management system.

### Next Mission

**Mission 024 — 🛫 Ready for Takeoff**

**Atlas Understands Conversations**

**Mission Call Sign:** Continuity

Mission 024 will allow Atlas to use prior conversation turns when interpreting follow-up questions.

The goal is to understand exchanges such as:

```text
User:
What classes will I take in the fall?

Atlas:
...

User:
Which of those meet on Tuesday?
```

Visible history already exists.

Mission 024 will convert that visible history into controlled conversational context without allowing earlier messages to override source-grounded retrieval.
