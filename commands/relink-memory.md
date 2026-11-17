---
description: Retroactive wikilink pass over `<config-root>/memory/`. Scans every node file for plain-text mentions of known entities (people / clients / topics / workstreams / companies / domains) and proposes converting them to `[[wikilinks]]`. For heavy-mention persons without a person page yet, proposes graduation to `memory/person/<slug>.md`. User-gated. Idempotent. Gated by `memory/.migration-wikilink-relink-done` marker. Run once after upgrading to cortex v4.10+; future memory writes use wikilinks natively.
---

# /relink-memory

You are running the retroactive wikilink pass. The user's existing memory was written before v4.10's wikilink discipline — most entity mentions are plain text. This command finds them and proposes wikilink conversions, plus graduates heavily-mentioned persons into person pages.

This is a **one-time migration** (per `references/migrations.md`). Idempotent on re-run; gated by `<config-root>/memory/.migration-wikilink-relink-done` marker.

**`--rerun`** forces re-scan even after marker exists (for testing or after new entities have been added).

---

## Step 0 — Resolve config root

Standard pattern. If `<config-root>/memory/` doesn't exist, abort with "no memory to relink."

---

## Step 1 — Check marker

If `<config-root>/memory/.migration-wikilink-relink-done` exists AND user did not pass `--rerun`, log "wikilink relink already complete; skipping" and exit. Surface "run with `--rerun` to re-scan after adding new entities."

Otherwise continue.

---

## Step 2 — Build the entity registry

Walk `<config-root>/memory/` and build a list of every known entity (each one a target wikilink):

| Source | Entity wikilink | Display names to match |
|---|---|---|
| `memory/client/<slug>.md` | `[[client/<slug>]]` | Slug variants + the `# Title` line of the file + any aliases in front-matter or first paragraph |
| `memory/person/<slug>.md` | `[[person/<slug>]]` | Slug variants + the `# Name` line |
| `memory/company/<slug>.md` | `[[company/<slug>]]` | Slug variants + the `# Name` line + aliases |
| `memory/topic/<slug>.md` | `[[topic/<slug>]]` | Slug variants + the `# Title` line |
| `memory/workstream/<slug>.md` | `[[workstream/<slug>]]` | Slug variants + the `# Name` line |
| `memory/bizdev/<slug>.md` | `[[bizdev/<slug>]]` | Slug variants + the `# Name` line |
| Root-level domain nodes (e.g., `memory/<name>.md`) | `[[<name>]]` | Slug + the `# Title` line + Scope `aliases:` if present |

For each entity, derive **display name variants** that should be matched as plain-text mentions:
- The exact `# Title` / `# Name` line from the file
- Slug expansion (kebab-case → spaces: `sarah-chen` → "Sarah Chen")
- Aliases from front-matter (`aliases: [...]`) or from a `## Aliases` section
- Acronyms (for companies / topics) where listed

Build a registry dict in working memory: `{display_variant: [[wikilink]]}`.

Be careful with very short slugs (e.g., a 2-letter company name "AI") — they'd false-match too much text. **Minimum 3 characters** per match candidate; below that, require capitalization match + word-boundary.

---

## Step 2.5 — DASHBOARD wikilink regeneration (v4.10.1+)

Special-case `<config-root>/memory/DASHBOARD.md`. Pre-v4.10.1 DASHBOARDs typically use `### node-id` section-header style for active nodes with NO wikilinks. This makes DASHBOARD a graph-isolated island despite being the conceptual central hub.

Detection: if DASHBOARD.md has fewer than 5 wikilinks AND has ≥ 3 `### `-style section headers in its Active Nodes section, regenerate.

Regeneration procedure:
1. Read existing DASHBOARD.md.
2. Parse the "Active Nodes" section (headers + their summary content).
3. For each node ID found as a section header, determine its actual file path under `memory/` (e.g., `client:acme-corp` → `memory/client/acme-corp.md`; `brightway-profile` → `memory/brightway-profile.md`).
4. Rewrite DASHBOARD using the wikilink-emitting template from `commands/remember.md` "Dashboard File Format" section:
   - Convert `### brightway-profile` → `### [[brightway-profile]]`
   - Convert any plain `[node-id]` token to `[[node-id]]`
   - Preserve section content (summaries, P0 lists, etc.); only the references get wikilinked
5. Verify the rewritten DASHBOARD has the wikilinks; check that every section header that previously was a node-id is now wikilinked.

Surface to user:

> "DASHBOARD.md regenerated with wikilinks: <N> node references converted. DASHBOARD is now the graph view's central hub."

If DASHBOARD already has wikilinks (≥ 5), skip regeneration.

---

## Step 3 — Scan for plain-text mentions

For each node file in `memory/` (except the entity's own file — we don't self-link):

1. Read the file content.
2. For each display variant in the registry:
   - Find plain-text occurrences NOT already inside a wikilink (regex: match the display variant only when NOT preceded by `[[`).
   - Count occurrences.
   - Determine context (which section: Knowledge / People / Changelog / Open threads / etc.).
3. **First-name expansion (v4.10.1+).** After matching full-name occurrences of a person within a file, also scan for bare first-name occurrences in the same file — these often refer to the same person after the first introduction. Rules:
   - Apply only AFTER a full-name match has been found in the file.
   - The first name must be unambiguous in this file (no other person mentioned in the file shares the same first name).
   - The bare first name must appear in a contextually consistent passage (same paragraph, or within a section that already references the full name).
   - Apply word-boundary regex to avoid substring matches ("Eric" should not match inside "America").
   - Skip very short first names (≤ 2 letters).
   - Example: file mentions "Maria Santos" once, then "Maria" three more times → all four occurrences get wikilinked to `[[person/maria-santos]]`.
4. Build a per-file conversion plan: `[(line_number, old_text, new_wikilink, section), ...]`

Also: track unmatched person-shaped mentions (capitalized "First Last" patterns) that DON'T resolve to any existing person page. These are graduation candidates.

---

## Step 4 — Identify graduation candidates

A graduation candidate is a person-name string that:
- Appears in ≥ 3 different node files, OR
- Appears ≥ 5 times total across all node files
- Does NOT have a corresponding `memory/person/<slug>.md` yet
- Is NOT in any "suppressed" list (`.person-mention-counts.json` `suppressed: true` entries)

For each candidate:
- Compute slug from the name (kebab-case)
- Resolve name collisions via the rule in CLAUDE.md (append company hint if needed)
- Collect all source nodes + first occurrences (for the one-shot synthesis pass)

---

## Step 5 — Present the proposal

Surface a summary:

```
Memory wikilink scan complete.

Scanned: 30 node files
Existing wikilinks: 28
Plain-text entity mentions found: <N>

Conversion proposals:
  - <count> mentions → [[client/<slug>]] (page exists)
  - <count> mentions → [[person/<slug>]] (page exists)
  - <count> mentions → [[topic/<slug>]] (page exists)
  - <count> mentions → [[workstream/<slug>]] (page exists)
  - <count> mentions → [[<other-types>]]

Graduation candidates (person pages to create):
  - Kim Smith (5 mentions across 3 nodes) → person/kim-smith.md
  - Jamie Park (4 mentions across 2 nodes) → person/jamie-park.md
  - ... (<count> total)

Estimated edges added to graph: ~<N>

Choose:
  (a)ccept-all — convert all mentions + graduate all candidates
  (l)inks-only — convert mentions to wikilinks; skip graduation
  (s)elect — walk per-entity with per-conversion gate
  (g)raduate-only — create person pages but don't relink existing nodes
  (c)ancel — write no changes
```

---

## Step 6 — Execute per user choice

All file mutations below go through `scripts/cortex_cli.py` (acquires the lock, writes atomically, releases — see `references/core-contract.md` §11); do not hand-edit node files directly. Because a wikilink conversion is a text substitution across an entire file rather than one section, use `write-file` with the full updated content:
```
python3 scripts/cortex_cli.py write-file --memory-root <config-root>/memory \
  "<node-relative-path>" "<entire file content with mentions converted>"
```

### `accept-all`
- For each affected node: read the file, replace every plain-text mention with the wikilink in memory (preserve surrounding whitespace and punctuation), then `write-file` the whole updated content back in one call.
- For each graduation candidate: run the synthesis pass (Step 7) to create the person page. Then re-scan that name across all nodes and convert plain-text mentions to `[[person/<slug>]]` the same way.
- Log every change.

### `links-only`
- Only convert mentions where the target wikilink already exists.
- Skip graduation candidates entirely.

### `select`
- Walk per-entity. For each unique entity in the proposal:
  > "Convert <N> mentions of "Kim Smith" → `[[person/kim-smith]]`? (Page exists.) (y/n/skip-entity)"
  > "(For graduation candidates:) Create person page for Sarah Park (4 mentions across 2 nodes)? (y/n/never)"

### `graduate-only`
- Run synthesis for all graduation candidates.
- Don't touch existing plain-text mentions in other nodes (they stay as plain text).

### `cancel`
- Write no changes. Don't write the marker. Next run starts over.

---

## Step 7 — Person-page synthesis (for graduations)

For each name being graduated:

1. Read every node file that mentions the name.
2. Extract contextual information:
   - Role / title (from PEOPLE entries: "VP Eng," "founder")
   - Company / affiliation (from PEOPLE entries: "Acme contact")
   - Recent interactions (from changelog mentions, dates)
   - Open threads referencing them
   - Notes / context from mentions in knowledge entries
3. **Person-to-person cross-linking (v4.10.1+).** While scanning source nodes, also collect OTHER persons mentioned in the same contexts (paragraphs, sections, or open threads). For each other person, check whether their person page exists:
   - If yes → add to the new page's `## Linked entities` under `Other people: [[person/<slug>]]`.
   - If no → skip (don't pre-graduate cascading).
   - Limit: 10 cross-linked people per page (more dilutes the signal).
   - Examples of co-occurrence that qualify: appearing in the same PEOPLE block, mentioned in the same Recent Interactions entry, in the same Open Threads item, in the same Changelog line.
4. Compose a person page following the schema (Identity / Relationship / Recent interactions / Open threads / Notes / Linked entities). The Linked entities section now includes:
   - **Employer / affiliation:** `[[brightway-profile]]` or `[[client/<slug>]]` or `[[company/<slug>]]` as applicable
   - **Primary engagements:** `[[client/<slug>]]`, `[[bizdev/<slug>]]`, `[[workstream/<slug>]]`
   - **Other people (v4.10.1+):** cross-linked colleagues from Step 7.3
   - **Topics they discuss:** `[[topic/<slug>]]` if there are clear topic threads in their interactions
5. Write the new page:
   ```
   python3 scripts/cortex_cli.py write-file --memory-root <config-root>/memory \
     "person/<slug>.md" "<composed page content>"
   ```
6. Update `<config-root>/memory/.person-mention-counts.json` — reset the count for this person to 0 (now that they have a page, future mentions are wikilinked directly). Also a `write-file` call, same pattern.
7. **Reciprocal back-linking (v4.10.1+).** For each `Other people` entry added in Step 7.3, also append the new person to THAT person's page's `Other people` list:
   ```
   python3 scripts/cortex_cli.py append-section --memory-root <config-root>/memory \
     "person/<other-slug>.md" "## Linked entities" "Other people: [[person/<new-slug>]]"
   ```
   Avoids one-way edges — if Erica links to Mary Kate, Mary Kate also links back to Erica. Idempotent: check the section body first and skip the call if already present.

If the synthesis can't extract enough context (e.g., the name only appears in a list with no surrounding detail), the page is created with sparse content + a note: "Sparse page — populate via /recall person:<slug> or by editing directly."

### Cross-linking pass for existing person pages (v4.10.1+ on --rerun)

If `/relink-memory --rerun` is invoked, ALSO run the cross-linking pass over existing person pages (not just newly-graduated ones). For each existing person page:
- Scan source nodes that mention this person.
- Identify other persons mentioned in the same contexts.
- Add missing `Other people: [[person/<slug>]]` entries to `## Linked entities`.
- Reciprocate the link on the other person's page.

This back-fills the network fabric on pages that were graduated before v4.10.1 (where person-to-person edges weren't created).

---

## Step 8 — Refresh derived state

After conversions complete:

1. `python3 scripts/cortex_cli.py reindex --memory-root <config-root>/memory` — regenerates `<config-root>/memory/index.md` (now with workstream + person sections populated correctly).
2. `python3 scripts/cortex_cli.py refresh-hot --memory-root <config-root>/memory --trigger manual` — refreshes hot.md.
3. `python3 scripts/cortex_cli.py append-line --memory-root <config-root>/memory "staged/queues/reindex" "<today ISO> touched: relink-memory"` — the next `/end-day` will re-confirm.

---

## Step 9 — Write the marker

If the full pass completed successfully (`accept-all`, `links-only`, or `select` with at least one accept):

```
python3 scripts/cortex_cli.py write-file --memory-root <config-root>/memory \
  ".migration-wikilink-relink-done" "<today ISO> wikilink-relink complete: <C> mentions converted, <G> person pages graduated, <S> entity types touched.
"
```

If user chose `cancel`, do NOT write the marker — next run starts fresh.

---

## Step 10 — Log + report

Invoke `log-writer` skill:
- **op_name:** `relink-memory`
- **summary:** `<C> wikilink conversions, <G> person pages graduated. Graph density ~<old>× → ~<new>× (estimated <X> new edges).`

Surface to user:

```
Memory relink complete.

Wikilink conversions: <C>
Person pages graduated: <G> (now at memory/person/)
Estimated graph edges: <before> → <after>

Open Obsidian graph view to see your network. The graph view auto-refreshes on file changes; no manual reload needed.

Going forward: cortex v4.10+ emits wikilinks natively for any new memory writes. You won't need to run /relink-memory again unless you add many entities manually outside of /remember.
```

---

## Idempotent re-runs

After successful completion, the marker file gates re-execution. `/relink-memory` without `--rerun` is a no-op.

`/relink-memory --rerun` deletes the marker and re-scans — useful when:
- New entities have been added since the last run (and you want to back-fill their plain-text mentions in older nodes).
- You manually edited a node and want to verify wikilink density.
- Testing or debugging.

---

## Conflict handling

- **Name collisions** (two persons → same slug): apply the CLAUDE.md rule (append company hint to slug). Surface the proposed slug variants to the user before writing.
- **Existing wikilinks not re-converted**: text already inside `[[...]]` is left alone.
- **Partial matches** ("Kim" matching "Kimberly"): require word-boundary regex + minimum 3-character match. Surface uncertain matches in `select` mode.
- **Case-insensitive proper-noun match** for entity names: "kim smith" in lowercase still matches `[[person/kim-smith]]`. The wikilink display text preserves the original casing.

---

## What this command does NOT do

- Does not modify entity content (the wikilink target files are not edited; only OTHER files that mention them).
- Does not delete or archive anything.
- Does not change knowledge-entry tags (`[confirmed:...]`, `[recalled:...]` — those stay).
- Does not affect `staged/` content (drafts are pre-merge; they relink themselves when accepted).
- Does not modify `briefs/`, `archive/`, or any non-memory directory.
- Does not require an internet connection.
- Does not call any LLM beyond the cheap-tier classifier for name-collision and person-page-synthesis tasks.

---

## Cost

For a typical memory (30-100 nodes):
- Scan + match: pure file walk, ~5 seconds.
- Conversion application: file writes, ~10 seconds.
- Person-page synthesis: full-tier model (Claude adapter: Sonnet) for each graduation, ~30 seconds per page.
- Total: 1-3 minutes for ~30 nodes; 5-10 minutes for ~100 nodes.

Token cost: ~$0.10-0.50 per run depending on graduation count and node-content volume.
