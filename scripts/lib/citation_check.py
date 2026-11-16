"""Deterministic citation checks for a /listen commit draft.

This is the cheap first pass that runs before the `verifier` agent. It answers
only questions a script can answer for certain:

- does each proposal cite a source at all?
- does the cited file exist inside the config root?
- does the cited line number exist in that file?
- does the proposed text appear in the cited file (near-)verbatim?

It never judges meaning. A proposal whose source exists but whose text is not
a verbatim match is reported as `needs-verifier`, not as a failure: paraphrase
is normal and is the verifier agent's job to assess.

Reports carry proposal numbers, node names, file names and statuses only. They
never carry proposal text or source text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

PROPOSAL_RE = re.compile(r"^###\s+Proposal\s+(\d+)\s*[—–-]\s*(.*)$")
FIELD_RE = re.compile(r"^-\s+\*\*([^*:]+):\*\*\s*(.*)$")
# A file citation: a relative path with an extension, optionally followed by a locator.
PATH_RE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]{1,5})")
LINE_RE = re.compile(r"\blines?\s+(\d+)(?:\s*[-–]\s*(\d+))?", re.IGNORECASE)

STATUS_PASS = "pass-verbatim"
STATUS_NEEDS = "needs-verifier"
STATUS_FAIL = "fail"

REASON_NO_SOURCE = "no-source-cited"
REASON_NOT_A_FILE = "source-is-not-a-file-path"
REASON_ESCAPES = "source-outside-config-root"
REASON_MISSING = "source-file-missing"
REASON_BAD_LINE = "cited-line-out-of-range"
REASON_NO_CONTENT = "no-proposed-content"


@dataclass
class Proposal:
    number: int
    title: str
    fields: dict[str, str] = field(default_factory=dict)
    content: str = ""


@dataclass
class Result:
    number: int
    node: str
    status: str
    reasons: list[str]
    sources: list[str]
    citation_count: int

    def as_dict(self) -> dict:
        return {
            "proposal": self.number,
            "node": self.node,
            "status": self.status,
            "reasons": self.reasons,
            "sources": self.sources,
            "citation_count": self.citation_count,
        }


def parse_draft(text: str) -> list[Proposal]:
    """Split a commit draft into proposals with their bullet fields."""
    proposals: list[Proposal] = []
    current: Proposal | None = None
    in_content = False
    for raw in text.splitlines():
        m = PROPOSAL_RE.match(raw)
        if m:
            current = Proposal(number=int(m.group(1)), title=m.group(2).strip())
            proposals.append(current)
            in_content = False
            continue
        if current is None:
            continue
        if raw.startswith("## "):
            current = None
            in_content = False
            continue
        f = FIELD_RE.match(raw)
        if f:
            key = f.group(1).strip().lower()
            current.fields[key] = f.group(2).strip()
            in_content = key == "proposed content"
            if in_content and f.group(2).strip():
                current.content = f.group(2).strip()
            continue
        if in_content:
            stripped = raw.strip()
            if stripped.startswith(">"):
                piece = stripped.lstrip(">").strip()
                current.content = f"{current.content} {piece}".strip()
            elif stripped:
                in_content = False
    return proposals


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[*_`>\[\]]", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _node_of(p: Proposal) -> str:
    placement = p.fields.get("target placement", "")
    m = re.search(r"`([^`]+)`", placement)
    if m:
        return m.group(1)
    return p.title.split(":", 1)[0].strip()


def check_proposal(p: Proposal, config_root: Path) -> Result:
    root = config_root.resolve()
    source_field = p.fields.get("source", "")
    node = _node_of(p)
    if not source_field or source_field.lower() in {"none", "n/a"}:
        return Result(p.number, node, STATUS_FAIL, [REASON_NO_SOURCE], [], 0)

    # Citations are separated by ';'. Each one may or may not be a file path.
    citations = [c.strip() for c in source_field.split(";") if c.strip()]
    reasons: list[str] = []
    sources: list[str] = []
    readable: list[tuple[str, str]] = []  # (citation text, file text)
    file_citations = 0

    for citation in citations:
        m = PATH_RE.search(citation)
        if not m:
            continue
        file_citations += 1
        rel = m.group(1)
        sources.append(rel)
        target = (root / rel).resolve()
        if root != target and root not in target.parents:
            reasons.append(REASON_ESCAPES)
            continue
        if not target.is_file():
            reasons.append(REASON_MISSING)
            continue
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            reasons.append(REASON_MISSING)
            continue
        line = LINE_RE.search(citation)
        if line:
            last = int(line.group(2) or line.group(1))
            if int(line.group(1)) < 1 or last > len(text.splitlines()):
                reasons.append(REASON_BAD_LINE)
                continue
        readable.append((citation, text))

    if file_citations == 0:
        # Thread IDs, record IDs and the like cannot be checked from disk.
        return Result(p.number, node, STATUS_NEEDS, [REASON_NOT_A_FILE], [], len(citations))
    if reasons:
        return Result(p.number, node, STATUS_FAIL, sorted(set(reasons)), sources, len(citations))
    if not p.content:
        return Result(p.number, node, STATUS_NEEDS, [REASON_NO_CONTENT], sources, len(citations))

    needle = _normalize(p.content)
    if needle and any(needle in _normalize(text) for _, text in readable):
        return Result(p.number, node, STATUS_PASS, [], sources, len(citations))
    return Result(p.number, node, STATUS_NEEDS, [], sources, len(citations))


def check_draft(draft_text: str, config_root: Path) -> list[Result]:
    return [check_proposal(p, config_root) for p in parse_draft(draft_text)]


def summarize(results: list[Result]) -> dict:
    counts = {STATUS_PASS: 0, STATUS_NEEDS: 0, STATUS_FAIL: 0}
    for r in results:
        counts[r.status] += 1
    return {"total": len(results), **counts}
