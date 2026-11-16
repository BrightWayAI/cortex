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

from scripts.lib import decision_records as dr  # noqa: E402
from scripts.lib.index_generator import collect_entries  # noqa: E402

DAY = date(2026, 11, 16)


def make(**kw) -> dr.Decision:
    base = dict(title="Use Pipedrive as the CRM", what="We will run the pipeline in Pipedrive.",
                why="Pricing scales better at our size.", decided=DAY, decided_by="sample-user",
                inputs=["Vendor quote, archive/2026-11-15/quote.md"], affects=["client/acme"])
    base.update(kw)
    return dr.Decision(**base)


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "memory"
        (self.root / "client").mkdir(parents=True)
        (self.root / "client" / "acme.md").write_text("# Acme\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, d: dr.Decision) -> dict:
        p = dr.plan(self.root, d)
        target = self.root / p["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(p["content"], encoding="utf-8")
        if p["superseded_id"]:
            (self.root / "decision" / f"{p['superseded_id']}.md").write_text(p["superseded_content"], encoding="utf-8")
        return p


class Create(Base):
    def test_record_has_every_required_part(self) -> None:
        p = self.write(make())
        self.assertEqual(p["id"], "2026-11-16-use-pipedrive-as-the-crm")
        text = (self.root / p["path"]).read_text(encoding="utf-8")
        front = dr.read_front(text)
        self.assertEqual((front["type"], front["decided"], front["decided_by"], front["status"]),
                         ("decision", "2026-11-16", "sample-user", "active"))
        for heading in ("## Decision", "## Inputs", "## Why", "## Affects", "## Revisit when"):
            self.assertIn(heading, text)
        self.assertIn("- [[client/acme]]", text)
        self.assertIn("Vendor quote", text)
        self.assertNotIn("supersedes:", text)

    def test_pointer_line_matches_the_inline_decision_format(self) -> None:
        p = self.write(make())
        self.assertEqual(p["pointer_line"],
                         "DECISION [confirmed:2026-11-16] Use Pipedrive as the CRM → [[decision/2026-11-16-use-pipedrive-as-the-crm]] [by:sample-user]")

    def test_same_title_same_day_gets_a_new_id_not_an_overwrite(self) -> None:
        first = self.write(make())
        second = self.write(make(what="A different decision with the same title."))
        self.assertNotEqual(first["id"], second["id"])
        self.assertIn("We will run the pipeline", (self.root / first["path"]).read_text(encoding="utf-8"))

    def test_missing_affected_node_is_reported_not_fatal(self) -> None:
        p = dr.plan(self.root, make(affects=["client/acme", "client/ghost"]))
        self.assertEqual(p["missing_affects"], ["client/ghost"])

    def test_who_decided_is_mandatory(self) -> None:
        for bad in ("", "unresolved", "Sample User", "../x"):
            with self.assertRaises(dr.DecisionError):
                dr.plan(self.root, make(decided_by=bad))

    def test_what_why_and_title_are_mandatory(self) -> None:
        for field_name in ("title", "what", "why"):
            with self.assertRaises(dr.DecisionError):
                dr.plan(self.root, make(**{field_name: "   "}))

    def test_affected_node_cannot_be_a_path_escape(self) -> None:
        for bad in ("../outside", "/etc/passwd", "client/../../x", "has space"):
            with self.assertRaises(dr.DecisionError):
                dr.plan(self.root, make(affects=[bad]))


class Supersede(Base):
    def test_new_decision_marks_the_old_one_and_points_both_ways(self) -> None:
        old = self.write(make())
        new = self.write(make(title="Move the pipeline to HubSpot", what="HubSpot from January.",
                              decided=date(2027, 1, 5), supersedes=f"[[decision/{old['id']}]]"))
        old_text = (self.root / old["path"]).read_text(encoding="utf-8")
        new_text = (self.root / new["path"]).read_text(encoding="utf-8")
        self.assertEqual(dr.read_front(old_text)["status"], "superseded")
        self.assertEqual(dr.read_front(old_text)["superseded_by"], f"decision/{new['id']}")
        self.assertEqual(dr.read_front(new_text)["supersedes"], f"decision/{old['id']}")
        self.assertIn("We will run the pipeline in Pipedrive.", old_text)  # the old decision is kept, not rewritten
        self.assertEqual(new["superseded_id"], old["id"])

    def test_cannot_supersede_twice_or_supersede_a_non_decision(self) -> None:
        old = self.write(make())
        self.write(make(title="Second", supersedes=old["id"]))
        with self.assertRaises(dr.DecisionError) as ctx:
            dr.plan(self.root, make(title="Third", supersedes=old["id"]))
        self.assertIn("already superseded", str(ctx.exception))
        with self.assertRaises(dr.DecisionError):
            dr.plan(self.root, make(title="Fourth", supersedes="2020-01-01-nothing-here"))
        with self.assertRaises(dr.DecisionError):
            dr.plan(self.root, make(title="Fifth", supersedes="client/acme"))

    def test_plan_writes_nothing(self) -> None:
        dr.plan(self.root, make())
        self.assertFalse((self.root / "decision").exists())


class IndexAndCli(Base):
    def test_decisions_get_their_own_index_section(self) -> None:
        self.write(make())
        sections = collect_entries(self.root, DAY)
        self.assertEqual([e.node_id for e in sections["decision"]], ["decision/2026-11-16-use-pipedrive-as-the-crm"])
        self.assertEqual(sections["decision"][0].descriptor, "Use Pipedrive as the CRM")

    def cli(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(REPO / "scripts" / "cortex_cli.py"), "record-decision", "--memory-root", str(self.root),
             "--title", "Use Pipedrive as the CRM", "--what", "We will run the pipeline in Pipedrive.",
             "--why", "Pricing scales better.", "--date", "2026-11-16", "--affects", "client/acme", *extra],
            capture_output=True, text=True,
        )

    def test_cli_creates_the_record_and_prints_no_decision_text(self) -> None:
        out = self.cli("--decided-by", "sample-user", "--input", "Vendor quote")
        self.assertEqual(out.returncode, 0, out.stderr)
        report = json.loads(out.stdout)
        self.assertTrue((self.root / report["path"]).is_file())
        self.assertNotIn("We will run the pipeline", out.stdout)
        self.assertFalse((self.root / ".lock").exists())

    def test_cli_refuses_a_decision_with_no_decider(self) -> None:
        out = self.cli("--decided-by", "unresolved")
        self.assertEqual(out.returncode, 1)
        self.assertFalse((self.root / "decision").exists())

    def test_cli_supersede_round_trip(self) -> None:
        first = json.loads(self.cli("--decided-by", "sample-user").stdout)
        out = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "cortex_cli.py"), "record-decision", "--memory-root", str(self.root),
             "--title", "Move to HubSpot", "--what", "HubSpot from January.", "--why", "We outgrew it.",
             "--decided-by", "sample-user", "--date", "2027-01-05", "--supersedes", first["id"]],
            capture_output=True, text=True)
        self.assertEqual(json.loads(out.stdout)["superseded"], first["id"])
        self.assertEqual(dr.read_front((self.root / first["path"]).read_text(encoding="utf-8"))["status"], "superseded")


if __name__ == "__main__":
    unittest.main()
