"""Node path validation — prevents traversal outside the memory root.

Implements core-contract.md §3 (node-to-file mapping) and §11 (mutating
workflows must validate targets before writing).
"""
from __future__ import annotations

import os
from pathlib import Path

# Private scopes that a cloud-first config-root symlinks into <root>/.private/ (core-contract §11B).
PRIVATE_SCOPES = ("me", "staged")


class PathTraversalError(Exception):
    """Raised when a node reference would resolve outside the memory root."""


def resolve_node_path(memory_root: Path, relative: str) -> Path:
    """Resolve `relative` against `memory_root`, refusing any escape.

    Rejects absolute paths, `..` segments that climb above the root, and
    symlink-based escapes (resolution is done with `Path.resolve()`, which
    follows symlinks, before the containment check).
    """
    raw_root = Path(os.path.abspath(memory_root))
    memory_root = Path(memory_root).resolve()
    if Path(relative).is_absolute():
        raise PathTraversalError(
            f"node path must be relative to the memory root, got absolute path {relative!r}"
        )

    candidate = (memory_root / relative).resolve()
    try:
        candidate.relative_to(memory_root)
    except ValueError as e:
        if _inside_private_scope(raw_root, relative, candidate):
            return candidate
        raise PathTraversalError(
            f"node path {relative!r} resolves outside memory root {memory_root}"
        ) from e
    return candidate


def _inside_private_scope(raw_root: Path, relative: str, candidate: Path) -> bool:
    """True when `relative` goes through memory/me or memory/staged and lands inside
    the matching directory of the sibling .private/ checkout (and nowhere else)."""
    parts = Path(relative).parts
    if not parts or parts[0] not in PRIVATE_SCOPES:
        return False
    scope = (raw_root.parent / ".private" / parts[0]).resolve()
    try:
        candidate.relative_to(scope)
    except ValueError:
        return False
    return (raw_root / parts[0]).is_symlink()


def resolve_two_node_paths(memory_root: Path, src_relative: str, dest_relative: str) -> tuple[Path, Path]:
    """Resolve two node-relative paths against the same memory root.

    Convenience for move/merge operations that must validate both endpoints
    before touching either file.
    """
    return (
        resolve_node_path(memory_root, src_relative),
        resolve_node_path(memory_root, dest_relative),
    )


def node_id_to_relative_path(node_id: str) -> str:
    """Map a node ID to its file path, relative to the memory root.

    `person/sarah-chen` -> `person/sarah-chen.md`
    `person:sarah-chen` -> `person/sarah-chen.md` (legacy colon syntax, core-contract.md §3)
    `hiring` -> `hiring.md`
    """
    node_id = node_id.strip()
    if not node_id:
        raise ValueError("node_id must not be empty")
    normalized = node_id.replace(":", "/", 1)
    return f"{normalized}.md"
