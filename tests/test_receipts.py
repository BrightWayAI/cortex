from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.lib import receipts as rc  # noqa: E402

IDENTITY = "# User Identity\n\n## Person\n- **Actor ID:** sample-user\n- **Name:** Sample User\n"
BASE = dict(schedule="nightly-listen", run_id="run-1", started_at="2026-01-06T03:00:00Z",
            ended_at="2026-01-06T03:05:00Z", outcome="succeeded", actor_id="sample-user", actor_source="identity")


def make_root(tmp: str, identity: str | None = IDENTITY) -> Path:
    root = Path(tmp) / "root"
    (root / "memory" / "me").mkdir(parents=True)
    if identity is not None:
        (root / "memory" / "me" / "identity.md").write_text(identity, encoding="utf-8")
    return root


class ActorTests(unittest.TestCase):
    def test_identity_file_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rc.resolve_actor(make_root(tmp), "someone-else"), ("sample-user", "identity"))

    def test_registration_actor_is_the_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rc.resolve_actor(make_root(tmp, None), "sample-user"), ("sample-user", "registration"))
            self.assertEqual(rc.resolve_actor(Path(tmp) / "missing", "sample-user"), ("sample-user", "registration"))

    def test_actor_is_never_invented(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rc.resolve_actor(make_root(tmp, None)), (rc.UNRESOLVED, "unresolved"))
            self.assertEqual(rc.resolve_actor(make_root(tmp + "/b", "## Person\n- **Name:** X\n")), (rc.UNRESOLVED, "unresolved"))

    def test_malformed_actor_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ("...", "Sample User", "a/b", "../x", ""):
                root = make_root(tmp + "/" + str(abs(hash(bad))), f"- **Actor ID:** {bad}\n")
                self.assertEqual(rc.resolve_actor(root, bad)[1], "unresolved", bad)


class BuildTests(unittest.TestCase):
    def test_receipt_has_actor_and_schema(self) -> None:
        r = rc.build(**BASE)
        self.assertEqual(r["schema_version"], "1.1.0")
        self.assertEqual((r["actor_id"], r["actor_source"], r["outcome"], r["error_codes"]),
                         ("sample-user", "identity", "succeeded", []))

    def test_old_outcome_spellings_are_normalized(self) -> None:
        self.assertEqual(rc.build(**{**BASE, "outcome": "success"})["outcome"], "succeeded")
        self.assertEqual(rc.build(**{**BASE, "outcome": "FAILED"})["outcome"], "failed")
        with self.assertRaises(ValueError):
            rc.build(**{**BASE, "outcome": "fine"})

    def test_unresolved_actor_is_flagged_not_hidden(self) -> None:
        r = rc.build(**{**BASE, "actor_id": rc.UNRESOLVED, "actor_source": "unresolved"})
        self.assertIn("actor_unresolved", r["error_codes"])

    def test_extra_fields_cannot_override_core_fields(self) -> None:
        self.assertEqual(rc.build(**BASE, extra={"counts": {"closed": 2}})["counts"], {"closed": 2})
        for key in ("actor_id", "outcome", "status", "schema_version"):
            with self.assertRaises(ValueError):
                rc.build(**BASE, extra={key: "x"})

    def test_names_cannot_carry_paths(self) -> None:
        for bad in ("../x", "a/b", "", "x y"):
            with self.assertRaises(ValueError):
                rc.build(**{**BASE, "run_id": bad})
            with self.assertRaises(ValueError):
                rc.build(**{**BASE, "schedule": bad})


class CliTests(unittest.TestCase):
    def cli(self, root: Path, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(REPO / "scripts" / "cortex_cli.py"), "write-receipt", "--config-root", str(root),
             "--schedule", "nightly-listen", "--run-id", "run-1", "--started-at", "2026-01-06T03:00:00Z",
             "--ended-at", "2026-01-06T03:05:00Z", *extra],
            capture_output=True, text=True,
        )

    def test_writes_receipt_with_actor_from_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            out = self.cli(root, "--outcome", "succeeded", "--extra", '{"counts": {"closed": 1}, "state_source": "none"}')
            self.assertEqual(out.returncode, 0, out.stderr)
            on_disk = json.loads(rc.receipt_path(root, "nightly-listen", "run-1").read_text(encoding="utf-8"))
            self.assertEqual(on_disk, json.loads(out.stdout))
            self.assertEqual((on_disk["actor_id"], on_disk["actor_source"]), ("sample-user", "identity"))
            self.assertEqual(on_disk["counts"], {"closed": 1})
            self.assertNotIn("Sample User", out.stdout)

    def test_unreachable_root_emits_to_stdout_with_registration_actor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self.cli(Path(tmp) / "nope", "--outcome", "failed", "--actor-id", "sample-user",
                           "--error-code", "config_root_unreachable")
            self.assertEqual(out.returncode, 2)
            r = json.loads(out.stdout)
            self.assertEqual((r["outcome"], r["actor_id"], r["actor_source"]), ("failed", "sample-user", "registration"))
            self.assertEqual(r["error_codes"], ["config_root_unreachable"])
            self.assertFalse((Path(tmp) / "nope").exists())

    def test_no_identity_and_no_fallback_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self.cli(make_root(tmp, None), "--outcome", "succeeded")
            r = json.loads(out.stdout)
            self.assertEqual(r["actor_id"], "unresolved")
            self.assertIn("actor_unresolved", r["error_codes"])

    def test_bad_outcome_or_extra_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            self.assertEqual(self.cli(root, "--outcome", "great").returncode, 1)
            self.assertEqual(self.cli(root, "--outcome", "succeeded", "--extra", "[1]").returncode, 1)
            self.assertEqual(self.cli(root, "--outcome", "succeeded", "--extra", '{"actor_id": "x"}').returncode, 1)
            self.assertFalse(rc.receipt_path(root, "nightly-listen", "run-1").exists())


if __name__ == "__main__":
    unittest.main()
