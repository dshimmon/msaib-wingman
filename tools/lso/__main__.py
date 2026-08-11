"""Command-line entry point for Wingman's Landing Signal Officer v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.lso.controller import (
    create_authorization_receipt,
    execute_closeout,
    prepare_closeout,
    verify_plan,
)
from tools.lso.core import LSOError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser(
        "prepare", help="prepare a non-mutating exact closeout plan"
    )
    prepare.add_argument("--repository", type=Path, default=Path.cwd())
    prepare.add_argument("--mission-record", type=Path, required=True)
    prepare.add_argument("--envelope", type=Path, required=True)
    prepare.add_argument("--report", type=Path, required=True)
    prepare.add_argument("--reconciliation", type=Path, required=True)
    prepare.add_argument("--implementation-commit-message", required=True)
    prepare.add_argument("--closeout-commit-message", required=True)
    prepare.add_argument("--final-authorization-gate", required=True)
    prepare.add_argument("--next-gate", required=True)
    prepare.add_argument("--final-approval-scope", required=True)
    prepare.add_argument("--output-root", type=Path, required=True)
    prepare.add_argument("--expires-in-seconds", type=int, default=86400)

    verify = commands.add_parser("verify", help="revalidate an exact closeout plan")
    verify.add_argument("plan", type=Path)

    authorize = commands.add_parser(
        "authorize", help="record exact external Maverick authorization"
    )
    authorize.add_argument("plan", type=Path)
    authorize.add_argument("authorization_text", type=Path)
    authorize.add_argument("--output", type=Path, required=True)
    authorize.add_argument("--expires-in-seconds", type=int, default=3600)

    execute = commands.add_parser(
        "execute", help="execute one exact receipt-bound closeout"
    )
    execute.add_argument("plan", type=Path)
    execute.add_argument("receipt", type=Path)
    execute.add_argument(
        "--execute",
        action="store_true",
        help="required acknowledgement that repository and remote writes are intended",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_closeout(
                args.repository,
                mission_record=args.mission_record,
                envelope_path=args.envelope,
                report_path=args.report,
                reconciliation_path=args.reconciliation,
                implementation_commit_message=args.implementation_commit_message,
                closeout_commit_message=args.closeout_commit_message,
                final_authorization_gate=args.final_authorization_gate,
                next_gate=args.next_gate,
                final_approval_scope=args.final_approval_scope,
                output_root=args.output_root,
                expires_in_seconds=args.expires_in_seconds,
            )
        elif args.command == "verify":
            plan = verify_plan(args.plan)
            result = {"plan_id": plan["plan_id"], "valid": True}
        elif args.command == "authorize":
            result = create_authorization_receipt(
                args.plan,
                args.authorization_text,
                args.output,
                expires_in_seconds=args.expires_in_seconds,
            )
        else:
            if not args.execute:
                raise LSOError(
                    "closeout execution requires the explicit --execute flag"
                )
            result = execute_closeout(args.plan, args.receipt)
    except (LSOError, ValueError, OSError) as error:
        print(f"LSO control failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.command == "execute" and result.get("status") != "COMPLETE":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
