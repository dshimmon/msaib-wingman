"""Strict Ledger Transition command surface with no arbitrary SQL or argv."""

from __future__ import annotations

import argparse
import json

from wingman.core.ledger.dry_run import run_disposable_dry_run
from wingman.core.ledger.recovery import recover_incomplete
from wingman.core.ledger.transition import execute_authorized_transition


def parser():
    result = argparse.ArgumentParser(prog="wingman-ledger-transition")
    commands = result.add_subparsers(dest="command", required=True)

    execute = commands.add_parser("execute")
    execute.add_argument("--manifest", required=True)
    execute.add_argument("--receipt", required=True)

    recover = commands.add_parser("recover")
    recover.add_argument("--target", required=True)

    dry_run = commands.add_parser("dry-run")
    dry_run.add_argument("--source", required=True)
    dry_run.add_argument("--workspace", required=True)
    return result


def main(argv=None):
    arguments = parser().parse_args(argv)
    if arguments.command == "execute":
        result = execute_authorized_transition(
            arguments.manifest,
            arguments.receipt,
        )
    elif arguments.command == "recover":
        result = recover_incomplete(arguments.target)
    else:
        result = run_disposable_dry_run(
            arguments.source,
            arguments.workspace,
        )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
