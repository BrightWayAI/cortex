from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.lib import citation_check as cc  # noqa: E402
from scripts.lib import verification_record as vr  # noqa: E402
from tests.test_citation_check import SOURCE, draft, proposal  # noqa: E402

STAMP = "2026-01-06T03:00:00-05:00"
SRC = "archive/2026-01-05/kickoff.md"


def vres(*items: dict) -> dict:
    return {"schema_version": "1.0.0", "results": list(items)}


def item(i: int, verdict: str, confidence: str = "high", quote: str = "Budget for phase one is approved", reasons=None) -> dict:
    ev = [{"source": SRC, "locator": "line 4", "quote": quote}] if quote else []
    return {"id": str(i), "verdict": verdict, "confidence": confidence, "evidence": ev, "reasons": reasons or []}


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "archive" / "2026-01-05").mkdir(parents=True)
        self.drafts = self.root / "memory" / "staged" / "commit-drafts"
        self.drafts.mkdir(parents=True)
        (self.root / SRC).write_text(SOURCE, encoding="utf-8")
        self.text = draft(
            proposal(1, f"{SRC} (line 4)", "Budget for phase one is approved"),
            proposal(2, "archive/2026-01-05/nope.md", "Something"),
            proposal(3, f"{SRC} (line 3)", "Summary is due Wednesday"),
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def det(self) -> list[cc.Result]:
        return cc.check_draft(self.text, self.root)


class MergeTests(Base):
    def test_verifier_verdicts_are_recorded(self) -> None:
        recs = vr.merge(self.det(), vres(item(1, "pass"), item(3, "fail", reasons=["unsupported-part"])))
        self.assertEqual([r.verdict for r in recs], ["pass", "fail", "fail"])
        self.assertEqual(recs[2].reasons, ["unsupported-part"])
        self.assertIn(SRC, recs[0].evidence[0])

    def test_deterministic_fail_is_final_even_if_verifier_passes_it(self) -> None:
        recs = vr.merge(self.det(), vres(item(1, "pass"), item(2, "pass"), item(3, "pass")))
        self.assertEqual(recs[1].verdict, "fail")
        self.assertEqual(recs[1].reasons, [cc.REASON_MISSING])

    def test_no_verifier_output_means_not_run_never_pass(self) -> None:
        recs = vr.merge(self.det(), None)
        self.assertEqual([r.verdict for r in recs], ["not-run", "fail", "not-run"])
        self.assertEqual(recs[0].citation_check, cc.STATUS_PASS)
        self.assertEqual(recs[0].reasons, ["verifier-not-run"])

    def test_missing_id_is_not_run(self) -> None:
        recs = vr.merge(self.det(), vres(item(1, "pass")))
        self.assertEqual(recs[2].verdict, "not-run")

    def test_pass_at_low_confidence_becomes_unverifiable(self) -> None:
        recs = vr.merge(self.det(), vres(item(1, "pass", "low")))
        self.assertEqual(recs[0].verdict, "unverifiable")
        self.assertIn("pass-at-low-confidence", recs[0].reasons)

    def test_pass_without_evidence_becomes_unverifiable(self) -> None:
        recs = vr.merge(self.det(), vres(item(1, "pass", quote="")))
        self.assertEqual(recs[0].verdict, "unverifiable")
        self.assertIn("pass-without-evidence", recs[0].reasons)

    def test_garbage_verdict_is_not_run(self) -> None:
        recs = vr.merge(self.det(), vres({"id": "1", "verdict": "approved", "confidence": "high"}))
        self.assertEqual(recs[0].verdict, "not-run")
        self.assertEqual(recs[0].reasons, ["invalid-verifier-result"])

    def test_malformed_verifier_payloads_do_not_crash(self) -> None:
        for bad in ({}, {"results": "x"}, {"results": [1, "a", None]}, [], "text"):
            recs = vr.merge(self.det(), bad)  # type: ignore[arg-type]
            self.assertEqual(recs[0].verdict, "not-run")

    def test_long_quote_is_truncated_to_25_words(self) -> None:
        recs = vr.merge(self.det(), vres(item(1, "pass", quote=" ".join(f"w{i}" for i in range(60)))))
        quoted = recs[0].evidence[0].split("— ", 1)[1]
        self.assertEqual(len(quoted.replace("…", "").replace('"', "").split()), 25)
        self.assertIn("…", quoted)


class ApplyTests(Base):
    def apply(self, text: str | None = None) -> str:
        recs = vr.merge(self.det(), vres(item(1, "pass"), item(3, "fail", reasons=["unsupported-part"])))
        return vr.apply_to_draft(text if text is not None else self.text, recs, STAMP)

    def test_fields_are_written_under_each_proposal(self) -> None:
        out = self.apply()
        self.assertEqual(out.count("- **Verification:**"), 3)
        blocks = out.split("### Proposal ")[1:]
        self.assertIn("- **Verification:** pass", blocks[0])
        self.assertIn("- **Verification:** fail", blocks[1])
        self.assertIn("source-file-missing", blocks[1])
        self.assertIn("unsupported-part", blocks[2])
        for b in blocks:
            self.assertLess(b.index("- **Conflicts:**"), b.index("- **Citation check:**"))

    def test_summary_section_precedes_proposals(self) -> None:
        out = self.apply()
        self.assertEqual(out.count(vr.SUMMARY_HEADING + "\n"), 1)
        self.assertLess(out.index(vr.SUMMARY_HEADING), out.index("## Proposals"))
        self.assertIn("- 1 pass", out)
        self.assertIn("- 2 fail", out)

    def test_original_content_is_preserved(self) -> None:
        out = self.apply()
        for line in self.text.splitlines():
            self.assertIn(line, out)

    def test_rerun_replaces_rather_than_stacks(self) -> None:
        once = self.apply()
        twice = self.apply(once)
        self.assertEqual(once, twice)

    def test_still_parses_after_writing(self) -> None:
        results = cc.check_draft(self.apply(), self.root)
        self.assertEqual([r.status for r in results], [cc.STATUS_PASS, cc.STATUS_FAIL, cc.STATUS_NEEDS])


class CliTests(Base):
    def setUp(self) -> None:
        super().setUp()
        self.draft = self.drafts / "2026-01-05.md"
        self.draft.write_text(self.text, encoding="utf-8")

    def run_cli(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(REPO / "scripts" / "cortex_cli.py"), "record-verification",
             "--config-root", str(self.root), *args],
            capture_output=True, text=True, input=stdin,
        )

    def test_writes_results_from_stdin(self) -> None:
        out = self.run_cli("--draft", "2026-01-05", "--verifier-results", "-", stdin=json.dumps(vres(item(1, "pass"))))
        self.assertEqual(out.returncode, 0, out.stderr)
        report = json.loads(out.stdout)
        self.assertEqual(report["verifier_results"], "read")
        self.assertEqual(report["summary"], {"total": 3, "pass": 1, "fail": 1, "unverifiable": 0, "not-run": 1})
        self.assertIn("- **Verification:** pass", self.draft.read_text(encoding="utf-8"))
        self.assertNotIn("Budget", out.stdout)

    def test_without_verifier_results_everything_checkable_is_not_run(self) -> None:
        out = self.run_cli("--draft", "2026-01-05")
        report = json.loads(out.stdout)
        self.assertEqual(report["verifier_results"], "not-provided")
        self.assertEqual(report["summary"]["pass"], 0)
        self.assertEqual(report["summary"]["not-run"], 2)

    def test_unparseable_verifier_output_is_reported_and_nothing_passes(self) -> None:
        out = self.run_cli("--draft", "2026-01-05", "--verifier-results", "-", stdin="not json at all")
        self.assertEqual(out.returncode, 0)
        report = json.loads(out.stdout)
        self.assertEqual(report["verifier_results"], "unusable")
        self.assertEqual(report["summary"]["pass"], 0)

    def test_draft_name_cannot_escape_the_drafts_folder(self) -> None:
        (self.root / "memory" / "evil.md").write_text(self.text, encoding="utf-8")
        out = self.run_cli("--draft", "../../evil")
        self.assertEqual(out.returncode, 1)
        self.assertEqual((self.root / "memory" / "evil.md").read_text(encoding="utf-8"), self.text)

    def test_missing_draft_exits_nonzero(self) -> None:
        self.assertEqual(self.run_cli("--draft", "2026-03-03").returncode, 1)


if __name__ == "__main__":
    unittest.main()
