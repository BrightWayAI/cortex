# Cortex v4.15 — One Second Brain Across AI Hosts

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/BrightWayAI/claude-cortex/actions/workflows/validate.yml/badge.svg)](https://github.com/BrightWayAI/claude-cortex/actions/workflows/validate.yml)

**Give Claude, ChatGPT Work, and Codex one shared second brain.**

Most AI conversations are disposable. Cortex makes them cumulative. It runs silently in the background — observing your preferences, capturing knowledge, learning from corrections — so every conversation builds on the last.

Explicit commands provide the reliable capture path; host auto-recall and
auto-commit behavior is best-effort.

Works on **Cowork** (Claude Desktop), **Claude Code**, **ChatGPT Work**, and
**Codex**. Local surfaces use the user-owned Markdown directly; cloud Work
reaches it through a private MCP tunnel.

---

## What's New in v4

### The Always-On Brain

On Claude hosts, v4 can observe and recall automatically. The OpenAI adapter
keeps durable commits explicit: use `$remember` or `@Cortex remember` when a
save matters.

| Behavior | What it does | Platform |
|----------|-------------|----------|
| **Auto-recall** | Loads your profile and project context at conversation start | Claude hosts; bounded SessionStart recall in Codex |
| **Passive observation** | Learns preferences, corrections, and domain knowledge | Claude hosts |
| **Contextual recall** | Surfaces relevant knowledge when you mention a project/topic | All hosts when the workflow is active |
| **Auto-commit** | Saves knowledge and observations when the conversation ends | Claude hosts, best effort |
| **Explicit commit** | Previews and confirms durable memory changes | All hosts |
| **User profile** | Persistent model of who you are and how you like to work | All hosts |
| **Per-project config** | Controls capture behavior via `.cortex.json` when the host loads it | Host-dependent |
| **Claude Code support** | Drop-in CLAUDE.md instructions + optional hooks | Claude Code |
| **Codex support** | AGENTS.md + Agent Skills + bounded SessionStart recall | Codex |

### The Learning Loop

```
Claude-hosted conversation starts
  → Auto-recall loads your profile + project context
  → Claude adapts to your known preferences

Conversation happens
  → Passive observation accumulates new signals
  → Contextual recall surfaces relevant knowledge on mention
  → Claude adapts in real-time

Conversation ends (best effort; explicit /remember is reliable)
  → Auto-commit saves decisions, knowledge, and observations
  → Your profile and project nodes get smarter

Next conversation starts
  → Claude knows more. Repeats less. Helps better.
```

---

## Quick Start

### Claude Code / Cowork via the Nucleus marketplace — recommended

```
/plugin marketplace add BrightWayAI/nucleus
/plugin install cortex@nucleus
```

### Cowork (Claude Desktop) — Full Support

1. Download the plugin zip
2. Claude Desktop → Cowork tab → Customize → Upload custom plugin
3. Select `cortex.zip`
4. Start talking. Memory activates automatically.

Release maintainers should build the ZIP with
`python3 scripts/build_release_archive.py --output /tmp/cortex.zip`; never
archive a raw working directory containing ignored local settings.

### Claude Code — Full Support (new in v4)

**Minimal setup (no hooks):**
1. Copy the contents of `claude-code/INSTRUCTIONS.md` into your `~/.claude/CLAUDE.md` (global) or project-level `CLAUDE.md`
2. `mkdir -p ~/Documents/Claude/memory`
3. Start a new Claude Code session. Done.

**With hooks (recommended):**
1. Do the minimal setup above
2. Add the hooks from `claude-code/hooks.json` to your `~/.claude/settings.json`
3. Hooks make auto-recall more reliable by feeding data at session init

### Codex — Shared-memory adapter

1. Resolve the existing Cortex root with `python3 hooks/session_start.py --print-root`
2. Add that exact path to Codex's sandbox writable roots
3. Enable this repository's portable plugin and trust its SessionStart hook
4. Invoke `$recall`, `$remember`, `$note`, or any other generated workflow

See `docs/CODEX_SETUP.md` for the permission snippet, supported roles, and
explicit degradation rules.

### ChatGPT Work — Local or cloud

- **Local Work:** install the portable plugin. Its bundled stdio MCP bridge
  resolves the same Cortex root and uses the same shared CLI for writes.
- **Cloud/web Work:** connect that bridge through OpenAI's Secure MCP Tunnel;
  cloud Work cannot directly read files on your Mac.

See `docs/CHATGPT_WORK_SETUP.md` for the complete trust boundary, one-time
tunnel setup, tool list, and public-deployment requirements.

#### Install from a shared GitHub checkout

Prerequisites: ChatGPT desktop, `git`, `uv`, and Codex CLI.

```bash
git clone https://github.com/BrightWayAI/claude-cortex.git
cd claude-cortex
codex plugin marketplace add "$PWD"
codex plugin add cortex@cortex-local
```

Restart ChatGPT desktop and open a new **Local Work** chat. Type `@Cortex` or
ask naturally. Plugins with bundled MCP are desktop-only when distributed
through a GitHub workspace marketplace.

#### Choose the memory location on first run

New users can configure Cortex in either of two equivalent ways:

```bash
python3 scripts/configure_cortex.py \
  --config-root "$HOME/Documents/Cortex"
```

Or, after installing the plugin:

```text
@Cortex configure my memory at ~/Documents/Cortex. Show me the exact path and
ask for confirmation before creating anything.
```

This writes one vendor-neutral pointer file at `~/.cortex/config-root` and
creates only missing starter files under `<config-root>/memory/`. It never
overwrites existing memory. If the pointer already targets another location,
switching requires a separate explicit confirmation.

Existing Claude users normally do **not** configure a second location. Check
the root Claude already resolves, then install Cortex for Work:

```bash
python3 hooks/session_start.py --print-root
```

No additional ChatGPT-specific config file is required. `.cortex.json` is an
optional project-level behavior override, not the global memory pointer.

#### Share across a ChatGPT organization

A workspace administrator can import this GitHub repository from **Admin →
Plugins → Add → Import marketplace**. Use the repository URL, leave Path
blank, and pin a release tag or full commit SHA. The admin then chooses which
roles may install Cortex. Each member configures a separate local memory root;
the repository distributes plugin code, never anyone's memory files.

See `docs/ORGANIZATION_DISTRIBUTION.md` for the administrator and member
checklists.

---

## How It Works

### Always-On Behaviors (no commands needed)

#### Auto-Recall
At conversation start, Claude reads your user profile and checks for attention items. If you have overdue P0s or stale threads, it tells you. If you mention a known project, it loads context automatically. All silently — no "loading memory..." preamble.

#### Passive Observation
During every conversation, Claude watches for:
- **Corrections** ("don't do that", "I prefer this") — highest priority, always saved
- **Preferences** (communication style, tool choices, working patterns)
- **Domain knowledge** (how your company works, industry terms, constraints)
- **Relationship context** (who's who, who owns what)

It never interrupts to capture these. It adapts in real-time and saves at conversation end.

#### Contextual Recall
When you mention a project, person, or topic with memory, Claude surfaces relevant knowledge naturally — "Heads up, Acme's procurement requires 3 vendor quotes" — without dumping a formal recall block.

#### Auto-Commit
On supported Claude hosts, Cortex can attempt a silent end-of-session commit.
Session-end hooks are best effort, so important knowledge should still be
saved with `/remember`. Codex and ChatGPT Work require an explicit, previewed
commit; they do not claim guaranteed background saving.

### The User Profile

New in v4: a `user` node that accumulates knowledge about **you**:

- Communication preferences (terse vs. detailed, options vs. decisions)
- Working style (batching, cadence, delegation patterns)
- Corrections (things Claude should never do again)
- Domain expertise (what you know, what needs explaining)
- Relationships (who you work with, their roles)
- Tool preferences (which platforms you use)

This is what makes Claude feel like it "knows" you. It carries across all projects and both platforms.

---

## Explicit Commands

All commands from v3 still work. v4 added subagent invocation; v4.2 adds shared-config commands and closing rituals.

### Memory commands

| Command | What it does |
|---------|-------------|
| `/remember` | Full session commit with confirmation |
| `/recall [project?]` | Dashboard (no arg) or specific project context |
| `/learn [node] [type?] [content]` | Alias for `/remember --knowledge <type>` |
| `/note [node] [content]` | Alias for `/remember --quick` |
| `/search [query]` | Cross-project search (delegates to `memory-librarian` for broad queries) |
| `/forget [node]` | Archive a project |
| `/cleanup` | Memory health audit |

`/review` (weekly synthesis digest) and `/timeline` (chronological activity) moved to the `briefing` plugin (Today's Brief) on 2026-09-15, as part of consolidating every "what's going on" surface into one plugin.

### Shared-config commands (v4.2+)

These write to canonical files under the resolved `<config-root>` that
compatible BrightWayAI plugins can read. Capture once, all compatible plugins
benefit.

| Command | What it does |
|---------|-------------|
| `/setup-identity` | Captures name, company, role, primary tools, and communication defaults in the resolved config root. |

Voice capture lives in Comms Desk's `/setup-voice` — the interview writes to the
same Cortex-owned canonical file (`<config-root>/memory/me/voice.md`), but the
command itself is owned and shipped by the Comms Desk plugin.

### Closing rituals (v4.2+)

| Command | What it does |
|---------|-------------|
| `/end-day` | 5-min daily close — recap today, prompt for reflection, commit learnings to memory, optionally pre-stage tomorrow via `plan-tomorrow`. |
| `/end-week` | 15-min Friday close — runs `note-taker` (mode: transcript) for uncaptured commitments, `/cleanup` for memory hygiene, briefing's `/review` for synthesis (skipped if briefing isn't installed), prompts for weekly reflection, optionally pre-stages Monday's outreach via `weekly-outreach`. |

### Always-On Skill

| Skill | Behavior |
|-------|----------|
| `observe` | Runs silently in every conversation. No trigger needed. Captures preferences, corrections, and domain knowledge. |

### Auto-firing Skills

Commands also fire from natural language:

| Trigger | Skill |
|---------|-------|
| "save this", wrapping up, farewell | `remember` (auto-commit) |
| Conversation start, greeting, "catch me up" | `recall` (auto-recall) |
| "TIL", "gotcha:", "the trick is...", "I was wrong about" | `learn` |
| "note that", "jot down", "quick note" | `note` |
| "any gotchas with", "what's blocked", "how does X work" | `search` |
| "we're done with X", "archive X" | `forget` |
| "clean up memory", "what's stale" | `cleanup` |
| "set up my identity", "configure my profile across plugins" | `setup-identity` |
| "set up my voice", "update my writing voice" | Comms Desk's `setup-voice` |
| "wrapping up", "calling it a day", "end of day" | `end-day` |
| "Friday wrap-up", "close out the week", "end of week" | `end-week` |

---

## Subagents (v4.1+)

Cortex ships specialist subagents that handle heavy memory work off the main conversation thread. Other plugins (or Cortex's own commands) can delegate to them via the Task tool.

| Subagent | Purpose | Used by |
|---|---|---|
| **`memory-librarian`** | Search, synthesize, and deduplicate across all working-memory files for broad / cross-cutting queries. Returns a structured Summary / Source Entries / Open Threads / Confidence response. Read-only. | `/search` (cortex) for broad queries; any other skill that needs cross-node memory synthesis |
| **`gap-researcher`** | Finds thin, stale, contradictory, or orphaned memory and researches a fill with ≥2 independent sources. | `/research-gaps`, optionally `/end-week` |
| **`note-taker`** | Mode-dispatched nightly mining agent — `mode: transcript` (configured note-source providers), `mode: conversation` (other Cowork sessions), `mode: activity` (CRM/email/calendar events). Returns a commitments delta and a learnings delta per mode. Merges the former `transcript-reviewer` + `conversation-miner` + `activity-miner` agents (2026-09-15). | `/listen` (nightly), `/end-day` full mode, `/end-week` |

Subagents inherit parent tools at runtime, so they work with whichever connectors (Granola, CRM, etc.) the user has connected. Tool allowlists are kept tight where possible (e.g., memory-librarian uses only Read/Grep/Glob).

To invoke a subagent directly via the Task tool (Cowork or Claude Code):

```
Use the Task tool with subagent_type="memory-librarian"
and pass: query="[your question]"
```

The agents are registered automatically when Cortex is installed — they appear in Claude's `subagent_type` enum alongside built-in agents.

---

## What Gets Captured

### Project State (what changed)
- Decisions made and reasoning
- Open threads with staleness tracking
- Blockers and who/what is blocking
- Artifacts created (docs, decks, proposals)
- Next actions (P0/P1/P2/WAITING)

### Knowledge (what was learned)
| Type | Example |
|------|---------|
| **Insight** | "Churn is an onboarding problem, not a product problem" |
| **Lesson** | "Same-day proposals fail. 48-hour tailored decks close 3x better" |
| **Model** | "Their approval: dept head → finance → VP → procurement" |
| **Gotcha** | "Fiscal year starts April, not January — adjust all budget timing" |
| **Recipe** | "For exec buy-in: lead with their metric, show the gap, propose one action" |
| **Correction** | "Not price-sensitive — they need ROI framing for internal approval" |

### User Observations (who you are)
| Type | Example |
|------|---------|
| **Preference** | "Prefers terse responses — told Claude to stop summarizing" |
| **Correction** | "Don't add emojis to professional communications" |
| **Pattern** | "Starts mornings with email triage, then deep work blocks" |
| **Domain** | "Deep expertise in AI go-to-market — skip 101 explanations" |
| **Relationship** | "Reports to [Name] (CEO), weekly 1:1s on Mondays" |

---

## Per-Project Config

Control behavior per project via `.cortex.json` in the project root:

```json
{
  "node": "client:acme-corp",
  "capture": "aggressive",
  "auto_recall": true,
  "auto_commit": true,
  "observe": true
}
```

| Capture Level | Behavior |
|--------------|----------|
| `"aggressive"` | Capture everything. Use for high-value client work. |
| `"normal"` | Standard capture. Default. |
| `"minimal"` | Only explicit commands. No auto behaviors. |

See `cortex.config.md` for the full spec.

---

## Memory Storage

Memory lives at `<config-root>/memory/`, resolved through the vendor-neutral
pointer chain. The same root is shared by Cowork, Claude Code, and Codex.

```
<config-root>/memory/
├── DASHBOARD.md          ← Master index
├── user.md               ← Your profile (NEW in v4)
├── archive/              ← Archived nodes
├── client/
│   ├── acme-corp.md
│   └── northstar.md
├── bizdev/
│   └── partnerships.md
├── strategy/
│   └── q2-growth.md
├── hiring.md
└── brand.md
```

All files are plain markdown. Human-readable. Editable. Backupable.

### Config-root precedence

Every host resolves the same location in this order:

1. Project/workflow explicit override (`config_root` in `.cortex.json`)
2. `CORTEX_CONFIG_ROOT`
3. `~/.cortex/config-root` — recommended persistent, cross-host pointer
4. `~/Documents/.claude-plugin-config-root` — legacy Claude pointer
5. `~/Documents/Claude` — backward-compatible default

For most users, `~/.cortex/config-root` is the only configuration file needed.
It contains one absolute path on one line. Prefer
`scripts/configure_cortex.py` over editing it manually because the command
validates unsafe paths and initializes the directory safely.

---

## Node Conventions

Use kebab-case. Organize however fits your work:

| Pattern | Example |
|---------|---------|
| Client work | `client:acme-corp` |
| Business dev | `bizdev:stripe-partnership` |
| Internal ops | `company-ops`, `hiring`, `finance` |
| Strategy | `strategy:q2-growth` |
| Products | `onboarding-program`, `crm-dashboard` |
| Learning | `learning:sales-ops` |
| Domain | `domain:healthcare-compliance` |
| Infrastructure | `infra:data-pipeline` |
| Personal | `personal` |
| **User profile** | `user` (auto-managed) |

---

## Platform Comparison

| Feature | Cowork | Claude Code | Codex |
|---------|--------|-------------|-------|
| Plugin system | Native | Via CLAUDE.md | Portable Agent Plugin |
| Auto-recall | Skill auto-fire | Instructions + hooks | Bounded SessionStart hook |
| Auto-commit | Best-effort skill | Best-effort instruction | Explicit `$remember` |
| Passive adaptation | Skill | Instructions | Current-session skill behavior |
| User profile | Shared | Shared | Shared |
| Explicit workflows | 29 skills/commands | 9 slash adapters + skills | 29 `$skill` adapters |
| Memory files | Shared root | Shared root | Shared root |

All three hosts can read and write the same memory files. Cross-host writes
coordinate through the same lock and atomic-write implementation.

---

## Changelog

See `CHANGELOG.md` for the full version-by-version history (this section only tracks major milestones).

### v4.15.0 — ChatGPT Work and organization distribution
- **One installable plugin**: 29 bundled workflows plus a bounded local MCP bridge
- **First-run location setup**: a confirmation-gated command writes the shared vendor-neutral pointer and initializes an empty Cortex safely
- **Organization sharing**: repository marketplace support for ChatGPT workspace GitHub import and direct local installation
- **Per-user privacy**: plugin code is shared; each person's Markdown memory remains in their own configured folder
- **Release hardening**: synchronized manifests, private-cache ignores, a shareable-surface privacy audit, and 156 fixture-only tests

### v4.14.0 — Portability and stabilization refactor
- **Host-neutral core**: a single canonical storage/workflow contract (`references/core-contract.md`) and capability matrix (`references/capability-matrix.md`), so Claude and Codex share one memory without duplicating behavior
- **Real locking and atomic writes**: memory mutation now goes through tested code (`scripts/cortex_cli.py` + `scripts/lib/`), not just careful prose — closes a real concurrent-write risk now that memory can be driven by more than one AI session at once
- **Deterministic index/hot-cache generation**: `/reindex` and the rolling 7-day `hot.md` cache are backed by fixture-tested code, not model-executed algorithms
- **`.claude/commands/` de-drifted**: mechanically regenerated from the canonical `commands/*.md` files (was hand-duplicated and had silently fallen behind)
- **Codex adapter**: `AGENTS.md`, 26 generated Agent Skills, portable `plugin.json`, bounded session-start recall, and four read-only role bindings
- 135 unit/integration tests; `python3 scripts/check_repo.py` validates taxonomy drift, broken references, skill/command coverage, both adapter families, and version agreement

### v4.0.0 — Always-On Learning
- **Passive observation engine**: Claude silently learns about you during every conversation
- **User profile node**: Persistent model of preferences, corrections, patterns, domain expertise
- **Auto-recall**: Context loads at conversation start without commands
- **Auto-commit**: Knowledge saves at conversation end without commands
- **Contextual recall**: Relevant knowledge surfaces mid-conversation on mention
- **Claude Code support**: Full integration via CLAUDE.md instructions and optional hooks
- **Per-project config**: `.cortex.json` for per-directory behavior control
- **Silent mode**: Auto-triggered commits produce no output (unless creating new nodes)
- **The learning loop**: Every conversation makes the next one better

### v3.0.0
- File-based storage under the resolved `<config-root>/memory/`
- Two-tier structure: DASHBOARD.md + individual node files
- Dynamic directory creation from node prefixes
- Archive support

### v2.2.0
- Business-operator friendly language and examples
- Strategy/planning node types

### v2.1.0
- Knowledge-first redesign with six knowledge types
- Added `/learn` and `/note` for quick capture
- `/review` weekly digest

### v2.0.0
- Added `/search`, `/forget`, `/timeline`, `/cleanup`
- Priority system, staleness tracking, cross-project signals

### v1.0.0
- Initial release with `/remember` and `/recall`
