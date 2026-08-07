"""Focused safety tests for bounded local-folder discovery."""

import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from wingman.core.folder_intake import (  # noqa: E402
    collect_folder_entries,
    normalized_relative_path,
    read_selected_file,
    resolve_selected_path,
)


class FolderIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name) / "selected"
        self.root.mkdir()

    def write(self, relative, content=b"content"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_non_recursive_default_excludes_hidden_and_sorts(self):
        self.write("zeta.txt")
        self.write("Alpha.md")
        self.write("nested/inside.txt")
        self.write(".hidden.txt")
        self.write(".private/inside.txt")

        entries = collect_folder_entries(self.root)

        self.assertEqual(
            [entry.relative_path for entry in entries],
            ["Alpha.md", "zeta.txt"],
        )
        self.assertTrue(all(entry.accepted for entry in entries))

    def test_recursion_and_hidden_entries_require_explicit_options(self):
        self.write("nested/B.txt")
        self.write(".private/A.txt")
        entries = collect_folder_entries(
            self.root,
            recursive=True,
            include_hidden=True,
        )
        self.assertEqual(
            [entry.relative_path for entry in entries],
            [".private/A.txt", "nested/B.txt"],
        )

    def test_symlink_files_and_directories_are_rejected_without_following(self):
        target_file = self.write("target.txt")
        target_directory = self.root / "target-directory"
        target_directory.mkdir()
        self.write("target-directory/inside.txt")
        file_link = self.root / "file-link.txt"
        directory_link = self.root / "directory-link"
        try:
            file_link.symlink_to(target_file)
            directory_link.symlink_to(target_directory, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Symlinks are unavailable: {error}")

        entries = collect_folder_entries(self.root, recursive=True)
        rejected = {
            entry.relative_path: entry.reason_code
            for entry in entries
            if not entry.accepted
        }
        self.assertEqual(rejected["file-link.txt"], "path_symlink")
        self.assertEqual(rejected["directory-link"], "path_symlink")
        self.assertNotIn("directory-link/inside.txt", rejected)

    def test_single_hard_link_inside_root_is_rejected(self):
        outside = self.root.parent / "outside.txt"
        outside.write_bytes(b"outside")
        linked = self.root / "linked.txt"
        try:
            os.link(outside, linked)
        except OSError as error:
            self.skipTest(f"Hard links are unavailable: {error}")

        entries = collect_folder_entries(self.root)
        self.assertEqual(len(entries), 1)
        self.assertFalse(entries[0].accepted)
        self.assertEqual(entries[0].reason_code, "path_hard_link")

    def test_previewed_file_cannot_be_replaced_by_symlink(self):
        selected = self.write("selected.txt", b"selected")
        entry = collect_folder_entries(self.root)[0]
        outside = self.root.parent / "outside.txt"
        outside.write_bytes(b"outside")
        selected.unlink()
        try:
            selected.symlink_to(outside)
        except OSError as error:
            self.skipTest(f"Symlinks are unavailable: {error}")

        with self.assertRaisesRegex(OSError, "safe preview"):
            read_selected_file(
                entry.root,
                entry.relative_path,
                expected_root_identity=entry.root_identity,
                expected_file_identity=entry.file_identity,
            )

    def test_relative_paths_reject_parent_absolute_and_alias_segments(self):
        for value in (
            "../escape.txt",
            "/escape.txt",
            "C:/escape.txt",
            "folder/./file.txt",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalized_relative_path(value)

    def test_resolve_selected_path_stays_confined(self):
        selected = self.write("nested/file.txt")
        self.assertEqual(
            resolve_selected_path(self.root, "nested/file.txt"),
            selected.resolve(),
        )
        with self.assertRaises(ValueError):
            resolve_selected_path(self.root, "../outside.txt")

    def test_root_symlink_is_rejected(self):
        link = self.root.parent / "selected-link"
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Symlinks are unavailable: {error}")
        with self.assertRaisesRegex(ValueError, "root cannot be a symbolic"):
            collect_folder_entries(link)


if __name__ == "__main__":
    unittest.main()
