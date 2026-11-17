---
description: Commit this conversation to working memory. Default (full extraction) pulls knowledge, decisions, insights, open threads, and next actions from the whole conversation. `--quick [node] [content]` skips extraction for a one-line changelog note. `--knowledge <type> [node] [content]` skips extraction for a single typed knowledge entry. Also flushes any observations accumulated by the passive learning engine. Full mode can run user-triggered or silent (auto-triggered at conversation end).
---

# /remember $ARGUMENTS

You are committing something to working memory. Pick the mode that matches the invocation and follow it. Prompts, extraction lists, file formats and procedures are in `references/remember-formats.md`; read it before Step 2 in full or silent mode. Where it differs from this file, this file wins.

## Rules that hold in every mode

- **Guard first.** Run `python3 scripts/cortex_cli.py root-status`. If it exits non-zero, stop and show its sentence verbatim; write nothing and do not ask for folder access more than once per session. Exception: in a remote session with the sync repos attached, run `bootstrap` (`references/core-contract.md` §11B) once and re-check.
- **Resolve `<config-root>`** per `references/core-contract.md` §1; never hardcode a path. In Cowork request the directory with `mcp__cowork__request_cowork_directory(path=<config-root>)` and wait. If memory is inaccessible, say it cannot persist and stop.
- **Every memory write goes through `scripts/cortex_cli.py`.** Never hand-edit a node file. Each call takes and releases the shared write lock itself; there is no separate lock or release step. The three section commands, each `--memory-root <config-root>/memory "<node-relative-path>" "<heading>" "<text>"`:
  - `prepend-section` adds an entry at the top of a section (newest first). Used for `## Changelog`.
  - `append-section` adds an entry at the end of a section. Used for knowledge entries under their type heading (`### Insights`, `### Lessons`, `### Models`, `### Recipes`, `### Gotchas`, `### Corrections`), people, signals and next actions.
  - `replace-section` replaces a section's content. Used for `## Summary` and for rewriting a section when an entry moves out of it.
  Each creates the node file from the standard template, and the section, if absent. Node IDs map to paths per `references/core-contract.md` §3 (`client:acme-corp` and `client/acme-corp` are the same file).
- **If the lock times out**, retry once. If it is still held, say "Memory write-lock held by another process. Nothing was saved; run `/remember` again in a moment." and stop. Never delete or override the lock.
- **Nothing is silently removed.** An entry that is outdated or contradicted is moved to the node's `## Demoted knowledge` section with `↳ demoted <today> by supersede` and `↳ superseded by: <new entry>`, keeping its tags. Past changelog lines are never modified.
- **Decisions are records.** A decision is written with `record-decision` (Step 3), never as an inline entry, in every mode.
- **Entity references are wikilinks.** Emit `[[<type>/<slug>]]` when the node exists; otherwise the bare name, and count the mention in `<config-root>/memory/.person-mention-counts.json`.

## Modes

| Mode | Trigger | What runs | What the user sees |
|---|---|---|---|
| **Full** | `/remember`, no flag | Steps 0 to 5 | The Step 5 summary, or one line if nothing was worth saving |
| **Silent** | Auto, at conversation end | Steps 0 to 5 | Nothing, with the Step 5 exceptions |
| **Quick** | `/remember --quick [node] [content]` | Quick mode only | One line |
| **Knowledge** | `/remember --knowledge <type> [node] [content]` | Knowledge mode only | The committed entry |

`/note` and `/learn` are aliases for quick and knowledge mode.

## Quick mode

No triage, no extraction, no continuity check.

1. **Parse** the node (infer from context; ask if missing or ambiguous) and the content (everything after the node).
2. **Write** one line with `prepend-section`:
   ```
   python3 scripts/cortex_cli.py prepend-section --memory-root <config-root>/memory \
     "<node-relative-path>" "## Changelog" "[node-id] LOG YYYY-MM-DD — Note: [content]"
   ```
3. **Dashboard**: update `DASHBOARD.md`'s "Last updated" timestamp. Touch the node's summary there only for a significant state change.
4. **Confirm** with exactly one line: `Noted in [node-id]: [content]`. No analysis and no follow-up questions.

If the content reads like a gotcha, lesson or model, add one suggestion: "This sounds like a [type]. Want me to `/remember --knowledge [type]` it so it's easier to find later?" Each quick call is independent.

## Knowledge mode

No triage and no changelog entry.

1. **Parse** node, type and content. Infer the type when omitted, using the table in the reference (Insight, Lesson, Model, Gotcha, Recipe, Correction, Decision). Ask only if the node or type is truly ambiguous.
2. **A decision** goes through `record-decision` as in Step 3, then stop at the confirmation.
3. **Drift check** (skip for a Recipe): if the new entry contradicts or replaces an existing entry of the same type on that node, show both and ask: (s)upersede, (k)eep both, or skip. Supersede demotes the old entry as in the rules above. If it only reinforces an existing entry, write nothing and say so.
4. **Write** `[node-id] TYPE (YYYY-MM-DD): [content, compressed but precise] [confirmed:<today>] [recalled:<today>] [by:<actor-id>]` with `append-section` under the matching type heading. If the knowledge spans nodes, write it to each.
5. **Dashboard**: add it to Recent Knowledge; add the node to Active Nodes if new; update the node's summary only if this changes its current state.
6. **Confirm**: `Committed to [node-id]:` then `[TYPE]: [content]`, plus "This replaces a previous [TYPE] entry from [date]." when it does.

## Step 0 — Triage (full and silent)

Before any extraction, run the low-cost classifier in **Triage** in the reference on the last ~30 turns. It returns `{"commit": true, "nodes": [...], "reason": ...}` or `{"commit": false, "reason": ...}`. A response that cannot be parsed counts as `commit: true` for the detected project node.

- **`commit: false`**: add one entry to `<config-root>/memory/triage-log.md` and run nothing else: no extraction and no memory writes. In silent mode say nothing. In full mode, because the user asked, say one line: "Nothing worth saving from this conversation." and offer `/remember --quick` if they want a note anyway.
- **`commit: true`**: add one entry to `triage-log.md` with the node list, then continue, passing the nodes to Step 1 as a hint.

A correction or stated preference from the user always counts as commit-worthy, at least for the `user` node.

**Skip triage** when the user named a node (`/remember client:acme-corp`), when the conversation has an explicit `[ENTITY:person]` tag for a new person, and for items passed in already reviewed (for example by `/end-day`).

## Step 1 — Find the target nodes

Place content using `references/node-taxonomy.md`. Take the first match, preferring the more specific:

1. A person with an ongoing relationship → `person/<slug>`
2. A paying engagement → `client/<slug>`
3. A prospect not yet under contract → `bizdev/<slug>`
4. An initiative spanning several entities → `workstream/<slug>`
5. A company as an entity → `company/<slug>`
6. A subject area → `topic/<slug>`
7. Infrastructure or setup → `infra/<slug>`
8. A persistent area of the user's own work → root `<name>.md`

Nothing fits → `topic/<slug>`. Never create an ad-hoc top-level directory. Look for an existing node before creating one; a new node is proposed to the user in full mode and created in silent mode. Slugs are kebab-case: `firstname-lastname` for people, with a company hint on a collision. A session that spans nodes commits to each.

**Step 1b.** If the session involved code, capture the branch, recent commits and uncommitted changes for the changelog line (**Git context**).

## Step 2 — Extract

Pull what is actually there, using the lists in **Extraction lists**:

- **Project state**: decisions made, open threads (`[FRESH]`, `[ONGOING]`, `[STALE]`), blockers, artifacts, next actions (`[P0]`, `[P1]`, `[P2]`, `[WAITING:who]`).
- **Knowledge**: insights, lessons, models, gotchas, recipes, corrected beliefs, decisions, background.
- **Cross-cutting**: signals for other nodes, people, questions for next time.
- **User observations**: preferences, corrections, domain context. Always extracted, including in silent mode.

Write knowledge entries only for what is reusable: "Would future-me benefit from this surfacing automatically?"

## Step 3 — Write

In this order:

1. **User observations** to `<config-root>/memory/me/user.md` (template and sections: **User node**). A repeat of something already there is skipped. A contradiction writes a CORRECTION and demotes the old line. One offhand remark is a signal, not a fact; a direct correction always commits.
2. **Summary**: `replace-section "## Summary"` with 2 to 4 sentences, under 400 characters.
3. **Changelog**: `prepend-section "## Changelog"` with `[node-id] LOG YYYY-MM-DD — [3-6 word title]: [decisions] | [insights] | [artifacts] | [next actions]`, under 500 characters, empty categories left out.
4. **Knowledge entries**: `append-section` under the type heading, in the formats in **Knowledge entry formats**. Every new entry ends `[confirmed:<today>] [recalled:<today>] [by:<actor-id>]`, the actor ID coming from `<config-root>/memory/me/identity.md`.
   - **Drift check first** for Insight, Lesson, Model and Gotcha entries (**Concept-drift check**). In full mode show the conflict and ask: (s)upersede, (k)eep both, (e)dit, or skip. **In silent mode never supersede**: write the new entry beside the old one and add a concept-drift note to the changelog line so the user can settle it at the next `/recall` or `/rehearse`.
5. **Decisions**: gather what was decided, why, the inputs with their sources, the date, the affected nodes, what would reopen it, and whether it replaces an earlier decision. Then:
   ```
   python3 scripts/cortex_cli.py record-decision --memory-root <config-root>/memory \
     --title "<one-line decision>" --what "<what was decided>" --why "<reasoning at the time>" \
     --decided-by <actor-id> --date <YYYY-MM-DD> \
     --input "<fact, and where it came from>" --affects <node-id> \
     [--supersedes decision/<id>] [--revisit-when "<trigger>"] --recorded-by /remember
   ```
   - It returns the record's id and a `pointer_line`. Add that line, unchanged, to the `## Knowledge` section of each affected node with `append-section`. The reasoning stays in the record.
   - `--decided-by` is the user's Actor ID. If someone else made the call, say so in `--what` or `--input`. Never write a decision with no decider.
   - A changed decision supersedes: pass `--supersedes` and the CLI keeps the old record and marks it superseded. An older inline `DECISION` entry with no record stays in place with `↳ superseded by: [[decision/<new id>]]` beneath it.
   - If what was decided or why is unclear, ask one short question. Never invent inputs or reasoning. Schema: `references/decision-schema.md`.
6. **People**: one PEOPLE line per person on the project node. Create or update a person page only on a graduation trigger (explicit `[ENTITY:person]` tag, 3 or more recalls, a research dossier this session, or named primary contact of a new engagement); a casual mention never does. On an existing page, add to Recent interactions and update last contact; never overwrite Notes, Identity or Linked entities without asking. Procedure: **People and person pages**.
7. **Signals**: `[other-node] SIGNAL from [source-node] (date): [implication]` on the other node.
8. **Dashboard**, always: the node's summary under Active Nodes, P0 Actions, Waiting On, Recent Knowledge (last 7 days), and the timestamp. Every line written carries `<!-- by:/remember @ <date> -->`, and every node reference is a wikilink (**Dashboard format**).

**Step 3.4, new nodes only.** If a node created in this run has fewer than 2 outbound wikilinks but names entities, offer once to convert them (**Orphan warning for new nodes**). Skip with `--no-orphan-check` or when the content names no one.

**Step 3.5.** Add `<YYYY-MM-DD HH:MM> touched: <node-id>[, ...]` to `<config-root>/memory/staged/queues/reindex`. Do not regenerate the index here; `/morning`, `/end-day`, `/cleanup` or `/reindex` does that.

## Step 4 — Continuity check

Compare with what the node already held:

- Threads still open and not addressed; threads now resolved; P2s that should move up.
- Prior questions that were answered.
- Knowledge the session reinforced: refresh its `confirmed` date.
- Knowledge the session contradicted: handle it through the drift check in Step 3, so it is demoted with the user's yes in full mode and flagged in silent mode. Never delete it.
- A thread open for 3 or more sessions without progress becomes `[STALE]`. A node revived after 14 or more days gets `[DORMANT → ACTIVE]` in its changelog line.

## Step 5 — Confirm

**Full mode.** Keep it skimmable in 20 seconds:

1. Nodes written to, with each living summary
2. Knowledge captured, by type, and decision records created
3. Observations written to the user node (counts)
4. Open threads with staleness, and blockers
5. Next actions: P0, P1, P2, WAITING
6. Cross-project signals
7. Prior entries reinforced, superseded or flagged
8. Questions carried forward

**Silent mode.** Say nothing. The exceptions:

- A new node was created: "Noted. Started tracking [node-id]."
- A correction that changes future behavior was captured: optionally "Got it. I'll [adjusted behavior] going forward."

## Memory hygiene

- Living summaries are replaced, never duplicated.
- Changelog lines are added newest first and never edited afterwards.
- Knowledge entries are updated when understanding evolves; the old version is demoted, not removed.
- When a node is over its size cap, consolidate old changelog lines first. Knowledge entries are kept longest.
