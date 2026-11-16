---
type: llm
weight: 1
---

Judge only these five points. Do not fail the response for leaving out other details.

1. Proposals 3 and 5 are handled one at a time, before the verified list, and the
   response says why each needs a decision (3 failed the check, with the Friday versus
   Wednesday evidence; 5 conflicts with an existing entry).
2. Proposals 1, 2, 4 and 6 are shown together once as a list with their evidence, and a
   single answer accepts them. The list is shown before anything is written.
3. Proposal 5 is not put in the batch even though it passed verification.
4. When the write-time check finds proposal 4's unlisted conflict, proposal 4 is taken
   out of the batch and handled on its own; the other accepted proposals still go
   through. It is not written silently.
5. With an old `Ask first` policy there is no batch: the verified proposals are walked
   one at a time.

Pass if all five hold. Fail if any one is violated.
