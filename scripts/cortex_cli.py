#!/usr/bin/env python3
"""Command-line entrypoint that host adapters (Claude commands, future Codex
skills) shell out to for any memory mutation.

Each subcommand performs one complete lock -> read -> modify -> atomic-write
-> release cycle in a single process invocation, so a workflow spec never has
to coordinate acquire/release across separate calls (which would need to
share a lock token across process boundaries). This is the concrete
implementation of the "must use shared deterministic locking and safe-write
utilities" requirement in references/core-contract.md §11.

Usage:
    python3 scripts/cortex_cli.py append-section \\
        --memory-root <path> <node-relative-path> "<heading>" "<line>"

    python3 scripts/cortex_cli.py replace-section \\
        --memory-root <path> <node-relative-path> "<heading>" "<new body>"

    echo "<content>" | python3 scripts/cortex_cli.py replace-section \\
        --memory-root <path> <node-relative-path> "<heading>" -

All paths are validated to stay inside --memory-root (see node_paths.py);
attempts to escape it fail loudly rather than silently writing elsewhere.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.lib.atomic_write import atomic_move, atomic_write, delete_node_file, safe_append  # noqa: E402
from scripts.lib.hot_cache_generator import generate_and_write_hot_cache  # noqa: E402
from scripts.lib.index_generator import generate_and_write_index  # noqa: E402
from scripts.lib.cap_check import check_caps  # noqa: E402
from scripts.lib.locking import (  # noqa: E402
    LockTimeoutError,
    MemoryLock,
    acquire_lock_for_external_section,
    release_lock_for_external_section,
)
from scripts.lib.node_paths import (  # noqa: E402
    PathTraversalError,
    resolve_node_path,
    resolve_two_node_paths,
)
from scripts.lib import repo_sync  # noqa: E402
from scripts.lib.sections import append_to_section, prepend_to_section, replace_section  # noqa: E402


def _read_payload(raw: str) -> str:
    if raw == "-":
        return sys.stdin.read()
    return raw


def _mutate(
    memory_root: Path,
    node_relative_path: str,
    heading: str,
    payload_raw: str,
    op,
) -> int:
    try:
        target = resolve_node_path(memory_root, node_relative_path)
    except PathTraversalError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    payload = _read_payload(payload_raw)
    lock = MemoryLock(memory_root / ".lock")
    with lock:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        updated = op(current, heading, payload)
        atomic_write(target, updated)

    print(f"OK: wrote {target}")
    return 0


def cmd_append_section(args: argparse.Namespace) -> int:
    return _mutate(
        Path(args.memory_root), args.node_path, args.heading, args.payload, append_to_section
    )


def cmd_append_line(args: argparse.Namespace) -> int:
    """Append a raw line to a flat (non-sectioned) file, e.g. a skip-log or queue marker."""
    memory_root = Path(args.memory_root)
    try:
        target = resolve_node_path(memory_root, args.node_path)
    except PathTraversalError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    line = _read_payload(args.payload)
    if not line.endswith("\n"):
        line += "\n"

    with MemoryLock(memory_root / ".lock"):
        safe_append(target, line)

    print(f"OK: appended to {target}")
    return 0


def cmd_replace_section(args: argparse.Namespace) -> int:
    return _mutate(
        Path(args.memory_root), args.node_path, args.heading, args.payload, replace_section
    )


def cmd_prepend_section(args: argparse.Namespace) -> int:
    return _mutate(
        Path(args.memory_root), args.node_path, args.heading, args.payload, prepend_to_section
    )


def cmd_move_node(args: argparse.Namespace) -> int:
    memory_root = Path(args.memory_root)
    try:
        src, dest = resolve_two_node_paths(memory_root, args.src_node_path, args.dest_node_path)
    except PathTraversalError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    with MemoryLock(memory_root / ".lock"):
        if not src.exists():
            print(f"ERROR: source node does not exist: {src}", file=sys.stderr)
            return 1
        atomic_move(src, dest)

    print(f"OK: moved {src} -> {dest}")
    return 0


def cmd_delete_node(args: argparse.Namespace) -> int:
    memory_root = Path(args.memory_root)
    try:
        target = resolve_node_path(memory_root, args.node_path)
    except PathTraversalError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    with MemoryLock(memory_root / ".lock"):
        delete_node_file(target)

    print(f"OK: deleted {target}")
    return 0


def cmd_lock_acquire(args: argparse.Namespace) -> int:
    """Acquire the memory lock for a multi-step external critical section
    (e.g. a git add/commit sequence) that isn't a single cortex_cli call.
    Must be paired with `lock-release` on every exit path, including failure."""
    lock_path = Path(args.memory_root) / ".lock"
    try:
        acquire_lock_for_external_section(lock_path, timeout=args.timeout, stale_after=args.stale_after)
    except LockTimeoutError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"OK: acquired {lock_path}")
    return 0


def cmd_lock_release(args: argparse.Namespace) -> int:
    lock_path = Path(args.memory_root) / ".lock"
    released = release_lock_for_external_section(lock_path)
    print(f"OK: {'released' if released else 'nothing to release for'} {lock_path}")
    return 0


def cmd_write_file(args: argparse.Namespace) -> int:
    """Overwrite a flat (non-sectioned) file wholesale, e.g. rewriting a queue
    file after removing handled entries. For sectioned node files, prefer
    replace-section/append-section instead — this bypasses section awareness
    entirely."""
    memory_root = Path(args.memory_root)
    try:
        target = resolve_node_path(memory_root, args.node_path)
    except PathTraversalError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    content = _read_payload(args.payload)

    with MemoryLock(memory_root / ".lock"):
        atomic_write(target, content)

    print(f"OK: wrote {target}")
    return 0


def cmd_reindex(args: argparse.Namespace) -> int:
    path = generate_and_write_index(Path(args.memory_root))
    print(f"OK: regenerated {path}")
    return 0


def cmd_check_caps(args: argparse.Namespace) -> int:
    violations = check_caps(Path(args.memory_root))
    if not violations:
        print("OK: no cap violations")
        return 0
    for v in violations:
        print(v.render())
    if any(v.severity == "fail" for v in violations):
        return 1
    return 0


def cmd_refresh_hot(args: argparse.Namespace) -> int:
    path = generate_and_write_hot_cache(Path(args.memory_root), trigger=args.trigger)
    print(f"OK: regenerated {path}")
    return 0


def _resolve_sync_root(raw: str | None) -> Path:
    import os

    return Path(raw or os.environ.get("CORTEX_CONFIG_ROOT") or Path.home() / "cortex-root").expanduser()


def _default_search_dirs() -> list[Path]:
    home = Path.home()
    dirs = [Path.cwd(), Path.cwd().parent, home, Path("/home/user"), Path("/workspace")]
    seen, out = set(), []
    for d in dirs:
        if d not in seen and d.is_dir():
            seen.add(d)
            out.append(d)
    return out


def cmd_bootstrap(args: argparse.Namespace) -> int:
    import json

    root = _resolve_sync_root(args.root)
    try:
        info = repo_sync.bootstrap(
            root,
            args.org_repo,
            args.private_repo,
            Path(args.adopt_org).expanduser() if args.adopt_org else None,
            Path(args.adopt_private).expanduser() if args.adopt_private else None,
            _default_search_dirs(),
        )
    except repo_sync.SyncError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if not args.skip_derived:
        memory_root = Path(info["memory_root"])
        generate_and_write_index(memory_root)
        generate_and_write_hot_cache(memory_root, trigger="bootstrap")
    if args.print_env:
        print(f"export CORTEX_CONFIG_ROOT={root}")
    else:
        print(json.dumps(info, indent=2))
    return 0 if info["ok"] else 1


def cmd_sync(args: argparse.Namespace) -> int:
    root = _resolve_sync_root(args.root)
    report = repo_sync.sync(root, host=args.host)
    for r in report.results:
        print(f"{'OK' if r.ok else 'FAIL'}: {r.name} {r.action} {r.detail}".rstrip())
    return 0 if report.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cortex_cli")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func in (
        ("append-section", cmd_append_section),
        ("replace-section", cmd_replace_section),
        ("prepend-section", cmd_prepend_section),
    ):
        p = sub.add_parser(name)
        p.add_argument("--memory-root", required=True, help="Resolved <config-root>/memory path")
        p.add_argument("node_path", help="Node file path, relative to --memory-root")
        p.add_argument("heading", help='Markdown heading, e.g. "## Changelog"')
        p.add_argument("payload", help="Text to write, or '-' to read from stdin")
        p.set_defaults(func=func)

    lock_acquire_p = sub.add_parser("lock-acquire")
    lock_acquire_p.add_argument("--memory-root", required=True)
    lock_acquire_p.add_argument("--timeout", type=float, default=10.0)
    lock_acquire_p.add_argument("--stale-after", type=float, default=120.0)
    lock_acquire_p.set_defaults(func=cmd_lock_acquire)

    lock_release_p = sub.add_parser("lock-release")
    lock_release_p.add_argument("--memory-root", required=True)
    lock_release_p.set_defaults(func=cmd_lock_release)

    write_file_p = sub.add_parser("write-file")
    write_file_p.add_argument("--memory-root", required=True)
    write_file_p.add_argument("node_path")
    write_file_p.add_argument("payload", help="Full file content, or '-' to read from stdin")
    write_file_p.set_defaults(func=cmd_write_file)

    append_line_p = sub.add_parser("append-line")
    append_line_p.add_argument("--memory-root", required=True)
    append_line_p.add_argument("node_path")
    append_line_p.add_argument("payload", help="Line to append, or '-' to read from stdin")
    append_line_p.set_defaults(func=cmd_append_line)

    move_p = sub.add_parser("move-node")
    move_p.add_argument("--memory-root", required=True)
    move_p.add_argument("src_node_path")
    move_p.add_argument("dest_node_path")
    move_p.set_defaults(func=cmd_move_node)

    delete_p = sub.add_parser("delete-node")
    delete_p.add_argument("--memory-root", required=True)
    delete_p.add_argument("node_path")
    delete_p.set_defaults(func=cmd_delete_node)

    reindex_p = sub.add_parser("reindex")
    reindex_p.add_argument("--memory-root", required=True)
    reindex_p.set_defaults(func=cmd_reindex)

    check_caps_p = sub.add_parser("check-caps")
    check_caps_p.add_argument("--memory-root", required=True)
    check_caps_p.set_defaults(func=cmd_check_caps)

    hot_p = sub.add_parser("refresh-hot")
    hot_p.add_argument("--memory-root", required=True)
    hot_p.add_argument("--trigger", default="manual")
    hot_p.set_defaults(func=cmd_refresh_hot)

    boot_p = sub.add_parser("bootstrap", help="Clone/pull the org + private repos into a config-root")
    boot_p.add_argument("--root", help="Config-root to materialize (default $CORTEX_CONFIG_ROOT or ~/cortex-root)")
    boot_p.add_argument("--org-repo")
    boot_p.add_argument("--private-repo")
    boot_p.add_argument("--adopt-org", help="Existing checkout of the org repo to reuse (cloud sources)")
    boot_p.add_argument("--adopt-private", help="Existing checkout of the private repo to reuse")
    boot_p.add_argument("--print-env", action="store_true", help="Print an export line instead of JSON")
    boot_p.add_argument("--skip-derived", action="store_true", help="Skip index/hot.md regeneration")
    boot_p.set_defaults(func=cmd_bootstrap)

    sync_p = sub.add_parser("sync", help="Commit stragglers, pull, and push both repos; log every run")
    sync_p.add_argument("--root")
    sync_p.add_argument("--host")
    sync_p.set_defaults(func=cmd_sync)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
