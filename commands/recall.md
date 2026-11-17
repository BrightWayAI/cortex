---
description: Surface working memory into the current conversation. Runs automatically at conversation start to load the user profile and surface attention items. Also runs explicitly via /recall [project] to load context for a specific project, or /recall alone for the full dashboard. Default load for a project is frontmatter + Current state + Open loops only — pass `--full` to also load the node's Record (full knowledge base, changelog, people, history).
---

# /recall [project?]

Surface working memory to set up the current session. Layouts for every view are in `references/recall-formats.md`.

## Modes

- **Auto** (conversation start, no user trigger): load silently and say only what needs attention. If the first message names a project, load that context; if it is a greeting, show the brief attention summary; if it is a direct task, load what is relevant and weave it in.
- **Explicit** (the user types `/recall`): the full dashboard, or the project, person, or topic asked for, with complete detail.
- **Contextual** (a project, person, or topic comes up mid-conversation): no recall block. Weave in what is relevant.

## Step 0 — Load the hot cache and user profile (always, first)

Resolve `<config-root>` per `references/core-contract.md` §1. If `<config-root>/memory/` cannot be reached, say that memory cannot be loaded without it and stop; if a host needs folder access granted, request it for the resolved root, not for a hard-coded path. If the memory directory does not exist or is empty, say so and offer to help set it up.

1. Read `<config-root>/memory/hot.md` if it exists (skip it if missing or `hot_cache.enabled: false`). It is the rolling 7-day buffer: recent reflections, active people, open threads, commitments.
2. Read `<config-root>/memory/me/user.md` if it exists.

Apply both immediately and silently: communication preferences, working style, corrections, tool preferences, who is who, and recent activity (do not ask "what have you been working on" when the cache says). **Do not announce this.**

**Pending overnight draft.** If `<config-root>/memory/staged/commit-drafts/` holds a file dated yesterday or today that is not in `staged/commit-drafts/archive/`, end the auto-recall with one line: "Heads up: overnight `/listen` proposals are pending. Run `/morning` when you're ready." Do not list the proposals.

## What to read for each form

Node IDs map to files: `client:acme-corp` → `memory/client/acme-corp.md`; no prefix (`hiring`) → `memory/hiring.md`.

- `/recall` → `memory/DASHBOARD.md`; show the dashboard.
- `/recall <node>` → that node's file; show the project view within the load boundary below.
- `/recall person:<slug>` → `memory/person/<slug>.md`; if there is none, fall through to `@name`.
- `/recall @name` → find the nodes in DASHBOARD.md, then search their PEOPLE entries.
- `/recall <topic>` → use DASHBOARD.md to pick the likely nodes, then search their knowledge entries and LOGs.

## A project (`/recall client:acme`)

**Default load boundary.** Load only frontmatter, `## Current state` (or legacy `## Summary`), and `## Open loops` (or legacy `## Next Actions` P0/P1 plus `## Open Threads`). Stop at a `---` divider followed by `## Record` — do not read past it. If the Record lives in a sibling `<node>.record.md` file, do not open that file at all in default mode.

**`--full`** also loads the Record (or the sibling file): every knowledge entry (INSIGHT, LESSON, MODEL, GOTCHA, RECIPE, CORRECTION, DECISION pointers), PEOPLE, Changelog, all Open Threads and Next Actions, and SIGNALs.

**Nodes not yet restructured** (no `## Current state`, no Record divider) behave exactly as before: full-file load, no behavior change.

Then:

1. Compute staleness from the last update: **Active** within 7 days, **Warm** 8–14, **Cooling** 15–30, **Dormant** 30+.
2. Present the **Project view**. Knowledge entries are grouped by type, up to 5 most recent per group with "N more"; P0 actions are highlighted; threads are marked FRESH, ONGOING, or STALE, and STALE ones get a warning.
3. In default mode on a restructured node, the knowledge, people, sessions, and signals sections are thin or empty because that content is in the unloaded Record. Show Current State and the open loops as the substance, note once "Full history in Record — run `/recall <node> --full` for it.", and omit empty sections; do not render them with apologetic placeholder text.
4. End with **"What are we working on today?"**

## No project (`/recall`)

Show the **Dashboard**: nodes sorted by recency (Active in detail; Warm, Cooling, and Dormant in less), then Needs Attention (STALE threads, overdue P0s, unresolved blockers), Recent Learning (the 3–5 most recent INSIGHT, LESSON, or GOTCHA entries across all nodes), Cross-Project Signals, and People Across Projects (anyone in 2+ nodes). End with **"Which project are we picking up today?"**

## A person (`/recall person:<slug>` or `/recall @name`)

- **Page exists** → show the **Person page** view: identity, how you know each other, open threads, the top 5 interactions from the last 90 days, linked projects, notes.
- **No page** → show the **Cross-project profile** (projects and roles, recent mentions, open items involving them), then: "No person page for <slug> yet. After 3 recalls I'll offer to graduate them."

**Recall counter.** Every recall that names a person, in either form, increments their entry in `<config-root>/memory/.person-recall-counter.json` (create the file if missing; a new slug starts at `{count: 1, last_recalled_at: now}`). The file is private to cortex.

- Count reaches 3 **and no page exists** → after the profile, ask: "I've recalled <name> 3 times now. Want to graduate them to a person page? I'll synthesize a starting page from existing mentions across nodes." On yes: scan the node files for PEOPLE entries matching the name, write `memory/person/<slug>.md` following the person-page schema, add an "Active people" entry to DASHBOARD.md, and reset the count to 0. Never create the page without that yes.
- A page already exists → still increment (it tells `/cleanup` which pages are cold), but do not prompt.

## A topic (`/recall pricing`)

Search knowledge entries and LOGs for the topic and show the **Topic** view (models, lessons and insights, gotchas, recipes, corrections, and the nodes it appears in). End with **"Want to dive deeper or add to what we know?"**

**Duplicate-topic check, before the answer.** Send the query and DASHBOARD.md's Active Nodes summaries (node ID plus one line each) to the low-cost classifier: "Given the query `<query>` and these node summaries: `<list>`, return the single closest semantic match if any node summary is plausibly about the same topic. Otherwise return `null`. Output exactly `{"match": "<node-id>"}` or `{"match": null}` — no other text." If it names a node this recall is not already showing, put one line first: "Note: `<matched-node>` may already cover this. Want to read that first?" Then give the topic answer.

## Auto-recall at conversation start

Read DASHBOARD.md and present the **Auto-recall** summary:

- **Maximum 8 lines.** This is a glance, not a report.
- Only overdue P0s (not P1 or P2), threads stale for 3+ sessions, and the 1–2 most recent sessions.
- Nothing needs attention → "All clear — what are we working on?"
- Weave in anything from the user profile that matters today, such as a known meeting cadence.
- Never show the full dashboard in auto mode, and never offer the aging-entries triage.

## Contextual recall

Read the relevant node, pick the 1–3 entries that bear on what is being discussed, and weave them into the response naturally — don't format as a recall block. Example: the user says "I need to follow up with Acme"; memory says their procurement needs three quotes; say "Heads up — Acme's procurement requires 3 vendor quotes even for renewals, so factor in 2 weeks lead time." Having memory does not mean dumping it.

## `[recalled:...]` tags

Whenever a knowledge entry is shown to the user, set its `[recalled:YYYY-MM-DD]` tag to today.

- Only the `[recalled:...]` tag changes. `[confirmed:...]` needs an explicit re-confirmation.
- Update only entries the user actually saw, not every entry read for context.
- An entry with no tags gets both: `[confirmed:<original-date>] [recalled:<today>]`.
- These are in-place edits to the node file, idempotent. Don't announce tag updates to the user.

## Aging entries

Classify each rendered knowledge entry by the age of its `[confirmed:...]` date, using the thresholds, type modifiers, and node `decay_profile` defined in `references/decay-model.md` (`effective_threshold = base_threshold × type_modifier × decay_profile_multiplier`; a modifier of 0, as for CORRECTION, means never flagged). Thresholds come from `<config-root>/memory/.decay-config.md`; if it is missing, create it with the documented defaults. Don't prompt the user about that.

| Age | State | Flag appended to the rendered line |
|---|---|---|
| below `threshold_fresh` | Fresh | none |
| up to `threshold_dormant` | Stale | ` [stale-confidence]` |
| up to `threshold_cold` | Dormant | ` [dormant — last confirmed <N> days ago]` |
| beyond | Cold | ` [cold — last confirmed <N> days ago; consider rehearse or archive]` |

The flag is display-only; it does NOT get written into the entry text. Entries under `## Demoted knowledge` are shown after the active sections, headed "Below: entries previously demoted. Kept for reference; not surfaced as active knowledge.", and are left out of counts and highlights.

**Triage offer.** Only when the user ran `/recall` explicitly and some entries are flagged, show the **Triage offer** block. Do NOT offer this in auto-recall mode or for contextual recall.

- **(r)e-confirm** → set `[confirmed:<today>]` on every flagged entry; confirm in one line.
- **(s)elect** → one entry at a time: `(c)onfirm / (d)emote / (a)rchive entry / (s)kip / (e)dit then confirm`. Demote moves the entry, with its tags, to the node's `## Demoted knowledge` section (create it if missing) and appends `↳ demoted <today> by user-recall-action`. There is no entry-level archive: treat it as demote plus a note that the user asked for removal, and point to `/forget` for archiving a whole node.
- **(d)emote all dormant + cold** → move every Dormant and Cold entry to its node's `## Demoted knowledge`; Stale entries stay.
- **(k) skip** → no changes.

## Behavior notes

- No entries → say so and ask whether to start building context. Sparse memory → show what exists.
- Surface committed data accurately; don't editorialize. Use human-readable dates ("March 4").
- The only files this command writes are the node files it updates tags or demotions in, the recall counter, and a missing `.decay-config.md`.
