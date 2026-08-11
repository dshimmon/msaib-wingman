"""Cooperative process locks and unambiguous Ledger path identity."""

from __future__ import annotations

import errno
import fcntl
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path


DEFAULT_LOCK_TIMEOUT_SECONDS = 5.0


class LedgerPathError(RuntimeError):
    """A Ledger target cannot be identified without ambiguity."""


class LedgerLockTimeout(TimeoutError):
    """The requested cooperative Ledger lock was not acquired in time."""


def _existing_components(path: Path):
    components = list(path.parents)
    components.reverse()
    components.append(path)
    for component in components:
        try:
            os.lstat(component)
        except FileNotFoundError:
            continue
        yield component


def canonical_database_path(
    database_path,
    *,
    create_parent=False,
    reject_alias=False,
):
    """Return one absolute target while rejecting symlink aliases."""
    supplied = Path(database_path)
    if reject_alias and not supplied.is_absolute():
        raise LedgerPathError(
            "Ledger transition paths must be absolute and canonical."
        )
    absolute = (
        supplied
        if supplied.is_absolute()
        else Path.cwd() / supplied
    )
    normalized = Path(os.path.abspath(absolute))

    target_is_symlink = normalized.is_symlink()
    if target_is_symlink:
        raise LedgerPathError("Ledger target may not be a symlink.")

    resolved_parent = normalized.parent.resolve(strict=False)
    resolved = resolved_parent / normalized.name
    if reject_alias and resolved != normalized:
        raise LedgerPathError("Ledger target uses a symlink path alias.")

    if create_parent:
        resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def database_identity(database_path):
    """Return the canonical path and stable filesystem identity."""
    path = canonical_database_path(database_path, reject_alias=True)
    details = {
        "canonical_path": str(path),
        "exists": path.exists(),
    }
    if path.exists():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise LedgerPathError("Ledger target must be a regular file.")
        if info.st_nlink != 1:
            raise LedgerPathError("Ledger target has a hard-link alias.")
        details.update(
            {
                "device": info.st_dev,
                "inode": info.st_ino,
                "size": info.st_size,
            }
        )
    return details


def lock_path_for(database_path):
    path = canonical_database_path(database_path, create_parent=True)
    return path.with_name(f".{path.name}.ledger.lock")


def recovery_journal_path_for(database_path):
    path = canonical_database_path(database_path)
    return path.with_name(f".{path.name}.recovery.json")


def assert_no_active_recovery(database_path):
    journal = recovery_journal_path_for(database_path)
    if journal.exists():
        raise RuntimeError(
            "Ledger recovery is incomplete; application access is blocked."
        )


@dataclass
class LedgerFileLock:
    """One bounded BSD advisory lock on a target-specific sidecar."""

    database_path: Path
    mode: str
    timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS
    descriptor: int | None = None

    def acquire(self):
        if self.mode not in {"shared", "exclusive"}:
            raise ValueError("Ledger lock mode must be shared or exclusive.")
        if self.descriptor is not None:
            raise RuntimeError("Ledger lock is already acquired.")

        lock_path = lock_path_for(self.database_path)
        descriptor = os.open(
            lock_path,
            os.O_RDWR
            | os.O_CREAT
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        lock_info = os.fstat(descriptor)
        if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_nlink != 1:
            os.close(descriptor)
            raise LedgerPathError("Ledger lock sidecar identity is unsafe.")
        self.descriptor = descriptor
        try:
            self._convert(self.mode)
        except Exception:
            os.close(descriptor)
            self.descriptor = None
            raise
        return self

    def _convert(self, mode):
        if self.descriptor is None:
            raise RuntimeError("Ledger lock is not acquired.")
        operation = (
            fcntl.LOCK_SH if mode == "shared" else fcntl.LOCK_EX
        )
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fcntl.flock(
                    self.descriptor,
                    operation | fcntl.LOCK_NB,
                )
                self.mode = mode
                return
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN}:
                    raise
                if time.monotonic() >= deadline:
                    raise LedgerLockTimeout(
                        f"Timed out acquiring {mode} Ledger lock."
                    ) from error
                time.sleep(0.01)

    def release(self):
        if self.descriptor is None:
            return
        try:
            fcntl.flock(self.descriptor, fcntl.LOCK_UN)
        finally:
            os.close(self.descriptor)
            self.descriptor = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        return False
