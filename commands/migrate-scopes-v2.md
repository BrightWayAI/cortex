---
description: One-time migration that splits personal facts (identity.md, voice.md, user.md, reflections.md, surfacing-prefs.md, style-eval-guide.md) into a private `memory/me/` scope, excluded from the shared git remote via .gitignore. Idempotent, gated by a marker file per references/migrations.md. Everything else in memory/ stays exactly where it is — no org/ wrapper directory.
---

# /migrate-scopes-v2

You are running the private-scope migration. This is Phase 2 step 2.4 of the Nucleus Operating Model Refactor: identity/voice/preferences are personal, not org-shared BrightWay facts, so they move to a scope that's excluded from whatever shared remote `memory/` eventually gets pushed to.

**Deliberately does NOT create a physical `memory/org/` directory.** Moving `client/`, `bizdev/`, `person/`, `workstream/`, etc. into an `org/` wrapper would change the node-path prefix convention baked into every plugin's node-resolution logic (`memory/{prefix}/{slug}.md`) — a much bigger, riskier ripple than this migration needs. The privacy boundary works identically without it: anything not in `me/` is implicitly shareable.

---

## Step 0 — Resolve config root, check marker

Standard config-root pattern. If `<config-root>/memory/.migration-scopes-v2-done` exists, say "Already migrated (see marker for date)" and stop.

---

## Step 1 — Move the private files

For each of these files, if it exists at `<config-root>/memory/<file>` or `<config-root>/<file>` (identity.md and voice.md have historically been written to both locations — see Step 1a):

```
identity.md
voice.md
user.md
reflections.md
surfacing-prefs.md
style-eval-guide.md
```

`git mv <config-root>/memory/<file> <config-root>/memory/me/<file>` (creates `memory/me/` if it doesn't exist). Use `git mv` specifically — this preserves file history, not a copy+delete.

### Step 1a — Resolve identity.md/voice.md duplication if present

Some installs have `identity.md` and `voice.md` at both `<config-root>/` (root) and `<config-root>/memory/` — a legacy artifact from before `references/core-contract.md`'s config-root pattern was consistently applied. If both exist:
1. Diff them. If they differ, the `memory/` copy is canonical (it's the one `/setup-identity` and Comms's `/setup-voice` have been writing to since v4.x).
2. `git mv` the `memory/` copy into `memory/me/`.
3. Delete the stale root-level duplicate (plain `rm` — it's outside the `memory/` git repo, so there's no history to preserve, but confirm the diff first so nothing unique is lost).

---

## Step 2 — Update `.gitignore`

Add to `<config-root>/memory/.gitignore` (create if missing, using `references/gitignore-template.md` as the base):

```
# Private scope — personal facts and preferences, never shared to the org
# remote. Each person keeps their own private remote or none.
me/
```

If any of the Step 1 files were tracked in git before the move, they'll show as staged renames — unstage them (`git reset HEAD -- me/ <old-paths>`) so the new `me/` location is untracked and gitignored, not tracked-but-ignored. The goal is "never committed," not "committed once then hidden."

---

## Step 3 — Update read paths (marketplace-wide, one-time)

This step is normally already done by the time a user runs this command — the Nucleus Operating Model Refactor shipped the path updates across every plugin in the same release cycle this migration was introduced (cortex v4.18.0+, and the corresponding version bump in every other plugin's own changelog). If you're running this on an older marketplace snapshot where plugins still read `<config-root>/identity.md` directly, upgrade the marketplace first — don't try to patch paths by hand.

---

## Step 4 — Write the marker

Write `<config-root>/memory/.migration-scopes-v2-done` with the ISO timestamp and the list of files moved. This is what prevents Step 1 from re-firing on the next `/end-day`, `/cleanup`, or manual re-run.

---

## Step 5 — Report

```
Private-scope migration complete.

Moved to memory/me/: identity.md, voice.md, user.md, reflections.md, surfacing-prefs.md, style-eval-guide.md
memory/.gitignore updated to exclude me/.

Everything else in memory/ is unchanged — no org/ wrapper, no path changes to client/bizdev/person/workstream nodes.
```

---

## Rerun

`/migrate-scopes-v2 --rerun` deletes the marker and re-checks for any of the six files that ended up back outside `me/` (e.g. a plugin update that regressed to writing the old path) — safe to run anytime, a no-op if everything's already in place.

---

## What this command does NOT do

- Does not create `memory/org/`.
- Does not touch `client/`, `bizdev/`, `person/`, `workstream/`, `infra/`, `team/`, or any domain node — those stay at `memory/` root.
- Does not create a remote or push anything. That's a separate, explicit user decision (see the Nucleus Operating Model Refactor brief §6 open decision #2).
- Does not rewrite `author:`/`by:` tags on existing historical knowledge entries — those apply going forward on new writes only (a full retroactive rewrite of thousands of entries is a separate, much larger undertaking not in scope here).
