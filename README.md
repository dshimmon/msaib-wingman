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

Run the offline suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

`tests/run_retrieval_tests.py` is a separate API-backed diagnostic.

## Airframe boundary

[`docs/architecture/Airframe.md`](docs/architecture/Airframe.md) records
the current Core, Shared Product Framework, Atlas, and Product Configuration
boundary. `src/airframe_manifest.py` is the matching machine-readable
inventory used by static architecture tests.

The Ledger remains physically at migrations 1–3. The temporary `program`
and `academic_year` columns are translated privately by the source
repository into generic metadata; metadata wins if both representations
contain a key, and reads do not mutate storage.

Physical schema conversion, authorization, locking, backup, and restoration
belong to the future Ledger Transition after Assurance v1. Mission 027
contains no executable transition procedure.
