# /end-day formats and procedures

Detail for `commands/end-day.md`. The command file is the order of operations and the
rules; this file holds the formats, tables and step-by-step procedures it points to.
Where the two differ, the command file wins. Step numbers match the command file.

## Scope migration (one time)

The mining layer (Steps 2a / 2b below) routes extracted content to nodes using a Scope convention on each domain-shaped node. This migration runs **once** to adopt the convention on existing nodes. After it completes, a marker file at `<config-root>/memory/.scope-migration-done` prevents re-prompting.

Skip this block if `<config-root>/memory/.scope-migration-done` exists. Otherwise:

#### A — Detect domain-shaped nodes

Scan `<config-root>/memory/`. A node is "domain-shaped" if ALL of:

- It's a `.md` file at root level (e.g., `<config-root>/memory/<name>.md`), OR a `.md` file in a non-reserved subdirectory
- Its filename is NOT one of: `user.md`, `DASHBOARD.md`, `triage-log.md`, `CLAUDE.md`
- Its containing directory is NOT one of: `client/`, `bizdev/`, `person/`, `archive/` (these are project / prospect / person / archive — not domain)
- Its YAML front-matter (if present) does NOT set `type: project` (engagement state, handled separately)

The detection is purely structural. The plugin does not know or care what specific domains the user has — it works against whatever nodes exist.

#### B — Synthesize a Scope draft per detected node

For each detected node, read its current content and produce a draft Scope section pre-filled from what's already in the file:

- **Topics:** lowercased keywords inferred from existing knowledge-entry tags, recurring nouns in the Summary, and recurring section headers
- **Aliases:** alternate names mentioned in PEOPLE entries or Summary (e.g., a node named `studio.md` whose Summary references "Learning Production System" gets that as an alias)
- **What goes here:** one-line synthesis from the Summary section
- **What does NOT go here:** left empty in the draft — this is the most useful field but requires user judgment

#### C — Per-node confirmation

Present each draft to the user, one node at a time:

> "Node `<name>`. Proposed Scope section:
>
> [draft]
>
> (a)ccept / (e)dit / (s)kip"

- `accept` → insert the Scope section as the first section of the node file (above existing Summary). Idempotent: if a Scope section already exists, replace it; if not, insert.
- `edit` → drop into edit mode. User edits inline, then accept.
- `skip` → skip this node. It can still receive routed content from miners, but routing accuracy drops without the Scope hint. The migration will not re-prompt for this node — user can re-run `/end-day` with `--rerun-scope-migration` later to revisit.

#### D — Offer new domain nodes (open-ended)

After all detected nodes are processed, ask once:

> "Want to create any new domain nodes now? (open-ended — list them comma-separated, or skip)"

For each name the user lists:
1. Confirm node ID (kebab-case, lowercased)
2. Walk through the same Scope interview (topics / aliases / what goes here / what does NOT go here — all four asked, no draft to pre-fill since the node is new)
3. Create the node file at `<config-root>/memory/<name>.md` with the Scope section, an empty Summary placeholder, and standard sections (Knowledge / People / Changelog / Open Threads / Next Actions)

The plugin does not suggest names. The user drives the list.

#### E — Mark complete

Write `<config-root>/memory/.scope-migration-done` with the ISO timestamp and the list of nodes processed (one line per node, `<status> <node-id>` — accepted, edited, skipped, or created). This file is the only check that prevents re-prompting on subsequent `/end-day` runs.

If the user runs `/end-day --rerun-scope-migration`, delete the marker and re-run this block.

#### F — On failure

If Pre-chain B errors partway through (e.g., a node file is unreadable), log the partial state to `<config-root>/memory/.scope-migration-partial` and prompt the user: "Scope migration hit an error on `<node>`. Resume later via `/end-day --rerun-scope-migration`? Or continue with the rest of `/end-day` now using whatever Scope sections were captured?" Default: continue.

## Source card (Step 0.7)

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

> Design note: this is one card with checkboxes + costs + a single confirm. Never gate each source behind its own prompt.

## Reading the brief state (Step 2c.0)

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

#### Step 2c.0a — Fallback gate (D2c — fires only when state is unreadable AND the paste path was skipped)

When no source yields a blob, **ask exactly one multi-select question** rather than skipping the brief:

> "I couldn't read today's brief state automatically. Which of today's surfaced items did you complete / delegate / kill?"

Seed the options from **today's brief task list** (read the priorities from `<config-root>/briefs/<today_local>.md` or the `<today_local>.seed.json` that generated it — the same list rendered into the artifact). Let the user tag each selected item done / delegated / skipped / not-important (a second quick prompt per selected item, or free-text). Route the answers through the **normal Step 2c.1 / 2c.2 write-backs** exactly as if they'd come from the blob.

If the brief task list itself is unavailable (no markdown, no seed), only then skip Step 2c with a one-line honest note ("brief state unreadable and no task list on disk — skipped").

## Brief write-backs (Steps 2c.1 to 2c.3)

Every write below is proposed first (see the command file): memory writes as one
batch, CRM writes one at a time. Nothing in this section runs unreviewed.

#### Step 2c.1 — Write back task actions (per surfacing-prefs taxonomy)

For each entry in `tasks`, apply the action's write-back (taxonomy is canonical in `<config-root>/memory/me/surfacing-prefs.md` "Action taxonomy"):

| Action | Write-back |
|---|---|
| `done` | Mark the source node action COMPLETED (project node `## Next Actions`); if CRM-linked and not already closed by `/process-brief`, queue COMPLETED. **Candidate "biggest thing done"** → carry to Step 4 reflection pre-fill. |
| `delegate` (detail = who) | Reassign in the source node (`[WAITING:<who>]`); if CRM connected and no delegatee task exists yet, create one. Log the delegation. |
| `skip` (detail = duration) | Defer; **increment a per-task skip counter** in `<config-root>/memory/.brief-skip-counts.json` (`{task_id: {count, last_skipped, title}}`). Feeds the repeat-ignore rule (Step 2c.3). |
| `not_important` | Append the item to `surfacing-prefs.md` **Do-not-resurface** (Step 2c.3) and demote/close the source node action. |

**Step 2c.1a — Reprioritizations (D3).** For any `tasks` entry with `reprioritized: true`, edit the priority on the source-node action (`## Next Actions` `[P0]`/`[P1]`/`[P2]` tag on the matching item) to the entry's `priority`. This applies whether or not the entry also has a disposition `action`. Carry the new priority into Step 4.5's tomorrow-priority ordering so the change is reflected in the next day's brief.

`annotations` that weren't already handled by `/process-brief` route the same way `/process-brief` Step 2 routes them (draft_reply / reschedule_task / dismiss / clarify). If `/process-brief` already ran today (check `briefing.dismissed-log.md` / the brief's processed section), don't double-act — only handle annotations with no recorded downstream action.

#### Step 2c.2 — Write back outreach actions

For each entry in `outreach_actions`, write to the relevant person/bizdev node (idempotent — skip if `/process-brief` already logged the same touch today):

- `sent` → log a touch + the `value_add` used on the person/bizdev node Recent Interactions; roll `bucket` + `signal` + `value_add` into outreach analytics.
- `booked` → advance the pipeline stage + create a prep task.
- `nudge` → log a follow-up touch.
- `let_go` / `dead` → mark dead, remove from the active queue.
- `skip` → defer reappearance by `detail` (the v2 brief UI has no outreach detail prompt, so `detail` is usually absent — default to a 3-day defer when it's empty).

Bucket/value-add/signal roll up into outreach analytics over time (append a line to `<config-root>/growth/outreach-analytics.jsonl` if growth is installed: `{date, contact, action, bucket, signal, value_add}`).

#### Step 2c.3 — Suppression learning (writes surfacing-prefs.md)

This is the learning half — what the user explicitly skips/dismisses teaches the brief to stop surfacing noise.

1. **`not_important` actions** → for each, append to `surfacing-prefs.md` **Do-not-resurface** with a reason and source:
   `- **<title>** (<source node/id>) — marked not-important via brief <today>. [suppressed:<today>, reason:user-stated-unimportant]`
   Also demote/close the source node action so it stops generating the task.

2. **Repeat-ignore rule** → read `.brief-skip-counts.json`. For any task surfaced ≥3 times with 0 `done`/`delegate` actions (only carryover or `skip`), surface a one-line proposal:
   > "`<title>` has been surfaced <N> times and you've never acted on it. Move it to do-not-resurface? (y / keep / never-ask)"
   On `y` → append to Do-not-resurface with `reason:repeat-ignore`. On `keep` → reset nothing, it'll re-ask after 3 more. On `never-ask` → mark the counter entry `suppress_prompt: true`.
   These proposals appear under Forgettings in the Step 2b review; none is applied without it.

3. **Create the file if missing** — if `surfacing-prefs.md` doesn't exist, create it from the template in `references/surfacing-prefs-template.md` (Do-not-resurface / Surfacing rules / Action taxonomy / Changelog) before writing.

Append a Changelog line to `surfacing-prefs.md` summarizing what was suppressed this close.

## Miner inputs and merge (Steps 2 and 2a)

Invoke `note-taker` with `mode: "transcript"`:
- `time_window: 1 day`
- `note_sources: [<filtered list>]`
- `node_inventory`, `node_summaries`, `dashboard_snapshot` (built from `<config-root>/memory/`)
- `crm_task_snapshot`: current HubSpot tasks owned by the user

The agent returns two streams: `commitments_delta` and `learnings_delta`.

1. `note-taker` with `mode: "conversation"`:
   - `time_window: 1 day`
   - `current_session_id`: the session running `/end-day` (exclude from mining)
   - `node_inventory`, `node_summaries`, `dashboard_snapshot`
   - `user_email`, `user_local_tz` (from identity.md)

2. `note-taker` with `mode: "activity"`:
   - `time_window: 1 day`
   - `node_inventory`, `node_summaries`, `dashboard_snapshot`
   - `user_email`, `user_local_tz`

Each mode runs its own cheap-tier triage gate first. Modes that triage-skip return empty and cost ~nothing.

#### Merge step

Combine three sources of proposals:

- `note-taker`'s (`mode: transcript`) `learnings_delta` from Step 2
- `note-taker`'s (`mode: conversation`) `learnings_delta`
- `note-taker`'s (`mode: activity`) `learnings_delta`

Apply cross-mode dedup:

- For each proposal in the `mode: conversation` stream, check against `mode: transcript`'s stream — if a proposal on the same target_node has > 70% content overlap, drop the conversation version (transcript is the source of record).
- For each proposal in `mode: activity`'s stream, do the same against `mode: transcript`.
- Within each remaining set, dedup against existing node content (n-gram > 70% overlap → drop).

Group surviving proposals by `target_node`. Sort within each group by `confidence DESC, update_type` (corrections first, then decisions/insights, then gotchas/models, then relationship-context).

## Review gate (Step 2b)

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

#### Auto-expand cross-refs

When rendering a proposal that has `cross_ref: [<id>]`, render the linked proposal's `content` inline as a "cross-ref →" line under it (see format above). The user reviews both in context without having to jump.

#### High-confidence toggle behavior

If the user picks `(h)`, render only proposals with `confidence: high`. The rest are deferred (logged as "deferred — review tomorrow" in the dismissal log — they re-surface in tomorrow's mining if still applicable; they don't get auto-committed and they don't permanently disappear).

#### New-node-creation confirmation

If any proposal has `node_type: new` (with a `new_node_suggestion`), surface a dedicated confirmation BEFORE accepting any content into it:

> "Create new node `<id>`? Type: <type>. Scope: <one-line>. (y / edit-scope / n)"

If `y` → create the node file with a Scope section (interview the user inline for the 4 Scope fields), then accept the proposal into it.
If `edit-scope` → walk the 4-field Scope interview before creating.
If `n` → drop all proposals targeting that new node (or, on a per-proposal basis, ask whether to re-route each one to an existing node).

This makes taxonomy growth explicit rather than silent.

#### Dismissal log

Skipped proposals (whether from `(k)skip all`, per-item skip, or implicit when `(h)high-confidence` was chosen) are logged to `<config-root>/memory/dismissed-proposals.log` (append-only), keyed by a hash of `(source.note_id or session_id or event_ref) + content` so they don't re-surface tomorrow. Format:

```
<ISO timestamp>  <proposal_id>  <target_node>  <update_type>  <source_kind>:<ref-hash>  <one-line content>
```

Miners read this log at the top of every run and skip any proposal whose source-ref + content hash matches a dismissed entry within the last 7 days. (After 7 days, re-surfacing is permitted — the user may have changed their mind.)

## Person-page graduation (Step 3.7)

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

## Reflection (Step 4)

#### Step 4.0 — Pre-fill from brief artifact (v4.13+ reads v0.7.0 shape)

Reuse the brief state already read in Step 2c (via the Step 2c.0 chain: state-mirror file `briefs/<today_local>.state.json` → widget context → paste path → fallback gate; canonical v0.7.0 shape: `tasks` / `annotations` / `outreach_actions` / `reflection`). Don't re-read if Step 2c already loaded it. If `state.reflection` is already populated (the user filled in Today's Reflection in the artifact), show it as the pre-fill for all three questions below rather than deriving from `done`/annotations separately, and skip straight to confirming it in Step 4.1.

Pre-fill the reflection prompts from the mined actions:

- **Biggest thing done** ← the "biggest thing done" candidates carried forward from Step 2c.4 (tasks with `action == "done"`, most-substantial first; title from `tasks[id].name`).
- **What blocked you** ← `annotations` containing "blocked", "stuck", "waiting"; and any `delegate` actions (handed off because blocked).
- **One thing tomorrow has to move** ← `annotations` containing "tomorrow", "P0", "must"; and the top surviving incomplete P0 from Step 2c.4.

**Sanitize, don't quote verbatim.** The annotation content may contain raw business context ("Sarah is unhappy with proposal terms" → render as "Issue with proposal discussion"). The reflection captures the user's read of the day; it should NOT include verbatim sensitive client content. See nucleus contracts.md "Data-flow trace for annotations" for the privacy reasoning.

If Cowork artifact tools aren't available (Claude Code), skip Step 4.0 and ask the three questions cold per Step 4.1 below.

#### Step 4.1 — Ask the reflection questions

Ask the user, conversationally, one at a time (pre-filled candidates from Step 4.0 shown as suggestions, not assumptions):

1. **"Biggest thing that got done today?"** — pre-fill with the most-substantial `done` task from Step 2c.4. User can accept, edit, or override. Captured as an INSIGHT (or DECISION if it was a choice) on the relevant project node.
2. **"What blocked you, if anything?"** (optional) — pre-fill with candidate blockers from annotations. Captured as a GOTCHA if structural, or as a BLOCKER on the project's open threads.
3. **"What's the one thing tomorrow has to move?"** — pre-fill with candidate priorities from annotations. Captured as a `[P0]` next-action on the relevant project node, dated tomorrow, AND fed to Step 4.5 + section 1 (Center of Gravity) of tomorrow's brief.

These three answers also feed Step 5's pre-stage as section 5 (Yesterday's Reflection) content of tomorrow's brief.

Keep conversational. If the user says "nothing major today," that's valid — skip to Step 5.

If the user provides answers, **append them to today's brief markdown snapshot** at `<config-root>/briefs/<today_local>.md` under a `## Reflection` section (v4.6+ — was Section 7 prior to briefing v0.3.0). Idempotent: if a `## Reflection` section already exists from a prior `/end-day` run today, replace its contents rather than duplicating.

Format:

```markdown
### Reflection

- **Biggest thing that got done today:** <answer or "—">
- **What blocked you:** <answer or "—">
- **The one thing tomorrow has to move:** <answer or "—">
- _Captured by /end-day at <HH:MM>._
```

This is the canonical write — tomorrow's `/brief` Section 5 (Yesterday's Reflection) reads from this section. If the user said "nothing major today," still write the `## Reflection` section with `—` placeholders and a "skipped" timestamp so tomorrow's brief shows the explicit non-event rather than "no reflection logged."

If `<config-root>/briefs/<today_local>.md` doesn't exist (user ran `/end-day` without ever generating today's brief), create the file with a minimal `# End-of-day reflection — <today>` header followed by the `## Reflection` section. Don't try to back-fill the missing brief content.

#### Step 4.2 — Append to the longitudinal reflection store (B.7 — v4.13+)

In addition to the per-day `## Reflection` in the brief markdown, append today's reflection to the rolling **`<config-root>/memory/me/reflections.md`** so reflections become a longitudinal, queryable record ("what have my biggest wins been this month," "what keeps blocking me"). This store is itself an input to `/end-week` / briefing's `/review` and to future surfacing decisions.

Create the file from `references/reflections-template.md` if missing (header + "newest first" convention). Append one dated block at the top of the log:

```markdown
### <today_local> (<Day>)
- **Biggest thing done:** <answer or "—">
- **What blocked you:** <answer or "—">
- **One thing tomorrow has to move:** <answer or "—">
```

Append-only; never rewrite prior entries. Idempotent for the same day (replace today's block if it already exists from a re-run). `reflections.md` decays slowly — it's a record, not a working surface — so it's excluded from the v4.4 decay sweep. Queue an index refresh (it's a memory file) so it appears in `index.md`.

## HubSpot logging (Step 4.7)

2. **If the user names things to log**, interpret each into a concrete HubSpot write and route via the HubSpot MCP (use the same tool surface the rest of Nucleus uses — `manage_crm_objects` for create/update, the HubSpot search tool to resolve named entities to object ids):
   - **Note / activity** on a contact, company, or deal → create the engagement/note and associate it to the right object (search the CRM for the named entity first).
   - **Task / follow-up** → create a task object, owner = user, due date as given (default tomorrow).
   - **Deal stage / property update** → update the deal's stage or property.
   - **New contact / company / deal** → create the object, pre-filled from what the user said + any matching cortex node context.
3. **Confirm before writing.** Present a single table of the intended HubSpot writes (object, action, key fields):
   ```
   Log to HubSpot:
     · Note → deal "Acme Corp" : "Sent phased plan; Fairview Fund ~July 1 creates pull"
     · Task → contact "Priya (VendorCo)" : "Confirm project ID" due tomorrow
     · Stage → deal "Beacon Analytics diagnostic" : Qualified → Proposal

   Approve each row: (y)es / (n)o / (e)dit
   ```
   Then get approval for each row before writing it (CRM writes are high risk in
   `references/autonomy-policy.md`; approving one row approves only that row). Report
   successes and failures. No mode setting removes this approval.
4. **Cross-link to memory.** For any HubSpot object that maps to a cortex person/bizdev/client node, append a one-line Recent Interactions / Changelog entry noting the CRM write, so the memory trail and CRM stay in sync. Reuse the growth `/touchpoint` path if growth is installed.

Record what was logged for the Step 6 close summary ("Logged to HubSpot: 1 note, 1 task, 1 stage move.").

## Pre-staging tomorrow's brief (Step 5)

1. Invoke its `/brief` command with `target_date: tomorrow_local`. `/brief` reads `<config-root>/briefs/<tomorrow_local>.seed.json` (written by Steps 4.5/4.6) if present and seeds sections 3 (Priority Tasks) & 4 (Outreach Queue) from it, then merges live pulls — so the priorities/outreach the user just walked are already on tomorrow's surface.
2. If Step 1 ran (full mode only), pass the inbox-triage results so the brief doesn't re-query Gmail. In quick mode, the brief queries Gmail itself in the morning — no shared state needed.
3. **Today's reflection is read by tomorrow's `/brief` Section 5 (Yesterday's Reflection) directly from today's markdown's `## Reflection` section** (briefing v0.5.0+). No explicit handoff from this step.
4. **Artifact consistency rule (v4.12.0+):** the brief generator MUST call `mcp__cowork__update_artifact` with id `todays-brief` to refresh the persistent Cowork artifact. **Never** create a new artifact and never produce only a markdown-only fallback when Cowork is available — the artifact id must remain stable so the user always opens the same persistent surface. If no `todays-brief` artifact exists yet, create it once with that id; update it on every subsequent `/end-day` and `/brief` run. The markdown snapshot at `<config-root>/briefs/<tomorrow_local>.md` is still written as the canonical text record, but the Cowork artifact is the working surface and must also be updated.
5. **Canonical artifact format (v4.13+ — 5 fixed sections per the End-Day Routine Improvement Spec Part A):** the `todays-brief` artifact always includes these sections in this order — (1) **Center of Gravity** accent banner (the single most important thing; not interactive), (2) **Calendar Block** = visual timeline strip + written block list with per-meeting notes, (3) **Priority Tasks** with richer per-row actions (done / delegate / skip / not_important / **reprioritize** / annotate) + progress bar, (4) **Outreach Queue** tiered (today / this week / backlog) with per-contact actions + optional category tags (bucket / value-add; signal auto-fills), (5) **Yesterday's Reflection** (read-only). A sticky header carries the date + counts line. localStorage key is `brief-YYYY-MM-DD` (schema_version 0.7.0); the artifact also mirrors its state to `briefs/<date>.state.json` for the close to read (D2a). All interactive controls are inline — the template uses **no** `prompt()`/`confirm()`/`alert()` (blocked in Cowork's artifact sandbox). Reference implementation: briefing v0.6.0+ ships this as `references/brief-artifact-template.html`; this Step 5 routes to that. Formatting MUST be identical whether produced by `/brief` or this pre-stage.
6. If Cowork artifact tools aren't available (Claude Code), produce the markdown snapshot only with a clear notice — but explicitly flag the degraded surface so the user knows to open the Cowork app for the full working brief.

## Memory commit (Step 5.8)

Check whether `<config-root>/memory/.git/` exists.
- **If exists** → proceed.
- **If not** → offer to initialize it once (closes the proposal's "next /end-day after upgrade runs init" migration path), respecting the autonomy slider:
  - `auto` → skip silently (don't init without consent — git init + first commit is a meaningful change); log a one-line note.
  - `suggest` (default) / `confirm` → prompt once: "Memory-as-git isn't initialized — it powers `/morning`'s overnight-diff review and rollback safety. Initialize `<config-root>/memory/` as a local git repo now? (y / not now / never)."
    - `y` → run the same init path as `/setup-identity` Step 3.6 (symlink-into-cloud-sync warning, write `memory/.gitignore` from `references/memory-gitignore-template.md`, `git init`, initial commit), then continue with today's commit below.
    - `not now` → skip this run; re-offer next `/end-day`.
    - `never` → write `memory_as_git.enabled: false` to `<config-root>/plugins/cortex.user-context.md` so this never re-prompts. Skip.
  - If, after the offer, `.git/` still doesn't exist → skip the rest of Step 5.8.

#### Step 5.8.0 — Memory write-lock acquisition (v4.12.2+)

Before any git operation, acquire the memory lock — the `git add`/`git commit` sequence below spans multiple shell commands, not one `cortex_cli.py` call, so use the paired acquire/release subcommands (see `scripts/lib/locking.py`'s `acquire_lock_for_external_section`/`release_lock_for_external_section` and `references/core-contract.md` §11):

```
python3 scripts/cortex_cli.py lock-acquire --memory-root <config-root>/memory --timeout 10 --stale-after 600
```

- On success (exit 0): proceed to Step 5.8.1.
- On failure (exit 1, timeout — lock held by another process past its staleness window): surface "Memory write-lock held by another process — skipping memory commit; retry next `/end-day`." Exit Step 5.8 with a status note. Continue to Step 6 (close). Do **not** manually delete the lock file — staleness reclaim is automatic and handled by the lock itself.

The same lock (and CLI) is used by `/listen`, `/morning`, `/remember`, `/note`, `/forget`, `/cleanup`, `/rehearse`, `/relink-memory`, and `/sync-linked-entities` for every node-file mutation — this is one shared lock, not a per-command one.

The lock is `memory/.lock` — covered by both gitignore variants (local-only and remote-safe).

#### Step 5.8.1 — Defensive .gitignore validation (v4.12.2+ fingerprint-precise)

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

#### Step 5.8.2 — Pre-commit index safety check (v4.12.2+)

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

#### Step 5.8.3 — Compose + commit

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

#### Step 5.8.4 — Post-commit verification (v4.12.2+)

```
post_status = git status --porcelain | wc -l
if post_status > 0:
  Surface: "⚠ Memory commit succeeded but working tree is still dirty: <files>. This may indicate a race (another command mutated memory mid-commit) or a hook side-effect. Inspect: cd <config-root>/memory && git status."
  Log the dirty state to memory/log.md.
```

#### Step 5.8.5 — Release the write-lock

```
python3 scripts/cortex_cli.py lock-release --memory-root <config-root>/memory
```

Run this on every exit path from Step 5.8 — success or failure — same as the old prose said, but now backed by real ownership-checked release logic instead of an unconditional `rm` (which could otherwise delete a different process's lock if this one's had already gone stale and been reclaimed).

**Optional push:**
- If `cortex.user-context.md` has `memory_as_git.remote: <url>` AND `memory_as_git.push_on_close: true`, run `git push <memory_as_git.remote_name, default "origin"> main` after commit.
- Default: no remote configured; commits are local-only.
- As of v4.18.3, `/morning` also runs this same commit+push (its Step 4) since it's the required daily touch and `/end-day` is optional. This copy stays for users who still run `/end-day` in full mode on a day `/morning` was skipped.

**Failure mode:** if commit fails (rare — usually merge conflict from external edits or git config error), log the error and continue to Step 6. Don't block the close on a maintenance task. Surface to user: "Memory-as-git commit failed — investigate `<config-root>/memory/.git` state."

**Idempotent:** empty commits are a no-op. Safe to run multiple times per day if the closing ritual runs twice.
