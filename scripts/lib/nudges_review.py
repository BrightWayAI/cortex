"""Which staged nudges are still open, for /morning's "Needs a nudge" section.

Read-only. Reads the day files growth's `/nudges` staged under
`<config-root>/memory/staged/nudges/` and the ledger beside them, and returns
the items the user has not yet acted on, snoozed, or dismissed.

An item is closed when the ledger has an `acted`, `snoozed`, or `dismissed`
line for its key dated on or after the day file it appears in. A day file with
no open items left is reported as archivable. Reports carry keys, triggers,
subjects and dates; they never carry the drafted message.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

NUDGE_RE = re.compile(r"^###\s+Nudge\s+(\d+)\s*[—–-]\s*(.*)$")
FIELD_RE = re.compile(r"^-\s+\*\*([^*:]+):\*\*\s*(.*)$")
FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
CLOSING = ("acted", "snoozed", "dismissed")


@dataclass
class Item:
    file: str
    number: int
    subject: str
    fields: dict[str, str] = field(default_factory=dict)
    has_draft: bool = False

    def as_dict(self) -> dict:
        return {
            "file": self.file,
            "number": self.number,
            "key": self.fields.get("key", ""),
            "trigger": self.fields.get("trigger", ""),
            "subject": self.subject,
            "quiet_since": self.fields.get("quiet since", ""),
            "days_quiet": self.fields.get("days quiet", ""),
            "has_draft": self.has_draft,
        }


def _day(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def parse_day_file(name: str, text: str) -> list[Item]:
    items: list[Item] = []
    current: Item | None = None
    in_draft = False
    for raw in text.splitlines():
        m = NUDGE_RE.match(raw)
        if m:
            current = Item(file=name, number=int(m.group(1)), subject=m.group(2).strip())
            items.append(current)
            in_draft = False
            continue
        if current is None:
            continue
        f = FIELD_RE.match(raw)
        if f:
            key = f.group(1).strip().lower()
            value = f.group(2).strip()
            current.fields[key] = value
            in_draft = key == "draft"
            if in_draft and value and not value.lower().startswith("none"):
                current.has_draft = True
            continue
        if in_draft and raw.strip().startswith(">"):
            body = raw.strip().lstrip(">").strip()
            if body and not body.lower().startswith("none"):
                current.has_draft = True
    return items


def closed_on(ledger_text: str) -> dict[str, date]:
    """Latest closing date per key."""
    latest: dict[str, date] = {}
    for line in ledger_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict) or entry.get("event") not in CLOSING:
            continue
        key, when = entry.get("key"), _day(entry.get("ts"))
        if isinstance(key, str) and when and (key not in latest or when > latest[key]):
            latest[key] = when
    return latest


def open_nudges(nudges_dir: Path) -> dict:
    if not nudges_dir.is_dir():
        return {"files": [], "open": [], "archivable": [], "summary": {"open": 0, "files": 0}}
    ledger_path = nudges_dir / "ledger.jsonl"
    closed = closed_on(ledger_path.read_text(encoding="utf-8", errors="replace")) if ledger_path.is_file() else {}

    files = sorted(p for p in nudges_dir.iterdir() if p.is_file() and FILE_RE.match(p.name))
    open_items: list[Item] = []
    archivable: list[str] = []
    seen: set[str] = set()
    # Newest file first, so a key flagged again later is shown once, from its latest file.
    for path in reversed(files):
        day = _day(FILE_RE.match(path.name).group(1))  # type: ignore[union-attr]
        items = parse_day_file(path.name, path.read_text(encoding="utf-8", errors="replace"))
        still_open = 0
        for item in items:
            key = item.fields.get("key", "")
            if not key:
                # Cannot be tracked or closed; keep showing it rather than hide it.
                open_items.append(item)
                still_open += 1
                continue
            if key in seen:
                continue
            if key in closed and day is not None and closed[key] >= day:
                continue
            seen.add(key)
            open_items.append(item)
            still_open += 1
        if still_open == 0:
            archivable.append(path.name)
    open_items.sort(key=lambda i: (i.file, i.number))
    return {
        "files": [p.name for p in files],
        "open": [i.as_dict() for i in open_items],
        "archivable": sorted(archivable),
        "summary": {"open": len(open_items), "files": len(files)},
    }
