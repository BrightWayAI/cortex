"""Sort the proposals in a /listen commit draft into review groups for /morning.

Groups follow the autonomy policy's tiers (references/autonomy-policy.md):

- `brief`  — came from yesterday's brief (Step 1.5). /morning has its own rules
             for these; this script only sets them aside.
- `batch`  — medium risk: passed verification and lists no conflict. Shown once
             as a list and accepted together.
- `review` — high risk: failed, unverifiable, not checked, or in conflict.
             Walked one at a time.

The rule is deliberately conservative: anything that is not a clean `pass`
with no conflict goes to `review`. Reports carry numbers, node names and
reasons only, never proposal text.
"""
from __future__ import annotations

from dataclasses import dataclass

from scripts.lib import citation_check as cc

GROUP_BRIEF = "brief"
GROUP_BATCH = "batch"
GROUP_REVIEW = "review"

BRIEF_TAG = "listen-step-1.5"
NO_CONFLICT = {"", "none", "none.", "n/a", "-", "—"}


@dataclass
class Triage:
    number: int
    node: str
    group: str
    why: list[str]

    def as_dict(self) -> dict:
        return {"proposal": self.number, "node": self.node, "group": self.group, "why": self.why}


def _is_brief(p: cc.Proposal) -> bool:
    haystack = " ".join([p.title, *p.fields.values()]).lower()
    return BRIEF_TAG in haystack


def triage_proposal(p: cc.Proposal) -> Triage:
    node = cc._node_of(p)
    if _is_brief(p):
        return Triage(p.number, node, GROUP_BRIEF, ["from-yesterdays-brief"])
    why: list[str] = []
    verdict = p.fields.get("verification", "").strip().lower()
    if not verdict:
        why.append("not-checked")
    elif verdict != "pass":
        why.append(f"verification-{verdict}" if verdict in ("fail", "unverifiable", "not-run") else "verification-unrecognized")
    if p.fields.get("conflicts", "").strip().lower() not in NO_CONFLICT:
        why.append("conflict-listed")
    if "conflicts" not in p.fields:
        why.append("conflicts-field-missing")
    if why:
        return Triage(p.number, node, GROUP_REVIEW, why)
    return Triage(p.number, node, GROUP_BATCH, [])


def triage_draft(text: str) -> list[Triage]:
    return [triage_proposal(p) for p in cc.parse_draft(text)]


def summarize(items: list[Triage]) -> dict:
    counts = {GROUP_BRIEF: 0, GROUP_BATCH: 0, GROUP_REVIEW: 0}
    for t in items:
        counts[t.group] += 1
    return {"total": len(items), **counts}
