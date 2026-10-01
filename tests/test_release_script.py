"""Unit tests for the release helper script and changelog automation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

# Import release helper functions
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from release import (
    CHANGELOG_PREAMBLE,
    Commit,
    calculate_next_version,
    categorize_commits,
    generate_changelog_entry,
    get_current_version,
    get_last_tag,
    update_changelog_file,
)


class TestReleaseScript(unittest.TestCase):
    def test_calculate_next_version_patch(self) -> None:
        self.assertEqual(calculate_next_version("0.2.0", "patch"), "0.2.1")
        self.assertEqual(calculate_next_version("1.9.9", "patch"), "1.9.10")

    def test_calculate_next_version_minor(self) -> None:
        self.assertEqual(calculate_next_version("0.2.0", "minor"), "0.3.0")
        self.assertEqual(calculate_next_version("0.2.5", "minor"), "0.3.0")

    def test_calculate_next_version_major(self) -> None:
        self.assertEqual(calculate_next_version("0.2.0", "major"), "1.0.0")
        self.assertEqual(calculate_next_version("1.4.2", "major"), "2.0.0")

    def test_calculate_next_version_explicit(self) -> None:
        self.assertEqual(calculate_next_version("0.2.0", "0.5.0"), "0.5.0")
        self.assertEqual(calculate_next_version("0.2.0", "1.0.0-rc1"), "1.0.0-rc1")

    def test_get_current_version(self) -> None:
        ver = get_current_version()
        self.assertRegex(ver, r"^\d+\.\d+\.\d+")

    def test_categorize_commits(self) -> None:
        commits = [
            Commit("abc1", "feat", "beans", "add cool widget", False),
            Commit("abc2", "fix", "core", "fix event loop", False),
            Commit("abc3", "perf", "", "boost rendering", False),
            Commit("abc4", "docs", "readme", "clarify install", False),
            Commit("abc5", "refactor", "tea", "simplify commands", False),
            Commit("abc6", "test", "beans", "add button tests", False),
            Commit("abc7", "chore", "ci", "update actions", False),
            Commit("abc8", "feat", "api", "redesign model signature", True),
        ]
        cats = categorize_commits(commits)
        self.assertEqual(len(cats["feat"]), 2)
        self.assertEqual(len(cats["breaking"]), 1)
        self.assertEqual(cats["breaking"][0].hash, "abc8")
        self.assertEqual(len(cats["fix"]), 1)
        self.assertEqual(len(cats["perf"]), 1)
        self.assertEqual(len(cats["docs"]), 1)
        self.assertEqual(len(cats["refactor"]), 1)
        self.assertEqual(len(cats["test"]), 1)
        self.assertEqual(len(cats["maintenance"]), 1)

    def test_generate_changelog_entry(self) -> None:
        commits = [
            Commit("1234567", "feat", "beans", "add marquee bean", False),
            Commit("2345678", "fix", "crema", "fix ansi wrap bounds", False),
        ]
        entry = generate_changelog_entry(
            new_version="0.3.0",
            last_tag="v0.2.0",
            repo_url="https://github.com/kimusan/espresso",
            commits=commits,
        )
        self.assertIn("## [0.3.0](https://github.com/kimusan/espresso/compare/v0.2.0...v0.3.0)", entry)
        self.assertIn("### 🚀 Features", entry)
        self.assertIn("- **beans**: Add marquee bean ([1234567](https://github.com/kimusan/espresso/commit/1234567))", entry)
        self.assertIn("### 🐛 Bug Fixes", entry)
        self.assertIn("- **crema**: Fix ansi wrap bounds ([2345678](https://github.com/kimusan/espresso/commit/2345678))", entry)

    def test_generate_changelog_entry_initial_tag(self) -> None:
        commits = [Commit("1111111", "feat", "", "initial framework commit", False)]
        entry = generate_changelog_entry(
            new_version="0.2.0",
            last_tag=None,
            repo_url="https://github.com/kimusan/espresso",
            commits=commits,
        )
        self.assertIn("## [0.2.0](https://github.com/kimusan/espresso/releases/tag/v0.2.0)", entry)
        self.assertIn("- Initial framework commit ([1111111](https://github.com/kimusan/espresso/commit/1111111))", entry)

    def test_update_changelog_file_new_and_prepend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            changelog_path = Path(tmp_dir) / "CHANGELOG.md"

            # 1. Create initial file
            entry_v1 = "## [0.2.0](url/0.2.0) - 2026-10-01\n\n### 🚀 Features\n- Base feature"
            update_changelog_file(changelog_path, entry_v1, "0.2.0")
            content = changelog_path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith(CHANGELOG_PREAMBLE))
            self.assertIn("## [0.2.0]", content)

            # 2. Prepend second version
            entry_v2 = "## [0.2.1](url/0.2.1) - 2026-10-02\n\n### 🐛 Bug Fixes\n- Quick fix"
            update_changelog_file(changelog_path, entry_v2, "0.2.1")
            content_v2 = changelog_path.read_text(encoding="utf-8")
            idx_v2 = content_v2.index("## [0.2.1]")
            idx_v1 = content_v2.index("## [0.2.0]")
            self.assertLess(idx_v2, idx_v1)

            # 3. Idempotent replacement for existing version
            entry_v2_updated = "## [0.2.1](url/0.2.1) - 2026-10-02\n\n### 🐛 Bug Fixes\n- Updated quick fix description"
            update_changelog_file(changelog_path, entry_v2_updated, "0.2.1")
            content_v3 = changelog_path.read_text(encoding="utf-8")
            self.assertEqual(content_v3.count("## [0.2.1]"), 1)
            self.assertIn("Updated quick fix description", content_v3)

    def test_release_tui_model_stages(self) -> None:
        from espresso.crema import strip_ansi
        from release import ReleaseTUI

        # With changelog (default)
        app = ReleaseTUI(curr_ver="0.2.0", next_ver="0.2.1", dry_run=True, skip_tests=True)
        stage_titles = [s.title for s in app.pipeline.stages]
        self.assertIn("Generate CHANGELOG.md", stage_titles)

        cmd = app.init()
        self.assertIsNotNone(cmd)
        view = app.view()
        clean = strip_ansi(view)
        self.assertIn("ESPRESSO RELEASE MANAGER", clean)
        self.assertIn("0.2.0", clean)
        self.assertIn("0.2.1", clean)

        # Without changelog
        app_no_cl = ReleaseTUI(curr_ver="0.2.0", next_ver="0.2.1", dry_run=True, skip_tests=True, no_changelog=True)
        stage_titles_no_cl = [s.title for s in app_no_cl.pipeline.stages]
        self.assertNotIn("Generate CHANGELOG.md", stage_titles_no_cl)


if __name__ == "__main__":
    unittest.main()
