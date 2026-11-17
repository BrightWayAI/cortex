# /recall display formats

The layouts `/recall` uses. The command file holds the rules for what is loaded and shown; these are only how each view is laid out. Omit a section that has nothing in it.

## Project view

```
## [Project Node] — [today's date] [staleness badge]

**Current State**
[living summary]

**What We Know**
[Knowledge entries grouped by type. Show up to 5 most recent, note "N more" if needed.]

Models:
- [MODEL entry]

Gotchas:
- [GOTCHA entry]

Lessons:
- [LESSON entry]

Recipes:
- [RECIPE entry]

Corrections:
- [CORRECTION entry]

Insights:
- [INSIGHT entry]

**Blockers**
[active blockers, or "None"]

**Open Threads** ([count])
- [FRESH/ONGOING/STALE] [thread]

**Next Actions**
- [P0] [action] ← HIGHLIGHT
- [P1] [action]
- [P2] [action]
- [WAITING:who] [action]

**Unanswered Questions**
[from prior sessions, or "None"]

**Key People**
- [Name] ([role]) — [context]

**Recent Sessions**
- [date] [title]: [1-line summary]
- [date] [title]: [1-line summary]
- [date] [title]: [1-line summary]

**Signals from other projects**
[cross-project flags, or "None"]
```

## Dashboard (no project)

```
## Working World — [today's date]

### Active (within 7 days)

**[node-id]** [badge]
[summary — 1-2 sentences]
Knowledge: [count] entries
Open threads: [count]
Next up: [top action]

...

### Warm / Cooling / Dormant
[same format, less detail]

---

### Needs Attention
[STALE threads, overdue P0s, unresolved blockers]

### Recent Learning
[3-5 most recently committed INSIGHT/LESSON/GOTCHA entries across ALL nodes]

### Cross-Project Signals
[Recent SIGNALs]

### People Across Projects
[Anyone in 2+ nodes]
```

## Person page

```
## [Name] — person page

> Last updated: [date] · Temperature: [Cold|Warm|Active|Dormant]

**Identity** — [title], [company link]. [email]
**How we know each other** — [relationship line]

**Open threads**
- [WAITING:them] — [thread]
- [WAITING:you] — [thread]
- [P0] — [thread]

**Recent interactions (last 90 days)**
- [date] — [type] — [summary]
- ... (top 5)

**Linked projects** — [client/...], [bizdev/...]

**Notes**
[free-form]
```

## Cross-project profile (legacy `@name`)

```
## [Name] — Cross-Project Profile

**Projects:** [node-id]: [role]. [node-id]: [role].

**Recent mentions:** [date] in [node]: [context]

**Open items involving them:** [WAITING:them] [description]
```

## Topic

```
## What we know about: [topic]

**Mental Models**
[MODEL entries]

**Lessons & Insights**
[LESSON/INSIGHT entries]

**Gotchas**
[GOTCHA entries]

**Recipes**
[RECIPE entries]

**Corrections**
[CORRECTION entries]

**Appears in:** [nodes where this comes up]
```

## Auto-recall at conversation start

```
Welcome back. Here's what needs attention:

**Overdue**
- [P0 action] in [node] — was due [date]

**Stale**
- [thread] in [node] — no progress in [count] sessions

**Recent**
- Last worked on [node] ([date]): [1-line summary]

What are we working on?
```

## Person recall counter file

`<config-root>/memory/.person-recall-counter.json`:

```json
   {
     "sarah-chen": { "count": 4, "last_recalled_at": "2026-05-12T14:23:00Z" },
     "tom-reyes": { "count": 2, "last_recalled_at": "2026-05-10T09:11:00Z" }
   }
   ```

## Triage offer (explicit `/recall` only)

> "[N] entries flagged as aging:
>  [N_stale] stale · [N_dormant] dormant · [N_cold] cold
>
>  Triage now?
>  (r)e-confirm — mark them all as confirmed today
>  (s)elect — walk one by one, choose per entry
>  (d)emote all dormant + cold — move to Demoted knowledge sections
>  (k)skip — leave as-is; they'll resurface on next recall or rehearsal"
