# MSAIB Wingman

Wingman is a source-grounded knowledge operating system. Atlas is the
academic product currently composed on it.

## Runtime

Use Python 3.10 or newer and install `requirements.txt`.

Terminal:

```bash
python3 src/main.py
```

Streamlit:

```bash
python3 -m streamlit run src/streamlit_app.py
```

Preview a bounded folder batch (non-recursive by default):

```bash
PYTHONPATH=src python3 -m bulk_ingestion ./selected-folder \
  --course-id AI-101
```

Add `--execute` only after reviewing the deterministic per-file preview. Use
`--recursive` explicitly to include nested folders. Browser and folder intake
support PDF, DOCX, XLSX, PPTX, CSV, TXT, MD, and MARKDOWN files.

Run the offline suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

`tests/run_retrieval_tests.py` is a separate API-backed diagnostic.

## Airframe and Product Contract

[`docs/architecture/Airframe.md`](docs/architecture/Airframe.md) records
the current Core, Shared Product Framework, Atlas, and Product Configuration
boundary. `src/airframe_manifest.py` is the matching machine-readable
inventory used by static architecture tests.

[`docs/architecture/Product-Contract-v1.md`](docs/architecture/Product-Contract-v1.md)
defines the explicit typed Hardpoints seam. Atlas owns its immutable definition
and the closed production registry; Shared applies an explicit Product Context
to neutral Core ingestion and retrieval. A concise attachment walkthrough is in
[`docs/Product-Attachment-Guide.md`](docs/Product-Attachment-Guide.md).

[`docs/journal/Wingman-Ingests-Documents-in-Bulk.md`](docs/journal/Wingman-Ingests-Documents-in-Bulk.md)
records the unnumbered bulk-ingestion architecture, folder safety, manifest,
retry, failure isolation, and offline scale procedures.

The Ledger remains physically at migrations 1–3. The temporary `program`
and `academic_year` columns are translated privately by the source
repository into generic metadata; metadata wins if both representations
contain a key, and reads do not mutate storage.

Physical schema conversion, authorization, locking, backup, and restoration
belong to the future Ledger Transition after Assurance v1. Mission 027
contains no executable transition procedure.
