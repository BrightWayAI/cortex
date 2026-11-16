"""Decision records: one file per decision, under `memory/decision/`.

A decision record says what was decided, on what inputs, by whom, when, and
what earlier decision it replaces. Records are never edited to change what was
decided and never deleted: a later decision supersedes an earlier one, and the
earlier record is marked `superseded` and points forward.

Schema: references/decision-schema.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

DECISION_DIR = "decision"
_ACTOR_OK = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_NODE_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*$")
_ID_OK = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]{0,79}$")
_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


class DecisionError(ValueError):
    """Raised for an input that would produce an untrustworthy record."""


@dataclass
class Decision:
    title: str
    what: str
    why: str
    decided: date
    decided_by: str
    inputs: list[str] = field(default_factory=list)
    affects: list[str] = field(default_factory=list)
    supersedes: str | None = None
    revisit_when: str = "n/a"
    recorded_by: str = "/remember"


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = "-".join(slug.split("-")[:8])[:80].strip("-")
    if not slug:
        raise DecisionError("title must contain letters or digits")
    return slug


def _one_line(text: str, label: str, required: bool = True) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if required and not cleaned:
        raise DecisionError(f"{label} is required")
    return cleaned


def normalize_ref(ref: str) -> str:
    """Accept `decision/<id>`, `[[decision/<id>]]`, or a bare id; return the id."""
    r = ref.strip().strip("[]").strip()
    if r.endswith(".md"):
        r = r[:-3]
    if r.startswith(DECISION_DIR + "/"):
        r = r[len(DECISION_DIR) + 1 :]
    if not _ID_OK.match(r):
        raise DecisionError(f"not a decision id: {ref!r}")
    return r


def validate(d: Decision) -> None:
    _one_line(d.title, "title")
    _one_line(d.what, "what was decided")
    _one_line(d.why, "why")
    if not _ACTOR_OK.match(d.decided_by or "") or d.decided_by == "unresolved":
        raise DecisionError("decided_by must be a real Actor ID; a decision record always names who decided")
    for node in d.affects:
        if not _NODE_OK.match(node) or ".." in node:
            raise DecisionError(f"affected node is not a valid node id: {node!r}")


def render(d: Decision, decision_id: str) -> str:
    front = [
        "---",
        "type: decision",
        f"decided: {d.decided.isoformat()}",
        f"decided_by: {d.decided_by}",
        "status: active",
    ]
    if d.supersedes:
        front.append(f"supersedes: {DECISION_DIR}/{d.supersedes}")
    front.append("affects: [" + ", ".join(d.affects) + "]")
    front.append(f"recorded_by: {_one_line(d.recorded_by, 'recorded_by')}")
    front.append("---")
    inputs = [f"- {_one_line(i, 'input')}" for i in d.inputs if i and i.strip()] or ["- none recorded"]
    affects = [f"- [[{n}]]" for n in d.affects] or ["- none recorded"]
    body = [
        f"# {_one_line(d.title, 'title')}",
        "",
        "## Decision",
        d.what.strip(),
        "",
        "## Inputs",
        *inputs,
        "",
        "## Why",
        d.why.strip(),
        "",
        "## Affects",
        *affects,
        "",
        "## Revisit when",
        _one_line(d.revisit_when, "revisit when", required=False) or "n/a",
        "",
        f"<!-- {decision_id} [confirmed:{d.decided.isoformat()}] [by:{d.decided_by}] -->",
        "",
    ]
    return "\n".join(front + [""] + body)


def read_front(text: str) -> dict[str, str]:
    m = _FRONT.match(text)
    out: dict[str, str] = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def mark_superseded(text: str, new_id: str) -> str:
    m = _FRONT.match(text)
    if not m:
        raise DecisionError("superseded record has no frontmatter")
    lines = [ln for ln in m.group(1).splitlines() if not ln.startswith(("status:", "superseded_by:"))]
    out: list[str] = []
    for ln in lines:
        out.append(ln)
        if ln.startswith("decided_by:"):
            out.append("status: superseded")
            out.append(f"superseded_by: {DECISION_DIR}/{new_id}")
    if not any(ln.startswith("status:") for ln in out):
        out.extend(["status: superseded", f"superseded_by: {DECISION_DIR}/{new_id}"])
    return "---\n" + "\n".join(out) + "\n---\n" + text[m.end() :]


def plan(memory_root: Path, d: Decision) -> dict:
    """Validate and work out what would be written. Reads only; writes nothing."""
    validate(d)
    folder = memory_root / DECISION_DIR
    base = f"{d.decided.isoformat()}-{slugify(d.title)}"
    decision_id, n = base, 2
    while (folder / f"{decision_id}.md").exists():
        decision_id, n = f"{base[:76]}-{n}", n + 1

    superseded_text = None
    if d.supersedes:
        d.supersedes = normalize_ref(d.supersedes)
        old = folder / f"{d.supersedes}.md"
        if not old.is_file():
            raise DecisionError(f"superseded decision not found: {DECISION_DIR}/{d.supersedes}")
        old_text = old.read_text(encoding="utf-8")
        front = read_front(old_text)
        if front.get("type") != "decision":
            raise DecisionError(f"{DECISION_DIR}/{d.supersedes} is not a decision record")
        if front.get("status") == "superseded":
            raise DecisionError(
                f"{DECISION_DIR}/{d.supersedes} is already superseded by {front.get('superseded_by', 'another decision')}; "
                "supersede that one instead"
            )
        superseded_text = mark_superseded(old_text, decision_id)

    missing = [n_ for n_ in d.affects if not (memory_root / f"{n_}.md").is_file()]
    pointer = (
        f"DECISION [confirmed:{d.decided.isoformat()}] {_one_line(d.title, 'title')} "
        f"→ [[{DECISION_DIR}/{decision_id}]] [by:{d.decided_by}]"
    )
    return {
        "id": decision_id,
        "path": f"{DECISION_DIR}/{decision_id}.md",
        "content": render(d, decision_id),
        "superseded_id": d.supersedes,
        "superseded_content": superseded_text,
        "pointer_line": pointer,
        "missing_affects": missing,
    }
