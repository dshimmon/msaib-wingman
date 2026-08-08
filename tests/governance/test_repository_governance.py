"""Executable checks for canonical repository-governance records."""

import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from tools.governance import repository


class RepositoryGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.missions = repository.load_missions()
        cls.decisions = repository.load_decisions()

    def test_live_repository_satisfies_all_governance_invariants(self):
        self.assertEqual(repository.validate(), [])

    def test_generated_views_are_fresh(self):
        self.assertEqual(
            repository.validate_generated(self.missions, self.decisions), []
        )

    def _mission(self, mission_id):
        return next(
            record for record in self.missions
            if record.metadata["id"] == mission_id
        )

    def _with_metadata(self, record, **changes):
        metadata = copy.deepcopy(record.metadata)
        metadata.update(changes)
        return repository.Record(record.path, metadata)

    def test_bulk_ingestion_conflict_is_rejected(self):
        record = self._mission("atlas/bulk-ingestion")
        errors = repository.validate_mission_journal_authority(
            [record], exists=lambda path: path.name == "journal.md"
        )
        self.assertEqual(
            errors,
            ["atlas/bulk-ingestion: completed mission retains competing journal.md"],
        )

    def test_prompt_optimizer_conflict_is_rejected(self):
        record = self._mission("wingman-os/prompt-optimizer")
        errors = repository.validate_mission_journal_authority(
            [record], exists=lambda path: path.name == "journal.md"
        )
        self.assertEqual(
            errors,
            [
                "wingman-os/prompt-optimizer: completed mission retains "
                "competing journal.md"
            ],
        )

    def test_any_completed_mission_retaining_journal_is_rejected(self):
        record = self._mission("wingman-os/foundation")
        errors = repository.validate_mission_journal_authority(
            [record], exists=lambda path: True
        )
        self.assertTrue(any("competing journal.md" in error for error in errors))

    def test_schema_rejects_malformed_priority(self):
        record = self._with_metadata(self.missions[0], priority={"rank": 1})
        errors = repository.validate_record_schemas([record], self.decisions)
        self.assertTrue(any("priority" in error for error in errors), errors)

    def test_schema_rejects_unexpected_metadata_field(self):
        record = self._with_metadata(self.missions[0], unexpected="claim")
        errors = repository.validate_record_schemas([record], self.decisions)
        self.assertTrue(
            any("Additional properties" in error for error in errors), errors
        )

    def test_schema_rejects_malformed_approval_evidence(self):
        record = self._with_metadata(
            self.missions[0],
            approval_evidence=[{"date": "2026-08-07", "authority": "Maverick"}],
        )
        errors = repository.validate_record_schemas([record], self.decisions)
        self.assertTrue(any("scope" in error for error in errors), errors)

    def test_decision_schema_rejects_unexpected_and_malformed_evidence(self):
        metadata = copy.deepcopy(self.decisions[0].metadata)
        metadata["approval_evidence"] = {"unsupported": True}
        metadata["unexpected"] = "claim"
        record = repository.Record(self.decisions[0].path, metadata)
        errors = repository.validate_record_schemas(self.missions, [record])
        self.assertTrue(
            any("approval_evidence" in error for error in errors), errors
        )
        self.assertTrue(
            any("Additional properties" in error for error in errors), errors
        )

    def test_false_pushed_and_merged_claims_are_rejected(self):
        record = self._with_metadata(
            self._mission("atlas/bulk-ingestion"), pushed=True, merged=True
        )
        with (
            patch.object(repository, "_remote_refs_containing", return_value=()),
            patch.object(repository, "_merge_target_contains", return_value=False),
        ):
            errors = repository.validate_publication_evidence([record])
        self.assertTrue(any("pushed=True contradicts" in error for error in errors))
        self.assertTrue(any("merged=True contradicts" in error for error in errors))

    def test_invalid_unreachable_active_mission_commit_is_rejected(self):
        record = self._with_metadata(
            self._mission("governance/repository-architecture"),
            implementation_commits=["f" * 40],
        )
        with (
            patch.object(repository, "_commit_exists", return_value=False),
            patch.object(repository, "_commit_is_reachable", return_value=False),
            patch.object(repository, "_remote_refs_containing", return_value=()),
            patch.object(repository, "_merge_target_contains", return_value=False),
        ):
            errors = repository.validate_metadata([record], self.decisions)
        self.assertTrue(
            any("recorded commit does not exist" in error for error in errors),
            errors,
        )

    def test_repository_relative_link_may_not_escape_root(self):
        errors = repository.validate_link_target(
            repository.ROOT / "README.md", "../outside.md"
        )
        self.assertTrue(any("escapes root" in error for error in errors), errors)

    def test_repository_map_matches_canonical_locations(self):
        self.assertEqual(repository.validate_repository_map(), [])

    def test_repository_map_rejects_missing_canonical_location(self):
        text = repository.REPOSITORY_MAP.read_text(encoding="utf-8").replace(
            "`docs/missions/operations/`",
            "`docs/missions/ops/`",
        )
        errors = repository.validate_repository_map(text)
        self.assertIn(
            "repository map omits canonical location: docs/missions/operations/",
            errors,
        )

    def test_repository_map_rejects_nonexistent_mapped_directory(self):
        location = "src/products/vector/"
        text = repository.REPOSITORY_MAP.read_text(encoding="utf-8").replace(
            "    radar/                                # `src/products/radar/`",
            "    radar/                                # `src/products/radar/`"
            f"\n    vector/                               # `{location}`",
        )
        errors = repository.validate_repository_map(text)
        self.assertIn(
            "repository map mapped directory does not exist: " + location,
            errors,
        )

    def test_repository_map_requires_compatibility_facade_warning(self):
        text = repository.REPOSITORY_MAP.read_text(encoding="utf-8").replace(
            "no new implementation belongs there.",
            "legacy imports remain supported.",
        )
        errors = repository.validate_repository_map(text)
        self.assertTrue(
            any("compatibility facades only" in error for error in errors),
            errors,
        )

    def test_full_implementation_disguised_as_facade_is_rejected(self):
        source = '''"""Compatibility facade for the historical `knowledge` module."""
from wingman.shared.compatibility import expose as _expose

def hidden_implementation():
    return "not thin"

_expose(__name__, "knowledge")
'''
        errors = repository.validate_facade_source(source, "knowledge")
        self.assertEqual(errors, ["facade does not match the permitted thin AST"])

    def test_archived_snapshot_without_local_banner_is_rejected(self):
        path = repository.ARCHIVE_ROOT / "architecture" / "unlabeled.md"
        errors = repository.validate_archive_document(
            path, "# Current repository\n\nStatus: complete\n"
        )
        self.assertTrue(
            any("archive classification" in error for error in errors), errors
        )

    def test_foreground_preservation_manifest_is_self_consistent(self):
        path = (
            repository.MISSION_ROOT
            / "governance/repository-architecture/artifacts"
            / "foreground-preservation-manifest.json"
        )
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            repository.validate_foreground_preservation_manifest(manifest), []
        )
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(len(manifest["entries"]), 11)
        self.assertEqual(
            manifest["path_disposition_counts"],
            {"deleted": 3, "moved": 5, "unchanged": 3},
        )
        self.assertTrue(manifest["protected_foreground_versions_excluded"])
        self.assertTrue(
            repository._commit_is_reachable(manifest["correction_comparison_head"])
        )
        for entry in manifest["entries"]:
            with self.subTest(path=entry["path"]):
                self.assertFalse(entry["foreground_version_incorporated"])
                self.assertEqual(
                    entry["exact_working_version_matches_in_correction"], []
                )
                target = entry["target_path"]
                if target is None:
                    self.assertIsNone(entry["target_path_sha256"])
                    continue
                digest = hashlib.sha256(
                    (repository.ROOT / target).read_bytes()
                ).hexdigest()
                self.assertEqual(digest, entry["target_path_sha256"])

    def test_wrong_existing_foreground_rename_target_is_rejected(self):
        path = repository.FOREGROUND_PRESERVATION_MANIFEST
        manifest = json.loads(path.read_text(encoding="utf-8"))
        wrong_target = "docs/archive/governance/pre-mission-message.txt"
        entry = next(
            item for item in manifest["entries"]
            if item["path"] == "docs/Mission-brief.md"
        )
        entry["target_path"] = wrong_target
        entry["target_path_sha256"] = hashlib.sha256(
            (repository.ROOT / wrong_target).read_bytes()
        ).hexdigest()

        errors = repository.validate_foreground_preservation_manifest(manifest)

        self.assertIn(
            "docs/Mission-brief.md: declared moved target "
            "docs/archive/governance/pre-mission-message.txt disagrees with Git "
            "rename destination docs/missions/operations/flightline/setup/"
            "artifacts/approved-brief.md",
            errors,
        )

    def test_duplicate_ids_and_aliases_are_rejected(self):
        duplicate = self.missions[0]
        with patch.object(repository, "_commit_is_reachable", return_value=True):
            errors = repository.validate_metadata(
                [*self.missions, duplicate], self.decisions
            )
        self.assertTrue(
            any("duplicate mission ID" in error for error in errors), errors
        )
        self.assertTrue(
            any("colliding legacy mission alias" in error for error in errors),
            errors,
        )

    def test_completed_mission_requires_an_implementation_commit(self):
        metadata = copy.deepcopy(self.missions[0].metadata)
        metadata.update(
            {
                "id": "governance/no-implementation",
                "legacy_aliases": [],
                "lifecycle": "completed",
                "portfolio_primary": False,
                "implementation_commits": [],
            }
        )
        record = repository.Record(
            repository.MISSION_ROOT
            / "governance"
            / "no-implementation"
            / "mission.md",
            metadata,
        )
        with patch.object(repository, "_commit_is_reachable", return_value=True):
            errors = repository.validate_metadata(
                [*self.missions, record], self.decisions
            )
        self.assertIn(
            "governance/no-implementation: completed mission needs an "
            "implementation commit",
            errors,
        )

    def test_gov_003_does_not_claim_later_completed_missions(self):
        later = self._with_metadata(
            self._mission("governance/repository-architecture"),
            id="governance/later-completion",
        )

        errors = repository.validate_historical_ratification(
            [*self.missions, later], self.decisions
        )

        self.assertEqual(errors, [])

    def test_gov_003_ratified_mission_must_remain_completed(self):
        mission_id = "atlas/briefing"
        ratified = self._mission(mission_id)
        replacement = self._with_metadata(ratified, lifecycle="archived")
        missions = [
            replacement if item.metadata["id"] == mission_id else item
            for item in self.missions
        ]

        errors = repository.validate_historical_ratification(
            missions, self.decisions
        )

        self.assertIn(
            f"{mission_id}: GOV-003 ratified mission is not completed",
            errors,
        )

    def test_active_workstreams_may_not_overlap(self):
        primary = next(
            item for item in self.missions if item.metadata["portfolio_primary"]
        )
        metadata = copy.deepcopy(primary.metadata)
        metadata.update(
            {
                "id": "governance/concurrent-overlap",
                "legacy_aliases": [],
                "portfolio_primary": False,
            }
        )
        record = repository.Record(
            repository.MISSION_ROOT
            / "governance"
            / "concurrent-overlap"
            / "mission.md",
            metadata,
        )
        with patch.object(repository, "_commit_is_reachable", return_value=True):
            errors = repository.validate_metadata(
                [*self.missions, record], self.decisions
            )
        self.assertTrue(
            any("active writable scopes overlap" in error for error in errors),
            errors,
        )

    def test_canonical_documents_links_and_hygiene_are_valid(self):
        self.assertEqual(repository.validate_links_and_documents(), [])
        self.assertEqual(repository.validate_repository_hygiene(), [])

    def test_compatibility_and_first_read_rules_are_valid(self):
        self.assertEqual(repository.validate_compatibility_facades(), [])
        self.assertEqual(repository.validate_schemas_and_first_reads(), [])


if __name__ == "__main__":
    unittest.main()
