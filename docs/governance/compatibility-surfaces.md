# Compatibility Surface Register

[ARCH-004](../decisions/architecture/compatibility-facades.md) is the official
decision. The machine-readable registry is
`src/wingman/shared/compatibility.py`; governance validation requires every
historical facade to be registered and tested.

Each entry records:

- historical import or entry point;
- canonical target;
- owner (`wingman-core`, `shared-product-framework`, or `atlas`);
- reason retained;
- supported callers; and
- objective removal condition.

The physical package migration retains all previously supported flat runtime
module imports, the `ledger.*` package imports, terminal and Streamlit script
entry points, the document and bulk-ingestion CLIs, and the existing
monkeypatch surfaces. A facade aliases the canonical module object so a patch
through the historical name affects the implementation used by canonical
callers.

No facade may own product policy or be removed merely because canonical code
no longer imports it. Removal requires an approved caller migration, an
inventory proving supported callers moved, replacement entry-point evidence,
and explicit Maverick authorization.
