"""Fail-closed Git inspection and execution primitives for LSO v1."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from tools.crew_chief.git_evidence import (
    git_state,
    is_ancestor,
    repository_identity,
    resolve_commit,
    resolve_repository,
    untracked_paths,
)
from tools.crew_chief.core import atomic_write, redact_text
from tools.lso.core import LSOError, validate_subject_path


@dataclass(frozen=True)
class GitIndexSnapshot:
    path: Path
    payload: bytes
    mode: int


def git(
    repository: Path,
    *arguments: str,
    check: bool = True,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_EDITOR": "true",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    if extra_environment:
        environment.update(extra_environment)
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        diagnostic = redact_text((result.stderr or result.stdout).strip())
        raise LSOError(f"Git operation failed ({' '.join(arguments)}): {diagnostic}")
    return result


def branch_name(repository: Path) -> str:
    value = git(repository, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    if not value or value == "main" or not value.startswith("codex/"):
        raise LSOError("LSO requires a non-main codex/* implementation branch")
    return value


def remote_url_hash_input(repository: Path, remote: str) -> str:
    value = git(repository, "remote", "get-url", remote).stdout.strip()
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"} and (parsed.username or parsed.password):
        raise LSOError("credential-bearing Git remote URL is forbidden")
    if not value:
        raise LSOError(f"Git remote has no URL: {remote}")
    return value


def receipt_consumption_directory(repository: Path, repository_id: str) -> Path:
    """Return the durable repository-scoped receipt-consumption directory."""
    identity = repository_identity(repository)
    if identity["repository_id"] != repository_id:
        raise LSOError("LSO repository identity changed before receipt consumption")
    common = Path(identity["git_common_dir"])
    if common.is_symlink() or not common.is_dir():
        raise LSOError("LSO Git common directory is invalid")
    return common / "wingman-lso" / "consumed" / repository_id


def changed_path_sets(repository: Path) -> tuple[set[str], set[str], set[str]]:
    def paths(*arguments: str) -> set[str]:
        value = git(repository, *arguments).stdout
        return {validate_subject_path(item) for item in value.splitlines() if item}

    staged = paths("diff", "--cached", "--name-only")
    unstaged = paths("diff", "--name-only")
    untracked = {validate_subject_path(item) for item in untracked_paths(repository)}
    return staged, unstaged, untracked


def capture_index(repository: Path) -> GitIndexSnapshot:
    """Capture the exact real-worktree index before an authorized mutation."""
    value = git(
        repository,
        "rev-parse",
        "--path-format=absolute",
        "--git-path",
        "index",
    ).stdout.strip()
    path = Path(value)
    if not path.is_absolute():
        path = repository / path
    path = Path(os.path.abspath(path))
    if path.is_symlink() or not path.is_file():
        raise LSOError("LSO real Git index must be a regular non-symlink file")
    return GitIndexSnapshot(
        path=path,
        payload=path.read_bytes(),
        mode=stat.S_IMODE(path.stat().st_mode),
    )


def restore_index(snapshot: GitIndexSnapshot) -> None:
    """Atomically restore and verify one captured real-worktree index."""
    if snapshot.path.is_symlink():
        raise LSOError("LSO real Git index became a symlink before restoration")
    atomic_write(snapshot.path, snapshot.payload)
    snapshot.path.chmod(snapshot.mode)
    if (
        snapshot.path.is_symlink()
        or not snapshot.path.is_file()
        or snapshot.path.read_bytes() != snapshot.payload
        or stat.S_IMODE(snapshot.path.stat().st_mode) != snapshot.mode
    ):
        raise LSOError("LSO could not restore the exact pre-execution Git index")


def expected_tree(repository: Path, authorized_paths: list[str]) -> str:
    if not authorized_paths:
        raise LSOError("LSO closeout requires at least one audited path")
    with tempfile.TemporaryDirectory(prefix="wingman-lso-index-") as temporary:
        index = Path(temporary) / "index"
        environment = {"GIT_INDEX_FILE": str(index)}
        git(repository, "read-tree", "HEAD", extra_environment=environment)
        git(
            repository,
            "add",
            "--all",
            "--",
            *authorized_paths,
            extra_environment=environment,
        )
        git(
            repository,
            "diff",
            "--cached",
            "--check",
            extra_environment=environment,
        )
        return git(
            repository, "write-tree", extra_environment=environment
        ).stdout.strip()


def remote_head(repository: Path, remote: str, branch: str) -> str:
    result = git(
        repository,
        "ls-remote",
        "--heads",
        remote,
        f"refs/heads/{branch}",
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise LSOError(f"remote branch is missing or ambiguous: {remote}/{branch}")
    commit, reference = lines[0].split("\t", 1)
    if reference != f"refs/heads/{branch}" or len(commit) != 40:
        raise LSOError(f"remote branch response is malformed: {remote}/{branch}")
    return commit


__all__ = [
    "branch_name",
    "capture_index",
    "changed_path_sets",
    "expected_tree",
    "git",
    "git_state",
    "is_ancestor",
    "remote_head",
    "remote_url_hash_input",
    "receipt_consumption_directory",
    "repository_identity",
    "restore_index",
    "resolve_commit",
    "resolve_repository",
]
