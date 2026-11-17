from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.lib import memory_diff as md  # noqa: E402

NOW = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.mem = Path(self._tmp.name) / "memory"
        self.mem.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str, when: str = "2026-11-16T22:00:00+00:00") -> None:
        env = {"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
               "HOME": self._tmp.name, "GIT_CONFIG_NOSYSTEM": "1"}
        subprocess.run(["git", "-C", str(self.mem), *args], check=True, capture_output=True, env=env)

    def write(self, rel: str, text: str) -> None:
        p = self.mem / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def commit(self, msg: str, when: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg, when=when)

    def two_commits(self) -> None:
        self.git("init", "-q")
        self.write("client/acme.md", "# Acme\n")
        self.commit("first", "2026-11-15T22:00:00+00:00")
        self.write("client/acme.md", "# Acme\nSECRET LINE\nmore\n")
        self.write("person/dana.md", "# Dana\n")
        self.write("hot.md", "hot\n")
        self.commit("second", "2026-11-16T23:00:00+00:00")


class Summaries(Base):
    def test_not_a_git_repo(self) -> None:
        self.assertEqual(md.summarize(self.mem, NOW), {"status": "not-git"})

    def test_single_commit_is_fresh(self) -> None:
        self.git("init", "-q")
        self.write("a.md", "x\n")
        self.commit("first", "2026-11-16T22:00:00+00:00")
        self.assertEqual(md.summarize(self.mem, NOW)["status"], "fresh")

    def test_changed_reports_counts_and_names_but_no_content(self) -> None:
        self.two_commits()
        r = md.summarize(self.mem, NOW)
        self.assertEqual((r["status"], r["previous_commit_date"], r["files"]), ("changed", "2026-11-15", 3))
        self.assertEqual(r["insertions"], 4)
        self.assertEqual(r["by_directory"], {"(root)": {"count": 1, "nodes": ["hot"]}, "client": {"count": 1, "nodes": ["acme"]},
                                             "person": {"count": 1, "nodes": ["dana"]}})
        self.assertNotIn("SECRET", str(r))

    def test_dirty_tree_is_reported_before_any_diff(self) -> None:
        self.two_commits()
        self.write("client/acme.md", "# Acme\nuncommitted\n")
        self.write("new.md", "x\n")
        r = md.summarize(self.mem, NOW)
        self.assertEqual((r["status"], r["dirty_count"]), ("dirty", 2))
        self.assertEqual(sorted(r["dirty_files"]), ["client/acme.md", "new.md"])
        self.assertNotIn("files", r)

    def test_no_overnight_commit_when_previous_commit_is_today(self) -> None:
        self.git("init", "-q")
        self.write("a.md", "1\n")
        self.commit("first", "2026-11-17T06:00:00+00:00")
        self.write("a.md", "2\n")
        self.commit("second", "2026-11-17T07:00:00+00:00")
        r = md.summarize(self.mem, NOW, today=date(2026, 11, 17))
        self.assertEqual(r["status"], "no-overnight-commit")

    def test_listen_still_running_blocks_the_diff(self) -> None:
        self.two_commits()
        started, expected = NOW - timedelta(minutes=7), NOW + timedelta(minutes=5)
        self.write("staged/queues/listen-in-progress", f"{started.isoformat()}|{expected.isoformat()}")
        self.assertEqual(md.summarize(self.mem, NOW), {"status": "listen-running", "started_minutes_ago": 7})

    def test_listen_marker_inside_grace_period_still_blocks(self) -> None:
        self.two_commits()
        self.write("staged/queues/listen-in-progress", f"{(NOW - timedelta(minutes=30)).isoformat()}|{(NOW - timedelta(minutes=1)).isoformat()}")
        self.assertEqual(md.summarize(self.mem, NOW)["status"], "listen-running")

    def test_stale_or_garbled_listen_marker_is_flagged_not_obeyed(self) -> None:
        self.two_commits()
        for content in (f"{(NOW - timedelta(hours=5)).isoformat()}|{(NOW - timedelta(hours=4)).isoformat()}", "garbage"):
            self.write("staged/queues/listen-in-progress", content)
            self.git("add", "-A"); self.git("commit", "-q", "-m", "marker", when="2026-11-16T23:30:00+00:00")
            r = md.summarize(self.mem, NOW)
            self.assertEqual(r["status"], "changed")
            self.assertTrue(r["stale_listen_marker"])

    def test_it_changes_nothing(self) -> None:
        self.two_commits()
        self.write("uncommitted.md", "x\n")
        before = subprocess.run(["git", "-C", str(self.mem), "status", "--porcelain"], capture_output=True, text=True).stdout
        head = subprocess.run(["git", "-C", str(self.mem), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
        md.summarize(self.mem, NOW)
        self.assertEqual(subprocess.run(["git", "-C", str(self.mem), "status", "--porcelain"], capture_output=True, text=True).stdout, before)
        self.assertEqual(subprocess.run(["git", "-C", str(self.mem), "rev-parse", "HEAD"], capture_output=True, text=True).stdout, head)

    def test_cli(self) -> None:
        self.two_commits()
        out = subprocess.run([sys.executable, str(REPO / "scripts" / "cortex_cli.py"), "memory-diff", "--config-root", self._tmp.name],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('"status"', out.stdout)


if __name__ == "__main__":
    unittest.main()
