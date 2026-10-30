---
description: Commit this conversation to working memory. Default (full extraction) pulls knowledge, decisions, insights, open threads, and next actions from the whole conversation. `--quick [node] [content]` skips extraction for a one-line changelog note. `--knowledge <type> [node] [content]` skips extraction for a single typed knowledge entry. Also flushes any observations accumulated by the passive learning engine. Full mode can run user-triggered or silent (auto-triggered at conversation end).
---

# /remember

You are committing something to Claude's working memory. Work through the mode that matches the invocation.

---

## Step G — Config-root guard (run first)

Run `python3 scripts/cortex_cli.py root-status`. If it exits non-zero, **stop** and show its sentence verbatim; write nothing anywhere else and do not ask for folder access more than once per session. Exception: in a remote session with the sync repos attached, run the documented `bootstrap` (`references/core-contract.md` §11B) once and re-check before stopping.

## Mode Detection

This command runs in one of four modes:

### Full mode (default — user triggered `/remember` explicitly, no flag)
- Complete extraction with all steps below (Step 0 onward)
- Confirmation output at the end
- User sees what was committed

### Silent mode (auto-triggered at conversation end)
- Same extraction logic as full mode, but NO confirmation output
- Triggered when the conversation is ending (farewell signals detected)
- Skip if the conversation was trivial (no decisions, no knowledge, no meaningful observations)
- Exception: if creating a NEW node, briefly mention: "Noted — started tracking [node-id]."
- Always commit user observations (corrections, preferences) even from trivial conversations — these are never wasted

### Quick mode (`/remember --quick [node] [content]`)
- Absolute minimum friction: one line, no extraction, no continuity check. Replaces the retired `/note` command (2026-09-15) — same behavior, same usage.
- Skip Steps 0 onward entirely. Go straight to "Quick mode workflow" below.

### Knowledge mode (`/remember --knowledge <type> [node] [content]`)
- Single typed knowledge entry, no full-conversation extraction, no changelog entry. Replaces the retired `/learn` command (2026-09-15) — same behavior, same usage.
- Skip Steps 0 onward entirely. Go straight to "Knowledge mode workflow" below.

---

## Quick mode workflow

Usage patterns:
```
/remember --quick client:acme Kim confirmed the March 15 deadline
/remember --quick bizdev Had intro call with Stripe partnership team — they're interested
/remember --quick hiring Sent offer letter to Jordan for the ops manager role
/remember --quick strategy:pricing Competitor just dropped their entry tier to $29/mo
```

1. **Parse.** Extract **node** (required — infer from conversation context or ask if missing/ambiguous) and **content** (everything after the node).
2. **Resolve `<config-root>`** per `references/core-contract.md` §1 (respects the legacy pointer, the `~/.cortex/config-root` pointer, and the `~/Documents/Claude` default — never hardcode a path). Cowork: `mcp__cowork__request_cowork_directory(path=<config-root>)`, wait for approval. Claude Code: direct filesystem access. If inaccessible, explain memory can't persist without it and stop.
3. **Write.** Determine the node's relative file path from the node ID (`references/core-contract.md` §3; legacy `client:acme-corp` colon syntax and `client/acme-corp` slash syntax map to the same file). Build the entry `[node-id] LOG YYYY-MM-DD — Note: [content]` and write via the shared locking/atomic-write utility — do not hand-edit the file:
   ```
   python3 scripts/cortex_cli.py prepend-section \
     --memory-root <config-root>/memory \
     "<node-relative-path>" "## Changelog" "[node-id] LOG YYYY-MM-DD — Note: [content]"
   ```
   This inserts newest-first in `## Changelog`, creates the section/file from the standard template if absent, and handles locking/atomicity internally.
4. **Update `DASHBOARD.md`'s "Last updated" timestamp.** Only update the dashboard summary if the note represents a significant state change; don't touch the living summary otherwise.
5. **Confirm** with exactly one line: `Noted in [node-id]: [content]`. No analysis, no follow-up questions.

If the content looks like it should be a knowledge entry (gotcha, lesson, model) instead, suggest: "This sounds like a [type] — want me to `/remember --knowledge [type]` it instead so it's easier to find later?" Multiple quick-mode calls in a row are handled independently.

---

## Knowledge mode workflow

Usage patterns:
```
/remember --knowledge gotcha client:acme Their procurement team requires 3 vendor quotes even for renewals — build in 2 weeks lead time
/remember --knowledge model bizdev:partnerships Channel partners want co-marketing commitments before signing — lead with the joint campaign plan, not the rev share
/remember --knowledge lesson strategy:pricing Tried usage-based pricing with mid-market — too unpredictable for their budgets. Flat tiers with overage charges landed better.
/remember --knowledge recipe domain:healthcare-compliance For HIPAA BAAs: use our template, get their legal to redline first, then negotiate — saves 2 rounds of back-and-forth
/remember --knowledge insight learning:sales-ops The bottleneck isn't lead gen — it's the handoff from SDR to AE. Leads go cold in the 48-hour gap.
/remember --knowledge that the API rate limit resets hourly not daily
```

1. **Parse.** Extract **node** (required), **type** (one of the seven canonical types below — infer from content if omitted), **content**. If given as bare natural language with no explicit type/node, infer both from conversation context (ask if genuinely ambiguous).

2. **Infer type if not specified**, against the canonical seven-type taxonomy (see Step 3's Knowledge Taxonomy note below):

   | If the content sounds like... | Assign type |
   |-------------------------------|-------------|
   | "X works by..." / "Their process is..." / "The way X actually works is..." | MODEL |
   | "Watch out for..." / "Don't assume X" / "They require Y even though..." | GOTCHA |
   | "Tried X, it [worked/failed] because..." / "What worked was..." | LESSON |
   | "I was wrong about X — actually it's Y" / "Turns out..." | CORRECTION |
   | "For [situation], do [steps]" / "The playbook for X is..." | RECIPE |
   | A forward-looking commitment with a clear trigger to revisit | DECISION |
   | General realization or connection that doesn't fit the above | INSIGHT |

3. **Resolve `<config-root>`** the same way as Quick mode; never bypass the resolver with a hardcoded default path.

4. **Write.** Determine the node file path per `references/core-contract.md` §3. Read the node file if it exists. Append the entry to the matching section (`### Insights`, `### Lessons`, `### Models`, `### Gotchas`, `### Recipes`, `### Corrections`, `### Decisions` — see the Node File Format in Step 4 below for the canonical section list) using the shared locking/atomic-write utility (`cortex_cli.py prepend-section`), never a hand-edit. If the node file doesn't exist, create it from the standard template first.

   ```
   [node-id] TYPE (YYYY-MM-DD): [content, compressed but precise]
   ```

   A DECISION entry follows the required-fields format in Step 3 §B below (Why / Affected / Revisit when / Status), not the bare one-liner.

5. **Concept-drift check.** Does this new knowledge invalidate or reinforce an existing entry in the same section? Invalidates → update/remove the old entry, note the correction (or write a CORRECTION entry if the old entry is worth preserving as a superseded marker). Reinforces → no file change, mention it in the confirmation. Skip this check for RECIPE entries (additive techniques, not competing facts) — same rule as full mode.

6. **Update `DASHBOARD.md`** — add/update the node's Active Nodes summary if new, add to Recent Knowledge, add to Global Gotchas if the entry is a broadly-applicable GOTCHA. Update the living summary only if this knowledge materially changes the node's current state.

7. **Confirm:**
   ```
   Committed to [node-id]:
   [TYPE]: [content]

   [If applicable: "This updates/replaces a previous [TYPE] entry from [date]."]
   ```

If the knowledge clearly spans multiple nodes, write to each. Multiple knowledge-mode calls in one session are independent.

---

## Step 0 — Cheap-tier commit triage (v4.2+)

Before running the full-tier extraction below (Claude adapter: Sonnet), run a low-cost/fast-tier classifier (Claude adapter: Haiku) on the conversation to decide whether to commit at all and, if yes, which nodes are affected. This keeps per-commit cost predictable as commit volume grows.

### A — Classifier prompt

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

### B — Decision routing

Parse the classifier's response. If parsing fails (malformed JSON, model timeout), default to `commit: true, nodes: ["<detected project node>"]` so we don't silently lose a substantive conversation.

- **`commit: false`** → log one entry to `<config-root>/memory/triage-log.md` (format below), return silently. Do not run Steps 1-5. The conversation contributes nothing to memory beyond this audit line.
- **`commit: true`** → log one entry to `triage-log.md` (with the node list), then proceed to Step 1 but **pass the node list forward** so Step 1's project-detection is informed (not overridden) by the classifier's call.

### C — Triage log format

Append to `<config-root>/memory/triage-log.md` (create file if missing). Format:

```markdown
# Triage Log

_Auto-appended by cortex's two-stage commit triage. Audit weekly for false-negatives (commit:false when a real decision was made) and over-attribution (commit:true with too many nodes)._

## YYYY-MM-DD HH:MM
- Decision: [commit | skip]
- Nodes: [list, or omit if skip]
- Reason: <one-line from classifier>
- Conversation context: <one-line synthesized from your own read of the turns — what the conversation was about>
```

### D — Cost discipline

The low-cost/fast-tier call is the only model call until classification completes. If `commit: false`, Steps 1-5 (full-tier synthesis) never run. Expected cost per `/remember` invocation:
- Trivial conversations: ~$0.001 (low-cost/fast-tier classifier only)
- Substantive conversations: previous cost + ~$0.001 (negligible overhead)

Total full-tier cost drops 30-50% measured weekly when ~30-40% of conversations are trivial.

### E — When to bypass Step 0

User-invoked `/remember` with an explicit node argument (e.g., `/remember client:acme-corp`) bypasses Step 0 entirely — the user is asserting commit-worthiness. Silent mode and auto-fire commits still run Step 0.

Also bypass Step 0 if the conversation contains an explicit `[ENTITY:person]` tag with a new person — that's a strong-enough graduation signal to commit unconditionally.

---

## Step 1 — Detect the target node (v4.11+: consults taxonomy)

Scan the full conversation and identify which node(s) this content belongs to.

**First: consult `references/node-taxonomy.md` for placement rules.** The taxonomy is prescriptive — every content shape maps to one obvious node type. Apply its decision rules:

1. Is this about a specific person you have an ongoing relationship with? → `person/<slug>` (graduate via the v4.2 graduation rules if not yet a page)
2. Is this about a specific paying engagement? → `client/<slug>`
3. Is this about a prospect / opportunity not yet under contract? → `bizdev/<slug>`
4. Is this an ongoing initiative spanning multiple entities? → `workstream/<slug>` (v4.9+)
5. Is this about a company as an entity (not as engagement)? → `company/<slug>`
6. Is this a subject-area body of knowledge? → `topic/<slug>`
7. Is this infrastructure / setup / plugin-config? → `infra/<slug>`
8. Is this a persistent area of YOUR work (ops, finances, profile)? → root domain `<name>.md`

Use the FIRST match. If multiple fit, prefer the more specific (`client/` over `topic/`; `person/` over `bizdev/`).

If nothing fits cleanly, default to `topic/<slug>`. **Don't create ad-hoc top-level directories** — the taxonomy covers every legitimate shape.

**Existing node check:** Before creating a new node, search existing memory for a matching node at the proposed path. If exists, route the content there. If not, propose creation to the user (or auto-create if autonomy = `auto`).

**Slug rules:** kebab-case; firstname-lastname for persons (with company-hint disambiguation for collisions); company name for clients; descriptive of the initiative for workstreams; prospect name or contact name for bizdev.

If the session spans multiple nodes, you'll commit to each one separately in Step 3.

---

### Legacy naming conventions (deprecated as of v4.11+)

Older versions of cortex used colon-prefixed names: `client:acme-corp`, `bizdev:stripe-partnership`, `strategy:q2-growth`. These still work (the file system is path-based; `client:acme` → `client/acme.md`) but new content should follow the taxonomy directly. The colon-prefix style was a transitional convention; the prescriptive taxonomy is the canonical reference going forward.

---

## Step 1b — Capture git context (if available)

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

---

## Step 2 — Extract structured memory

Pull from two categories: **what changed** (project state) and **what was learned** (knowledge).

Not every session will have entries in every category. A pure learning/exploration session may have nothing in "project state" — that's fine. Extract what's actually there.

### A. Project State (what changed)

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

### B. Knowledge (what was learned)

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

DECISIONS (v4.9+):
- A choice made — forward-looking commitment, not a retrospective lesson
- Cues: "we decided," "I'm going with," "settled on," "going forward we'll," "the call is," "made the call to"
- Required fields when captured:
  - **What was decided:** the choice
  - **When:** YYYY-MM-DD
  - **Why:** reasoning at the time
  - **Affected:** wikilinked entities affected by the decision
  - **Revisit when:** trigger condition for re-evaluation ("if vendor raises prices," "annually," "if we hire a 3rd person") — or "n/a" if no specific trigger
  - **Status:** active (default), superseded, revisit-now
- Format inline:
  - `DECISION [confirmed:YYYY-MM-DD] <one-line decision>`
  - `  - What was decided: ...`
  - `  - When: YYYY-MM-DD`
  - `  - Why: ...`
  - `  - Affected: [[entity]], [[entity]]`
  - `  - Revisit when: ...`
  - `  - Status: active`
- DECISIONs decay slowly (1.5× modifier) — they stay relevant longer than INSIGHTs. They supersede via concept-drift detection (a later DECISION on the same topic moves the earlier one to Demoted knowledge with `↳ superseded by: ...`).
- Example: "DECISION [confirmed:2026-05-15] Going with Pipedrive over HubSpot for the firm's CRM. **Why:** Pipedrive's pricing scales better at our size; HubSpot's marketing automation is more than we need. **Affected:** [[client/acme]], [[bizdev]]. **Revisit when:** if we hit 5+ active sales pipelines, re-evaluate. **Status:** active."

CONTEXT & BACKGROUND:
- Domain knowledge needed to understand this project or topic
- Terminology, acronyms, or jargon defined
- Historical context: why things are the way they are
- Constraints or requirements that shape decisions
```

### C. Cross-cutting

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

### D. User Observations (from passive learning engine)

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

These observations are ALWAYS extracted, even in silent mode. They go to the `user` node, not project nodes (unless the observation is project-specific domain knowledge).

---

## Step 3 — Write to memory

### Storage Location

Memory is stored in `<config-root>/memory/` after resolving the root per
`references/core-contract.md` §1.

**Before writing**: Check if `<config-root>/memory/` is accessible.
- **Cowork**: Use `mcp__cowork__request_cowork_directory(path=<config-root>)` to request access. Wait for the user to approve.
- **Claude Code**: The directory is accessible directly via the filesystem. Create it with `mkdir -p` if it doesn't exist.

If the directory cannot be accessed, explain that memory cannot be persisted without this folder and stop.

### Step 3.0 — Acquire memory write-lock

Every write in this step goes through `scripts/cortex_cli.py`, which acquires
`<config-root>/memory/.lock` internally (see `scripts/lib/locking.py` and
`references/core-contract.md` §11), performs the read-modify-write, and
releases the lock before returning — this coordinates with `/end-day`,
`/listen`, `/morning`, `/cleanup`, and any other command using the same CLI,
regardless of whether memory-as-git is enabled. Do not hand-edit node files
for the writes in this step; do not additionally implement a separate
`.write-lock` file — the CLI's lock is the single lock for this purpose. If
the CLI reports a timeout (lock held by another process past its timeout),
surface: "Memory write-lock held by another process — wait or override?" and
retry once before asking the user (`auto` autonomy) or asking immediately
(`suggest`).

1. Determine the node's relative file path from the node ID (`references/core-contract.md` §3; `client:acme-corp` and `client/acme-corp` map to the same file).
2. Determine each section's new content (living summary, new knowledge entries, changelog line, etc.) per the formats below.
3. For each section that changes, invoke:
   ```
   python3 scripts/cortex_cli.py replace-section \
     --memory-root <config-root>/memory "<node-relative-path>" "## Summary" "<new summary text>"

   python3 scripts/cortex_cli.py append-section \
     --memory-root <config-root>/memory "<node-relative-path>" "## Knowledge" "<new entry line>"

   python3 scripts/cortex_cli.py prepend-section \
     --memory-root <config-root>/memory "<node-relative-path>" "## Changelog" "<new changelog line>"
   ```
   Each call creates the node file (with the standard template) if it doesn't exist, and creates the named section if absent — you do not need a separate "create the file" step.
4. After writing the node file, ALWAYS update `memory/DASHBOARD.md`:
   - Replace or add the node's living summary in the Active Nodes section
   - Update the Unified P0 Actions list
   - Update Waiting On if applicable
   - Add any new knowledge entries to Recent Knowledge (keep last 7 days only)
   - Update the "Last updated" timestamp
6. **Line provenance (v4.12.0+):** every line written or modified in DASHBOARD must carry an HTML comment immediately after with `<!-- by:<command> @ <YYYY-MM-DD> -->`. This makes drift detection trivial for `/cleanup` (which surfaces stale lines whose owning command hasn't refreshed them in N days).
   - Example: `- [P0] [[bizdev:harbor-education-group]]: studio.co intro angle — see if it fits <!-- by:/listen @ 2026-05-28 -->`
   - Format: `<!-- by:<command-with-slash> @ <ISO-date> -->`
   - The comment is HTML-comment syntax so it renders invisibly in Markdown previews and Obsidian — humans see clean lines.
   - When a line is refreshed by the same command on a later run, update the date. When a different command refreshes it, replace the by-value too.
   - For lines that came from manual edits (no command), use `<!-- by:manual @ <date> -->` if you know the date; otherwise omit (the absence of provenance is itself a signal `/cleanup` Section K — see below — will surface).

#### Dashboard File Format (v4.10.1+: wikilink-emitting)

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

#### Node File Format

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
[node] DECISION (date): [entry]

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
(append-only, newest first)

## Open Threads
- [FRESH/ONGOING/STALE] [description]

## Next Actions
- [P0] [action]
- [P1] [action]
- [WAITING:who] [action]

## Signals
[node] SIGNAL from [other-node] (date): [implication]
```

### User Node — Observation Flush

**Before writing project data**, flush observations to the user profile node:

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

4. Before appending, check for duplicates or contradictions:
   - If new observation reinforces existing → skip (already captured)
   - If new observation contradicts existing → write a CORRECTION entry, remove the old one
   - If new observation is genuinely new → append

5. Update `DASHBOARD.md` with the user node's last-updated timestamp

**Confidence gating**: Only commit observations with reasonable confidence. A single offhand remark is a signal, not a fact. But direct corrections — always commit.

### A. Living Summary (replace if exists, create if new)

Format:
```
[node-id] SUMMARY (updated YYYY-MM-DD): [2-4 sentences — what this is, where it stands, what's known. Include top blocker/P0 if any. Include most important recent insight if learning-heavy.]
```

Keep under 400 characters.

### B. Changelog Entry (always append)

Format:
```
[node-id] LOG YYYY-MM-DD — [3-6 word title]: [decisions] | [insights/lessons] | [artifacts] | [next actions]
```

Keep under 500 characters. Skip empty categories.

### C. Knowledge Entries (append or update)

For significant, reusable knowledge, write dedicated entries. These persist longer than logs — they're the highest-value memory content.

#### C.0 Entry metadata convention (v4.3+)

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

#### C.1 Entry formats (seven canonical types — see `CLAUDE.md` Knowledge Taxonomy)

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
[node-id] DECISION (YYYY-MM-DD): [the choice] (see DECISION required fields in §B above)  [confirmed:YYYY-MM-DD] [recalled:YYYY-MM-DD] [by:<actor-id>]
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

#### C.2 Concept-drift detection (v4.4+)

Before writing a new INSIGHT, LESSON, MODEL, or GOTCHA entry, check whether it contradicts, supersedes, or meaningfully refines an existing entry of the same type on the same node. RECIPE entries are excluded from this check (recipes are additive techniques, not competing facts). DECISION entries supersede via their own concept-drift path (a later DECISION on the same topic demotes the earlier — see §B). CORRECTION entries already encode supersede explicitly via `[old belief] → [corrected understanding]` and don't need the check.

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

### D. People Index (append or update)

```
[node-id] PEOPLE: [[person/<slug>]] ([role]) — [context]. Also in: [[<other-node-id>]], [[<other-node-id>]]
```

**Wikilink rule (v4.10+):** Always emit `[[person/<slug>]]` if the person page exists at `<config-root>/memory/person/<slug>.md`. If no page exists yet, emit the bare name (e.g., `Kim Smith`) and update `<config-root>/memory/.person-mention-counts.json` — when a person hits ≥3 mentions across ≥2 nodes, the next `/end-day` Step 3 cheap-tier triage proposes graduation to a person page. Same wikilink rule applies to client / company / topic / workstream / domain references within this entry.

#### D.1 Person-page graduation (v4.2+)

After writing PEOPLE entries to project nodes, check each person against the graduation triggers from cortex's CLAUDE.md:

1. **Explicit `[ENTITY:person]` tag** in the conversation → graduate immediately. This is the strongest signal.
2. **Three or more `/recall` invocations** for this person (check `memory/.person-recall-counter.json`) → graduate.
3. **`contact-researcher` produced a dossier** earlier in this conversation (look for a recent run of that agent referencing this slug) → graduate; use the dossier as the page's initial Notes section.
4. **`project-setup` named them as primary contact** for a new engagement that's also being committed in this run → graduate.

To graduate:
1. Compute slug: `firstname-lastname` lowercased, hyphenated. Check for name collision: if `memory/person/<slug>.md` exists but is about a different person (different company / different email), prompt the user once to disambiguate; recommend appending a company hint (`<slug>-<company-slug>.md`).
2. Create `memory/person/<slug>.md` with the schema from CLAUDE.md. Pre-fill what you know from this conversation (Identity, Relationship line, first Recent interactions entry dated today). Leave unknown fields as `_(unknown — fill in next conversation)_`.
3. Add an "Active people" entry to DASHBOARD.md (see DASHBOARD format in section "Dashboard File Format" below).
4. If a recall counter entry exists for this slug, reset its count to `0` (the page now satisfies the trigger).

If a page **already exists** for this person, treat this run as an additive update:

- Append a new line to the page's **Recent interactions** section: `<today> — <conversation_or_activity_type> — <one-line summary>`. Don't duplicate; if an identical line already exists for today, skip.
- Update **Last meaningful contact** in the Relationship section.
- Update **Relationship temperature** if today's interaction crosses a threshold (e.g., from Cold → Warm after a meeting).
- Never overwrite **Notes**, **Identity**, or **Linked entities** without explicit user confirmation. If new identity info contradicts existing, surface the conflict and ask.
- Keep Recent interactions to the last 90 days; older entries get archived to the page's bottom under a `## Archive (>90 days)` section to keep the active surface readable.

Casual mentions (a name appearing in conversation without any of the graduation triggers above) **do not** create or update a person page. They stay in the project node's PEOPLE index.

### E. Cross-Project Signals (if applicable)

```
[other-node-id] SIGNAL from [source-node-id] (YYYY-MM-DD): [the implication]
```

---

## Step 3.4 — Orphan warning for new nodes (v4.11+)

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

---

## Step 3.5 — Queue an index refresh (v4.5+)

After all writes succeed, append a line to `<config-root>/memory/staged/queues/reindex`:

```
<today YYYY-MM-DD HH:MM> touched: <node-id>[, <node-id>, ...]
```

Create the file if it doesn't exist. Idempotent — multiple `/remember` calls just append more lines.

This step does NOT regenerate `<config-root>/memory/index.md`. That happens at the next `/end-day` Step 5.5, the next `/cleanup` Step 4.5, or an explicit `/reindex`. Synchronously regenerating on every `/remember` would chunk fast capture sessions.

If the reindex-queue file ever exceeds 200 lines, the next consumer of it (indexer) ignores the contents and just runs a full regeneration — the queue is a *hint*, not a critical record.

## Step 3.6 — Lock release

No separate release step is needed: each `cortex_cli.py` invocation in Step
3.0 acquires and releases its own lock within a single process call (see
`scripts/lib/locking.py`'s context-manager semantics — release runs on
success, failure, or exception, automatically).

Silent mode (auto-commit) writes the queue line too. The next session's `/recall` auto-fire will trigger the next index refresh chain.

---

## Step 4 — Continuity check

Scan for:
- **Orphaned threads**: Still open from previous sessions, not addressed
- **Completed threads**: Previously open, now resolved
- **Escalated items**: P2s that should now be P0/P1
- **Invalidated knowledge**: New learning contradicts a prior INSIGHT/MODEL/GOTCHA → update or remove old entry
- **Reinforced knowledge**: New evidence strengthens a prior insight
- **Answered questions**: Prior "questions for next time" that got answered

---

## Step 5 — Confirm

### Full mode (user-triggered)

Respond with:
1. **Node(s)** written to
2. **Living summary** (for verification)
3. **Knowledge captured** — list INSIGHT / LESSON / MODEL / RECIPE / DECISION / GOTCHA / CORRECTION entries
4. **Observations captured** — count of preferences, corrections, patterns written to user node
5. **Open threads** with staleness
6. **Blockers** (if any)
7. **Next actions** — P0 → P1 → P2 → WAITING
8. **Cross-project signals** (if any)
9. **Knowledge updates** — prior entries invalidated, reinforced, or corrected
10. **Unanswered questions** carried forward

Keep tight. Skimmable in 20 seconds.

### Silent mode (auto-triggered)

- Say nothing unless creating a new node
- If creating a new node: "Noted — started tracking [node-id]."
- If a critical correction was captured that changes future behavior, optionally note: "Got it — I'll [adjusted behavior] going forward."
- Otherwise: complete silence. The user shouldn't notice the commit happened.

---

## Memory hygiene

- **Living summaries**: Always replace, never duplicate
- **Logs**: Append only, never modify past entries
- **Knowledge entries**: Update if understanding evolves. CORRECTION supersedes original. Remove outdated entries.
- **Memory full**: Consolidate old LOGs first. Knowledge entries should be preserved longest — they're the most reusable content.
- **Dormant nodes**: Note `[DORMANT → ACTIVE]` if reviving after 14+ days
- **Staleness**: Open threads 3+ sessions without progress → [STALE]
