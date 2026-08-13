"""Command-line entry point for Crew Chief v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.crew_chief.controller import (
    build_proposed_closeout_record,
    prepare_audit,
    reconcile_report,
    render_reconciliation_markdown,
    render_report_markdown,
    verify_envelope,
)
from tools.crew_chief.core import (
    CrewChiefError,
    atomic_write,
    ensure_external_path,
    read_json,
    write_canonical_json,
)
from tools.crew_chief.pool import pool_exit_code, run_pool
from tools.crew_chief.retention import (
    DEFAULT_MAX_RETAINED_REPORTS,
    DEFAULT_RETENTION_DAYS,
    prune_reports,
)
from tools.crew_chief.runner import run_audit
from tools.crew_chief.validation import validate_report


def _claims(path: Path) -> dict[str, Any]:
    value = read_json(path)
    if not isinstance(value, dict):
        raise CrewChiefError("test claims must be a JSON object")
    return value


def _report(path: Path) -> dict[str, Any]:
    value = read_json(path)
    if not isinstance(value, dict):
        raise CrewChiefError("report must be a JSON object")
    return value


def _dispositions(path: Path) -> list[dict[str, Any]]:
    value = read_json(path)
    if isinstance(value, dict):
        value = value.get("dispositions")
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise CrewChiefError("dispositions must be a JSON array of objects")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="freeze an audit envelope")
    prepare.add_argument("--repository", type=Path, default=Path.cwd())
    prepare.add_argument(
        "--task-authority",
        type=Path,
        help="bounded task authority to freeze for an ordinary audit",
    )
    prepare.add_argument(
        "--mission-record",
        type=Path,
        help="optional canonical mission record for legacy or mission work",
    )
    prepare.add_argument("--base", required=True)
    prepare.add_argument("--head", default="HEAD")
    prepare.add_argument("--engineer-report", type=Path, required=True)
    prepare.add_argument("--evidence", type=Path, action="append", required=True)
    prepare.add_argument("--test-claims", type=Path, required=True)
    prepare.add_argument(
        "--profile", choices=("standard", "deep", "exempt"), default="standard"
    )
    prepare.add_argument("--profile-justification")
    prepare.add_argument("--output-root", type=Path)
    prepare.add_argument("--include-working-tree", action="store_true")
    prepare.add_argument("--allow-untracked", action="append", default=[])
    prepare.add_argument("--expires-in-seconds", type=int, default=86400)

    run = commands.add_parser(
        "run", help="prepare or launch one fresh read-only review"
    )
    run.add_argument("envelope", type=Path)
    run.add_argument("--workspace", type=Path)
    run.add_argument("--codex", default="codex")
    run.add_argument("--execute", action="store_true")
    run.add_argument("--allow-fresh-session-fallback", action="store_true")
    run.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    run.add_argument(
        "--max-retained-reports",
        type=int,
        default=DEFAULT_MAX_RETAINED_REPORTS,
    )

    pool = commands.add_parser(
        "pool", help="prepare or run a bounded concurrent audit pool"
    )
    pool.add_argument("manifest", type=Path)
    pool.add_argument("--output-root", type=Path, required=True)
    pool.add_argument("--max-concurrency", type=int, default=2)
    pool.add_argument("--codex", default="codex")
    pool.add_argument("--execute", action="store_true")
    pool.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    pool.add_argument(
        "--max-retained-reports",
        type=int,
        default=DEFAULT_MAX_RETAINED_REPORTS,
    )

    retention = commands.add_parser(
        "retention", help="inspect or prune completed external report bundles"
    )
    retention.add_argument("output_root", type=Path)
    retention.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    retention.add_argument(
        "--max-retained-reports",
        type=int,
        default=DEFAULT_MAX_RETAINED_REPORTS,
    )
    retention.add_argument("--dry-run", action="store_true")

    validate = commands.add_parser(
        "validate-report", help="validate a structured Crew Chief report"
    )
    validate.add_argument("envelope", type=Path)
    validate.add_argument("report", type=Path)
    validate.add_argument("--markdown-output", type=Path)
    validate.add_argument("--proposed-closeout-output", type=Path)

    reconcile = commands.add_parser(
        "reconcile", help="validate every finding disposition"
    )
    reconcile.add_argument("envelope", type=Path)
    reconcile.add_argument("report", type=Path)
    reconcile.add_argument("dispositions", type=Path)
    reconcile.add_argument("--output", type=Path, required=True)
    reconcile.add_argument("--markdown-output", type=Path)
    return parser


def _prepare(args: argparse.Namespace) -> dict[str, Any]:
    return prepare_audit(
        args.repository,
        task_authority=args.task_authority,
        mission_record=args.mission_record,
        base=args.base,
        head=args.head,
        engineer_report=args.engineer_report,
        evidence_artifacts=args.evidence,
        test_claims=_claims(args.test_claims),
        profile=args.profile,
        profile_justification=args.profile_justification,
        output_root=args.output_root,
        include_worktree=args.include_working_tree,
        authorized_untracked=args.allow_untracked,
        expires_in_seconds=args.expires_in_seconds,
    )


def _validate_report(args: argparse.Namespace) -> dict[str, Any]:
    envelope = verify_envelope(args.envelope)
    report = _report(args.report)
    validate_report(envelope, report)
    if args.markdown_output:
        target = ensure_external_path(
            Path(envelope["repository"]["repository_root"]),
            args.markdown_output,
            "Markdown report",
        )
        atomic_write(target, render_report_markdown(report).encode("utf-8"))
    result = {
        "audit_id": report["audit_id"],
        "verdict": report["verdict"],
        "valid": True,
    }
    if args.proposed_closeout_output and report["verdict"] == "PASS":
        repository = Path(envelope["repository"]["repository_root"])
        target = ensure_external_path(
            repository,
            args.proposed_closeout_output,
            "proposed closeout output",
        )
        proposed = build_proposed_closeout_record(envelope, report)
        write_canonical_json(target, proposed)
        result["proposed_closeout_path"] = str(target)
    return result


def _reconcile(args: argparse.Namespace) -> dict[str, Any]:
    envelope = verify_envelope(args.envelope, require_current_state=False)
    report = _report(args.report)
    package = reconcile_report(envelope, report, _dispositions(args.dispositions))
    repository = Path(envelope["repository"]["repository_root"])
    output = ensure_external_path(repository, args.output, "reconciliation output")
    write_canonical_json(output, package)
    if args.markdown_output:
        markdown = ensure_external_path(
            repository, args.markdown_output, "reconciliation Markdown"
        )
        atomic_write(markdown, render_reconciliation_markdown(package).encode("utf-8"))
    return {
        "approval_ready": package["approval_ready"],
        "output": str(output),
        "reconciliation_complete": package["reconciliation_complete"],
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    exit_code = 0
    try:
        if args.command == "prepare":
            result = _prepare(args)
        elif args.command == "run":
            result = run_audit(
                args.envelope,
                args.workspace,
                execute=args.execute,
                allow_fresh_session_fallback=args.allow_fresh_session_fallback,
                codex_executable=args.codex,
                retention_days=args.retention_days,
                max_retained_reports=args.max_retained_reports,
            )
        elif args.command == "pool":
            result = run_pool(
                args.manifest,
                args.output_root,
                max_concurrency=args.max_concurrency,
                execute=args.execute,
                codex_executable=args.codex,
                retention_days=args.retention_days,
                max_retained_reports=args.max_retained_reports,
            )
            exit_code = pool_exit_code(result)
        elif args.command == "retention":
            result = prune_reports(
                args.output_root,
                retention_days=args.retention_days,
                max_retained_reports=args.max_retained_reports,
                dry_run=args.dry_run,
            )
        elif args.command == "validate-report":
            result = _validate_report(args)
        else:
            result = _reconcile(args)
    except CrewChiefError as error:
        print(f"Crew Chief control failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
