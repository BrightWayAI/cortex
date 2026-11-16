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
from scripts.lib import draft_triage as dt  # noqa: E402
from scripts.lib import verification_record as vr  # noqa: E402
from tests.test_citation_check import SOURCE, draft, proposal  # noqa: E402

SRC = "archive/2026-01-05/kickoff.md"


def block(n: int, verification: str | None, conflicts: str | None = "none", frm: str = "note-taker (mode: transcript)") -> str:
    lines = [
        f"### Proposal {n} — client/acme: thing {n}",
        "- **Type:** INSIGHT",
        f"- **From:** {frm}",
        f"- **Source:** {SRC} (line 4)",
        "- **Proposed content:**",
        "  > Budget for phase one is approved",
        "- **Target placement:** `client/acme` · section `Knowledge`",
        "- **Confidence:** high",
    ]
    if conflicts is not None:
        lines.append(f"- **Conflicts:** {conflicts}")
    if verification is not None:
        lines.append(f"- **Verification:** {verification}")
    return "\n".join(lines) + "\n\n"


def one(text: str) -> dt.Triage:
    items = dt.triage_draft("## Proposals\n\n" + text)
    assert len(items) == 1
    return items[0]


class TriageTests(unittest.TestCase):
    def test_clean_pass_goes_to_batch(self) -> None:
        t = one(block(1, "pass"))
        self.assertEqual((t.group, t.why, t.node), (dt.GROUP_BATCH, [], "client/acme"))

    def test_anything_but_pass_goes_to_review(self) -> None:
        for verdict, why in (("fail", "verification-fail"), ("unverifiable", "verification-unverifiable"),
                             ("not-run", "verification-not-run"), ("PASSED!!", "verification-unrecognized")):
            t = one(block(1, verdict))
            self.assertEqual(t.group, dt.GROUP_REVIEW, verdict)
            self.assertEqual(t.why, [why])

    def test_unchecked_draft_goes_to_review(self) -> None:
        t = one(block(1, None))
        self.assertEqual((t.group, t.why), (dt.GROUP_REVIEW, ["not-checked"]))

    def test_pass_with_a_conflict_goes_to_review(self) -> None:
        t = one(block(1, "pass", conflicts="supersedes the 2025-12-01 budget entry"))
        self.assertEqual((t.group, t.why), (dt.GROUP_REVIEW, ["conflict-listed"]))

    def test_pass_with_no_conflicts_field_goes_to_review(self) -> None:
        t = one(block(1, "pass", conflicts=None))
        self.assertEqual(t.group, dt.GROUP_REVIEW)
        self.assertIn("conflicts-field-missing", t.why)

    def test_none_variants_count_as_no_conflict(self) -> None:
        for v in ("none", "None", "None.", "n/a", ""):
            self.assertEqual(one(block(1, "pass", conflicts=v)).group, dt.GROUP_BATCH, repr(v))

    def test_brief_items_are_set_aside_whatever_their_check_says(self) -> None:
        for verdict in ("pass", "not-run", None):
            t = one(block(1, verdict, frm="listen-step-1.5 (explicit mark: done)"))
            self.assertEqual(t.group, dt.GROUP_BRIEF)

    def test_several_reasons_are_all_reported(self) -> None:
        t = one(block(1, "fail", conflicts="contradicts existing entry"))
        self.assertEqual(t.why, ["verification-fail", "conflict-listed"])

    def test_summary_and_no_text_in_report(self) -> None:
        items = dt.triage_draft("## Proposals\n\n" + block(1, "pass") + block(2, "fail") + block(3, "pass", frm="from: listen-step-1.5"))
        self.assertEqual(dt.summarize(items), {"total": 3, "brief": 1, "batch": 1, "review": 1})
        self.assertNotIn("Budget", json.dumps([t.as_dict() for t in items]))

    def test_works_on_a_draft_written_by_record_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "archive" / "2026-01-05").mkdir(parents=True)
            (root / SRC).write_text(SOURCE, encoding="utf-8")
            text = draft(
                proposal(1, f"{SRC} (line 4)", "Budget for phase one is approved"),
                proposal(2, "archive/2026-01-05/nope.md", "x"),
                proposal(3, f"{SRC} (line 3)", "Due Wednesday"),
            )
            verifier = {"results": [
                {"id": "1", "verdict": "pass", "confidence": "high",
                 "evidence": [{"source": SRC, "locator": "line 4", "quote": "Budget for phase one is approved"}]},
                {"id": "3", "verdict": "fail", "confidence": "high", "evidence": [], "reasons": ["unsupported-part"]},
            ]}
            recs = vr.merge(cc.check_draft(text, root), verifier)
            out = vr.apply_to_draft(text, recs, "2026-01-06T03:00:00-05:00")
            self.assertEqual([t.group for t in dt.triage_draft(out)], [dt.GROUP_BATCH, dt.GROUP_REVIEW, dt.GROUP_REVIEW])


class CliTests(unittest.TestCase):
    def test_cli_reports_groups_and_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            drafts = root / "memory" / "staged" / "commit-drafts"
            drafts.mkdir(parents=True)
            f = drafts / "2026-01-05.md"
            f.write_text("## Proposals\n\n" + block(1, "pass") + block(2, "fail"), encoding="utf-8")
            before = f.read_text(encoding="utf-8")
            cli = [sys.executable, str(REPO / "scripts" / "cortex_cli.py"), "triage-draft", "--config-root", str(root)]
            out = subprocess.run([*cli, "--draft", "2026-01-05"], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            report = json.loads(out.stdout)
            self.assertEqual(report["summary"], {"total": 2, "brief": 0, "batch": 1, "review": 1})
            self.assertEqual(f.read_text(encoding="utf-8"), before)
            self.assertEqual(subprocess.run([*cli, "--draft", "../../x"], capture_output=True, text=True).returncode, 1)


if __name__ == "__main__":
    unittest.main()
