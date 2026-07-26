# Mission 021 — Atlas Opens Its Sources

**Mission Call Sign:** Traceback

**Status:** ✅ Complete

---

## Objective

Strengthen Wingman’s source-preservation system by separating internal source identifiers from user-friendly source metadata and giving Atlas users a direct path back to the original document.

Mission 021 upgraded Atlas’s supporting evidence from internal filenames and raw locations into friendly, traceable source cards.

---

## Deliverables

* Created `data/sources/source-registry.json`.
* Introduced a persistent registry for source identity and metadata.
* Registered the MSAIB onboarding presentation using its stable internal source ID:

  * `msaib-onboarding-2026`
* Added user-facing source metadata:

  * Display name
  * Original filename
  * File type
  * MIME type
  * Domain
  * Program
  * Academic year
  * Original local path
  * Future source URL
* Created `src/source_registry.py`.
* Added source-registry loading.
* Added registry structure validation.
* Added evidence-source enrichment.
* Preserved the internal source identifier while attaching friendly metadata.
* Added fallback behavior for unregistered sources.
* Updated `src/wingman_service.py`.
* Enriched evidence after answer generation.
* Preserved raw retrieval evidence for reasoning.
* Returned source-enriched evidence to application interfaces.
* Updated `src/streamlit_app.py`.
* Replaced internal filenames with friendly source names.
* Added exact source-location display.
* Added file type, program, and academic-year metadata.
* Preserved the original supporting evidence text.
* Added original-file download controls.
* Added support for future cloud-based source links.
* Preserved evidence metadata inside Streamlit session history.
* Confirmed source cards continued to render correctly after Streamlit reruns.
* Confirmed the original PowerPoint could be downloaded successfully.
* Confirmed Orientation displayed:

  * MSAIB Onboarding 2026
  * Correct slide references
  * PPTX
  * MSAIB
  * 2026–2027
* Ran the complete retrieval regression suite.
* Preserved the expanded retrieval baseline:

  * 7 passed
  * 0 failed
* Updated:

  * `docs/architecture/Current-Architecture.txt`
  * `docs/architecture/Mission-021-Architecture.txt`

---

## Engineering Concepts

* Source registries
* Stable internal identifiers
* Friendly display names
* Metadata enrichment
* Source provenance
* Traceability
* Evidence lineage
* Interface-specific presentation
* Local file access
* File downloads
* MIME types
* Cloud source URLs
* Graceful fallback behavior
* Separation of reasoning data and presentation data
* Session-state compatibility
* Registry validation

---

## Key Lessons

* Internal identifiers and user-facing names serve different purposes.
* Stable source IDs should not depend on how a source is presented to the user.
* Friendly names can change without breaking retrieval references.
* A source registry provides one authoritative place for document metadata.
* Retrieved evidence should preserve its original source identity.
* Presentation metadata should enrich evidence rather than replace it.
* Source enrichment should occur after retrieval and reasoning.
* Atlas may summarize evidence, but users must retain a path back to the source.
* Exact slide, page, sheet, or section references are essential to trustworthy answers.
* A local prototype can provide source downloads before cloud storage exists.
* A future source URL can be added without redesigning the evidence schema.
* Stored session history may contain stale evidence after an evidence schema changes.
* Restarting the Streamlit session can be necessary when stored interface objects change.
* Retrieval regression tests protect the engine while interface behavior evolves.

---

## Interview Takeaway

Explain how Wingman preserves source traceability while presenting friendly source information.

Every document has a stable internal source identifier used by the retrieval system.

A separate source registry maps that identifier to user-facing metadata such as the display name, file type, program, academic year, original filename, and original source location.

After Wingman retrieves evidence and generates an answer, the evidence is enriched with this source metadata before being returned to the interface.

This preserves the deterministic retrieval identity while allowing the browser application to display clean source cards and provide access to the original document.

The user can see the exact slide supporting the answer and download the original PowerPoint.

---

## Architectural Decision

**Decision:** Store source metadata in a dedicated registry and enrich retrieved evidence only after answer generation.

**Why we made it:**

Knowledge objects already contained an internal document identifier:

`msaib-onboarding-2026`

That identifier is useful for storage, retrieval, and stable references.

However, it is not the best user-facing presentation.

Atlas should display:

`MSAIB Onboarding 2026`

while retaining the internal ID underneath.

A source registry allows Wingman to separate these responsibilities.

The retrieval and reasoning layers continue using stable source identifiers.

The interface receives enriched evidence containing friendly metadata and access information.

Source enrichment occurs after answer generation so presentation data does not alter retrieval or reasoning behavior.

**Alternatives considered:**

* Rename the internal source identifier.
* Store all metadata directly inside every knowledge object.
* Hardcode friendly names in the Streamlit interface.
* Let the LLM invent friendly document names.
* Pass local file paths into the reasoning context.
* Display only the raw filename.
* Wait for cloud storage before adding source access.
* Build source registration directly into the uploader before validating the registry model.

**Tradeoffs:**

The current source registry must be updated manually.

Local file downloads work only where the original file exists.

A local path will not automatically work after deployment to another machine.

Cloud source URLs are supported by the schema but not yet populated.

The source registry currently contains only one registered document.

However, the design creates a stable foundation for automatic registration during Mission 022.

---

## Goose's Notes

Mission 021 completed one of Wingman’s oldest promises:

> Atlas may summarize the evidence, but the user must always be able to trace the answer back to the original source.

Before Traceback, the browser displayed:

`msaib-onboarding-2026`

and:

`Slide 8`

The source location was preserved, but the experience still looked like an internal engineering system.

After Traceback, Atlas displays:

`MSAIB Onboarding 2026`

`Location: Slide 8`

`PPTX • MSAIB • 2026-2027`

and:

`Download Original Source`

The internal source ID still exists and remains unchanged.

This is important because source presentation may evolve while stored evidence references must remain stable.

The completed flow is:

```text
Retrieved Evidence
        |
        v
Internal Source ID
        |
        v
Source Registry Lookup
        |
        v
Friendly Metadata Attached
        |
        v
Atlas Source Card
        |
        v
Exact Location + Original File
```

---

## Mission Debrief

### What We Built

Atlas now has:

* A persistent source registry
* Stable internal source identities
* Friendly source display names
* Original filenames
* File-type metadata
* MIME-type metadata
* Program metadata
* Academic-year metadata
* Original local source paths
* Future cloud source URL support
* Source-enriched evidence
* Friendly Streamlit source cards
* Exact slide references
* Original evidence text
* Download access to the original document
* Source metadata preserved in visible session history
* A verified seven-test retrieval baseline

### Biggest Lesson

Source traceability is not only a citation at the bottom of an answer.

A trustworthy knowledge system should preserve the complete path:

```text
Answer
    |
    v
Evidence
    |
    v
Exact Location
    |
    v
Source Identity
    |
    v
Original Document
```

Friendly source presentation and deterministic source identity should remain separate.

One serves the user.

The other protects the system.

### Architecture Impact

Before Mission 021:

```text
Retrieved Evidence
        |
        v
Internal Source ID
        |
        v
Streamlit Display
```

After Mission 021:

```text
Retrieved Evidence
        |
        v
Internal Source ID
        |
        v
source_registry.py
        |
        v
Friendly Source Metadata
        |
        v
Streamlit Source Card
        |
        +-- Display name
        +-- Exact location
        +-- File details
        +-- Evidence text
        +-- Original-file access
```

The answer-generation flow remains:

```text
Question
    |
    v
Retrieval
    |
    v
Raw Evidence
    |
    v
Reasoning
    |
    v
Answer
```

The presentation flow is now:

```text
Raw Evidence
    |
    v
Source Registry Enrichment
    |
    v
Display Evidence
    |
    v
Browser Interface
```

### Validated Source Tests

**Friendly Source Name**

Question:

`Orientation`

Expected:

`MSAIB Onboarding 2026`

Result:

Passed.

---

**Exact Source Locations**

Expected:

* Slide 7
* Slide 23

Result:

Passed.

---

**Source Metadata**

Expected:

* PPTX
* MSAIB
* 2026–2027

Result:

Passed.

---

**Original File Access**

Expected:

The original onboarding PowerPoint can be downloaded from the Atlas source card.

Result:

Passed.

---

**Retrieval Regression Suite**

Result:

```text
Passed: 7
Failed: 0
Total:  7
```

### Accepted Limitations

* Source registration is currently manual.
* Only the onboarding presentation is registered.
* Original source access currently uses a local file download.
* Local paths will require a deployment-aware storage solution.
* Cloud source URLs are not yet populated.
* Atlas cannot yet upload documents through the browser.
* Source cards do not open directly to a specific PowerPoint slide.
* PDF page links, Word section links, and Excel sheet links do not yet exist.
* Source permissions and user ownership are not yet modeled.
* Duplicate-source detection is not yet implemented.

These limitations are intentionally deferred to the multi-format intake and knowledge-library missions.

### Next Mission

**Mission 022 — 🛫 Ready for Takeoff**

**Atlas Accepts New Documents**

**Mission Call Sign:** Intake

Mission 022 will introduce browser-based document uploads and a shared ingestion-routing system.

Atlas will support:

* PowerPoint `.pptx`
* PDF `.pdf`
* Word `.docx`
* Excel `.xlsx`

Each format will use a specialized adapter but produce Wingman’s common knowledge-object and evidence schema.

Uploaded sources will be:

* Validated
* Stored
* Registered automatically
* Routed to the correct extractor
* Converted into knowledge objects
* Enriched with concepts and records
* Embedded
* Added to Atlas’s knowledge base

Mission 021 gave every source an identity.

Mission 022 will allow new sources to enter the system.
