# LSO Repository Runbook — Superseded

> **Historical pointer; not an active runbook.** Repository-owned LSO
> execution was removed on 2026-08-14 under [GOV-006](../decisions/governance/external-closeout.md).

The historical mission and evidence remain under
[`docs/missions/governance/lso/`](../missions/governance/lso/). The superseded
design decision remains in [GOV-005](../decisions/governance/lso-closeout.md).
Historical source and procedure bytes remain recoverable from Git before the
GOV-006 extraction.

Current work must use a conforming external landing capability under the
[External Development-Operations Closeout Contract](../governance/external-closeout-contract.md).
This repository provides no LSO executable, schema, receipt writer, staging
controller, or publication controller. If an external exact landing operator
is unavailable, report the landing gate as `BLOCKED`; do not substitute manual
Git mutation.
