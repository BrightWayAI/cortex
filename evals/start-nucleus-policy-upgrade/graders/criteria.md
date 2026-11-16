---
type: llm
weight: 1
---

Judge only these four points. Do not fail the response for leaving out other details.

1. It recognizes the 1.0.0 shape and explains the change: the middle bucket becomes two
   tiers, everything that needed approval before is high risk and still needs approval
   each time, and a new medium tier allows a single batch review of verified, undoable
   memory updates.
2. Its choices include both adopting the 2.0.0 policy and keeping the 1.0.0 policy
   (offering a further option such as deciding later is fine).
3. For adopt: it asks which tier the custom "#clients Slack channel" line belongs in
   (defaulting to high risk when unsure), shows the replacement, and writes only after
   confirmation, through `cortex_cli.py replace-section` rather than a hand edit.
4. For keep: it changes nothing in the policy, records the choice (`1.0.0-kept`), and
   says there is then no medium tier: `Ask first` items, and anything that would be
   medium, are handled as high risk.

Pass if all four hold. Fail if any one is violated, or if it writes the policy without
the user's confirmation.
