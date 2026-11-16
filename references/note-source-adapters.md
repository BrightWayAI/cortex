# Note-source adapters

This file is read by `note-taker` (`mode: transcript`) before each run. Each section below is a prompt-only adapter for one note-source provider. To add a new provider, add a new section here — no code change required.

Every adapter implements three concerns:

1. **`fetch(time_window) → [normalized notes]`** — pull notes from the provider for the window
2. **Field mapping** — translate provider-native fields to the normalized note shape
3. **`health_check()`** — quick smoke test the adapter runs once per session to verify the connector is reachable and the configured filters return at least one historical match (so misconfigurations fail loud at setup, not silent at `/end-day`)

The normalized note shape every adapter must produce:

```yaml
- note_id: <provider-native id>
  provider: granola | gemini | fireflies | otter | notion | drive-folder | gmail-label | custom
  source_id: <which configured source-entry this came from>
  title: <string>
  datetime: <ISO timestamp in user's local TZ>
  attendees: [<string>]
  body: <full transcript or notes text>
  source_url: <deeplink, null if unavailable>
  participants_count: <int, null if unknown>
  duration_minutes: <int, null if notes-only source>
```

---

## granola

**Config schema:**
```yaml
- id: <unique>
  provider: granola
  label: <human-readable>
  enabled: true
  scope: global | project:<node-id>
  config: {}   # no provider-specific config needed
```

**Tools used:** Granola MCP — `list_meetings`, `query_granola_meetings`, `get_meeting_transcript`.

**`fetch(time_window)`:**

1. Call `query_granola_meetings` with the window's `from` and `to` (or fall back to `list_meetings` if the query tool isn't available, then filter client-side).
2. For each meeting returned, call `get_meeting_transcript` to fetch the body.
3. Map fields:
   - `note_id` ← Granola's meeting ID
   - `title` ← meeting title
   - `datetime` ← meeting start time (Granola returns UTC; convert to user's local TZ)
   - `attendees` ← list of attendee names + emails
   - `body` ← transcript text
   - `source_url` ← Granola deeplink if the API returns one; null otherwise
   - `participants_count` ← `len(attendees)`
   - `duration_minutes` ← derived from start/end

**`health_check()`:** call `list_meetings` with a small window (e.g., last 14 days). Pass if ≥ 1 meeting returns. Fail if connector is unreachable or returns 0 historical meetings (likely misconfigured account).

---

## gemini

Gemini meeting notes can land in two places — Drive (the doc Gemini drops into a folder) or Gmail (the summary email). Two methods.

**Config schema:**
```yaml
- id: <unique>
  provider: gemini
  label: <human-readable>
  enabled: true
  scope: global | project:<node-id>
  config:
    method: drive-folder | gmail-search
    # drive-folder method:
    folder_id: <gdrive folder where Gemini drops notes>
    filename_pattern: <regex or glob — typically "Notes by Gemini">
    # gmail-search method:
    query: <Gmail query, e.g., "from:meet-noreply@google.com OR subject:'Notes by Gemini'">
```

**Tools used:**
- For `drive-folder`: Drive MCP — `search_files`, `read_file_content`
- For `gmail-search`: Gmail MCP — `search_threads`, `get_thread`

**`fetch(time_window)` (drive-folder method):**

1. Call `search_files` scoped to `folder_id`, filename matches `filename_pattern`, modified within window.
2. For each match, call `read_file_content`.
3. Parse the Gemini doc structure (typical: title at top, attendees list, meeting summary, action items, full transcript). Map:
   - `note_id` ← Drive file ID
   - `title` ← doc title (usually the meeting title)
   - `datetime` ← parsed from doc body (Gemini includes the meeting datetime in the doc header) or fall back to file's `createdTime`
   - `attendees` ← parsed from doc's attendees section
   - `body` ← doc body (full)
   - `source_url` ← Drive `webViewLink`
   - `participants_count` ← `len(attendees)`
   - `duration_minutes` ← parsed from doc if present, else null

**`fetch(time_window)` (gmail-search method):**

1. Call `search_threads` with the configured query, restricted to the time window.
2. For each thread, `get_thread` to fetch the message body.
3. Map similarly — extract title, datetime, attendees from the email subject and body.
4. `source_url` ← Gmail thread URL.

**Cross-source dedup hint:** Gemini-via-Drive and Gemini-via-Gmail almost always represent the same meeting twice. `note-taker` (`mode: transcript`)'s cross-source dedup step will merge them automatically (same title, datetime ±10 min, attendees match). Don't worry about it at the adapter level.

**`health_check()`:**
- `drive-folder`: call `search_files` on the configured folder; pass if folder exists and has ≥ 1 matching file historically
- `gmail-search`: call `search_threads` with the configured query and a 90-day window; pass if ≥ 1 match

Fail if the folder ID is invalid or the query syntax is malformed — return the error verbatim so the user knows what to fix.

---

## fireflies

**Config schema:**
```yaml
- id: <unique>
  provider: fireflies
  label: <human-readable>
  enabled: true
  scope: global | project:<node-id>
  config: {}   # optional: filter by team or workspace if user has multiple
```

**Tools used:** Fireflies MCP — meeting list / get methods. If the user doesn't have a Fireflies MCP connected, this adapter's health check fails and the source is skipped.

**`fetch(time_window)`:**

1. List meetings in the window via the Fireflies MCP.
2. For each, fetch the transcript.
3. Map to the normalized shape using Fireflies' native field names (meeting_id, title, date, attendees, transcript, deeplink).

**`health_check()`:** list meetings for the last 14 days; pass if ≥ 1 returns.

---

## otter

**Config schema:**
```yaml
- id: <unique>
  provider: otter
  label: <human-readable>
  enabled: true
  scope: global | project:<node-id>
  config: {}
```

**Tools used:** Otter MCP (if connected). Otter doesn't have a first-party Cowork MCP at time of writing — most users with Otter sync recordings into a Drive folder, in which case use the `drive-folder` provider instead with a filename pattern matching Otter's output.

If a native Otter MCP exists: `list_recordings`, `get_recording_transcript`.

**`fetch(time_window)`:** standard — list + fetch + map.

**`health_check()`:** as above.

---

## notion

**Config schema:**
```yaml
- id: <unique>
  provider: notion
  label: <human-readable>
  enabled: true
  scope: global | project:<node-id>
  config:
    database_id: <Notion database holding meeting notes>
    title_property: <name of the title property in that DB>
    date_property: <name of the date property>
    attendees_property: <optional: name of the attendees property>
```

**Tools used:** Notion MCP — `query_database`, `read_page`.

**`fetch(time_window)`:**

1. Call `query_database` on `database_id`, filtered by `date_property` within window.
2. For each row, call `read_page` to fetch content.
3. Map:
   - `note_id` ← Notion page ID
   - `title` ← page's `title_property` value
   - `datetime` ← page's `date_property` value (converted to local TZ)
   - `attendees` ← page's `attendees_property` if set, else parsed from page body or left empty
   - `body` ← full page content (markdown-rendered)
   - `source_url` ← Notion page URL
   - `participants_count` / `duration_minutes` ← null unless the page has explicit properties for them

**`health_check()`:** call `query_database` with no date filter; pass if database exists and returns ≥ 1 row historically. Fail with the Notion API error if the database ID is invalid.

---

## drive-folder (generic)

Generic adapter for any folder in Drive that receives meeting notes (any provider, any format — Apple Notes exports, Obsidian sync, manually-saved docs).

**Config schema:**
```yaml
- id: <unique>
  provider: drive-folder
  label: <human-readable>
  enabled: true
  scope: global | project:<node-id>
  config:
    folder_id: <gdrive folder>
    filename_pattern: <regex or glob, optional — defaults to "*">
    title_extraction: filename | doc-title | first-line   # how to pull title
    datetime_extraction: file-created | file-modified | parse-from-body   # how to pull datetime
```

**Tools used:** Drive MCP — `search_files`, `read_file_content`.

**`fetch(time_window)`:**

1. `search_files` scoped to folder, filename matches pattern, modified within window.
2. For each file, `read_file_content`.
3. Map per `title_extraction` and `datetime_extraction` config.
4. `attendees` ← parsed from body if a known marker is present (e.g., "Attendees:" line), else empty list
5. `source_url` ← Drive `webViewLink`

**`health_check()`:** search the folder for any historical file matching the pattern. Pass if ≥ 1 found.

This adapter is intentionally lenient — it's the catch-all. Users running providers without first-party MCPs can drop notes here.

---

## gmail-label (generic)

Generic adapter for any Gmail thread tagged with a specific label.

**Config schema:**
```yaml
- id: <unique>
  provider: gmail-label
  label: <human-readable>
  enabled: true
  scope: global | project:<node-id>
  config:
    label: <Gmail label name, e.g., "meeting-notes">
    sender_filter: <optional, e.g., "from:assistant@otter.ai">
```

**Tools used:** Gmail MCP — `search_threads`, `get_thread`.

**`fetch(time_window)`:**

1. `search_threads` with query `label:<label>` (+ optional sender filter) in the window.
2. For each thread, `get_thread`.
3. Map: title from subject, datetime from message date, attendees from thread participants, body from message body.

**`health_check()`:** check the label exists (`list_labels`) and a 90-day window returns ≥ 1 match.

---

## custom

Open-ended free-form adapter for sources that don't fit the above. Configured with a free-form prompt describing how to fetch and map.

**Config schema:**
```yaml
- id: <unique>
  provider: custom
  label: <human-readable>
  enabled: true
  scope: global | project:<node-id>
  config:
    description: <free-form prose: where the notes live, how to fetch them, how to map fields>
    tools: [<list of MCP tool names the adapter should use>]
```

**`fetch(time_window)`:** the agent reads `description` and figures it out using the named tools. This is the lowest-confidence adapter — quality depends entirely on how clearly the user described the source.

**`health_check()`:** the agent attempts the described fetch with a 14-day window. If it errors or returns nothing, mark unhealthy.

---

## Adding a new provider

To add support for a new note source (e.g., Zoom Cloud Recordings, Loom):

1. Add a new `##` section to this file matching the pattern above (Config schema → Tools used → `fetch(time_window)` → `health_check()`).
2. Decide the provider ID (lowercase, hyphenated).
3. If the new provider's MCP isn't already in the user's stack, document the install step in the section's intro.
4. No agent code changes required — `note-taker` (`mode: transcript`) reads this file at the top of each run and uses whichever adapter matches each configured source's `provider` field.
