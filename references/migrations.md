# Cortex migrations — the marker-gated one-time migration pattern

_Documented 2026-05-20. Update when adding new migrations._

Some cortex changes require a one-time data transformation on existing installs — moving files, renaming sections, populating new metadata. These run **once per install**, gated by a marker file so they don't re-fire on every command.

This doc names the pattern, lists active migrations, and provides the template for adding new ones.

---

## The pattern

Each migration has:

1. **A marker file** at `<config-root>/memory/.migration-<name>-done` (hidden, simple text file with timestamp + outcome).
2. **A guard at the top of the migration's execution context** that checks the marker; if it exists, skip the migration.
3. **A standalone command or skill** that performs the migration (preferred: `/migrate-<name>`).
4. **A safe abort** — failures don't damage existing data; the marker isn't written until success.
5. **An optional `--rerun-<name>` flag** on the entry point to force re-running (for testing or recovery).

**Bad pattern (deprecated):** bolting migrations into the middle of frequently-used chains (e.g., the Scope migration was inside `/end-day` Pre-chain B for several versions). This makes the chain heavier to read and risks the migration silently re-firing if the marker is deleted.

**Good pattern (post-v4.8.1):** migrations are their own command. `/end-day` doesn't reference them. The migration runs once when the user runs `/migrate-X`, or when the chain that depends on its output detects the marker is missing and prompts the user.

---

## Active migrations

### `scope-migration` (v4.3+)

- **What:** Adds a Scope section to existing domain-shaped nodes so the mining layer can route content accurately.
- **Marker:** `<config-root>/memory/.migration-scope-done`
- **Command (post-v4.8.1):** `/migrate-scopes` (extracted from `/end-day` Pre-chain B).
- **First introduced:** cortex v4.3.0
- **Status:** stable; most existing users have completed it.
- **Rerun:** `/migrate-scopes --rerun` deletes the marker and re-walks all domain nodes.

### `decay-config-init` (v4.4+)

- **What:** Creates `<config-root>/memory/.decay-config.md` with documented default thresholds on first v4.4+ run.
- **Marker:** the existence of the file itself (no separate marker).
- **Command:** runs inline in any command that reads `.decay-config.md` if the file is missing.
- **First introduced:** cortex v4.4.0
- **Status:** stable; idempotent inline check.

### `gitignore-privacy-defaults` (v4.7.2+)

- **What:** Writes `<config-root>/.gitignore` with privacy defaults (excluding `archive/`, `memory/.commit-drafts/`, etc.) on first v4.7.2+ run.
- **Marker:** the existence of `<config-root>/.gitignore` (no separate marker — but the migration also *appends* to existing `.gitignore` files that lack the expected entries).
- **Command:** inline in `/setup-identity` Step 3.5 and `/listen` Step 0.5.
- **First introduced:** cortex v4.7.2
- **Status:** stable; idempotent.

### `wikilink-relink` (v4.10+)

- **What:** Retroactive wikilink pass over `<config-root>/memory/`. Scans existing node files for plain-text entity mentions, proposes wikilink conversion, and graduates heavily-mentioned persons into `memory/person/<slug>.md` pages.
- **Marker:** `<config-root>/memory/.migration-wikilink-relink-done`
- **Command:** `/relink-memory` (or `/relink-memory --rerun` to force re-scan after marker exists).
- **First introduced:** cortex v4.10.0
- **Status:** **new in v4.10.0.** Run once after upgrading; future memory writes use wikilinks natively per the canonical rule in cortex CLAUDE.md.
- **Failure mode:** if the user cancels mid-walk, marker is NOT written. Partial changes (the per-conversion writes that already happened) are preserved; user can re-run to finish.
- **Rerun:** `/relink-memory --rerun` is supported. Useful when new entities have been added since the last run, or for testing.

### `staged-substrates-reorg` (v4.8.1+)

- **What:** Moves dotfile-style staged state (`.commit-drafts/`, `.research-drafts/`, `.rehearse-queue.md`, etc.) into a unified `<config-root>/memory/staged/` directory tree.
- **Marker:** `<config-root>/memory/.migration-staged-reorg-done`
- **Command:** `/migrate-staged-substrates` (or inline at next `/end-day` / `/listen` / `/morning` if marker missing — auto-applies on first command that would write to either old or new path).
- **First introduced:** cortex v4.8.1
- **Status:** **new in v4.8.1.** Detect-and-move logic is gentle: if both old and new paths exist (user manually pre-created), do nothing and warn.
- **Rerun:** N/A — once moved, files are at the new path and there's nothing to re-migrate.

### `scopes-v2` (v4.18+)

- **What:** Moves personal facts (`identity.md`, `voice.md`, `user.md`, `reflections.md`, `surfacing-prefs.md`, `style-eval-guide.md`) into a private `<config-root>/memory/me/` scope, excluded from the shared remote via `.gitignore`. Deliberately does NOT create a physical `memory/org/` wrapper — `client/`, `bizdev/`, `person/`, `workstream/`, `infra/` stay at `memory/` root, since moving them would ripple through every plugin's node-path resolution logic for no privacy benefit.
- **Marker:** `<config-root>/memory/.migration-scopes-v2-done`
- **Command:** `/migrate-scopes-v2` (or `--rerun` to re-check).
- **First introduced:** cortex v4.18.0, as part of the Nucleus Operating Model Refactor Phase 2 step 2.4. Shipped alongside a marketplace-wide path update (every plugin that read `<config-root>/identity.md`/`voice.md` directly was updated to `<config-root>/memory/me/...` in the same release cycle, to avoid a broken intermediate state).
- **Status:** new in v4.18.0.
- **Failure mode:** if a duplicate `identity.md`/`voice.md` exists at both config-root and `memory/` (a legacy artifact), the migration diffs them and treats the `memory/` copy as canonical before deleting the stale root duplicate. If they differ in a way that isn't a clean "one is older," it should surface the diff and ask rather than guess.
- **Rerun:** `/migrate-scopes-v2 --rerun` is safe anytime — no-op if the six files are already in `me/`.

### `hot-cache-first-generation` (v4.7+)

- **What:** Generates `<config-root>/memory/hot.md` for the first time on a v4.7+ install.
- **Marker:** the existence of the file itself.
- **Command:** runs inline in the hot-cache regenerator if file doesn't exist.
- **First introduced:** cortex v4.7.0
- **Status:** stable; idempotent.

---

### `plugin-configs` (v4.31+)

- **What:** Archives legacy files in `<config-root>/plugins/` to `plugins/archive/` (the old-location `ops.schedules.md`, retired config files whose replacement exists, `*.bak-<date>` backups) and creates `plugins/ops/schedules.md` from the old file or the ops starter template.
- **Marker:** `<config-root>/memory/.migration-plugin-configs-done`
- **Command:** `/migrate-plugin-configs`, backed by `cortex_cli.py migrate-plugin-configs` (dry-run unless `--apply`).
- **First introduced:** cortex v4.31.0
- **Status:** new. Never run inline by another command.
- **Failure mode:** stops at the first error; nothing is deleted or overwritten; marker not written; safe to retry.
- **Rerun:** `--rerun` ignores the marker.

## Template for new migrations

Use this template when adding a new migration:

```markdown
### `<migration-slug>` (v<X.Y.Z>+)

- **What:** [One-line description of the data transformation.]
- **Marker:** `<config-root>/memory/.migration-<slug>-done`
- **Command:** `/migrate-<slug>` (preferred) OR inline check at [chain entry point].
- **First introduced:** cortex v<X.Y.Z>
- **Status:** [stable / new / deprecated]
- **Failure mode:** [What happens if the migration aborts partway? Marker NOT written; safe to retry.]
- **Rerun:** [How to force re-run for testing/recovery.]
```

When implementing:

1. Check marker → if exists, log "skipped (already done)" and return.
2. Perform the transformation.
3. On success, write the marker with `<today ISO> <outcome>` content.
4. On failure, log error, do not write marker, surface a recovery hint.

---

## Why this pattern

- **Idempotency.** Re-running commands doesn't re-transform data.
- **Auditability.** Marker files document when each migration ran.
- **Decomposition.** Migrations live in standalone commands; chains stay focused on their primary purpose.
- **Reversibility.** Easy to delete the marker + re-run for debugging.
- **Cross-version compatibility.** A user on v4.8.x can install v4.9.x and have all intermediate migrations apply in order on first run.

---

## Anti-patterns to avoid

- **Migrations bolted into chains.** Bad: `/end-day` Pre-chain B used to do Scope migration. It made `/end-day` longer and harder to read, and the migration was conceptually unrelated to closing the day. Good: `/migrate-scopes` standalone.
- **Migrations without markers.** Without a marker, the chain has to use heuristics ("does this node have a Scope section?") which can be wrong (some legitimate nodes might genuinely lack a Scope section). Markers are explicit truth.
- **Silent re-firing.** If a marker is deleted (e.g., by user, by sync conflict), the migration re-fires. Always log the re-fire and offer the user a one-line "I'm re-running migration X because marker was missing" notice.
- **Data-destructive migrations without backup.** If a migration moves files, copy first, verify, then delete originals — never `mv` blindly.
