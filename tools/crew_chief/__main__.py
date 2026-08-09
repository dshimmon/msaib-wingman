"""Command-line entry point for Crew Chief v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.crew_chief.controller import (
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
    if not isinstance(value, list) or not all(
        isinstance(item, dict) for item in value
    ):
        raise CrewChiefError("dispositions must be a JSON array of objects")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="freeze an audit envelope")
    prepare.add_argument("--repository", type=Path, default=Path.cwd())
    prepare.add_argument("--mission-record", type=Path, required=True)
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

    validate = commands.add_parser(
        "validate-report", help="validate a structured Crew Chief report"
    )
    validate.add_argument("envelope", type=Path)
    validate.add_argument("report", type=Path)
    validate.add_argument("--markdown-output", type=Path)

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
    return {
        "audit_id": report["audit_id"],
        "verdict": report["verdict"],
        "valid": True,
    }


def _reconcile(args: argparse.Namespace) -> dict[str, Any]:
    envelope = verify_envelope(args.envelope, require_current_state=False)
    report = _report(args.report)
    package = reconcile_report(
        envelope, report, _dispositions(args.dispositions)
    )
    repository = Path(envelope["repository"]["repository_root"])
    output = ensure_external_path(repository, args.output, "reconciliation output")
    write_canonical_json(output, package)
    if args.markdown_output:
        markdown = ensure_external_path(
            repository, args.markdown_output, "reconciliation Markdown"
        )
        atomic_write(
            markdown, render_reconciliation_markdown(package).encode("utf-8")
        )
    return {
        "approval_ready": package["approval_ready"],
        "output": str(output),
        "reconciliation_complete": package["reconciliation_complete"],
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
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
            )
        elif args.command == "validate-report":
            result = _validate_report(args)
        else:
            result = _reconcile(args)
    except CrewChiefError as error:
        print(f"Crew Chief control failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
