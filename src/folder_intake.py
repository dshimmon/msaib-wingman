"""Bounded, deterministic local-folder document discovery."""

import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath


@dataclass(frozen=True)
class FolderEntry:
    """One safe regular file or one rejected filesystem entry."""

    relative_path: str
    path: Path | None
    reason_code: str | None = None
    message: str | None = None
    root: Path | None = None
    root_identity: tuple[int, int] | None = None
    file_identity: tuple[int, int] | None = None

    @property
    def accepted(self):
        return self.path is not None and self.reason_code is None


def normalized_relative_path(value):
    """Validate and normalize a portable manifest-relative path."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A relative file path is required.")
    normalized = value.replace("\\", "/")
    raw_parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise ValueError("File paths cannot contain aliases or empty segments.")
    relative = PurePosixPath(normalized)
    if relative.is_absolute() or PureWindowsPath(normalized).is_absolute():
        raise ValueError("File paths must remain relative to the selected root.")
    return relative.as_posix()


def validate_root(root):
    """Resolve exactly one real, non-symlink directory root."""
    root_path = Path(root)
    if ".." in root_path.parts:
        raise ValueError("The selected root cannot contain '..' aliases.")
    if root_path.is_symlink():
        raise ValueError("The selected root cannot be a symbolic link.")
    resolved = root_path.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError("The selected root must be a directory.")
    return resolved


def resolve_selected_path(root, relative_path):
    """Resolve one manifest path without permitting escape or symlinks."""
    resolved_root = validate_root(root)
    normalized = normalized_relative_path(relative_path)
    candidate = resolved_root.joinpath(*PurePosixPath(normalized).parts)
    current = resolved_root
    for part in PurePosixPath(normalized).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(
                f"Symbolic links are not accepted: {normalized}"
            )
    resolved_candidate = candidate.resolve(strict=True)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(
            "The selected file resolves outside the selected root."
        ) from error
    if not resolved_candidate.is_file():
        raise ValueError("The selected path must be a regular file.")
    return resolved_candidate


def _identity(stat_result):
    return (stat_result.st_dev, stat_result.st_ino)


def _safe_open_flags(*, directory=False):
    if not hasattr(os, "O_NOFOLLOW"):
        raise OSError("This platform cannot safely read selected folder files.")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    if directory:
        flags |= getattr(os, "O_DIRECTORY", 0)
    return flags


def read_selected_file(
    root,
    relative_path,
    *,
    expected_root_identity,
    expected_file_identity,
):
    """Read a previewed file without following replaced path components."""
    resolved_root = Path(root)
    normalized = normalized_relative_path(relative_path)
    parts = PurePosixPath(normalized).parts
    opened_directories = []
    file_descriptor = None
    try:
        root_descriptor = os.open(
            resolved_root,
            _safe_open_flags(directory=True),
        )
        opened_directories.append(root_descriptor)
        if _identity(os.fstat(root_descriptor)) != expected_root_identity:
            raise OSError("The selected folder changed after preview.")

        parent_descriptor = root_descriptor
        for part in parts[:-1]:
            parent_descriptor = os.open(
                part,
                _safe_open_flags(directory=True),
                dir_fd=parent_descriptor,
            )
            opened_directories.append(parent_descriptor)

        file_descriptor = os.open(
            parts[-1],
            _safe_open_flags(),
            dir_fd=parent_descriptor,
        )
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise OSError("The selected path is no longer a regular file.")
        if before.st_nlink != 1:
            raise OSError("Hard-linked files are not accepted.")
        if _identity(before) != expected_file_identity:
            raise OSError("The selected file changed after preview.")

        with os.fdopen(file_descriptor, "rb", closefd=True) as file_handle:
            file_descriptor = None
            content = file_handle.read()
            after = os.fstat(file_handle.fileno())
        if _identity(after) != expected_file_identity or after.st_nlink != 1:
            raise OSError("The selected file changed while it was read.")
        return content
    except (OSError, ValueError) as error:
        raise OSError(
            "The selected folder file no longer matches its safe preview."
        ) from error
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        for directory_descriptor in reversed(opened_directories):
            os.close(directory_descriptor)


def collect_folder_entries(root, *, recursive=False, include_hidden=False):
    """Collect files safely and sort them by normalized relative path."""
    resolved_root = validate_root(root)
    root_identity = _identity(resolved_root.stat(follow_symlinks=False))
    entries = []
    seen_files = {}
    seen_names = set()

    def visible(path):
        return include_hidden or not path.name.startswith(".")

    def relative_name(path):
        return path.relative_to(resolved_root).as_posix()

    def inspect_directory(directory):
        for child in sorted(
            directory.iterdir(),
            key=lambda path: (path.name.casefold(), path.name),
        ):
            if not visible(child):
                continue
            relative = relative_name(child)
            if child.is_symlink():
                entries.append(
                    FolderEntry(
                        relative,
                        None,
                        "path_symlink",
                        "Symbolic-link files and directories are not accepted.",
                    )
                )
                continue
            if child.is_dir():
                if recursive:
                    inspect_directory(child)
                continue
            if not child.is_file():
                entries.append(
                    FolderEntry(
                        relative,
                        None,
                        "path_not_regular",
                        "Only regular files are accepted.",
                    )
                )
                continue

            resolved_child = child.resolve(strict=True)
            try:
                resolved_child.relative_to(resolved_root)
            except ValueError:
                entries.append(
                    FolderEntry(
                        relative,
                        None,
                        "path_escape",
                        "The file resolves outside the selected root.",
                    )
                )
                continue

            stat_result = child.stat(follow_symlinks=False)
            if not stat.S_ISREG(stat_result.st_mode):
                entries.append(
                    FolderEntry(
                        relative,
                        None,
                        "path_changed",
                        "The selected path changed during folder discovery.",
                    )
                )
                continue
            identity = (stat_result.st_dev, stat_result.st_ino)
            if stat_result.st_nlink != 1:
                entries.append(
                    FolderEntry(
                        relative,
                        None,
                        "path_hard_link",
                        "Hard-linked files are not accepted.",
                    )
                )
                continue
            normalized_name = relative.casefold()
            prior = seen_files.get(identity)
            if prior is not None or normalized_name in seen_names:
                entries.append(
                    FolderEntry(
                        relative,
                        None,
                        "path_alias",
                        f"The file aliases another selected path: {prior or relative}",
                    )
                )
                continue
            seen_files[identity] = relative
            seen_names.add(normalized_name)
            entries.append(
                FolderEntry(
                    relative,
                    resolved_child,
                    root=resolved_root,
                    root_identity=root_identity,
                    file_identity=identity,
                )
            )

    inspect_directory(resolved_root)
    return sorted(
        entries,
        key=lambda entry: (
            entry.relative_path.casefold(),
            entry.relative_path,
        ),
    )
