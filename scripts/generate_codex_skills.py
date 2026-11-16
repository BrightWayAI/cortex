#!/usr/bin/env python3
"""Generate the shared Agent Skill wrappers used by Cortex hosts.

The workflow itself remains canonical in commands/<name>.md.  These wrappers
only bind that workflow to the host-neutral capability contract and enforce
the deterministic mutation boundary.  They are emitted both to skills/ (the
portable plugin path, also consumed by Claude/Cowork) and .agents/skills/
(Codex project discovery).
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class SkillSpec:
    description: str
    status: str
    note: str


WORK_SUPPORTED = frozenset(
    {
        "cleanup",
        "note",
        "recall",
        "reindex",
        "remember",
        "search",
    }
)


MODEL_INVOCATION_DISABLED = frozenset(
    {
        "cleanup",
        "end-day",
        "end-week",
        "forget",
        "listen",
        "merge-research-draft",
        "migrate-plugin-configs",
        "migrate-scopes-v2",
        "migrate-staged-substrates",
        "rehearse",
        "reindex",
        "relink-memory",
        "research-gaps",
        "setup-identity",
        "setup-obsidian",
        "setup-sources",
        "start-nucleus",
        "start-workstream",
        "sync-linked-entities",
    }
)


SPECS: dict[str, SkillSpec] = {
    "cleanup": SkillSpec("Audit and maintain Cortex memory health, then apply only approved cleanup actions.", "supported", "Approved memory changes are explicitly wired through cortex_cli.py."),
    "end-day": SkillSpec("Run Cortex's end-of-day review, capture, reflection, and next-day preparation workflow.", "partial", "Only the cortex_cli.py-backed steps are deterministic; connector, sibling-plugin, and remaining prose-only writes must degrade or be previewed."),
    "end-week": SkillSpec("Run Cortex's end-of-week cleanup, review, rehearsal, and reflection sequence.", "partial", "This orchestration depends on partially wired child workflows and optional sibling plugins."),
    "forget": SkillSpec("Remove, archive, or correct Cortex memories after showing impact and obtaining confirmation.", "supported", "Destructive actions are confirmed and explicitly wired through cortex_cli.py."),
    "learn": SkillSpec("Capture durable knowledge in Cortex using its seven-type knowledge taxonomy.", "partial", "The canonical workflow still describes its writes in prose; produce a proposal unless every write is expressed through the shared CLI."),
    "listen": SkillSpec("Ingest configured daily sources and yesterday's brief state, stage memory proposals, and refresh the hot cache.", "partial", "Connectors are optional and archive writes remain partly prose-only. Brief-state mining works from the canonical local state file and Markdown twin; without explicit state it runs inference-only. Skip unavailable sources and never invent records."),
    "merge-research-draft": SkillSpec("Review a staged Cortex research draft and merge approved findings into active memory.", "partial", "Review is available, but canonical merge mutations are not yet fully wired through cortex_cli.py."),
    "migrate-plugin-configs": SkillSpec("Preview and perform Cortex's one-time cleanup of legacy files in the config root's plugins directory.", "supported", "Every file operation is wired through cortex_cli.py migrate-plugin-configs; dry-run first, then apply after confirmation."),
    "migrate-scopes-v2": SkillSpec("Preview and perform Cortex's private memory-scope migration idempotently.", "partial", "The migration moves and deletes files and updates git state; preview every affected path and obtain explicit confirmation before applying it."),
    "migrate-staged-substrates": SkillSpec("Preview and perform Cortex's staged-substrate layout migration idempotently.", "partial", "The canonical migration is prose-specified and lacks a complete deterministic CLI path."),
    "morning": SkillSpec("Review overnight Cortex proposals, including yesterday's brief actions, then seed today's priorities and context.", "partial", "Brief-derived proposals and cache refresh are available from local files; optional sources and any prose-only writes degrade."),
    "note": SkillSpec("Append a short timestamped note to an existing Cortex node.", "supported", "The memory mutation is explicitly wired through cortex_cli.py."),
    "recall": SkillSpec("Load and synthesize relevant Cortex memory for a topic, node, or current context.", "supported", "Read-only workflow; broad queries may delegate but always have an inline fallback."),
    "rehearse": SkillSpec("Review aging Cortex knowledge and confirm, demote, archive, or connect selected entries.", "supported", "Approved memory changes are explicitly wired through cortex_cli.py."),
    "reindex": SkillSpec("Regenerate Cortex's deterministic memory index from current node files.", "supported", "The operation is implemented by cortex_cli.py reindex."),
    "relink-memory": SkillSpec("Audit and improve Cortex wikilinks and entity relationships with confirmation.", "supported", "Approved memory changes are explicitly wired through cortex_cli.py."),
    "remember": SkillSpec("Commit conversation decisions, knowledge, open threads, and observations to Cortex memory.", "supported", "Memory mutations are explicitly wired through cortex_cli.py; model extraction remains non-deterministic and must be reviewed in full mode."),
    "research-gaps": SkillSpec("Detect Cortex knowledge gaps, research approved items, and stage cited proposals.", "partial", "Web search and delegation are optional, while draft and merge writes are not yet completely CLI-wired."),
    "search": SkillSpec("Search across Cortex memory and return deduplicated answers with file citations.", "supported", "Read-only workflow with an inline fallback when subagent delegation is unavailable."),
    "setup-identity": SkillSpec("Configure the identity and working-context information Cortex uses.", "partial", "Non-memory config writes are prose-specified; preview them unless performed with the shared atomic-write library."),
    "setup-obsidian": SkillSpec("Configure Cortex memory as an Obsidian-readable vault and graph.", "partial", "External application setup and non-memory config writes require explicit host support and confirmation."),
    "setup-sources": SkillSpec("Configure the note and activity sources Cortex may read.", "partial", "Connector authorization is host-specific and config writes require the shared atomic-write library."),
    "start-nucleus": SkillSpec("Create the initial Cortex memory nucleus from approved source material.", "partial", "Source access is host-specific and canonical bulk writes are not fully CLI-wired."),
    "start-workstream": SkillSpec("Create a Cortex workstream node and link it to relevant entities.", "partial", "Canonical node creation and link updates are not yet completely CLI-wired."),
    "sync-linked-entities": SkillSpec("Synchronize approved summaries and metadata across linked Cortex entities.", "supported", "Approved memory changes are explicitly wired through cortex_cli.py."),
}


def _command_description(text: str) -> str:
    match = re.search(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return ""
    desc = re.search(r"^description:\s*(.+)$", match.group(1), re.MULTILINE)
    return desc.group(1).strip() if desc else ""


def render(name: str, spec: SkillSpec) -> str:
    support_rule = (
        "The canonical workflow is supported on Codex under the capability binding below."
        if spec.status == "supported"
        else "This adapter is intentionally partial. Never imply that its unavailable steps completed."
    )
    work_status = "supported" if name in WORK_SUPPORTED else "partial"
    work_rule = (
        "The workflow is supported in ChatGPT Work through the bounded Cortex MCP tools."
        if work_status == "supported"
        else "In ChatGPT Work, preview or skip any step for which the bounded MCP bridge has no mutation tool."
    )
    invocation_gate = (
        "disable-model-invocation: true\n" if name in MODEL_INVOCATION_DISABLED else ""
    )
    return f"""---
{invocation_gate}name: {name}
description: {spec.description}
metadata:
  cortex-canonical: commands/{name}.md
  codex-status: {spec.status}
  chatgpt-work-status: {work_status}
---

# Cortex: {name}

This is a thin host adapter. Starting from this loaded `SKILL.md` file, walk upward to the nearest directory containing `AGENTS.md`, `commands/{name}.md`, and `scripts/cortex_cli.py`; call it `<cortex-repo-root>`. Do not assume the current working directory is the Cortex repository. If no such root is readable, stop.

Read `<cortex-repo-root>/AGENTS.md`, `<cortex-repo-root>/commands/{name}.md`, `<cortex-repo-root>/references/core-contract.md`, and the current host's column (Claude Code, Cowork, Codex, or ChatGPT Work) in `<cortex-repo-root>/references/capability-matrix.md` completely before acting. The command file is the workflow authority. If those sources conflict, stop and report the conflict instead of inventing behavior.

## Invocation

On Claude, use the text following `/{name}`; on Codex, use the text following `${name}`; in ChatGPT Work, use the user's text after selecting Cortex or this skill with `@`. Natural-language activation is also allowed when the request clearly matches the description.

## Host binding

1. Resolve `<config-root>` through the shared `scripts/lib/config_root.py` precedence chain. On filesystem-capable hosts, `<cortex-repo-root>/hooks/session_start.py --print-root` is available. In cloud Work, call `cortex_status`; the MCP bridge resolves the same chain on the machine that owns the memory. Do not create a host-specific pointer.
2. Require `filesystem.read` for memory access. On Claude Code, Codex, or Local Work, the resolved root must be inside the host's readable/writable roots as appropriate; Cowork requests its directory grant. In cloud Work, use `cortex_recall` and `cortex_search`; never claim direct access to device files.
3. Bind every optional operation through `references/capability-matrix.md`. Skip unavailable connectors, web search, scheduling, artifacts, or delegation exactly as that capability's degrade rule says.
4. Treat model-tier names in the canonical workflow as cost/latency intent. Use a host-available low-cost/fast model when possible; otherwise run inline and disclose the degradation.

## Mutation boundary

For every local write under `<config-root>/memory/`, shell out to `<cortex-repo-root>/scripts/cortex_cli.py` or import the existing implementation from `<cortex-repo-root>/scripts/lib/`. In cloud Work, use `cortex_configure` only for a confirmed first-run pointer setup; for memory mutations use only `cortex_add_note`, `cortex_update_section`, `cortex_reindex`, and `cortex_refresh_hot`. Show the exact proposed change and obtain confirmation before setting `user_confirmed=true`. Replacing an existing pointer requires a separate confirmation before `force_pointer=true`. The bridge intentionally has no move, delete, append-line, or whole-file-write tool; preview or skip those steps. Never hand-edit memory files and never reimplement locking, atomic replacement, index generation, or hot-cache generation.

If the canonical step has no deterministic CLI/library path, show a proposed change or skip that step; do not turn prose into an unreviewed write. Session-end hooks are best-effort reminders, never proof that `/remember` completed.

## Adapter status: {spec.status}

{support_rule} {spec.note} {work_rule}

End with a concise account of what was read, what changed, which optional capabilities were unavailable, and which partial steps were left unapplied.
"""


def expected_files() -> dict[Path, str]:
    command_names = {path.stem for path in (ROOT / "commands").glob("*.md")}
    spec_names = set(SPECS)
    if command_names != spec_names:
        missing = sorted(command_names - spec_names)
        extra = sorted(spec_names - command_names)
        raise ValueError(f"skill specs differ from commands (missing={missing}, extra={extra})")

    out: dict[Path, str] = {}
    for name, spec in sorted(SPECS.items()):
        command_text = (ROOT / "commands" / f"{name}.md").read_text(encoding="utf-8")
        if not _command_description(command_text):
            raise ValueError(f"commands/{name}.md has no frontmatter description")
        out[ROOT / "skills" / name / "SKILL.md"] = render(name, spec)
        out[ROOT / ".agents" / "skills" / name / "SKILL.md"] = render(name, spec)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write generated wrappers")
    parser.add_argument("--check", action="store_true", help="fail if wrappers are stale")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")

    try:
        files = expected_files()
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    stale: list[str] = []
    for path, content in files.items():
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        elif not path.exists() or path.read_text(encoding="utf-8") != content:
            stale.append(str(path.relative_to(ROOT)))

    if stale:
        print("ERROR: stale Codex skill adapters: " + ", ".join(stale), file=sys.stderr)
        return 1
    verb = "wrote" if args.write else "verified"
    print(f"OK: {verb} {len(files)} generated Agent Skill wrappers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
