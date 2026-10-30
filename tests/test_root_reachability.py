from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hooks import session_start
from scripts.lib.config_root import ConfigRootResult
from scripts.lib.root_reachability import (
    RootState,
    classify,
    is_remote_session,
    status_block,
    user_message,
)

ROOT = Path(__file__).resolve().parent.parent
REMOTE = {"CLAUDE_CODE_REMOTE": "true"}


class TempHome(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.root = self.home / "cortex-root"
        self.result = ConfigRootResult(path=self.root, source="test")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_memory(self) -> None:
        (self.root / "memory").mkdir(parents=True)
        (self.root / "memory" / "user.md").write_text("# user\n\nfixture profile\n", encoding="utf-8")


class RootClassificationTests(TempHome):
    def test_truthy_and_falsy_remote_values(self) -> None:
        for value in ("1", "true", "TRUE", "yes", "On", " 1 "):
            self.assertTrue(is_remote_session({"CLAUDE_CODE_REMOTE": value}), value)
        for value in ("", "0", "false", "no", "off", "maybe"):
            self.assertFalse(is_remote_session({"CLAUDE_CODE_REMOTE": value}), value)
        self.assertFalse(is_remote_session({}))

    def test_missing_root_is_remote_or_local_by_environment(self) -> None:
        self.assertIs(classify(self.result, REMOTE), RootState.REMOTE_NOT_ATTACHED)
        self.assertIs(classify(self.result, {}), RootState.LOCAL_MISSING)
        self.assertIs(classify(self.result, {"CLAUDE_CODE_REMOTE": "0"}), RootState.LOCAL_MISSING)

    def test_path_that_is_a_file_counts_as_missing(self) -> None:
        self.root.write_text("not a directory", encoding="utf-8")
        self.assertIs(classify(self.result, {}), RootState.LOCAL_MISSING)

    def test_existing_root_without_memory_is_empty_remote_or_local(self) -> None:
        self.root.mkdir()
        self.assertIs(classify(self.result, {}), RootState.EXISTS_BUT_EMPTY)
        self.assertIs(classify(self.result, REMOTE), RootState.EXISTS_BUT_EMPTY)
        (self.root / "memory").mkdir()
        self.assertIs(classify(self.result, {}), RootState.EXISTS_BUT_EMPTY)

    def test_root_with_memory_is_ok_remote_or_local(self) -> None:
        self.make_memory()
        self.assertIs(classify(self.result, {}), RootState.OK)
        self.assertIs(classify(self.result, REMOTE), RootState.OK)

    def test_classification_never_creates_anything(self) -> None:
        for env in ({}, REMOTE):
            classify(self.result, env)
            user_message(RootState.REMOTE_NOT_ATTACHED, self.result)
        self.assertFalse(self.root.exists())

    def test_messages(self) -> None:
        remote = user_message(RootState.REMOTE_NOT_ATTACHED, self.result)
        self.assertEqual(
            "Your Nucleus files are on your Mac and this chat can't see them yet. "
            "In the Claude desktop app, use + → Add folder and pick ~/cortex-root, "
            "then send any message.",
            remote,
        )
        self.assertNotIn("Add folder", user_message(RootState.LOCAL_MISSING, self.result))
        self.assertNotIn("Add folder", user_message(RootState.EXISTS_BUT_EMPTY, self.result))
        self.assertEqual("", user_message(RootState.OK, self.result))

    def test_status_block_leads_with_broken_and_blocks_filesystem_sections(self) -> None:
        block = status_block(RootState.REMOTE_NOT_ATTACHED, self.result)
        self.assertTrue(block.startswith("BROKEN"))
        self.assertIn(user_message(RootState.REMOTE_NOT_ATTACHED, self.result), block)
        self.assertIn("blocked: config root not attached", block)
        self.assertNotIn("unknown", block)
        self.assertEqual("", status_block(RootState.OK, self.result))


class SessionStartReachabilityTests(TempHome):
    def context(self, environ: dict[str, str]) -> str:
        return session_start.build_context(home=self.home, environ=environ, explicit=str(self.root))

    def test_remote_not_attached_tells_user_how_to_attach(self) -> None:
        context = self.context(REMOTE)
        self.assertIn("No recall files were readable.", context)
        self.assertIn("Add folder", context)
        self.assertIn("~/cortex-root", context)
        self.assertIn("first reply", context)
        self.assertIn("do not retry", context)
        self.assertFalse(self.root.exists())

    def test_local_missing_does_not_mention_add_folder(self) -> None:
        context = self.context({})
        self.assertIn("No recall files were readable.", context)
        self.assertNotIn("Add folder", context)
        self.assertFalse(self.root.exists())

    def test_loaded_recall_has_no_guidance(self) -> None:
        self.make_memory()
        context = self.context(REMOTE)
        self.assertIn("fixture profile", context)
        self.assertNotIn("No recall files", context)
        self.assertNotIn("Add folder", context)

    def test_unattended_remote_run_leaves_a_metadata_only_receipt(self) -> None:
        argv = [sys.executable, str(ROOT / "hooks" / "session_start.py"), "--home", str(self.home),
                "--config-root", str(self.root), "--unattended", "nightly-listen"]
        env = {**os.environ, "CLAUDE_CODE_REMOTE": "1"}
        subprocess.run(argv, env=env, capture_output=True, text=True, check=True)
        receipts = list((self.home / ".cortex" / "pending-receipts" / "nightly-listen").glob("*.json"))
        self.assertEqual(1, len(receipts))
        data = json.loads(receipts[0].read_text(encoding="utf-8"))
        self.assertEqual("config_root_unreachable", data["error_code"])
        self.assertEqual("failed", data["status"])
        self.assertFalse(self.root.exists())

    def test_unattended_local_missing_writes_no_receipt(self) -> None:
        argv = [sys.executable, str(ROOT / "hooks" / "session_start.py"), "--home", str(self.home),
                "--config-root", str(self.root), "--unattended", "nightly-listen"]
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_REMOTE"}
        subprocess.run(argv, env=env, capture_output=True, text=True, check=True)
        self.assertFalse((self.home / ".cortex").exists())

    def test_cli_root_status_exit_codes(self) -> None:
        argv = [sys.executable, str(ROOT / "scripts" / "cortex_cli.py"), "root-status", "--root", str(self.root)]
        env = {**os.environ, "HOME": str(self.home), "CLAUDE_CODE_REMOTE": "1"}
        bad = subprocess.run(argv, env=env, capture_output=True, text=True)
        self.assertEqual(1, bad.returncode)
        self.assertTrue(bad.stdout.startswith("BROKEN"))
        self.make_memory()
        good = subprocess.run(argv, env=env, capture_output=True, text=True)
        self.assertEqual(0, good.returncode)
        self.assertTrue(good.stdout.startswith("OK"))


if __name__ == "__main__":
    unittest.main()
