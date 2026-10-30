"""Classify whether a resolved Cortex config root is actually reachable.

Resolution (``config_root.py``) says where the root *should* be. This module
says whether this session can see it, and what to tell the user when it cannot.
Every entry point (session hook, /status, /diagnose, write-skills) shares it so
a degraded state is never reported as healthy.

Read-only by contract: only ``stat``/``iterdir`` calls, never create, write or
mkdir anything.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Mapping

from scripts.lib.config_root import ConfigRootResult

_TRUTHY = frozenset({"1", "true", "yes", "on"})
CLOUD_ROOT_HINT = "~/cortex-root"


class RootState(str, Enum):
    OK = "OK"
    REMOTE_NOT_ATTACHED = "REMOTE_NOT_ATTACHED"
    LOCAL_MISSING = "LOCAL_MISSING"
    EXISTS_BUT_EMPTY = "EXISTS_BUT_EMPTY"


def is_remote_session(environ: Mapping[str, str]) -> bool:
    """True inside a remote/cloud session. The single place hosts are detected."""
    return environ.get("CLAUDE_CODE_REMOTE", "").strip().lower() in _TRUTHY


def _has_memory(root: Path) -> bool:
    memory = root / "memory"
    try:
        return memory.is_dir() and any(memory.iterdir())
    except OSError:
        return False


def classify(result: ConfigRootResult, environ: Mapping[str, str]) -> RootState:
    root = result.path
    try:
        is_dir = root.is_dir()
    except OSError:
        is_dir = False
    if not is_dir:
        return RootState.REMOTE_NOT_ATTACHED if is_remote_session(environ) else RootState.LOCAL_MISSING
    return RootState.OK if _has_memory(root) else RootState.EXISTS_BUT_EMPTY


def user_message(state: RootState, result: ConfigRootResult | None = None) -> str:
    """The one plain sentence to show the user for a non-OK state ("" for OK)."""
    where = str(result.path) if result is not None else "the resolved config folder"
    if state is RootState.OK:
        return ""
    if state is RootState.REMOTE_NOT_ATTACHED:
        return (
            "Your Nucleus files are on your Mac and this chat can't see them yet. "
            f"In the Claude desktop app, use + → Add folder and pick {CLOUD_ROOT_HINT}, "
            "then send any message."
        )
    if state is RootState.LOCAL_MISSING:
        return (
            f"Your Nucleus config folder {where} doesn't exist. Run /start-nucleus to create "
            "it, or fix the path in ~/.cortex/config-root."
        )
    return (
        f"Your Nucleus config folder {where} exists but has no memory in it yet. "
        "Run /start-nucleus to set it up, or check that the pointer targets the right folder."
    )


def status_block(state: RootState, result: ConfigRootResult | None = None) -> str:
    """Terse /status-style block; empty for OK. First section is always BROKEN."""
    if state is RootState.OK:
        return ""
    sections = ("Shared config", "Plugin setup", "Memory health", "Scheduled loop")
    lines = ["BROKEN", f"  {user_message(state, result)}", ""]
    lines.append("Connectors: detected from this session (no filesystem needed)")
    lines.extend(f"{name}: blocked: config root not attached" for name in sections)
    return "\n".join(lines)


def describe(result: ConfigRootResult, environ: Mapping[str, str]) -> dict[str, str]:
    state = classify(result, environ)
    return {
        "state": state.value,
        "path": str(result.path),
        "source": result.source,
        "message": user_message(state, result),
    }
