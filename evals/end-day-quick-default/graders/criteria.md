---
type: llm
weight: 1
---

This is a dry run: the response describes what the command would do and executes nothing, which is correct. Judge the described behavior against these points only. Do not fail the response for leaving out other details.

1. The response says the quick close runs by default, and that with few transcripts and a light inbox it does not ask whether the user wants the full close.
2. The response says sources are never gated one prompt at a time: when there is more than the brief to review they are shown together on one card, and the brief is always included rather than being an optional checkbox. Saying the card is skipped here because the brief is the only source left is correct.
3. The response says mined proposals are never committed to memory automatically; the user reviews them first.
4. The response says the HubSpot logging prompt is skipped entirely because HubSpot is not connected.

Pass if all hold. Fail only if one is clearly violated.
