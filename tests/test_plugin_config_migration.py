from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.lib import plugin_config_migration as mig  # noqa: E402

TABLE = "# Schedules\n\n| Name | Cron / Schedule | Action |\n|---|---|---|\n| nightly-listen | daily 23:00 | `/listen` |\n"
TODAY = date(2026, 11, 16)


class PlanAndApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.plugins = self.root / "plugins"
        self.plugins.mkdir()
        (self.root / "memory").mkdir()
        self.template = self.root / "schedules.template.md"
        self.template.write_text("TEMPLATE\n" + TABLE, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _w(self, rel: str, text: str = "x\n") -> Path:
        p = self.plugins / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def _run(self):
        actions = mig.plan(self.plugins, TODAY, self.template)
        mig.apply(self.plugins, actions, self.template)
        return actions

    def test_plan_is_read_only(self) -> None:
        self._w("ops.schedules.md", TABLE)
        before = sorted(p.name for p in self.plugins.rglob("*"))
        mig.plan(self.plugins, TODAY, self.template)
        self.assertEqual(before, sorted(p.name for p in self.plugins.rglob("*")))

    def test_legacy_schedules_are_carried_then_archived(self) -> None:
        self._w("ops.schedules.md", "MINE\n" + TABLE)
        self._run()
        self.assertTrue((self.plugins / "ops/schedules.md").read_text().startswith("MINE"))
        self.assertFalse((self.plugins / "ops.schedules.md").exists())
        self.assertTrue((self.plugins / "archive/ops.schedules.2026-11-16.md").read_text().startswith("MINE"))

    def test_legacy_without_table_falls_back_to_template(self) -> None:
        self._w("ops.schedules.md", "just notes, no table\n")
        self._run()
        self.assertTrue((self.plugins / "ops/schedules.md").read_text().startswith("TEMPLATE"))
        self.assertTrue((self.plugins / "archive/ops.schedules.2026-11-16.md").exists())

    def test_template_used_when_nothing_exists(self) -> None:
        self._run()
        self.assertTrue((self.plugins / "ops/schedules.md").read_text().startswith("TEMPLATE"))

    def test_no_template_and_no_legacy_is_a_skip(self) -> None:
        actions = mig.plan(self.plugins, TODAY, None)
        self.assertEqual([a.kind for a in actions], ["skip"])
        mig.apply(self.plugins, actions, None)
        self.assertFalse((self.plugins / "ops/schedules.md").exists())

    def test_existing_definitions_are_never_overwritten(self) -> None:
        self._w("ops/schedules.md", "CURRENT\n")
        self._w("ops.schedules.md", "OLD\n" + TABLE)
        self._run()
        self.assertEqual((self.plugins / "ops/schedules.md").read_text(), "CURRENT\n")
        self.assertTrue((self.plugins / "archive/ops.schedules.2026-11-16.md").exists())

    def test_retired_file_archived_only_when_replacement_exists(self) -> None:
        self._w("client-status.user-context.md")
        actions = mig.plan(self.plugins, TODAY, self.template)
        self.assertIn(("skip", "client-status.user-context.md"), [(a.kind, a.source) for a in actions])
        self._w("clients-status.user-context.md")
        self._run()
        self.assertFalse((self.plugins / "client-status.user-context.md").exists())
        self.assertTrue((self.plugins / "archive/client-status.user-context.2026-11-16.md").exists())
        self.assertTrue((self.plugins / "clients-status.user-context.md").exists())

    def test_live_config_files_are_left_alone(self) -> None:
        keep = ["plan-tomorrow.user-context.md", "admin.user-context.md", "clients.sow-template.md",
                "cortex.note-sources.md", ".relationships-migrated-from-legacy"]
        for name in keep:
            self._w(name)
        self._w("cortex-patches/anything.py")
        self._run()
        for name in keep:
            self.assertTrue((self.plugins / name).exists(), name)
        self.assertTrue((self.plugins / "cortex-patches/anything.py").exists())

    def test_backups_follow_the_archive_naming_convention(self) -> None:
        self._w("admin.user-context.md.bak-2026-10-16")
        self._w("time.csv.bak-2026-11-02b")
        self._run()
        self.assertTrue((self.plugins / "archive/admin.user-context.2026-10-16.bak.md").exists())
        self.assertTrue((self.plugins / "archive/time.csv.2026-11-02b.bak.md").exists())

    def test_archive_name_collision_gets_a_suffix(self) -> None:
        self._w("archive/admin.user-context.2026-10-16.bak.md", "EARLIER\n")
        self._w("admin.user-context.md.bak-2026-10-16", "LATER\n")
        self._run()
        self.assertEqual((self.plugins / "archive/admin.user-context.2026-10-16.bak.md").read_text(), "EARLIER\n")
        self.assertEqual((self.plugins / "archive/admin.user-context.2026-10-16.bak-2.md").read_text(), "LATER\n")

    def test_second_run_plans_nothing_to_move(self) -> None:
        self._w("ops.schedules.md", TABLE)
        self._w("admin.user-context.md.bak-2026-10-16")
        self._run()
        again = mig.plan(self.plugins, TODAY, self.template)
        self.assertEqual([a for a in again if a.kind != "skip"], [])

    def test_apply_refuses_a_target_outside_plugins(self) -> None:
        bad = [mig.Action("move", "a.md", "../escaped.md", "test")]
        self._w("a.md")
        with self.assertRaises(ValueError):
            mig.apply(self.plugins, bad, None)
        self.assertTrue((self.plugins / "a.md").exists())


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "plugins").mkdir()
        (self.root / "memory").mkdir()
        (self.root / "plugins/ops.schedules.md").write_text("SECRET-CONTENT\n" + TABLE, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _cli(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(REPO / "scripts/cortex_cli.py"), "migrate-plugin-configs",
             "--config-root", str(self.root), *extra],
            capture_output=True, text=True,
        )

    def test_dry_run_changes_nothing_and_prints_no_contents(self) -> None:
        r = self._cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["status"], "dry-run")
        self.assertNotIn("SECRET-CONTENT", r.stdout)
        self.assertTrue((self.root / "plugins/ops.schedules.md").exists())
        self.assertFalse((self.root / "memory" / mig.MARKER_NAME).exists())

    def test_apply_writes_marker_and_second_run_is_a_noop(self) -> None:
        r = self._cli("--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.root / "plugins/ops/schedules.md").exists())
        self.assertTrue((self.root / "memory" / mig.MARKER_NAME).exists())
        again = json.loads(self._cli("--apply").stdout)
        self.assertEqual(again["status"], "already-done")

    def test_missing_plugins_dir_fails_cleanly(self) -> None:
        (self.root / "plugins/ops.schedules.md").unlink()
        (self.root / "plugins").rmdir()
        self.assertEqual(self._cli().returncode, 1)


if __name__ == "__main__":
    unittest.main()
