---
description: Nightly autonomous ingest. Pulls yesterday's calendar / Gmail / Slack / transcripts / Drive activity into immutable `<config-root>/archive/YYYY-MM-DD/`, mines yesterday's Today's Brief state (explicit marks + an unmarked-item inference pass) into closures/snoozes/reflection, runs the note-taker mining agent (modes: transcript, conversation, activity) against the archive, and stages all proposed memory commits as a single draft at `<config-root>/memory/staged/commit-drafts/YYYY-MM-DD.md`. Refreshes `<config-root>/memory/hot.md`. Designed for unattended scheduled execution. Pair with `/morning` to review and merge the draft.
---

# /listen

You are running the overnight ingest pipeline. This command is **unattended by design** — no user gates, no interactive prompts. It runs to completion or fails gracefully.

The output is a single review-ready draft the user merges via `/morning` the next day. `/listen` itself never modifies active memory nodes.

---

## Step 0 — Resolve config root and target date

Standard config-root pattern.

**Cloud-first materialize (v4.29+).** If no config-root resolves, or the resolved root is
the cloud default, run `python3 scripts/cortex_cli.py bootstrap --print-env` (adopting the
routine's repo checkouts with `--adopt-org`/`--adopt-private` when present) and use the
printed root. When the root is a synced checkout, `bootstrap` has already pulled both repos;
re-run `cortex_cli.py sync` at the end (Step 8.5). No Mac attachment is required.

**Config-root reachability check (hard gate — v4.28+).** Once `<config-root>` is
resolved, verify it is actually readable AND writable before doing anything else:
stat the directory, then write and immediately delete a probe file at
`<config-root>/memory/staged/queues/.listen-probe`. This is not a graceful no-op —
`/listen` is a scheduled task that can fire on a device/context that never had
`<config-root>` attached (e.g. a schedule registered without folder binding, or a
Mac where an external volume is unmounted), and a silent skip here is exactly the
failure mode this check exists to catch. If either the stat or the probe write/delete
fails:

1. Write a receipt using the same field names as ops's Step 5 schema (see
   `ops/commands/register-schedules.md` Step 5) to
   `<config-root or best-effort fallback path>/plugins/ops/schedule-runs/nightly-listen/<run_id>.json`
   if any writable location can be reached at all; otherwise emit the receipt to
   stdout so the scheduler's own run log captures it.
2. Set `status: "failed"`, `error_code: "config_root_unreachable"` on the receipt.
3. Exit non-zero. Do not report success, and do not proceed to Step 0.5 or beyond.

This hard gate applies only to the whole config root being unreachable. Graceful
degradation (log to `_index.md` under `## Errors` and continue) remains the correct
behavior for an individual connector failing — e.g. one calendar/Gmail/Slack source
being down does not abort the run; an unreachable config root does.

## Step 0.5 — Privacy defaults (v4.7.2+)

Before pulling any external data, ensure `<config-root>/.gitignore` exists and contains the privacy-sensitive paths. This is defensive — `/listen` is about to write raw email / Slack / transcript content to `archive/`, and we don't want that committed to a git repo silently.

Logic:
1. Check whether `<config-root>/.gitignore` exists.
2. If it doesn't exist, write it with the full template from `references/gitignore-template.md`. Log to stdout: "Wrote `.gitignore` with privacy defaults — see `references/gitignore-template.md` for what's protected and why."
3. If it exists, check whether `archive/` and `memory/staged/commit-drafts/` are listed. If either is missing, append the missing patterns under a section: `# Added by cortex /listen first-run — privacy defaults`. Don't reorder or delete user content.
4. Cloud-sync warning: check whether `<config-root>/` lives inside common cloud-sync paths (`~/Library/Mobile Documents/com~apple~CloudDocs/` for iCloud, `~/Dropbox/`, `~/OneDrive*/`, `~/Google Drive/`). If it does, log one line: "Heads up — `<config-root>` is inside <provider>. `.gitignore` does NOT prevent cloud sync. See `references/gitignore-template.md` cloud-sync section for alternatives (local-only archive via symlink)."

This step never blocks. If file write fails, log the error and continue — privacy defaults are best-effort, not blocking.

Determine target date:
- **No argument** → yesterday in identity time zone (most common case; default for scheduled runs at e.g. 11pm or 6am).
- `/listen --date YYYY-MM-DD` → that date.
- `/listen --backfill N` → run the pipeline once per day for the last N days that don't yet have archives. Each day produces its own draft.
- `/listen --remine YYYY-MM-DD` → skip the source-pull phase; only re-run mining against an existing archive. Produces `staged/commit-drafts/<date>-remine-<seq>.md` (doesn't overwrite the original).

If `<config-root>/archive/<target_date>/` already exists AND mode is not `--rewrite` or `--remine`, log "Archive for <date> already exists; skipping pull. Use --remine to re-run mining or --rewrite to force re-pull." and exit with status 0. **Do not silently overwrite a prior archive — it's the immutable substrate.**

---

## Step 0.7 — Write listen-in-progress marker (v4.12.2+)

Before any memory mutation, write `<config-root>/memory/staged/queues/listen-in-progress` with content `<iso8601-started>|<iso8601-expected-completion>` (expected completion = now + 30 min as a conservative default; can be adjusted based on archive size).

```
mkdir -p <config-root>/memory/staged/queues/
echo "$(date -Iseconds)|$(date -Iseconds -d '+30 min')" > <config-root>/memory/staged/queues/listen-in-progress
```

The marker is read by `/morning` Step 0.5.0 Check 3 to detect a still-running /listen and pause the diff review until completion.

The marker is deleted at the end of Step 7.5 (Log to chronicle), on success or failure.

If the marker already exists when /listen starts:
- Read its content; check if expected_completion is in the past + 2 min grace → treat as stale, overwrite.
- Otherwise surface: "Another /listen is already running (started <X> min ago, expected complete <Y> min from now). Exit and let it finish? (y to exit / f to force-overwrite)"

## Step 0.8 — Acquire memory write-lock (v4.12.2+)

Same pattern as `/end-day` Step 5.8.0. Acquire `<config-root>/memory/.lock`:

```
LOCK_PATH = <config-root>/memory/.lock
If LOCK_PATH exists:
  age_seconds = now - <acquired-at from file content>
  If age_seconds > 600:
    Treat as stale; remove and proceed.
  Else:
    Surface: "Memory write-lock held by <command> — /listen will wait 60s and retry once." Sleep, retry. After two retries, abort with "Memory busy — try /listen again later." Note: /listen runs unattended (cron), so on abort, log to memory/log.md and exit cleanly.
Else:
  Write "listen|<iso8601-now>|<session-id-or-pid>" to LOCK_PATH.

# Lock released at end of Step 7.5 — or any failure path — by deleting LOCK_PATH.
```

## Step 1 — Pull yesterday's substrate (skipped in --remine)

For each enabled note source per `<config-root>/plugins/cortex.user-context.md` and `/setup-sources`:

### Calendar (Calendar MCP)
Pull events where start_date matches `target_date` in the user's time zone. Skip blocked time and personal events. Write to `<config-root>/archive/<target_date>/calendar.md` per the format in `references/archive-layout.md`.

### Gmail (Gmail MCP)
Gmail search: `after:<target_date> before:<target_date+1> (to:me OR cc:me)` AND the user is not the most recent sender on the thread. Cap at 50 threads. Default privacy: metadata + 200-char snippet only. If `listen.inbox.full_body: true` is set in user-context, include full message body. Write to `archive/<target_date>/inbox.md`.

### Slack (Slack MCP — optional)
For each channel the user has joined, pull messages from `target_date` where (a) the user was @mentioned, or (b) the user authored the message. Cap 100 messages total. Write to `archive/<target_date>/slack.md` grouped by channel.

### Drive (Drive MCP — optional)
For each watched folder per user-context, list files modified or created on `target_date`. Metadata only. Write to `archive/<target_date>/drive.md`.

### Transcripts (per-adapter)
For each configured note source per `/setup-sources` and `agents/lib/note-source-adapters.md`:
- Granola: query Granola API for meetings dated `target_date`.
- Gemini: query Gemini meetings.
- Fireflies / Otter: same.
- Generic Drive folder: walk the configured transcript folder for files created on `target_date`.

For each transcript found, write `archive/<target_date>/transcripts/<meeting-id>-<slug>.md` with front-matter (source adapter, original ID, title, participants, date) and the transcript body.

### Failures
Each source-pull failure is logged to `archive/<target_date>/_index.md` under `## Errors`. Do not abort the whole pipeline on a single source failure — proceed with what was successfully pulled.

---

## Step 1.5 — Mine yesterday's brief (v4.27+)

The brief is the user's most explicit daily signal. This step is what makes marking something done / delegate / skip / not important / reprioritized in the artifact actually round-trip into memory, the next brief, and `/relationships`, without depending on `/end-day`. Runs in **both** the normal pull and `--remine` modes; runs even when `target_date`'s brief state is missing or empty (the inference pass still has value against the archive just pulled in Step 1).

### Step 1.5a — Read and archive the brief state

**Preflight:** read `<config-root>/briefs/.artifact-runtime.json` (written and overwritten on every publish by `/brief` Step 3.0). If it names a hosted artifact with a `capability: "db"`, read document `briefs/<target_date>` from that artifact's database (collection `<collection>` from the runtime file, doc_id `<target_date>` per `doc_id_pattern`) and write it to `<config-root>/briefs/<target_date>.state.json` before continuing. If `.artifact-runtime.json` is absent, or names no `db` capability, this is a no-op (desktop Cowork mirrors the state file directly and never needs this). If the file is present but the read fails (capability unreachable, doc missing, malformed runtime file), log it to `archive/<target_date>/_index.md` under `## Errors` and continue with whatever `<target_date>.state.json` already exists on disk — never block the rest of `/listen` on this read.

Read `<config-root>/briefs/<target_date>.state.json`. Tolerate:
- `tasks_checked`-only blobs (v0.4.x) — treat each `true` as `{action: "done"}`.
- Entries with `reprioritized: true` and no `action`.
- Missing `reflection` / `return_on` fields (0.4.x–0.6.0) — treat as absent, not an error.

If the file exists, copy it verbatim to `<config-root>/archive/<target_date>/brief-state.json`. If it doesn't exist, note that in the archive index (Step 2) and skip to Step 1.5d (inference still runs).

### Step 1.5b — Map ids to titles and nodes

Read `<config-root>/briefs/<target_date>.md` (and `<target_date>.seed.json` if present) so `task-<id>` / `outreach-<id>` / `event-<id>` map back to titles, related nodes, and (for outreach) person/bizdev slugs.

### Step 1.5c — Explicit marks become proposals (skipped if already processed)

If `<config-root>/briefs/<target_date>.state.processed` exists, `/end-day` Step 2c already wrote these back today — skip straight to Step 1.5d (inference-only). Otherwise, for each entry in `tasks` / `annotations` / `outreach_actions`, stage a proposal in the Step 4 commit draft using the **same semantics as `/end-day` Step 2c.1–2c.3**:

| Signal | Proposal |
|---|---|
| `done` | Close the source-node action (project node `## Next Actions` → COMPLETED) + propose completing the linked HubSpot task (never auto-write CRM — this is a proposal, reviewed at `/morning`). Carry as a "biggest thing done" candidate. |
| `delegate` (detail = who) | Reassign proposal (`[WAITING:<who>]` on the source node; CRM delegatee task if connected). |
| `skip` (detail, return_on) | Write a snooze-ledger entry (Step 1.5h) — this is a direct write, not a proposal, per the Constraints below — and propose incrementing the skip counter. |
| `not_important` | Do-not-resurface proposal on `surfacing-prefs.md`, plus close/demote the source node action. |
| `reprioritized: true` + `priority` | Priority-edit proposal on the source node's `[P0]`/`[P1]`/`[P2]` tag. Applies whether or not `action` is also set. |
| task/outreach `annotations` | Carried verbatim as a proposal (or a carry-forward note if no clear action) — same routing families `/process-brief` Step 2 uses (draft_reply / reschedule_task / dismiss / clarify) when not already actioned there today. |
| calendar-note `annotations["event-<id>"]` | Touchpoint / person-node proposal on the linked attendee's node. |
| outreach `sent` / `nudge` / `booked` / `let_go` | Touch-log proposal on the person/bizdev node, **and** append an event to growth's `<config-root>/relationships/events.jsonl` in its existing shape (`ts, brief_id: null, option_id: "outreach-<id>", person_slug, bucket, channel: null, action: <sent|nudge|booked|let_go mapped to growth's copied\|sent\|skipped\|snoozed vocabulary>, notes: <annotation if any>`) — this is a direct append (see Constraints), not a proposal, matching how `/relationships-action` already writes this file. |

Never auto-close a node action or write CRM directly from this step — those are proposals for `/morning`.

### Step 1.5d — Inference pass (always runs)

For each task and outreach item on `<target_date>`'s brief with **no explicit mark** (present in the seed/markdown list but absent from `tasks`/`outreach_actions`, or the state file was missing entirely), check the archive just pulled in Step 1 (sent mail, calendar, transcripts, CRM activity via note-taker's `mode: activity` pass) for evidence it was handled. Emit a "likely done" proposal citing the specific evidence (e.g. "sent mail to X at 3:14pm referencing this") with a confidence rating (high/medium/low). **Never auto-close on inference** — these are proposals like everything else, walked at `/morning` alongside the explicit ones.

### Step 1.5e — Write closures.json

Write `<config-root>/briefs/<target_date>.closures.json`:

```json
{
  "closed":     [{"id": "task-123", "title": "...", "source": "marked", "evidence": null}],
  "carried":    ["task-456"],
  "snoozed":    [{"id": "outreach-789", "return_on": "2026-09-20"}],
  "suppressed": ["task-321"],
  "annotations": {"task-456": "waiting on legal"}
}
```

`closed` entries from Step 1.5c get `source: "marked"`; `closed` entries from Step 1.5d's high-confidence inferences that the user hasn't reviewed yet do NOT belong here — this file only records what's actually decided (explicit marks). Inferred-likely-done items stay as commit-draft proposals until `/morning` accepts them; only then does a follow-up `/listen --remine` (or the next night's run, once `/morning` has merged) add them here. This is the machine-readable handoff `/brief` Step 0D0 reads to drop closed/suppressed items and hide snoozed ones.

**Authority note:** if `<target_date>.closures.json` already exists when `/listen` reaches this step (e.g. `briefing`'s `/brief` Step 0D0 wrote one under its own `written_by: "/brief fallback"` marker because `/listen` hadn't run yet for that date), treat the existing file as authoritative and do NOT overwrite it — `/listen` merges its own findings by writing a `-remine` companion (per Step 0's `--remine` naming) instead of clobbering the fallback record. This keeps whichever command ran first as the source of truth rather than letting a later run silently discard it.

### Step 1.5f — Unattended-safe

No prompts, no paste path, no fallback gate — this step runs exactly like the rest of `/listen`. If `<target_date>.state.json` is unreadable and no fallback source yields a blob, log one honest line to `archive/<target_date>/_index.md` ("Brief state: absent, inference pass only") and continue to Step 1.5d. If the brief markdown/seed list is also missing, log "Brief state: absent, no task list on disk, skipped" and continue to Step 2.

### Step 1.5g — Reflection carry-forward

Read `state.reflection` for `target_date`. If present and non-empty:
- If `<config-root>/briefs/<target_date>.md` does not already have a `## Reflection` section, write one in the **exact format** `/morning` Step 4.6 and `/end-day` Step 4.1 use (so `/brief` Section 5 and Center of Gravity read it unchanged):
  ```markdown
  ## Reflection

  - **Biggest thing that got done today:** <reflection.biggest or "—">
  - **What blocked you:** <reflection.blocked or "—">
  - **The one thing tomorrow has to move:** <reflection.one_thing or "—">
  - _Captured by /listen at <HH:MM>, from the brief artifact._
  ```
- If `## Reflection` already exists for that date (e.g. `/end-day` or `/morning` already wrote one), do **not** overwrite it — log "Reflection already present for `<target_date>`, left as-is" and move on.
- Also stage the reflection as a commit-draft proposal targeting `<config-root>/memory/me/reflections.md`, in the same block format `/end-day` Step 4.2 uses, for `/morning` to accept.

### Step 1.5h — Snooze ledger + growth sync

`<config-root>/briefs/.snooze-ledger.json` is the canonical snooze ledger for the brief, keyed by brief item id — **this file is owned by the brief, not by growth**. Shape:

```json
{
  "task-123":    {"title": "...", "kind": "task", "node": "...", "return_on": "2026-09-22", "skipped_on": "2026-09-17", "skip_count": 2, "last_detail": "3d"},
  "outreach-45": {"title": "...", "kind": "outreach", "node": "person/sarah-chen", "return_on": "2026-09-20", "skipped_on": "2026-09-17", "skip_count": 1, "last_detail": "3d"}
}
```

For every `skip` action from Step 1.5c: write or update this entry (increment `skip_count` if one already exists for this id, else start at 1). This feeds the repeat-ignore rule the same way `.brief-skip-counts.json` always has — for tasks specifically, keep incrementing the existing `.brief-skip-counts.json` counter too (don't fork the repeat-ignore data source; the ledger's `skip_count` and the skip-counts file should agree for task ids).

For every ledger entry with `kind: "outreach"` whose `node` resolves to a known `memory/person/<slug>.md`: **also** write/update the matching entry in `<config-root>/relationships/snoozes.json` (growth's existing file, read by `/relationships` Step 3) — `{"slug": <slug>, "until_date": <return_on>, "reason": <last_detail>, "snoozed_at": <ISO now>}`. `/listen` is the only writer that keeps both files in sync; growth's file stays the single source `/relationships` reads, the brief ledger stays the single source `/brief` reads.

`let_go` / `dead` outreach actions and `not_important` task actions **delete** the corresponding ledger entry (and, for outreach, the matching `snoozes.json` entry) rather than updating it — the item is dead, not snoozed.

### Step 1.5j — Write the scheduled-run receipt

After closures.json (1.5e), the snooze ledger + growth sync (1.5h), and the
`## Reflection` section (1.5g) are all written, emit one metadata-only receipt using
the same field names as ops's Step 5 schema (`ops/commands/register-schedules.md`
Step 5), to `<config-root>/plugins/ops/schedule-runs/nightly-listen/<run_id>.json`:

```json
{
  "schema_version": "1.0.0",
  "run_id": "<host run id or UUID>",
  "schedule": "nightly-listen",
  "started_at": "<ISO-8601>",
  "ended_at": "<ISO-8601>",
  "outcome": "succeeded",
  "state_source": "state.json | artifact-db | none",
  "counts": {"closed": 0, "carried": 0, "snoozed": 0, "suppressed": 0, "reflection_written": false},
  "error_codes": []
}
```

`counts` reflects what Step 1.5e/1.5g actually produced for `target_date`. If
`<target_date>.state.json` was missing on disk AND the `.artifact-runtime.json`
preflight (1.5a) yielded nothing, set `state_source: "none"` and all counts to zero
except whatever the inference pass (1.5d) staged as commit-draft proposals — a run
that mined zero brief items because state was genuinely absent must say so plainly
in the receipt rather than being indistinguishable from "nothing happened to mine."

### Constraints on this step specifically

Per the command's overall unattended/read-only design, Step 1.5 is allowed to write **directly** (not as staged proposals) to: the archive copy (1.5a), `closures.json` (1.5e), the snooze ledger + its growth mirror (1.5h), `.brief-skip-counts.json` (1.5c/h), growth's `events.jsonl` append (1.5c), and the `## Reflection` section of that day's twin (1.5g) — these are mechanical record-keeping, not memory-node mutation. Everything that touches an active memory node (person/project/client/bizdev pages, `surfacing-prefs.md`, `reflections.md`) stays a commit-draft proposal, same as the rest of `/listen`.

### Step 1.5i — Idempotency

If `<config-root>/briefs/<target_date>.state.processed` exists (written by `/end-day` Step 2c when the user ran it for that date — see that command), skip Step 1.5c's explicit write-backs entirely (already done) and run only Step 1.5d's inference pass for genuinely unmarked items. `--remine` on a date already mined by this step must not duplicate: before staging any proposal, event-log append, or ledger write, check whether an equivalent entry already exists (same id + same action) in that date's prior commit draft / `events.jsonl` / ledger, and skip it if so. The `## Reflection` section write in 1.5g is itself idempotent by construction (Step 1.5g's own check).

---

## Step 2 — Write the archive index

After all sources complete, write `archive/<target_date>/_index.md`:

```markdown
# Archive index — <target_date>

Generated by /listen at <ISO timestamp>.

## Counts
- Calendar events: <N>
- Inbox threads: <N>
- Slack mentions: <N>
- Drive changes: <N>
- Transcripts: <N>
- Brief state: read | absent | processed-skip
- Brief proposals staged: <N> (<M> closures, <K> snoozed, <inference-count> inferred)

## Sources pulled
- Calendar MCP: ok | skipped | error
- Gmail MCP: ok | skipped | error
- Slack MCP: ok | skipped | error
- Drive MCP: ok | skipped | error
- Granola adapter: ok (<N> meetings) | skipped | error
- ...

## Errors
- (none) or list with retry hints
```

This file is the canonical "what did /listen accomplish" record.

---

## Step 3 — Run note-taker against the archive

Now mine the archive into proposed memory commits. Invoke `note-taker` once per mode — all three modes run **read-only against the archive** and **read-only against active memory**; they propose, they never write to nodes directly.

### mode: transcript
Invoke `note-taker` with `mode: "transcript"`:
- Scope: `<config-root>/archive/<target_date>/transcripts/`
- Cross-reference: active person pages + open threads on project/client nodes
- Output: proposed knowledge entries (INSIGHT, MODEL, GOTCHA, LESSON), proposed commitments (to / from others), proposed person-page updates.

### mode: conversation
Invoke `note-taker` with `mode: "conversation"`:
- Scope: Cowork session metadata for `target_date` (via session-info MCP if available)
- Cross-reference: active project nodes
- Output: proposed knowledge entries, proposed user-observation updates.

### mode: activity
Invoke `note-taker` with `mode: "activity"`:
- Scope: `archive/<target_date>/calendar.md`, `inbox.md`, `slack.md`, `drive.md`
- Cross-reference: active person + client + topic nodes
- Output: proposed person-page entries (interactions, status), proposed open-thread updates, proposed commitment captures.

All three modes return structured proposal lists. Aggregate them.

---

## Step 4 — Stage the commit draft

Write all proposals to a single file: `<config-root>/memory/staged/commit-drafts/<target_date>.md`.

Structure:

```markdown
# Commit draft — <target_date>

Generated by /listen at <ISO timestamp>.
Total proposals: <N> across <M> nodes.

## Summary
- <P> proposed knowledge entries
- <Q> proposed person-page updates
- <R> proposed commitments
- <S> proposed thread updates / closures

## Proposals

### Proposal 1 — <node>: <one-line summary>
- **Type:** INSIGHT | MODEL | GOTCHA | LESSON | RECIPE | CORRECTION | person-update | thread-update | commitment
- **From:** note-taker (mode: transcript) | note-taker (mode: conversation) | note-taker (mode: activity)
- **Source:** archive/<target_date>/<file> (line <N> or section <X>)
- **Proposed content:**
  > <verbatim or near-verbatim text to add>
- **Target placement:** `<node-path>` · section `<section-name>`
- **Confidence:** high | medium | low
- **Conflicts:** <list of existing entries on the same node this might supersede / contradict; or "none">

### Proposal 2 ...
```

Sort by priority (Critical / High / Medium / Low) within type. Group by source agent for transparency.

This file is what `/morning` walks the user through. It is **not** active memory — it's a draft for review.

---

## Step 5 — Refresh `<config-root>/memory/hot.md`

```
python3 scripts/cortex_cli.py refresh-hot --memory-root <config-root>/memory --trigger listen
```

Implemented in `scripts/lib/hot_cache_generator.py` (see `references/hot-cache.md` for the spec and its current scope). Pure file walk + filter + render. Zero LLM cost.

After this step, the morning's `/recall` auto-fire will load the freshest possible context including yesterday's activity.

---

## Step 6 — Telemetry (optional)

If `ops` is installed, log one line via `/log-agent-run`:
```
skill: listen, date: <target_date>, archive_size_bytes: <N>, proposals_count: <M>, runtime_ms: <T>
```

---

## Step 7 — Retention tail (weekly)

Once per week (e.g., when `target_date` is Sunday), additionally:
- Compress `archive/YYYY-MM-DD/` directories older than 30 days into monthly tarballs at `archive/YYYY-MM.tar.gz`. Use OS-native compression (tar / gzip).
- Do NOT delete tarballs > 180 days old silently. Prompt-style retention requires user interaction; `/listen` skips it.

If today is not Sunday, skip Step 7.

---

## Step 7.5 — Log to chronicle (v4.7.1+, centralized in v4.7.2+)

Invoke the `log-writer` skill (see `skills/log-writer/SKILL.md`) with:
- **op_name:** `listen`
- **summary:** `archived <target_date> (<events> events, <inbox> inbox, <mentions> mentions, <transcripts> transcripts, <errors> errors). <P> proposals staged.`

The log-writer creates `log.md` if missing, writes the timestamped entry, and returns a best-effort status. If the write fails, continue — don't fail the `/listen` run on an audit-log error.

---

## Step 8 — Exit

Print a one-line summary to stdout (visible to scheduled-task logs):

```
/listen <target_date> complete: <N> proposals staged in staged/commit-drafts/<target_date>.md. Run /morning to review.
```

## Step 8.5 — Publish and health trace (v4.29+)

In a `finally`-equivalent that runs on success AND failure:

1. Append one line to `<config-root>/memory/staged/listen-health.md`:
   `<iso8601> OK <date>: <N> proposals (...)` or `<iso8601> FAILED <date>: <reason>` or
   `<iso8601> NOOP: ...`. Written on every run, scheduled or manual.
2. Refresh `hot.md` (Step 5) before this if the run succeeded.
3. Run `python3 scripts/cortex_cli.py sync --root <config-root>`. Exit non-zero if it fails.
   A failed sync is a failed run: say so in the summary line and notify (below).
4. If any step failed, send a Slack DM / push notification with the one-line reason, since a
   failed sync means the health line never reached GitHub.

## Step 8 — Release locks (v4.12.2+)

Always (success or failure path):

```
rm <config-root>/memory/staged/queues/listen-in-progress 2>/dev/null
rm <config-root>/memory/.lock 2>/dev/null
```

Both removals are silent on no-op. Use `trap` semantics in shell or `try/finally` in code — the locks MUST be released even if Step 1-7 errored. Otherwise subsequent `/listen` or `/morning` runs will see stale locks.

Exit with status 0 on success; non-zero only on hard failures (config-root missing, all sources failed, etc.).

---

## Behavior rules

- **No interactive prompts.** `/listen` is designed for cron. Errors go to the archive's `_index.md`, not to the user.
- **Idempotent on the archive.** Re-running for the same date without `--rewrite` is a no-op.
- **Privacy-conservative.** Default to metadata-only for inbox / Slack. Full bodies only with explicit opt-in via user-context.
- **Never modify active memory.** Proposals stage to `staged/commit-drafts/`. The user gates the merge.
- **Skip silently when empty.** If a date had zero source data (weekend, vacation), still write a minimal `_index.md` noting zero activity. Don't stage an empty draft — skip the draft entirely and log "no activity to mine."
- **Honor adapter health.** If `/setup-sources` flagged an adapter as unhealthy in its last health-check, skip that adapter's pull and note in `_index.md`.

---

## Scheduling

Recommended schedule (register via `/register-schedules` in ops):

```yaml
- name: listen-nightly
  cron: "0 23 * * *"          # 11pm local
  command: /listen
  args: ""
```

Alternative early-morning schedule (if user prefers proposals to be fresh at start of day rather than waiting overnight):

```yaml
- name: listen-early-am
  cron: "0 5 * * 1-5"          # 5am weekdays
  command: /listen
  args: ""
```

**Cloud-only (v4.29+, preferred).** Register as a cloud routine with no device attached
(no `requires-computer`). Prompt contract: bootstrap, catch-up date walk over missing
`archive/<date>/_index.md` (cap 3), `/listen` per date including the brief-state read from
the hosted artifact (Step 1.5a), `hot.md` refresh, Step 8.5 publish + health line on every
run, then a one-line summary message. Pair with a Mac `launchd` job running
`cortex_cli.py sync` so the local copy follows.

Both work. The 11pm version means the proposals exist by the time the user wakes up; the 5am version means they're as fresh as possible.

---

## What this command does NOT do

- Does not modify active memory directly — brief mining (Step 1.5) stages proposals just like every other source; the only direct writes are the mechanical record-keeping listed in Step 1.5's Constraints (archive copy, closures.json, snooze ledger + growth mirror, skip counters, events.jsonl, the twin's `## Reflection` section).
- Does not invoke `gap-researcher` (web research) — that's `/research-gaps`.
- Does not invoke, render, or generate the brief artifact — it reads brief **state** (Step 1.5) but never calls `/brief` and never touches the artifact itself.
- Does not run mining synchronously with the user (that's what `/end-day` is for, when the user chooses to run it instead of waiting for `/listen` + `/morning`).
- Does not chain into `/morning` — they're separate commands by design.
- Does not skip `--remine` runs based on `_index.md` errors; re-mining is always allowed against an existing archive.
- Does not prompt, ever, for brief mining either — no paste path, no fallback gate. Missing or unreadable brief state degrades to inference-only (Step 1.5f), never to a question.
