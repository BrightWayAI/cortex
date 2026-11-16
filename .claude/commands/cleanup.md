---
description: Run maintenance on working memory. Consolidates old log entries, detects stale threads, identifies orphaned nodes, and reports on memory health. Run periodically to keep memory sharp and within limits.
---

# /cleanup $ARGUMENTS

You are performing maintenance on Claude's working memory. This keeps the memory graph healthy and within size limits.

---

## Step 1 — Audit current memory

### How to Audit

**Before auditing**: Check if `<config-root>/memory/` is accessible (resolve `<config-root>` per `references/core-contract.md` §1).
- **Cowork**: Use `mcp__cowork__request_cowork_directory(path=<config-root>)` to request access. Wait for the user to approve.
- **Claude Code**: The directory is accessible directly via the filesystem.

If the directory cannot be accessed, explain that memory cannot be audited without this folder and stop.

1. Read `<config-root>/memory/DASHBOARD.md`
2. List all `.md` files in `memory/` and subdirectories (excluding DASHBOARD.md and archive/)
3. For each file, check: last modified date, number of LOG entries, staleness of open threads
4. Compare dashboard entries against actual files (detect orphaned dashboard entries or node files missing from dashboard)
5. Check `memory/archive/` for any archived nodes

Scan all memory entries and compile:

```
## Memory Health Report — [today's date]

### Size
- Total entries: [count]
- By type: [SUMMARY: x] [LOG: x] [PEOPLE: x] [SIGNAL: x] [ARCHIVED: x]
- Estimated usage: [rough assessment: light / moderate / heavy / near limit]

### Nodes
- Active nodes: [count] (updated within 7 days)
- Warm nodes: [count] (8-14 days)
- Cooling nodes: [count] (15-30 days)
- Dormant nodes: [count] (30+ days)
- Archived nodes: [count]
```

---

## Step 2 — Identify maintenance opportunities

Check for each of these issues:

### A. Log consolidation candidates
Nodes with 10+ LOG entries. Oldest entries can be consolidated:
```
Consolidation candidates:
- [node-id]: [count] log entries. Oldest: [date]. Suggest archiving entries before [date].
```

### B. Stale threads
Open threads that have been open for 3+ sessions or 14+ days without mention:
```
Stale threads:
- [node-id]: "[thread description]" — open since [date], last mentioned [date]
- ...
```

### C. Dormant nodes
Nodes with no activity in 30+ days:
```
Dormant nodes (consider archiving):
- [node-id]: Last active [date]. Summary: [1-line]
- ...
```

### D. Orphaned people
People entries that reference nodes that no longer exist or are archived:
```
Orphaned people entries:
- [Name] references [node-id] which is [archived/missing]
```

### E. Expired signals
SIGNAL entries older than 30 days that were never acted on:
```
Expired signals:
- [signal description] — from [date], between [node] and [node]
```

### F. Duplicate or conflicting entries
Any nodes with multiple SUMMARY entries (should only ever have one), or people listed multiple times:
```
Duplicates found:
- [node-id]: [count] SUMMARY entries (should be 1)
- [Name]: appears [count] times in people index
```

### G. Orphan / isolated notes (v4.2+)

Scan all memory nodes for files that are floating off the map. A node is "isolated" when ALL of:

- **No incoming links** — no other node file mentions this node's id (e.g., as `[client/acme]`, `[strategy/q2-growth]`, or a SIGNAL pointing here)
- **No outgoing links** — this node file doesn't reference any other node id
- **Last updated more than 30 days ago** (use the `> Last updated:` line at the top of the file, or `mtime` as fallback)

For each isolated node, suggest one of three dispositions:

- **Archive** — recommended if the node has < 5 entries total and no open threads
- **Merge into <candidate>** — recommended if a sibling node covers the same topic; suggest by low-cost/fast-tier semantic match (Claude adapter: Haiku) against active node summaries (1 call, ~$0.01)
- **Keep as standalone** — accept the orphan if it's a genuine one-off (a reference file, a personal log)

Format:

```
Isolated notes (no inbound or outbound links, untouched 30+ days):
- [node-id]: [last updated date], [entry count] entries — suggest: [archive | merge into <candidate> | keep]
```

Also reflect these in DASHBOARD.md's `## Isolated Notes` section so the user sees them on next conversation start.

### H. Person-page maintenance (v4.2+, deepened in v4.4)

Check each file in `memory/person/`. Load thresholds from `<config-root>/memory/.decay-config.md`:

- `person_threshold_cooling` (default 90)
- `person_threshold_dormant` (default 180)
- `person_threshold_archive` (default 365)

For each page:

- **Cooling pages** — `person_threshold_cooling ≤ days_since_last_contact < person_threshold_dormant` AND < 2 recall-counter increments in last 90 days → flag in DASHBOARD's Active People table with `[cooling]` badge. No action proposed.
- **Dormant pages** — `person_threshold_dormant ≤ days_since_last_contact < person_threshold_archive` AND no recalls in 180+ days → propose `archive`.
- **Cold-archive candidates** — `days_since_last_contact ≥ person_threshold_archive` AND no recalls in 180+ days → propose `archive` with a stronger recommendation flag.
- **Stale Recent interactions** — entries older than 90 days that haven't been moved to the page's `## Archive (>90 days)` section → propose `trim` (move them to the page's archive section).
- **Person pages with no Linked entities and < 2 Recent interactions** — likely premature graduation. Surface for review with `keep with note` or `archive` options.

Format:

```
Person-page maintenance:
- person:[slug]: [state] (last contact <N>d ago, <M> recalls in 180d) — suggest: [archive | trim | keep with note]
```

**On accept of `archive`**: move `<config-root>/memory/person/<slug>.md` to `<config-root>/memory/person/archive/<slug>.md`. Remove the row from DASHBOARD's Active People table. The recall counter entry for the slug is preserved (so if the user later interacts with this person again, `/recall person:<slug>` finds the archived page and can offer to unarchive).

`/recall person:<slug>` on an archived page renders the content but flags it: `**[archived person page]** — moved to archive <date>. To bring back: edit <slug>'s file or run \`/recall person:<slug> --unarchive\`.`

### I. Dormant knowledge entries (v4.4+)

Load thresholds from `<config-root>/memory/.decay-config.md`. Scan all active node files (skip `## Demoted knowledge` sections — those entries are already user-demoted).

For each knowledge entry, compute `age = today - [confirmed:...]` (default to original commit date if tag absent). Cross-reference with the entry's type modifier and the node's `decay_profile` front-matter to get the effective threshold (see `references/decay-model.md`).

Surface:

- **Dormant entries** (`threshold_dormant ≤ age < threshold_cold`) — list them grouped by node, sorted by age desc, capped at 15 per cleanup run. Per-entry suggestion: `rehearse | demote | archive`.
- **Cold entries** (`age ≥ threshold_cold`) — list separately with a stronger flag. Suggest `demote` or `archive` by default.

Format:

```
Dormant knowledge:
- [node-id] INSIGHT (2025-09-12, confirmed:2025-09-12): "<first 80 chars>..." [<N>d dormant] — suggest: rehearse | demote | archive
- ...

Cold knowledge:
- [node-id] MODEL (2024-11-03, confirmed:2024-11-03): "<first 80 chars>..." [<N>d cold] — suggest: demote | archive
- ...
```

CORRECTIONs are excluded from this audit (immune to decay).

**On accept of `rehearse`**: tag the entry for the next `/rehearse` batch (this defers the decision rather than acting now). Logged to `<config-root>/memory/staged/queues/rehearse.md` so `/rehearse` picks them up.

**On accept of `demote`**: move entry to the node's `## Demoted knowledge` section with metadata trail.

**On accept of `archive`**: there's no entry-level archive directory; this is equivalent to `demote` plus a note that the user chose archive. (Entry stays readable, just out of active rotation.)

### K. Structurally-isolated nodes (v4.11+)

Find nodes that are graph-orphans: zero outbound `[[wikilinks]]` AND zero inbound wikilinks (no other node references them).

Procedure:

1. For each node file in `memory/` (excluding `archive/`, `staged/`, and system files `DASHBOARD.md` / `CLAUDE.md` / `index.md` / `hot.md` / `log.md` / `user.md`):
   - Count outbound `[[` occurrences in the file's content.
   - Count inbound: grep for the file's slug across all other node files; count `[[<slug>]]` or `[[<type>/<slug>]]` references.
2. Flag any node with outbound = 0 AND inbound = 0 as **isolated**.
3. For each isolated node, surface for review:

```
ISOLATED NODE: <node-path>
  Last updated: <date>
  Content length: <N> lines
  Type (per taxonomy): <inferred type>

  Possible reasons:
  - Created via plain-text /note with no entity references
  - Orphaned from a removed parent node
  - Solo scratch note that doesn't need connections
  - Should be relinked or merged into a richer node

  (r)elink — run /relink-memory scoped to this node; try to convert plain-text mentions
  (a)rchive — move to memory/archive/
  (m)erge — merge into an existing node (prompts for target)
  (k)eep — leave isolated (legitimate solo note); suppress for 90 days
  (s)kip — defer
```

4. **On accept `relink`:** invoke `/relink-memory --scope <node-path>` to attempt wikilink conversion within just this file. If still isolated after relink (no entities matched any existing nodes), prompt for `archive` or `keep`.

5. **On accept `archive`:** move the file to `memory/archive/<original-path>`. Update DASHBOARD if it referenced this node.

6. **On accept `merge`:** prompt for target node. Move the content into the target's appropriate sections (knowledge entries go to Knowledge; recent activity goes to Changelog; etc.). Delete the original file.

7. **On accept `keep`:** append to `<config-root>/memory/staged/skip-logs/cleanup-isolated.md` with reason field; suppress for 90 days.

8. **Cap:** 10 isolated nodes per `/cleanup` run (avoid fatigue). Re-surface remaining at the next run.

Different from existing section G (Orphan / isolated notes) which checks dashboard-presence and recency. Section K checks **graph connectivity** specifically — is this node part of the knowledge network at all?

System files (DASHBOARD, CLAUDE.md, etc.) are always excluded — they're structural, not knowledge nodes.

---

### J. DECISION revisit-trigger scan (v4.9+)

Scan all active DECISION entries across nodes. For each:

1. Read the entry's `Revisit when:` field. If "n/a" or empty → skip.
2. Determine whether the trigger condition appears to have fired. Cheap-tier (low-cost/fast-tier model, Claude adapter: Haiku) classifier:
   - Read the trigger text + last 30 days of activity in the same node + recent log.md entries
   - Output: `{triggered: true|false, reason: '...'}`
3. If `triggered: true`, surface for re-evaluation:

```
DECISION potentially needs revisit: [[<node>]] · "<decision>"
  Triggered by: <reason — what activity matches the revisit-when trigger>
  Original reasoning: <why>
  Original date: <YYYY-MM-DD>

  (a)ccept — mark Status: revisit-now (surfaces in next /recall on this node)
  (n)o-change — note the trigger was false-positive; suppress for 90 days
  (u)pdate-now — re-confirm or supersede the DECISION inline
  (s)kip
```

4. **On accept (revisit-now):** edit the DECISION's `Status:` field to `revisit-now`. Add a note to the entry: "Trigger fired YYYY-MM-DD: <reason>." Surfaces with extra prominence in `/recall` until user updates.

5. **On no-change:** log to `<config-root>/memory/staged/skip-logs/decision-revisit.md` with reason; suppress this (decision, trigger) pair for 90 days.

6. **On update-now:** chain into `/remember` with the original DECISION pre-loaded; user can supersede with a new DECISION or re-confirm with an updated `Revisit when` trigger.

7. **On skip:** no action; this DECISION will be re-checked at next `/cleanup`.

Cap: 10 DECISIONs per `/cleanup` run. Run too many at once and the user fatigues. Prioritize by trigger-confidence (the classifier's `reason` strength) and recency of trigger activity.

---

### L.0 — First-run baseline-stamp (v4.12.3+)

Before running Section L (or K) on a system that pre-dates v4.12.0, check for a baseline marker:

```
marker = <config-root>/memory/staged/skip-logs/dashboard-baseline-acknowledged
```

If marker does NOT exist (first /cleanup run after v4.12.3 install), surface BEFORE Section L:

> "DASHBOARD has <N> lines without provenance comments (predates the v4.12.0 provenance addition). Section L would flag all of them as 'missing provenance' candidates and surface 15 per run — multi-run migration grind for existing users.
>
> Three options:
>   (b)aseline-stamp ALL existing lines as `<!-- by:manual @ <today> -->` to defer them for 60 days. Section L will then surface only lines that actually need attention going forward. Recommended.
>   (w)alk individually as Section L normally does — 15 lines per /cleanup run, ~<N/15> runs to clear backlog.
>   (s)kip Section L entirely for this run; baseline decision deferred.
>
> Choose: b / w / s"

On `b`: walk DASHBOARD.md, append `<!-- by:manual @ <today_local> -->` to every non-empty line that lacks a provenance comment. Write the marker file. Proceed to Section L (will surface only the rare line that has expired provenance from an explicit owning command).

On `w`: skip the baseline; proceed to Section L which walks lines as documented below.

On `s`: skip Section L entirely; re-prompt next run.

**Same pattern for Section K** (graph-isolation, v4.11+). First /cleanup run after v4.12.3 install on legacy memory will surface hundreds of structurally-isolated nodes. Marker: `<config-root>/memory/staged/skip-logs/section-k-baseline-acknowledged`. Same three-option prompt: `(b)aseline-defer` writes per-slug entries to `staged/skip-logs/sectionK-defer.md` with `resurface-after: <today + 90d>`; `(w)alk` per normal Section K behavior; `(s)kip` for this run.

---

### L. DASHBOARD line staleness via provenance (v4.12.0+)

Scan `<config-root>/memory/DASHBOARD.md` for stale lines using the provenance markers written by `/remember` Step 3 (and ideally by every command that writes DASHBOARD entries). Each line should carry `<!-- by:<command> @ <YYYY-MM-DD> -->`. Stale signals:

1. **Owning-command hasn't refreshed in N days.** Default thresholds:
   - Lines from auto-mining commands (`/listen`, `/morning`, `/end-day`, `/sweep`): stale at 7 days
   - Lines from user-driven commands (`/remember`, `/note`, `/learn`): stale at 30 days
   - Lines marked `manual`: stale at 60 days (manual = the user wrote it; expect slower refresh)
   - Override per-line via inline comment `<!-- by:<cmd> @ <date> · stale-after:<days> -->`

2. **Missing provenance.** Any DASHBOARD line without a `<!-- by: -->` comment is itself a drift signal — it predates v4.12.0 or was written by a command not yet updated to emit provenance.

3. **Orphaned references.** Lines that reference a node id that no longer exists (e.g., DASHBOARD says `[[bizdev:foo-corp]]` but the file was archived or renamed). Cross-check against `memory/index.md`.

Surface:

```
DASHBOARD has <N> potentially stale lines:

  STALE (owning command hasn't refreshed in N+ days):
  - "studio.co intro angle..." <!-- by:/listen @ 2026-05-12 --> · 16 days old
  - "Draft Sylvia outreach" <!-- by:/remember @ 2026-04-22 --> · 36 days old

  MISSING PROVENANCE (pre-v4.12 or unattributed):
  - "WAITING:Caitlyn — Logo permission" (no by-tag)

  ORPHANED REFERENCES:
  - "[[bizdev/foo-corp]]: ..." — node no longer exists

For each line:
  (k)eep — update provenance to `manual @ <today>` to suppress staleness for 60 days
  (u)pdate-now — invoke owning command (or /remember if manual) to refresh
  (d)elete — remove the line entirely
  (s)kip — re-check next /cleanup
```

Cap: 15 stale lines per `/cleanup` run. Prioritize by age (oldest first) then by line type (P0/WAITING items rise above informational entries).

**On `k` (keep):** rewrite the line's provenance to `<!-- by:manual @ <today> -->`. Effectively re-confirms it for 60 days.

**On `u` (update-now):** if owning command is a chained command (`/listen`, `/morning`, `/end-day`), surface "this updates on next scheduled run — keep waiting? (y/n)" since manually firing those is heavyweight. If owning command is light (`/remember`, `/note`), offer to invoke inline.

**On `d` (delete):** remove the line. Log to `staged/skip-logs/dashboard-prune.md` with the deleted text + date.

**On `s` (skip):** no action; log to `<config-root>/memory/staged/skip-logs/dashboard-prune.md` with `(line-content, skip-date, reason-code)` where `reason-code` is a **constrained enum (v4.12.3+)**:

- `not-stale` — user judges the line still relevant despite the age
- `intentional-archive` — keeping for historical visibility
- `pending-review` — defer to next run
- `unclear` — generic skip

**Free-form text is NOT accepted in this log** — same privacy reasoning as the `schema-validation.md` enum constraint shipped in relationships v0.2.2: free-form rationale captures PII ("Sarah is going through a divorce, kept the line as historical context") which then sits in a screenshot-able log. If the user wants to capture nuanced reasoning, put it in the DASHBOARD line itself or the related node's Notes section.

### L.1 — Skip-log enum for `sync-linked.md` (v4.12.3+)

Same constraint applies to `<config-root>/memory/staged/skip-logs/sync-linked.md` (written by `/sync-linked-entities` on user `(s)kip` action). The previously-free-form `reason` field is now constrained to the same enum: `not-stale | intentional-archive | pending-review | unclear`. Existing entries with free-form text continue to parse; new entries use the enum.

This section closes the dogfooding gap surfaced 2026-05-28: DASHBOARD accumulates stale lines because nothing actively detects them. Provenance + this scan turns staleness from invisible drift into a routine `/cleanup` review.

---

### M. Cap violations (v4.16+, Nucleus Operating Model Refactor Phase 2 step 2.3)

```
python3 scripts/cortex_cli.py check-caps --memory-root <config-root>/memory
```

Read-only, deterministic (`scripts/lib/cap_check.py` — same check `/reindex` Step 2.5 runs). Warns at 150 / fails at 200 lines for any node's `## Current state` section (nodes not yet restructured are skipped — no `## Current state` heading, no cap applies); warns at 200 lines for always-loaded files (`hot.md`, `CLAUDE.md`, `user.md`).

This is the only section that **fails loudly** rather than proposing an action — cap violations aren't a maintenance suggestion, they're a broken invariant `/recall`'s default load boundary depends on. Include the raw output in the Memory Health Report under "Cap violations" verbatim (or "Cap violations: none" when clean, so `/diagnose` can key off a stable line). This section does not offer a menu action in Step 3 — a FAIL is reported and the user decides how to trim it (there's no safe automatic edit for "make this summary shorter" without losing meaning).

---

## Step 3 — Propose actions (autonomy-aware in v4.7.2+)

**Consult autonomy mode** per `references/autonomy-policy.md` (Per-command confirmation modes). Default for `/cleanup`: `suggest`.

- **Mode = `auto`**: execute all proposed actions without the gate. Print the actions inline as they happen ("Consolidating [node-id]... Escalating [thread]..."). This is for trusting users running scheduled cleanups.
- **Mode = `suggest`** (default): standard menu prompt as below; user picks `all` / numbered / `none`.
- **Mode = `confirm`**: walk one action at a time; each gets a per-item yes/no/skip prompt instead of the batch menu.

Default prompt (suggest mode):

```
## Recommended Actions

1. **Consolidate** [node-id] logs: Archive [count] entries from [date range] into 1 archive entry
2. **Escalate** stale thread in [node-id]: "[thread]" → move to SUMMARY as a blocker
3. **Archive** dormant node [node-id]: No activity in [count] days
4. **Clean** orphaned people entry for [Name]
5. **Expire** signal between [node] and [node] from [date]
6. **Deduplicate** [specifics]

Execute all? Or select specific actions? (all / 1,3,5 / none)
```

---

## Step 4 — Execute approved actions

For each approved action, use `scripts/cortex_cli.py` (see `references/core-contract.md` §11 — every one of these acquires the lock and writes atomically in one call; do not hand-edit files for these actions):
- **Consolidate**: write the archive entry with `append-section`/`replace-section`, then remove the individual old log lines with `replace-section` on `## Changelog`.
- **Escalate**: `replace-section`/`append-section` to move the thread into `## Summary` with a `[STALE]` tag.
- **Archive**: same primitive as `/forget --archive` — `move-node` into `archive/`, then update DASHBOARD.md.
- **Clean**: `replace-section` to remove or update orphaned entries.
- **Expire**: `replace-section` to delete old signal entries.
- **Deduplicate**: `replace-section` to merge duplicate entries, keeping the most recent.

Report what was done after each action.

---

## Step 4.5 — Refresh memory index (v4.5+)

If any approved actions in Step 4 changed memory (demotions, archives, consolidations, edits), invoke the `indexer` skill to regenerate `<config-root>/memory/index.md`.

Deterministic and zero-LLM — runs in seconds. See `skills/indexer/SKILL.md` and `commands/reindex.md`.

If no actions touched memory in Step 4, skip this step.

---

## Step 4.7 — Log to chronicle (v4.7.1+, centralized in v4.7.2+)

Invoke the `log-writer` skill (see `skills/log-writer/SKILL.md`) with:
- **op_name:** `cleanup`
- **summary:** `<A> actions taken. Section H: <person-pages-archived>. Section I: <dormant-entries-deferred> deferred, <demoted> demoted.`

---

## Step 5 — Post-cleanup summary

```
## Cleanup Complete

- Entries before: [count] → After: [count] (freed [count])
- Actions taken: [count]
- Memory health: [assessment]

Next recommended cleanup: [suggest a date based on activity level]
```

---

## Behavior notes

- Always show the audit report before taking any action
- Never auto-execute — always get user approval for destructive changes
- Default to archive over delete for any content removal
- If memory is already clean and healthy, say so and skip the action proposals
- Suggest running `/cleanup` monthly for moderate users, weekly for heavy users
