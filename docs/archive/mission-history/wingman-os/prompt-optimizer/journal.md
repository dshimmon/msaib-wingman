<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/wingman-os/prompt-optimizer/mission.md",
  "archived_from": "docs/missions/wingman-os/prompt-optimizer/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> mission record is [`docs/missions/wingman-os/prompt-optimizer/mission.md`](../../../../missions/wingman-os/prompt-optimizer/mission.md).
> Every lifecycle, approval, commit, publication, and next-gate claim in
> the preserved body below is time-bound historical evidence and is not
> authoritative current status.

# Wingman Optimizes Prompts

**Canonical mission number:** Not assigned by Maverick

**Canonical call sign:** Not assigned by Maverick

**Product:** Wingman OS; exposed by the current Atlas-owned Streamlit shell

**Authority:** Maverick's August 7, 2026 instruction authorized the bounded
implementation and local offline validation described here. Maverick
subsequently authorized the exact bounded Prompt Optimizer commit. Push,
merge, deployment, and real model requests remain unauthorized.

**Implementation state:** Implemented, locally tested, staged as an exact
seven-file bounded snapshot, and approved for commit. This journal was updated
after staged-snapshot validation and frozen before commit creation; push,
merge, and any declaration of completion remain separate gates.

## Objective and user value

Prompt Optimizer turns a user-authored draft into a clearer, more structured
prompt without answering it, inventing requirements, or changing its intent.
The complete Streamlit workflow must be reliable: blank input cannot invoke the
model, successful output is visibly tied to its source prompt, stale output is
invalidated, failures cannot expose an older result, and a user can move the
optimized result back into the editor without a Streamlit state exception.

## Verified starting repository state

- Repository root:
  `/Users/davidshimmon/Developer/Wingman/msaib-wingman`.
- Branch: `codex/Audit`.
- HEAD: `2b3b9a63f77e14e7baf8e44b8e43e5452b7b248a`.
- The branch had no configured upstream. Cached `origin/main` was six commits
  behind HEAD and zero commits ahead of it; no fetch was performed.
- Mission 028 Hardpoints was already approved, committed, and closed at HEAD;
  it remained unpushed and unmerged according to its canonical journal.
- The working tree was already materially dirty. It contained unrelated
  Finder metadata, Flightline corrections, and a large unnumbered
  bulk-ingestion proposal.
- Bulk ingestion already modified `src/streamlit_app.py`,
  `src/airframe_manifest.py`, `docs/architecture/Airframe.md`, and
  `docs/architecture/Product-Contract-v1.md`. Those changes were preserved.
- The initial Prompt Optimizer implementation already existed as untracked
  `src/prompt_optimizer.py` and `tests/test_prompt_optimizer.py`, with related
  hunks in the overlapping Streamlit and Airframe files.
- The initial service tests passed, but there were no Streamlit application
  tests. Reproduction through Streamlit `AppTest` confirmed that clicking
  **Edit Optimized Prompt** raised `StreamlitAPIException` because the code
  changed `st.session_state.prompt_optimizer_input` after instantiating the
  keyed text-area widget.

## Approved scope

This bounded implementation may:

- repair the keyed-widget state transition;
- invalidate stale output on source change and before every model attempt;
- preserve the existing OpenAI client, `gpt-5`, and intent-preserving model
  instructions;
- add fully offline service and Streamlit `AppTest` regressions;
- document and test the Product Contract v1 boundary;
- update the existing Airframe ownership explanation without changing the
  unrelated bulk-ingestion content; and
- create this unnumbered journal.

## Explicit exclusions

This implementation does not:

- assign or imply a mission number or canonical call sign;
- add a Product Contract field, capability, version, registry entry, or
  product-controlled optimizer configuration;
- add prompt history, persistence, product-specific templates, model selection,
  telemetry, authentication, deployment, or another product;
- change the Ledger, migrations, live data, source registry, or bulk-ingestion
  behavior;
- use a real API credential, make a real model or network request, or claim
  live-model quality validation; or
- push, merge, fetch, deploy, or declare the work complete.

## Architectural context and Product Contract decision

Product Contract v1 is the authoritative product-to-Wingman attachment seam.
It controls product identity, product capabilities, product-owned records and
metadata rules, retrieval and Briefing composition, product defaults, and
bounded product UI vocabulary. Atlas currently declares the Chat, Briefing,
and Library workspace terms.

Prompt Optimizer is product-neutral. Its Core service receives only
user-authored text, imports the existing Core OpenAI client, contains no Atlas
or other product vocabulary, and receives no `ProductContext`. Products do not
supply, select, or configure its behavior.

The smallest coherent design is therefore an explicitly declared global shell
workspace. The Atlas-owned Streamlit composition root now separates
`GLOBAL_SHELL_WORKSPACES` from the three contract-declared Atlas workspaces.
Airframe and Product Contract documentation state the boundary, and a
regression proves the optimizer is Core-owned, absent from
`ProductCapability`, and absent from Atlas's contract workspace terms.

Adding a capability would imply that each product controls or opts into the
optimizer when no current behavior supports that claim. Product-specific
optimizer settings would be a different design and require a separately
approved Product Contract change.

## Implementation summary

### Safe editor transition

`edit_optimized_prompt()` is registered as the edit button's `on_click`
callback. Streamlit executes that callback before the next script rerun and
before the keyed text area is instantiated. The callback copies the optimized
text into `prompt_optimizer_input` and clears the displayed result. It does not
force an additional rerun.

### Stale-result invalidation

`clear_prompt_optimizer_result()` is the text area's `on_change` callback. Any
source-prompt change removes the prior result before rendering the next app
state. The optimize action also clears the result immediately before calling
the service. A failed retry therefore leaves an error and no optimized output,
even when the source text did not change.

### Service behavior

The service still:

- uses the existing `openai_client.client` and model `gpt-5`;
- strips and rejects blank input before a client call;
- instructs the model to preserve facts, constraints, quotes, placeholders,
  and intent while improving clarity and structure;
- forbids answering the prompt, inventing requirements, silently resolving
  ambiguity, or returning commentary; and
- rejects blank or non-text model output with a controlled `RuntimeError`.

### Application regression coverage

Streamlit `AppTest` now exercises the actual application file and rerun model.
All optimization calls are patched at the service boundary. Coverage includes:

- navigation to Prompt Optimizer;
- a disabled action for blank input;
- an enabled action for nonblank input;
- successful mocked optimization and result rendering;
- returning the result to the keyed editor without an exception;
- removal of stale output after source-prompt changes;
- removal of prior output before a same-prompt failed retry; and
- the global-shell/Product Contract boundary.

## Files in the Prompt Optimizer feature delta

| File | Treatment in this bounded implementation |
|---|---|
| `src/prompt_optimizer.py` | Existing untracked service corrected to reject non-text empty output safely; retains existing client, model, and instruction policy. |
| `src/openai_client.py` | Existing Core dependency inspected and preserved; no task change. |
| `src/streamlit_app.py` | Existing overlapping file updated only in Prompt Optimizer declarations, callbacks, workspace rendering, and navigation declaration. |
| `tests/test_prompt_optimizer.py` | Existing untracked service tests extended with five Streamlit UI/boundary tests. |
| `src/airframe_manifest.py` | Inspected and preserved; its pre-existing `prompt_optimizer: CORE` ownership entry was already correct. |
| `docs/architecture/Airframe.md` | Existing overlapping document updated with the explicit Core/global-shell boundary and product-specific prompt wording. |
| `docs/architecture/Product-Contract-v1.md` | Existing overlapping document updated to distinguish product workspace vocabulary from neutral global shell workspaces. No contract implementation changed. |
| `src/product_contract.py` and `src/product_config.py` | Authoritative contract and Atlas definition inspected and preserved; no Prompt Optimizer field, capability, or product declaration was added. |
| `tests/test_architecture_boundaries.py` and `tests/test_product_contract.py` | Existing boundary suites inspected, preserved, and run; the Prompt Optimizer-specific global-shell assertion lives with the feature tests. |
| `docs/journal/Wingman-Optimizes-Prompts.md` | Added as this unnumbered canonical implementation journal. |

Repository-wide reference search found no additional file containing Prompt
Optimizer symbols, labels, or ownership declarations.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Blank source input cannot invoke optimization. | PASS | Service call rejection and disabled-button AppTest. |
| Nonblank source input enables optimization. | PASS | Streamlit AppTest. |
| Successful offline-mocked output is displayed. | PASS | Streamlit AppTest inspects the rendered code element. |
| Edit returns output to the editor and clears the result without exception. | PASS | Streamlit AppTest covers the previously failing click and asserts no app exception. |
| Source changes invalidate prior output. | PASS | Streamlit text-area change AppTest. |
| Every attempt clears prior output, including failure. | PASS | Same-source success-then-failure AppTest. |
| Product Contract v1 is not silently bypassed or weakened. | PASS | Explicit global-shell documentation, unchanged contract implementation, boundary test, and Airframe suite. |
| Core contains no product-specific optimizer vocabulary. | PASS | Airframe static architecture tests. |
| Existing client, `gpt-5`, and intent-preserving policy remain. | PASS | Service code and unit assertions. |

## Exact validation evidence

All commands used the provisioned Python 3.12 environment, disabled dotenv,
used an inert placeholder key, and made no model request.

### Final staged-snapshot validation

The final index was exported with `git checkout-index --all` to
`/private/tmp/wingman-prompt-optimizer-staged-pkHQEA`. The focused, boundary,
full-suite, and compilation commands below were then repeated from that
directory with the repository's provisioned Python executable. This isolated
the exact proposed commit from every unrelated working-tree change.

```bash
PYTHONPATH=src PYTHON_DOTENV_DISABLED=1 \
  OPENAI_API_KEY=prompt-optimizer-offline-placeholder \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  /Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
  -m unittest tests.test_prompt_optimizer -v

PYTHONPATH=src PYTHON_DOTENV_DISABLED=1 \
  OPENAI_API_KEY=prompt-optimizer-offline-placeholder \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  /Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
  -m unittest tests.test_architecture_boundaries tests.test_product_contract -v

PYTHONPATH=src PYTHON_DOTENV_DISABLED=1 \
  OPENAI_API_KEY=prompt-optimizer-offline-placeholder \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  PYTHONPYCACHEPREFIX=/private/tmp/wingman-prompt-optimizer-staged-full-pycache-20260807 \
  /Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
  -m unittest discover -s tests -p 'test_*.py'

PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  PYTHONPYCACHEPREFIX=/private/tmp/wingman-prompt-optimizer-staged-compile-pycache-20260807 \
  /Users/davidshimmon/Developer/Wingman/msaib-wingman/.venv/flightline-py312/bin/python \
  -m py_compile src/prompt_optimizer.py src/streamlit_app.py \
  tests/test_prompt_optimizer.py
```

Results: focused `Ran 9 tests in 1.104s` — `OK`; architecture and
Product Contract `Ran 27 tests in 0.239s` — `OK`; complete offline snapshot
`Ran 231 tests in 2.957s` — `OK`; affected-source compilation exit `0`, no
output. No test failed or skipped. Expected negative-path diagnostic logs,
Streamlit missing-context and SWIG deprecation warnings, and the existing
PyMuPDF layout suggestion were informational.

### Focused Prompt Optimizer service and Streamlit UI

```bash
PYTHONPATH=src PYTHON_DOTENV_DISABLED=1 \
  OPENAI_API_KEY=prompt-optimizer-offline-placeholder \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  .venv/flightline-py312/bin/python -m unittest \
  tests.test_prompt_optimizer -v
```

Final post-overlap result: `Ran 9 tests in 0.985s` — `OK`.

### Airframe architecture and Product Contract v1

```bash
PYTHONPATH=src PYTHON_DOTENV_DISABLED=1 \
  OPENAI_API_KEY=prompt-optimizer-offline-placeholder \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  .venv/flightline-py312/bin/python -m unittest \
  tests.test_architecture_boundaries tests.test_product_contract -v
```

Final post-overlap result: `Ran 29 tests in 0.260s` — `OK`.

### Complete offline suite

```bash
PYTHONPATH=src PYTHON_DOTENV_DISABLED=1 \
  OPENAI_API_KEY=prompt-optimizer-offline-placeholder \
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  PYTHONPYCACHEPREFIX=/private/tmp/wingman-prompt-optimizer-final-full-pycache-20260807 \
  .venv/flightline-py312/bin/python -m unittest discover \
  -s tests -p 'test_*.py' -v
```

Final post-overlap result: `Ran 276 tests in 5.505s` — `OK`. No test failed
or skipped. This authoritative rerun occurred after the overlapping
bulk-ingestion files stopped changing; its one-test increase covers the
concurrent assignment-confirmation regression.
Expected negative-path diagnostic logs, Streamlit missing-context and SWIG
deprecation warnings, and the existing PyMuPDF layout suggestion were
informational.

### Affected-source compilation

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  PYTHONPYCACHEPREFIX=/private/tmp/wingman-prompt-optimizer-final-compile-pycache-20260807 \
  .venv/flightline-py312/bin/python -m py_compile \
  src/prompt_optimizer.py src/streamlit_app.py tests/test_prompt_optimizer.py
```

Result: exit `0`, no output.

### Diff and journal whitespace hygiene

```bash
git diff --check
```

Result: exit `0`, no output. Because the journal is untracked and therefore
outside ordinary `git diff`, it was also scanned directly:

```bash
rg -n '[[:blank:]]+$' docs/journal/Wingman-Optimizes-Prompts.md
```

Result: no matches.

## Validation limitations

- All service calls in Streamlit tests were mocked. No real model request,
  credential use, network call, or qualitative model-output review occurred.
- Streamlit `AppTest` exercised the real script, widget callbacks, session
  state, reruns, and rendered elements. A separate manual browser session was
  not used for this correction.
- The pre-fix reproduction intentionally produced the known
  `StreamlitAPIException`; no post-fix validation command failed.
- The complete suite validates the combined dirty working tree, including the
  overlapping unnumbered bulk-ingestion and Flightline corrections. A passing
  combined suite does not approve or attribute those unrelated changes to this
  implementation.

## Working-tree preservation and review state

No unrelated working file was overwritten or reverted. Initial staging
verification exposed unrelated bulk-ingestion entries in the index, so Codex
stopped before commit, restored those exact entries to their prior unstaged
state without changing the working files, reset the four mixed files in the
index, and reapplied only the Prompt Optimizer hunks. The final staged snapshot
contains seven files and no bulk-ingestion content. The overlapping
bulk-ingestion hunks in Streamlit, Airframe, the manifest, and the Product
Contract document remain present only in the working tree. Finder metadata and
Flightline changes remain untouched. No unrelated change was committed.

Codex performed implementation-time source and diff review, but that is not an
independent audit. Crew Chief remains unimplemented, and no independent Crew
Chief audit occurred. No fresh Independent Auditor was launched for this work.

## Status separation

| State | Status |
|---|---|
| Implemented | Yes, in the working tree. |
| Tested | Yes, locally and offline with the evidence above. |
| Reviewed | Codex self-review only; Maverick review pending. |
| Independently audited | No. |
| Approved | Yes for the bounded implementation and exact Prompt Optimizer commit. |
| Staged | Yes; exact seven-file snapshot independently exported and tested. |
| Committed | Authorized; this journal was frozen before commit creation. |
| Pushed | No. |
| Merged | No. |
| Mission-complete | No numbered mission exists, and Maverick has not declared this work complete. |

## Unresolved risks

- Real-model output quality and API/runtime behavior remain unverified by
  instruction; the service relies on the configured OpenAI account supporting
  `gpt-5`.
- The current shell has only Atlas as a production product. The global-shell
  decision is structurally tested but has not yet been exercised by a second
  production shell/product.
- The combined working tree contains other unapproved work. Any future commit
  must isolate and review exact authorized paths and overlapping hunks.
- Independent Crew Chief assurance remains pending.

## Exact next gate

After the authorized exact bounded commit, Codex reports the commit identity,
staged-snapshot validation, preserved unrelated work, and final Git status to
Maverick. Push, merge, deployment, naming, independent audit disposition, and
any declaration of completion remain later independent gates.
