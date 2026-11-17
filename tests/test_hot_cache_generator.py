from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.lib.hot_cache_generator import (  # noqa: E402
    generate_and_write_hot_cache,
    render_hot_cache,
)


def _write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


class RenderHotCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.memory_root = Path(self._tmpdir.name)
        self.today = date(2026, 6, 10)
        self.now = datetime(2026, 6, 10, 8, 0)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_includes_changelog_entries_within_window(self) -> None:
        _write(
            self.memory_root,
            "client/acme.md",
            "# client/acme\n\n## Changelog\n- 2026-06-09 — Kim confirmed the deadline\n"
            "- 2025-01-01 — ancient entry, out of window\n",
        )
        output = render_hot_cache(self.memory_root, self.today, self.now)
        self.assertIn("Kim confirmed the deadline", output)
        self.assertNotIn("ancient entry", output)

    def test_excludes_changelog_entries_outside_window(self) -> None:
        _write(
            self.memory_root,
            "client/acme.md",
            "# client/acme\n\n## Changelog\n- 2026-05-01 — too old\n",
        )
        output = render_hot_cache(self.memory_root, self.today, self.now)
        self.assertIn("nothing logged", output)

    def test_includes_recent_decisions(self) -> None:
        _write(
            self.memory_root,
            "workstream/q3-outbound.md",
            "# workstream/q3-outbound\n\n"
            "[workstream/q3-outbound] DECISION (2026-06-08): going with plan B "
            "[confirmed:2026-06-08]\n",
        )
        output = render_hot_cache(self.memory_root, self.today, self.now)
        self.assertIn("going with plan B", output)

    def test_excludes_old_decisions(self) -> None:
        _write(
            self.memory_root,
            "workstream/q3-outbound.md",
            "# workstream/q3-outbound\n\n"
            "[workstream/q3-outbound] DECISION (2020-01-01): ancient decision "
            "[confirmed:2020-01-01]\n",
        )
        output = render_hot_cache(self.memory_root, self.today, self.now)
        self.assertNotIn("ancient decision", output)

    def test_includes_open_threads(self) -> None:
        _write(
            self.memory_root,
            "client/acme.md",
            "# client/acme\n\n## Open threads\n- [P0] finalize contract\n"
            "- [WAITING:sarah] awaiting signature\n",
        )
        output = render_hot_cache(self.memory_root, self.today, self.now)
        self.assertIn("finalize contract", output)
        self.assertIn("awaiting signature", output)

    def test_excludes_private_proposals_staged_and_archive(self) -> None:
        _write(
            self.memory_root,
            "staged/commit-drafts/draft.md",
            "## Changelog\n- 2026-06-09 — should not appear\n",
        )
        _write(
            self.memory_root,
            "archive/old.md",
            "## Changelog\n- 2026-06-09 — should not appear either\n",
        )
        _write(
            self.memory_root,
            "proposals/alice/2026-06-09/p1.md",
            "## Changelog\n- 2026-06-09 — proposed only\n",
        )
        _write(
            self.memory_root,
            "me/user.md",
            "## Changelog\n- 2026-06-09 — private only\n",
        )
        output = render_hot_cache(self.memory_root, self.today, self.now)
        self.assertNotIn("should not appear", output)
        self.assertNotIn("proposed only", output)
        self.assertNotIn("private only", output)

    def test_trigger_is_recorded(self) -> None:
        output = render_hot_cache(self.memory_root, self.today, self.now, trigger="listen")
        self.assertIn("by listen", output)

    def test_empty_memory_root_does_not_crash(self) -> None:
        output = render_hot_cache(self.memory_root, self.today, self.now)
        self.assertIn("# Hot cache", output)
        self.assertIn("nothing logged", output)

    def test_output_stable_across_repeated_renders(self) -> None:
        _write(
            self.memory_root, "client/acme.md", "# client/acme\n\n## Changelog\n- 2026-06-09 — stable entry\n"
        )
        first = render_hot_cache(self.memory_root, self.today, self.now)
        second = render_hot_cache(self.memory_root, self.today, self.now)
        self.assertEqual(first, second)


class GenerateAndWriteHotCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.memory_root = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_writes_file_and_releases_lock(self) -> None:
        path = generate_and_write_hot_cache(
            self.memory_root, today=date(2026, 6, 10), now=datetime(2026, 6, 10, 8, 0)
        )
        self.assertTrue(path.exists())
        self.assertFalse((self.memory_root / ".lock").exists())


class CurrentNodeFormatTests(unittest.TestCase):
    """Formats written by /morning, /end-day and /remember since 4.28.

    The 4.28.1 regex fix shipped without tests. A generator that only reads the
    legacy formats renders an empty cache against a live root, so each format
    the fix added is pinned here.
    """

    def setUp(self) -> None:
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.memory_root = Path(self._tmpdir.name)
        self.today = date(2026, 11, 16)
        self.now = datetime(2026, 11, 16, 8, 0)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _render(self) -> str:
        return render_hot_cache(self.memory_root, self.today, self.now)

    def test_node_prefixed_log_lines_count_as_changelog(self) -> None:
        _write(
            self.memory_root,
            "client/acme.md",
            "# client/acme\n\n## Changelog\n"
            "[client/acme] LOG 2026-11-14 — kickoff call held\n"
            "[client/acme] LOG 2026-01-02 — stale log line\n",
        )
        output = self._render()
        self.assertIn("kickoff call held", output)
        self.assertNotIn("stale log line", output)
        self.assertNotIn("nothing logged", output)

    def test_decision_with_tags_before_the_colon(self) -> None:
        _write(
            self.memory_root,
            "workstream/pricing.md",
            "# workstream/pricing\n\n"
            "[workstream/pricing] DECISION (2026-11-12) [confirmed:2026-11-13] "
            "[by:zach-wagner]: hold the nonprofit rate\n",
        )
        output = self._render()
        self.assertIn("hold the nonprofit rate", output)
        self.assertIn("2026-11-13 — [[workstream/pricing]]", output)

    def test_decision_with_text_after_the_date(self) -> None:
        _write(
            self.memory_root,
            "workstream/pricing.md",
            "# workstream/pricing\n\n"
            "[workstream/pricing] DECISION (2026-11-12, call with Derek): ramp confirmed\n",
        )
        self.assertIn("ramp confirmed", self._render())

    def test_bold_and_dated_priority_tags_are_open_threads(self) -> None:
        _write(
            self.memory_root,
            "client/acme.md",
            "# client/acme\n\n## Open threads\n"
            "- **[P0]** send the recap\n"
            "- **[P0 2026-11-04]** post the user flow\n"
            "- **[WAITING:Dana]** project plan\n"
            "- [P1] plain tag still works\n"
            "- an untagged bullet is not a thread\n",
        )
        output = self._render()
        for expected in ("send the recap", "post the user flow", "project plan", "plain tag still works"):
            self.assertIn(expected, output)
        self.assertNotIn("untagged bullet", output)

    def test_alternate_open_section_headings(self) -> None:
        for i, heading in enumerate(
            ("## Open Threads", "## Open loops", "## Open Loops", "## Open Operational Threads")
        ):
            _write(
                self.memory_root,
                f"client/node{i}.md",
                f"# client/node{i}\n\n{heading}\n- [P1] thread under heading {i}\n",
            )
        output = self._render()
        for i in range(4):
            self.assertIn(f"thread under heading {i}", output)

    def test_threads_from_two_open_sections_in_one_node_are_merged(self) -> None:
        _write(
            self.memory_root,
            "company-ops.md",
            "# company-ops\n\n## Open threads\n- [P1] first section item\n\n"
            "## Open Operational Threads\n- [P2] second section item\n",
        )
        output = self._render()
        self.assertIn("first section item", output)
        self.assertIn("second section item", output)


if __name__ == "__main__":
    unittest.main()
