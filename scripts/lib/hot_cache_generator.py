"""Deterministic, zero-LLM generator for <config-root>/memory/hot.md.

Implements the node-local part of references/hot-cache.md's generation
logic: changelog entries, open threads, and decisions from the last 7 days,
pulled straight from each node file. Pure file-walk and date-filtering, no
model calls.

Not yet implemented (documented limitation, not silently dropped): pulling
from `<config-root>/briefs/` reflections or `staged/commit-drafts/archive/`
resolved drafts (references/hot-cache.md steps 7-8) — those subsystems are
outside the scope of this refactor phase. `render_hot_cache` only covers
steps 1-6 (node changelog / open threads / decisions).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from scripts.lib.atomic_write import atomic_write
from scripts.lib.locking import MemoryLock
from scripts.lib.sections import get_section

# Accepts both the legacy "- YYYY-MM-DD — text" form and the current
# "[node] LOG YYYY-MM-DD — text" form written by /morning and /end-day.
CHANGELOG_LINE_RE = re.compile(
    r"^(?:\[[^\]]+\]\s+LOG\s+|\-?\s*\[?)(\d{4}-\d{2}-\d{2})\]?\s*[—\-:]\s*(.+)$"
)
DECISION_RE = re.compile(
    r"^\[(?P<node>[^\]]+)\]\s+DECISION\s*\((?P<date>\d{4}-\d{2}-\d{2})[^)]*\)"
    r"(?:\s*\[confirmed:(?P<confirmed>\d{4}-\d{2}-\d{2})\])?(?:\s*\[[a-z]+:[^\]]*\])*"
    r":\s*(?P<body>.+?)\s*$",
    re.MULTILINE,
)
OPEN_THREAD_RE = re.compile(r"^\-\s*(?:\*\*)?\[(?:WAITING:[^\]]+|P[012](?:\s+\d{4}-\d{2}-\d{2})?)\].*$", re.MULTILINE)
OPEN_SECTION_HEADINGS = ("## Open threads", "## Open Threads", "## Open loops", "## Open Loops", "## Open Operational Threads")

WINDOW_DAYS = 7


def _node_id_for(memory_root: Path, path: Path) -> str:
    rel = path.relative_to(memory_root).with_suffix("")
    return str(rel).replace("\\", "/")


@dataclass
class WorkedOnEntry:
    when: date
    node_id: str
    summary: str


def _recent_changelog_lines(text: str, node_id: str, cutoff: date) -> list[WorkedOnEntry]:
    body = get_section(text, "## Changelog")
    if not body:
        return []
    out = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        m = CHANGELOG_LINE_RE.match(line)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if d >= cutoff:
            out.append(WorkedOnEntry(when=d, node_id=node_id, summary=m.group(2).strip()))
    return out


def _recent_decisions(text: str, cutoff: date) -> list[str]:
    out = []
    for m in DECISION_RE.finditer(text):
        confirmed = m.group("confirmed")
        entry_date_str = confirmed or m.group("date")
        try:
            d = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d >= cutoff:
            out.append(f"{entry_date_str} — [[{m.group('node')}]]: {m.group('body').strip()}")
    return out


def _open_threads(text: str, node_id: str) -> list[str]:
    body = "\n".join(get_section(text, h) or "" for h in OPEN_SECTION_HEADINGS)
    if not body.strip():
        return []
    out = []
    for line in body.splitlines():
        line = line.strip()
        if OPEN_THREAD_RE.match(line):
            out.append(f"[[{node_id}]] — {line.lstrip('- ').strip()}")
    return out


def render_hot_cache(memory_root: Path, today: date, now: datetime, trigger: str = "manual") -> str:
    cutoff = today - timedelta(days=WINDOW_DAYS)

    worked_on: list[WorkedOnEntry] = []
    decisions: list[str] = []
    threads: list[str] = []

    for path in sorted(memory_root.rglob("*.md")):
        rel = path.relative_to(memory_root)
        parts = rel.parts
        if parts[0] in {"staged", "archive", "proposals", "me"}:
            continue
        if "archive" in parts[:-1]:
            continue
        if len(parts) == 1 and rel.name in {"index.md", "hot.md", "log.md", "triage-log.md", "DASHBOARD.md", ".decay-config.md"}:
            continue

        text = path.read_text(encoding="utf-8")
        node_id = _node_id_for(memory_root, path)

        worked_on.extend(_recent_changelog_lines(text, node_id, cutoff))
        decisions.extend(_recent_decisions(text, cutoff))
        threads.extend(_open_threads(text, node_id))

    worked_on.sort(key=lambda e: (e.when, e.node_id))
    decisions.sort()
    threads.sort()

    lines = [
        "# Hot cache",
        "",
        f"_Last refreshed: {now.strftime('%Y-%m-%d %H:%M')} by {trigger}._",
        f"_Rolling window: last {WINDOW_DAYS} days._",
        "",
        "## What I worked on (last 7 days)",
    ]
    if worked_on:
        for e in worked_on:
            lines.append(f"- {e.when.isoformat()} — [[{e.node_id}]]: {e.summary}")
    else:
        lines.append("- (nothing logged in the last 7 days)")
    lines.append("")

    lines.append("## Active threads (open, modified in last 7 days)")
    if threads:
        lines.extend(f"- {t}" for t in threads)
    else:
        lines.append("- (no open threads touched in the last 7 days)")
    lines.append("")

    lines.append("## Recent decisions")
    if decisions:
        lines.extend(f"- {d}" for d in decisions)
    else:
        lines.append("- (no decisions in the last 7 days)")
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def generate_and_write_hot_cache(
    memory_root: Path, today: date | None = None, now: datetime | None = None, trigger: str = "manual"
) -> Path:
    today = today or date.today()
    now = now or datetime.now()
    content = render_hot_cache(memory_root, today, now, trigger)
    target = memory_root / "hot.md"
    with MemoryLock(memory_root / ".lock"):
        atomic_write(target, content)
    return target
