#!/usr/bin/env python3
"""Fail-closed PreToolUse and PermissionRequest guard for Flightline roles."""

import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


FORBIDDEN_GIT_OPERATIONS = {
    "add",
    "am",
    "apply",
    "branch",
    "checkout",
    "cherry-pick",
    "clean",
    "commit",
    "fetch",
    "merge",
    "mv",
    "pull",
    "push",
    "rebase",
    "reset",
    "restore",
    "revert",
    "rm",
    "stash",
    "switch",
    "tag",
    "worktree",
}
SAFE_GIT_OPERATIONS = {"diff", "log", "rev-parse", "show", "show-ref", "status"}
FLIGHTLINE_AUTHORITY_COMMANDS = {
    "issue-auditor",
    "launch",
    "preflight-auditor-schema",
    "prepare-worktree",
}
SHELL_OPERATORS = {"|", "||", "&&", ";", ">", ">>", "<", "<<", "&"}
SHELL_METACHARACTERS = frozenset("|;&<>$`\r\n\0")
EXTERNAL_TOOL_MARKERS = {
    "apps",
    "browser",
    "collaboration",
    "computer",
    "image_gen",
    "mcp",
    "request_permissions",
    "web",
}


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _deny(reason: str, event_name: str = "PreToolUse") -> Dict[str, Any]:
    if event_name == "PermissionRequest":
        return {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "deny", "message": reason},
            },
        }
    return {
        "continue": True,
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }


def _allow() -> Dict[str, Any]:
    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        },
    }


def _load_envelope(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("envelope is not an object")
    return value


def _normalized_tool(tool_name: str) -> str:
    return tool_name.rsplit(".", 1)[-1].lower()


def _approved_prefix(argv: Sequence[str], prefixes: Sequence[Sequence[str]]) -> bool:
    return any(list(argv[: len(prefix)]) == list(prefix) for prefix in prefixes)


def _git_subcommand(argv: Sequence[str]) -> Optional[str]:
    if not argv or Path(argv[0]).name != "git":
        return None
    index = 1
    options_with_values = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
    while index < len(argv):
        token = argv[index]
        if token in options_with_values:
            index += 2
            continue
        if any(token.startswith(value + "=") for value in options_with_values if value.startswith("--")):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return ""


def _flightline_authority_command(argv: Sequence[str]) -> Optional[str]:
    for index, token in enumerate(argv):
        if token == "tools.flightline.flightline" and index > 0 and argv[index - 1] == "-m":
            return argv[index + 1] if index + 1 < len(argv) else ""
        if Path(token).name == "flightline.py":
            return argv[index + 1] if index + 1 < len(argv) else ""
    return None


def _shell_decision(tool_input: Mapping[str, Any], envelope: Mapping[str, Any]) -> Dict[str, Any]:
    command_value = tool_input.get("cmd", tool_input.get("command"))
    if isinstance(command_value, list):
        argv = [str(value) for value in command_value]
        if any(any(character in token for character in SHELL_METACHARACTERS) for token in argv):
            return _deny("shell expansion and control syntax are not allowed")
    elif isinstance(command_value, str):
        if any(character in command_value for character in SHELL_METACHARACTERS):
            return _deny("shell expansion and control syntax are not allowed")
        try:
            argv = shlex.split(command_value)
        except ValueError:
            return _deny("command cannot be parsed safely")
    else:
        return _deny("shell command is missing")
    if not argv:
        return _deny("empty commands are not allowed")
    if any(token in SHELL_OPERATORS for token in argv):
        return _deny("shell control operators are not allowed")
    executable = Path(argv[0]).name
    if executable in {"sh", "bash", "zsh", "fish", "dash", "osascript", "codex"}:
        return _deny("nested command interpreters are outside Flightline authority")
    git_subcommand = _git_subcommand(argv)
    if git_subcommand is not None and (
        git_subcommand in FORBIDDEN_GIT_OPERATIONS or git_subcommand not in SAFE_GIT_OPERATIONS
    ):
        return _deny("Git mutation or unsupported Git operation is outside Flightline authority")
    authority_command = _flightline_authority_command(argv)
    if authority_command in FLIGHTLINE_AUTHORITY_COMMANDS:
        return _deny("a Flightline role cannot issue or consume its own authorization")
    if executable in {"rm", "rmdir", "mv", "chmod", "chown", "sudo"}:
        return _deny("destructive or privilege-changing command is outside Flightline authority")
    if not _approved_prefix(argv, envelope.get("approved_command_prefixes", [])):
        return _deny("command is not in the approved prefix allowlist")

    cwd_value = tool_input.get("workdir", tool_input.get("cwd", envelope.get("worktree_path")))
    try:
        cwd = Path(str(cwd_value)).resolve(strict=False)
        worktree = Path(str(envelope["worktree_path"])).resolve(strict=False)
        temp_roots = [Path(str(value)).resolve(strict=False) for value in envelope.get("allowed_temp_paths", [])]
    except (KeyError, OSError):
        return _deny("command working directory cannot be validated")
    if not (_is_within(cwd, worktree) or any(_is_within(cwd, root) for root in temp_roots)):
        return _deny("command working directory is outside the isolated role scope")
    if tool_input.get("sandbox_permissions") not in (None, "use_default"):
        return _deny("sandbox escalation is forbidden")
    return _allow()


def _patch_paths(patch: str) -> List[str]:
    prefixes = ("*** Add File: ", "*** Update File: ", "*** Delete File: ", "*** Move to: ")
    return [line[len(prefix) :] for line in patch.splitlines() for prefix in prefixes if line.startswith(prefix)]


def _patch_decision(tool_input: Mapping[str, Any], envelope: Mapping[str, Any]) -> Dict[str, Any]:
    if envelope.get("role") != "development-engineer":
        return _deny("the Auditor cannot edit production files")
    patch = tool_input.get("patch", tool_input.get("input", ""))
    if not isinstance(patch, str) or not patch:
        return _deny("patch content is missing")
    if "*** Delete File:" in patch or "*** Move to:" in patch:
        return _deny("deletions and moves are not authorized")
    worktree = Path(str(envelope["worktree_path"])).resolve(strict=False)
    allowed = [Path(str(value)).resolve(strict=False) for value in envelope.get("allowed_write_paths", [])]
    paths = _patch_paths(patch)
    if not paths:
        return _deny("patch targets cannot be determined")
    for value in paths:
        target = Path(value)
        if not target.is_absolute():
            target = worktree / target
        target = target.resolve(strict=False)
        if not any(_is_within(target, root) or target == root for root in allowed):
            return _deny("patch target is outside approved writable scope")
    return _allow()


def evaluate(payload: Mapping[str, Any], envelope: Mapping[str, Any]) -> Dict[str, Any]:
    event_name = str(payload.get("hook_event_name", ""))
    if event_name == "PermissionRequest":
        return _deny("Flightline approval policy is fail-closed", event_name="PermissionRequest")
    if event_name != "PreToolUse":
        return _deny("unexpected hook event")
    tool_name = str(payload.get("tool_name", ""))
    normalized = _normalized_tool(tool_name)
    lowered = tool_name.lower()
    if any(marker in lowered for marker in EXTERNAL_TOOL_MARKERS):
        return _deny("external, delegated, or permission tools are disabled")
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return _deny("tool input is not an object")
    if normalized in {"exec_command", "shell", "shell_command", "unified_exec"}:
        return _shell_decision(tool_input, envelope)
    if normalized == "apply_patch":
        return _patch_decision(tool_input, envelope)
    if normalized in envelope.get("allowed_tools", []):
        return _allow()
    return _deny("tool is not in the approved allowlist")


def main() -> int:
    envelope_value = os.environ.get("WINGMAN_FLIGHTLINE_ENVELOPE")
    if not envelope_value:
        print(json.dumps(_deny("Flightline envelope environment is missing")))
        return 0
    try:
        payload = json.load(sys.stdin)
        envelope = _load_envelope(Path(envelope_value).resolve())
        if not isinstance(payload, dict):
            raise ValueError("hook payload is not an object")
        decision = evaluate(payload, envelope)
    except Exception as exc:  # Hooks must fail closed on every parsing error.
        decision = _deny("Flightline guard failed closed: {}".format(type(exc).__name__))
    print(json.dumps(decision, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
