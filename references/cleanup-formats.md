# /cleanup display formats

The layouts and prompts `/cleanup` shows. The command file holds the rules for what is checked and what may be done; these are only how each finding is presented.

## Memory Health Report (Step 1)

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

## A. Consolidation candidates

```
Consolidation candidates:
- [node-id]: [count] log entries. Oldest: [date]. Suggest archiving entries before [date].
```

## B. Stale threads

```
Stale threads:
- [node-id]: "[thread description]" — open since [date], last mentioned [date]
- ...
```

## C. Dormant nodes

```
Dormant nodes (consider archiving):
- [node-id]: Last active [date]. Summary: [1-line]
- ...
```

## D. Orphaned people

```
Orphaned people entries:
- [Name] references [node-id] which is [archived/missing]
```

## E. Expired signals

```
Expired signals:
- [signal description] — from [date], between [node] and [node]
```

## F. Duplicates

```
Duplicates found:
- [node-id]: [count] SUMMARY entries (should be 1)
- [Name]: appears [count] times in people index
```

## G. Isolated notes

```
Isolated notes (no inbound or outbound links, untouched 30+ days):
- [node-id]: [last updated date], [entry count] entries — suggest: [archive | merge into <candidate> | keep]
```

## H. Person-page maintenance

```
Person-page maintenance:
- person:[slug]: [state] (last contact <N>d ago, <M> recalls in 180d) — suggest: [archive | trim | keep with note]
```

## I. Dormant and cold knowledge

```
Dormant knowledge:
- [node-id] INSIGHT (2025-09-12, confirmed:2025-09-12): "<first 80 chars>..." [<N>d dormant] — suggest: rehearse | demote | archive
- ...

Cold knowledge:
- [node-id] MODEL (2024-11-03, confirmed:2024-11-03): "<first 80 chars>..." [<N>d cold] — suggest: demote | archive
- ...
```

## J. Decision revisit

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

## K. Structurally isolated node

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

## L.0. Baseline prompt

> "DASHBOARD has <N> lines without provenance comments (predates the v4.12.0 provenance addition). Section L would flag all of them as 'missing provenance' candidates and surface 15 per run — multi-run migration grind for existing users.
>
> Three options:
>   (b)aseline-stamp ALL existing lines as `<!-- by:manual @ <today> -->` to defer them for 60 days. Section L will then surface only lines that actually need attention going forward. Recommended.
>   (w)alk individually as Section L normally does — 15 lines per /cleanup run, ~<N/15> runs to clear backlog.
>   (s)kip Section L entirely for this run; baseline decision deferred.
>
> Choose: b / w / s"

## L. Stale dashboard lines

```
DASHBOARD has <N> potentially stale lines:

  STALE (owning command hasn't refreshed in N+ days):
  - "studio.co intro angle..." <!-- by:/listen @ 2026-05-12 --> · 16 days old
  - "Draft Sylvia outreach" <!-- by:/remember @ 2026-04-22 --> · 36 days old

  MISSING PROVENANCE (pre-v4.12 or unattributed):
  - "WAITING:Priya — Logo permission" (no by-tag)

  ORPHANED REFERENCES:
  - "[[bizdev/foo-corp]]: ..." — node no longer exists

For each line:
  (k)eep — update provenance to `manual @ <today>` to suppress staleness for 60 days
  (u)pdate-now — invoke owning command (or /remember if manual) to refresh
  (d)elete — remove the line entirely
  (s)kip — re-check next /cleanup
```

## Recommended Actions (Step 3, suggest mode)

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

## Cleanup Complete (Step 5)

```
## Cleanup Complete

- Entries before: [count] → After: [count] (freed [count])
- Actions taken: [count]
- Memory health: [assessment]

Next recommended cleanup: [suggest a date based on activity level]
```

