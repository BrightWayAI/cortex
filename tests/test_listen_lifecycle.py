from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.lib import listen_lifecycle as ll  # noqa: E402

NOW = datetime(2026, 11, 17, 3, 0, tzinfo=timezone.utc)
TEMPLATE = REPO / "references" / "gitignore-template.md"


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "home"
        self.root = self.home / "cortex-root"
        (self.root / "memory").mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def start(self, **kw) -> dict:
        kw.setdefault("sleep", lambda s: None)
        kw.setdefault("clock", lambda: NOW)
        return ll.start(self.root, NOW, self.home, template_path=TEMPLATE, **kw)


class Start(Base):
    def test_clean_start_writes_marker_lock_and_gitignore(self) -> None:
        r = self.start()
        self.assertEqual((r["status"], r["gitignore"], r["cloud_sync"]), ("ok", "created", None))
        marker = (self.root / ll.MARKER_REL).read_text(encoding="utf-8").strip().split("|")
        self.assertEqual(datetime.fromisoformat(marker[1]) - datetime.fromisoformat(marker[0]), timedelta(minutes=30))
        self.assertTrue((self.root / ll.LOCK_REL).read_text(encoding="utf-8").startswith("listen|2026-11-17T03:00:00"))
        ignore = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("archive/", ignore)
        self.assertIn("memory/staged/", ignore)
        self.assertFalse((self.root / ll.PROBE_REL).exists())

    def test_unreachable_root_stops_before_anything_is_written(self) -> None:
        missing = self.home / "nope"
        r = ll.start(missing, NOW, self.home)
        self.assertEqual(r["status"], "unreachable")
        self.assertFalse(missing.exists())

    def test_existing_gitignore_is_extended_not_rewritten(self) -> None:
        (self.root / ".gitignore").write_text("node_modules/\narchive/\n", encoding="utf-8")
        first = self.start()
        self.assertEqual(first["gitignore"], "updated")
        text = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("node_modules/\narchive/\n"))
        self.assertIn(ll.ADDED_HEADER, text)
        self.assertEqual(text.count("archive/\n"), 1)
        ll.finish(self.root, first["token"])
        self.assertEqual(self.start()["gitignore"], "ok")

    def test_legacy_commit_drafts_pattern_counts_as_protected(self) -> None:
        (self.root / ".gitignore").write_text("archive/\nmemory/staged/commit-drafts/\n", encoding="utf-8")
        self.assertEqual(self.start()["gitignore"], "ok")

    def test_cloud_synced_root_is_reported(self) -> None:
        for name, rel in (("iCloud", "Library/Mobile Documents/com~apple~CloudDocs/cortex"), ("Dropbox", "Dropbox/cortex"),
                          ("OneDrive", "OneDrive - Example/cortex"), ("Google Drive", "Google Drive/cortex")):
            root = self.home / rel
            (root / "memory").mkdir(parents=True)
            self.assertEqual(ll.cloud_sync_provider(root, self.home), name)
        self.assertIsNone(ll.cloud_sync_provider(self.root, self.home))

    def test_another_run_in_progress_is_not_overwritten(self) -> None:
        self.start()
        first_marker = (self.root / ll.MARKER_REL).read_text(encoding="utf-8")
        (self.root / ll.LOCK_REL).unlink()
        r = self.start()
        self.assertEqual((r["status"], r["started_minutes_ago"]), ("already-running", 0))
        self.assertEqual((self.root / ll.MARKER_REL).read_text(encoding="utf-8"), first_marker)
        self.assertEqual(self.start(force=True)["status"], "ok")

    def test_stale_marker_is_replaced(self) -> None:
        marker = self.root / ll.MARKER_REL
        marker.parent.mkdir(parents=True)
        marker.write_text(f"{(NOW - timedelta(hours=3)).isoformat()}|{(NOW - timedelta(hours=2)).isoformat()}", encoding="utf-8")
        r = self.start()
        self.assertEqual((r["status"], r["replaced_stale_marker"]), ("ok", True))

    def test_fresh_lock_means_busy_after_retries_and_nothing_is_taken(self) -> None:
        lock = self.root / ll.LOCK_REL
        lock.write_text(f"end-day|{(NOW - timedelta(seconds=30)).isoformat()}|99", encoding="utf-8")
        waits: list[float] = []
        r = self.start(sleep=waits.append)
        self.assertEqual(r["status"], "busy")
        self.assertEqual(waits, [60.0, 60.0])
        self.assertTrue(lock.read_text(encoding="utf-8").startswith("end-day|"))
        self.assertFalse((self.root / ll.MARKER_REL).exists())

    def test_lock_released_during_the_wait_lets_the_run_start(self) -> None:
        lock = self.root / ll.LOCK_REL
        lock.write_text(f"end-day|{(NOW - timedelta(seconds=30)).isoformat()}|99", encoding="utf-8")
        r = self.start(sleep=lambda s: lock.unlink())
        self.assertEqual(r["status"], "ok")

    def test_lock_older_than_ten_minutes_is_reclaimed(self) -> None:
        (self.root / ll.LOCK_REL).write_text(f"end-day|{(NOW - timedelta(seconds=601)).isoformat()}|99", encoding="utf-8")
        r = self.start()
        self.assertEqual((r["status"], r["reclaimed_stale_lock"]), ("ok", True))


class Finish(Base):
    def test_finish_removes_own_marker_and_lock_and_is_repeatable(self) -> None:
        token = self.start()["token"]
        self.assertEqual(ll.finish(self.root, token), {"marker": "removed", "lock": "removed"})
        self.assertEqual(ll.finish(self.root, token), {"marker": "absent", "lock": "absent"})

    def test_finish_never_removes_another_runs_marker_or_lock(self) -> None:
        self.start()
        before = ((self.root / ll.MARKER_REL).read_text(encoding="utf-8"), (self.root / ll.LOCK_REL).read_text(encoding="utf-8"))
        for wrong in ("deadbeefdeadbeef", "", "listen"):
            self.assertEqual(ll.finish(self.root, wrong), {"marker": "not-ours", "lock": "not-ours"})
        self.assertEqual(((self.root / ll.MARKER_REL).read_text(encoding="utf-8"), (self.root / ll.LOCK_REL).read_text(encoding="utf-8")), before)

    def test_finish_leaves_another_commands_lock_alone(self) -> None:
        (self.root / ll.LOCK_REL).write_text("end-day|2026-11-17T03:00:00+00:00|9", encoding="utf-8")
        self.assertEqual(ll.finish(self.root, "9x")["lock"], "not-ours")
        self.assertTrue((self.root / ll.LOCK_REL).exists())

    def test_marker_with_token_is_still_read_as_running_by_morning(self) -> None:
        from scripts.lib import memory_diff as md
        self.start()
        self.assertFalse(md._listen_running(self.root / "memory", NOW)["stale"])


class Cli(Base):
    def cli(self, cmd: str, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(REPO / "scripts" / "cortex_cli.py"), cmd, "--config-root", str(self.root), *extra],
                              capture_output=True, text=True)

    def test_exit_codes(self) -> None:
        ok = self.cli("listen-start", "--no-wait")
        self.assertEqual((ok.returncode, json.loads(ok.stdout)["status"]), (0, "ok"))
        token = json.loads(ok.stdout)["token"]
        self.assertEqual(self.cli("listen-start", "--no-wait").returncode, 4)
        self.assertEqual(json.loads(self.cli("listen-finish", "--token", "wrong").stdout)["marker"], "not-ours")
        self.assertEqual(json.loads(self.cli("listen-finish", "--token", token).stdout), {"marker": "removed", "lock": "removed"})
        (self.root / ll.LOCK_REL).write_text(f"end-day|{datetime.now().astimezone().isoformat()}|9", encoding="utf-8")
        self.assertEqual(self.cli("listen-start", "--no-wait").returncode, 5)
        gone = subprocess.run([sys.executable, str(REPO / "scripts" / "cortex_cli.py"), "listen-start", "--config-root",
                               str(self.home / "missing"), "--no-wait"], capture_output=True, text=True)
        self.assertEqual(gone.returncode, 3)


if __name__ == "__main__":
    unittest.main()
