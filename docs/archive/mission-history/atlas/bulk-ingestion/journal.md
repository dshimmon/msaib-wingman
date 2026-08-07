<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/atlas/bulk-ingestion/mission.md",
  "archived_from": "docs/missions/atlas/bulk-ingestion/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> mission record is [`docs/missions/atlas/bulk-ingestion/mission.md`](../../../../missions/atlas/bulk-ingestion/mission.md).
> Every lifecycle, approval, commit, publication, and next-gate claim in
> the preserved body below is time-bound historical evidence and is not
> authoritative current status.

# Wingman Ingests Documents in Bulk

**Canonical mission number:** Not assigned by Maverick

**Canonical call sign:** Not assigned by Maverick

**Product:** Wingman OS, with Atlas as the implementing product

**Implementation state:** Implemented and locally tested; unapproved,
uncommitted, unpushed, and unmerged

## Objective and boundaries

Atlas can preview and ingest one explicitly authorized, sequential batch of
mixed-format documents. Every ingestible file requires a confirmed Atlas
`course_id`; every completed source keeps its own original, stable source ID,
SHA-256 hash, product metadata, exact evidence locations, Library actions, and
retrieval traceback.

This working record is deliberately unnumbered. Maverick has not assigned the
canonical mission number or call sign, and Rangefinder's numbering is
unchanged.

The mission does not add OCR, generated summaries, automatic course
classification, revision replacement, Contrail, Truth Clock, folder watching,
archives, concurrent writers, queues, background jobs, batch deletion,
retrieval optimization, Rangefinder, Storage Port, cloud storage,
authentication, agents, Radar, a Product Contract version bump, or a Ledger
migration.

## Architecture and ownership

- Core owns the CSV and inert UTF-8 text/Markdown adapters, typed extraction
  errors, document routing, atomic processed-knowledge write, and bounded
  folder discovery.
- Atlas owns `batch_ingestion`, the `course_id` meaning and validation rule,
  batch policy, manifest/report schema, browser behavior, and the repository
  folder CLI.
- The batch service receives an explicit `ProductContext`; Core never does.
- Course identity crosses generic storage and retrieval boundaries only as
  opaque source metadata through Product Contract v1's existing metadata
  extension surface.
- The existing single-file `ingest_uploaded_document` and
  `document_ingestion` facades remain supported. The browser uses the same
  batch path for one or many selected files.

No dependency was added. CSV uses Python's standard library, and plain text and
Markdown are parsed as inert UTF-8 text. Existing PDF, DOCX, XLSX, and PPTX
libraries and extraction behavior remain in place.

## Input modes and folder safety

The Streamlit uploader accepts multiple `.pdf`, `.docx`, `.xlsx`, `.pptx`,
`.csv`, `.txt`, `.md`, and `.markdown` files. It shows a pre-mutation table,
batch course assignment, per-file course and display-name overrides, explicit
assignment confirmation, per-file progress, terminal results, and the final
report. Successful sources remain individually manageable in Library.

The repository-native folder command is preview-only unless `--execute` is
explicitly supplied:

```bash
PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=bulk-ingestion-offline-placeholder \
  PYTHONPATH=src python3 -m bulk_ingestion ./selected-folder \
  --course-id AI-101 --recursive

PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=bulk-ingestion-offline-placeholder \
  PYTHONPATH=src python3 -m bulk_ingestion ./selected-folder \
  --course-id AI-101 --recursive --execute
```

Folder intake uses exactly one selected root, is non-recursive by default, and
requires `--recursive` to descend. Hidden files and directories are excluded
unless `--include-hidden` is supplied. Normalized relative paths determine
order. Parent aliases, empty/dot aliases, root or child symlinks, non-regular
files, root escapes, case aliases, and every multiply-linked file are rejected.
Accepted inputs retain the previewed root and file device/inode identities.
Execution opens every path component through directory descriptors with
no-follow flags, then rechecks identity, regular-file type, and link count
before and after reading. A file or directory replaced after preview is not
read or ingested.

## Supported evidence locations

| Format | Stable location and behavior |
|---|---|
| PDF | Physical `Page N`; a PDF with no extractable text becomes `needs_ocr`. |
| DOCX | Existing heading-aware `Section N`. |
| XLSX | Existing `Sheet NAME, Rows X-Y`. Formulas remain inert strings. |
| PPTX | Existing physical `Slide N`. |
| CSV | Physical `Row N`, with stable unique column labels and row/column relationships. |
| TXT | `Line N` or `Lines N-M` for contiguous readable groups. |
| Markdown | Heading-aware `Line N` or `Lines N-M`; links, code, formulas, macros, and embedded objects are never executed. |

CSV, text, and Markdown decoding is deterministic UTF-8 with an optional UTF-8
BOM. Invalid encoding and empty readable content fail clearly.

## Course metadata

No authoritative course identifier existed in the current curriculum records.
Atlas therefore declares the smallest source-metadata identifier, `course_id`,
inside its existing Product Contract v1 definition. It is trimmed, bounded to
120 characters, and restricted to readable identifier punctuation. The batch
default and every override require explicit confirmation; filenames and folder
names never assign a course automatically. The browser binds confirmation to
the selected-file, batch-default, and per-file-override signature. Changing any
course assignment clears confirmation, starts fresh batch state, and requires
the operator to confirm the new preview.

`course_id` is stored with the source, appears in Library, is attached to
retrieved evidence, survives manifest resume/retry and Library reprocessing,
and preserves the existing `program`, `academic_year`, opaque-metadata, and
missing-versus-explicit-null behavior. Products that do not declare the field
are rejected by the Atlas batch service and receive no Atlas course metadata.

## Per-file atomicity and isolation

The mutation order is:

```text
validate and hash
  -> write original through local temporary replacement
  -> extract and enrich
  -> atomically save processed knowledge
  -> atomically update embeddings
  -> register source in one Ledger transaction
  -> persist terminal manifest state
```

Atomic batch intake snapshots the exact pre-file embedding and concept-store
bytes. Extraction, enrichment, knowledge-save, indexing, or registration
failure removes the new original and processed file, restores both shared
stores byte-for-byte, verifies restoration, and only then permits the next
file. Ledger source registration is last and transactional. A failed
registration does not commit a source. A rollback or verification failure is
typed, records the file and stage, stops the batch, and leaves later files
pending. Earlier successful files are never rolled back.

Operational manifest persistence happens between stages. A manifest write
failure stops further processing. If interruption happens after canonical
registration but before the terminal manifest update, resume finds the
registered content hash and records a safe duplicate instead of reprocessing.
If no source is registered, resume removes deterministic unregistered
per-source artifacts before trying again.

## Duplicate and possible-revision behavior

- The same SHA-256 bytes under any name return `duplicate` and the existing
  source ID; no new ingestion occurs.
- The same visible filename with different bytes creates a distinct stable
  source and reports the earlier source as a possible revision.
- Possible revision is advisory only. No source is overwritten, removed,
  superseded, or linked into inferred lineage.

## Manifest, resume, retry, and report authority

Manifest version 1 is written atomically under ignored local `data/imports/`
storage by default. It contains the batch/product IDs, timestamps, input mode,
safe filename, size, hash, course assignment, stage, terminal result, attempt
count, stable reason, source/duplicate ID, knowledge count, cleanup evidence,
and possible-revision warnings. It contains no document body or unrestricted
absolute source path.

Manifest and report paths are required to be distinct. A caller-supplied
Markdown manifest such as `batch-state.md` therefore writes its report as
`batch-state.report.md`; the JSON manifest remains loadable for resume. An
explicit report path that aliases the manifest is rejected before either path
is written.

Successful, duplicate, skipped, and `needs_ocr` files are never blindly
reprocessed. Pending or interrupted files require the same relative identity
and SHA-256 bytes. Changed content is rejected into a new-batch action.
Terminal failures run again only through explicit `--retry-failed` or the
browser retry action.

The Markdown report is generated only from the manifest. It reports counts,
assignments, per-file outcomes, source IDs, revision warnings, cleanup-stop
state, and retry actions. It is operational evidence; the Ledger and source
registry remain canonical.

## OCR deferral

A PDF for which the current adapter exposes no text is classified
`needs_ocr`. The report says only that no extractable text was exposed, that
the file was not ingested as searchable knowledge, and that OCR is required
before processing. It does not claim reliable image-only detection. The
original, processed JSON, embeddings, and concepts are removed and verified.

## Offline scale and retrieval evidence

The blocking generated 100-document command is:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  .venv/flightline-py312/bin/python -m unittest \
  tests.test_bulk_ingestion_scale -v
```

Observed August 7, 2026 after the bounded audit corrections: one test passed in
3.051 seconds (5.62 seconds wall time). A direct evidence run processed exactly
100 files in 2.692 seconds (4.73 seconds wall time): first pass 95 succeeded, 2
skipped, 1 duplicate, 1 `needs_ocr`, and 1 recoverable failure; explicit retry
ended with 96 succeeded, 2 skipped, 1 duplicate, 1 `needs_ocr`, and 0 failed.
It covered every supported adapter, course default/override, possible revision,
interruption/resume, explicit retry, survival of earlier successes, and absent
failed/`needs_ocr` artifacts.

The documented 500-document soak is:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  .venv/flightline-py312/bin/python -m tools.bulk_ingestion_soak --count 500
```

Observed August 7, 2026 after the bounded audit corrections: 500 succeeded, 0
skipped, 0 duplicate, 0 `needs_ocr`, and 0 failed in 48.378 seconds of harness
time (52.97 seconds wall time). The run used generated fixtures, deterministic
embeddings, disposable originals and Ledger, and no model or external product
service.

The fixed retrieval smoke retained the disposable baseline source and found a
representative imported source. On the 100-document evidence run, elapsed
text retrieval moved from 0.000293 seconds before ingestion to 0.009273 seconds
after ingestion. On the corrected 500-document soak it moved from 0.000307
seconds to 0.074956 seconds. These are local diagnostics, not recall thresholds,
latency budgets, production promises, telemetry, or retrieval optimization.

## Assurance and next gate

Final local validation after the bounded audit corrections on August 7, 2026
passed 148 focused ingestion, contract, Library, and architecture tests; the
blocking 100-document test; the
500-document soak; the focused ingestion Ruff check passed; bytecode
compilation; dependency integrity; the
unchanged Ledger migration sequence `[1, 2, 3]`; diff whitespace checks; and
the repository-wide 276-test suite. Expected exception-path diagnostic logs
and the PyMuPDF layout suggestion were informational; no test failed or
skipped.

No Crew Chief audit is claimed. Crew Chief remains unimplemented. The next
gate is Maverick's review and approval decision. Commit, push, merge, canonical
numbering, naming, and mission completion remain separately unauthorized.
