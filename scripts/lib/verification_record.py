"""Record verification results in a /listen commit draft.

Merges the deterministic citation check with the `verifier` agent's JSON and
writes the result next to each proposal. The merge rules are the ones in
references/verification.md, enforced here so a workflow cannot get them wrong:

- a deterministic `fail` is final;
- a claim the verifier did not return a valid result for is `not-run`, never
  `pass`;
- a `pass` at `low` confidence becomes `unverifiable`.

Re-running replaces the previous fields; it never stacks duplicates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from scripts.lib import citation_check as cc

VERDICTS = ("pass", "fail", "unverifiable", "not-run")
CONFIDENCES = ("high", "medium", "low")
FIELD_NAMES = ("Citation check", "Verification", "Verifier confidence", "Evidence", "Verification reasons")
SUMMARY_HEADING = "## Verification"
MAX_QUOTE_WORDS = 25

_OWN_FIELD_RE = re.compile(r"^-\s+\*\*(" + "|".join(re.escape(n) for n in FIELD_NAMES) + r"):\*\*")


@dataclass
class Record:
    number: int
    citation_check: str
    verdict: str
    confidence: str = ""
    evidence: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "proposal": self.number,
            "citation_check": self.citation_check,
            "verification": self.verdict,
            "confidence": self.confidence or None,
            "reasons": self.reasons,
        }


def _clean(text: object) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def _evidence_line(item: object) -> str | None:
    if not isinstance(item, dict):
        return None
    source = _clean(item.get("source", ""))
    if not source:
        return None
    locator = _clean(item.get("locator", ""))
    words = _clean(item.get("quote", "")).replace('"', "'").split()
    quote = " ".join(words[:MAX_QUOTE_WORDS]) + (" …" if len(words) > MAX_QUOTE_WORDS else "")
    head = f"{source} ({locator})" if locator else source
    return f'{head} — "{quote}"' if quote else head


def merge(det_results: list[cc.Result], verifier: dict | None) -> list[Record]:
    by_id: dict[str, dict] = {}
    if isinstance(verifier, dict) and isinstance(verifier.get("results"), list):
        for item in verifier["results"]:
            if isinstance(item, dict) and "id" in item:
                by_id[str(item["id"]).strip()] = item

    records: list[Record] = []
    for det in det_results:
        if det.status == cc.STATUS_FAIL:
            records.append(Record(det.number, det.status, "fail", "high", [], list(det.reasons)))
            continue
        item = by_id.get(str(det.number))
        if item is None:
            records.append(Record(det.number, det.status, "not-run", "", [], ["verifier-not-run"]))
            continue
        verdict = _clean(item.get("verdict", "")).lower()
        confidence = _clean(item.get("confidence", "")).lower()
        if verdict not in ("pass", "fail", "unverifiable") or confidence not in CONFIDENCES:
            records.append(Record(det.number, det.status, "not-run", "", [], ["invalid-verifier-result"]))
            continue
        reasons = [_clean(r) for r in item.get("reasons", []) if _clean(r)] if isinstance(item.get("reasons"), list) else []
        evidence = [e for e in (_evidence_line(x) for x in item.get("evidence", []) or []) if e] if isinstance(item.get("evidence"), list) else []
        if verdict == "pass" and confidence == "low":
            verdict = "unverifiable"
            reasons.append("pass-at-low-confidence")
        if verdict == "pass" and not evidence:
            verdict = "unverifiable"
            reasons.append("pass-without-evidence")
        records.append(Record(det.number, det.status, verdict, confidence, evidence, reasons))
    return records


def summarize(records: list[Record]) -> dict:
    counts = {v: 0 for v in VERDICTS}
    for r in records:
        counts[r.verdict] += 1
    return {"total": len(records), **counts}


def _field_lines(r: Record) -> list[str]:
    return [
        f"- **Citation check:** {r.citation_check}",
        f"- **Verification:** {r.verdict}",
        f"- **Verifier confidence:** {r.confidence or 'n/a'}",
        f"- **Evidence:** {'; '.join(r.evidence) if r.evidence else 'none'}",
        f"- **Verification reasons:** {', '.join(r.reasons) if r.reasons else 'none'}",
    ]


def _summary_block(records: list[Record], stamp: str) -> list[str]:
    s = summarize(records)
    return [
        SUMMARY_HEADING,
        f"Checked at {stamp}. See `references/verification.md`.",
        f"- {s['pass']} pass",
        f"- {s['fail']} fail",
        f"- {s['unverifiable']} unverifiable",
        f"- {s['not-run']} not run",
        "",
    ]


def apply_to_draft(text: str, records: list[Record], stamp: str) -> str:
    """Return the draft with verification fields written under each proposal."""
    by_number = {r.number: r for r in records}
    lines = text.splitlines()

    # Drop any previous run's fields and summary section.
    kept: list[str] = []
    skipping_summary = False
    for line in lines:
        if line.strip() == SUMMARY_HEADING:
            skipping_summary = True
            continue
        if skipping_summary:
            if line.startswith("## ") or line.startswith("### "):
                skipping_summary = False
            else:
                continue
        if _OWN_FIELD_RE.match(line):
            continue
        kept.append(line)

    out: list[str] = []
    summary_done = False
    i = 0
    n = len(kept)
    while i < n:
        line = kept[i]
        if not summary_done and line.strip() == "## Proposals":
            out.extend(_summary_block(records, stamp))
            summary_done = True
        m = cc.PROPOSAL_RE.match(line)
        if not m:
            out.append(line)
            i += 1
            continue
        # Collect the proposal block up to the next heading.
        block = [line]
        i += 1
        while i < n and not kept[i].startswith("### ") and not kept[i].startswith("## "):
            block.append(kept[i])
            i += 1
        trailing: list[str] = []
        while len(block) > 1 and not block[-1].strip():
            trailing.append(block.pop())
        record = by_number.get(int(m.group(1)))
        if record is not None:
            block.extend(_field_lines(record))
        out.extend(block)
        out.extend(reversed(trailing) if trailing else ([""] if i < n else []))
    result = "\n".join(out)
    return result + ("\n" if text.endswith("\n") and not result.endswith("\n") else "")
