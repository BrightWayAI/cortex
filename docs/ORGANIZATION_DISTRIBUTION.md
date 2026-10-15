# Organization and direct GitHub distribution

Cortex can be shared privately without submission to the public OpenAI plugin
directory. The GitHub repository distributes the plugin code; it never
contains or synchronizes a user's Cortex memory.

## Release-owner checklist

Before publishing a tag or commit for others to install:

1. Confirm `.channels_cache_v2.json`, `.users_cache.json`, virtual
   environments, bytecode, and OS metadata are ignored.
2. Review `git status --short --untracked-files=all` and the staged diff.
3. Run `python3 scripts/check_repo.py`.
4. Run `uv run --with 'mcp==2.2.0' python scripts/smoke_chatgpt_work.py` (confirm
   2.2.0 is still the intended pin before running; the plugin directory's
   pre-submission checks require an exact version on every `uv run`/`uvx`
   launcher, not a range).
5. Build a shareable archive with
   `python3 scripts/build_release_archive.py --output /tmp/cortex.zip`. Do not
   ZIP or copy the raw working directory; it may contain ignored local settings.
6. Test the package from a clean temporary copy with an injected temporary
   home and `CORTEX_CONFIG_ROOT`. Never test a release against real memory.
7. Test explicit `/recall` and `/remember` discovery in Claude/Cowork using a
   disposable config root before merging shared `skills/` changes.
8. Keep `.claude-plugin/plugin.json`, root `plugin.json`,
   `.codex-plugin/plugin.json`, `adapters/chatgpt_work/codex-plugin.json`, and
   `CHANGELOG.md` on the same version.
9. Publish a tag or pin a full commit SHA. Avoid pointing an organization at
   a development branch that receives unreviewed changes.

## ChatGPT workspace installation

A ChatGPT workspace administrator:

1. Opens **Admin → Plugins → Add → Import marketplace**.
2. Enters the GitHub repository URL only—not a file or subdirectory URL.
3. Leaves **Path** blank because `.agents/plugins/marketplace.json` is at the
   repository root.
4. Selects the release tag or full commit SHA.
5. Authorizes a GitHub account that can read the repository. Public and
   private repositories are supported.
6. Reviews the import result and configures Cortex as **Available** or
   **Installed** for the intended roles.

Cortex declares a bundled MCP server, so GitHub/workspace imports are marked
**Desktop only**. Members use ChatGPT desktop Local Work; installing the
workspace entry does not make local Mac files available to cloud/web Work.

## Member first run

Each member needs ChatGPT desktop and `uv`. They should start a new Local Work
chat after installation and choose their own private memory location:

```text
@Cortex configure my memory at ~/Documents/Cortex. Show me the exact path and
ask for confirmation before creating anything.
```

Equivalent terminal setup:

```bash
python3 scripts/configure_cortex.py \
  --config-root "$HOME/Documents/Cortex"
```

This creates `~/.cortex/config-root` and a minimal memory nucleus. Existing
Claude users should retain Claude's resolved root instead:

```bash
python3 hooks/session_start.py --print-root
```

Verify before any real write:

```text
@Cortex report status only. Do not read memory. Tell me the resolved config
root and whether memory exists.
```

Then test read-only recall:

```text
@Cortex recall my dashboard.
```

For the first write, require an exact preview and explicit confirmation.

## Direct repository sharing

A user who receives the repository directly can install from a checkout:

```bash
git clone https://github.com/BrightWayAI/claude-cortex.git
cd claude-cortex
codex plugin marketplace add "$PWD"
codex plugin add cortex@cortex-local
```

Restart ChatGPT desktop and begin a new Local Work chat after installation.

## Storage and permissions

The persistent cross-host pointer is `~/.cortex/config-root`. Its one line is
an absolute path. Resolution precedence is:

1. explicit project/workflow override;
2. `CORTEX_CONFIG_ROOT`;
3. `~/.cortex/config-root`;
4. the legacy Claude pointer;
5. `~/Documents/Claude`.

Every user owns a separate root by default. Do not point multiple organization
members at one shared filesystem folder: Cortex currently has process locking,
but not multi-user identity, permissions, attribution, or merge conflict
resolution.

## Updates

GitHub workspace marketplaces synchronize automatically each day and can be
updated immediately with **Admin → Plugins → Marketplaces → Sync now**. Review
and test repository changes before updating the pinned tag or commit.
