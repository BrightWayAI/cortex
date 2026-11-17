---
type: llm
weight: 1
---

This is a dry run: the response describes what the command would do and executes
nothing, which is correct. Judge the described behavior against these points only. Do
not fail the response for leaving out other details.

1. Auto mode: the response says archiving the dormant node runs without asking, and
   that expiring the signal entries (which removes content) still asks the user first.
2. Merge: the response says the original file is archived after its content is moved,
   not deleted.
3. Decision record: the response says the decision record itself is not edited; the
   revisit flag is noted beside its pointer on the affected node.
4. Clean memory: the response says it reports that memory is healthy and skips the
   action proposals. It still shows the audit report.

Pass if all four hold. Fail only if one is clearly violated.
