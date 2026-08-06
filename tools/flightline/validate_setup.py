#!/usr/bin/env python3
"""Run harmless negative tests against installed Codex permission profiles."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from tools.flightline.flightline import CANARY, build_permission_profile


def _run(profile_id: str, override: str, cwd: Path, command: Sequence[str], log_denials: bool = False) -> Dict[str, Any]:
    argv = [
        "codex",
        "sandbox",
        "-c",
        "default_permissions=\"{}\"".format(profile_id),
        "-c",
        override,
        "-P",
        profile_id,
        "-C",
        str(cwd),
    ]
    if log_denials:
        argv.append("--log-denials")
    argv.extend(command)
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    return {
        "argv": ["codex", "sandbox", "<PROFILE>", "--"] + list(command),
        "exit_code": result.returncode,
        "output": result.stdout[-4000:],
    }


def _expect(name: str, result: Mapping[str, Any], allowed: bool, output_contains: str = "") -> Dict[str, Any]:
    passed = (result["exit_code"] == 0) if allowed else (result["exit_code"] != 0)
    if output_contains:
        passed = passed and output_contains.lower() in str(result["output"]).lower()
    return {
        "name": name,
        "expected": "allow" if allowed else "deny",
        "passed": passed,
        "exit_code": result["exit_code"],
        "output": result["output"],
    }


def _envelope(foreground: Path, worktree: Path, output: Path, secret: Path, role: str) -> Dict[str, Any]:
    return {
        "role": role,
        "repository_root": str(foreground),
        "worktree_path": str(worktree),
        "allowed_write_paths": [str(worktree / "src")] if role == "development-engineer" else [],
        "protected_data_paths": [str(secret), str(foreground / "data")],
        "credential_paths": [str(foreground / ".credentials")],
        "allowed_temp_paths": [str(output)],
    }


def run_validation(root: Path, protected_probe: Path) -> Dict[str, Any]:
    if root.exists():
        raise RuntimeError("validation root already exists: {}".format(root))
    foreground = root / "foreground"
    worktree = root / "worktree"
    output = root / "evidence"
    for path in (foreground / ".git", foreground / "data", worktree / "src", output):
        path.mkdir(parents=True, exist_ok=True)
    secret = foreground / ".credentials"
    secret.write_text("harmless-flightline-fixture\n", encoding="utf-8")
    runtime = foreground / ".venv" / "flightline-py312"
    runtime.mkdir(parents=True)
    (runtime / "runtime-readable.txt").write_text("fixture-runtime\n", encoding="utf-8")
    (foreground / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (worktree / "readable.txt").write_text("fixture\n", encoding="utf-8")

    engineer = _envelope(foreground, worktree, output, secret, "development-engineer")
    if protected_probe:
        engineer["credential_paths"].append(str(protected_probe.resolve()))
    engineer_id, engineer_override = build_permission_profile(engineer)
    auditor = _envelope(foreground, worktree, output, secret, "independent-auditor")
    auditor["runtime_paths"] = [str(runtime)]
    if protected_probe:
        auditor["credential_paths"].append(str(protected_probe.resolve()))
    auditor_id, auditor_override = build_permission_profile(auditor)

    checks: List[Dict[str, Any]] = []
    checks.append(_expect("engineer reads isolated worktree", _run(engineer_id, engineer_override, worktree, ["/bin/ls", "readable.txt"]), True))
    checks.append(_expect("engineer writes scoped path", _run(engineer_id, engineer_override, worktree, ["/usr/bin/touch", str(worktree / "src" / "allowed")]), True))
    checks.append(_expect("engineer cannot write worktree root", _run(engineer_id, engineer_override, worktree, ["/usr/bin/touch", str(worktree / "blocked")]), False))
    checks.append(_expect("engineer cannot read fixture secret", _run(engineer_id, engineer_override, worktree, ["/bin/dd", "if={}".format(secret), "of=/dev/null", "bs=1", "count=1"]), False))
    if protected_probe:
        checks.append(_expect("engineer cannot read protected repository secret", _run(engineer_id, engineer_override, worktree, ["/bin/dd", "if={}".format(protected_probe.resolve()), "of=/dev/null", "bs=1", "count=1"]), False))
    checks.append(_expect("engineer reads foreground Git metadata only", _run(engineer_id, engineer_override, worktree, ["/bin/ls", str(foreground / ".git" / "HEAD")]), True))
    checks.append(_expect("engineer cannot write foreground Git metadata", _run(engineer_id, engineer_override, worktree, ["/usr/bin/touch", str(foreground / ".git" / "blocked")]), False))
    checks.append(_expect("engineer cannot read foreground data", _run(engineer_id, engineer_override, worktree, ["/bin/ls", str(foreground / "data")]), False))
    network = _run(
        engineer_id,
        engineer_override,
        worktree,
        ["/usr/bin/ruby", "-rsocket", "-e", "TCPSocket.new('127.0.0.1', 9)"],
        log_denials=True,
    )
    checks.append(_expect("engineer network is disabled", network, False))
    checks.append(_expect("auditor reads immutable audit source", _run(auditor_id, auditor_override, worktree, ["/bin/ls", str(worktree / "readable.txt")]), True))
    checks.append(_expect("auditor reads only the bound runtime exception", _run(auditor_id, auditor_override, worktree, ["/bin/ls", str(runtime / "runtime-readable.txt")]), True))
    checks.append(_expect("auditor cannot write source", _run(auditor_id, auditor_override, worktree, ["/usr/bin/touch", str(worktree / "src" / "auditor-blocked")]), False))
    checks.append(_expect("auditor cannot write foreground repository", _run(auditor_id, auditor_override, worktree, ["/usr/bin/touch", str(foreground / "auditor-blocked")]), False))
    checks.append(_expect("auditor cannot write foreground Git metadata", _run(auditor_id, auditor_override, worktree, ["/usr/bin/touch", str(foreground / ".git" / "auditor-blocked")]), False))
    checks.append(_expect("auditor cannot run a Git-state mutation", _run(auditor_id, auditor_override, worktree, ["/usr/bin/git", "-C", str(foreground), "init"]), False))
    checks.append(_expect("auditor cannot read fixture credential", _run(auditor_id, auditor_override, worktree, ["/bin/dd", "if={}".format(secret), "of=/dev/null", "bs=1", "count=1"]), False))
    if protected_probe:
        checks.append(_expect("auditor cannot read protected repository secret", _run(auditor_id, auditor_override, worktree, ["/bin/dd", "if={}".format(protected_probe.resolve()), "of=/dev/null", "bs=1", "count=1"]), False))
    checks.append(_expect("auditor cannot read foreground protected data", _run(auditor_id, auditor_override, worktree, ["/bin/ls", str(foreground / "data")]), False))
    auditor_network = _run(
        auditor_id,
        auditor_override,
        worktree,
        ["/usr/bin/ruby", "-rsocket", "-e", "TCPSocket.new('127.0.0.1', 9)"],
        log_denials=True,
    )
    checks.append(_expect("auditor network is disabled", auditor_network, False))
    checks.append(_expect("auditor writes audit output", _run(auditor_id, auditor_override, worktree, ["/usr/bin/touch", str(output / "auditor-report")]), True))

    report = {
        "canary": CANARY,
        "status": "PASS" if all(check["passed"] for check in checks) else "FAIL",
        "fixture_root": str(root),
        "protected_probe": str(protected_probe.resolve()) if protected_probe else None,
        "checks": checks,
        "created_at_epoch_seconds": int(time.time()),
        "cleanup_performed": False,
        "note": "Validation artifacts are intentionally preserved for inspection; no external host was contacted.",
    }
    report_path = output / "safety-validation.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--protected-probe", type=Path)
    args = parser.parse_args()
    try:
        report = run_validation(args.fixture_root.resolve(strict=False), args.protected_probe)
    except Exception as exc:
        print("BLOCKED: {}".format(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
