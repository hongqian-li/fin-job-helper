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

**Bug: the negation check itself had a false-negative bug (found while testing V4, fixed in V4)**
A real-world JD ("...curiosity for learning new technologies. Native Finnish speaker with professional proficiency in English...") was wrongly screened as not requiring Finnish. Cause: the negation check matched `"no"` as a plain substring of the 10 characters preceding "Native Finnish" — and "tech**no**logies" contains that substring, with nothing to do with negation. Fixed by switching the negation check from `word in text` to a word-boundary regex (`\bno\b`, `\bnot\b`, etc.), so it only matches whole negation words. This is a different failure mode than the "Finnish buried in a sentence" gap below — that one is a coverage gap (a real requirement phrasing missing from the pattern list); this was an outright bug in working code, caught by running a real JD through the live app rather than a synthetic test string.

**Known gap: Finnish buried in a sentence**
"Good communication skills in English and Finnish" requires Finnish but doesn't trigger any pattern in `FINNISH_REQUIREMENT_PATTERNS`. Real example: Insta Digital Cloud Architect role. Adding more keywords risks over-matching, so this is left for the V5 eval harness where the tradeoff can be measured properly.

**Hard stops go into history too**
A skipped role is still a decision. Logging "skipped - Finnish required" keeps the history complete — filtering it out would make the record misleading.

## How V3 works

`profile.py` is split into chunks (one per paragraph) and stored in a local ChromaDB vector index via `build_profile_db.py`. This only needs to run once. When a JD is screened, `retriever.py` converts the JD text into a vector and finds the 2 most semantically similar profile chunks — not by keyword, but by meaning. Only those chunks go into the prompt, not the full profile. As the profile grows, irrelevant sections stay out of the model's context automatically.

## Why V3.5

The `END` marker was awkward and there was no visual separation between the Finnish check, the retrieved chunks, and the verdict. Streamlit fixed both without touching the core logic — same building blocks, browser instead of terminal.

Kept the terminal aesthetic on purpose. This tool has one user. It doesn't need to look friendly.

## How V4 works

After a verdict comes back, `agent.py` decides which extra tools (if any) are worth calling, based on what's actually in the verdict and the JD — not every JD triggers every tool. Three independent conditions, each checked separately: an ambiguous match score (5-7/10) triggers a company web search; an explicit application deadline found in the JD triggers a calendar reminder; a strong match (score >= 7) generates cover-letter talking points (a structured outline of what the JD emphasizes and which background facts serve as evidence — not full prose, since the candidate should always write and personalize the actual letter) and saves the full analysis. Wired into both `analyzer.py` (printed section headers) and `app.py` (notice boxes in the same dark/monospace aesthetic as the rest of the UI). Google Calendar, Google Drive, and the web search are all currently mocked (`print(f"[MOCK] ...")`) rather than real API calls — only the conditional decision logic is real so far.

## V4 findings

**Known gap: cover letter talking points format is unstable across runs**
The same prompt (`generate_cl_talking_points`), run 5 times against the identical Insta Digital JD/chunks/verdict, produced 5 different outputs. 2 of 5 runs added an unwanted preamble line ("Here are the extracted talking points...") despite the prompt explicitly saying not to add any introduction. The section title also drifted wording across runs ("this JD" / "the JD" / dropped the word entirely), and one run broke the numbered-list structure with an extra unnumbered sentence. Left as-is for now — talking points are a starting point the candidate reviews and personalizes anyway, not an authoritative verdict, so format noise matters less here than for the Finnish-requirement hard stop. Candidate for the V5 eval harness if it turns out to matter in practice.

**Design correction: replaced the `is_recommend_to_apply` keyword check with a score threshold**
The first version of `is_recommend_to_apply` looked for `apply` / `recommend` / `worth applying` on the verdict's Recommendation line. A TestCorp Cloud Architect JD scored an 8/10 match (clearly strong) but phrased the recommendation as "Consider the candidate for an interview based on their strong technical skills..." — none of the three keywords appeared, so the agent skipped cover-letter talking points and the Drive save for a role that should have triggered both. Initially logged as a one-off paraphrasing gap, the same prompt was then run against 10 more real JDs (scores ranging 6-9/10) to check how common this was: **zero** of those 10 verdicts phrased the Recommendation line using any of the three keywords — llama3.2 consistently hedges ("consider for interview", "experience may be lacking", "would be beneficial to assess") regardless of score. That's strong enough evidence that the model's wording, not the specific keyword list, was the real problem — no keyword list would have been reliable here, so this wasn't treated as a "leave it for V5" known gap like the Finnish-phrasing one above. Fix: `is_recommend_to_apply` now takes the already-parsed numeric score (from `parse_match_score`) and returns `score >= 7`, a deterministic check with no dependence on the model's phrasing at all.
