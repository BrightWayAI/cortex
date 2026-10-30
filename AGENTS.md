# Cortex — Codex handoff

This is the durable instruction entrypoint for Codex sessions working in
this repository, or working against Cortex memory from any other directory
once `<config-root>` is resolved. It exists because you (Codex) are about
to be introduced as a second host alongside Claude Code/Cowork, sharing the
same memory.

**Do not duplicate workflow content into this file.** It points at the
canonical, host-neutral sources; it does not re-describe them. If something
here conflicts with the files it points to, those files win — this is a
map, not the territory.

## Read these first, in order

1. **`references/core-contract.md`** — the single canonical definition of
   config-root resolution, memory layout, node schema, the 7-type knowledge
   taxonomy, wikilink rules, locking/atomic-write requirements, privacy
   tiers, and backward-compatibility guarantees. Everything else assumes
   you've read this.
2. **`references/capability-matrix.md`** — the logical capabilities
   (`filesystem.read`, `web.search`, `subagent.delegate`, etc.) that
   canonical workflows reference instead of naming a specific tool. Your
   job as the Codex adapter is to map each capability to whatever Codex
   actually offers, and to document degrade behavior for the ones you
   don't have.
3. **`docs/PORTABILITY_READINESS.md`** — the Codex-specific mapping table
   (`AGENTS.md` ↔ `CLAUDE.md`, Agent Skills ↔ `commands/*.md`, etc.) and,
   critically, the **Known gaps** and **Risks that would require testing
   against real memory** sections. Read those before assuming anything here
   is more finished than it is.

## What already exists and is safe to use as-is

- **`scripts/cortex_cli.py`** — a plain Python CLI, no Claude-specific
  dependencies. Shell out to it exactly the way `commands/*.md` files
  already do: `python3 scripts/cortex_cli.py <subcommand> --memory-root
  <config-root>/memory ...`. This is the actual mechanism that acquires the
  shared lock, writes atomically, and releases — using it is not optional
  for any memory mutation. See `references/core-contract.md` §11.
- **`scripts/lib/*.py`** — the underlying deterministic utilities (locking,
  atomic writes, section editing, decay classification, index/hot-cache
  generation, node-path validation, repo checks). All are plain Python,
  fixture-tested under `tests/`, with no Claude/Cowork dependency. Import
  them directly if you're writing Codex-side tooling instead of shelling
  out.
- **`commands/*.md`** — the canonical workflow specs. These are the
  workflows themselves; a Codex Agent Skill for e.g. `/remember` should be
  a thin wrapper that reads and follows `commands/remember.md`, the same
  relationship `.claude/commands/remember.md` has to it (see
  `scripts/generate_claude_commands.py` for exactly how thin — Codex's
  equivalent doesn't have to be auto-generated, but should be similarly
  non-divergent).
- **The config-root pointer chain.** To share memory with an existing
  Claude Code/Cowork setup, read (in this order): `CORTEX_CONFIG_ROOT` env
  var → `~/.cortex/config-root` file → legacy
  `~/Documents/.claude-plugin-config-root` file → `~/Documents/Claude`
  default. Whoever set up Claude Code already resolves to one of these; use
  the same one rather than inventing a Codex-specific pointer.
- **First-run configuration.** `scripts/configure_cortex.py` safely writes the
  vendor-neutral pointer and initializes only missing starter files through the
  shared CLI. ChatGPT Work exposes the same operation as the confirmation-gated
  `cortex_configure` MCP tool. Neither path deletes or migrates an old root.

## Adapter status and remaining limits

- **The OpenAI adapter exists.** `skills/*/SKILL.md` and
  `.agents/skills/*/SKILL.md` are generated wrappers over `commands/*.md`;
  `plugin.json` is the portable manifest; `hooks/session_start.py` provides
  bounded read-only recall; `.codex/agents/` contains the supported role
  bindings; and `adapters/chatgpt_work/` exposes a bounded MCP bridge for Local
  and cloud Work. Setup is documented in `docs/CODEX_SETUP.md` and
  `docs/CHATGPT_WORK_SETUP.md`; workspace sharing is documented in
  `docs/ORGANIZATION_DISTRIBUTION.md`.
- **Several mutating commands are wired to `cortex_cli.py`, not all.**
  `/remember`, `/note`, `/forget`, `/cleanup`, `/rehearse`,
  `/relink-memory`, `/sync-linked-entities`, and `/end-day`'s index/hot-cache/
  lock steps use it. Anything not listed there may still describe its
  writes in prose only — check the specific `commands/<name>.md` file
  before assuming a write path is code-backed.
- **Four `agents/*.md` roles have read-only Codex bindings**:
  memory-librarian, note-taker, and gap-researcher.
  `note-taker`'s `mode: conversation` mines Cowork's own session history; Codex has no
  equivalent and the role is intentionally unavailable.
- **Model-tier language** (e.g. "a low-cost/fast-tier model, Claude
  adapter: Haiku") appears throughout `commands/*.md` for cost-tiering
  decisions. Substitute Codex's own equivalent cheap/fast model where the
  workflow calls for one; don't skip the tiering distinction, it exists for
  real cost reasons documented inline.

## Testing and validation

Before trusting any change you make in this repo, run:

```
python3 scripts/check_repo.py
```

This runs frontmatter validation, the repo-check suite (skill naming,
broken internal references, taxonomy drift, command/skill coverage,
version agreement), the Claude-command and Agent-Skill freshness checks, and the full
fixture-based test suite under `tests/` (unit tests import
`scripts/lib/*.py` directly; `tests/test_integration_cli_subprocess.py`
invokes `scripts/cortex_cli.py` as a real subprocess against fixture memory
roots — read that file for worked examples of full command sequences, e.g.
what `/remember` actually does end-to-end). None of this touches real user
memory; if you add tests, keep it that way — always operate against
`tempfile.TemporaryDirectory()`.

## Maintaining the Codex adapter

Invoke workflows as `$remember`, `$recall`, `$note`, and the other skill
names. Edit `commands/*.md` for workflow behavior or
`scripts/generate_codex_skills.py` for adapter metadata, then run:

```
python3 scripts/generate_codex_skills.py --write
python3 scripts/check_repo.py
```

Keep capability translation in `references/capability-matrix.md`, not in a
fork of the workflow, and keep all development tests on fixtures or temporary
directories.

## Cloud-first sync (v4.29+) — read before writing memory

Cortex is now GitHub-first. A config-root is two checkouts (`memory/` = org repo,
`.private/` = per-user private repo) joined by directory symlinks, so every path in
`references/core-contract.md` §2 is unchanged. Do not re-describe the rules here; the
canonical definition is **core-contract.md §11B** and the capability is
`workspace.bootstrap` / `sync.git` in `references/capability-matrix.md`.

What changes for you as a Codex host:

- If no config-root resolves, run `python3 scripts/cortex_cli.py bootstrap --print-env`
  (finds the two repos by their `.cortex-role` marker when attached as sources; otherwise
  needs `CORTEX_ORG_REPO` / `CORTEX_PRIVATE_REPO` or `--org-repo` / `--private-repo`),
  then use the printed root. `~/cortex-root` is now a resolution tier (§1 #5).
- After approved writes, run `python3 scripts/cortex_cli.py sync --root <config-root>`.
  Never force-push; a conflict is pushed to `conflict/<host>/<ts>` and reported.
- `me/`, `staged/`, `archive/`, `briefs/`, and `plugins/` are private and live in the
  private repo. The org repo must never track them or any symlink; `sync` enforces this.
- `.lock` is per-checkout and does not coordinate across machines — git does.
- A Mac `launchd` job runs `sync` on the user's machine; if you run there, you will see its
  commits (`autosync <host> <ts>`) and `.sync-status.json` / `staged/sync-log.md`.
