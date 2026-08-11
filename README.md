# MSAIB Wingman

Wingman is a source-grounded knowledge operating system. Atlas is the
academic product currently composed on it.

Repository work begins with [`AGENTS.md`](AGENTS.md). The generated
[`CURRENT_MISSION.md`](CURRENT_MISSION.md) then identifies current authority,
the official mission record, last completed work, and next gate. README is not
a mission-status authority.

## Runtime

Use Python 3.10 or newer and install `requirements.txt`.

Canonical Atlas terminal:

```bash
PYTHONPATH=src python3 -m products.atlas.main
```

The historical `python3 src/main.py` entry point remains supported through a
registered compatibility facade.

Canonical Atlas Streamlit composition:

```bash
python3 -m streamlit run src/products/atlas/streamlit_app.py
```

Preview a bounded folder batch (non-recursive by default):

```bash
PYTHONPATH=src python3 -m products.atlas.bulk_ingestion ./selected-folder \
  --course-id AI-101
```

Add `--execute` only after reviewing the deterministic per-file preview. Use
`--recursive` explicitly to include nested folders. Browser and folder intake
support PDF, DOCX, XLSX, PPTX, CSV, TXT, MD, and MARKDOWN files.

Run the offline suite:

```bash
python3 -m unittest discover -s tests -t . -p 'test_*.py'
```

When no `OPENAI_API_KEY` is supplied, the test package establishes a
nonsecret, test-only placeholder before importing modules that construct the
OpenAI client and disables dotenv loading by default. It never replaces a
caller-supplied value and is not an application default; offline tests mock API
behavior rather than making real OpenAI requests.

`tests/products/atlas/run_retrieval_tests.py` is a separate API-backed
diagnostic.

## Architecture and governance

[`docs/wingman-os/architecture.md`](docs/wingman-os/architecture.md) records the
current Core, Shared Product Framework, and product boundary.
`src/wingman/shared/airframe_manifest.py` is the matching machine-readable
ownership inventory.

[`docs/wingman-os/product-contract-v1.md`](docs/wingman-os/product-contract-v1.md)
defines the explicit typed Hardpoints seam. Atlas owns its immutable definition
and the closed production registry; Shared applies an explicit Product Context
to neutral Core ingestion and retrieval. The attachment procedure is in
[`docs/runbooks/product-attachment.md`](docs/runbooks/product-attachment.md).

Documentation homes are indexed in [`docs/README.md`](docs/README.md).
Authoritative missions live under [`docs/missions/`](docs/missions/), enduring
decisions under [`docs/decisions/`](docs/decisions/), and approved sequence in
[`docs/roadmap.md`](docs/roadmap.md).

Wingman Core now supports Ledger schema versions 3 and 4. Fresh empty
databases initialize at version 4; existing version-3 databases remain on
version 3 unless an exact governed transition is separately authorized. The
private source repository preserves version-3 compatibility while version 4
stores product-owned source fields only in opaque metadata.

The governed transition, locking, backup, restoration, dry-run, rollback, and
postflight mechanisms are implemented and published. They are not permission
to operate on the default or a live Ledger. See the
[Ledger Transition mission record](docs/missions/wingman-os/ledger-transition/mission.md),
[runbook](docs/runbooks/ledger-transition.md), and
[DATA-001](docs/decisions/security/ledger-and-data-safety.md) for the remaining
Assurance v1, exact-package, receipt, review, and Maverick approval gates.
