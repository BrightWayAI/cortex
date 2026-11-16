"""Deterministic, zero-LLM generator for <config-root>/memory/index.md.

Implements the algorithm in references/memory-index.md. Pure file-walk and
string extraction — no model calls, no judgement calls about importance.
Re-running with unchanged source files produces byte-identical output
except for the refresh timestamp line.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from scripts.lib.atomic_write import atomic_write
from scripts.lib.locking import MemoryLock
from scripts.lib.decay import (
    DecayThresholds,
    classify,
    extract_confirmed_dates,
    extract_decay_profile,
    extract_entry_types,
    parse_decay_config,
)

SKIP_DIR_NAMES = {"staged", "archive", "proposals", "me"}
SYSTEM_FILES = {"DASHBOARD.md", ".decay-config.md"}
SKIP_ROOT_FILES = {"index.md", "hot.md", "log.md", "triage-log.md"}

SECTION_TITLES = {
    "user": "User profile",
    "client": "Clients",
    "person": "People",
    "company": "Companies",
    "topic": "Topics",
    "workstream": "Workstreams",
    "bizdev": "Bizdev (active prospects)",
    "decision": "Decisions",
}
SECTION_ORDER = ["user", "client", "person", "company", "topic", "workstream", "bizdev", "decision"]


@dataclass
class NodeEntry:
    node_id: str
    descriptor: str
    state: str
    last_confirmed: date | None


def _strip_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block so it is never used as a descriptor."""
    if not text.startswith("---"):
        return text
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1 :])
    return text


def _descriptor(text: str) -> str:
    text = _strip_frontmatter(text)
    lines = [ln.strip() for ln in text.splitlines()]
    non_empty = [ln for ln in lines if ln]
    if not non_empty:
        return "(empty node)"
    first = non_empty[0]
    h1 = first.lstrip("#").strip() if first.startswith("#") else None
    descriptor = None
    if h1 and "/" not in h1 and ":" not in h1 and " " in h1:
        descriptor = h1
    elif h1:
        # H1 looks like just the slug/node-id; use next non-empty line instead.
        for ln in non_empty[1:]:
            if ln.startswith(">") or ln.startswith("#"):
                continue
            descriptor = ln
            break
        if descriptor is None:
            descriptor = h1
    else:
        descriptor = first
    descriptor = descriptor.lstrip("-* ").strip()
    return (descriptor[:77] + "...") if len(descriptor) > 80 else descriptor


def _node_id_for(memory_root: Path, path: Path) -> str:
    rel = path.relative_to(memory_root).with_suffix("")
    return str(rel).replace("\\", "/")


def _section_for(memory_root: Path, path: Path) -> str | None:
    rel = path.relative_to(memory_root)
    parts = rel.parts
    if len(parts) == 1:
        if rel.name == "user.md":
            return "user"
        return None  # domain notes, handled separately
    top = parts[0]
    if top in SKIP_DIR_NAMES:
        return None
    return top


def _build_entry(memory_root: Path, path: Path, today: date, thresholds: DecayThresholds) -> NodeEntry:
    text = path.read_text(encoding="utf-8")
    node_id = _node_id_for(memory_root, path)
    descriptor = _descriptor(text)

    confirmed_dates = extract_confirmed_dates(text)
    if confirmed_dates:
        last_confirmed = max(confirmed_dates)
    else:
        last_confirmed = date.fromtimestamp(path.stat().st_mtime)

    entry_types = frozenset(extract_entry_types(text))
    decay_profile = extract_decay_profile(text)
    state = classify(
        last_confirmed=last_confirmed,
        today=today,
        thresholds=thresholds,
        entry_types=entry_types,
        decay_profile=decay_profile,
    )
    return NodeEntry(node_id=node_id, descriptor=descriptor, state=state, last_confirmed=last_confirmed)


def collect_entries(memory_root: Path, today: date) -> dict[str, list[NodeEntry]]:
    """Walk memory_root and classify every node file into a section."""
    decay_config_path = memory_root / ".decay-config.md"
    thresholds = (
        parse_decay_config(decay_config_path.read_text(encoding="utf-8"))
        if decay_config_path.exists()
        else DecayThresholds()
    )

    sections: dict[str, list[NodeEntry]] = {}
    domain_notes: list[NodeEntry] = []
    others: dict[str, list[NodeEntry]] = {}

    for path in sorted(memory_root.rglob("*.md")):
        rel = path.relative_to(memory_root)
        parts = rel.parts

        if len(parts) == 1:
            if rel.name in SKIP_ROOT_FILES or rel.name in SYSTEM_FILES:
                continue
        elif parts[0] in SKIP_DIR_NAMES:
            continue
        elif "archive" in parts[:-1]:
            continue

        section = _section_for(memory_root, path)
        entry = _build_entry(memory_root, path, today, thresholds)

        if section is None:
            if len(parts) == 1:
                domain_notes.append(entry)
            continue
        if section in SECTION_TITLES:
            sections.setdefault(section, []).append(entry)
        else:
            others.setdefault(section, []).append(entry)

    sections["_domain"] = domain_notes
    for k, v in others.items():
        sections[f"_other:{k}"] = v
    return sections


def _sort_key(entry: NodeEntry) -> tuple[int, str]:
    order = {"Fresh": 0, "Stale": 1, "Dormant": 2, "Cold": 3}
    return (order.get(entry.state, 4), entry.node_id)


def render_index(memory_root: Path, today: date, now: datetime) -> str:
    sections = collect_entries(memory_root, today)
    total = sum(len(v) for k, v in sections.items() if not k.startswith("_") or k == "_domain")

    counts_by_type = {
        k: len(v) for k, v in sections.items() if k in SECTION_TITLES and v
    }
    counts_str = ", ".join(f"{n} {t}" for t, n in counts_by_type.items()) or "none"

    lines = [
        "# Memory index",
        "",
        f"_Last updated: {now.strftime('%Y-%m-%d %H:%M')}. Auto-maintained by cortex; do not hand-edit._",
        f"_Total nodes: {total} ({counts_str})._",
        "",
    ]

    for section_key in SECTION_ORDER:
        entries = sections.get(section_key, [])
        if not entries:
            continue
        lines.append(f"## {SECTION_TITLES[section_key]}")
        for e in sorted(entries, key=_sort_key):
            confirmed_str = e.last_confirmed.isoformat() if e.last_confirmed else "unknown"
            lines.append(f"- [[{e.node_id}]] — {e.descriptor}. _{e.state}. Confirmed {confirmed_str}._")
        lines.append("")

    domain = sections.get("_domain", [])
    if domain:
        lines.append("## Domain notes")
        for e in sorted(domain, key=_sort_key):
            confirmed_str = e.last_confirmed.isoformat() if e.last_confirmed else "unknown"
            lines.append(f"- [[{e.node_id}]] — {e.descriptor}. _{e.state}. Confirmed {confirmed_str}._")
        lines.append("")

    for key in sorted(sections):
        if not key.startswith("_other:"):
            continue
        dir_name = key.split(":", 1)[1]
        entries = sections[key]
        if not entries:
            continue
        lines.append(f"## {dir_name.capitalize()}")
        for e in sorted(entries, key=_sort_key):
            confirmed_str = e.last_confirmed.isoformat() if e.last_confirmed else "unknown"
            lines.append(f"- [[{e.node_id}]] — {e.descriptor}. _{e.state}. Confirmed {confirmed_str}._")
        lines.append("")

    lines.append("## System")
    lines.append("- [[DASHBOARD]] — Auto-recall entry point.")
    lines.append("- [[.decay-config]] — Decay thresholds. Hand-editable.")
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def generate_and_write_index(memory_root: Path, today: date | None = None, now: datetime | None = None) -> Path:
    """Regenerate index.md wholesale, under lock, atomically. Returns the path written."""
    today = today or date.today()
    now = now or datetime.now()
    content = render_index(memory_root, today, now)
    target = memory_root / "index.md"
    with MemoryLock(memory_root / ".lock"):
        atomic_write(target, content)
    return target
