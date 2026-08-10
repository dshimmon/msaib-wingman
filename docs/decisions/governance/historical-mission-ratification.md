# GOV-003 — Historical Mission Ratification and Record Authority

<!-- wingman-decision-metadata
{
  "schema_version": 1,
  "id": "GOV-003",
  "title": "Historical Mission Ratification and Record Authority",
  "namespaces": ["governance"],
  "status": "accepted",
  "date": "2026-08-07",
  "authority": "Maverick",
  "scope": "Retrospective completion ratification for the missions listed at bf73134",
  "approval_evidence": "Maverick's 2026-08-07 correction-engineer instruction explicitly ratifying all 30 completed missions",
  "ratified_missions": [
    {"id": "atlas/briefing", "implementation_commits": ["109dc2a3e2502d3142dcba8c7c94fa2e4a191a0f"]},
    {"id": "atlas/bulk-ingestion", "implementation_commits": ["c88a226ac13e69e235ed5df1347a3872e3330554"]},
    {"id": "atlas/cockpit", "implementation_commits": ["06ec9efbc9598607e5e5c2d2f2e035a467618938"]},
    {"id": "atlas/continuity", "implementation_commits": ["c284ba2890e0bfcef0dc8d6f7db8c5e2d8f40f1a"]},
    {"id": "atlas/intake", "implementation_commits": ["d961bddaaaa2542e69ad3f5abab25437e12c1e26"]},
    {"id": "atlas/library", "implementation_commits": ["178bce8661f7eefff6f6911d6e96483a429e7c42"]},
    {"id": "atlas/traceback", "implementation_commits": ["215501a47a70df4a45c278e09cb1c68039b68274"]},
    {"id": "operations/flightline/setup", "implementation_commits": ["ea9f3e0baa1ad0eddba3cc8da358d7be4c76fd3c"]},
    {"id": "wingman-os/airframe", "implementation_commits": ["e1570b0c0d759933eaa0d2d0b48839051337d441", "7c3402cce5e9a476d18e3b23b8248a9d4793b562"]},
    {"id": "wingman-os/checkpoint", "implementation_commits": ["390cfc587ddd568d01fbe114f0433b3ea5286737"]},
    {"id": "wingman-os/decision-maker", "implementation_commits": ["5d9ea052016371e2d219a79e252630b0fa3bbbe7"]},
    {"id": "wingman-os/external-knowledge", "implementation_commits": ["bd4fdb822da0129ef50781f52fe9553382ede5c2"]},
    {"id": "wingman-os/first-contact", "implementation_commits": ["938c8d2a8207388ca9082d053c1f1c6e59f61cac"]},
    {"id": "wingman-os/first-document", "implementation_commits": ["6d01c007891e84f9525d52eeb246840ee361c1e2"]},
    {"id": "wingman-os/first-flight", "implementation_commits": ["010055130d25d257c7501ad2543ab9dd87b90c46"]},
    {"id": "wingman-os/foundation", "implementation_commits": ["58f074ca67673a10e9f65b476bcf8e39ae6e973d", "24db23c1649a08b3e9ea7af194f07481caca3042"]},
    {"id": "wingman-os/hardpoints", "implementation_commits": ["2b3b9a63f77e14e7baf8e44b8e43e5452b7b248a"]},
    {"id": "wingman-os/intelligent-responses", "implementation_commits": ["d6dcfd19f526f1cd65d664ea0f43435211ee5f04"]},
    {"id": "wingman-os/knowledge-base", "implementation_commits": ["ae42c0ebd54caf8682da31b335c9c83cffe11d29"]},
    {"id": "wingman-os/knowledge-memory", "implementation_commits": ["e0a633e603ae696c546f0822b61c6beb33dfbafb"]},
    {"id": "wingman-os/knowledge-representation", "implementation_commits": ["55684ea5dac628eae3546221f7aa008c37a6784c"]},
    {"id": "wingman-os/knowledge-retrieval", "implementation_commits": ["ec697da771f3b95725536eca0ecb594c83f12ede"]},
    {"id": "wingman-os/ledger", "implementation_commits": ["440fb41235146f4d2366f343d22b5f0f8e764506", "db6ec6fe008d619b9cc2e1701ce376d5eab08987", "cd64f483a005d7f0526a2167fc44134a1653ec6b", "d52dfed411baca66d47e0b3650ebd355b4139a6d"]},
    {"id": "wingman-os/modular-wingman", "implementation_commits": ["6d15eb06764c06e5f16ab1ac08753879e5a64dc5"]},
    {"id": "wingman-os/priority", "implementation_commits": ["e5095a2e30c52fb9797176b7f9d4b5a78a27a7aa"]},
    {"id": "wingman-os/prompt-optimizer", "implementation_commits": ["22b418bc460ba03a6520e990699b9dc52ab472cd"]},
    {"id": "wingman-os/semantic", "implementation_commits": ["9269e6a4f90d41714d0efb5f949798e4fe0768d3"]},
    {"id": "wingman-os/structured-retrieval", "implementation_commits": ["df78df7d9ac15882b92c3e3464e898e707c5549a"]},
    {"id": "wingman-os/unified-intelligence", "implementation_commits": ["7c4bf5c26cd404ad83f89e3125fb11d5d912a420"]},
    {"id": "wingman-os/unified-knowledge", "implementation_commits": ["7cb6bfa2d5bdde6c6bcadc60f1feeb9fb28c66a7"]}
  ],
  "supersedes": [],
  "superseded_by": null
}
-->

## Decision

Maverick retrospectively ratified completion of the missions listed below on
2026-08-07. The list is preserved as historical evidence rather than enforced
as a permanent repository-wide mission count. This ratification explicitly
includes `atlas/bulk-ingestion` and `wingman-os/prompt-optimizer`.

Each mission's `mission.md` is its sole canonical mission-status surface.
Retained journals are noncanonical, time-bound historical evidence and may not
control lifecycle, approval, commit, publication, or next-gate state.

Completion, implementation, review, audit, commit, push, and merge remain
distinct states. This decision ratifies completion only. `pushed` and `merged`
booleans remain controlled by available Git evidence and are not changed by
retrospective completion ratification.

## Ratified missions and implementation commits

| Mission | Implementation commits |
|---|---|
| `atlas/briefing` | `109dc2a3e2502d3142dcba8c7c94fa2e4a191a0f` |
| `atlas/bulk-ingestion` | `c88a226ac13e69e235ed5df1347a3872e3330554` |
| `atlas/cockpit` | `06ec9efbc9598607e5e5c2d2f2e035a467618938` |
| `atlas/continuity` | `c284ba2890e0bfcef0dc8d6f7db8c5e2d8f40f1a` |
| `atlas/intake` | `d961bddaaaa2542e69ad3f5abab25437e12c1e26` |
| `atlas/library` | `178bce8661f7eefff6f6911d6e96483a429e7c42` |
| `atlas/traceback` | `215501a47a70df4a45c278e09cb1c68039b68274` |
| `operations/flightline/setup` | `ea9f3e0baa1ad0eddba3cc8da358d7be4c76fd3c` |
| `wingman-os/airframe` | `e1570b0c0d759933eaa0d2d0b48839051337d441`, `7c3402cce5e9a476d18e3b23b8248a9d4793b562` |
| `wingman-os/checkpoint` | `390cfc587ddd568d01fbe114f0433b3ea5286737` |
| `wingman-os/decision-maker` | `5d9ea052016371e2d219a79e252630b0fa3bbbe7` |
| `wingman-os/external-knowledge` | `bd4fdb822da0129ef50781f52fe9553382ede5c2` |
| `wingman-os/first-contact` | `938c8d2a8207388ca9082d053c1f1c6e59f61cac` |
| `wingman-os/first-document` | `6d01c007891e84f9525d52eeb246840ee361c1e2` |
| `wingman-os/first-flight` | `010055130d25d257c7501ad2543ab9dd87b90c46` |
| `wingman-os/foundation` | `58f074ca67673a10e9f65b476bcf8e39ae6e973d`, `24db23c1649a08b3e9ea7af194f07481caca3042` |
| `wingman-os/hardpoints` | `2b3b9a63f77e14e7baf8e44b8e43e5452b7b248a` |
| `wingman-os/intelligent-responses` | `d6dcfd19f526f1cd65d664ea0f43435211ee5f04` |
| `wingman-os/knowledge-base` | `ae42c0ebd54caf8682da31b335c9c83cffe11d29` |
| `wingman-os/knowledge-memory` | `e0a633e603ae696c546f0822b61c6beb33dfbafb` |
| `wingman-os/knowledge-representation` | `55684ea5dac628eae3546221f7aa008c37a6784c` |
| `wingman-os/knowledge-retrieval` | `ec697da771f3b95725536eca0ecb594c83f12ede` |
| `wingman-os/ledger` | `440fb41235146f4d2366f343d22b5f0f8e764506`, `db6ec6fe008d619b9cc2e1701ce376d5eab08987`, `cd64f483a005d7f0526a2167fc44134a1653ec6b`, `d52dfed411baca66d47e0b3650ebd355b4139a6d` |
| `wingman-os/modular-wingman` | `6d15eb06764c06e5f16ab1ac08753879e5a64dc5` |
| `wingman-os/priority` | `e5095a2e30c52fb9797176b7f9d4b5a78a27a7aa` |
| `wingman-os/prompt-optimizer` | `22b418bc460ba03a6520e990699b9dc52ab472cd` |
| `wingman-os/semantic` | `9269e6a4f90d41714d0efb5f949798e4fe0768d3` |
| `wingman-os/structured-retrieval` | `df78df7d9ac15882b92c3e3464e898e707c5549a` |
| `wingman-os/unified-intelligence` | `7c4bf5c26cd404ad83f89e3125fb11d5d912a420` |
| `wingman-os/unified-knowledge` | `7cb6bfa2d5bdde6c6bcadc60f1feeb9fb28c66a7` |

## Consequences

The listed canonical mission records cite this decision as their dated
completion authority. Journals may preserve or summarize substantive history;
the mission record controls when statements conflict. Publication evidence
continues to be evaluated from cached remote-tracking refs and the canonical
cached merge target.
