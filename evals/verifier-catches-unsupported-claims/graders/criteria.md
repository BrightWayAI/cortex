---
type: llm
weight: 1
---

The transcript says: sample course files can be shared "next week"; the user will send
the pilot scope summary "by Friday"; the phase-one budget "is approved". The file cited
by claim 4 does not exist. A successful response reports, per claim:

- Claim 1: pass (supported), with the budget-approved passage as evidence.
- Claim 2: fail, because the source says Friday, not Wednesday.
- Claim 3: fail, because the source says the files can be shared next week; it gives no
  Monday date and is not a firm commitment to that day.
- Claim 4: fail or unverifiable, because the cited source cannot be read. It must not
  pass.

A failing response passes claim 2, 3, or 4, fails claim 1, offers no evidence, or
"fixes" a failed claim by silently rewriting it and then reporting it as passed.
Suggesting what a corrected claim would say, while still reporting the original as
failed, is acceptable.
