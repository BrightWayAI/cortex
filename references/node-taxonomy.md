# Node taxonomy (v4.11+)

The canonical rules for **what node type to use when**. Prescriptive, not descriptive — `/remember` Step 1 consults this when deciding where new content lives.

The goal: every piece of content has one obvious node type. New users (and mining agents) don't drift into ad-hoc placements that fragment the second brain over time.

## The 9 node types

| Node type | Path | When to use | Example |
|---|---|---|---|
| **user** | `memory/me/user.md` | The user themselves — preferences, corrections, patterns, profile | The one and only user node |
| **client** | `memory/client/<slug>.md` | A specific client engagement — active contract, deliverables, billing relationship | `client/acme`, `client/aurora-labs` |
| **person** | `memory/person/<slug>.md` | A relationship with a specific person worth tracking individually (graduated; not every name mention) | `person/sarah-chen` |
| **company** | `memory/company/<slug>.md` | A company as an entity (not as a current engagement) — partner, vendor, target market | `company/anthropic`, `company/hubspot` |
| **topic** | `memory/topic/<slug>.md` | A subject area / body of knowledge — what you've learned about something | `topic/ai-governance`, `topic/cohort-pricing` |
| **workstream** | `memory/workstream/<slug>.md` | Ongoing initiative pipeline spanning multiple clients/people/topics (v4.9+) | `workstream/q3-outbound`, `workstream/product-strategy-2026` |
| **bizdev** | `memory/bizdev/<slug>.md` | A prospect / opportunity not yet a client — outreach in progress, deal in discovery | `bizdev/atlas-ventures`, `bizdev/jordan-cole` |
| **decision** | `memory/decision/<date>-<slug>.md` | One decision: what, inputs, who, when, what it replaces (v4.38+; `references/decision-schema.md`). Written only by `cortex_cli.py record-decision`. | `decision/2026-11-16-use-pipedrive-as-the-crm` |
| **domain** (root) | `memory/<name>.md` | A persistent area of work that isn't an engagement — operations, infrastructure, finance, profile | `company-ops.md`, `brightway-profile.md`, `studio.md` |

Two reserved subdirectories that aren't node types per se:

| Path | What |
|---|---|
| `memory/infra/<slug>.md` | Infrastructure / setup notes that aren't operational topics — plugin configs, MCP wiring, system docs |
| `memory/archive/<slug>.md` | Archived nodes (any type). `/forget --archive` moves files here. |

## Decision rules — what to pick

Ask in this order; first match wins:

1. **Is this about a specific person you have ongoing relationship with?** → `person/<slug>`
2. **Is this about a specific paying engagement?** → `client/<slug>`
3. **Is this about a prospect or opportunity not yet under contract?** → `bizdev/<slug>`
4. **Is this an ongoing initiative spanning multiple clients/people/topics over weeks-to-months with a clear start and eventual end?** → `workstream/<slug>` (v4.9+)
5. **Is this about a company as an entity (not as your current engagement with them)?** → `company/<slug>`
6. **Is this knowledge about a subject area that doesn't fit cleanly into any of the above?** → `topic/<slug>`
7. **Is this infrastructure / setup / plugin-config?** → `infra/<slug>`
8. **Is this a persistent area of YOUR work (your ops, your finances, your profile)?** → root domain `<name>.md`

A **decision** is not chosen by these rules. Whatever node the content is about, if the content is a choice that commits you going forward, it also gets a decision record (`references/decision-schema.md`), and the node it is about gets a one-line pointer to it.

If none match cleanly, use `topic/<slug>` as the default. Don't create new top-level directories.

## Anti-patterns to avoid

- **Don't conflate prospect with client.** A bizdev opportunity that closes becomes a `client/` node (with the bizdev record archived or moved). Two distinct lifecycle phases, two distinct nodes.
- **Don't put a person's role description in `client/<slug>`'s PEOPLE section if they meet graduation criteria.** Graduate them to `person/<slug>` and wikilink from the client node. Tracked via `memory/.person-mention-counts.json`.
- **Don't make ad-hoc top-level directories.** If you find yourself wanting `memory/projects/`, `memory/strategy/`, `memory/team/` — pause. Strategy is `topic/`. Team members are `person/`. Projects are `client/` or `workstream/`. Domain-shaped work is root-level `<name>.md`.
- **Don't dump knowledge into one mega-node.** A node should be focused. If `studio.md` grows past ~300 lines of knowledge entries, consider splitting subtopics into `topic/<slug>` and linking from studio.
- **Don't create a node without wikilink connections.** A new node should reference at least one existing entity. Otherwise it's a graph orphan. `/remember` Step 3.8 surfaces an orphan warning to prevent this (v4.11+).

## Naming conventions

- **Slugs are kebab-case.** `acme-corp`, `sarah-chen`, `q3-outbound`.
- **Person slugs are firstname-lastname.** Name-collision rule (per cortex CLAUDE.md): append a company hint if needed — `sarah-chen-acme`, `sarah-chen-globex`.
- **Client slugs are the company name** (kebab-case) unless multiple engagements with the same client; then append a project label — `acme-platform-rebuild`, `acme-data-strategy`.
- **Workstream slugs are descriptive of the initiative**, not the company — `q3-outbound`, `product-strategy-2026`, `ops-platform-eval`.
- **Bizdev slugs match the prospect company OR the contact person** depending on which is more identifying — `atlas-ventures`, `jordan-cole`.

## How /remember Step 1 uses this

When `/remember` is detecting the target node for new content (Step 1), it consults this taxonomy:

1. Read the content's primary subject (person / company / engagement / topic / etc.).
2. Apply the decision rules above.
3. Determine the slug.
4. Check whether the node file exists at the proposed path.
   - If yes → write into the existing node.
   - If no → flag for creation; surface the proposed node type + slug + path to the user for confirmation (or auto-create if autonomy = `auto`).

The user can always override the detection ("actually log this to topic/foo not client/acme"). But the default routing should follow the taxonomy.

## How /relink-memory uses this (v4.10.1+)

When `/relink-memory` walks existing memory and finds ad-hoc node placements (e.g., a person-shape node sitting at root level instead of in `person/`), it can propose a one-time relocation. User-gated; not auto.

## What this doc is NOT

- Not a constraint on what cortex CAN read. Cortex reads any markdown file under `memory/`; the taxonomy is about *where things should live going forward*.
- Not a hard schema enforcement. Existing nodes don't break if they violate the taxonomy. The doc guides new creation.
- Not a substitute for `/cleanup`'s orphan detection (which checks structural connection, not type placement).
- Not opinionated about the user's vocabulary. "Topic" might mean different things to different users. The taxonomy is about *shape*, not *label*.

## Quick reference

When in doubt: ask "is this an engagement? a person? a prospect? an initiative? a subject area?" Pick the one that fits. If multiple fit, prefer the more specific one (`client/` over `topic/`; `person/` over `bizdev/`).
