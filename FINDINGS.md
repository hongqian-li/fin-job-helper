# fin-job-helper V1 — findings

## Fixed

**Empty line truncates multi-paragraph JD**
Original stop signal was a blank line. Real JDs have paragraph breaks, so the script cut off after the first section. Fixed by switching to `END` as the explicit terminator — discovered during step 6 real JD test.

## Model limits

**Finnish language detection unreliable**
Even "Native Finnish speaker" (the clearest possible phrasing) was judged as `No`. The model also confused "does the JD require Finnish" with "does the candidate speak Finnish" — a logic error, not a format error. Prompt tuning improved the label but not the underlying judgment.

**Self-contradiction in same response**
Line 1 said "Finnish required: No". The Recommendation section in the same output said "candidate does not meet the language requirement." The model held two contradictory positions simultaneously — no amount of prompt engineering fixes this reliably.

**Hallucination on first test**
Asked for a fun fact about Finland, the model invented a "Finnish philosopher Vilhelm Mannheim" who coined the word hygge in 1911. Hygge is a Danish/Norwegian word; the person never existed. Classic confident confabulation.

## Minor

**Output format instability**
Early prompt caused the model to echo placeholder text (`Yes / No` literally) instead of picking one. Fixed by rewriting the format block with explicit replacement instructions. Format is now stable across tests.

## What this means for V2

**Design decision: rule-based Finnish detection layer**
Keyword scan runs first: `Finnish required`, `Native Finnish`, `sujuva suomi`, `äidinkieli`, etc. If any match → hard Yes, no model call needed. Model is used only as fallback for ambiguous cases. This is the same hybrid architecture as the thesis GDPR classifier.

**Key takeaway:**
> In the first real-world test, the model marked "Native Finnish speaker required" as not requiring Finnish — then contradicted itself two sentences later. That single test made the design rationale for the rule layer concrete. It's the same reason the thesis used deterministic keyword detection as the first gate before any LLM call: auditability and reliability on the cases that matter most.
