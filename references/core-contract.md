# Cortex core contract (host-neutral)

> This is the single canonical definition of the Cortex storage and workflow
> contract. Every command, skill, agent, and future host adapter (Claude
> today; Codex and others later) must point here instead of re-describing
> these rules. If a host-specific doc and this file disagree, this file wins
> and the host doc is stale and should be fixed.
>
> This document describes *behavior*, not *implementation*. It uses no
> vendor, model, or tool names. Host adapters translate the capabilities
> named in §11 into whatever tools their platform provides.

## 1. Config-root resolution

Cortex resolves a single **config-root** directory at the start of any
workflow that touches memory. Precedence, highest first:

1. **Explicit override** — a `config_root` key in a project-local
   `.cortex.json`, or an explicit argument passed to a workflow. Used for
   fixtures, tests, and rare per-project pinning.
2. **`CORTEX_CONFIG_ROOT` environment variable** — the primary
   vendor-neutral mechanism. Preferred for sandboxed or ephemeral hosts that
   can set environment variables before filesystem access to the real home
   directory is negotiated.
3. **`~/.cortex/config-root`** — a new, vendor-neutral pointer *file*
   (plain text, single line, an absolute path or `~`-prefixed path). Lives
   outside `~/Documents` deliberately, since `~/Documents` reads as a
   single vendor's document folder, not a neutral config location. This is
   the default cross-host source of truth once more than one host is in
   use — every host reads the same file.
4. **`~/Documents/.claude-plugin-config-root`** — the legacy pointer file.
   Read only if #2 and #3 are both absent. Kept indefinitely for backward
   compatibility; never removed, never required to be migrated.
5. **`~/cortex-root`** — the cloud-first default, used only if it was
   materialized by `cortex_cli.py bootstrap` (it contains `.cortex-repos.json`).
   Lets a cloud session or scheduled task resolve without a host-specific
   pointer.
6. **`~/Documents/Claude`** — the backward-compatible default, used only if
   none of the above resolve.

Resolution rules:

- `~` and platform home paths are expanded deterministically before any
  other processing.
- A resolved path must be absolute. A resolver that produces a relative
  path, an empty string, an unresolved environment variable reference, or a
  filesystem root (`/`, `C:\`, home directory itself with no subpath) is a
  **resolution error**, not a valid config-root — never used as a
  destructive-operation target.
- Resolution errors are returned as structured data (what was tried, what
  was found, what precedence step failed) so a host adapter can render an
  actionable message. Resolution never silently falls back past a
  malformed higher-precedence source to a lower one — a malformed pointer
  is an error, not a skip.
- `<config-root>` in every other Cortex document refers to the directory
  produced by this resolution. `<memory-root>` is always
  `<config-root>/memory/`.

## 2. Memory directory layout

```
<config-root>/
├── archive/                 # immutable nightly source archive (see references/archive-layout.md)
└── memory/
    ├── index.md             # auto-maintained catalog, zero-LLM, deterministic
    ├── hot.md               # rolling 7-day context cache
    ├── DASHBOARD.md         # master index, living summaries, P0 list
    ├── me/                  # private current-user scope; never shared remotely
    │   ├── identity.md
    │   ├── voice.md
    │   ├── user.md
    │   ├── reflections.md
    │   └── autonomy-acknowledgment.json
    ├── log.md               # unified append-only operation chronicle
    ├── triage-log.md        # append-only commit-triage log
    ├── .decay-config.md     # decay thresholds
    ├── person/<slug>.md
    ├── client/<slug>.md
    ├── company/<slug>.md
    ├── topic/<slug>.md
    ├── workstream/<slug>.md
    ├── bizdev/<slug>.md
    ├── infra/<slug>.md
    ├── team/<slug>.md       # internal team entity nodes, not private profiles
    ├── proposals/<actor-id>/# sanitized, append-only shared-write intake
    ├── archive/<slug>.md    # archived nodes (memory-level; distinct from <config-root>/archive/)
    ├── <name>.md            # unprefixed root-domain nodes
    └── staged/
        ├── commit-drafts/
        ├── research-drafts/
        ├── heartbeat-drafts/
        ├── queues/
        └── skip-logs/
```

Full node-type decision rules live in `references/node-taxonomy.md`; this
contract does not duplicate them.

Everything under `me/` is private to the current actor. Existing client,
person, workstream, bizdev, team, and domain nodes remain directly under
`memory/`; there is deliberately no physical `memory/org/` wrapper. Everything
outside `me/`, derived caches, and explicitly ignored operational state is
potentially shareable and must follow §11A before multiple people write.

## 3. Node identifiers and file mapping

- A node ID is `<type>/<slug>` (e.g. `person/sarah-chen`, `client/acme`) or
  an unprefixed `<slug>` for root-domain nodes (e.g. `hiring`).
- Mapping is mechanical: `<type>/<slug>` → `memory/<type>/<slug>.md`;
  unprefixed `<slug>` → `memory/<slug>.md`.
- Slugs are kebab-case. Name collisions are resolved by appending a
  disambiguating hint (e.g. `sarah-chen-acme`), never by overwriting an
  existing file.
- **Legacy colon-prefixed node references** (`person:sarah-chen` as used in
  reference syntax throughout pre-v4.10 docs and possibly in older prose
  entries) are semantically identical to `person/sarah-chen` and must
  always resolve to the same file. A reader encountering a literal
  colon-separated filename (`person:sarah-chen.md`, if one is ever found)
  treats it as equivalent to `person/sarah-chen.md` — never as a distinct
  node. No mass migration of existing files is required or performed by
  this contract; this is a read-time equivalence rule only.

## 4. Canonical knowledge types

Seven types, defined once here (see `CLAUDE.md` for the full description
table, kept in sync with this list):

`INSIGHT`, `LESSON`, `MODEL`, `GOTCHA`, `RECIPE`, `CORRECTION`, `DECISION`.

- `GOTCHA` and `RECIPE` decay 1.5× slower than default (see
  `references/decay-model.md`).
- `CORRECTION` never decays.
- `DECISION` requires: what, when, why, affected entities, revisit-when
  trigger, status.
- **Legacy compatibility:** a short-lived v4.13 attempt consolidated these
  into four types (`INSIGHT`/`DECISION`/`GOTCHA`/`CORRECTION`, with
  `[mental-model]`/`[recipe]` tags on `INSIGHT`). That consolidation is
  superseded by this contract — the seven-type list above is canonical for
  all new writes. Entries already written in the four-type form remain
  valid and readable; no migration is forced or performed.

## 5. User-observation types

Stored only in `user.md`: `PREFERENCE`, `CORRECTION`, `PATTERN`, `MODEL`,
`PEOPLE`. Distinct namespace from knowledge types — `MODEL` here means
"domain/company knowledge about the user's world," not the knowledge-type
`MODEL`.

## 6. Node sections

**Required** on every node file: a top-level `# <node-id>` heading, a
`> Last updated: YYYY-MM-DD` line, and a `## Summary` section (may be
empty on a brand-new node).

**Optional**, present only when relevant content exists: `## Knowledge`
(with `### Insights` / `### Lessons` / `### Models` / `### Recipes` /
`### Decisions` / `### Gotchas` / `### Corrections` subsections),
`## People`, `## Open threads`, `## Changelog`, `## Linked entities`,
`## Demoted knowledge`, `## Archive`.

A node is never required to carry a section it has no content for. Tooling
must not treat an absent optional section as malformed.

## 7. Wikilink rules

Every reference to another entity uses `[[<type>/<slug>]]` if a node file
exists for that entity. If no node file exists yet, use the bare name and
increment the mention counter for graduation tracking. Full detail and the
graduation thresholds live in `CLAUDE.md` (Person pages / Wikilink rule)
and are not duplicated here. Bare square brackets (`[Name]`, `[role]`) in
templates are placeholder syntax, never output syntax.

## 8. Timestamps and timezone

All dates are `YYYY-MM-DD`. A date is stamped using the **local timezone
of the machine/process performing the write** — there is no fixed
canonical timezone. This matches current behavior and requires no
migration. A future multi-host setup where writes from different
timezones need reconciling is out of scope for this contract; if that
becomes a real problem, it should be solved by adding an explicit UTC
timestamp alongside the display date, not by changing the display
convention.

## 9. Append-only vs. replaceable sections

- **Append-only, never rewritten in place:** `## Changelog`, `memory/log.md`,
  `triage-log.md`, everything under `<config-root>/archive/` (immutable
  after write), `skip-logs/`.
- **Replaced wholesale each session:** `## Summary` (living summary),
  `hot.md`, `DASHBOARD.md`, `index.md` (regenerated deterministically, not
  hand-edited).
- **Additive with occasional demotion:** `## Knowledge` subsections — new
  entries are appended; existing entries move to `## Demoted knowledge`
  rather than being deleted (see decay model and concept-drift rules in
  `commands/remember.md` §B/§C).
- Everything else (Notes, free-form context) is user-owned prose and may be
  edited freely by the user; automated workflows only append to it.

## 10. Staging and archive behavior

- `<config-root>/archive/` (source layer) is immutable once written per
  day; only `/listen --rewrite` may overwrite a day, and that is a rare,
  explicit operation. See `references/archive-layout.md`.
- `memory/staged/` holds in-flight proposals (commit-drafts,
  research-drafts, heartbeat-drafts) that a human or a merge workflow must
  explicitly accept before they become active memory. Nothing reads staged
  content as authoritative.
- `memory/archive/<slug>.md` holds archived *nodes* (any type), moved there
  by `/forget --archive`. Archiving is reversible by moving the file back;
  it is not a delete.

## 11. Locking and atomic-write requirements

Every workflow that creates, appends, edits, overwrites, moves, archives,
merges, or deletes memory content **must** use the shared locking and
atomic-write utilities implemented at `scripts/lib/locking.py`,
`scripts/lib/atomic_write.py`, `scripts/lib/node_paths.py`, and
`scripts/lib/sections.py` (fixture-tested in `tests/test_locking.py`,
`tests/test_atomic_write.py`, `tests/test_node_paths.py`,
`tests/test_sections.py`). As of this writing these utilities exist and are
tested but are not yet called from any command or skill — wiring existing
mutating workflows to use them is remaining work, not yet done. Requirements
binding on any implementation:

- Acquire a lock scoped to the memory root (or a documented finer scope)
  before the first read-modify-write step, and release it on success,
  failure, interruption, or early exit — never leave a stale lock as the
  normal outcome of a crash.
  - Stale-lock recovery (a lock left behind by a killed or crashed process)
    must be handled automatically by the lock protocol itself — e.g. a
    timeout plus ownership/liveness check — not by requiring a human to
    manually delete lock files.
- Locks must coordinate across processes and hosts via the shared
  filesystem — never via in-memory state private to one host session.
- Writes are atomic: write to a temporary file in the same filesystem,
  then rename over the target. A reader must never observe a partially
  written file.
- A prose instruction telling a model to "check for a lock file" is not a
  substitute for this — it must be enforced by deterministic code once
  that code exists.

## 11A. Authorship and collaborative writes

Single-actor installs may continue writing approved changes through the shared
CLI under the memory lock. Every new durable knowledge entry includes a stable
`[by:<actor-id>]` tag, where `actor-id` comes from
`memory/me/identity.md`. Existing untagged entries remain valid.

Once more than one actor writes to the same shared memory remote, model-driven
work must not edit shared nodes directly. Each actor first writes a sanitized,
cited, append-only proposal beneath
`memory/proposals/<actor-id>/<YYYY-MM-DD>/<proposal-id>.md`. A designated merge
workflow validates provenance and base revision, acquires the shared memory lock,
applies an accepted proposal atomically, and records acceptance or conflict without
rewriting the proposal. Raw connector payloads and private `me/` content never enter
the shared proposal tree.

Conflict and supersession behavior, proposal schema, privacy rules, and the
single-writer-to-multi-writer transition are defined in
`references/shared-memory-writes.md`.

## 11B. Distributed sync (cloud-first)

GitHub is the source of truth; every host (cloud session, scheduled task, Mac)
holds a synced copy. A config-root is two git checkouts:

- `<root>/memory/` — the shared/org memory repo.
- `<root>/.private/` — the per-user private repo holding `me/`, `staged/`,
  `archive/` (index + closures only; raw payloads never leave the run that
  pulled them), `briefs/`, `plugins/`.
- Directory symlinks (`memory/me`, `memory/staged`, `archive`, `briefs`,
  `plugins`) point into `.private/`, so every path in §2 resolves unchanged.
  The org repo ignores `/me` and `/staged` and must never track a symlink.

Binding rules, implemented in `scripts/lib/repo_sync.py` and exposed as
`cortex_cli.py bootstrap` / `sync`:

- **Materialize:** a workflow on a host with no resolved root runs
  `bootstrap` (idempotent clone/adopt, fast-forward pull, link creation,
  derived `index.md`/`hot.md` regeneration) before anything else.
- **Pull before write, push after write.** `.lock` stays per-checkout; it does
  not span machines. Cross-machine safety is the git protocol.
- **Never force-push.** A rejected push is fetched, rebased, retried (3x).
- **Conflicts never touch main.** On a rebase conflict the rebase is aborted,
  local commits are pushed to `conflict/<host>/<timestamp>`, the checkout
  realigns to origin, and the run reports the conflict in its health line.
  Facts are superseded (§12), not overwritten.
- **Privacy guard.** `sync` refuses to push the org repo if it tracks any path
  under `me|staged|archive|briefs|plugins` or any symlink.
- **Never silent.** Every sync writes `<root>/.sync-status.json` and appends to
  `staged/sync-log.md`; non-zero exit on any failure.
- Append-only files (`staged/listen-health.md`, `staged/sync-log.md`) use
  `merge=union` via `.gitattributes`.

## 12. Conflict and concept-drift behavior

Before writing a new `INSIGHT`, `LESSON`, `MODEL`, or `GOTCHA` entry, check
whether it contradicts, supersedes, or refines an existing entry of the
same type on the target node. `RECIPE` entries are additive and skip this
check. `DECISION` entries supersede through their own later-decision path.
`CORRECTION` entries encode their own supersede relationship explicitly
and skip the check. Full procedure: `commands/remember.md` §C.2.

## 13. Privacy classification

Two tiers:

- **Sensitive** — `<config-root>/archive/` (raw calendar/inbox/Slack/drive/
  transcript content), everything under `memory/me/`, everything under
  `memory/staged/` (drafts not yet
  reviewed), and any node content that itself contains PII (emails, phone
  numbers, addresses) copied from a sensitive source. This tier should
  never be assumed safe to sync to a third-party service, paste into an
  external tool, or commit to a shared/public git remote.
- **Normal** — everything else in `memory/` once written: node summaries,
  knowledge entries, changelogs, the index and hot-cache. Still personal
  data, but distilled and user-reviewed rather than raw external-source
  content.

This classification is descriptive, not enforced by code today. Phase 8 of
the portability refactor uses it to correct security documentation; a
future phase may enforce it (e.g. refusing to include `archive/` content in
a payload sent to `web.search` or `subagent.delegate`).

## 14. Backward compatibility guarantees

- Legacy colon-prefixed node references resolve identically to slash-path
  references (§3).
- Legacy four-type knowledge entries remain readable (§4).
- Knowledge entries without `[by:<actor-id>]` remain readable and are attributed
  to `legacy-unknown`; no retroactive rewrite is required.
- The legacy `~/Documents/.claude-plugin-config-root` pointer continues to
  work indefinitely (§1).
- A legacy, user-owned `memory/CLAUDE.md` may remain the canonical
  memory-specific instruction file. Setup may create a short
  `memory/AGENTS.md` forwarding shim when Codex import tooling expects that
  filename; it must not copy, rename, or rewrite the legacy file.
- The `~/Documents/Claude` default continues to resolve for installations
  with no pointer at all (§1).
- No existing node identifier changes the file it maps to as a result of
  this contract.

## 15. Capability names

Canonical logical capabilities referenced by workflows (full matrix with
per-host implementation and degrade behavior: Phase 6 of the portability
refactor, not yet written as of this document):

```
filesystem.read
filesystem.write
filesystem.atomic_replace
filesystem.lock
user.confirm
web.search
connector.calendar.read
connector.mail.read
connector.crm.write
connector.transcripts.read
subagent.delegate
artifact.read
artifact.update
scheduler.register
```

Canonical workflow specs (skills, `commands/*.md`) reference only these
names. Host adapters translate a capability into the concrete tool, MCP
server, or API call available on that host, and document what happens
when an optional capability is unavailable.

## Architecture decision record

**Decision:** Cortex's storage and workflow contract is defined once, in
this file, using no vendor/model/tool-specific language, and is layered
beneath host adapters (Claude commands/skills/hooks today, a future Codex
adapter, others later).

**Why host-neutral:** the repository was accumulating behavioral drift
because the same rules were being restated — slightly differently each
time — in `CLAUDE.md`, individual command files, and duplicated
`.claude/commands/` copies. A second host (Codex) was about to be added on
top of that drift, which would have doubled the restatement surface. A
single contract removes the restatement: hosts consume it, they don't
re-derive it.

**How future adapters should consume it:** an adapter (a) resolves
`<config-root>` per §1 using whatever mechanism the host offers for
environment variables and file reads, (b) maps its own tool names onto the
capability list in §15, (c) points its durable-instruction entrypoint
(`CLAUDE.md` for Claude, `AGENTS.md` for Codex) at this file rather than
duplicating it, and (d) implements its own lifecycle glue (hooks, slash
commands, skill invocation syntax) without touching the schema, taxonomy,
locking, or resolution rules defined here. If an adapter needs to deviate
from this contract for a host limitation, that deviation is documented in
the adapter's own file as an explicit exception, not silently folded back
into this contract.
