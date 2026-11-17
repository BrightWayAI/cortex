# /remember formats and procedures

Detail for `commands/remember.md`. The command file is the order of operations and the
rules; this file holds the prompts, extraction lists, file formats and procedures it
points to. Where the two differ, the command file wins.

## Usage examples

Quick mode:

```
/remember --quick client:acme Kim confirmed the March 15 deadline
/remember --quick bizdev Had intro call with Stripe partnership team — they're interested
/remember --quick hiring Sent offer letter to Jordan for the ops manager role
/remember --quick strategy:pricing Competitor just dropped their entry tier to $29/mo
```

Knowledge mode:

```
/remember --knowledge gotcha client:acme Their procurement team requires 3 vendor quotes even for renewals — build in 2 weeks lead time
/remember --knowledge model bizdev:partnerships Channel partners want co-marketing commitments before signing — lead with the joint campaign plan, not the rev share
/remember --knowledge lesson strategy:pricing Tried usage-based pricing with mid-market — too unpredictable for their budgets. Flat tiers with overage charges landed better.
/remember --knowledge recipe domain:healthcare-compliance For HIPAA BAAs: use our template, get their legal to redline first, then negotiate — saves 2 rounds of back-and-forth
/remember --knowledge insight learning:sales-ops The bottleneck isn't lead gen — it's the handoff from SDR to AE. Leads go cold in the 48-hour gap.
/remember --knowledge that the API rate limit resets hourly not daily
```

Type inference for knowledge mode:

| If the content sounds like... | Assign type |
|-------------------------------|-------------|
| "X works by..." / "Their process is..." / "The way X actually works is..." | MODEL |
| "Watch out for..." / "Don't assume X" / "They require Y even though..." | GOTCHA |
| "Tried X, it [worked/failed] because..." / "What worked was..." | LESSON |
| "I was wrong about X — actually it's Y" / "Turns out..." | CORRECTION |
| "For [situation], do [steps]" / "The playbook for X is..." | RECIPE |
| A forward-looking commitment with a clear trigger to revisit | DECISION |
| General realization or connection that doesn't fit the above | INSIGHT |

## Triage (Step 0)

#### A — Classifier prompt

Send the last ~30 conversation turns (or the whole conversation if shorter) to the low-cost/fast-tier model with this prompt:

> System: You are a memory-commit triage classifier for a personal working-memory system. Decide:
>
> 1. **Is this conversation commit-worthy?** Were decisions made, knowledge shared, corrections given, or entities mentioned in a way that should update existing memory nodes? Greetings, scheduling pings, and trivial Q&A without takeaways are NOT commit-worthy.
> 2. **If yes, which nodes are affected?** Return only nodes that need updating. Don't over-attribute. Use the user's existing node namespace (you'll be told what nodes exist).
>
> Existing node namespace (truncated to active set from DASHBOARD.md): <list of active node ids>
>
> Output exactly one JSON object on a single line, no other text:
>
> `{"commit": true, "nodes": ["client:acme-corp", "person:sarah-chen"], "reason": "<one line>"}`
>
> or
>
> `{"commit": false, "reason": "<one line>"}`
>
> Rules:
> - Always include any user-observation work (corrections, preferences) as commit-worthy AT MINIMUM to the `user` node, even if no project nodes apply. So if the user corrected your approach, `commit: true, nodes: ["user"]`.
> - Person-page graduation triggers (explicit `[ENTITY:person]` tag, contact-researcher dossier produced this session, etc.) → include `person:<slug>` in nodes.
> - When in doubt, lean conservative: `commit: false` is preferred over a noisy commit. The user reviews `triage-log.md` weekly to catch false-negatives.

#### C — Triage log format

Append to `<config-root>/memory/triage-log.md` (create file if missing). Format:

```markdown
# Triage Log

_Auto-appended by cortex's two-stage commit triage. Audit weekly for false-negatives (commit:false when a real decision was made) and over-attribution (commit:true with too many nodes)._

### YYYY-MM-DD HH:MM
- Decision: [commit | skip]
- Nodes: [list, or omit if skip]
- Reason: <one-line from classifier>
- Conversation context: <one-line synthesized from your own read of the turns — what the conversation was about>
```

#### D — Cost discipline

The low-cost/fast-tier call is the only model call until classification completes. If `commit: false`, Steps 1-5 (full-tier synthesis) never run. Expected cost per `/remember` invocation:
- Trivial conversations: ~$0.001 (low-cost/fast-tier classifier only)
- Substantive conversations: previous cost + ~$0.001 (negligible overhead)

Total full-tier cost drops 30-50% measured weekly when ~30-40% of conversations are trivial.

## Git context (Step 1b)

If the conversation involves code or a git repository, capture the development context:

1. **Current branch**: Record the branch name being worked on
2. **Recent commits**: Note the last 3-5 commit messages from this session (if any)
3. **Uncommitted changes**: Summarize what's staged or modified (high-level, not full diffs)
4. **Related branches**: Note any branches mentioned (feature branches, PRs, upstream)

Include this as a `GIT CONTEXT` block in the changelog entry:
```
[node-id] LOG YYYY-MM-DD — title: ... | Git: branch [branch-name], [count] commits ([summary])
```

Skip this step entirely if the session doesn't involve code or version control.

## Extraction lists (Step 2)

#### A. Project State (what changed)

```
DECISIONS MADE:
- What was definitively resolved, chosen, or agreed upon
- Include reasoning if non-obvious

OPEN THREADS:
- Things started but not finished
- Questions raised but unanswered
- Ideas flagged for later
- Mark each: [FRESH], [ONGOING], or [STALE]

BLOCKERS:
- Anything actively preventing progress
- Dependencies on people, systems, or information
- Include who/what is blocking and since when

ARTIFACTS:
- Documents created, decks built, spreadsheets drafted (include filenames/paths)
- External resources, URLs, or references worth keeping
- Emails sent, proposals delivered, contracts shared, campaigns launched

NEXT ACTIONS:
- Explicitly stated or implied next steps
- Tag each with priority:
  - [P0] — Do immediately
  - [P1] — Do soon / this week
  - [P2] — Do eventually
  - [WAITING:person/thing] — Blocked on someone/something specific
```

#### B. Knowledge (what was learned)

> **Canonical knowledge taxonomy.** There are seven knowledge types: **Insight · Lesson · Model · Gotcha · Recipe · Correction · Decision** (see `CLAUDE.md` and `references/core-contract.md` for definitions and decay rules — GOTCHA and RECIPE decay 1.5× slower, CORRECTION never decays).
> The extraction buckets below map directly to these types; use the bucket name as the type when you write the entry in Step 3.

```
INSIGHTS:
- New understanding gained during this session
- "Aha" moments, reframes, or realizations
- Connections spotted between previously unrelated things
- Example: "Realized our churn isn't a product problem — it's an onboarding problem. Customers who complete setup in week 1 retain at 92%."

LESSONS LEARNED:
- Things tried that worked → why they worked
- Things tried that failed → why they failed, what to do instead
- Mistakes made → what the correct approach is
- Example: "Tried sending proposals same-day — close rate dropped. Waiting 48 hours with a tailored deck closes 3x better."

MENTAL MODELS:
- How something works, explained for future reference
- Business processes, decision frameworks, domain rules, workflows
- "The way X actually works is..."
- Example: "Their approval process: department head → finance review → VP sign-off → procurement. Skip finance and it stalls for weeks."

GOTCHAS & PITFALLS:
- Specific traps or non-obvious behaviors in processes, tools, or relationships
- Things that look like they should work but don't
- Surprising rules, undocumented requirements, edge cases
- Example: "Their fiscal year starts in April, not January — all budget conversations need to reference Q1 as April-June."

PATTERNS & RECIPES:
- Techniques or approaches that proved effective
- Reusable solutions to specific types of problems
- Workflows or processes worth repeating
- Example: "For getting executive buy-in: lead with the metric they own, show the gap, propose one action, name the timeline."

CORRECTED BELIEFS:
- Assumptions that turned out to be wrong
- Previous understanding that was updated or reversed
- Example: "Previously assumed they were price-sensitive — actually they have budget, they just need ROI framing to get internal approval."

DECISIONS:
- A choice made: a forward-looking commitment, not a retrospective lesson
- Cues: "we decided," "I'm going with," "settled on," "going forward we'll," "the call is," "made the call to"
- Written as a decision record, never inline (command file, Step 3)

CONTEXT & BACKGROUND:
- Domain knowledge needed to understand this project or topic
- Terminology, acronyms, or jargon defined
- Historical context: why things are the way they are
- Constraints or requirements that shape decisions
```

#### C. Cross-cutting

```
CROSS-PROJECT SIGNALS:
- Anything with implications for a different node
- Knowledge that applies across projects
- "The caching pattern here would solve the performance issue in [other-node]"

PEOPLE:
- Anyone who came up: name, role, context
- What they know or own relative to this project
- Tag with other nodes they appear in
- If the user explicitly tagged someone with [ENTITY:person] in the conversation, that's an
  explicit graduation trigger (#5 from the schema in CLAUDE.md) — record the slug.

QUESTIONS FOR NEXT TIME:
- Things to investigate, test, or verify
- Research to do before the next session
- Hypotheses to confirm or reject
```

#### D. User Observations (from passive learning engine)

```
PREFERENCES:
- Communication style signals (terse vs. detailed, options vs. decisions)
- Tool/platform preferences expressed or demonstrated
- Working style patterns (batching, time-of-day, delegation)
- Vocabulary and framing they use and expect

CORRECTIONS:
- Anything the user corrected about your approach
- Implicit corrections (they ignored your suggestion and did it differently)
- Format: [what was wrong] → [what they wanted] → [why, if given]

DOMAIN CONTEXT:
- Facts about their company, team, industry shared in passing
- How their processes/systems work
- Constraints they operate under
```

## Dashboard format

**Line provenance (v4.12.0+):** every line written or modified in DASHBOARD must carry an HTML comment immediately after with `<!-- by:<command> @ <YYYY-MM-DD> -->`. This makes drift detection trivial for `/cleanup` (which surfaces stale lines whose owning command hasn't refreshed them in N days).
   - Example: `- [P0] [[bizdev:harbor-education-group]]: studio.co intro angle — see if it fits <!-- by:/listen @ 2026-05-28 -->`
   - Format: `<!-- by:<command-with-slash> @ <ISO-date> -->`
   - The comment is HTML-comment syntax so it renders invisibly in Markdown previews and Obsidian — humans see clean lines.
   - When a line is refreshed by the same command on a later run, update the date. When a different command refreshes it, replace the by-value too.
   - For lines that came from manual edits (no command), use `<!-- by:manual @ <date> -->` if you know the date; otherwise omit (the absence of provenance is itself a signal `/cleanup` Section K will surface).

DASHBOARD must use `[[wikilinks]]` for every node reference so the Obsidian graph view treats it as the central hub — every active node connects to DASHBOARD via a real edge.

If `DASHBOARD.md` doesn't exist, create it with this template:

```markdown
# Working World Dashboard
> Last updated: YYYY-MM-DD

## Active Nodes
| Node | Summary | Last Updated |
|------|---------|-------------|
| [[node-id]] | [1-line living summary] | YYYY-MM-DD |

## Active People (v4.2+)
Top 10 graduated person pages sorted by Last updated desc.

| Person | Temperature | Last contact | Open threads |
|--------|-------------|--------------|--------------|
| [[person/sarah-chen]] | Active | 2026-05-10 | 2 |

## P0 Actions
- [P0] [[node-id]]: [action]

## Waiting On
- [WAITING:who] [[node-id]]: [what]

## Recent Knowledge (last 7 days)
- [[node-id]] [TYPE] (date): [entry]

## Stale Threads
- [[node-id]]: [thread] — open since [date]

## Dormant Nodes
- [[node-id]]: Last active [date]

## Isolated Notes (v4.2+)
Surfaced by `/cleanup`'s orphan-detection guardrail. Nodes with no incoming/outgoing links and last updated >30 days ago.
- [[node-id]]: Last updated [date] — suggest [archive / merge / keep]
```

**v4.10.1 wikilink rule for DASHBOARD writes:** Every `[node-id]` in the template above gets emitted as `[[node-id]]` in the actual file. This converts every node reference into a real graph edge from DASHBOARD outward. Combined with the canonical wikilink rule in CLAUDE.md, DASHBOARD becomes the central hub instead of an isolated island.

**Upgrade path for existing DASHBOARD files:** Pre-v4.10.1 DASHBOARDs typically use `### node-id` section-header style for active nodes (not wikilinks). Running `/relink-memory --rerun` in cortex v4.10.1+ detects this and regenerates DASHBOARD using the wikilink-emitting template. See `commands/relink-memory.md` Step 2.5.

## Node file format

```markdown
# {node-id}
> Last updated: YYYY-MM-DD

## Summary
[Living summary — replaced each session]

## Knowledge

### Insights
[node] INSIGHT (date): [entry]

### Lessons
[node] LESSON (date): [entry]

### Models
[node] MODEL (date): [entry]

### Recipes
[node] RECIPE (date): [entry]

### Decisions
[[decision/<id>]] pointer line (date)

### Gotchas
[node] GOTCHA (date): [entry]

### Corrections
[node] CORRECTION (date): [entry]

(Canonical taxonomy: Insight / Lesson / Model / Gotcha / Recipe / Correction /
Decision — see `CLAUDE.md` Knowledge Taxonomy. Entries written under the earlier
v4.13 four-type consolidation attempt (`INSIGHT [mental-model]` / `INSIGHT [recipe]`)
are still read; new writes use the sections above.)

## People
[node] PEOPLE: [[person/<slug>]] (role) — context. Also in: [[<other-node>]], [[<other-node>]]

(v4.10+ wikilink rule: ALWAYS emit `[[person/<slug>]]` if a person page exists; if not, emit the bare name + flag for graduation tracking via `memory/.person-mention-counts.json`. Same applies to client / company / topic / workstream references in this entry.)

## Changelog
[node] LOG YYYY-MM-DD — title: content
(newest first; past entries are never modified)

## Open Threads
- [FRESH/ONGOING/STALE] [description]

## Next Actions
- [P0] [action]
- [P1] [action]
- [WAITING:who] [action]

## Signals
[node] SIGNAL from [other-node] (date): [implication]
```

## User node

1. File path: `<config-root>/memory/me/user.md`
2. If it doesn't exist, create it with this template:

```markdown
# user
> Last updated: YYYY-MM-DD

## Communication Preferences

## Working Style

## Corrections

## Domain Expertise

## Relationships & Org Context

## Tool & Platform Preferences
```

3. Append new observations to the appropriate section:
   - Preferences → Communication Preferences or Working Style or Tool & Platform Preferences
   - Corrections → Corrections (always — these are highest priority)
   - Domain context → Domain Expertise
   - Relationship info → Relationships & Org Context

**Confidence gating**: Only commit observations with reasonable confidence. A single offhand remark is a signal, not a fact. But direct corrections — always commit.

## Summary and changelog formats

#### A. Living Summary (replace if exists, create if new)

Format:
```
[node-id] SUMMARY (updated YYYY-MM-DD): [2-4 sentences — what this is, where it stands, what's known. Include top blocker/P0 if any. Include most important recent insight if learning-heavy.]
```

Keep under 400 characters.

#### B. Changelog Entry (always added, newest first)

Format:
```
[node-id] LOG YYYY-MM-DD — [3-6 word title]: [decisions] | [insights/lessons] | [artifacts] | [next actions]
```

Keep under 500 characters. Skip empty categories.

## Knowledge entry formats

##### C.0 Entry metadata convention (v4.3+)

Every knowledge entry carries three timestamps plus stable actor provenance. The first is the original date the entry was committed. The second is the date the entry was last meaningfully touched (re-affirmed, edited, or referenced as evidence in a downstream commit). The third is the date the entry was last surfaced via `/recall` or returned by `memory-librarian`.

Encoded inline using key:value tags at the end of the entry line:

```
[node-id] <TYPE> (YYYY-MM-DD): <entry body>  [confirmed:YYYY-MM-DD] [recalled:YYYY-MM-DD] [by:<actor-id>]
```

- The leading `(YYYY-MM-DD)` is the **original commit date** — set once at creation, never changed.
- `[confirmed:YYYY-MM-DD]` is the **last-confirmed-at** timestamp — updated whenever:
  - The user accepts a mining-layer proposal that references this entry (Pre-chain B + Step 2b)
  - A new commit explicitly reinforces this entry (e.g., new evidence for an existing INSIGHT)
  - The user re-confirms via a future v4.4 rehearsal prompt
- `[recalled:YYYY-MM-DD]` is the **last-surfaced-at** timestamp — updated whenever `memory-librarian` returns this entry in a Source Entries list or `/recall` renders it in a project view.
- `[by:<actor-id>]` is immutable authorship from
  `<config-root>/memory/me/identity.md`. It identifies the person whose approved
  workflow committed the entry, not the host or model that drafted it.

Both tags default to the original commit date if no later event has touched them.

These tags are the substrate for v4.4's forgetting/decay layer. **In v4.3 we write and maintain them but do not yet decay or demote based on them.** v4.4 reads these timestamps and decides which entries to demote, surface for rehearsal, or auto-archive.

Existing entries without `by:` remain valid as `legacy-unknown`; do not rewrite history merely to add authorship.

##### C.1 Entry formats (seven canonical types — see `CLAUDE.md` Knowledge Taxonomy)

```
[node-id] INSIGHT (YYYY-MM-DD): [the insight, compressed but precise]  [confirmed:YYYY-MM-DD] [recalled:YYYY-MM-DD] [by:<actor-id>]
```
```
[node-id] LESSON (YYYY-MM-DD): [what was tried] → [what happened] → [takeaway]  [confirmed:YYYY-MM-DD] [recalled:YYYY-MM-DD] [by:<actor-id>]
```
```
[node-id] MODEL (YYYY-MM-DD): [how something works, 1-3 sentences]  [confirmed:YYYY-MM-DD] [recalled:YYYY-MM-DD] [by:<actor-id>]
```
```
[node-id] RECIPE (YYYY-MM-DD): [technique name] — [when to use] → [how to do it]  [confirmed:YYYY-MM-DD] [recalled:YYYY-MM-DD] [by:<actor-id>]
```
```
[[decision/<id>]] pointer line returned by `cortex_cli.py record-decision` (decisions are records; see `references/decision-schema.md`)
```
```
[node-id] GOTCHA (YYYY-MM-DD): [the trap and how to avoid it — an actionable warning]  [confirmed:YYYY-MM-DD] [recalled:YYYY-MM-DD] [by:<actor-id>]
```
```
[node-id] CORRECTION (YYYY-MM-DD): [old belief] → [corrected understanding]  [confirmed:YYYY-MM-DD] [recalled:YYYY-MM-DD] [by:<actor-id>]
```

- On new commit, both `confirmed` and `recalled` are set to the commit date.
- GOTCHA and RECIPE decay 1.5× slower than the default; CORRECTION never decays (see `references/decay-model.md`).

**Backward compatibility:** entries written under the earlier v4.13 four-type consolidation attempt (`INSIGHT [mental-model]`, `INSIGHT [recipe]`) remain valid and are still read by `/recall` and `memory-librarian` — no migration is forced or performed by this refactor.

**Quality bar**: Only write knowledge entries for things that are genuinely reusable. The test: "Would future-me benefit from this surfacing automatically?"

## Concept-drift check

Process:

1. Read all entries of the same type from the target node's active sections (skip `## Demoted knowledge` and `## Archive`). If the node is brand new with no prior entries of this type, skip the drift check.
2. If there are more than 20 existing entries of the same type, scope to the most-recently-confirmed 20 (read each entry's `[confirmed:...]` tag; sort desc, take top 20). The drift check is most useful against recent beliefs; old beliefs that contradict are less likely to still be active.
3. Send to a low-cost/fast-tier model (Claude adapter: Haiku-tier):

   > "You are a concept-drift detector for working memory. New entry:
   > `<new entry text>`
   >
   > Existing entries of the same type on this node (most recent 20):
   > [1] `<entry text>`
   > [2] `<entry text>`
   > ...
   >
   > Does the new entry contradict, supersede, or meaningfully refine any of the existing entries? Output exactly:
   > `{supersedes: [<index>], relationship: 'contradicts' | 'supersedes' | 'refines', reason: '<one line>'}`
   > or
   > `{supersedes: null}`
   >
   > Rules:
   > - 'contradicts' = new entry asserts the opposite of the existing one
   > - 'supersedes' = new entry replaces the existing one with an updated version
   > - 'refines' = new entry sharpens or qualifies an existing one without replacing it
   > - Be conservative — only flag when the relationship is clear. Most new entries are additive, not superseding."

4. Parse the response. If `supersedes` is non-null:

   In FULL mode (user-triggered `/remember`):
   - Surface inline before writing:
     > "New entry: '<text>'
     >  Concept-drift detector flagged this against existing entry [<index>]: '<existing text>'
     >  Relationship: <contradicts | supersedes | refines>. Reason: <one line>.
     >
     >  How to handle?
     >  (s)upersede — move existing to ## Demoted knowledge; write new in its place
     >  (k)eep both — write new alongside; existing stays active
     >  (e)dit relationship — describe the relationship inline (e.g., "this is a refinement that should be cross-referenced, not a supersede")
     >  (skip) skip new entry — don't commit it"

   In SILENT mode (auto-commit at conversation end):
   - **Never auto-supersede in silent mode.** Silently demoting a held belief is too destructive for an unattended path. Instead: write the new entry alongside the old, append a `## Concept-drift flags` note to the changelog entry ("New entry on [node] may supersede [existing entry] — review via /rehearse"), and let the user resolve at the next `/recall` or `/rehearse`.

5. On user-chosen `supersede` action:
   - Move the existing entry to the node's `## Demoted knowledge` section (create if missing)
   - Append metadata under the demoted entry: `↳ demoted <today> by supersede` and `↳ superseded by: <new entry's first 60 chars>`
   - Write the new entry in the active section as normal
   - Preserve the old entry's `[confirmed:...]` and `[recalled:...]` tags

6. On `keep both` → write the new entry alongside; both stay active.

7. On `edit relationship` → drop into inline editing for the new entry. After save, write it normally without supersede.

8. On `skip new entry` → do not commit the new entry. Log to triage-log: "skipped new <type> on <node> — concept-drift conflict with existing entry, user declined."

Cost: one low-cost/fast-tier call per new knowledge entry that's being written to a node with > 0 prior entries of the same type. Typical commit writes 2-4 knowledge entries → 2-4 calls → ~$0.005 per `/remember` invocation. Negligible.

## People and person pages

#### D. People Index (append or update)

```
[node-id] PEOPLE: [[person/<slug>]] ([role]) — [context]. Also in: [[<other-node-id>]], [[<other-node-id>]]
```

**Wikilink rule (v4.10+):** Always emit `[[person/<slug>]]` if the person page exists at `<config-root>/memory/person/<slug>.md`. If no page exists yet, emit the bare name (e.g., `Kim Smith`) and update `<config-root>/memory/.person-mention-counts.json` — when a person hits ≥3 mentions across ≥2 nodes, the next `/end-day` (Step 3.7) proposes graduation to a person page. Same wikilink rule applies to client / company / topic / workstream / domain references within this entry.

##### D.1 Person-page graduation (v4.2+)

After writing PEOPLE entries to project nodes, check each person against the graduation triggers from cortex's CLAUDE.md:

1. **Explicit `[ENTITY:person]` tag** in the conversation → graduate immediately. This is the strongest signal.
2. **Three or more `/recall` invocations** for this person (check `memory/.person-recall-counter.json`) → graduate.
3. **`contact-researcher` produced a dossier** earlier in this conversation (look for a recent run of that agent referencing this slug) → graduate; use the dossier as the page's initial Notes section.
4. **`project-setup` named them as primary contact** for a new engagement that's also being committed in this run → graduate.

To graduate:
1. Compute slug: `firstname-lastname` lowercased, hyphenated. Check for name collision: if `memory/person/<slug>.md` exists but is about a different person (different company / different email), prompt the user once to disambiguate; recommend appending a company hint (`<slug>-<company-slug>.md`).
2. Create `memory/person/<slug>.md` with the schema from CLAUDE.md. Pre-fill what you know from this conversation (Identity, Relationship line, first Recent interactions entry dated today). Leave unknown fields as `_(unknown — fill in next conversation)_`.
3. Add an "Active people" entry to DASHBOARD.md (see **Dashboard format** above).
4. If a recall counter entry exists for this slug, reset its count to `0` (the page now satisfies the trigger).

If a page **already exists** for this person, treat this run as an additive update:

- Append a new line to the page's **Recent interactions** section: `<today> — <conversation_or_activity_type> — <one-line summary>`. Don't duplicate; if an identical line already exists for today, skip.
- Update **Last meaningful contact** in the Relationship section.
- Update **Relationship temperature** if today's interaction crosses a threshold (e.g., from Cold → Warm after a meeting).
- Never overwrite **Notes**, **Identity**, or **Linked entities** without explicit user confirmation. If new identity info contradicts existing, surface the conflict and ask.
- Keep Recent interactions to the last 90 days; older entries get archived to the page's bottom under a `## Archive (>90 days)` section to keep the active surface readable.

Casual mentions (a name appearing in conversation without any of the graduation triggers above) **do not** create or update a person page. They stay in the project node's PEOPLE index.

#### E. Cross-Project Signals (if applicable)

```
[other-node-id] SIGNAL from [source-node-id] (YYYY-MM-DD): [the implication]
```

## Orphan warning for new nodes (Step 3.4)

If Step 3 created a NEW node file (didn't write to an existing one), check the new node's outbound wikilink count:

1. Count `[[` occurrences in the new file's content.
2. Scan the content for named-entity mentions (capitalized "First Last" patterns, capitalized company names, recognized topic keywords).
3. If outbound wikilinks < 2 AND named entities are mentioned in content but NOT wikilinked, surface a one-shot prompt:

```
Heads up: <node-path> is a new node with <N> outbound wikilinks but mentions:
  - <entity 1>
  - <entity 2>
  - <entity 3>

These look like they should be wikilinks. Convert?
  (y)es — convert plain-text mentions to wikilinks where matching nodes exist
  (n)o — keep as plain text for now (you can run /relink-memory later)
  (s)kip-always — don't ask for new nodes again this session
```

**Autonomy mode handling:**
- `auto` → skip the prompt; convert silently using `/relink-memory`-style heuristic
- `suggest` (default) → surface the prompt
- `confirm` → surface the prompt with extra emphasis

This step does NOT run when updating existing nodes (only on first-write of a new node). The goal is to prevent orphans at birth, not to nag on every memory write.

**Skip cases:**
- The new node is in `staged/` (drafts; not finalized)
- The user passed `--no-orphan-check` on the `/remember` invocation
- The content is genuinely solo (no named entities mentioned) — just a thought or scratch note

This is the v4.11 forward-looking discipline that prevents new memory from drifting into the same disconnected pattern that `/relink-memory` had to back-fill in v4.10.
