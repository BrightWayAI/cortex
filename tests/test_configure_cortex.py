from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.configure_cortex import ConfigureError, configure_cortex
from scripts.lib.config_root import resolve_config_root


ROOT = Path(__file__).resolve().parent.parent


class LocationDefaultsTests(unittest.TestCase):
    def test_default_root_is_cortex_root_without_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = configure_cortex(home=home, config_root="~/cortex-root", environ={}, repo_root=ROOT)
            self.assertEqual(home / "cortex-root", result.config_root)
            self.assertIsNone(result.location_warning)

    def test_documents_location_warns_but_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = configure_cortex(home=home, config_root="~/Documents/Cortex", environ={}, repo_root=ROOT)
            self.assertIn("~/Documents", result.location_warning or "")
            self.assertTrue((home / "Documents" / "Cortex" / "memory").is_dir())


class ConfigureCortexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.target = self.base / "cortex-data"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_configures_pointer_and_minimal_memory_using_fixture_only(self) -> None:
        result = configure_cortex(
            home=self.home,
            config_root=str(self.target),
            environ={},
            repo_root=ROOT,
        )

        pointer = self.home / ".cortex" / "config-root"
        self.assertEqual(f"{self.target}\n", pointer.read_text(encoding="utf-8"))
        self.assertEqual(self.target, resolve_config_root(home=self.home).path)
        for relative in ("DASHBOARD.md", "user.md", "log.md", "index.md", "hot.md"):
            self.assertTrue((self.target / "memory" / relative).is_file(), relative)
        self.assertTrue(result.pointer_changed)
        self.assertFalse((self.target / "memory" / ".lock").exists())

    def test_repeated_setup_is_idempotent_and_preserves_existing_content(self) -> None:
        configure_cortex(
            home=self.home,
            config_root=str(self.target),
            environ={},
            repo_root=ROOT,
        )
        user_path = self.target / "memory" / "user.md"
        user_path.write_text("# user\n\nprivate fixture preference\n", encoding="utf-8")

        result = configure_cortex(
            home=self.home,
            config_root=str(self.target),
            environ={},
            repo_root=ROOT,
        )

        self.assertFalse(result.pointer_changed)
        self.assertIn("private fixture preference", user_path.read_text(encoding="utf-8"))

    def test_legacy_claude_memory_instructions_get_a_codex_forwarding_shim(self) -> None:
        memory_root = self.target / "memory"
        memory_root.mkdir(parents=True)
        legacy = memory_root / "CLAUDE.md"
        legacy.write_text("# Private fixture instructions\n", encoding="utf-8")

        result = configure_cortex(
            home=self.home,
            config_root=str(self.target),
            environ={},
            repo_root=ROOT,
        )

        shim = memory_root / "AGENTS.md"
        self.assertTrue(shim.is_file())
        self.assertIn("Read `CLAUDE.md`", shim.read_text(encoding="utf-8"))
        self.assertEqual("# Private fixture instructions\n", legacy.read_text(encoding="utf-8"))
        self.assertIn("AGENTS.md", result.initialized_files)

    def test_existing_memory_agents_file_is_never_replaced(self) -> None:
        memory_root = self.target / "memory"
        memory_root.mkdir(parents=True)
        (memory_root / "CLAUDE.md").write_text("legacy\n", encoding="utf-8")
        agents = memory_root / "AGENTS.md"
        agents.write_text("user-owned Codex instructions\n", encoding="utf-8")

        configure_cortex(
            home=self.home,
            config_root=str(self.target),
            environ={},
            repo_root=ROOT,
        )

        self.assertEqual("user-owned Codex instructions\n", agents.read_text(encoding="utf-8"))

    def test_refuses_to_replace_a_different_pointer_without_force(self) -> None:
        other = self.base / "other"
        pointer = self.home / ".cortex" / "config-root"
        pointer.parent.mkdir(parents=True)
        pointer.write_text(f"{other}\n", encoding="utf-8")

        with self.assertRaisesRegex(ConfigureError, "--force-pointer"):
            configure_cortex(
                home=self.home,
                config_root=str(self.target),
                environ={},
                repo_root=ROOT,
            )

        self.assertEqual(f"{other}\n", pointer.read_text(encoding="utf-8"))
        self.assertFalse(self.target.exists())

    def test_force_replaces_pointer_but_does_not_delete_old_root(self) -> None:
        other = self.base / "other"
        old_file = other / "memory" / "keep.md"
        old_file.parent.mkdir(parents=True)
        old_file.write_text("fixture", encoding="utf-8")
        pointer = self.home / ".cortex" / "config-root"
        pointer.parent.mkdir(parents=True)
        pointer.write_text(f"{other}\n", encoding="utf-8")

        configure_cortex(
            home=self.home,
            config_root=str(self.target),
            environ={},
            force_pointer=True,
            repo_root=ROOT,
        )

        self.assertEqual(f"{self.target}\n", pointer.read_text(encoding="utf-8"))
        self.assertTrue(old_file.is_file())

    def test_reports_environment_override_that_would_hide_pointer(self) -> None:
        env_target = self.base / "env-target"
        result = configure_cortex(
            home=self.home,
            config_root=str(self.target),
            environ={"CORTEX_CONFIG_ROOT": str(env_target)},
            repo_root=ROOT,
        )
        self.assertIn("takes precedence", result.resolution_warning or "")

    def test_failed_initialization_does_not_publish_pointer(self) -> None:
        missing_repo = self.base / "missing-repo"
        with self.assertRaisesRegex(ConfigureError, "initialization"):
            configure_cortex(
                home=self.home,
                config_root=str(self.target),
                environ={},
                repo_root=missing_repo,
            )
        self.assertFalse((self.home / ".cortex" / "config-root").exists())

    def test_cli_supports_injected_home_for_distribution_smoke_test(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "configure_cortex.py"),
                "--home",
                str(self.home),
                "--config-root",
                str(self.target),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn(str(self.target), completed.stdout)
        self.assertTrue((self.target / "memory" / "DASHBOARD.md").is_file())


if __name__ == "__main__":
    unittest.main()
