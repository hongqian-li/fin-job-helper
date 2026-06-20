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


def should_search_company(score):
    """
    Decide whether a match score is ambiguous enough to be worth looking
    up the company before finalizing a recommendation.

    5-7 is the chosen range because that's the zone where extra company
    info could genuinely tip the recommendation: below 5 the match is
    already weak enough that more research won't change the decision,
    and above 7 the candidate is already a strong fit and doesn't need
    extra confirmation.

    Returns:
        bool
    """
    return score in (5, 6, 7)


def mock_web_search(company_name):
    """
    Stand-in for a real web search call (to be wired up later). Prints
    what it would search for and returns a placeholder string so the
    rest of the decision logic has something to work with in the
    meantime.

    Returns:
        str: a placeholder search result
    """
    print(f"[MOCK] Would search web for: {company_name}")
    return f"[placeholder web search result for {company_name}]"


# Phrase patterns that commonly introduce an application deadline in a JD.
# Each one captures whatever date text immediately follows it -- the date
# itself is matched by DATE_PATTERN below, not hardcoded into each phrase,
# so all four phrasings can share the same date-format coverage.
DEADLINE_PHRASE_PATTERNS = [
    r"apply by\s+({date})",
    r"deadline:?\s*({date})",
    r"no later than\s+({date})",
    r"by the end of\s+({date})",
]

MONTH_NAMES = (
    "January|February|March|April|May|June|July|August|September"
    "|October|November|December"
)

# Three date shapes this is meant to catch, in the order checked below:
# "30th of May" (day-first with "of"), "May 30th, 2026" / "May 30"
# (month-first, day and year both optional), and "31.05.2026"
# (numeric DD.MM.YYYY, common in Finnish JDs). re.IGNORECASE (applied at
# the re.search call below) covers any casing of the month names.
DATE_PATTERN = (
    rf"(?:\d{{1,2}}(?:st|nd|rd|th)?\s+of\s+(?:{MONTH_NAMES}))"
    rf"|(?:(?:{MONTH_NAMES})(?:\s+\d{{1,2}}(?:st|nd|rd|th)?)?(?:,?\s*\d{{4}})?)"
    rf"|(?:\d{{1,2}}\.\d{{1,2}}\.\d{{2,4}})"
)


def extract_deadline(jd_text):
    """
    Scan jd_text for a stated application deadline (e.g. "Apply by May
    30th, 2026", "deadline: 31.05.2026") and return the matched date text.

    Returns:
        str or None: the matched date, or None if no deadline phrase is
        found.
    """
    for phrase_pattern in DEADLINE_PHRASE_PATTERNS:
        pattern = phrase_pattern.format(date=DATE_PATTERN)
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def mock_create_calendar_reminder(deadline_text, job_title):
    """
    Stand-in for a real Google Calendar MCP call (to be wired up later).
    Prints what reminder it would create and returns True so the rest of
    the decision logic has a success signal to work with in the meantime.

    Returns:
        bool
    """
    print(f"[MOCK] Would create calendar reminder: Apply to {job_title} by {deadline_text}")
    return True


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

    # should_search_company: below the range, inside the range, above it
    for score in (3, 6, 9):
        print(f"Score {score} -> should_search_company: {should_search_company(score)}")

    print()
    mock_web_search("Acme Oy")

    # extract_deadline: two different phrase/date-format combinations,
    # plus a JD with no deadline mentioned at all (the case that motivates
    # returning None instead of raising an error).
    print()
    deadline_samples = [
        "We are hiring a Cloud Engineer. Apply by May 30th, 2026 to be considered.",
        "Open position, deadline: 31.05.2026. Send your CV.",
        "This role is fully remote and open until filled.",
    ]

    for jd in deadline_samples:
        print(f"JD snippet: {jd}")
        print(f"Extracted deadline: {extract_deadline(jd)}\n")

    mock_create_calendar_reminder("May 30th, 2026", "Cloud Engineer")
