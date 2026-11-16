"""Scheduled-run receipts (schema 1.1.0).

A receipt is the metadata-only record that an unattended run happened and who
it ran for. Schema 1.1.0 adds the accountable actor and settles the outcome
vocabulary. Writers go through this module so a receipt cannot be written
without an actor field or with an outcome readers do not understand.

Receipts never carry connector payloads, message or transcript text,
credentials, or memory content.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_VERSION = "1.1.0"
OUTCOMES = ("succeeded", "partial", "skipped", "failed")
# Older writers used these spellings; normalize rather than reject.
OUTCOME_ALIASES = {"success": "succeeded", "ok": "succeeded", "failure": "failed"}
UNRESOLVED = "unresolved"

_ACTOR_LINE = re.compile(r"^\s*-\s*\*\*Actor ID:\*\*\s*(.+?)\s*$", re.MULTILINE)
_ACTOR_OK = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_NAME_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def normalize_outcome(value: str) -> str:
    v = (value or "").strip().lower()
    v = OUTCOME_ALIASES.get(v, v)
    if v not in OUTCOMES:
        raise ValueError(f"outcome must be one of {', '.join(OUTCOMES)}; got {value!r}")
    return v


def valid_actor(value: str | None) -> bool:
    return bool(value) and bool(_ACTOR_OK.match(value.strip()))


def resolve_actor(config_root: Path, explicit: str | None = None) -> tuple[str, str]:
    """Return (actor_id, source). Source is `identity`, `registration`, or `unresolved`.

    The identity file wins when it is readable. `explicit` is the actor the
    schedule was registered for, carried in the registered prompt; it is the
    fallback when the identity file cannot be read (for example when the config
    root is unreachable). An actor is never invented.
    """
    identity = config_root / "memory" / "me" / "identity.md"
    try:
        m = _ACTOR_LINE.search(identity.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        m = None
    if m and valid_actor(m.group(1)):
        return m.group(1).strip(), "identity"
    if valid_actor(explicit):
        return explicit.strip(), "registration"  # type: ignore[union-attr]
    return UNRESOLVED, "unresolved"


def build(
    *,
    schedule: str,
    run_id: str,
    started_at: str,
    ended_at: str,
    outcome: str,
    actor_id: str,
    actor_source: str,
    host_id: str | None = None,
    extra: dict | None = None,
    error_codes: list[str] | None = None,
) -> dict:
    for label, value in (("schedule", schedule), ("run_id", run_id)):
        if not _NAME_OK.match(value or ""):
            raise ValueError(f"{label} must be a plain name (letters, digits, . _ -); got {value!r}")
    codes = [c for c in (error_codes or []) if c]
    if actor_id == UNRESOLVED and "actor_unresolved" not in codes:
        codes.append("actor_unresolved")
    receipt: dict = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "schedule": schedule,
        "actor_id": actor_id,
        "actor_source": actor_source,
        "started_at": started_at,
        "ended_at": ended_at,
        "outcome": normalize_outcome(outcome),
        "error_codes": codes,
    }
    if host_id:
        receipt["host_id"] = host_id
    reserved = set(receipt) | {"status", "error_code"}
    for key, value in (extra or {}).items():
        if key in reserved:
            raise ValueError(f"extra field {key!r} is reserved")
        receipt[key] = value
    return receipt


def receipt_path(config_root: Path, schedule: str, run_id: str) -> Path:
    return config_root / "plugins" / "ops" / "schedule-runs" / schedule / f"{run_id}.json"


def render(receipt: dict) -> str:
    return json.dumps(receipt, indent=2, sort_keys=False) + "\n"
