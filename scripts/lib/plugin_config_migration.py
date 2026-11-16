"""One-time cleanup of legacy files in ``<config-root>/plugins/``.

Plans and applies three kinds of move, all inside the plugins directory:

1. ``ops.schedules.md`` (pre-reorg location) becomes ``ops/schedules.md`` when
   it holds a schedule table and no definitions file exists yet. Otherwise the
   bundled starter template is copied there, if the caller supplied one.
2. Retired config files are archived, but only once their replacement exists.
3. Backup siblings (``*.bak-YYYY-MM-DD*``) are archived.

Nothing is deleted and nothing is overwritten. The plan lists file names only;
this module never returns or prints file contents. ``plan()`` is read-only.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Optional

from scripts.lib.atomic_write import atomic_write

MARKER_NAME = ".migration-plugin-configs-done"
ARCHIVE_DIR = "archive"
LEGACY_SCHEDULES = "ops.schedules.md"
SCHEDULES_TARGET = "ops/schedules.md"

# retired file -> the file that must already exist before the retired one is archived
RETIRED_WHEN_REPLACED = {
    "client-status.user-context.md": "clients-status.user-context.md",
}

_BAK_RE = re.compile(r"^(?P<base>.+?)(?:\.md)?\.bak-(?P<stamp>\d{4}-\d{2}-\d{2}[A-Za-z0-9]*)$")
_TABLE_HEADER_RE = re.compile(r"^\|\s*Name\s*\|.*(Cron|Schedule)", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class Action:
    kind: str  # "move" | "create" | "skip"
    source: Optional[str]  # relative to the plugins dir
    target: Optional[str]  # relative to the plugins dir
    reason: str

    def as_dict(self) -> dict:
        return asdict(self)


def _free_name(directory: Path, name: str, taken: set[str]) -> str:
    """Return ``name``, or ``name`` with a numeric suffix, that is not in use."""
    stem, ext = os.path.splitext(name)
    candidate, n = name, 2
    while (directory / candidate).exists() or candidate in taken:
        candidate = f"{stem}-{n}{ext}"
        n += 1
    taken.add(candidate)
    return candidate


def _archive_name(filename: str, today: date) -> str:
    m = _BAK_RE.match(filename)
    if m:
        return f"{m.group('base')}.{m.group('stamp')}.bak.md"
    stem = filename[:-3] if filename.endswith(".md") else filename
    return f"{stem}.{today.isoformat()}.md"


def has_schedule_table(text: str) -> bool:
    return bool(_TABLE_HEADER_RE.search(text))


def plan(plugins_dir: Path, today: date, schedules_template: Optional[Path] = None) -> list[Action]:
    actions: list[Action] = []
    if not plugins_dir.is_dir():
        return actions
    archive = plugins_dir / ARCHIVE_DIR
    taken: set[str] = set()

    def archive_move(name: str, reason: str) -> None:
        dest = _free_name(archive, _archive_name(name, today), taken)
        actions.append(Action("move", name, f"{ARCHIVE_DIR}/{dest}", reason))

    legacy = plugins_dir / LEGACY_SCHEDULES
    target = plugins_dir / SCHEDULES_TARGET
    if target.exists():
        if legacy.is_file():
            archive_move(LEGACY_SCHEDULES, "definitions already exist at ops/schedules.md")
    elif legacy.is_file() and has_schedule_table(legacy.read_text(encoding="utf-8")):
        actions.append(Action("create", LEGACY_SCHEDULES, SCHEDULES_TARGET,
                              "carry existing schedule definitions to the current location"))
        archive_move(LEGACY_SCHEDULES, "superseded by ops/schedules.md")
    elif schedules_template is not None and schedules_template.is_file():
        actions.append(Action("create", None, SCHEDULES_TARGET, "copy the bundled starter template"))
        if legacy.is_file():
            archive_move(LEGACY_SCHEDULES, "no schedule table found; starter template used instead")
    else:
        actions.append(Action("skip", None, SCHEDULES_TARGET,
                              "no legacy definitions and no --schedules-template supplied"))

    for retired, replacement in sorted(RETIRED_WHEN_REPLACED.items()):
        if not (plugins_dir / retired).is_file():
            continue
        if (plugins_dir / replacement).is_file():
            archive_move(retired, f"replaced by {replacement}")
        else:
            actions.append(Action("skip", retired, None, f"{replacement} does not exist yet; still the only copy"))

    for entry in sorted(plugins_dir.iterdir()):
        if entry.is_file() and _BAK_RE.match(entry.name):
            archive_move(entry.name, "backup copy")

    return actions


def _inside(plugins_dir: Path, rel: str) -> Path:
    root = plugins_dir.resolve()
    path = (root / rel).resolve()
    if root != path and root not in path.parents:
        raise ValueError(f"{rel!r} resolves outside the plugins directory")
    return path


def apply(plugins_dir: Path, actions: list[Action], schedules_template: Optional[Path] = None) -> None:
    """Carry out ``actions``. Creates run before moves so a carried file is read first."""
    for a in (x for x in actions if x.kind == "create"):
        dest = _inside(plugins_dir, a.target)
        if dest.exists():
            raise FileExistsError(f"{a.target} already exists; refusing to overwrite")
        src = _inside(plugins_dir, a.source) if a.source else schedules_template
        dest.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(dest, src.read_text(encoding="utf-8"))
    for a in (x for x in actions if x.kind == "move"):
        src, dest = _inside(plugins_dir, a.source), _inside(plugins_dir, a.target)
        if dest.exists():
            raise FileExistsError(f"{a.target} already exists; refusing to overwrite")
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dest)


def marker_text(today: date, actions: list[Action]) -> str:
    moved = sum(1 for a in actions if a.kind == "move")
    created = sum(1 for a in actions if a.kind == "create")
    return f"{today.isoformat()} plugin-configs migration: {moved} archived, {created} created\n"
