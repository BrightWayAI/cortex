# Capability matrix (Phase 6)

Canonical workflows (`commands/*.md` and `references/*.md`) describe what they
need in terms of the **logical capabilities** below, never a specific host tool,
MCP server, model name, or "Task tool" syntax. Generated
`skills/*/SKILL.md` files are adapter entrypoints: they may name the shared
host-neutral Cortex CLI, but host-specific tools belong in this table. Host
adapters (Claude Code, Cowork, Codex) translate a capability into whatever
mechanism that host actually offers.

If a canonical file names a concrete tool (e.g. `mcp__cowork__request_cowork_directory`,
"the Task tool", `subagent_type="memory-librarian"`), that is host leakage and
should be rewritten to reference a capability name from this table instead,
with the concrete tool name pushed into the per-host column here.

## Capabilities

### `filesystem.read` / `filesystem.write`

| | |
|---|---|
| Required or optional | Required |
| Claude Code | Native filesystem access via the Read/Write/Edit/Bash tools. |
| Cowork | `mcp__cowork__request_cowork_directory(path=<config-root>)`, then native fs once granted. |
| Codex | Native filesystem and shell tools, constrained by the active sandbox. Configure the resolved `<config-root>` as a readable root and, for mutating workflows, a writable root. |
| ChatGPT Work | Local Work uses permissioned local access or the bundled stdio Cortex MCP server. Cloud Work has no direct device filesystem and uses the private Secure MCP Tunnel bridge in `adapters/chatgpt_work/`; a marketplace install alone is insufficient. |
| Behavior when unavailable | Fatal — memory cannot function without this. Explain and stop; never fabricate memory content in its place. |
| Reads/writes external state | No (local disk only). |
| Confirmation policy | Cowork requires one-time user approval per directory; Claude Code requires none (sandboxed to the working directory / explicitly granted paths). |

### `filesystem.atomic_replace`

| | |
|---|---|
| Required or optional | Required for any mutating workflow. |
| Claude Code | `scripts/lib/atomic_write.py` (`atomic_write`/`safe_append`), invoked via `scripts/cortex_cli.py`. |
| Cowork | Same underlying utility — Cowork's model shells out to the same repo scripts via its filesystem access; no separate implementation. |
| Codex | Same shared utility, invoked through `scripts/cortex_cli.py` or imported from `scripts/lib/`; direct model edits to memory files are not an implementation of this capability. |
| ChatGPT Work | The Cortex MCP bridge shells out to the same `scripts/cortex_cli.py`; it never treats an MCP tool handler's direct file write as atomic replacement. |
| Behavior when unavailable | Fatal for mutating workflows — fall back to `filesystem.write` is explicitly disallowed once a node file exists, since it risks partial writes. |
| Reads/writes external state | No. |
| Confirmation policy | None beyond the workflow's own user-facing confirmation step. |

### `filesystem.lock`

| | |
|---|---|
| Required or optional | Required for any mutating workflow. |
| Claude Code | `scripts/lib/locking.py` (`MemoryLock`), invoked via `scripts/cortex_cli.py`. |
| Cowork | Same utility, same mechanism — the lock file lives in `<config-root>/memory/.lock` on shared disk, so it coordinates across hosts regardless of which one is writing. |
| Codex | Same shared lock and CLI. The lock file is host-neutral, so Claude and Codex writers coordinate on the same `<config-root>/memory/.lock`. |
| ChatGPT Work | Same host-neutral lock through the MCP bridge and shared CLI, including when the call arrived through Secure MCP Tunnel. |
| Behavior when unavailable | Fatal for mutating workflows. A workflow must not write without acquiring this. |
| Reads/writes external state | No. |
| Confirmation policy | None; surfaces a wait/timeout message to the user only on contention (see `references/core-contract.md` §11). |

### `user.confirm`

| | |
|---|---|
| Required or optional | Required wherever a workflow calls for it (e.g. destructive `/forget`, ambiguous node routing). |
| Claude Code | A message in the conversation asking the user to respond. |
| Cowork | Same — a chat turn. |
| Codex | Same — ask in the active chat turn. Unattended tasks must stage a proposal instead of assuming approval. |
| ChatGPT Work | Ask in chat and use the host's write-tool approval UI. The MCP bridge additionally rejects write calls unless `user_confirmed=true`; unattended calls must not set it. |
| Behavior when unavailable | N/A — this capability is definitionally always available in an interactive session. In fully unattended/autonomous runs (e.g. `/listen`), workflows must not depend on it and must instead stage a proposal for later confirmation. |
| Reads/writes external state | No. |
| Confirmation policy | This *is* the confirmation mechanism. |

### `web.search`

| | |
|---|---|
| Required or optional | Optional (used by `/research-gaps`). |
| Claude Code | `WebSearch`/`WebFetch` tools. |
| Cowork | Equivalent built-in web tools, or an MCP web-search server if configured. |
| Codex | The host's web-search tool when enabled. If it is absent, use the common skip-and-disclose degradation; do not substitute uncited model knowledge for current research. |
| ChatGPT Work | Built-in web search when enabled by the workspace and available to the chat; otherwise use the same skip-and-disclose behavior. |
| Behavior when unavailable | Degrade predictably — skip web-sourced findings, tell the user research was skipped, don't fabricate sources. |
| Reads/writes external state | Reads (queries a third-party service; queries themselves leave the local machine). |
| Confirmation policy | None required by default; a workflow may choose to confirm before sending a query that contains sensitive node content (see `references/core-contract.md` §13 privacy tiers). |

### `connector.calendar.read` / `connector.mail.read` / `connector.transcripts.read`

| | |
|---|---|
| Required or optional | Optional — only used by `/listen` and sibling-plugin-fed ingest. |
| Claude Code | Provided by an MCP connector or a sibling Nucleus plugin, if configured. Not implemented in this repo. |
| Cowork | Same — via whatever connector integration Cowork has configured. |
| Codex | Provided by configured MCP servers, apps, or sibling plugins. Cortex ships no calendar, mail, or transcript connector. |
| ChatGPT Work | Provided by separately installed and authorized plugins or MCP apps. Installing Cortex does not grant connector authorization. |
| Behavior when unavailable | `/listen` skips the source, notes it as unavailable in `_index.md` (see `references/archive-layout.md`), and continues with whatever sources it does have. Never fatal. |
| Reads/writes external state | Reads (pulls from a third-party calendar/mail/transcript service). |
| Confirmation policy | One-time authorization at connector setup time (outside this repo's scope); no per-run confirmation. |

### `connector.slack.read`

| | |
|---|---|
| Required or optional | Optional — used by `/listen` to pull mentions and authored messages into `archive/YYYY-MM-DD/slack.md`. |
| Claude Code / Cowork | Provided by a Slack MCP server if configured. |
| Codex | Provided by a configured Slack MCP server or app; otherwise unavailable. |
| ChatGPT Work | Provided by an installed and authorized Slack plugin/app; otherwise unavailable. |
| Behavior when unavailable | `/listen` skips Slack for that day's archive, notes it in `_index.md` as skipped, and continues with other sources. Never fatal. |
| Reads/writes external state | Reads. |
| Confirmation policy | One-time authorization at connector setup; no per-run confirmation. |

### `connector.drive.read`

| | |
|---|---|
| Required or optional | Optional — used by `/listen` to pull file changes in watched folders into `archive/YYYY-MM-DD/drive.md`. |
| Claude Code / Cowork | Provided by a Drive MCP server if configured. |
| Codex | Provided by a configured Drive MCP server or app; otherwise unavailable. |
| ChatGPT Work | Provided by an installed and authorized Drive plugin/app; otherwise unavailable. |
| Behavior when unavailable | `/listen` skips Drive for that day's archive, notes it in `_index.md` as skipped, and continues. Never fatal. |
| Reads/writes external state | Reads. |
| Confirmation policy | One-time authorization at connector setup; no per-run confirmation. |

### `connector.crm.read`

| | |
|---|---|
| Required or optional | Optional — used by `note-taker` (mode: activity) for deal-stage/lifecycle/task-closure events. |
| Claude Code / Cowork | Provided by a CRM MCP server if configured (e.g. HubSpot: `search_crm_objects`, `get_crm_objects`, `search_properties`). |
| Codex | Provided by a configured CRM MCP server or app; otherwise unavailable. |
| ChatGPT Work | Provided by an installed and authorized CRM plugin/app; otherwise unavailable. |
| Behavior when unavailable | `note-taker` (mode: activity) skips the CRM source and continues with mail/calendar (see its per-connector triage gate). Never fatal. |
| Reads/writes external state | Reads. |
| Confirmation policy | One-time authorization at connector setup; no per-run confirmation. |

### `connector.crm.write`

| | |
|---|---|
| Required or optional | Optional, and out of scope for core Cortex — this is a sibling-plugin (HubSpot-style) capability referenced by cross-plugin documentation, not implemented here. |
| Claude Code / Cowork | Provided entirely by the sibling plugin; Cortex core never writes to a CRM directly. |
| Codex | Same: only a separately configured sibling plugin may implement it. Cortex core never maps generic filesystem access to CRM writes. |
| ChatGPT Work | Same: only a separately authorized CRM plugin may write. Cortex never exposes CRM writes through its memory bridge. |
| Behavior when unavailable | No effect on core memory workflows — this capability doesn't gate anything in this repo. |
| Reads/writes external state | Writes (to an external CRM). |
| Confirmation policy | Owned by the sibling plugin, not documented here. |

### `subagent.delegate`

| | |
|---|---|
| Required or optional | Optional — an efficiency choice for broad/cross-node queries (e.g. `/search` Step 0). |
| Claude Code | The `Agent` tool with a named subagent type (e.g. `memory-librarian`). |
| Cowork | The `Task` tool with `subagent_type="memory-librarian"`. |
| Codex | Codex subagent delegation, with repository roles in `.codex/agents/` when custom agents are enabled. Fall back inline if the surface does not expose delegation. |
| ChatGPT Work | No portable named Cortex-role binding is assumed. Run inline when Work does not expose compatible delegation. |
| Behavior when unavailable | Fall through to inline execution — read the relevant files directly instead of delegating. Never treat delegation as required. |
| Reads/writes external state | No (delegates to another local agent instance). |
| Confirmation policy | None. |

### `artifact.read` / `artifact.update`

| | |
|---|---|
| Required or optional | Optional — Cowork-specific enhancement (e.g. paste-path / brief-state bridging). |
| Claude Code | Not applicable; Claude Code has no artifact layer distinct from the filesystem. |
| Cowork | Cowork artifact APIs. |
| Codex | No portable artifact binding is assumed. Use a filesystem snapshot only when the workflow explicitly permits that degradation; otherwise skip the enhancement. |
| ChatGPT Work | No separate Cortex artifact adapter is assumed. Local Work may use authorized files; cloud Work may use uploaded/project files, but neither substitutes for the Cortex MCP memory source. |
| Behavior when unavailable | Core memory workflows must work with this capability entirely absent — it is documented as an enhancement, never a dependency, per Phase 6 of the portability refactor. |
| Reads/writes external state | No (local to the host session). |
| Confirmation policy | None beyond the host's own artifact-access model. |

### `workspace.bootstrap` / `sync.git`

| | |
|---|---|
| Required or optional | Required on any host that does not already hold a config-root (cloud sessions, scheduled tasks). Optional elsewhere. |
| Claude Code | `python3 scripts/cortex_cli.py bootstrap` then `... sync`; no native equivalent. |
| Claude cloud / scheduled routine | Same CLI from the installed plugin. The routine's repo sources are reused via `--adopt-org` / `--adopt-private`; push uses the session's `GH_TOKEN`. No device attachment needed. |
| Cowork / Mac | The Mac copy is kept in sync by a launchd job running `cortex_cli.py sync` with the host's git credentials. |
| Codex | Same CLI; Codex must not edit shared nodes directly (see §11A) and must run `sync` after approved writes. |
| ChatGPT Work | Same CLI through the bridge; cloud Work has no device filesystem and relies on bootstrap. |
| Behavior when unavailable | Fall back to the existing local config-root; cloud workflows with no resolvable root stop with a structured error. |
| Reads/writes external state | Yes (git remotes). |
| Confirmation policy | None for pull/push of the user's own repos; conflicts are reported, never auto-resolved. |

### `scheduler.register`

| | |
|---|---|
| Required or optional | Optional — used by `/listen`'s nightly cron framing and similar unattended triggers. |
| Claude Code | No native scheduler; the user runs `/listen` manually or wires an external cron to invoke it. |
| Cowork | Cowork's own scheduled-task mechanism, if configured. |
| Codex | Codex scheduled tasks on surfaces that expose them; otherwise invoke `$listen` manually or use an external scheduler. The adapter does not register a schedule automatically. |
| ChatGPT Work | Use scheduled tasks only when the Work surface and workspace policy expose them. Otherwise invoke Cortex manually; the plugin does not auto-register a schedule. |
| Behavior when unavailable | The workflow remains available as an on-demand command; only the "runs automatically overnight" framing doesn't apply. |
| Reads/writes external state | No (registers a local trigger). |
| Confirmation policy | One-time setup confirmation when the schedule is first registered. |

### `connector.session_history.read`

| | |
|---|---|
| Required or optional | Optional and role-specific — used only by `note-taker` (mode: conversation) to inspect other host sessions. |
| Claude Code | Unavailable; Claude Code has no equivalent cross-session transcript source exposed to Cortex. |
| Cowork | Cowork session-history tools (`list_sessions` and `read_transcript`) when the host grants them. |
| Codex | Unavailable. Local Codex history is not a supported Cortex connector and must not be scraped as a substitute. `note-taker`'s `mode: conversation` is therefore not installed as a Codex custom agent (mode: transcript / mode: activity still are). |
| ChatGPT Work | Unavailable as a Cortex cross-chat connector. Do not scrape ChatGPT-managed history; remember the active conversation explicitly instead. |
| Behavior when unavailable | Skip `note-taker`'s `mode: conversation`, return an explicit source-unavailable note, and continue with transcript/activity sources that are configured. Never infer other-session content. |
| Reads/writes external state | Reads host-managed session data. |
| Confirmation policy | Governed by the host's session-history authorization and the role's `[no-mine]` privacy rule. |

## How to use this table

- A canonical workflow file should say "requires `subagent.delegate`" or "degrades if `web.search` is unavailable," not "use the Task tool" or "call `mcp__cowork__request_cowork_directory`."
- When you find a canonical file naming a concrete tool, replace it with a reference to this table's capability name, and (if the host-specific detail is worth keeping) fold it into this table's per-host column instead.
- This table is descriptive of the current host bindings (Claude Code, Cowork, Codex, ChatGPT Work). New hosts extend the per-capability rows rather than changing canonical workflows.
