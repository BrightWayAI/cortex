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


def cmd_root_status(args: argparse.Namespace) -> int:
    """Read-only reachability check. Exit 0 only when the root is OK."""
    import json
    import os

    from scripts.lib.config_root import ConfigRootError, resolve_config_root
    from scripts.lib.root_reachability import RootState, classify, describe, status_block

    try:
        result = resolve_config_root(home=Path.home(), environ=os.environ, explicit=args.root)
    except ConfigRootError as exc:
        print(f"BROKEN\n  Cortex config-root resolution failed: {exc.message}")
        return 1
    state = classify(result, os.environ)
    if args.format == "json":
        print(json.dumps(describe(result, os.environ), indent=2))
    elif state is RootState.OK:
        print(f"OK {result.path} ({result.source})")
    else:
        print(status_block(state, result))
    return 0 if state is RootState.OK else 1


def cmd_migrate_plugin_configs(args: argparse.Namespace) -> int:
    """Archive legacy files in <config-root>/plugins/ and create ops/schedules.md.

    Dry-run unless --apply. Prints file names only, never contents.
    """
    import json
    from datetime import date

    from scripts.lib import plugin_config_migration as mig

    root = Path(args.config_root).expanduser()
    plugins_dir = root / "plugins"
    memory_root = root / "memory"
    marker = memory_root / mig.MARKER_NAME
    template = Path(args.schedules_template).expanduser() if args.schedules_template else None

    if not plugins_dir.is_dir():
        print(f"ERROR: no plugins directory at {plugins_dir}", file=sys.stderr)
        return 1
    if marker.exists() and not args.rerun:
        print(json.dumps({"status": "already-done", "marker": str(marker), "actions": []}, indent=2))
        return 0

    today = date.today()
    actions = mig.plan(plugins_dir, today, template)
    report = {
        "status": "applied" if args.apply else "dry-run",
        "plugins_dir": str(plugins_dir),
        "actions": [a.as_dict() for a in actions],
    }
    if args.apply:
        try:
            with MemoryLock(memory_root / ".lock"):
                mig.apply(plugins_dir, actions, template)
                atomic_write(marker, mig.marker_text(today, actions))
        except (OSError, ValueError) as e:
            print(f"ERROR: {e}; marker not written, safe to retry", file=sys.stderr)
            return 1
        report["marker"] = str(marker)
    print(json.dumps(report, indent=2))
    return 0


def cmd_check_citations(args: argparse.Namespace) -> int:
    """Deterministic first-pass check of the citations in a /listen commit draft.

    Read-only. Prints proposal numbers, node names, file names and statuses;
    never proposal or source text. See references/verification.md.
    """
    import json

    from scripts.lib import citation_check as cc

    root = Path(args.config_root).expanduser()
    drafts = root / "memory" / "staged" / "commit-drafts"
    draft = Path(args.draft).expanduser() if "/" in args.draft or args.draft.endswith(".md") else drafts / f"{args.draft}.md"
    if not draft.is_file():
        print(f"ERROR: no commit draft at {draft}", file=sys.stderr)
        return 1
    results = cc.check_draft(draft.read_text(encoding="utf-8", errors="replace"), root)
    print(json.dumps({
        "draft": draft.name,
        "summary": cc.summarize(results),
        "proposals": [r.as_dict() for r in results],
    }, indent=2))
    return 0


def cmd_record_verification(args: argparse.Namespace) -> int:
    """Write verification results under each proposal in a /listen commit draft.

    Runs the deterministic citation check itself, merges the `verifier` agent's
    JSON if given, and rewrites the draft atomically. Touches only the draft.
    Prints numbers and statuses, never proposal or source text.
    """
    import json
    from datetime import datetime

    from scripts.lib import citation_check as cc
    from scripts.lib import verification_record as vr

    root = Path(args.config_root).expanduser()
    drafts = (root / "memory" / "staged" / "commit-drafts").resolve()
    draft = (drafts / f"{args.draft}.md").resolve()
    if draft.parent != drafts or not draft.is_file():
        print(f"ERROR: no commit draft named {args.draft}.md in {drafts}", file=sys.stderr)
        return 1

    verifier = None
    verifier_state = "not-provided"
    if args.verifier_results:
        raw = sys.stdin.read() if args.verifier_results == "-" else Path(args.verifier_results).expanduser().read_text(encoding="utf-8")
        try:
            verifier = json.loads(raw)
            verifier_state = "read" if isinstance(verifier, dict) and isinstance(verifier.get("results"), list) else "unusable"
        except json.JSONDecodeError:
            verifier_state = "unusable"

    text = draft.read_text(encoding="utf-8", errors="replace")
    records = vr.merge(cc.check_draft(text, root), verifier)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    atomic_write(draft, vr.apply_to_draft(text, records, stamp))
    print(json.dumps({
        "draft": draft.name,
        "verifier_results": verifier_state,
        "summary": vr.summarize(records),
        "proposals": [r.as_dict() for r in records],
    }, indent=2))
    return 0


def cmd_triage_draft(args: argparse.Namespace) -> int:
    """Read-only: sort a commit draft's proposals into /morning review groups."""
    import json

    from scripts.lib import draft_triage as dt

    root = Path(args.config_root).expanduser()
    drafts = (root / "memory" / "staged" / "commit-drafts").resolve()
    draft = (drafts / f"{args.draft}.md").resolve()
    if draft.parent != drafts or not draft.is_file():
        print(f"ERROR: no commit draft named {args.draft}.md in {drafts}", file=sys.stderr)
        return 1
    items = dt.triage_draft(draft.read_text(encoding="utf-8", errors="replace"))
    print(json.dumps({
        "draft": draft.name,
        "summary": dt.summarize(items),
        "proposals": [t.as_dict() for t in items],
    }, indent=2))
    return 0


def cmd_write_receipt(args: argparse.Namespace) -> int:
    """Write one scheduled-run receipt (schema 1.1.0) with the accountable actor.

    Resolves the actor from <config-root>/memory/me/identity.md, falling back to
    --actor-id (the actor the schedule was registered for). If the receipt file
    cannot be written, the receipt is printed to stdout and the exit code is 2,
    so the scheduler's own log still captures it.
    """
    import json

    from scripts.lib import receipts as rc

    root = Path(args.config_root).expanduser()
    try:
        extra = json.loads(args.extra) if args.extra else {}
        if not isinstance(extra, dict):
            raise ValueError("--extra must be a JSON object")
        actor_id, actor_source = rc.resolve_actor(root, args.actor_id)
        receipt = rc.build(
            schedule=args.schedule, run_id=args.run_id, started_at=args.started_at,
            ended_at=args.ended_at, outcome=args.outcome, actor_id=actor_id,
            actor_source=actor_source, host_id=args.host_id, extra=extra,
            error_codes=args.error_code or [],
        )
    except (ValueError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    text = rc.render(receipt)
    target = rc.receipt_path(root, args.schedule, args.run_id)
    try:
        if not root.is_dir():
            raise OSError(f"config root not reachable: {root}")
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(target, text)
    except OSError as e:
        print(text, end="")
        print(f"ERROR: receipt not written to disk ({e}); emitted to stdout instead", file=sys.stderr)
        return 2
    print(text, end="")
    return 0


def cmd_open_nudges(args: argparse.Namespace) -> int:
    """Read-only: list staged nudges the user has not acted on, snoozed, or dismissed."""
    import json

    from scripts.lib import nudges_review as nr

    root = Path(args.config_root).expanduser()
    print(json.dumps(nr.open_nudges(root / "memory" / "staged" / "nudges"), indent=2))
    return 0


def cmd_record_decision(args: argparse.Namespace) -> int:
    """Create a decision record under memory/decision/ and mark any decision it supersedes.

    One locked operation. Prints the new id and the pointer line to add to each
    affected node; never prints the decision text.
    """
    import json
    from datetime import date

    from scripts.lib import decision_records as dr

    memory_root = Path(args.memory_root).expanduser()
    try:
        decided = date.fromisoformat(args.date) if args.date else date.today()
        decision = dr.Decision(
            title=args.title, what=_read_payload(args.what), why=args.why,
            decided=decided, decided_by=args.decided_by, inputs=args.input or [], affects=args.affects or [],
            supersedes=args.supersedes, revisit_when=args.revisit_when or "n/a", recorded_by=args.recorded_by,
        )
        if not memory_root.is_dir():
            raise dr.DecisionError(f"memory root not found: {memory_root}")
        with MemoryLock(memory_root / ".lock"):
            p = dr.plan(memory_root, decision)
            target = memory_root / p["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(target, p["content"])
            if p["superseded_id"]:
                atomic_write(memory_root / dr.DECISION_DIR / f"{p['superseded_id']}.md", p["superseded_content"])
    except (dr.DecisionError, ValueError, LockTimeoutError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(json.dumps({
        "id": p["id"], "path": p["path"], "superseded": p["superseded_id"],
        "pointer_line": p["pointer_line"], "missing_affects": p["missing_affects"],
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_memory_diff(args: argparse.Namespace) -> int:
    """Read-only: is memory safe to diff right now, and what changed since the previous commit."""
    import json
    from datetime import datetime

    from scripts.lib import memory_diff as md

    root = Path(args.config_root).expanduser()
    print(json.dumps(md.summarize(root / "memory", datetime.now().astimezone()), indent=2))
    return 0


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

    root_p = sub.add_parser("root-status", help="Read-only: is the resolved config root reachable? Exit 0 if OK")
    root_p.add_argument("--root", help="Explicit config-root override")
    root_p.add_argument("--format", choices=("block", "json"), default="block")
    root_p.set_defaults(func=cmd_root_status)

    mig_p = sub.add_parser(
        "migrate-plugin-configs",
        help="Archive legacy files in <config-root>/plugins/ and create ops/schedules.md (dry-run unless --apply)",
    )
    mig_p.add_argument("--config-root", required=True, help="Resolved config root")
    mig_p.add_argument("--schedules-template", help="Path to ops references/schedules.template.md")
    mig_p.add_argument("--apply", action="store_true", help="Perform the moves; default is a dry run")
    mig_p.add_argument("--rerun", action="store_true", help="Ignore an existing done-marker")
    mig_p.set_defaults(func=cmd_migrate_plugin_configs)

    cite_p = sub.add_parser(
        "check-citations",
        help="Read-only: check that each proposal in a /listen commit draft cites a source that exists",
    )
    cite_p.add_argument("--config-root", required=True, help="Resolved config root")
    cite_p.add_argument("--draft", required=True, help="Draft date (YYYY-MM-DD) or path to the draft file")
    cite_p.set_defaults(func=cmd_check_citations)

    rec_p = sub.add_parser(
        "record-verification",
        help="Write citation-check and verifier results under each proposal in a /listen commit draft",
    )
    rec_p.add_argument("--config-root", required=True, help="Resolved config root")
    rec_p.add_argument("--draft", required=True, help="Draft date (YYYY-MM-DD)")
    rec_p.add_argument("--verifier-results", help="Path to the verifier agent's JSON, or - for stdin; omit if it did not run")
    rec_p.set_defaults(func=cmd_record_verification)

    tri_p = sub.add_parser(
        "triage-draft",
        help="Read-only: sort a /listen commit draft's proposals into batch / review / brief groups for /morning",
    )
    tri_p.add_argument("--config-root", required=True, help="Resolved config root")
    tri_p.add_argument("--draft", required=True, help="Draft date (YYYY-MM-DD)")
    tri_p.set_defaults(func=cmd_triage_draft)

    rcp_p = sub.add_parser("write-receipt", help="Write a scheduled-run receipt (schema 1.1.0) that records the accountable actor")
    rcp_p.add_argument("--config-root", required=True, help="Resolved config root")
    rcp_p.add_argument("--schedule", required=True, help="Schedule name, e.g. nightly-listen")
    rcp_p.add_argument("--run-id", required=True, help="Host run id or a UUID")
    rcp_p.add_argument("--started-at", required=True, help="ISO-8601")
    rcp_p.add_argument("--ended-at", required=True, help="ISO-8601")
    rcp_p.add_argument("--outcome", required=True, help="succeeded | partial | skipped | failed")
    rcp_p.add_argument("--actor-id", help="Actor the schedule was registered for; used only if the identity file cannot be read")
    rcp_p.add_argument("--host-id")
    rcp_p.add_argument("--error-code", action="append", help="Repeatable sanitized error code")
    rcp_p.add_argument("--extra", help="JSON object of extra metadata-only fields (counts, state_source, source_coverage)")
    rcp_p.set_defaults(func=cmd_write_receipt)

    nud_p = sub.add_parser("open-nudges", help="Read-only: staged nudges still awaiting the user, for /morning")
    nud_p.add_argument("--config-root", required=True, help="Resolved config root")
    nud_p.set_defaults(func=cmd_open_nudges)

    dec_p = sub.add_parser("record-decision", help="Create a decision record under memory/decision/ and mark the one it supersedes")
    dec_p.add_argument("--memory-root", required=True)
    dec_p.add_argument("--title", required=True, help="One-line statement of the decision")
    dec_p.add_argument("--what", required=True, help="What was decided, or - to read from stdin")
    dec_p.add_argument("--why", required=True, help="The reasoning at the time")
    dec_p.add_argument("--decided-by", required=True, help="Actor ID of the person who decided")
    dec_p.add_argument("--date", help="YYYY-MM-DD; default today")
    dec_p.add_argument("--input", action="append", help="Repeatable: a fact or source the decision rested on")
    dec_p.add_argument("--affects", action="append", help="Repeatable: node id affected, e.g. client/acme")
    dec_p.add_argument("--supersedes", help="Id of the decision this replaces, e.g. decision/2026-05-15-crm-choice")
    dec_p.add_argument("--revisit-when", help="What would reopen this decision; default n/a")
    dec_p.add_argument("--recorded-by", default="/remember", help="Command that recorded it")
    dec_p.set_defaults(func=cmd_record_decision)

    mdiff_p = sub.add_parser("memory-diff", help="Read-only: summary of memory changes since the previous commit, for /morning")
    mdiff_p.add_argument("--config-root", required=True, help="Resolved config root")
    mdiff_p.set_defaults(func=cmd_memory_diff)

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
