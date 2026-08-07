"""Executable checks for canonical repository-governance records."""

import copy
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
