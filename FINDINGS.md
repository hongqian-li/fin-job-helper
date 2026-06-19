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

## V2 findings

**Negation is a real edge case**
"No Finnish required" triggered a false positive — "Finnish required" matched as a substring inside the negated phrase. Fixed with a negation check on the 10 characters before each match. Switched from `re.search` to `re.finditer` so a negated first occurrence doesn't block a real match later in the same JD.

**Known gap: Finnish buried in a sentence**
"Good communication skills in English and Finnish" requires Finnish but doesn't trigger any pattern in `FINNISH_REQUIREMENT_PATTERNS`. Real example: Insta Digital Cloud Architect role. Adding more keywords risks over-matching, so this is left for the V5 eval harness where the tradeoff can be measured properly.

**Hard stops go into history too**
A skipped role is still a decision. Logging "skipped - Finnish required" keeps the history complete — filtering it out would make the record misleading.

## How V3 works

`profile.py` is split into chunks (one per paragraph) and stored in a local ChromaDB vector index via `build_profile_db.py`. This only needs to run once. When a JD is screened, `retriever.py` converts the JD text into a vector and finds the 2 most semantically similar profile chunks — not by keyword, but by meaning. Only those chunks go into the prompt, not the full profile. As the profile grows, irrelevant sections stay out of the model's context automatically.

## Why V3.5

The `END` marker was awkward and there was no visual separation between the Finnish check, the retrieved chunks, and the verdict. Streamlit fixed both without touching the core logic — same building blocks, browser instead of terminal.

Kept the terminal aesthetic on purpose. This tool has one user. It doesn't need to look friendly.
