"""Read-only summary of what changed in memory since the previous commit.

Used by /morning before it walks the overnight draft. It answers, without any
judgment: is memory under git, is it safe to diff right now, and what changed.
It never commits, stages, or modifies anything. It reports paths and counts,
never file contents.
"""
from __future__ import annotations

import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

GRACE = timedelta(minutes=2)


def _git(memory: Path, *args: str) -> tuple[int, str]:
    try:
        out = subprocess.run(["git", "-C", str(memory), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return out.returncode, out.stdout


def _listen_running(memory: Path, now: datetime) -> dict | None:
    marker = memory / "staged" / "queues" / "listen-in-progress"
    try:
        raw = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    parts = raw.split("|")
    try:
        started = datetime.fromisoformat(parts[0])
        expected = datetime.fromisoformat(parts[1])
    except (ValueError, IndexError):
        return {"stale": True}
    if started.tzinfo is None:
        started, expected = started.replace(tzinfo=now.tzinfo), expected.replace(tzinfo=now.tzinfo)
    if now < expected + GRACE:
        return {"stale": False, "started_minutes_ago": max(int((now - started).total_seconds() // 60), 0)}
    return {"stale": True}


def summarize(memory: Path, now: datetime, today: date | None = None) -> dict:
    today = today or now.date()
    if not (memory / ".git").exists():
        return {"status": "not-git"}

    running = _listen_running(memory, now)
    if running and not running["stale"]:
        return {"status": "listen-running", "started_minutes_ago": running["started_minutes_ago"]}
    stale_marker = bool(running and running["stale"])

    code, _ = _git(memory, "rev-parse", "--verify", "--quiet", "HEAD~1")
    if code != 0:
        return {"status": "fresh", "stale_listen_marker": stale_marker}

    _, porcelain = _git(memory, "status", "--porcelain")
    dirty = [ln for ln in porcelain.splitlines() if ln.strip()]
    if dirty:
        return {
            "status": "dirty",
            "dirty_count": len(dirty),
            "dirty_files": [ln[3:] for ln in dirty[:10]],
            "stale_listen_marker": stale_marker,
        }

    _, prev = _git(memory, "log", "-1", "--format=%cd", "--date=short", "HEAD~1")
    prev_date = prev.strip()
    if prev_date == today.isoformat():
        return {"status": "no-overnight-commit", "previous_commit_date": prev_date, "stale_listen_marker": stale_marker}

    _, numstat = _git(memory, "diff", "--numstat", "HEAD~1..HEAD")
    by_dir: dict[str, list[str]] = {}
    insertions = deletions = files = 0
    for line in numstat.splitlines():
        cols = line.split("\t")
        if len(cols) != 3:
            continue
        added, removed, path = cols
        files += 1
        insertions += int(added) if added.isdigit() else 0
        deletions += int(removed) if removed.isdigit() else 0
        parts = Path(path).parts
        top = parts[0] if len(parts) > 1 else "(root)"
        by_dir.setdefault(top, []).append(Path(path).stem)
    return {
        "status": "changed" if files else "no-changes",
        "previous_commit_date": prev_date,
        "files": files,
        "insertions": insertions,
        "deletions": deletions,
        "by_directory": {k: {"count": len(v), "nodes": sorted(v)[:5]} for k, v in sorted(by_dir.items())},
        "stale_listen_marker": stale_marker,
    }
