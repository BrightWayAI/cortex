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

SOURCE = (
    "# Kickoff\n"
    "Dana: We can share sample files next week.\n"
    "Sam: I will send the pilot scope summary by Friday.\n"
    "Dana: Budget for phase one is approved; phase two depends on results.\n"
)


def proposal(n: int, source: str, content: str, node: str = "client/northwind") -> str:
    return (
        f"### Proposal {n} — {node}: something\n"
        "- **Type:** INSIGHT\n"
        "- **From:** note-taker (mode: transcript)\n"
        f"- **Source:** {source}\n"
        "- **Proposed content:**\n"
        f"  > {content}\n"
        f"- **Target placement:** `{node}` · section `Knowledge`\n"
        "- **Confidence:** high\n"
        "- **Conflicts:** none\n\n"
    )


def draft(*proposals: str) -> str:
    return "# Commit draft — 2026-01-05\n\n## Summary\n- x\n\n## Proposals\n\n" + "".join(proposals)


class CitationCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "root"
        (self.root / "archive" / "2026-01-05").mkdir(parents=True)
        (self.root / "memory" / "staged" / "commit-drafts").mkdir(parents=True)
        (self.root / "archive" / "2026-01-05" / "kickoff.md").write_text(SOURCE, encoding="utf-8")
        (Path(self._tmp.name) / "outside.md").write_text(SOURCE, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def one(self, source: str, content: str) -> cc.Result:
        results = cc.check_draft(draft(proposal(1, source, content)), self.root)
        self.assertEqual(len(results), 1)
        return results[0]

    def test_verbatim_text_passes(self) -> None:
        r = self.one("archive/2026-01-05/kickoff.md (line 4)", "Budget for phase one is approved; phase two depends on results.")
        self.assertEqual(r.status, cc.STATUS_PASS)
        self.assertEqual(r.node, "client/northwind")
        self.assertEqual(r.sources, ["archive/2026-01-05/kickoff.md"])

    def test_verbatim_match_ignores_case_punctuation_and_markdown(self) -> None:
        r = self.one("archive/2026-01-05/kickoff.md", "**budget** for phase one is approved, phase two depends on results")
        self.assertEqual(r.status, cc.STATUS_PASS)

    def test_paraphrase_needs_the_verifier(self) -> None:
        r = self.one("archive/2026-01-05/kickoff.md (line 4)", "Phase-one funding has been signed off.")
        self.assertEqual(r.status, cc.STATUS_NEEDS)
        self.assertEqual(r.reasons, [])

    def test_missing_source_file_fails(self) -> None:
        r = self.one("archive/2026-01-05/nope.md (line 2)", "anything")
        self.assertEqual(r.status, cc.STATUS_FAIL)
        self.assertEqual(r.reasons, [cc.REASON_MISSING])

    def test_line_out_of_range_fails(self) -> None:
        r = self.one("archive/2026-01-05/kickoff.md (line 40)", "Budget for phase one is approved")
        self.assertEqual(r.status, cc.STATUS_FAIL)
        self.assertEqual(r.reasons, [cc.REASON_BAD_LINE])

    def test_line_range_is_checked_against_its_end(self) -> None:
        ok = self.one("archive/2026-01-05/kickoff.md (lines 2-4)", "Budget for phase one is approved")
        bad = self.one("archive/2026-01-05/kickoff.md (lines 2-9)", "Budget for phase one is approved")
        self.assertEqual(ok.status, cc.STATUS_PASS)
        self.assertEqual(bad.reasons, [cc.REASON_BAD_LINE])

    def test_path_escaping_the_root_fails(self) -> None:
        r = self.one("archive/../../outside.md", "Budget for phase one is approved")
        self.assertEqual(r.status, cc.STATUS_FAIL)
        self.assertEqual(r.reasons, [cc.REASON_ESCAPES])

    def test_no_source_fails(self) -> None:
        r = self.one("none", "anything")
        self.assertEqual(r.status, cc.STATUS_FAIL)
        self.assertEqual(r.reasons, [cc.REASON_NO_SOURCE])

    def test_non_file_source_needs_the_verifier(self) -> None:
        r = self.one("Gmail thread 18c2f9a", "anything")
        self.assertEqual(r.status, cc.STATUS_NEEDS)
        self.assertEqual(r.reasons, [cc.REASON_NOT_A_FILE])
        self.assertEqual(r.citation_count, 1)

    def test_two_citations_are_counted_and_one_bad_one_fails(self) -> None:
        good = self.one(
            "archive/2026-01-05/kickoff.md (line 4); Gmail thread 18c2f9a",
            "Budget for phase one is approved",
        )
        self.assertEqual(good.status, cc.STATUS_PASS)
        self.assertEqual(good.citation_count, 2)
        bad = self.one(
            "archive/2026-01-05/kickoff.md (line 4); archive/2026-01-05/nope.md",
            "Budget for phase one is approved",
        )
        self.assertEqual(bad.status, cc.STATUS_FAIL)

    def test_several_proposals_are_parsed_in_order(self) -> None:
        text = draft(
            proposal(1, "archive/2026-01-05/kickoff.md", "Budget for phase one is approved"),
            proposal(2, "archive/2026-01-05/nope.md", "x", node="ops/hiring"),
            proposal(3, "archive/2026-01-05/kickoff.md", "Something else entirely"),
        )
        results = cc.check_draft(text, self.root)
        self.assertEqual([r.number for r in results], [1, 2, 3])
        self.assertEqual([r.status for r in results], [cc.STATUS_PASS, cc.STATUS_FAIL, cc.STATUS_NEEDS])
        self.assertEqual(results[1].node, "ops/hiring")
        self.assertEqual(cc.summarize(results), {"total": 3, cc.STATUS_PASS: 1, cc.STATUS_NEEDS: 1, cc.STATUS_FAIL: 1})

    def test_report_never_contains_proposal_or_source_text(self) -> None:
        secret = "Budget for phase one is approved"
        results = cc.check_draft(draft(proposal(1, "archive/2026-01-05/kickoff.md", secret)), self.root)
        blob = json.dumps([r.as_dict() for r in results])
        self.assertNotIn("Budget", blob)
        self.assertNotIn("Dana", blob)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "archive" / "2026-01-05").mkdir(parents=True)
        drafts = self.root / "memory" / "staged" / "commit-drafts"
        drafts.mkdir(parents=True)
        (self.root / "archive" / "2026-01-05" / "kickoff.md").write_text(SOURCE, encoding="utf-8")
        self.draft = drafts / "2026-01-05.md"
        self.draft.write_text(
            draft(proposal(1, "archive/2026-01-05/kickoff.md (line 4)", "Budget for phase one is approved")),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(REPO / "scripts" / "cortex_cli.py"), "check-citations", *args],
            capture_output=True, text=True,
        )

    def test_by_date_reports_json_and_changes_nothing(self) -> None:
        before = self.draft.read_text(encoding="utf-8")
        out = self.run_cli("--config-root", str(self.root), "--draft", "2026-01-05")
        self.assertEqual(out.returncode, 0, out.stderr)
        report = json.loads(out.stdout)
        self.assertEqual(report["draft"], "2026-01-05.md")
        self.assertEqual(report["summary"]["total"], 1)
        self.assertEqual(report["proposals"][0]["status"], cc.STATUS_PASS)
        self.assertEqual(self.draft.read_text(encoding="utf-8"), before)

    def test_missing_draft_exits_nonzero(self) -> None:
        out = self.run_cli("--config-root", str(self.root), "--draft", "2026-02-02")
        self.assertEqual(out.returncode, 1)
        self.assertIn("no commit draft", out.stderr)


if __name__ == "__main__":
    unittest.main()
