# V4 decision layer: after analyzer.py/app.py get a verdict string back
# from the model, this module decides which extra tools (if any) the agent
# should call based on what's in that verdict and the original JD. Step 1
# here is just pulling the match score out of the verdict text -- every
# later decision (e.g. "is the score ambiguous enough to search the
# company") needs that number first, and the model's output is free text,
# not structured data, so it has to be parsed the same way
# finnish_detector.py parses the JD: a deterministic regex, not another
# model call.

import re


def parse_match_score(verdict_text):
    """
    Extract the numeric match score from a verdict string like
    "Match score: 7/10".

    Returns:
        int or None: the score, or None if no "Match score: X/10" line is
        found (e.g. the model didn't follow the expected output format).
    """
    match = re.search(r"Match score:\s*(\d+)\s*/\s*10", verdict_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


if __name__ == "__main__":
    # Quick manual test: a normal verdict, one with extra spacing around
    # the slash, and one missing the score line entirely (the edge case
    # that motivates returning None instead of raising an error).
    samples = [
        "Match score: 7/10\nMatching points: ...\nGaps: ...\nRecommendation: Apply",
        "Match score: 3 / 10\nGaps: many",
        "No score line here at all",
    ]

    for sample in samples:
        print(f"Verdict snippet: {sample[:40]}...")
        print(f"Parsed score: {parse_match_score(sample)}\n")
