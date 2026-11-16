---
disable-model-invocation: true
name: migrate-plugin-configs
description: Preview and perform Cortex's one-time cleanup of legacy files in the config root's plugins directory.
metadata:
  cortex-canonical: commands/migrate-plugin-configs.md
  codex-status: supported
  chatgpt-work-status: partial
---

# Cortex: migrate-plugin-configs

This is a thin host adapter. Starting from this loaded `SKILL.md` file, walk upward to the nearest directory containing `AGENTS.md`, `commands/migrate-plugin-configs.md`, and `scripts/cortex_cli.py`; call it `<cortex-repo-root>`. Do not assume the current working directory is the Cortex repository. If no such root is readable, stop.

Read `<cortex-repo-root>/AGENTS.md`, `<cortex-repo-root>/commands/migrate-plugin-configs.md`, `<cortex-repo-root>/references/core-contract.md`, and the current host's column (Claude Code, Cowork, Codex, or ChatGPT Work) in `<cortex-repo-root>/references/capability-matrix.md` completely before acting. The command file is the workflow authority. If those sources conflict, stop and report the conflict instead of inventing behavior.

## Invocation

On Claude, use the text following `/migrate-plugin-configs`; on Codex, use the text following `$migrate-plugin-configs`; in ChatGPT Work, use the user's text after selecting Cortex or this skill with `@`. Natural-language activation is also allowed when the request clearly matches the description.

## Host binding

1. Resolve `<config-root>` through the shared `scripts/lib/config_root.py` precedence chain. On filesystem-capable hosts, `<cortex-repo-root>/hooks/session_start.py --print-root` is available. In cloud Work, call `cortex_status`; the MCP bridge resolves the same chain on the machine that owns the memory. Do not create a host-specific pointer.
2. Require `filesystem.read` for memory access. On Claude Code, Codex, or Local Work, the resolved root must be inside the host's readable/writable roots as appropriate; Cowork requests its directory grant. In cloud Work, use `cortex_recall` and `cortex_search`; never claim direct access to device files.
3. Bind every optional operation through `references/capability-matrix.md`. Skip unavailable connectors, web search, scheduling, artifacts, or delegation exactly as that capability's degrade rule says.
4. Treat model-tier names in the canonical workflow as cost/latency intent. Use a host-available low-cost/fast model when possible; otherwise run inline and disclose the degradation.

## Mutation boundary

For every local write under `<config-root>/memory/`, shell out to `<cortex-repo-root>/scripts/cortex_cli.py` or import the existing implementation from `<cortex-repo-root>/scripts/lib/`. In cloud Work, use `cortex_configure` only for a confirmed first-run pointer setup; for memory mutations use only `cortex_add_note`, `cortex_update_section`, `cortex_reindex`, and `cortex_refresh_hot`. Show the exact proposed change and obtain confirmation before setting `user_confirmed=true`. Replacing an existing pointer requires a separate confirmation before `force_pointer=true`. The bridge intentionally has no move, delete, append-line, or whole-file-write tool; preview or skip those steps. Never hand-edit memory files and never reimplement locking, atomic replacement, index generation, or hot-cache generation.

If the canonical step has no deterministic CLI/library path, show a proposed change or skip that step; do not turn prose into an unreviewed write. Session-end hooks are best-effort reminders, never proof that `/remember` completed.

## Adapter status: supported

The canonical workflow is supported on Codex under the capability binding below. Every file operation is wired through cortex_cli.py migrate-plugin-configs; dry-run first, then apply after confirmation. In ChatGPT Work, preview or skip any step for which the bounded MCP bridge has no mutation tool.

End with a concise account of what was read, what changed, which optional capabilities were unavailable, and which partial steps were left unapplied.
