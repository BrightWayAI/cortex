"""Start-up and shut-down bookkeeping for an unattended /listen run.

`start` does, in order and without any judgment:

1. reachability: the config root must be readable and writable (probe file);
2. privacy defaults: `<config-root>/.gitignore` protects the raw archive and
   staged drafts (best-effort, never blocks);
3. in-progress marker, so /morning does not diff memory mid-run;
4. the memory write lock.

`finish` removes the marker and the lock. It is safe to call on any exit path.

These were prose steps in commands/listen.md (Steps 0, 0.5, 0.7, 0.8). The
behavior is the same; it is a script so an unattended run cannot get the shell
details wrong.
"""
from __future__ import annotations

import os
import re
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

MARKER_REL = Path("memory") / "staged" / "queues" / "listen-in-progress"
PROBE_REL = Path("memory") / "staged" / "queues" / ".listen-probe"
LOCK_REL = Path("memory") / ".lock"
EXPECTED_RUN = timedelta(minutes=30)
MARKER_GRACE = timedelta(minutes=2)
LOCK_STALE_SECONDS = 600
REQUIRED_IGNORES = ("archive/", "memory/staged/")
LEGACY_EQUIVALENT = {"memory/staged/": ("memory/staged/commit-drafts/",)}
ADDED_HEADER = "# Added by cortex /listen first-run — privacy defaults"
CLOUD_MARKERS = (
    ("iCloud", "Library/Mobile Documents/com~apple~CloudDocs"),
    ("Dropbox", "Dropbox"),
    ("OneDrive", "OneDrive"),
    ("Google Drive", "Google Drive"),
)
_FENCE = re.compile(r"```gitignore\n(.*?)```", re.DOTALL)


def probe(root: Path) -> str | None:
    """Return None if the root is readable and writable, else a short reason."""
    try:
        if not root.is_dir():
            return "config root is not a directory"
        target = root / PROBE_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("probe\n", encoding="utf-8")
        target.unlink()
    except OSError as e:
        return f"{type(e).__name__}"
    return None


def template_block(template_path: Path | None) -> str | None:
    if template_path is None:
        return None
    try:
        m = _FENCE.search(template_path.read_text(encoding="utf-8"))
    except OSError:
        return None
    return m.group(1) if m else None


def ensure_gitignore(root: Path, template_path: Path | None) -> str:
    """Create or extend <root>/.gitignore. Returns created | updated | ok | failed."""
    path = root / ".gitignore"
    try:
        if not path.exists():
            block = template_block(template_path) or "\n".join(REQUIRED_IGNORES) + "\n"
            path.write_text(block, encoding="utf-8")
            return "created"
        text = path.read_text(encoding="utf-8")
        present = {ln.strip() for ln in text.splitlines()}
        missing = [
            pat for pat in REQUIRED_IGNORES
            if pat not in present and not all(alt in present for alt in LEGACY_EQUIVALENT.get(pat, ("\0",)))
        ]
        if not missing:
            return "ok"
        addition = ("" if text.endswith("\n") or not text else "\n") + f"\n{ADDED_HEADER}\n" + "\n".join(missing) + "\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(addition)
        return "updated"
    except OSError:
        return "failed"


def cloud_sync_provider(root: Path, home: Path) -> str | None:
    try:
        resolved = str(root.resolve())
        home_s = str(home.resolve())
    except OSError:
        return None
    if not resolved.startswith(home_s + os.sep):
        return None
    rel = resolved[len(home_s) + 1 :]
    for name, marker in CLOUD_MARKERS:
        if rel == marker or rel.startswith(marker + os.sep) or (name == "OneDrive" and rel.startswith("OneDrive")):
            return name
    return None


def _marker_state(root: Path, now: datetime) -> tuple[str, int | None]:
    """Return (absent | stale | running, minutes since start)."""
    path = root / MARKER_REL
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return "absent", None
    parts = raw.split("|")
    try:
        started, expected = datetime.fromisoformat(parts[0]), datetime.fromisoformat(parts[1])
    except (ValueError, IndexError):
        return "stale", None
    if started.tzinfo is None:
        started, expected = started.replace(tzinfo=now.tzinfo), expected.replace(tzinfo=now.tzinfo)
    if now < expected + MARKER_GRACE:
        return "running", max(int((now - started).total_seconds() // 60), 0)
    return "stale", None


def _lock_age_seconds(lock: Path, now: datetime) -> float | None:
    try:
        raw = lock.read_text(encoding="utf-8")
        mtime = lock.stat().st_mtime
    except OSError:
        return None
    for piece in raw.replace("\n", "|").split("|"):
        try:
            stamp = datetime.fromisoformat(piece.strip())
        except ValueError:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=now.tzinfo)
        return (now - stamp).total_seconds()
    return now.timestamp() - mtime


def start(
    root: Path,
    now: datetime,
    home: Path,
    template_path: Path | None = None,
    force: bool = False,
    retries: int = 2,
    wait_seconds: float = 60.0,
    sleep=time.sleep,
    clock=None,
) -> dict:
    clock = clock or (lambda: datetime.now().astimezone())
    reason = probe(root)
    if reason:
        return {"status": "unreachable", "reason": reason}

    result: dict = {
        "status": "ok",
        "gitignore": ensure_gitignore(root, template_path),
        "cloud_sync": cloud_sync_provider(root, home),
    }

    state, minutes = _marker_state(root, now)
    if state == "running" and not force:
        return {**result, "status": "already-running", "started_minutes_ago": minutes}
    result["replaced_stale_marker"] = state == "stale" or (state == "running" and force)

    lock = root / LOCK_REL
    attempt = 0
    while True:
        age = _lock_age_seconds(lock, clock() if attempt else now)
        if age is None or age > LOCK_STALE_SECONDS:
            break
        if attempt >= retries:
            return {**result, "status": "busy", "lock_age_seconds": int(age)}
        attempt += 1
        sleep(wait_seconds)
    result["reclaimed_stale_lock"] = age is not None

    token = uuid.uuid4().hex[:16]
    marker = root / MARKER_REL
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        f"{now.isoformat(timespec='seconds')}|{(now + EXPECTED_RUN).isoformat(timespec='seconds')}|{token}\n", encoding="utf-8"
    )
    lock.write_text(f"listen|{now.isoformat(timespec='seconds')}|{token}\n", encoding="utf-8")
    result["token"] = token
    return result


def finish(root: Path, token: str) -> dict:
    """Remove the marker and lock that the run holding `token` created.

    A run that did not start (another run was in progress, or the lock was
    busy) has no token and must not call this: the marker and lock on disk
    belong to someone else. Anything not carrying this token is left alone.
    """
    removed = {}
    for name, rel in (("marker", MARKER_REL), ("lock", LOCK_REL)):
        path = root / rel
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            removed[name] = "absent"
            continue
        except OSError:
            removed[name] = "failed"
            continue
        # The token is always the last field; never match the command name or a timestamp.
        if not token or content.strip().split("|")[-1] != token:
            removed[name] = "not-ours"
            continue
        try:
            path.unlink()
            removed[name] = "removed"
        except OSError:
            removed[name] = "failed"
    return removed
