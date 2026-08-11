# Landing Signal Officer v1

LSO converts a final, unchanged Crew Chief `PASS` into one exact conditional
closeout gate. It does not run Crew Chief and does not infer authorization.

## 1. Freeze the engineering evidence

Run all required validation and encode the exact successful commands in a
`closeout-evidence-v1.schema.json` document. Prepare and execute Crew Chief
under its own runbook and authorization. Resolve every finding. LSO requires
the final report to be `PASS` with zero findings and reconciliation to be both
complete and approval-ready.

## 2. Prepare the closeout plan

Preparation is non-mutating. Supply the working-tree Crew Chief envelope,
report, reconciliation, active mission record, two commit messages, final
record text, and a new external output directory:

```text
PYTHONDONTWRITEBYTECODE=1 python -m tools.lso prepare \
  --repository /absolute/repository \
  --mission-record /absolute/repository/docs/missions/<mission>/mission.md \
  --envelope /absolute/audit-envelope.json \
  --report /absolute/crew-chief-report.json \
  --reconciliation /absolute/reconciliation.json \
  --implementation-commit-message "Implement bounded mission" \
  --closeout-commit-message "Complete bounded mission records" \
  --final-authorization-gate "closed by Maverick" \
  --next-gate "Maverick selects and authorizes a mission." \
  --final-approval-scope "Approved exact conditional closeout plan ..." \
  --output-root /private/tmp/wingman-lso-plan-<id>
```

LSO returns `closeout-plan.json` and a human-readable `approval-card.md`. Any
subsequent byte, Git, audit, test, mission, remote, or target change invalidates
the plan. Before issuing either artifact, preparation stages the exact audited
paths in a temporary index and runs Git's staged-byte whitespace check there,
including for files that are still untracked in the real working tree.

## 3. Record exact authorization

Maverick must approve the complete text printed in the approval card. Preserve
that exact UTF-8 text in an external file, then record the package-bound
receipt. Receipt creation does not execute a Git operation:

```text
PYTHONDONTWRITEBYTECODE=1 python -m tools.lso authorize \
  /private/tmp/wingman-lso-plan-<id>/closeout-plan.json \
  /absolute/authorization.txt \
  --output /private/tmp/wingman-lso-plan-<id>/authorization-receipt.json
```

## 4. Execute once

Execution requires both the receipt and the explicit CLI acknowledgement:

```text
PYTHONDONTWRITEBYTECODE=1 python -m tools.lso execute \
  /private/tmp/wingman-lso-plan-<id>/closeout-plan.json \
  /private/tmp/wingman-lso-plan-<id>/authorization-receipt.json \
  --execute
```

The receipt is consumed before the first repository mutation. The marker is
stored under the repository's Git common directory, scoped by repository and
receipt identity, so every linked worktree observes the same consumption state
and copying the external plan package cannot reset it. There is no automatic
retry. LSO uses ordinary non-force atomic pushes, first publishing the exact
audited implementation and then its generated completion record. Every action
is recorded in an external execution report.

Immediately before real staging, LSO snapshots the exact worktree index. A
staging or pre-commit verification failure restores and verifies that index
before LSO reports `FAILED`. If exact restoration also fails, LSO reports
`PARTIAL` with both errors and stops with the receipt consumed.

`COMPLETE` is the only success state. `FAILED` and `PARTIAL` stop the workflow;
preserve the report, diagnose the exact state, and obtain a new plan and
authorization. Never manually edit a receipt, reuse a consumed plan, weaken a
check, or represent partial publication as completion.

## Codex stop integration

LSO v1 deliberately does not install a global Stop hook. The deterministic
execution report is the enforcement source: an agent may say `MISSION
COMPLETE` only when a validated report says `COMPLETE`. A later hook deployment
may enforce that rule automatically after its exact configuration and trust
boundary are separately reviewed and approved.
