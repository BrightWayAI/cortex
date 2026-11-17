<!-- Loaded by commands/listen.md Step 1.5. This is the full procedure; the command file holds only a summary. -->

# /listen Step 1.5 — Mine yesterday's brief

The brief is the user's most explicit daily signal. This step is what makes marking something done / delegate / skip / not important / reprioritized in the artifact actually round-trip into memory, the next brief, and `/relationships`, without depending on `/end-day`. Runs in **both** the normal pull and `--remine` modes; runs even when `target_date`'s brief state is missing or empty (the inference pass still has value against the archive just pulled in Step 1).

## Step 1.5a — Read and archive the brief state

**Preflight:** read `<config-root>/briefs/.artifact-runtime.json` (written and overwritten on every publish by `/brief` Step 3.0). If it names a hosted artifact with a `capability: "db"`, read document `briefs/<target_date>` from that artifact's database (collection `<collection>` from the runtime file, doc_id `<target_date>` per `doc_id_pattern`) and write it to `<config-root>/briefs/<target_date>.state.json` before continuing. If `.artifact-runtime.json` is absent, or names no `db` capability, this is a no-op (desktop Cowork mirrors the state file directly and never needs this). If the file is present but the read fails (capability unreachable, doc missing, malformed runtime file), log it to `archive/<target_date>/_index.md` under `## Errors` and continue with whatever `<target_date>.state.json` already exists on disk — never block the rest of `/listen` on this read.

Read `<config-root>/briefs/<target_date>.state.json`. Tolerate:
- `tasks_checked`-only blobs (v0.4.x) — treat each `true` as `{action: "done"}`.
- Entries with `reprioritized: true` and no `action`.
- Missing `reflection` / `return_on` fields (0.4.x–0.6.0) — treat as absent, not an error.

If the file exists, copy it verbatim to `<config-root>/archive/<target_date>/brief-state.json`. If it doesn't exist, note that in the archive index (Step 2) and skip to Step 1.5d (inference still runs).

## Step 1.5b — Map ids to titles and nodes

Read `<config-root>/briefs/<target_date>.md` (and `<target_date>.seed.json` if present) so `task-<id>` / `outreach-<id>` / `event-<id>` map back to titles, related nodes, and (for outreach) person/bizdev slugs.

## Step 1.5c — Explicit marks become proposals (skipped if already processed)

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

## Step 1.5d — Inference pass (always runs)

For each task and outreach item on `<target_date>`'s brief with **no explicit mark** (present in the seed/markdown list but absent from `tasks`/`outreach_actions`, or the state file was missing entirely), check the archive just pulled in Step 1 (sent mail, calendar, transcripts, CRM activity via note-taker's `mode: activity` pass) for evidence it was handled. Emit a "likely done" proposal citing the specific evidence (e.g. "sent mail to X at 3:14pm referencing this") with a confidence rating (high/medium/low). **Never auto-close on inference** — these are proposals like everything else, walked at `/morning` alongside the explicit ones.

## Step 1.5e — Write closures.json

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

## Step 1.5f — Unattended-safe

No prompts, no paste path, no fallback gate — this step runs exactly like the rest of `/listen`. If `<target_date>.state.json` is unreadable and no fallback source yields a blob, log one honest line to `archive/<target_date>/_index.md` ("Brief state: absent, inference pass only") and continue to Step 1.5d. If the brief markdown/seed list is also missing, log "Brief state: absent, no task list on disk, skipped" and continue to Step 2.

## Step 1.5g — Reflection carry-forward

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

## Step 1.5h — Snooze ledger + growth sync

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

## Constraints on this step specifically

Per the command's overall unattended/read-only design, Step 1.5 is allowed to write **directly** (not as staged proposals) to: the archive copy (1.5a), `closures.json` (1.5e), the snooze ledger + its growth mirror (1.5h), `.brief-skip-counts.json` (1.5c/h), growth's `events.jsonl` append (1.5c), and the `## Reflection` section of that day's twin (1.5g) — these are mechanical record-keeping, not memory-node mutation. Everything that touches an active memory node (person/project/client/bizdev pages, `surfacing-prefs.md`, `reflections.md`) stays a commit-draft proposal, same as the rest of `/listen`.

## Step 1.5i — Idempotency

If `<config-root>/briefs/<target_date>.state.processed` exists (written by `/end-day` Step 2c when the user ran it for that date — see that command), skip Step 1.5c's explicit write-backs entirely (already done) and run only Step 1.5d's inference pass for genuinely unmarked items. `--remine` on a date already mined by this step must not duplicate: before staging any proposal, event-log append, or ledger write, check whether an equivalent entry already exists (same id + same action) in that date's prior commit draft / `events.jsonl` / ledger, and skip it if so. The `## Reflection` section write in 1.5g is itself idempotent by construction (Step 1.5g's own check).

The scheduled-run receipt that used to be Step 1.5j is now Step 1.6 in `commands/listen.md`.
