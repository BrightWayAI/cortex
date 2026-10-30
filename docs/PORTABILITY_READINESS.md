# Portability readiness

This document describes how a host other than Claude integrates Cortex and
records the implemented Codex adapter. The adapter is deliberately thin:
canonical behavior remains in `commands/*.md`, deterministic mutation remains
in `scripts/cortex_cli.py` and `scripts/lib/`, and both hosts resolve the same
`<config-root>`.

## What already exists to build on

- **A host-neutral data contract and workflow spec** — `references/core-contract.md`
  defines config-root resolution, memory layout, node schema, knowledge
  taxonomy, locking, and append/replace semantics without naming Claude,
  Cowork, or any model.
- **Deterministic utilities usable from any host that can shell out to
  Python** — `scripts/lib/{locking,atomic_write,node_paths,sections,decay,
  index_generator,hot_cache_generator}.py`, fronted by `scripts/cortex_cli.py`.
  A host adapter doesn't need to reimplement locking or atomic writes; it
  shells out to the same CLI Claude Code uses.
- **A capability matrix** (`references/capability-matrix.md`) naming the
  logical operations a workflow needs, independent of tool syntax.
- **Canonical workflow specs** (`commands/*.md`) written in host-neutral
  language wherever this refactor reached them (see Known gaps below for
  what's left).

## Generic integration pattern for a new host

Any host integrating Cortex needs to provide, in its own idiom:

1. **A durable instruction entrypoint** — a file the host always loads at
   session start that points at `references/core-contract.md` instead of
   re-describing it (mirrors what `CLAUDE.md` now does for Claude).
2. **Skill discovery and explicit invocation** — a way to list and invoke
   the workflows in `commands/*.md` (or a host-native equivalent format
   generated from them, as `.claude/commands/` is via `scripts/generate_claude_commands.py`).
3. **Lifecycle hooks** — session-start recall (read `hot.md`, `user.md`,
   `DASHBOARD.md`) and only such session-end reminders as the host can safely
   provide. Never represent a hook reminder as a guaranteed commit.
4. **Filesystem permission configuration** — the host's own mechanism for
   granting read/write access to `<config-root>`, resolved via
   `scripts/lib/config_root.py`'s precedence chain (§1 of the contract) —
   in particular, honoring `CORTEX_CONFIG_ROOT` and `~/.cortex/config-root`
   so multiple hosts share one memory root without host-specific pointer
   files.
5. **Logical capability adapters** — a translation from each entry in
   `references/capability-matrix.md` to the host's actual tools/APIs, plus
   documented degrade behavior for optional capabilities.
6. **Subagent role translation** — the roles described in `agents/*.md`
   (memory-librarian, note-taker, gap-researcher) translated into the host's
   own sub-agent/role configuration format.
7. **Plugin packaging** — a manifest in the host's own format, generated
   from or validated against `.claude-plugin/plugin.json` rather than
   hand-maintained separately.
8. **Scheduled tasks** — for hosts that support them, wiring `/listen` (or
   equivalent) to the host's own scheduler, with the `scheduler.register`
   capability documenting the degrade path (manual invocation) when absent.

## Implemented Codex mapping

| Cortex concept | Codex mechanism | Implementation |
|---|---|---|
| `CLAUDE.md` (durable instructions) | `AGENTS.md` | Root `AGENTS.md` is the mandatory entrypoint. |
| `commands/*.md` (canonical workflows) | Agent Skills | `skills/*/SKILL.md` and `.agents/skills/*/SKILL.md` are generated thin wrappers; `scripts/generate_codex_skills.py` prevents drift. |
| `.claude/commands/*.md` (slash-command adapter) | `$skill-name` or natural language | Use `$remember`, `$recall`, `$note`, etc. Identical slash syntax is neither required nor claimed. |
| Claude Code hooks | Codex `SessionStart` hook | `hooks/hooks.json` invokes the read-only, bounded `hooks/session_start.py`. No session-end commit hook is installed. |
| Claude Code filesystem access | Codex sandbox roots | The user adds the resolved `<config-root>` as a readable/writable root; machine-specific absolute paths are not committed. |
| `agents/*.md` roles | Codex custom agents | Read-only mappings live in `.codex/agents/`, sourced from `adapters/codex/agents/`. `note-taker`'s `mode: conversation` is unavailable. |
| `.claude-plugin/plugin.json` | Portable Agent Plugins manifest | Root `plugin.json` packages the shared skills and the OpenAI hook extension. |

Setup and trust steps are in `docs/CODEX_SETUP.md`.

For legacy user config roots, `memory/CLAUDE.md` is not renamed or duplicated.
The shared configurator creates a short `memory/AGENTS.md` forwarding shim only
when an imported Codex global instruction expects that path. This compatibility
file is distinct from the plugin repository's root `AGENTS.md`.

## Implemented ChatGPT Work mapping

| Cortex concept | ChatGPT Work mechanism | Implementation |
|---|---|---|
| Canonical workflows | Agent Skills in the shared plugin | Root `skills/*/SKILL.md`; invoke naturally, for example "use Cortex to recall…" |
| Local memory access | Local Work plus bundled stdio MCP | Root `mcp.json` launches `adapters/chatgpt_work/server.py` |
| Cloud memory access | Secure MCP Tunnel | The same stdio server runs on the machine that owns the Cortex folder |
| Config-root pointer | Shared resolver | `scripts/lib/config_root.py`; no ChatGPT-specific pointer |
| First-run configuration | Confirmed MCP setup tool or shared script | `cortex_configure` and `scripts/configure_cortex.py` write `~/.cortex/config-root`; replacing a different pointer requires separate confirmation |
| Safe mutations | MCP tools wrapping shared CLI | `cortex_add_note`, `cortex_update_section`, `cortex_reindex`, `cortex_refresh_hot` |
| Session recall | Trusted local hook, or explicit MCP recall | `hooks/session_start.py` locally; `cortex_recall` in cloud Work |
| Destructive workflows | Deliberately unavailable remotely | No MCP move, delete, or whole-file-write tool |

See `docs/CHATGPT_WORK_SETUP.md`. Work on the web cannot directly access the
user's Mac filesystem; a marketplace install alone is not a memory sync
mechanism.

### Workflow support

The generated frontmatter records `codex-status` for each workflow:

- **Supported:** cleanup, forget, note, recall, rehearse, reindex,
  relink-memory, remember, review, search, sync-linked-entities, timeline.
- **Partial:** end-day, end-week, learn, listen, merge-research-draft,
  migrate-staged-substrates, morning, research-gaps, all four setup workflows,
  start-nucleus, and start-workstream.

`partial` means the adapter can read, analyze, and run explicitly shared-CLI
steps, but must preview or skip remaining prose-only mutations. It never means
that a direct file edit is an acceptable fallback.

The same wrappers record `chatgpt-work-status`. Work supports cleanup, note,
recall, reindex, remember, review, search, and timeline through the bounded MCP
bridge. Other workflows are partial because they depend on connectors,
prose-only writes, or remote mutations the bridge intentionally does not
expose (move, delete, append-line, and whole-file replacement).

## Do not claim guaranteed behavior that isn't

Per `references/core-contract.md` and the working principles of this
refactor: a "stop reminder" or hook firing is host-provided best-effort
behavior, not a guarantee that auto-commit ran. Any adapter (Claude or
Codex) must document this distinction explicitly rather than imply
that session-end memory capture is guaranteed. Deterministic guarantees
exist only for the code paths in `scripts/lib/` and `scripts/cortex_cli.py`
— locking, atomic writes, index/hot-cache generation — not for model-driven
steps like extraction or knowledge-typing.

## Known gaps in the implemented adapter

These are current, explicit degradations rather than reasons to fork the
canonical workflows:

1. **Deterministic mutation coverage is incomplete.** `/remember`, `/note`,
   `/forget`, `/cleanup`, `/rehearse`, `/relink-memory`,
   `/sync-linked-entities`, and `/reindex` have explicit shared-CLI mutation
   paths. `/end-day` is partially wired, while `/listen` and `/morning` wire
   cache/index steps but not every surrounding write. Other mutating workflows
   remain prose-specified. Their Agent Skills are marked `partial` and must
   preview or skip unwired writes rather than hand-edit memory.
2. **The capability matrix is applied to `commands/*.md` and `agents/*.md`,
   not yet to `references/*.md`.** `commands/search.md`, `commands/end-day.md`,
   `commands/end-week.md` (removed "Task tool"/`subagent_type=`), and all
   five `agents/*.md` role files (frontmatter `tools:`/`model:` annotated as
   the Claude/Cowork binding; body prose naming MCP tools directly —
   `mcp__session_info__*`, `HubSpot MCP`, `Gmail MCP`, `WebSearch`/`WebFetch`
   — rewritten to name the capability first with the concrete tool as an
   implementation parenthetical) were fixed during this refactor. Added a
   missing `connector.crm.read` capability to the matrix in the process
   (only `connector.crm.write` existed before, but `note-taker`'s `mode: activity`
   reads CRM data). The broader sweep across `references/*.md` (`archive-layout.md`,
   `decay-model.md`, `gap-detection-rules.md`, `node-taxonomy.md`,
   `note-sources.md`) flagged in the Phase 0 audit has not been completed.
3. **`agents/*.md` still name a concrete model tier (`model: sonnet`) in
   frontmatter**, annotated as the Claude/Cowork binding rather than removed.
   `commands/remember.md` §C.2 also names "a Haiku-tier classifier" for the
   concept-drift check — this is a cost-tiering *decision*, not tool syntax,
   and rephrasing it as "a low-cost/fast-tier model" with the concrete choice
   pushed to the adapter layer has not been done.
4. **Conversation mining is unavailable on Codex.**
   `connector.session_history.read` is now formalized in the capability matrix,
   but Codex has no supported implementation. The adapter intentionally omits
   `note-taker`'s `mode: conversation` instead of scraping host history.
5. **External connectors remain installation-specific.** Calendar, mail,
   transcript, Slack, Drive, and CRM reads require separately configured MCP
   servers/apps. Each workflow follows the matrix's skip-and-disclose rule.
6. **Hot-cache generation is partial.** `scripts/lib/hot_cache_generator.py`
   covers node-local sources (changelog, open threads, decisions) but not
   `<config-root>/briefs/` reflections or resolved `staged/commit-drafts/archive/`
   items — documented as a gap in `references/hot-cache.md`, not silently
   dropped, but still a real gap both adapters inherit.
7. **Session-end capture is not guaranteed.** No Codex SessionEnd hook attempts
   model extraction. Users should invoke `$remember` for important commits;
   only completed CLI operations carry deterministic write guarantees.
8. **Cloud Work requires a running private bridge.** Secure MCP Tunnel is the
   supported private/developer transport. Organization members can install the
   plugin from a workspace GitHub marketplace, but remote memory access still
   requires the bridge on the machine that owns each user's files. Public
   cloud distribution remains unavailable until a stable HTTPS deployment with
   OAuth 2.1 and per-user storage isolation exists. Cloud hooks also cannot
   execute laptop scripts; explicit `cortex_recall` is the reliable cloud
   warm-start.
9. **Some canonical prose still assumes Claude's local layout.** Several
   `commands/*.md` files still show `~/Documents/Claude` or Claude/Cowork tool
   labels even though the core contract requires config-root resolution. The
   Work/Codex wrappers and MCP bridge override those host examples through the
   capability matrix. The canonical files should receive a separate cleanup
   pass rather than being forked inside this adapter.

## Risks that would require testing against real memory (not done here)

Everything in this refactor was validated against fixtures and temporary
directories only — no test in `tests/` touches `~/Documents/Claude`,
`~/Documents/ClaudeCortex`, or any other real user data, and none of this
work was run against a sanitized copy of real memory either. The following
would need real-memory testing before being trusted in production, and that
testing has explicitly **not** been done as part of this refactor:

- Whether `scripts/lib/index_generator.py`'s descriptor-extraction heuristic
  (`_descriptor()`) produces sensible output across the full variety of
  hand-authored node files that have accumulated over multiple cortex
  versions (v2.x through v4.13.x), including files with unusual front-matter
  or malformed sections.
- Whether the real `<config-root>/memory/` tree is large enough that
  `render_index`/`render_hot_cache`'s full-tree walk becomes a performance
  concern (fixtures used in testing are small, synthetic trees).
- Whether any real node file uses the legacy colon-prefixed filename form
  (`person:sarah-chen.md` as an actual filename, not just prose syntax) —
  this was never confirmed to exist in real data; the compatibility rule in
  `references/core-contract.md` §3 is written defensively but untested
  against an actual instance.
- Whether real `memory-as-git` repositories already have a committed
  `.write-lock`-based `.gitignore` entry that needs a one-time manual fix
  now that the canonical lock filename is `.lock` (this refactor fixed the
  *templates*, not any already-generated real `.gitignore` file).

Do not treat any of the above as validated. If real-memory testing is
wanted, it requires explicit authorization to work against a sanitized copy
of actual user data, which was out of scope for this session.

## Cloud-first sync (v4.29)

All hosts share a two-repo config-root materialized by `cortex_cli.py bootstrap` and kept
current by `cortex_cli.py sync` (`scripts/lib/repo_sync.py`; contract in
`references/core-contract.md` §11B). Codex needs no adapter change beyond calling those two
commands; the open question is credentials on each Codex surface (git push auth), which is
host-specific and untested here.
