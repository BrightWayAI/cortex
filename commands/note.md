---
description: Quick one-liner capture to a project node. Alias for `/remember --quick` (2026-09-15) — same behavior, kept as a separate command so existing muscle memory, schedules, and router intent mappings keep working.
---

# /note [node] [content]

`/note` is an alias for `/remember --quick`. Rewrite the invocation as `/remember --quick [node] [content]` and follow that command's Quick mode exactly — same parsing, same storage path, same one-line confirmation, same behavior notes. Do not duplicate the workflow here; `commands/remember.md` is the single source of truth.

```
/note client:acme Kim confirmed the March 15 deadline
```
is equivalent to
```
/remember --quick client:acme Kim confirmed the March 15 deadline
```
