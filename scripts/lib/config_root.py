"""Deterministic config-root resolution for Cortex.

Implements the precedence chain defined in references/core-contract.md §1:

    1. explicit override (project config / workflow argument)
    2. CORTEX_CONFIG_ROOT environment variable
    3. ~/.cortex/config-root pointer file (new, vendor-neutral)
    4. ~/Documents/.claude-plugin-config-root pointer file (legacy)
    5. ~/cortex-root, only if it was materialized by `cortex_cli.py bootstrap`
       (contains .cortex-repos.json) — the cloud-first default
    6. ~/Documents/Claude (backward-compatible default)

`home` is always passed in explicitly rather than read from the real
environment, so this module never touches a real user's filesystem unless
the caller deliberately passes their real home directory. Tests must pass a
fixture/temp directory as `home`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Mapping, Optional, Sequence

_WINDOWS_ABS_RE = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True)
class ConfigRootResult:
    """A successfully resolved config-root."""

    path: Path
    source: str  # which precedence tier matched, e.g. "explicit override"


@dataclass
class ConfigRootError(Exception):
    """Raised when no precedence tier resolves to a safe, absolute path."""

    message: str
    attempts: list[str] = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - trivial
        lines = [self.message]
        lines.extend(f"  - {a}" for a in self.attempts)
        return "\n".join(lines)


def _is_windows_style_absolute(raw: str) -> bool:
    return bool(_WINDOWS_ABS_RE.match(raw))


def _expand(raw: str, home: Path) -> Path:
    """Expand a leading ~ against the *injected* home, not the real $HOME."""
    raw = raw.strip()
    if raw == "~":
        return home
    if raw.startswith("~/") or raw.startswith("~\\"):
        return home / raw[2:]
    return Path(raw)


def _validate(raw: str, home: Path, tier: str, attempts: list[str]) -> Path:
    """Expand + validate a candidate path. Raises ConfigRootError on failure.

    A malformed value at a given precedence tier is a hard error — it does
    NOT fall through to the next tier. See core-contract.md §1.
    """
    if raw is None or not raw.strip():
        raise ConfigRootError(
            f"config-root resolution failed: {tier} was present but empty",
            attempts,
        )

    stripped = raw.strip()

    if _is_windows_style_absolute(stripped):
        # Accept syntactically (per contract §1 "Windows-style paths where
        # supported"); we don't attempt POSIX/NT interop resolution here,
        # only shape validation.
        return Path(stripped)

    expanded = _expand(stripped, home)

    if not expanded.is_absolute():
        raise ConfigRootError(
            f"config-root resolution failed: {tier} resolved to a non-absolute "
            f"path ({expanded!r})",
            attempts,
        )

    # Refuse filesystem roots and the bare home directory as destructive
    # mutation targets.
    root_markers = {Path(expanded.anchor), home}
    if expanded in root_markers:
        raise ConfigRootError(
            f"config-root resolution failed: {tier} resolved to an unsafe "
            f"target ({expanded!r}) — a filesystem root or bare home directory "
            "is never a valid config-root",
            attempts,
        )

    return expanded


def resolve_config_root(
    *,
    home: Path,
    environ: Optional[Mapping[str, str]] = None,
    explicit: Optional[str] = None,
    project_config: Optional[Mapping[str, object]] = None,
) -> ConfigRootResult:
    """Resolve the Cortex config-root using the documented precedence chain.

    Args:
        home: the home directory to resolve `~` and legacy/new pointer
            files against. Callers MUST pass a real home directory
            explicitly to use this against a real system; tests MUST pass
            a fixture/temp directory.
        environ: environment mapping to check for CORTEX_CONFIG_ROOT.
            Defaults to an empty mapping (never reads the real process
            environment implicitly).
        explicit: an explicit override path, highest precedence.
        project_config: a parsed `.cortex.json`-shaped mapping; if it has a
            `config_root` key, it is used as the explicit override when
            `explicit` itself is not given.

    Returns:
        ConfigRootResult with the resolved absolute path and which
        precedence tier produced it.

    Raises:
        ConfigRootError: if a present-but-malformed higher-precedence
            source is found, or if nothing resolves at all.
    """
    environ = environ or {}
    attempts: list[str] = []

    override = explicit
    if override is None and project_config is not None:
        pc_value = project_config.get("config_root")
        if pc_value is not None:
            override = str(pc_value)

    if override is not None:
        attempts.append(f"explicit override: {override!r}")
        return ConfigRootResult(
            path=_validate(override, home, "explicit override", attempts),
            source="explicit override",
        )
    attempts.append("explicit override: not provided")

    env_value = environ.get("CORTEX_CONFIG_ROOT")
    if env_value is not None:
        attempts.append(f"CORTEX_CONFIG_ROOT env var: {env_value!r}")
        return ConfigRootResult(
            path=_validate(env_value, home, "CORTEX_CONFIG_ROOT env var", attempts),
            source="CORTEX_CONFIG_ROOT env var",
        )
    attempts.append("CORTEX_CONFIG_ROOT env var: not set")

    new_pointer = home / ".cortex" / "config-root"
    if new_pointer.exists():
        try:
            content = new_pointer.read_text(encoding="utf-8")
        except OSError as e:
            raise ConfigRootError(
                f"config-root resolution failed: could not read {new_pointer} ({e})",
                attempts,
            ) from e
        attempts.append(f"~/.cortex/config-root pointer: {content.strip()!r}")
        return ConfigRootResult(
            path=_validate(content, home, "~/.cortex/config-root pointer", attempts),
            source="~/.cortex/config-root pointer",
        )
    attempts.append("~/.cortex/config-root pointer: file not found")

    legacy_pointer = home / "Documents" / ".claude-plugin-config-root"
    if legacy_pointer.exists():
        try:
            content = legacy_pointer.read_text(encoding="utf-8")
        except OSError as e:
            raise ConfigRootError(
                f"config-root resolution failed: could not read {legacy_pointer} ({e})",
                attempts,
            ) from e
        attempts.append(
            f"~/Documents/.claude-plugin-config-root pointer (legacy): {content.strip()!r}"
        )
        return ConfigRootResult(
            path=_validate(
                content, home, "~/Documents/.claude-plugin-config-root pointer (legacy)", attempts
            ),
            source="~/Documents/.claude-plugin-config-root pointer (legacy)",
        )
    attempts.append("~/Documents/.claude-plugin-config-root pointer (legacy): file not found")

    cloud_root = home / "cortex-root"
    if (cloud_root / ".cortex-repos.json").is_file():
        attempts.append(f"~/cortex-root (bootstrapped): {str(cloud_root)!r}")
        return ConfigRootResult(path=cloud_root, source="~/cortex-root (bootstrapped)")
    attempts.append("~/cortex-root (bootstrapped): not found")

    default = home / "Documents" / "Claude"
    attempts.append(f"default: {default!r}")
    return ConfigRootResult(path=default, source="default (~/Documents/Claude)")
