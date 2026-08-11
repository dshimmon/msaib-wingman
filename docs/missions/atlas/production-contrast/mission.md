# Atlas Production Contrast Correction

<!-- wingman-mission-metadata
{
  "schema_version": 1,
  "id": "atlas/production-contrast",
  "legacy_aliases": [],
  "title": "Atlas Production Contrast Correction",
  "call_sign": "ATLAS-CONTRAST",
  "namespace": "atlas",
  "lifecycle": "active",
  "priority": "high",
  "portfolio_primary": true,
  "authorization_gate": "implementation, validation, Crew Chief review, and LSO preparation authorized; commit and publication require the exact later LSO approval",
  "approval_evidence": [
    {
      "date": "2026-08-11",
      "authority": "Maverick",
      "scope": "Authorized a live corrective pass for Atlas production contrast using current origin/main and Streamlit 1.61.1, limited to Atlas-scoped presentation styles, focused regression coverage, credential-free light/dark browser evidence, Crew Chief review, and LSO preparation; no commit, push, main update, deployment operation, secret access, or live-data mutation authorized."
    }
  ],
  "baseline_commit": "0d40ea86a47725dc6a1a47d7f9ce43e7c141ff93",
  "implementation_commits": [],
  "pushed": false,
  "merged": false,
  "official_decisions": [
    "docs/decisions/architecture/product-separation.md",
    "docs/decisions/governance/crew-chief-audit.md",
    "docs/decisions/governance/lso-closeout.md"
  ],
  "workstream": {
    "owner_session": "Codex Atlas live contrast correction authorized by Maverick on 2026-08-11",
    "branch": "codex/atlas-production-contrast-20260811",
    "worktree": "/private/tmp/wingman-atlas-contrast-20260811-MMF2V0/repository",
    "writable_scope": [
      "src/products/atlas/ui/styles.py",
      "tests/products/atlas/test_ui_styles.py",
      "docs/missions/atlas/production-contrast/",
      "CURRENT_MISSION.md",
      "docs/missions/README.md",
      "docs/governance/mission-control-context.md"
    ],
    "state": "implementation",
    "next_gate": "Complete isolated light/dark validation, freeze the exact Crew Chief package, reconcile a zero-finding PASS, then prepare the exact LSO approval card."
  },
  "next_gate": "Crew Chief reviews the frozen corrective subject; after PASS and approval-ready reconciliation, LSO prepares the exact single-use closeout approval card.",
  "supersedes": null,
  "superseded_by": null,
  "paused": false,
  "cancelled": false,
  "capability_health": "maintenance_pending"
}
-->

Lifecycle: **active corrective implementation**. Call sign:
**ATLAS-CONTRAST**.

## Objective

Correct the live Atlas Streamlit interface's theme-dependent foregrounds while
preserving its intentional light surfaces, white brand text, white primary
control text, behavior, architecture, data boundaries, and deployment
configuration.

## Reproduced defect

Under Streamlit 1.61.1 with the viewer theme set to Dark, Atlas continues to
render its custom light surfaces while Streamlit supplies dark-theme alert and
control foregrounds. The main warning paragraph computed to
`rgb(255, 255, 194)` and the main info paragraph to `rgb(61, 157, 243)` on
their pale alert containers. Sidebar warning text remained readable only
because a narrower existing rule already pinned its foreground.

## Authorized boundary

- Change Atlas-owned presentation styles only.
- Use stable Streamlit selectors and data test IDs, never generated or hashed
  class names.
- Pin readable foregrounds for Atlas light surfaces, alerts, ordinary text,
  labels, inputs, links, buttons, disabled controls, Chat, sidebar, metrics,
  and focus states in both viewer themes.
- Preserve intentional white brand and primary-control text.
- Add focused deterministic CSS-contract tests and capture credential-free
  desktop/mobile before-and-after browser evidence.
- Do not access the live OpenAI secret, change behavior or deployment
  configuration, mutate Ledger/live data, or publish without the later exact
  LSO authorization.

## Current gate

Implementation and validation may proceed. Crew Chief must review a frozen,
unchanged corrective package. Only a zero-finding `PASS` with complete,
approval-ready reconciliation may proceed to non-mutating LSO preparation.
