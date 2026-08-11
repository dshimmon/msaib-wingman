# Atlas Production Contrast Correction — Evidence

The adjacent [`mission.md`](mission.md) is the authoritative lifecycle record.
This note records corrective evidence and does not authorize commit,
publication, deployment, live-data mutation, or mission completion.

## Baseline and reproduction

- GitHub `origin/main` and the isolated branch baseline were
  `0d40ea86a47725dc6a1a47d7f9ce43e7c141ff93`.
- Reproduction used Streamlit `1.61.1`, the version observed in deployment
  preflight, with an offline placeholder credential and an isolated temporary
  Ledger path.
- In viewer Theme=Dark, the main warning paragraph computed to
  `rgb(255, 255, 194)` and the main info paragraph to
  `rgb(61, 157, 243)` while Atlas retained pale light alert surfaces. The
  sidebar warning remained readable at `rgb(22, 37, 58)` because the original
  CSS already pinned that narrower case.
- The before screenshot visibly records the disappearing main warning and
  sidebar navigation label.

## Corrective boundary

Only `src/products/atlas/ui/styles.py` changes application behavior. It pins
theme-independent foregrounds for Atlas light surfaces using stable Streamlit
data test IDs and semantic descendants. The contract covers alerts, headings,
body text, captions, labels, links, metrics, text/select/upload controls, Chat,
primary and secondary buttons, nested button text, disabled states, and a
two-color focus indicator. Later, more specific rules preserve intentional
white brand and enabled/disabled primary-button text.

Focused regression tests in `tests/products/atlas/test_ui_styles.py` assert
the selectors, descendant overrides, absence of generated/hash class names,
and WCAG AA contrast ratios for ordinary, muted, link, primary, and disabled
text tokens.

## Browser verification

Real browser verification used the Streamlit viewer's visible Theme menu, not
storage manipulation. Theme=Light and Theme=Dark were each checked at
1440x900 desktop and 390x844 mobile. Final computed foregrounds included:

- main warning and info text: `rgb(22, 37, 58)`;
- sidebar warning, navigation, headings/body, labels, and secondary controls:
  the intended Atlas ink/navy/muted tokens with opacity `1`;
- primary-button nested text and Atlas brand text: `rgb(255, 255, 255)`;
- disabled primary control: white text on `rgb(102, 112, 133)`, opacity `1`;
- text area and Chat input: `rgb(22, 37, 58)` on white, with placeholder
  `rgb(82, 98, 120)` at opacity `1`; and
- keyboard-focused primary control: 3px white inner outline plus 6px
  `rgb(0, 94, 168)` outer ring.

The fresh final browser console contained zero errors. No live key was read or
recorded, no model/product network call was made, and no live Ledger or
repository `data/**` path was used.

Selected external screenshots and SHA-256 values:

- before Dark desktop 1440x900:
  `b8265f5d7d9b38419a254b7d847f111004d60f7b7123d715aeab93ad67a55344`;
- after Dark desktop 1440x900:
  `ba537986b634ec07de552cbdc10a7e5c62c5b811024a9cd68f08ae037c365482`;
- after Light desktop 1440x900:
  `10a445d2e3f4db8d5a1dac9f856892e52b0a49e63cdd305a4eef8484d1141b89`;
- after Dark mobile 390x844:
  `57f8021fde83660971731d0d16518bfe7979433022ca24068ef707b488b23aef`;
- after Light mobile 390x844:
  `6c45d8ab0f1b673a12f8459855f97f558fac7cb5f9446f8b358e21b8f276610c`;
  and
- after Dark info desktop 1280x720:
  `ff3038f66e054439516eed762d1bc1b0f4fdcde2e5cb764e2fd7246a968627b4`.

## Validation

- Focused Atlas/UI suite: **65/65 passed** in 4.684 seconds under Streamlit
  1.61.1.
- LSO focused suite: **11/11 passed** in 40.657 seconds.
- Repository governance validation: passed.
- Affected Ruff, Black, compilation, unstaged whitespace, and staged
  whitespace checks: passed.
- Complete credential-free offline discovery ran **492 tests** in 223.826
  seconds: **490 passed and 2 failed**. Both failures reproduce unchanged on
  the clean `0d40ea86` baseline and are pre-existing hard-coded governance
  assertions in `tests/governance/test_repository_governance.py`:
  `test_latest_completed_uses_final_recorded_commit_time` expects Atlas instead
  of canonical latest completion LSO, and
  `test_lso_is_the_active_portfolio_primary` expects LSO active while canonical
  generated state was between missions. This presentation-only correction
  does not alter or conceal those unrelated assertions.

The first offline-discovery invocation omitted shell quoting around the
`test_*.py` pattern and was rejected by zsh before tests ran. The quoted rerun
is the recorded 492-test result above.

## Current gate

Freeze these exact bytes and evidence for Crew Chief. Every finding must be
resolved, disputed with exact evidence, or escalated. Only a zero-finding
`PASS` with complete approval-ready reconciliation may proceed to LSO plan
preparation.
