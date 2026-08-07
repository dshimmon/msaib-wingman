<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/atlas/intake/mission.md",
  "archived_from": "docs/missions/atlas/intake/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> mission record is [`docs/missions/atlas/intake/mission.md`](../../../../missions/atlas/intake/mission.md).
> Every lifecycle, approval, commit, publication, and next-gate claim in
> the preserved body below is time-bound historical evidence and is not
> authoritative current status.

# Mission 022 — Atlas Accepts New Documents

**Mission Call Sign:** Intake

**Status:** ✅ Complete

---

## Objective

Allow Academic Wingman — Atlas to accept new documents through its browser interface and convert multiple file formats into searchable, traceable Wingman knowledge.

Mission 022 replaced the PowerPoint-specific ingestion process with a shared document-intake architecture supporting PowerPoint, PDF, Word, and Excel.

---

## Deliverables

* Added multi-format document intake support for:

  * PowerPoint `.pptx`
  * PDF `.pdf`
  * Word `.docx`
  * Excel `.xlsx`
* Added the required document-processing dependencies:

  * `PyMuPDF`
  * `python-docx`
  * `openpyxl`
* Refactored PowerPoint extraction into:

  * `src/powerpoint_adapter.py`
* Created:

  * `src/document_router.py`
* Defined one normalized document-unit contract:

```python
{
    "heading": str | None,
    "location": str,
    "text": str,
}
```

* Refactored `src/document_ingestion.py`.
* Separated format extraction from Wingman knowledge creation.
* Added support for stable source IDs independent from filenames.
* Preserved the existing PowerPoint ingestion behavior.
* Confirmed the onboarding presentation continued producing:

  * 23 knowledge objects
  * 9 curriculum records on Slide 8
* Created:

  * `src/word_adapter.py`
* Added Word extraction for:

  * Paragraphs
  * Heading-based sections
  * Tables
  * Pre-heading content
* Added stable Word locations:

  * `Section 1`
  * `Section 2`
* Created:

  * `src/pdf_adapter.py`
* Added PDF extraction for:

  * Readable page text
  * Conservative page headings
  * Best-effort tables
  * Exact physical page locations
* Added stable PDF locations:

  * `Page 1`
  * `Page 2`
* Added a clear error for PDFs containing no extractable text.
* Deferred OCR for image-only PDFs.
* Created:

  * `src/excel_adapter.py`
* Added Excel extraction for:

  * Worksheets in workbook order
  * Blank-row-delimited data groups
  * Text
  * Numbers
  * Booleans
  * Dates and datetimes
  * Formula strings
  * Internal empty cells
* Added stable Excel locations such as:

  * `Sheet Overview, Rows 1-5`
* Added a clear error for workbooks containing no readable data.
* Created:

  * `src/intake_service.py`
* Added browser-upload validation.
* Added empty-upload rejection.
* Added stable source-ID generation.
* Added SHA-256 content hashing.
* Added duplicate-content detection.
* Added local original-file storage.
* Added automatic knowledge-object creation.
* Added automatic embedding generation.
* Added automatic source registration.
* Added upload timestamps.
* Added cleanup when ingestion fails.
* Updated:

  * `src/source_registry.py`
* Added source-registry saving through atomic file replacement.
* Added source registration and metadata updating.
* Added source lookup by content hash.
* Updated:

  * `src/streamlit_app.py`
* Added the Atlas browser uploader.
* Added metadata fields for:

  * Display name
  * Domain
  * Program
  * Academic year
* Added success, duplicate, and failure messages.
* Added local upload protection through `.gitignore`.
* Prevented personal uploaded documents from being committed by default.
* Updated:

  * `src/retrieval_pipeline.py`
* Added a deterministic text-confidence gate.
* Prevented weak body-text matches from blocking semantic retrieval.
* Prevented a single broad search term from hijacking a multi-term question.
* Added a permanent mocked regression test for broad-term retrieval hijacking.
* Added automated tests for:

  * PowerPoint-compatible ingestion
  * Word extraction and routing
  * PDF extraction and routing
  * Excel extraction and routing
  * Intake validation
  * Duplicate detection
  * Failure cleanup
  * Source-registry persistence
  * Source-registry enrichment
  * Deterministic retrieval confidence
* Used Codex for contained implementation assignments after the shared architecture was established.
* Reviewed every Codex implementation before accepting it.
* Confirmed Codex did not commit or push.
* Updated:

  * `docs/architecture/Current-Architecture.txt`
  * `docs/architecture/Mission-022-Architecture.txt`

---

## Engineering Concepts

* Adapter pattern
* Document routing
* Normalized schemas
* Multi-format ingestion
* Dependency management
* Content hashing
* SHA-256
* Duplicate detection
* Stable identifiers
* Atomic file replacement
* Failure cleanup
* Transaction-like workflows
* File validation
* Source registration
* Browser uploads
* Temporary test fixtures
* Mocking
* Test isolation
* Reading-order extraction
* Table flattening
* Spreadsheet row grouping
* Formula preservation
* OCR detection
* Retrieval confidence
* Deterministic guardrails
* Agent-assisted development
* Human code review

---

## Key Lessons

* Different document formats require different extraction methods.
* Every knowledge source should produce the same evidence schema.
* File-format logic should remain separate from knowledge enrichment.
* A document router allows new formats to be added without changing downstream retrieval.
* Stable source identity should not depend only on a filename.
* Content hashes can detect duplicate files even when filenames differ.
* Original documents and processed knowledge should remain connected.
* Uploaded files should be private by default.
* Partial ingestion failures should clean up their generated artifacts.
* Persistent registry writes should avoid leaving partially written JSON.
* Word documents are naturally organized around headings and sections.
* PDFs are naturally traced by physical page numbers.
* PDF heading and table detection should favor conservative extraction over fabricated structure.
* Image-only PDFs require OCR rather than ordinary text extraction.
* Excel workbooks require structural preservation, not merely concatenated cell text.
* Empty spreadsheet cells can carry meaning because they preserve column relationships.
* Spreadsheet formulas should be preserved when the system cannot calculate them reliably.
* A browser upload feature is not complete until the resulting knowledge is searchable.
* A regression test that sometimes passes is not fully reliable, even when the underlying feature works.
* LLM-generated search terms can vary between identical questions.
* Deterministic software must protect retrieval from weak or overly broad model-generated terms.
* Best-effort extraction should preserve usable content, but recoverable failures should eventually be recorded through diagnostic logging.
* Codex is most effective after the architecture and acceptance criteria have already been defined.
* Agent-generated code still requires human review, local testing, and architectural approval.

---

## Interview Takeaway

Explain how Wingman supports multiple document formats without creating separate retrieval systems.

Wingman uses a format-adapter architecture.

PowerPoint, PDF, Word, and Excel each have a specialized extraction adapter because their structures differ.

Each adapter returns the same normalized document-unit schema containing a heading, source location, and text.

The shared ingestion pipeline then converts those units into Wingman knowledge objects, enriches them with concepts and structured records, creates embeddings, stores the processed knowledge, and registers the original source.

Because retrieval works against the normalized knowledge schema, it does not need to know whether the evidence originated from a slide, page, Word section, or Excel row range.

The upload service also hashes each file for duplicate detection and cleans up stored artifacts when ingestion fails.

---

## Architectural Decision

**Decision:** Create one format-specific adapter per document type while requiring every adapter to return the same normalized document-unit schema.

**Why we made it:**

PowerPoint, PDF, Word, and Excel represent information differently.

PowerPoint is organized into slides.

PDF is organized into physical pages.

Word is organized into headings, paragraphs, and tables.

Excel is organized into worksheets, rows, cells, and formulas.

Attempting to process all formats through one extraction function would mix unrelated parsing rules and create fragile code.

Instead, each adapter understands only its own format.

The document router chooses the correct adapter.

The shared ingestion pipeline handles everything after extraction.

This preserves the principle:

> Different file formats require different extraction methods, but every source should produce the same evidence schema.

**Alternatives considered:**

* Convert every source to plain text before ingestion.
* Use one large extraction function for all formats.
* Send every complete document directly to the LLM.
* Build only PowerPoint support.
* Delay Excel support.
* Introduce a third-party document-processing platform.
* Add OCR immediately.
* Store uploaded documents without duplicate detection.
* Use filenames as permanent source identities.
* Register sources manually after every upload.
* Commit uploaded user files to the repository.
* Trust any deterministic text result returned from LLM-generated search terms.

**Tradeoffs:**

Each supported format requires its own adapter and test suite.

PDF reading order and table detection remain best-effort.

Image-only PDFs cannot yet be ingested without OCR.

Word content in headers, footers, comments, text boxes, and embedded objects is not extracted.

Excel formulas are preserved but not calculated.

Excel date-only values may include a midnight timestamp after loading.

Uploads currently remain local to the running Atlas environment.

The first uploader displays more source evidence than the final polished interface should show.

However, the architecture provides transparent, testable, and extensible multi-format intake without replacing Wingman’s deterministic knowledge pipeline.

---

## Goose's Notes

Mission 022 was the largest Wingman mission so far.

Before Intake, Wingman’s ingestion process understood one known PowerPoint presentation.

After Intake, Atlas can accept four modern document formats from its browser:

```text
PowerPoint
PDF
Word
Excel
```

Each format now produces normalized evidence with a precise location:

```text
PowerPoint → Slide 8
PDF       → Page 1
Word      → Section 2
Excel     → Sheet Overview, Rows 1-5
```

The adapters were validated through synthetic documents and complete Wingman retrieval.

A Word document describing Project Falcon was ingested and retrieved successfully.

A PDF describing Project Orion was ingested and retrieved successfully.

An Excel workbook describing Project Apollo was ingested and retrieved successfully.

The browser uploader was then tested using a real document.

Atlas:

* Stored the original file
* Created knowledge objects
* Created embeddings
* Registered friendly source metadata
* Answered questions from the new source
* Detected a second upload of the same file

This mission also introduced Codex into the development workflow.

Goose established the architecture and acceptance criteria.

Codex implemented contained adapters and tests.

Maverick reviewed the results and ran the code locally.

Goose inspected the implementation before it was accepted.

The working model became:

```text
Goose defines the pattern
        |
        v
Codex accelerates implementation
        |
        v
Maverick tests and reviews
        |
        v
Goose approves architecture
```

---

## Mission Debrief

### What We Built

Atlas now has:

* A browser document uploader
* PowerPoint intake
* PDF intake
* Word intake
* Excel intake
* A document router
* A common normalized extraction schema
* Automatic knowledge-object creation
* Automatic concept enrichment
* Automatic structured-record extraction
* Automatic embedding generation
* Automatic source registration
* Stable source IDs
* Friendly source names
* Content-hash duplicate detection
* Original-file preservation
* Upload timestamps
* Atomic source-registry writes
* Failure cleanup
* Private local upload storage
* Exact slide, page, section, sheet, and row provenance
* A deterministic retrieval-confidence gate
* Thirty-six passing isolated unit tests
* Seven passing live retrieval tests

### Biggest Lesson

Supporting multiple file formats does not require multiple knowledge systems.

The correct architecture is:

```text
Different Extraction
        |
        v
Common Knowledge Representation
        |
        v
Shared Retrieval
```

The format adapter preserves what is unique about the source.

The normalized schema preserves what every source has in common.

### Architecture Impact

Before Mission 022:

```text
PowerPoint File
      |
      v
PowerPoint-Specific Ingestion
      |
      v
Wingman Knowledge
```

After Mission 022:

```text
PPTX ----+
PDF -----+
DOCX ----+----> document_router.py
XLSX ----+              |
                         v
               Format-Specific Adapter
                         |
                         v
              Normalized Document Units
                         |
                         v
               document_ingestion.py
                         |
                         +-- Knowledge objects
                         +-- Concepts
                         +-- Records
                         +-- Embeddings
                         |
                         v
                 Searchable Knowledge
```

The browser intake flow is:

```text
Uploaded File
      |
      v
Validate Extension and Content
      |
      v
Generate SHA-256 Hash
      |
      +-- Duplicate --> Return Existing Source
      |
      v
Create Stable Source ID
      |
      v
Store Original File
      |
      v
Route to Format Adapter
      |
      v
Create and Enrich Knowledge
      |
      v
Generate Embeddings
      |
      v
Register Source Metadata
      |
      v
Available to Atlas
```

### Validated Format Tests

**PowerPoint**

Result:

Passed.

The original onboarding presentation continued producing 23 knowledge objects and preserving all existing retrieval behavior.

---

**Word**

Synthetic source:

`Project Falcon`

Result:

Passed.

Atlas retrieved:

* Launch date
* Project owner
* Milestone
* Status

Source location:

`Section 2`

---

**PDF**

Synthetic source:

`Project Orion`

Result:

Passed.

Atlas retrieved:

* Launch date
* Project owner
* Milestone
* Status

Source location:

`Page 1`

---

**Excel**

Synthetic source:

`Project Apollo`

Result:

Passed.

Atlas retrieved:

* Project owner
* Launch date
* Budget status

Source location:

`Sheet Overview, Rows 1-2`

---

**Browser Upload**

Result:

Passed.

Atlas ingested a user-selected file, made it searchable, displayed its friendly source metadata, and rejected an identical duplicate upload.

### Testing Baseline

Isolated unit tests:

```text
Intake Service       7
Source Registry      8
Retrieval Pipeline   7
Excel Adapter        5
PDF Adapter          5
Word Adapter         4
Total               36
```

Live retrieval suite:

```text
Passed: 7
Failed: 0
Total:  7
```

### Accepted Limitations

* Legacy `.ppt`, `.doc`, and `.xls` files are not supported.
* Image-only PDFs require OCR.
* PDF layout extraction may require future improvement.
* PDF table errors are currently treated as recoverable without diagnostic logging.
* Word headers, footers, comments, text boxes, and embedded objects are not extracted.
* Excel formulas are preserved but not calculated.
* Excel date-only values may include a midnight timestamp.
* Upload storage is local rather than cloud-based.
* Uploaded documents are ignored by Git and are not synchronized between machines.
* The uploader accepts one file at a time.
* Upload metadata is entered manually.
* The source display currently shows more evidence text than the final polished interface should.
* User authentication and ownership are not implemented.
* Upload file-size limits have not been customized.
* A deployed environment will require persistent storage.
* LLM-dependent live retrieval tests can still incur API usage and network dependency.

These limitations are appropriate for the first multi-format intake system.

### Next Mission

**Mission 023 — 🛫 Ready for Takeoff**

**Atlas Manages Its Knowledge**

**Mission Call Sign:** Library

Mission 023 will create a document-library interface where users can:

* See every registered source
* Inspect source metadata
* View ingestion status
* See knowledge-object counts
* Detect and understand duplicates
* Reprocess sources
* Remove sources safely
* Understand which knowledge belongs to Atlas

Mission 022 allowed knowledge to enter Wingman.

Mission 023 will give users control over the knowledge already inside it.
