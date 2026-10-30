---
description: Optional 2-minute close (v4.16+ — demoted from required). The nightly `/listen` + `/morning` now handle overnight mining and tomorrow's brief seeding on their own; run this only when you want the deeper end-of-day pass — full transcript/inbox/Slack mining, a longitudinal reflections.md entry, or a HubSpot catch-all log. Opens with a per-source consent + cost gate (Today's Brief required & first), mines the brief artifact (task/outreach actions → memory write-backs + suppression learning into surfacing-prefs.md), surfaces the day's learnings as a plain-language narrative then proposes memories AND forgettings side by side, walks proposals batchably, proposes tomorrow's priorities/outreach individually, asks "anything else," offers to log anything to HubSpot, and captures a reflection appended to both the brief markdown and a longitudinal reflections.md store. Quick mode by default; --full adds transcript/inbox/Slack mining.
disable-model-invocation: true
---

# /end-day

**Optional as of v4.16.0.** `/listen` (nightly) + `/morning` (the required daily touch) now cover overnight mining and tomorrow's brief seeding — see `/morning` Step 4.6. Run `/end-day` when you want the deeper pass: full-mode transcript/inbox/Slack mining, the longitudinal `reflections.md` entry, or the HubSpot catch-all log (Step 4.7). It won't auto-trigger from natural language; invoke it explicitly with `/end-day`.

End-of-day closing chain. Reads the day, captures commitments, updates memory with cost discipline, and pre-stages tomorrow so the morning has a working surface waiting.

This rewrite (v4.2) ties together the second-brain v2 phases — inbox triage, transcript review, person-page graduation via cheap-tier commit triage, briefing pre-stage. Each step has a user gate so the chain never blocks on something the user wants to defer.

Run once per work day, ideally 4-6pm. If a downstream plugin isn't installed (e.g., `briefing` not yet adopted), the chain skips that step silently and continues.

---

## Pre-chain — Resolve config root and identity

**Cloud-first (v4.29+):** if no config-root resolves, run `python3 scripts/cortex_cli.py bootstrap --print-env` and use the printed root; on a synced checkout, run `cortex_cli.py sync` once here (pull) before reading anything.

Resolve `<config-root>` through the canonical precedence chain in
`references/core-contract.md` §1. Read `<config-root>/memory/me/identity.md` for
time zone (defines "today" / "tomorrow").

Determine `today_local` and `tomorrow_local` (next business day: Mon-Thu → tomorrow; Fri → Monday; Sat/Sun → Monday).

---

## Pre-chain B — One-time Scope migration (v4.3+)

The mining layer (Steps 2a / 2b below) routes extracted content to nodes using a Scope convention on each domain-shaped node. This migration runs **once** to adopt the convention on existing nodes. After it completes, a marker file at `<config-root>/memory/.scope-migration-done` prevents re-prompting.

Skip this block if `<config-root>/memory/.scope-migration-done` exists. Otherwise:

### A — Detect domain-shaped nodes

Scan `<config-root>/memory/`. A node is "domain-shaped" if ALL of:

- It's a `.md` file at root level (e.g., `<config-root>/memory/<name>.md`), OR a `.md` file in a non-reserved subdirectory
- Its filename is NOT one of: `user.md`, `DASHBOARD.md`, `triage-log.md`, `CLAUDE.md`
- Its containing directory is NOT one of: `client/`, `bizdev/`, `person/`, `archive/` (these are project / prospect / person / archive — not domain)
- Its YAML front-matter (if present) does NOT set `type: project` (engagement state, handled separately)

The detection is purely structural. The plugin does not know or care what specific domains the user has — it works against whatever nodes exist.

### B — Synthesize a Scope draft per detected node

For each detected node, read its current content and produce a draft Scope section pre-filled from what's already in the file:

- **Topics:** lowercased keywords inferred from existing knowledge-entry tags, recurring nouns in the Summary, and recurring section headers
- **Aliases:** alternate names mentioned in PEOPLE entries or Summary (e.g., a node named `studio.md` whose Summary references "Learning Production System" gets that as an alias)
- **What goes here:** one-line synthesis from the Summary section
- **What does NOT go here:** left empty in the draft — this is the most useful field but requires user judgment

### C — Per-node confirmation

Present each draft to the user, one node at a time:

> "Node `<name>`. Proposed Scope section:
>
> [draft]
>
> (a)ccept / (e)dit / (s)kip"

- `accept` → insert the Scope section as the first section of the node file (above existing Summary). Idempotent: if a Scope section already exists, replace it; if not, insert.
- `edit` → drop into edit mode. User edits inline, then accept.
- `skip` → skip this node. It can still receive routed content from miners, but routing accuracy drops without the Scope hint. The migration will not re-prompt for this node — user can re-run `/end-day` with `--rerun-scope-migration` later to revisit.

### D — Offer new domain nodes (open-ended)

After all detected nodes are processed, ask once:

> "Want to create any new domain nodes now? (open-ended — list them comma-separated, or skip)"

For each name the user lists:
1. Confirm node ID (kebab-case, lowercased)
2. Walk through the same Scope interview (topics / aliases / what goes here / what does NOT go here — all four asked, no draft to pre-fill since the node is new)
3. Create the node file at `<config-root>/memory/<name>.md` with the Scope section, an empty Summary placeholder, and standard sections (Knowledge / People / Changelog / Open Threads / Next Actions)

The plugin does not suggest names. The user drives the list.

### E — Mark complete

Write `<config-root>/memory/.scope-migration-done` with the ISO timestamp and the list of nodes processed (one line per node, `<status> <node-id>` — accepted, edited, skipped, or created). This file is the only check that prevents re-prompting on subsequent `/end-day` runs.

If the user runs `/end-day --rerun-scope-migration`, delete the marker and re-run this block.

### F — On failure

If Pre-chain B errors partway through (e.g., a node file is unreadable), log the partial state to `<config-root>/memory/.scope-migration-partial` and prompt the user: "Scope migration hit an error on `<node>`. Resume later via `/end-day --rerun-scope-migration`? Or continue with the rest of `/end-day` now using whatever Scope sections were captured?" Default: continue.

---

## Pre-chain C — Staged-substrates migration (v4.8.1+)

One-time migration of pre-v4.8.1 staged dotfile paths into the unified `memory/staged/` tree. Gated by `<config-root>/memory/.migration-staged-reorg-done` marker.

Logic:
1. Check whether `<config-root>/memory/.migration-staged-reorg-done` exists.
2. If exists → skip silently. Continue to Modes.
3. If absent → invoke `/migrate-staged-substrates`. The command is idempotent; on completion it writes the marker and any future `/end-day` skips this Pre-chain.

The migration is non-blocking. If it partially fails, log the error and continue to Modes — `/end-day`'s primary work is unaffected by staged-path layout.

See `references/migrations.md` for the pattern and `commands/migrate-staged-substrates.md` for the migration spec.

---

## Modes (v4.6+) — quick close (default) vs `--full`

`/end-day` runs in **quick mode by default** as of cortex v4.6.0. Real-user feedback: the previous 8-step chain felt like overhead on days when there were no transcripts, no inbox volume, and nothing to triage. The quick chain is the actionable spine:

- **Quick mode** (default): Step 3 (auto-commit), Step 4 (reflection), Step 5 (pre-stage brief), Step 5.5 (refresh memory index), Step 6 (close). Typically 30s – 3 min.
- **Full mode** (`/end-day --full`): adds Step 1 (inbox triage), Step 2 (transcript review), Step 2a (mining of non-transcript sources), Step 2b (unified review gate). Use when you actually have transcripts, heavy inbox volume, or a Slack-heavy day to mine. Typically 10-15 min.

**Auto-offer rule.** In quick mode, before Step 3, do a fast pre-check:
- Count transcripts dated today in known note sources (per `/setup-sources`).
- Count unread inbox threads where the user is in To/Cc from today.

If transcripts ≥ 2 OR inbox ≥ 5, surface a one-line prompt: "Heads up — you have <N> transcripts and <M> inbox threads from today. Want the full close (`/end-day --full`)? (default: no)" — default `no` after ~5s. If user says yes, restart in `--full` mode.

If transcripts and inbox are both low, **don't ask** — just run the quick chain. Don't introduce a prompt when there's nothing to prompt about.

---

## Step 0.7 — Source review & cost gate (B.1 — v4.13+)

Before reading anything, present **one lightweight batch card** (not five sequential yes/no prompts) listing the sources to be reviewed, each with a checkbox (default on/off per config) and an **approximate cost shown before running**.

Sources, in priority order:

1. **Today's Brief responses** — *required input, always first, never a checkbox.* Read the brief state (tasks, annotations, outreach actions) via the Step 2c.0 chain. Cheapest and highest-signal source.
2. **Transcripts** (Granola/Gemini) — today's meetings. (full mode)
3. **Email** (Gmail) — today's threads where the user is a participant. (full mode)
4. **Slack** — configured channels/DMs since yesterday. (full mode)
5. **CRM** (HubSpot) — today's deal/task/activity changes. (full / note-taker mode: activity)

**Cost estimate model.** For each source, estimate `volume × per-unit token cost` and convert to a rough dollar figure, e.g. *"Transcripts: 2 meetings (~14k tokens) ≈ USD 0.05"*, *"Email: 23 threads, ~4 likely-relevant ≈ USD 0.03"*. Show a **running total** at the bottom. Do a fast pre-count (the same counts the quick-mode auto-offer uses) to fill in volumes; if a count is unavailable, show "~" and estimate conservatively.

> Note: figures below use `USD` rather than a literal `$0` prefix on purpose — when this command is invoked with arguments, a bare `$0` in the doc gets mangled by args interpolation (renders `≈ --full.05` instead of `≈ USD 0.05`). Keep the `USD` form, or escape the dollar sign, in any example.

Card shape:

```
Tonight's close will review these sources. Estimated cost shown before running.

  [✓] Today's Brief responses   — required, always first      ~USD 0.00
  [✓] Transcripts               — 2 meetings (~14k tok)       ≈ USD 0.05
  [✓] Email                     — 23 threads, ~4 relevant     ≈ USD 0.03
  [ ] Slack                     — 3 channels since yesterday  ≈ USD 0.02
  [✓] CRM                       — today's deal/task changes   ≈ USD 0.01
  ─────────────────────────────────────────────────────────────────
  Running total (checked)                                     ≈ USD 0.09

  [R] Review all   ·   [C] Let me choose (toggle rows)   ·   [G] Go
```

- **Quick mode:** only "Today's Brief responses" + "CRM" (note-taker mode: activity) are in scope; the card is trivially small. Show it only if there's more than the brief to review — otherwise skip straight to Step 2c.
- **Full mode:** show the full card. Default checkbox states come from `<config-root>/plugins/cortex.user-context.md` `end_day.sources:` if set, else all-on except Slack.
- Respect the **autonomy slider** (`references/autonomy.md`): in `auto` mode, skip the card and review the default-on set; in `suggest`/`confirm`, show it.

Whatever the user unchecks is **skipped and logged** so Step 6's summary is honest about what was and wasn't reviewed. Record the skipped set in memory for the close summary ("Reviewed: brief, transcripts, CRM. Skipped: email, Slack.").

> Design note: this is one card with checkboxes + costs + a single confirm. Never gate each source behind its own prompt.

---

## Step 1 — Inbox triage for tomorrow (skipped in quick mode)

**Quick mode: skipped.** Inbox triage runs the next morning via `/brief` Section 2 anyway; running it again here is redundant for most users.

**Full mode only:** the original Step 1 behavior follows.

**Goal:** surface threads that will need a reply tomorrow so they can populate tomorrow's brief.

Behavior:

- If the user has the `inbox-triage` plugin installed and its `/triage-inbox` command is available → invoke it. The skill returns the top 3-7 Needs-reply-today threads (the classifier doesn't distinguish "today" from "tomorrow" — it returns "needs a reply in the next 24h," which from a 5pm vantage means tomorrow morning).
- If `inbox-triage` is NOT installed → fall back to a lighter Gmail search: messages received today where the user is in To/Cc and hasn't replied. Cap at 7.
- Either way, **stash the result** in memory for Step 5's pre-stage call. Don't render it to the user yet.

### User gate after Step 1

> "Tomorrow's inbox triage shows [N] threads. Want to review them now, or wait until morning when the brief surfaces them?"

- "Review now" → render the list and pause for user reactions before proceeding to Step 2
- "Wait" (default if no response within ~10s in interactive mode) → continue to Step 2

---

## Step 2 — Transcript review (skipped in quick mode; full mode only — v4.3+: two streams)

**Goal:** surface (a) commitments the user made today that aren't already in CRM tasks or cortex memory, and (b) learnings from the day's transcripts that aren't already captured in node content.

Read `<config-root>/plugins/cortex.note-sources.md` to get the configured note-sources list. Filter to enabled sources whose scope (global or `project:<node-id>`) matches the run's relevant nodes (sources scoped to a project node are included if that project has meetings in today's window).

If no sources are configured → skip this step with a one-line note: "No note sources configured. Run `/setup-sources` to enable transcript mining." Proceed to Step 2a.

Invoke `note-taker` with `mode: "transcript"`:
- `time_window: 1 day`
- `note_sources: [<filtered list>]`
- `node_inventory`, `node_summaries`, `dashboard_snapshot` (built from `<config-root>/memory/`)
- `crm_task_snapshot`: current HubSpot tasks owned by the user

The agent returns two streams: `commitments_delta` and `learnings_delta`.

### Commitments stream — user gate (unchanged from pre-v4.3)

For each item in `commitments_delta`, prompt per item:

> "Convert this to a CRM task / cortex P0 / both / skip?"

- **CRM task** → create via HubSpot MCP, due tomorrow (or a user-specified date), assigned to the user
- **Cortex P0** → append to the relevant project node's `## Next Actions` as `[P0]`
- **Both** → both side-effects
- **Skip** → no action, no log

If the delta is empty ("Nothing missing — all commitments already tracked"), confirm and continue. Don't pad.

### Learnings stream — DEFERRED to Step 2b unified gate

The `learnings_delta` stream is NOT reviewed here. Hold the proposals; they get merged with `note-taker`'s `mode: conversation` and `mode: activity` output in Step 2a, then reviewed once in Step 2b. This avoids review-fatigue and lets cross-source dedup happen across modes.

---

## Step 2a — Parallel mining of non-transcript sources (skipped in quick mode; full mode only — v4.3+)

**Goal:** mine the day's other Cowork sessions and CRM/email/calendar events for learnings that aren't yet in node content.

Run `note-taker` twice **in parallel**, once per mode, via the `subagent.delegate` capability (see `references/capability-matrix.md`) — one chat message, multiple delegation calls:

1. `note-taker` with `mode: "conversation"`:
   - `time_window: 1 day`
   - `current_session_id`: the session running `/end-day` (exclude from mining)
   - `node_inventory`, `node_summaries`, `dashboard_snapshot`
   - `user_email`, `user_local_tz` (from identity.md)

2. `note-taker` with `mode: "activity"`:
   - `time_window: 1 day`
   - `node_inventory`, `node_summaries`, `dashboard_snapshot`
   - `user_email`, `user_local_tz`

`code-miner` is deferred to a later cortex version (not built in v4.3).

Each mode runs its own cheap-tier triage gate first. Modes that triage-skip return empty and cost ~nothing.

### Merge step

Combine three sources of proposals:

- `note-taker`'s (`mode: transcript`) `learnings_delta` from Step 2
- `note-taker`'s (`mode: conversation`) `learnings_delta`
- `note-taker`'s (`mode: activity`) `learnings_delta`

Apply cross-mode dedup:

- For each proposal in the `mode: conversation` stream, check against `mode: transcript`'s stream — if a proposal on the same target_node has > 70% content overlap, drop the conversation version (transcript is the source of record).
- For each proposal in `mode: activity`'s stream, do the same against `mode: transcript`.
- Within each remaining set, dedup against existing node content (n-gram > 70% overlap → drop).

Group surviving proposals by `target_node`. Sort within each group by `confidence DESC, update_type` (corrections first, then decisions/insights, then gotchas/models, then relationship-context).

---

## Step 2b — Unified review gate (skipped in quick mode; full mode only — v4.3+)

Present the merged proposals once. Format:

```
Today's mining surfaced [N] proposed updates across [K] nodes:

  ▸ <node-id> (<count>)
      [<update_type>, <confidence>] <content>
        — <source>, <ref>
      [<update_type>, <confidence>] <content>
        — <source>, <ref>
        cross-ref → <other-node-id>: <one-line content of the linked proposal>
      ...

  ▸ <other-node-id> (<count>)
      ...

Review:
  (a)ccept all
  (s)elect per node — show one node at a time, accept/edit/skip per item
  (e)dit each — walk every item individually
  (h)igh-confidence only — show only high-confidence items, skip the rest
  (k)skip all
```

### Auto-expand cross-refs

When rendering a proposal that has `cross_ref: [<id>]`, render the linked proposal's `content` inline as a "cross-ref →" line under it (see format above). The user reviews both in context without having to jump.

### High-confidence toggle behavior

If the user picks `(h)`, render only proposals with `confidence: high`. The rest are deferred (logged as "deferred — review tomorrow" in the dismissal log — they re-surface in tomorrow's mining if still applicable; they don't get auto-committed and they don't permanently disappear).

### New-node-creation confirmation

If any proposal has `node_type: new` (with a `new_node_suggestion`), surface a dedicated confirmation BEFORE accepting any content into it:

> "Create new node `<id>`? Type: <type>. Scope: <one-line>. (y / edit-scope / n)"

If `y` → create the node file with a Scope section (interview the user inline for the 4 Scope fields), then accept the proposal into it.
If `edit-scope` → walk the 4-field Scope interview before creating.
If `n` → drop all proposals targeting that new node (or, on a per-proposal basis, ask whether to re-route each one to an existing node).

This makes taxonomy growth explicit rather than silent.

### Dismissal log

Skipped proposals (whether from `(k)skip all`, per-item skip, or implicit when `(h)high-confidence` was chosen) are logged to `<config-root>/memory/dismissed-proposals.log` (append-only), keyed by a hash of `(source.note_id or session_id or event_ref) + content` so they don't re-surface tomorrow. Format:

```
<ISO timestamp>  <proposal_id>  <target_node>  <update_type>  <source_kind>:<ref-hash>  <one-line content>
```

Miners read this log at the top of every run and skip any proposal whose source-ref + content hash matches a dismissed entry within the last 7 days. (After 7 days, re-surfacing is permitted — the user may have changed their mind.)

### Accepted proposals → Step 3

Accepted proposals (and edits) are passed forward to Step 3 as additional input alongside the current session's content.

---

## Step 2c — Mine the brief artifact (B.1 source #1 — ALWAYS runs, both modes — v4.13+)

The brief is the user's most explicit daily signal, yet historically it was the one source `/end-day` never mined. This step closes that loop. It runs in **quick mode and full mode** — the brief is the required first source from Step 0.7.

**Idempotency with `/listen` (v4.27+).** Before reading anything, check whether `<config-root>/briefs/<today_local>.state.processed` already exists for today. If it does, `/listen` Step 1.5 already ran its inference pass for today's not-yet-existent brief (unlikely — `/listen` targets yesterday by default) or a prior `/end-day` run today already processed this exact date; either way, skip Step 2c.1–2c.3's write-backs and log "already processed today — skipping explicit write-backs" then continue to Step 2c.4. Otherwise, after Step 2c.1–2c.3 complete, **write** `<config-root>/briefs/<today_local>.state.processed` with the current ISO timestamp — this is what tells a subsequent `/listen --remine <today_local>` (run against today's date rather than the usual yesterday) to skip explicit write-backs and run its inference pass only.

### Step 2c.0 — Read the brief state

The brief's action state lives in the artifact's `localStorage`. Cowork exposes **no widget-context handle for persisted artifacts** (`read_widget_context` only works for in-conversation widgets), so `localStorage` alone is invisible to the close — without a workaround, Done/Skip/Not-important clicks are lost and completed items resurface in the next brief. Read the state through this fallback chain, **stopping at the first source that yields a blob**:

1. **State-mirror file (primary — D2a).** Read `<config-root>/briefs/<today_local>.state.json`. The briefing ≥0.6.1 artifact auto-mirrors its full localStorage blob here on every action — but **only when `/brief` resolved a filesystem MCP write tool at render time** and declared it in the artifact's `mcp_tools` allowlist (the Cowork sandbox rejects undeclared tools; there is no built-in file access). Where no such tool is connected, this file exists only if the user pasted a sync blob earlier today (paste path, below). This is the canonical read path. Sanity-check freshness: if the file's `last_interaction_at` is from a prior day, treat it as absent.
2. **Widget context (legacy).** If no state file exists, try `mcp__cowork__read_widget_context(artifact_id="todays-brief")` for the blob at key `brief-<today_local>`. Works only where in-conversation widget context is exposed; usually empty for the persisted artifact.
3. **Paste path (Step 2c.0p — try BEFORE the multi-select gate).** Ask once: "I couldn't read today's brief state. Open Today's Brief, click **🔄 Sync brief state** (bottom of the artifact — it copies your action state), and paste it here. Or say 'skip' and I'll walk the list with you." If the user pastes a blob: validate it parses as a JSON object (tolerate surrounding whitespace/code fences), **write it verbatim to `<config-root>/briefs/<today_local>.state.json`**, then proceed exactly as if source 1 succeeded. This is one click + one paste versus re-stating every item by hand.
4. **Explicit fallback gate (Step 2c.0a).** If the user skips the paste (or the paste doesn't parse twice), run the fallback gate below — do **not** silently skip. Silently skipping is what let completed items resurface.

Canonical v0.7.0 blob shape (see `briefing/commands/brief.md` localStorage contract; 0.4.x-0.6.0 blobs still read fine, missing `reflection`/`return_on` treated as absent):

```json
{
  "tasks":            { "task-123": { "action": "done|delegate|skip|not_important", "detail": "", "priority": "P0|P1|P2", "reprioritized": true, "ts": "", "name": "" } },
  "annotations":      { "task-123": "free text", "inbox-...": "..." },
  "outreach_actions": { "contact-1": { "name": "", "action": "sent|skip|nudge|let_go|booked|dead", "bucket": "", "signal": "", "value_add": "", "detail": "", "ts": "" } },
  "last_interaction_at": "ISO8601"
}
```

Back-compat: a `tasks_checked: {id: bool}` map (v0.4.x) maps each `true` → `{action: "done"}`. A `tasks` entry may carry a `reprioritized: true` + `priority` with **no `action`** (priority changed, no disposition) — tolerate a missing `action` (route it via Step 2c.1a). Never fabricate brief actions.

### Step 2c.0a — Fallback gate (D2c — fires only when state is unreadable AND the paste path was skipped)

When no source yields a blob, **ask exactly one multi-select question** rather than skipping the brief:

> "I couldn't read today's brief state automatically. Which of today's surfaced items did you complete / delegate / kill?"

Seed the options from **today's brief task list** (read the priorities from `<config-root>/briefs/<today_local>.md` or the `<today_local>.seed.json` that generated it — the same list rendered into the artifact). Let the user tag each selected item done / delegated / skipped / not-important (a second quick prompt per selected item, or free-text). Route the answers through the **normal Step 2c.1 / 2c.2 write-backs** exactly as if they'd come from the blob. This makes the manual reconciliation Zach did by hand on 7/2 a spec'd step, not improvisation.

If the brief task list itself is unavailable (no markdown, no seed), only then skip Step 2c with a one-line honest note ("brief state unreadable and no task list on disk — skipped").

### Step 2c.1 — Write back task actions (per surfacing-prefs taxonomy)

For each entry in `tasks`, apply the action's write-back (taxonomy is canonical in `<config-root>/memory/me/surfacing-prefs.md` "Action taxonomy"):

| Action | Write-back |
|---|---|
| `done` | Mark the source node action COMPLETED (project node `## Next Actions`); if CRM-linked and not already closed by `/process-brief`, queue COMPLETED. **Candidate "biggest thing done"** → carry to Step 4 reflection pre-fill. |
| `delegate` (detail = who) | Reassign in the source node (`[WAITING:<who>]`); if CRM connected and no delegatee task exists yet, create one. Log the delegation. |
| `skip` (detail = duration) | Defer; **increment a per-task skip counter** in `<config-root>/memory/.brief-skip-counts.json` (`{task_id: {count, last_skipped, title}}`). Feeds the repeat-ignore rule (Step 2c.3). |
| `not_important` | Append the item to `surfacing-prefs.md` **Do-not-resurface** (Step 2c.3) and demote/close the source node action. |

**Step 2c.1a — Reprioritizations (D3).** For any `tasks` entry with `reprioritized: true`, edit the priority on the source-node action (`## Next Actions` `[P0]`/`[P1]`/`[P2]` tag on the matching item) to the entry's `priority`. This applies whether or not the entry also has a disposition `action`. Carry the new priority into Step 4.5's tomorrow-priority ordering so the change is reflected in the next day's brief.

`annotations` that weren't already handled by `/process-brief` route the same way `/process-brief` Step 2 routes them (draft_reply / reschedule_task / dismiss / clarify). If `/process-brief` already ran today (check `briefing.dismissed-log.md` / the brief's processed section), don't double-act — only handle annotations with no recorded downstream action.

### Step 2c.2 — Write back outreach actions

For each entry in `outreach_actions`, write to the relevant person/bizdev node (idempotent — skip if `/process-brief` already logged the same touch today):

- `sent` → log a touch + the `value_add` used on the person/bizdev node Recent Interactions; roll `bucket` + `signal` + `value_add` into outreach analytics.
- `booked` → advance the pipeline stage + create a prep task.
- `nudge` → log a follow-up touch.
- `let_go` / `dead` → mark dead, remove from the active queue.
- `skip` → defer reappearance by `detail` (the v2 brief UI has no outreach detail prompt, so `detail` is usually absent — default to a 3-day defer when it's empty).

Bucket/value-add/signal roll up into outreach analytics over time (append a line to `<config-root>/growth/outreach-analytics.jsonl` if growth is installed: `{date, contact, action, bucket, signal, value_add}`).

### Step 2c.3 — Suppression learning (writes surfacing-prefs.md)

This is the learning half — what the user explicitly skips/dismisses teaches the brief to stop surfacing noise.

1. **`not_important` actions** → for each, append to `surfacing-prefs.md` **Do-not-resurface** with a reason and source:
   `- **<title>** (<source node/id>) — marked not-important via brief <today>. [suppressed:<today>, reason:user-stated-unimportant]`
   Also demote/close the source node action so it stops generating the task.

2. **Repeat-ignore rule** → read `.brief-skip-counts.json`. For any task surfaced ≥3 times with 0 `done`/`delegate` actions (only carryover or `skip`), surface a one-line proposal:
   > "`<title>` has been surfaced <N> times and you've never acted on it. Move it to do-not-resurface? (y / keep / never-ask)"
   On `y` → append to Do-not-resurface with `reason:repeat-ignore`. On `keep` → reset nothing, it'll re-ask after 3 more. On `never-ask` → mark the counter entry `suppress_prompt: true`.
   In `auto` autonomy, apply repeat-ignore suppressions silently and log them.

3. **Create the file if missing** — if `surfacing-prefs.md` doesn't exist, create it from the template in `references/surfacing-prefs-template.md` (Do-not-resurface / Surfacing rules / Action taxonomy / Changelog) before writing.

Append a Changelog line to `surfacing-prefs.md` summarizing what was suppressed this close.

### Step 2c.4 — Feed forward

- "Biggest thing done" candidates (from `done` actions) → Step 4 reflection pre-fill.
- Surviving incomplete P0/P1 tasks (skipped or untouched, not suppressed) → Step 4.5 tomorrow-priorities proposal.
- Brief mining proposals (any learnings inferred from annotations) join the merged proposal set reviewed in Step 2b's gate if full mode ran, or are committed directly via Step 3 in quick mode.

---

## Step 2.9 — Learnings-first narrative, then memories AND forgettings (B.2 — v4.13+)

Before walking individual proposals, **say what today was about in plain language first** — a short narrative ("here's what today was about"), not raw proposals. Two or three sentences synthesized from the brief actions, the day's transcripts/conversations (full mode), and the reflection candidates. This orients the user before any accept/reject decisions.

Then present **memories and forgettings side by side** — forgettings are first-class, not an afterthought:

- **Memories** (proposed adds/updates): new/updated knowledge, decisions, relationship context. Each shows **type, confidence, target node, source citation**.
- **Forgettings** (proposed removals): stale facts to demote/archive (from the v4.4 decay layer surfacing Cold/Dormant entries touched today), items to suppress (the `not_important` + repeat-ignore proposals from Step 2c.3), and superseded beliefs (concept-drift flags). Each shows what's being demoted/suppressed and why.

The unified review gate (Step 2b in full mode, or a compact version here in quick mode) walks both columns with the batchable controls in B.4 (below). Forgettings use the same accept/edit/skip affordances as memories.

---

## Step 3 — Cortex auto-commit with cheap-tier triage

**Goal:** capture the day's learnings, decisions, and observations to memory — without burning full-tier model tokens on trivial conversations.

Run `/remember` in silent mode with **two inputs**:

1. The current session's content (normal /remember source)
2. The list of accepted proposals from Step 2b — these are pre-routed (each has a `target_node` and `section`) so /remember treats them as already-classified rather than re-classifying through Step 0's low-cost/fast-tier triage. The triage runs ONLY on the current session content; accepted proposals bypass it (the user just accepted them, that's the commit-worthy signal).

**Step 0 (cheap-tier triage) is mandatory for the current-session content** — it's the whole reason the session half is cost-disciplined.

- Classifier decides commit-worthiness and node list for the current session
- Synthesis runs only on affected nodes
- Trivial day with no accepted proposals → `commit: false` on the session AND empty accepted-proposals list → one line in `triage-log.md`, no full-tier model call
- Substantive day OR accepted proposals exist → normal flow, with the Phase 3 person-page graduation logic firing where relevant

User-observation CORRECTIONs always commit to the `user` node regardless of the classifier's decision (see `skills/observe/SKILL.md` for the override rule).

When writing the proposals to their target nodes, follow the v4.3+ knowledge-entry tag convention (see `/remember` Step 3 C.0): every new entry gets `[confirmed:<today>] [recalled:<today>]` tags. Entries the mining layer **updates** (e.g., a re-affirmed insight) get `[confirmed:<today>]` while leaving `[recalled:...]` to be updated by the next /recall that surfaces them.

Confirm briefly to the user (not verbose):

> "Memory updated: [N] nodes touched, [M] knowledge entries committed, [K] person-page updates, [P] mined proposals applied."

If the classifier returned `commit: false` AND no proposals were accepted, say: "Quiet day — nothing material to commit. Logged the audit line." and continue.

### Step 3.7 — Passive person-page graduation (v4.10+)

After the commits from Step 3 land, run a cheap-tier pass over `<config-root>/memory/.person-mention-counts.json` (created/updated by `/remember` and mining agents when they emit a person's name without a person page).

For each name where:
- Total mentions across all nodes ≥ 3, AND
- Number of distinct nodes mentioning the name ≥ 2, AND
- No `<config-root>/memory/person/<slug>.md` exists yet

Surface a one-line graduation prompt:

> "I've seen `<Name>` mentioned <N> times across <M> nodes. Graduate to a person page? (y / not yet / never — suppress)"

- **y** → run a one-shot synthesis pass: read all node files mentioning `<Name>`, compose a person page (Identity / Relationship / Open threads / Recent interactions / Notes / Linked entities), then write it and update the source nodes via `scripts/cortex_cli.py` (locks and writes atomically — see `references/core-contract.md` §11):
  ```
  python3 scripts/cortex_cli.py write-file --memory-root <config-root>/memory \
    "person/<slug>.md" "<composed page content>"

  python3 scripts/cortex_cli.py write-file --memory-root <config-root>/memory \
    "<source-node-relative-path>" "<entire file content with bare mentions replaced by [[person/<slug>]]>"
  ```
  (Same pattern as `/relink-memory` Step 6 — a wikilink conversion is a whole-file text substitution, not a single-section edit.)
- **not yet** → leave mention count growing; will re-surface next day if threshold still crossed.
- **never** → suppress this name:
  ```
  python3 scripts/cortex_cli.py write-file --memory-root <config-root>/memory \
    ".person-mention-counts.json" "<updated JSON with suppressed: true for this entry>"
  ```
  never propose again.

Cap: 3 graduation prompts per `/end-day` run (otherwise the close turns into a graduation marathon). The remaining candidates re-surface tomorrow.

If `memory/.person-mention-counts.json` doesn't exist or is empty (no candidates), skip silently.

---

## Step 4 — Reflective prompts

**Goal:** capture the human-readable version of what mattered today, separate from the structured commits in Step 3.

### Step 4.0 — Pre-fill from brief artifact (v4.13+ reads v0.7.0 shape)

Reuse the brief state already read in Step 2c (via the Step 2c.0 chain: state-mirror file `briefs/<today_local>.state.json` → widget context → paste path → fallback gate; canonical v0.7.0 shape: `tasks` / `annotations` / `outreach_actions` / `reflection`). Don't re-read if Step 2c already loaded it. If `state.reflection` is already populated (the user filled in Today's Reflection in the artifact), show it as the pre-fill for all three questions below rather than deriving from `done`/annotations separately, and skip straight to confirming it in Step 4.1.

Pre-fill the reflection prompts from the mined actions:

- **Biggest thing done** ← the "biggest thing done" candidates carried forward from Step 2c.4 (tasks with `action == "done"`, most-substantial first; title from `tasks[id].name`).
- **What blocked you** ← `annotations` containing "blocked", "stuck", "waiting"; and any `delegate` actions (handed off because blocked).
- **One thing tomorrow has to move** ← `annotations` containing "tomorrow", "P0", "must"; and the top surviving incomplete P0 from Step 2c.4.

**Sanitize, don't quote verbatim.** The annotation content may contain raw business context ("Sarah is unhappy with proposal terms" → render as "Issue with proposal discussion"). The reflection captures the user's read of the day; it should NOT include verbatim sensitive client content. See nucleus contracts.md "Data-flow trace for annotations" for the privacy reasoning.

If Cowork artifact tools aren't available (Claude Code), skip Step 4.0 and ask the three questions cold per Step 4.1 below.

### Step 4.1 — Ask the reflection questions

Ask the user, conversationally, one at a time (pre-filled candidates from Step 4.0 shown as suggestions, not assumptions):

1. **"Biggest thing that got done today?"** — pre-fill with the most-substantial `done` task from Step 2c.4. User can accept, edit, or override. Captured as an INSIGHT (or DECISION if it was a choice) on the relevant project node, per the consolidated taxonomy (`/remember` B.3: Insight / Decision / Gotcha / Correction).
2. **"What blocked you, if anything?"** (optional) — pre-fill with candidate blockers from annotations. Captured as a GOTCHA if structural, or as a BLOCKER on the project's open threads.
3. **"What's the one thing tomorrow has to move?"** — pre-fill with candidate priorities from annotations. Captured as a `[P0]` next-action on the relevant project node, dated tomorrow, AND fed to Step 4.5 + section 1 (Center of Gravity) of tomorrow's brief.

These three answers also feed Step 5's pre-stage as section 5 (Yesterday's Reflection) content of tomorrow's brief.

Keep conversational. If the user says "nothing major today," that's valid — skip to Step 5.

If the user provides answers, **append them to today's brief markdown snapshot** at `<config-root>/briefs/<today_local>.md` under a `## Reflection` section (v4.6+ — was Section 7 prior to briefing v0.3.0). Idempotent: if a `## Reflection` section already exists from a prior `/end-day` run today, replace its contents rather than duplicating.

Format:

```markdown
## Reflection

- **Biggest thing that got done today:** <answer or "—">
- **What blocked you:** <answer or "—">
- **The one thing tomorrow has to move:** <answer or "—">
- _Captured by /end-day at <HH:MM>._
```

This is the canonical write — tomorrow's `/brief` Section 5 (Yesterday's Reflection) reads from this section. If the user said "nothing major today," still write the `## Reflection` section with `—` placeholders and a "skipped" timestamp so tomorrow's brief shows the explicit non-event rather than "no reflection logged."

If `<config-root>/briefs/<today_local>.md` doesn't exist (user ran `/end-day` without ever generating today's brief), create the file with a minimal `# End-of-day reflection — <today>` header followed by the `## Reflection` section. Don't try to back-fill the missing brief content.

### Step 4.2 — Append to the longitudinal reflection store (B.7 — v4.13+)

In addition to the per-day `## Reflection` in the brief markdown, append today's reflection to the rolling **`<config-root>/memory/me/reflections.md`** so reflections become a longitudinal, queryable record ("what have my biggest wins been this month," "what keeps blocking me"). This store is itself an input to `/end-week` / briefing's `/review` and to future surfacing decisions.

Create the file from `references/reflections-template.md` if missing (header + "newest first" convention). Append one dated block at the top of the log:

```markdown
## <today_local> (<Day>)
- **Biggest thing done:** <answer or "—">
- **What blocked you:** <answer or "—">
- **One thing tomorrow has to move:** <answer or "—">
```

Append-only; never rewrite prior entries. Idempotent for the same day (replace today's block if it already exists from a re-run). `reflections.md` decays slowly — it's a record, not a working surface — so it's excluded from the v4.4 decay sweep. Queue an index refresh (it's a memory file) so it appears in `index.md`.

---

## Step 4.5 — Propose tomorrow's priorities & outreach (B.5 — individually, batchable — v4.13+)

After memory is settled, propose **tomorrow's priority tasks and outreach** so the morning surface is ready. This is where deliberateness matters most, so walk items **individually** — but offer a batch path when sensible.

Candidate priorities come from: surviving incomplete P0/P1 tasks (Step 2c.4), the "one thing tomorrow has to move" reflection answer, accepted `[P0]` next-actions from Step 3, and any `skip`-deferred tasks whose snooze elapses tomorrow. Candidate outreach comes from the growth pipeline tier for tomorrow plus any `nudge`/deferred contacts.

- **Respect `surfacing-prefs.md`** — never propose suppressed or noise-class items.
- Walk each proposed priority and outreach item individually: `(k)eep / (e)dit / (d)rop`.
- Offer a batch shortcut when items obviously carry over unchanged: "These 3 priorities carry over unchanged — keep all? (y / pick)".
- Output writes straight into **tomorrow's brief sections 3 (Priority Tasks) & 4 (Outreach Queue)** — these become the seed set Step 5 renders into the pre-staged `todays-brief` artifact. Persist them so Step 5's `/brief --target_date=tomorrow` includes them (write to `<config-root>/briefs/<tomorrow_local>.seed.json` with `{priorities:[...], outreach:[...]}` that `/brief` reads if present).

If there's nothing material to propose, say so and continue — don't pad tomorrow with filler.

## Step 4.6 — Anything else for tomorrow (B.6 — v4.13+)

Explicitly ask, once: **"Any other priorities or outreach for tomorrow?"** Free-form capture. Append whatever the user gives to tomorrow's seed (`briefs/<tomorrow_local>.seed.json`) so it lands in tomorrow's brief. If the user says "no" / stays silent, continue.

---

## Step 4.7 — Log to HubSpot (optional — v4.13+)

Explicitly ask, once: **"Anything to log in HubSpot before we close?"** This is the catch-all for CRM updates the user wants captured that didn't already flow through the brief actions in Step 2c (which already handles `done`→COMPLETED, `delegate`→delegatee task, outreach `sent`→touch, `booked`→prep task). Use it for meeting notes, new deals/contacts, deal-stage moves, follow-up tasks, or activity logging that came up in conversation today.

**Skip the prompt entirely if HubSpot MCP isn't connected** (no CRM to write to) — say nothing and continue to Step 5.

If connected, ask the single open question above. Then:

1. **If the user says "no" / stays silent** (or, in `auto` autonomy, when nothing actionable surfaced today) → continue to Step 5, no writes.
2. **If the user names things to log**, interpret each into a concrete HubSpot write and route via the HubSpot MCP (use the same tool surface the rest of Nucleus uses — `manage_crm_objects` for create/update, the HubSpot search tool to resolve named entities to object ids):
   - **Note / activity** on a contact, company, or deal → create the engagement/note and associate it to the right object (search the CRM for the named entity first).
   - **Task / follow-up** → create a task object, owner = user, due date as given (default tomorrow).
   - **Deal stage / property update** → update the deal's stage or property.
   - **New contact / company / deal** → create the object, pre-filled from what the user said + any matching cortex node context.
3. **Confirm before writing.** Present a single batch table of the intended HubSpot writes (object, action, key fields) and get one approval:
   ```
   Log to HubSpot:
     · Note → deal "Acme Corp" : "Sent phased plan; Fairview Fund ~July 1 creates pull"
     · Task → contact "Priya (VendorCo)" : "Confirm project ID" due tomorrow
     · Stage → deal "Beacon Analytics diagnostic" : Qualified → Proposal

   [Y]es to all · [N]o to all · [E]dit (toggle per row)
   ```
   On Y → batch-write; report successes/failures. On N → no writes. On E → per-row toggle, then batch.
   In `auto` autonomy, skip the confirmation table and write directly (still logging what was written).
4. **Cross-link to memory.** For any HubSpot object that maps to a cortex person/bizdev/client node, append a one-line Recent Interactions / Changelog entry noting the CRM write, so the memory trail and CRM stay in sync. Reuse the growth `/touchpoint` path if growth is installed.

Record what was logged for the Step 6 close summary ("Logged to HubSpot: 1 note, 1 task, 1 stage move.").

---

## Step 5 — Pre-stage tomorrow's brief

**Goal:** when tomorrow morning hits, the brief is already waiting AS THE SAME ARTIFACT FORMAT `/brief` produces — not a degraded markdown-only fallback.

If the `briefing` plugin is installed:

1. Invoke its `/brief` command with `target_date: tomorrow_local`. `/brief` reads `<config-root>/briefs/<tomorrow_local>.seed.json` (written by Steps 4.5/4.6) if present and seeds sections 3 (Priority Tasks) & 4 (Outreach Queue) from it, then merges live pulls — so the priorities/outreach the user just walked are already on tomorrow's surface.
2. If Step 1 ran (full mode only), pass the inbox-triage results so the brief doesn't re-query Gmail. In quick mode, the brief queries Gmail itself in the morning — no shared state needed.
3. **Today's reflection is read by tomorrow's `/brief` Section 5 (Yesterday's Reflection) directly from today's markdown's `## Reflection` section** (briefing v0.5.0+). No explicit handoff from this step.
4. **Artifact consistency rule (v4.12.0+):** the brief generator MUST call `mcp__cowork__update_artifact` with id `todays-brief` to refresh the persistent Cowork artifact. **Never** create a new artifact and never produce only a markdown-only fallback when Cowork is available — the artifact id must remain stable so the user always opens the same persistent surface. If no `todays-brief` artifact exists yet, create it once with that id; update it on every subsequent `/end-day` and `/brief` run. The markdown snapshot at `<config-root>/briefs/<tomorrow_local>.md` is still written as the canonical text record, but the Cowork artifact is the working surface and must also be updated.
5. **Canonical artifact format (v4.13+ — 5 fixed sections per the End-Day Routine Improvement Spec Part A):** the `todays-brief` artifact always includes these sections in this order — (1) **Center of Gravity** accent banner (the single most important thing; not interactive), (2) **Calendar Block** = visual timeline strip + written block list with per-meeting notes, (3) **Priority Tasks** with richer per-row actions (done / delegate / skip / not_important / **reprioritize** / annotate) + progress bar, (4) **Outreach Queue** tiered (today / this week / backlog) with per-contact actions + optional category tags (bucket / value-add; signal auto-fills), (5) **Yesterday's Reflection** (read-only). A sticky header carries the date + counts line. localStorage key is `brief-YYYY-MM-DD` (schema_version 0.7.0); the artifact also mirrors its state to `briefs/<date>.state.json` for the close to read (D2a). All interactive controls are inline — the template uses **no** `prompt()`/`confirm()`/`alert()` (blocked in Cowork's artifact sandbox). Reference implementation: briefing v0.6.0+ ships this as `references/brief-artifact-template.html`; this Step 5 routes to that. Formatting MUST be identical whether produced by `/brief` or this pre-stage.
6. If Cowork artifact tools aren't available (Claude Code), produce the markdown snapshot only with a clear notice — but explicitly flag the degraded surface so the user knows to open the Cowork app for the full working brief.

### User gate after Step 5

> "Tomorrow's brief is staged. Want to review it now, or wait until morning?"

- "Review now" → render section summaries inline (don't dump full sections — that's what the artifact / snapshot is for)
- "Wait" (default) → confirm and close

If `briefing` is NOT installed, skip Step 5 entirely. The chain still produced value (triage results visible in chat, commitments converted, memory committed, reflections captured to today's snapshot).

---

## Step 5.5 — Refresh memory index (v4.5+)

Regenerate `<config-root>/memory/index.md` so the next day's `/recall`, non-cortex agents, and Obsidian users see an up-to-date catalog.

```
python3 scripts/cortex_cli.py reindex --memory-root <config-root>/memory
```

Deterministic and zero-LLM (see `scripts/lib/index_generator.py` and `commands/reindex.md`) — runs in seconds, no user input required.

If `<config-root>/memory/staged/queues/reindex` exists (from prior `/remember` calls), the indexer notices it and deletes it after running.

No user gate. This step always runs. If the indexer fails, log the error and continue to Step 5.6 — don't block the close on a maintenance task.

---

## Step 5.6 — Refresh hot cache (v4.7+)

```
python3 scripts/cortex_cli.py refresh-hot --memory-root <config-root>/memory --trigger end-day
```

Regenerates `<config-root>/memory/hot.md` so tomorrow's `/recall` auto-fire opens with a fresh 7-day rolling buffer. Pure file walk + filter + render per `references/hot-cache.md`. Zero LLM cost.

If `hot_cache.enabled: false` is set in user-context, skip this step.

No user gate. If hot-cache generation fails, log and continue to Step 5.7.

---

## Step 5.7 — Log to chronicle (v4.7.1+, centralized in v4.7.2+)

Invoke the `log-writer` skill (see `skills/log-writer/SKILL.md`) with:
- **op_name:** `end-day`
- **summary:** `<quick|full> mode. <N> commitments captured, <M> reflection answers, <K> memory entries committed. tomorrow brief pre-staged.`

Adjust the metric counts based on what actually ran (don't include reflection-count if Step 4 was skipped; omit "tomorrow brief pre-staged" if briefing isn't installed).

---

## Step 5.8 — Memory-as-git commit (v4.12.0+; race-aware in v4.12.2+)

If memory-as-git is enabled, auto-commit today's memory changes. This makes the day a reviewable unit and gives `/morning` a diff to surface.

Check whether `<config-root>/memory/.git/` exists.
- **If exists** → proceed.
- **If not** → offer to initialize it once (closes the proposal's "next /end-day after upgrade runs init" migration path), respecting the autonomy slider:
  - `auto` → skip silently (don't init without consent — git init + first commit is a meaningful change); log a one-line note.
  - `suggest` (default) / `confirm` → prompt once: "Memory-as-git isn't initialized — it powers `/morning`'s overnight-diff review and rollback safety. Initialize `<config-root>/memory/` as a local git repo now? (y / not now / never)."
    - `y` → run the same init path as `/setup-identity` Step 3.6 (symlink-into-cloud-sync warning, write `memory/.gitignore` from `references/memory-gitignore-template.md`, `git init`, initial commit), then continue with today's commit below.
    - `not now` → skip this run; re-offer next `/end-day`.
    - `never` → write `memory_as_git.enabled: false` to `<config-root>/plugins/cortex.user-context.md` so this never re-prompts. Skip.
  - If, after the offer, `.git/` still doesn't exist → skip the rest of Step 5.8.

### Step 5.8.0 — Memory write-lock acquisition (v4.12.2+)

Before any git operation, acquire the memory lock — the `git add`/`git commit` sequence below spans multiple shell commands, not one `cortex_cli.py` call, so use the paired acquire/release subcommands (see `scripts/lib/locking.py`'s `acquire_lock_for_external_section`/`release_lock_for_external_section` and `references/core-contract.md` §11):

```
python3 scripts/cortex_cli.py lock-acquire --memory-root <config-root>/memory --timeout 10 --stale-after 600
```

- On success (exit 0): proceed to Step 5.8.1.
- On failure (exit 1, timeout — lock held by another process past its staleness window): surface "Memory write-lock held by another process — skipping memory commit; retry next `/end-day`." Exit Step 5.8 with a status note. Continue to Step 6 (close). Do **not** manually delete the lock file — staleness reclaim is automatic and handled by the lock itself.

The same lock (and CLI) is used by `/listen`, `/morning`, `/remember`, `/note`, `/forget`, `/cleanup`, `/rehearse`, `/relink-memory`, and `/sync-linked-entities` for every node-file mutation — this is one shared lock, not a per-command one.

The lock is `memory/.lock` — covered by both gitignore variants (local-only and remote-safe).

### Step 5.8.1 — Defensive .gitignore validation (v4.12.2+ fingerprint-precise)

```
cd <config-root>/memory

remote_set = (cortex.user-context.md contains memory_as_git.remote: with non-empty value)
chosen_variant = remote-safe if remote_set else local-only

# Detect v4.12.0 fingerprint precisely (per references/memory-gitignore-template.md Step 4a logic):
#   v4.12.0 had ALL THREE inline-comment lines:
#     - "log.md" + "operations chronicle" on one line
#     - "hot.md" + "7-day rolling cache" on one line
#     - "index.md" + "auto-maintained catalog" on one line
# Only treat as buggy if ALL THREE present.

if memory/.gitignore does not exist:
  Write chosen_variant to memory/.gitignore.
elif v4.12.0 fingerprint detected:
  Rewrite memory/.gitignore from chosen_variant.
  git rm --cached hot.md index.md log.md .state.json .person-mention-counts.json .person-recall-counter.json 2>/dev/null
  Log once: "Repaired v4.12.0 .gitignore bug; un-tracked high-churn cache files."
elif remote_set AND memory/.gitignore matches local-only fingerprint (contains log.md but not triage-log.md):
  Rewrite memory/.gitignore from remote-safe variant.
  git rm --cached triage-log.md dismissed-proposals.log 2>/dev/null
  Log once: "Promoted to remote-safe gitignore; un-tracked PII-dense files."
else:
  Leave it alone (user may have customized).
```

### Step 5.8.2 — Pre-commit index safety check (v4.12.2+)

```
# Check whether the index already has uncommitted changes from a prior failed Step 5.8 attempt.
prior_index = git diff --cached --stat | wc -l

if prior_index > 0:
  Surface: "Uncommitted changes from a prior /end-day attempt are staged. Commit those alone now, then continue with today's changes? (y/n/show)"
  On y: git commit -m "Recovery commit from prior failed /end-day"
  On show: render `git diff --cached`, then re-prompt.
  On n: skip Step 5.8 entirely with note; user can investigate manually.

# Now proceed with today's add.
git add .
git diff --cached --stat
```

### Step 5.8.3 — Compose + commit

```
If staged changes is empty → log "no memory changes today", release lock, and exit Step 5.8.

Otherwise compose commit message:
  <today_local> day close — <N> nodes touched, <K> entries added, <D> demoted, <A> archived
  Sources today: <commit-source-summary>
where commit-source-summary lists what touched memory today by reading
memory/log.md entries for today and counting occurrences. Example:
  "1 /listen merge via /morning · 3 /remember runs · 1 /research-gaps merge · /cleanup Section H archive"

git commit -m "<message>"
```

### Step 5.8.4 — Post-commit verification (v4.12.2+)

```
post_status = git status --porcelain | wc -l
if post_status > 0:
  Surface: "⚠ Memory commit succeeded but working tree is still dirty: <files>. This may indicate a race (another command mutated memory mid-commit) or a hook side-effect. Inspect: cd <config-root>/memory && git status."
  Log the dirty state to memory/log.md.
```

### Step 5.8.5 — Release the write-lock

```
python3 scripts/cortex_cli.py lock-release --memory-root <config-root>/memory
```

Run this on every exit path from Step 5.8 — success or failure — same as the old prose said, but now backed by real ownership-checked release logic instead of an unconditional `rm` (which could otherwise delete a different process's lock if this one's had already gone stale and been reclaimed).

**Optional push:**
- If `cortex.user-context.md` has `memory_as_git.remote: <url>` AND `memory_as_git.push_on_close: true`, run `git push <memory_as_git.remote_name, default "origin"> main` after commit.
- Default: no remote configured; commits are local-only.
- As of v4.18.3, `/morning` also runs this same commit+push (Step 4.7) since it's the required daily touch and `/end-day` is optional — see that command for the canonical logic. This copy stays for users who still run `/end-day` in full mode on a day `/morning` was skipped.

**Failure mode:** if commit fails (rare — usually merge conflict from external edits or git config error), log the error and continue to Step 6. Don't block the close on a maintenance task. Surface to user: "Memory-as-git commit failed — investigate `<config-root>/memory/.git` state."

**Idempotent:** empty commits are a no-op. Safe to run multiple times per day if the closing ritual runs twice.

---

## Step 6 — Close

**Publish (v4.29+).** If the config-root is a synced checkout (`<root>/.private` exists), run
`python3 scripts/cortex_cli.py sync --root <config-root>` as the final write and include its
result in the closing summary. A conflict is reported with its `conflict/<host>/<ts>` branch.


Confirm completion briefly:

> "Day closed. [N] commitments converted, [M] memory entries, [K] person pages touched[, [H] HubSpot writes]. Tomorrow's brief staged for [tomorrow_local]. See you tomorrow."

Include the HubSpot count only if Step 4.7 actually wrote anything.

Adjust the count summary based on what actually ran (don't fabricate counts for skipped steps).

---

## Default behavior on user-gate timeouts

If the user is running this in a fire-and-forget mode (e.g., via a scheduled task, or they walked away), apply these defaults:

- **Quick-mode auto-offer prompt** (the "want the full close?" prompt at the top) → "no" after ~5s
- **Step 1 gate** (full mode only) → "Wait" after ~10s
- **Step 2 commitments gate** (full mode only) → "Skip" per item after ~10s (don't auto-create CRM tasks without confirmation — destructive on the wrong side)
- **Step 2b unified review gate** (full mode only) → "Skip all" after ~30s. Never auto-commit mined proposals; too easy to pollute nodes silently. The 30s window (vs. 10s elsewhere) is longer because this gate has more density and the user may actually be reviewing it.
- **Step 4.7 HubSpot-logging gate** → "no" after ~10s (never auto-write to CRM in a fire-and-forget run — destructive on the wrong side)
- **Step 5 brief-pre-stage gate** → "Wait" after ~10s

The chain should never block. If the user is engaged, gates pause for input. If not, gates pick the conservative default and move on. Skipped Step 2b proposals are logged to the dismissal log per the Step 2b spec so they don't re-surface tomorrow.

---

## Behavior rules

- **Quick mode is the default.** Heavy steps (1, 2, 2a, 2b) only run with `--full` or when the user accepts the auto-offer prompt.
- **Don't introduce friction for nothing.** Auto-offer the full chain only when transcripts ≥ 2 or inbox ≥ 5. Otherwise skip the prompt.
- **Conversational, not formal.** This is a reflection ritual.
- **Skip what doesn't apply.** Missing plugins → skip that step silently.
- **Don't over-capture.** Step 3's cheap-tier triage exists to prevent over-capture; respect its decisions.
- **Honor user gates.** Never auto-convert transcript commitments to CRM tasks without explicit per-item confirmation (full mode).
- **Pre-stage is opt-in default.** If `briefing` isn't installed, the chain ends after Step 4. No nag.
- **Telemetry (optional).** If ops is installed, log one line at completion: `skill: end-day, mode: quick|full, steps_run: [...], commits_count, runtime_ms`.

## What this command is NOT for

- **Mid-day check-ins.** Use `/recall [node]` or `/search`.
- **Long retrospectives.** Use `/end-week` or briefing's `/review`.
- **Session memory dumps.** That's `/remember`. `/end-day` is the *day's* rhythm.
- **Tomorrow's calendar blocking.** That's `plan-tomorrow`'s job (different verb, different output). If you want both this chain AND calendar blocks for tomorrow, run `/end-day` then `/plan-tomorrow` — there's no automatic chain between them in v1.

## When to skip this entirely

- Weekend afternoons where nothing work-shaped happened today
- Days you took off (vacation, sick) — skip the ritual; don't reflect on a non-work-day
- After running `/end-week`, since that subsumes the day-level reflection
