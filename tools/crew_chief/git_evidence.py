"""Git-only evidence capture for Crew Chief audit envelopes."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from typing import Any

from tools.crew_chief.core import (
    CrewChiefError,
    canonical_json_bytes,
    normalize_repo_path,
    payload_encoding,
    sha256_bytes,
    validate_subject_path,
)


def _git(
    repository: Path,
    arguments: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
    )
    if check and result.returncode != 0:
        diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
        raise CrewChiefError(
            f"Git command failed ({' '.join(arguments)}): {diagnostic}"
        )
    return result


def _decode(value: bytes, label: str) -> str:
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CrewChiefError(f"{label} is not valid UTF-8") from error


def resolve_repository(path: Path) -> Path:
    result = _git(path, ["rev-parse", "--show-toplevel"])
    root = Path(_decode(result.stdout, "repository root").strip()).resolve()
    if root != path.resolve():
        raise CrewChiefError(
            f"authorized repository must be its canonical Git root: {root}"
        )
    return root


def resolve_commit(repository: Path, revision: str) -> str:
    result = _git(repository, ["rev-parse", "--verify", f"{revision}^{{commit}}"])
    commit = _decode(result.stdout, "commit ID").strip()
    if len(commit) != 40:
        raise CrewChiefError(f"Git did not resolve a full commit ID: {revision}")
    return commit


def repository_identity(repository: Path) -> dict[str, Any]:
    common = _decode(
        _git(repository, ["rev-parse", "--git-common-dir"]).stdout,
        "Git common directory",
    ).strip()
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = repository / common_path
    roots = _decode(
        _git(repository, ["rev-list", "--max-parents=0", "HEAD"]).stdout,
        "repository root commits",
    ).splitlines()
    identity_payload = {
        "git_common_dir": str(common_path.resolve()),
        "repository_root": str(repository.resolve()),
        "root_commits": sorted(roots),
    }
    return {
        **identity_payload,
        "repository_id": sha256_bytes(canonical_json_bytes(identity_payload)),
    }


def _zlist(value: bytes, label: str) -> list[str]:
    items = []
    for raw in value.split(b"\0"):
        if not raw:
            continue
        items.append(normalize_repo_path(_decode(raw, label)))
    return items


def _diff_paths(repository: Path, arguments: list[str]) -> list[str]:
    return _zlist(
        _git(repository, ["diff", "--name-only", "-z", *arguments]).stdout,
        "changed path",
    )


def untracked_paths(repository: Path) -> list[str]:
    return _zlist(
        _git(
            repository,
            ["ls-files", "--others", "--exclude-standard", "-z"],
        ).stdout,
        "untracked path",
    )


def git_state(repository: Path) -> dict[str, Any]:
    head = resolve_commit(repository, "HEAD")
    branch_result = _git(
        repository, ["symbolic-ref", "--quiet", "--short", "HEAD"], check=False
    )
    branch = (
        _decode(branch_result.stdout, "branch").strip()
        if branch_result.returncode == 0
        else "DETACHED"
    )
    staged_paths = set(_diff_paths(repository, ["--cached"]))
    unstaged_paths = set(_diff_paths(repository, []))
    observed_untracked = set(untracked_paths(repository))
    for path in sorted(staged_paths | unstaged_paths | observed_untracked):
        validate_subject_path(path)
    raw_status = _git(
        repository,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    ).stdout
    status = [_decode(item, "Git status") for item in raw_status.split(b"\0") if item]
    staged = _git(repository, ["diff", "--cached", "--binary", "--full-index"]).stdout
    unstaged = _git(repository, ["diff", "--binary", "--full-index"]).stdout
    value = {
        "head": head,
        "branch": branch,
        "status_porcelain_v1": status,
        "staged_diff_sha256": sha256_bytes(staged),
        "unstaged_diff_sha256": sha256_bytes(unstaged),
        "untracked_paths": sorted(observed_untracked),
    }
    value["state_hash"] = sha256_bytes(canonical_json_bytes(value))
    return value


def is_ancestor(repository: Path, base: str, head: str) -> bool:
    return (
        _git(
            repository,
            ["merge-base", "--is-ancestor", base, head],
            check=False,
        ).returncode
        == 0
    )


def _git_blob(repository: Path, specification: str) -> bytes | None:
    result = _git(repository, ["show", specification], check=False)
    return result.stdout if result.returncode == 0 else None


def _tree_mode(repository: Path, revision: str, path: str) -> str | None:
    result = _git(repository, ["ls-tree", "-z", revision, "--", path])
    if not result.stdout:
        return None
    header = result.stdout.split(b"\t", 1)[0]
    return _decode(header.split(b" ", 1)[0], "Git file mode")


def _index_mode(repository: Path, path: str) -> str | None:
    result = _git(repository, ["ls-files", "-s", "-z", "--", path])
    if not result.stdout:
        return None
    return _decode(result.stdout.split(b" ", 1)[0], "index file mode")


def _mode_type(mode: str | None) -> str | None:
    if mode is None:
        return None
    return {
        "100644": "regular",
        "100755": "executable",
        "120000": "symlink",
        "160000": "submodule",
    }.get(mode, "other")


def _worktree_value(repository: Path, path: str) -> tuple[str | None, bytes | None]:
    candidate = repository.joinpath(*Path(path).parts)
    if not candidate.exists() and not candidate.is_symlink():
        return None, None
    parent = candidate.parent.resolve()
    try:
        parent.relative_to(repository.resolve())
    except ValueError as error:
        raise CrewChiefError(f"changed path escapes through a symlink: {path}") from error
    metadata = candidate.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        payload = os.readlink(candidate).encode("utf-8")
        mode = "120000"
    elif stat.S_ISREG(metadata.st_mode):
        payload = candidate.read_bytes()
        mode = "100755" if metadata.st_mode & stat.S_IXUSR else "100644"
    else:
        raise CrewChiefError(f"unsupported changed file type: {path}")
    return mode, payload


def _blob_hash(value: bytes | None) -> str | None:
    return sha256_bytes(value) if value is not None else None


def _material_entry(
    path: str,
    state: str,
    revision: str,
    mode: str | None,
    payload: bytes | None,
) -> tuple[dict[str, Any], tuple[str, bytes] | None]:
    file_type = _mode_type(mode)
    if mode is None:
        return (
            {
                "repository_path": path,
                "state": state,
                "revision": revision,
                "presence": "absent",
                "file_type": None,
                "mode": None,
                "size": None,
                "encoding": None,
                "line_count": None,
                "frozen": None,
            },
            None,
        )
    if file_type == "submodule":
        return (
            {
                "repository_path": path,
                "state": state,
                "revision": revision,
                "presence": "present",
                "file_type": file_type,
                "mode": mode,
                "size": None,
                "encoding": "gitlink",
                "line_count": None,
                "frozen": None,
            },
            None,
        )
    if payload is None:
        raise CrewChiefError(
            f"unable to freeze {state} content for changed path: {path}"
        )
    digest = sha256_bytes(payload)
    encoding, line_count = payload_encoding(payload)
    relative = f"source-content/sha256/{digest}"
    binding = {"path": relative, "sha256": digest, "size": len(payload)}
    return (
        {
            "repository_path": path,
            "state": state,
            "revision": revision,
            "presence": "present",
            "file_type": file_type,
            "mode": mode,
            "size": len(payload),
            "encoding": encoding,
            "line_count": line_count,
            "frozen": binding,
        },
        (relative, payload),
    )


def capture_subject(
    repository: Path,
    base: str,
    head: str,
    *,
    include_worktree: bool,
    authorized_untracked: list[str],
) -> tuple[dict[str, Any], dict[str, bytes], dict[str, bytes]]:
    """Capture deterministic inventory, diffs, and deduplicated source bytes."""
    committed_paths = set(_diff_paths(repository, [base, head]))
    staged_paths = set(_diff_paths(repository, ["--cached"]))
    unstaged_paths = set(_diff_paths(repository, []))
    observed_untracked = set(untracked_paths(repository))
    allowed_untracked = {
        validate_subject_path(path) for path in authorized_untracked
    }
    for path in sorted(
        committed_paths | staged_paths | unstaged_paths | observed_untracked
    ):
        validate_subject_path(path)

    if include_worktree:
        if observed_untracked != allowed_untracked:
            missing = sorted(observed_untracked - allowed_untracked)
            unexpected = sorted(allowed_untracked - observed_untracked)
            raise CrewChiefError(
                "untracked allowlist does not bind the working tree; "
                f"unbound={missing}, absent={unexpected}"
            )
    elif staged_paths or unstaged_paths or observed_untracked:
        raise CrewChiefError(
            "committed-range audit requires a clean index and working tree"
        )

    paths = set(committed_paths)
    if include_worktree:
        paths.update(staged_paths)
        paths.update(unstaged_paths)
        paths.update(observed_untracked)
    if not paths:
        raise CrewChiefError("audit subject contains no changed files")

    diffs = {
        "committed.diff": _git(
            repository,
            ["diff", "--binary", "--full-index", base, head],
        ).stdout,
    }
    if include_worktree:
        diffs["staged.diff"] = _git(
            repository, ["diff", "--cached", "--binary", "--full-index"]
        ).stdout
        diffs["unstaged.diff"] = _git(
            repository, ["diff", "--binary", "--full-index"]
        ).stdout

    inventory: list[dict[str, Any]] = []
    source_material: list[dict[str, Any]] = []
    content_payloads: dict[str, bytes] = {}
    for raw_path in sorted(paths):
        path = validate_subject_path(raw_path)
        sources = []
        for label, collection in (
            ("committed", committed_paths),
            ("staged", staged_paths),
            ("unstaged", unstaged_paths),
            ("untracked", observed_untracked),
        ):
            if path in collection:
                sources.append(label)
        base_blob = _git_blob(repository, f"{base}:{path}")
        head_blob = _git_blob(repository, f"{head}:{path}")
        index_blob = _git_blob(repository, f":{path}")
        worktree_mode, worktree_blob = _worktree_value(repository, path)
        if path in observed_untracked and worktree_mode == "120000":
            raise CrewChiefError(f"authorized untracked symlink is forbidden: {path}")
        modes = {
            "base": _tree_mode(repository, base, path),
            "head": _tree_mode(repository, head, path),
            "index": _index_mode(repository, path),
            "worktree": worktree_mode,
        }
        effective_mode = next(
            (modes[name] for name in ("worktree", "index", "head", "base") if modes[name]),
            None,
        )
        inventory.append(
            {
                "path": path,
                "sources": sources,
                "file_type": _mode_type(effective_mode),
                "modes": modes,
                "sha256": {
                    "base": _blob_hash(base_blob),
                    "head": _blob_hash(head_blob),
                    "index": _blob_hash(index_blob),
                    "worktree": _blob_hash(worktree_blob),
                },
            }
        )
        states = [
            ("base", base, modes["base"], base_blob),
            ("head", head, modes["head"], head_blob),
        ]
        if include_worktree:
            states.extend(
                [
                    ("index", "INDEX", modes["index"], index_blob),
                    ("worktree", "WORKTREE", modes["worktree"], worktree_blob),
                ]
            )
        for state, revision, mode, payload in states:
            material, frozen_payload = _material_entry(
                path, state, revision, mode, payload
            )
            source_material.append(material)
            if frozen_payload is not None:
                relative, frozen_bytes = frozen_payload
                existing = content_payloads.setdefault(relative, frozen_bytes)
                if existing != frozen_bytes:
                    raise CrewChiefError(
                        f"source content digest collision detected: {relative}"
                    )

    subject = {
        "mode": "working-tree" if include_worktree else "committed-range",
        "base_commit": base,
        "head_commit": head,
        "authorized_untracked": sorted(allowed_untracked),
        "changed_files": inventory,
        "source_material": source_material,
    }
    return subject, diffs, content_payloads
