"""Deterministic preparation, authorization, and execution for LSO v1."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from tools.crew_chief.controller import verify_envelope
from tools.crew_chief.core import parse_time as crew_parse_time
from tools.crew_chief.validation import validate_reconciliation, validate_report
from tools.lso.core import (
    CANARY,
    CLOSEOUT_ACTIONS,
    GENERATED_GOVERNANCE_PATHS,
    LSOError,
    SCHEMA_VERSION,
    artifact_binding,
    consume_once,
    ensure_external,
    isoformat,
    new_external_directory,
    parse_time,
    plan_identifier,
    read_json,
    receipt_identifier,
    report_identifier,
    sha256_bytes,
    utc_now,
    validate_instance,
    verify_artifact,
    write_canonical_json,
)
from tools.lso.git_ops import (
    branch_name,
    capture_index,
    changed_path_sets,
    expected_tree,
    git,
    git_state,
    is_ancestor,
    remote_head,
    remote_url_hash_input,
    receipt_consumption_directory,
    repository_identity,
    restore_index,
    resolve_commit,
    resolve_repository,
)


MISSION_MARKER = "wingman-mission-metadata"


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise LSOError(f"{label} must be a regular file: {path}")
    value = read_json(path)
    if not isinstance(value, dict):
        raise LSOError(f"{label} must be a JSON object")
    return value


def _mission_metadata(path: Path) -> tuple[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    prefix = f"<!-- {MISSION_MARKER}\n"
    try:
        payload = text.split(prefix, 1)[1].split("\n-->", 1)[0]
        metadata = json.loads(payload)
    except (IndexError, json.JSONDecodeError) as error:
        raise LSOError(f"mission record has no valid metadata block: {path}") from error
    if not isinstance(metadata, dict):
        raise LSOError("mission metadata must be a JSON object")
    return text, metadata


def _replace_mission_metadata(path: Path, metadata: dict[str, Any]) -> None:
    text, _ = _mission_metadata(path)
    prefix = f"<!-- {MISSION_MARKER}\n"
    before, remainder = text.split(prefix, 1)
    _, after = remainder.split("\n-->", 1)
    rendered = json.dumps(metadata, ensure_ascii=False, indent=2)
    path.write_text(f"{before}{prefix}{rendered}\n-->{after}", encoding="utf-8")


def _manifest(envelope_path: Path, envelope: dict[str, Any]) -> dict[str, Any]:
    binding = envelope["manifest"]
    candidate = envelope_path.resolve().parent / binding["path"]
    value = _object(candidate, "Crew Chief evidence manifest")
    return value


def _frozen_test_claims(
    envelope_path: Path, manifest: dict[str, Any]
) -> tuple[Path, dict[str, Any]]:
    binding = manifest["test_claims"]
    path = envelope_path.resolve().parent / binding["path"]
    claims = _object(path, "closeout validation evidence")
    validate_instance("closeout-evidence-v1.schema.json", claims)
    return path, claims


def _wrap_crew_chief(operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except ValueError as error:
        raise LSOError(f"Crew Chief evidence is not closeout-ready: {error}") from error


def _validate_audit_package(
    envelope_path: Path,
    report_path: Path,
    reconciliation_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    envelope = _wrap_crew_chief(lambda: verify_envelope(envelope_path))
    report = _object(report_path, "Crew Chief report")
    reconciliation = _object(reconciliation_path, "Crew Chief reconciliation")
    _wrap_crew_chief(lambda: validate_report(envelope, report))
    _wrap_crew_chief(lambda: validate_reconciliation(reconciliation, report))
    if report["verdict"] != "PASS" or report["findings"]:
        raise LSOError("LSO closeout requires Crew Chief PASS with zero findings")
    if (
        not reconciliation["reconciliation_complete"]
        or not reconciliation["approval_ready"]
    ):
        raise LSOError("Crew Chief reconciliation is not approval-ready")
    if reconciliation["audit_id"] != envelope["audit_id"]:
        raise LSOError("Crew Chief reconciliation and envelope disagree")
    manifest = _manifest(envelope_path, envelope)
    return envelope, report, reconciliation, manifest


def _approval_text(plan: dict[str, Any]) -> str:
    mission = plan["mission"]["mission_id"]
    target = plan["repository"]["remote_target_commit"]
    actions = ", ".join(plan["delivery"]["actions"])
    return (
        f"Authorize exact LSO plan {plan['plan_id']} for {mission}: execute once "
        f"with no automatic retry against origin/main at {target}; perform only "
        f"{actions}; proceed only while every audit, file, test, Git, and remote "
        "binding remains unchanged; stop on any failure. This does not authorize "
        "a live operation."
    )


def prepare_closeout(
    repository: Path,
    *,
    mission_record: Path,
    envelope_path: Path,
    report_path: Path,
    reconciliation_path: Path,
    implementation_commit_message: str,
    closeout_commit_message: str,
    final_authorization_gate: str,
    next_gate: str,
    final_approval_scope: str,
    output_root: Path,
    expires_in_seconds: int = 86400,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Prepare a non-mutating exact closeout plan from a final Crew Chief PASS."""
    repository = resolve_repository(repository)
    if not 1 <= expires_in_seconds <= 86400:
        raise LSOError("LSO plan expiry must be between 1 and 86400 seconds")
    for source, label in (
        (envelope_path, "Crew Chief envelope"),
        (report_path, "Crew Chief report"),
        (reconciliation_path, "Crew Chief reconciliation"),
        (mission_record, "mission record"),
    ):
        if source.is_symlink() or not source.is_file():
            raise LSOError(f"{label} must be a regular file: {source}")
    envelope_path = envelope_path.resolve()
    report_path = report_path.resolve()
    reconciliation_path = reconciliation_path.resolve()
    envelope, _, reconciliation, manifest = _validate_audit_package(
        envelope_path, report_path, reconciliation_path
    )
    if Path(envelope["repository"]["repository_root"]).resolve() != repository:
        raise LSOError("Crew Chief envelope belongs to a different repository")
    if envelope["subject"]["mode"] != "working-tree":
        raise LSOError("LSO v1 requires a final working-tree Crew Chief audit")
    if envelope["subject"]["base_commit"] != envelope["subject"]["head_commit"]:
        raise LSOError("LSO v1 requires an uncommitted subject on the target base")

    mission_record = mission_record.resolve()
    try:
        mission_relative = mission_record.relative_to(repository).as_posix()
    except ValueError as error:
        raise LSOError("mission record is outside the repository") from error
    if mission_relative != envelope["mission"]["repository_path"]:
        raise LSOError("LSO mission record differs from the audited mission record")
    _, metadata = _mission_metadata(mission_record)
    if metadata.get("lifecycle") not in {"draft", "active"}:
        raise LSOError("LSO can close only a draft or active mission")
    if metadata.get("pushed") or metadata.get("merged"):
        raise LSOError("mission already claims publication or merge")

    branch = branch_name(repository)
    state = git_state(repository)
    if state != envelope["git_state"]:
        raise LSOError("Git state changed after the Crew Chief audit")
    if state["branch"] != branch:
        raise LSOError("Crew Chief audited a different implementation branch")
    workstream = metadata.get("workstream")
    if isinstance(workstream, dict) and workstream.get("branch") != branch:
        raise LSOError("mission workstream branch disagrees with the audited branch")

    authorized_paths = sorted(
        item["path"] for item in manifest["subject"]["changed_files"]
    )
    if mission_relative not in authorized_paths:
        raise LSOError("the active mission record is not part of the audited subject")
    target_commit = resolve_commit(repository, "refs/remotes/origin/main")
    if target_commit != envelope["subject"]["base_commit"]:
        raise LSOError("origin/main moved after the audited work began")
    if not is_ancestor(repository, target_commit, envelope["subject"]["head_commit"]):
        raise LSOError("audited branch is not based on origin/main")
    remote_url = remote_url_hash_input(repository, "origin")
    test_path, claims = _frozen_test_claims(envelope_path, manifest)
    created = clock()
    if created.tzinfo is None:
        raise LSOError("LSO clock must be timezone-aware")
    envelope_expiry = crew_parse_time(envelope["expires_at"])
    expires = min(created + timedelta(seconds=expires_in_seconds), envelope_expiry)
    if expires <= created:
        raise LSOError("Crew Chief envelope is already expired")

    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "canary": CANARY,
        "role": "lso",
        "repository": {
            "repository_id": repository_identity(repository)["repository_id"],
            "root": str(repository),
            "branch": branch,
            "remote": "origin",
            "target_branch": "main",
            "remote_target_commit": target_commit,
            "remote_url_sha256": sha256_bytes(remote_url.encode("utf-8")),
        },
        "mission": {
            "repository_path": mission_relative,
            "mission_id": metadata["id"],
            "frozen_sha256": artifact_binding(mission_record)["sha256"],
            "lifecycle_before": metadata["lifecycle"],
        },
        "audit": {
            "envelope": artifact_binding(envelope_path),
            "audit_id": envelope["audit_id"],
            "envelope_id": envelope["envelope_id"],
            "report": artifact_binding(report_path),
            "verdict": "PASS",
            "reconciliation": artifact_binding(reconciliation_path),
            "reconciliation_package_hash": reconciliation["package_hash"],
        },
        "subject": {
            "mode": "working-tree",
            "base_commit": target_commit,
            "head_commit": envelope["subject"]["head_commit"],
            "git_state_hash": state["state_hash"],
            "authorized_paths": authorized_paths,
            "expected_tree": expected_tree(repository, authorized_paths),
            "candidate_commits": [],
        },
        "validation": {
            "test_claims": artifact_binding(test_path),
            "required_checks_complete": claims["required_checks_complete"],
            "limitations": claims["limitations"],
        },
        "delivery": {
            "implementation_commit_message": implementation_commit_message.strip(),
            "closeout_commit_message": closeout_commit_message.strip(),
            "final_authorization_gate": final_authorization_gate.strip(),
            "next_gate": next_gate.strip(),
            "final_approval_scope": final_approval_scope.strip(),
            "actions": list(CLOSEOUT_ACTIONS),
        },
        "generated_paths": list(GENERATED_GOVERNANCE_PATHS),
        "created_at": isoformat(created),
        "expires_at": isoformat(expires),
        "authority_statement": (
            "LSO verifies and executes only an exact Maverick-authorized closeout; "
            "it does not approve work or live operations."
        ),
    }
    plan["plan_id"] = plan_identifier(plan)
    plan["approval"] = {"required_authorization_text": _approval_text(plan)}
    validate_instance("closeout-plan-v1.schema.json", plan)
    output = new_external_directory(repository, output_root)
    plan_path = output / "closeout-plan.json"
    write_canonical_json(plan_path, plan)
    card = "\n".join(
        [
            "# LSO Closeout Approval Card",
            "",
            f"- Mission: `{metadata['id']}`",
            f"- Plan: `{plan['plan_id']}`",
            "- Crew Chief: `PASS` with zero findings",
            f"- Target: `origin/main` at `{target_commit}`",
            f"- Audited paths: {len(authorized_paths)}",
            f"- Recorded limitations: {len(claims['limitations'])}",
            f"- Completion-record scope: {final_approval_scope.strip()}",
            "",
            "## Exact authorization text",
            "",
            plan["approval"]["required_authorization_text"],
            "",
        ]
    )
    (output / "approval-card.md").write_text(card, encoding="utf-8")
    return {
        "plan_id": plan["plan_id"],
        "plan_path": str(plan_path),
        "plan_sha256": artifact_binding(plan_path)["sha256"],
        "approval_card": str(output / "approval-card.md"),
        "required_authorization_text": plan["approval"]["required_authorization_text"],
    }


def verify_plan(
    plan_path: Path, *, clock: Callable[[], datetime] = utc_now
) -> dict[str, Any]:
    plan_path = plan_path.resolve()
    plan = _object(plan_path, "LSO closeout plan")
    validate_instance("closeout-plan-v1.schema.json", plan)
    if plan_identifier(plan) != plan["plan_id"]:
        raise LSOError("LSO plan identifier is invalid")
    if _approval_text(plan) != plan["approval"]["required_authorization_text"]:
        raise LSOError("LSO approval text is not canonical for the plan")
    now = clock()
    if now.tzinfo is None or now > parse_time(plan["expires_at"]):
        raise LSOError("LSO closeout plan expired")
    repository = resolve_repository(Path(plan["repository"]["root"]))
    identity = repository_identity(repository)
    if identity["repository_id"] != plan["repository"]["repository_id"]:
        raise LSOError("LSO repository identity changed")
    if branch_name(repository) != plan["repository"]["branch"]:
        raise LSOError("LSO implementation branch changed")
    if (
        sha256_bytes(remote_url_hash_input(repository, "origin").encode("utf-8"))
        != plan["repository"]["remote_url_sha256"]
    ):
        raise LSOError("LSO Git remote changed")
    if (
        resolve_commit(repository, "refs/remotes/origin/main")
        != plan["repository"]["remote_target_commit"]
    ):
        raise LSOError("origin/main changed after LSO plan preparation")

    envelope_path = verify_artifact(plan["audit"]["envelope"], "audit envelope")
    report_path = verify_artifact(plan["audit"]["report"], "Crew Chief report")
    reconciliation_path = verify_artifact(
        plan["audit"]["reconciliation"], "Crew Chief reconciliation"
    )
    envelope, _, reconciliation, manifest = _validate_audit_package(
        envelope_path, report_path, reconciliation_path
    )
    if envelope["audit_id"] != plan["audit"]["audit_id"]:
        raise LSOError("LSO plan audit binding changed")
    if reconciliation["package_hash"] != plan["audit"]["reconciliation_package_hash"]:
        raise LSOError("LSO reconciliation binding changed")
    mission = repository / plan["mission"]["repository_path"]
    if artifact_binding(mission)["sha256"] != plan["mission"]["frozen_sha256"]:
        raise LSOError("mission record changed after LSO plan preparation")
    _, metadata = _mission_metadata(mission)
    if metadata.get("id") != plan["mission"]["mission_id"]:
        raise LSOError("mission identity changed after LSO plan preparation")
    paths = sorted(item["path"] for item in manifest["subject"]["changed_files"])
    if paths != plan["subject"]["authorized_paths"]:
        raise LSOError("audited path inventory changed")
    state = git_state(repository)
    if state["state_hash"] != plan["subject"]["git_state_hash"]:
        raise LSOError("Git state changed after LSO plan preparation")
    if expected_tree(repository, paths) != plan["subject"]["expected_tree"]:
        raise LSOError("expected implementation tree changed")
    claims_path = verify_artifact(plan["validation"]["test_claims"], "test claims")
    claims = _object(claims_path, "closeout validation evidence")
    validate_instance("closeout-evidence-v1.schema.json", claims)
    return plan


def create_authorization_receipt(
    plan_path: Path,
    authorization_text_path: Path,
    output_path: Path,
    *,
    expires_in_seconds: int = 3600,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    plan = verify_plan(plan_path, clock=clock)
    repository = Path(plan["repository"]["root"])
    output_path = ensure_external(repository, output_path, "LSO receipt")
    if output_path.exists():
        raise LSOError(f"LSO receipt output already exists: {output_path}")
    if authorization_text_path.is_symlink() or not authorization_text_path.is_file():
        raise LSOError("authorization text must be a regular external file")
    text_path = ensure_external(
        repository, authorization_text_path, "authorization text"
    )
    payload = text_path.read_bytes()
    try:
        text = payload.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise LSOError("authorization text must be UTF-8") from error
    if text != plan["approval"]["required_authorization_text"]:
        raise LSOError("authorization text does not exactly approve this LSO plan")
    created = clock()
    expires = created + timedelta(seconds=expires_in_seconds)
    plan_expiry = parse_time(plan["expires_at"])
    if expires > plan_expiry:
        expires = plan_expiry
    if expires <= created:
        raise LSOError("LSO authorization receipt would already be expired")
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "canary": CANARY,
        "plan_id": plan["plan_id"],
        "plan_sha256": artifact_binding(plan_path)["sha256"],
        "authorization_text_sha256": sha256_bytes(payload),
        "authorization_text_size": len(payload),
        "asserted_authority": "Maverick",
        "allowed_actions": list(CLOSEOUT_ACTIONS),
        "single_use": True,
        "created_at": isoformat(created),
        "expires_at": isoformat(expires),
        "authority_boundary": (
            "The authenticated Mission Control interaction and trusted local "
            "operating-system account are the v1 authorization boundary; this "
            "receipt is tamper-evident, not independent identity proof."
        ),
    }
    receipt["receipt_id"] = receipt_identifier(receipt)
    validate_instance("authorization-receipt-v1.schema.json", receipt)
    write_canonical_json(output_path, receipt)
    return {
        "receipt_id": receipt["receipt_id"],
        "receipt_path": str(output_path),
    }


def validate_authorization_receipt(
    plan_path: Path,
    receipt_path: Path,
    *,
    clock: Callable[[], datetime] = utc_now,
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = verify_plan(plan_path, clock=clock)
    receipt = _object(receipt_path, "LSO authorization receipt")
    validate_instance("authorization-receipt-v1.schema.json", receipt)
    if receipt_identifier(receipt) != receipt["receipt_id"]:
        raise LSOError("LSO receipt identifier is invalid")
    if receipt["plan_id"] != plan["plan_id"]:
        raise LSOError("LSO receipt approves a different plan")
    if receipt["plan_sha256"] != artifact_binding(plan_path)["sha256"]:
        raise LSOError("LSO plan bytes changed after authorization")
    if receipt["allowed_actions"] != list(CLOSEOUT_ACTIONS):
        raise LSOError("LSO receipt actions are incomplete or reordered")
    now = clock()
    if now.tzinfo is None or now > parse_time(receipt["expires_at"]):
        raise LSOError("LSO authorization receipt expired")
    return plan, receipt


def _complete_mission_record(
    mission_path: Path,
    plan: dict[str, Any],
    implementation_commit: str,
    completed_at: datetime,
) -> None:
    _, metadata = _mission_metadata(mission_path)
    commits = list(metadata.get("implementation_commits", []))
    for commit in [*plan["subject"]["candidate_commits"], implementation_commit]:
        if commit not in commits:
            commits.append(commit)
    metadata["lifecycle"] = "completed"
    metadata["authorization_gate"] = plan["delivery"]["final_authorization_gate"]
    metadata["implementation_commits"] = commits
    metadata["pushed"] = True
    metadata["merged"] = True
    metadata["next_gate"] = plan["delivery"]["next_gate"]
    metadata.setdefault("approval_evidence", []).append(
        {
            "date": completed_at.astimezone(timezone.utc).date().isoformat(),
            "authority": "Maverick",
            "scope": plan["delivery"]["final_approval_scope"],
        }
    )
    workstream = metadata.get("workstream")
    if isinstance(workstream, dict):
        workstream["state"] = "completed"
        workstream["next_gate"] = plan["delivery"]["next_gate"]
    _replace_mission_metadata(mission_path, metadata)


def execute_closeout(
    plan_path: Path,
    receipt_path: Path,
    *,
    generate_governance: Callable[[], None] | None = None,
    validate_governance: Callable[[], list[str]] | None = None,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Execute one consumed, exact, no-retry closeout authorization."""
    started = clock()
    plan, receipt = validate_authorization_receipt(
        plan_path, receipt_path, clock=lambda: started
    )
    repository = Path(plan["repository"]["root"])
    output_root = ensure_external(repository, plan_path.resolve().parent, "LSO output")
    report_root = output_root / "reports" / receipt["receipt_id"]
    report_root.mkdir(parents=True, exist_ok=False)
    completed: list[str] = []
    failed_action: str | None = None
    error_text: str | None = None
    implementation_commit: str | None = None
    closeout_commit: str | None = None
    branch_remote_head: str | None = None
    target_remote_head: str | None = None
    index_snapshot = None
    persistent_precommit_mutation = False

    try:
        observed = remote_head(repository, "origin", "main")
        if observed != plan["repository"]["remote_target_commit"]:
            raise LSOError("GitHub main changed after LSO plan preparation")
        consumption_directory = receipt_consumption_directory(
            repository, plan["repository"]["repository_id"]
        )
        consume_once(consumption_directory, receipt["receipt_id"])
        authorized = plan["subject"]["authorized_paths"]

        failed_action = "stage_exact_audited_paths"
        index_snapshot = capture_index(repository)
        git(repository, "add", "--all", "--", *authorized)
        staged, unstaged, untracked = changed_path_sets(repository)
        if staged != set(authorized) or unstaged or untracked:
            raise LSOError("staged state does not exactly equal the audited path set")
        if (
            git(repository, "write-tree").stdout.strip()
            != plan["subject"]["expected_tree"]
        ):
            raise LSOError("staged tree differs from the audited expected tree")
        git(repository, "diff", "--cached", "--check")
        completed.append(failed_action)
        index_snapshot = None

        failed_action = "commit_implementation"
        parent = resolve_commit(repository, "HEAD")
        git(
            repository,
            "commit",
            "-m",
            plan["delivery"]["implementation_commit_message"],
        )
        implementation_commit = resolve_commit(repository, "HEAD")
        if resolve_commit(repository, "HEAD^") != parent:
            raise LSOError("implementation commit parent is not the audited HEAD")
        if (
            git(repository, "show", "-s", "--format=%T", "HEAD").stdout.strip()
            != plan["subject"]["expected_tree"]
        ):
            raise LSOError("implementation commit tree differs from the audited tree")
        if git(repository, "status", "--porcelain").stdout:
            raise LSOError("repository changed during implementation commit")
        completed.append(failed_action)

        failed_action = "publish_implementation_branch"
        branch = plan["repository"]["branch"]
        git(
            repository,
            "push",
            "--atomic",
            "origin",
            f"{implementation_commit}:refs/heads/{branch}",
            f"{implementation_commit}:refs/heads/main",
        )
        completed.append(failed_action)
        completed.append("fast_forward_main")
        branch_remote_head = remote_head(repository, "origin", branch)
        target_remote_head = remote_head(repository, "origin", "main")
        if (
            branch_remote_head != implementation_commit
            or target_remote_head != implementation_commit
        ):
            raise LSOError("implementation publication did not reach both remote refs")
        git(repository, "update-ref", "refs/remotes/origin/main", implementation_commit)
        git(
            repository,
            "update-ref",
            f"refs/remotes/origin/{branch}",
            implementation_commit,
        )

        failed_action = "publish_completion_records"
        mission_path = repository / plan["mission"]["repository_path"]
        _complete_mission_record(mission_path, plan, implementation_commit, started)
        if generate_governance is None or validate_governance is None:
            from tools.governance import repository as governance

            if governance.ROOT.resolve() != repository.resolve():
                raise LSOError("governance controller is bound to another repository")
            generate_governance = governance.generate
            validate_governance = governance.validate
        generate_governance()
        errors = validate_governance()
        if errors:
            raise LSOError("completion-record governance failed: " + "; ".join(errors))
        staged, unstaged, untracked = changed_path_sets(repository)
        if staged or untracked:
            raise LSOError("unexpected staged or untracked completion-record state")
        allowed_closeout = {
            plan["mission"]["repository_path"],
            *plan["generated_paths"],
        }
        if not unstaged or not unstaged.issubset(allowed_closeout):
            raise LSOError("completion-record changes exceed the governed allowlist")
        git(repository, "add", "--all", "--", *sorted(allowed_closeout))
        git(repository, "diff", "--cached", "--check")
        completed.append(failed_action)

        failed_action = "commit_completion_records"
        git(
            repository,
            "commit",
            "-m",
            plan["delivery"]["closeout_commit_message"],
        )
        closeout_commit = resolve_commit(repository, "HEAD")
        if git(repository, "status", "--porcelain").stdout:
            raise LSOError("repository changed during completion-record commit")
        completed.append(failed_action)

        failed_action = "publish_closeout"
        git(
            repository,
            "push",
            "--atomic",
            "origin",
            f"{closeout_commit}:refs/heads/{branch}",
            f"{closeout_commit}:refs/heads/main",
        )
        completed.append(failed_action)

        failed_action = "verify_remote"
        branch_remote_head = remote_head(repository, "origin", branch)
        target_remote_head = remote_head(repository, "origin", "main")
        if (
            branch_remote_head != closeout_commit
            or target_remote_head != closeout_commit
        ):
            raise LSOError("closeout publication did not reach both remote refs")
        git(repository, "update-ref", "refs/remotes/origin/main", closeout_commit)
        git(repository, "update-ref", f"refs/remotes/origin/{branch}", closeout_commit)
        completed.append(failed_action)

        failed_action = "declare_complete"
        if git(repository, "status", "--porcelain").stdout:
            raise LSOError("repository is not clean after closeout")
        _, final_metadata = _mission_metadata(mission_path)
        if final_metadata.get("lifecycle") != "completed":
            raise LSOError("canonical mission record does not declare completion")
        completed.append(failed_action)
        failed_action = None
    except Exception as error:  # preserve a bounded failure record; never retry
        error_text = str(error)
        if index_snapshot is not None:
            try:
                restore_index(index_snapshot)
            except Exception as recovery_error:
                persistent_precommit_mutation = True
                error_text = (
                    f"{error_text}; exact pre-execution Git index restoration "
                    f"failed: {recovery_error}"
                )

    completed_at = clock()
    status = (
        "COMPLETE"
        if completed == list(CLOSEOUT_ACTIONS)
        else ("PARTIAL" if completed or persistent_precommit_mutation else "FAILED")
    )
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "canary": CANARY,
        "plan_id": plan["plan_id"],
        "receipt_id": receipt["receipt_id"],
        "status": status,
        "started_at": isoformat(started),
        "completed_at": isoformat(completed_at),
        "completed_actions": completed,
        "failed_action": failed_action,
        "error": error_text,
        "implementation_commit": implementation_commit,
        "closeout_commit": closeout_commit,
        "remote_branch_head": branch_remote_head,
        "remote_target_head": target_remote_head,
        "mission_completed": status == "COMPLETE",
        "authority_statement": (
            "COMPLETE means the exact authorized closeout was committed, published, "
            "recorded, and remotely verified; it does not authorize or report a live "
            "operation."
        ),
    }
    report["report_id"] = report_identifier(report)
    validate_instance("execution-report-v1.schema.json", report)
    write_canonical_json(report_root / "execution-report.json", report)
    return {**report, "report_path": str(report_root / "execution-report.json")}
