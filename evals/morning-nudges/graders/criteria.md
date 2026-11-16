---
type: llm
weight: 1
---

Judge only these five points. Do not fail the response for leaving out other details.

1. With no overnight draft, the command does not exit: it goes on to the nudges.
2. Cedar: the nudge is dismissed (recorded as `dismissed` in the ledger with its key),
   and the response says it will not be flagged again.
3. Cedar's deal is not changed in the CRM on the strength of that sentence alone. Closing
   it or changing its stage is treated as a separate action that needs the exact change
   previewed and approved before it is made.
4. Pricing sheet: recorded as `snoozed` with an `until` date one week out.
5. Each decision is recorded as a line in the nudges ledger using the item's key
   taken from its file. Nothing is merged into a memory node and no message is sent.
   (Naming the exact command used to append the line is not required.)

Pass if all five hold. Fail if any one is violated.
