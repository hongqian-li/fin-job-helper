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
import requests  # same library analyzer.py/app.py use to call the local Ollama API
from retriever import retrieve_relevant_chunks  # used only in the __main__ test below

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"


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


def generate_cl_talking_points(jd_text, relevant_chunks, verdict_text):
    """
    Ask the model for structured cover-letter talking points -- not full
    prose. The candidate should always write and personalize the actual
    letter themselves; this only automates the tedious, mechanical part
    (re-reading the JD for what it emphasizes most, then cross-checking
    which background facts actually serve as evidence for that). Having
    the model write finished paragraphs instead would mean it's doing the
    candidate's own voice and judgment for them -- the line V4 is
    deliberately drawn against.

    Returns:
        str: the model's structured talking-points output
    """
    prompt = f"""Here is a job description:

{jd_text}

Here is the candidate's relevant background:

{relevant_chunks}

Here is the match verdict already produced for this JD:

{verdict_text}

Extract cover-letter talking points in exactly this format, do not add
any introduction, explanation, or full prose paragraphs:

Top 3 things this JD emphasizes most:
1. ...
2. ...
3. ...

Matching evidence from candidate's background:
1. [matches point 1] ...
2. [matches point 2] ...
3. [matches point 3] ...
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }

    response = requests.post(OLLAMA_URL, json=payload)
    data = response.json()
    return data["response"]


def mock_save_to_drive(jd_text, verdict_text, talking_points, job_title):
    """
    Stand-in for a real Google Drive MCP call (to be wired up later).
    Prints what document it would save and returns True so the rest of
    the decision logic has a success signal to work with in the
    meantime. This function only handles "saving" -- deciding whether a
    verdict actually qualifies as "recommend to apply" (and therefore
    whether this should be called at all) belongs to the caller, wired
    up in V4 step 6, not here.

    Returns:
        bool
    """
    print(f"[MOCK] Would save to Google Drive: {job_title}_analysis.md (JD + verdict + talking points)")
    return True


def guess_job_title_and_company(jd_text):
    """
    Best-effort guess at the job title and company name, used only to
    make printed agent-decision messages readable (e.g. "Apply to
    {job_title} by {deadline}"). This is a heuristic, not a reliable
    extractor -- many JDs don't state the company name in a consistent
    format, so callers should treat the fallback placeholders as a
    normal, expected outcome, not an error.

    Looks for a "<Job Title> - <Company>" first line, the format used by
    the Insta Digital JD already used elsewhere in this file's tests.

    Returns:
        tuple: (job_title: str, company_name: str)
    """
    first_line = jd_text.strip().split("\n")[0]

    if " - " in first_line:
        job_title, company_name = first_line.split(" - ", 1)
        return job_title.strip(), company_name.strip()

    return "this role", "company name not detected"


def is_recommend_to_apply(verdict_text):
    """
    Decide whether a verdict's Recommendation line counts as "recommend
    to apply" -- a keyword check on the Recommendation line specifically
    (not the whole verdict), so a Gaps section that happens to mention
    "apply" doesn't cause a false positive.

    Returns:
        bool
    """
    recommendation_match = re.search(r"Recommendation:\s*(.+)", verdict_text, re.IGNORECASE)
    if not recommendation_match:
        return False

    recommendation_line = recommendation_match.group(1).lower()
    apply_keywords = ["apply", "recommend", "worth applying"]
    return any(keyword in recommendation_line for keyword in apply_keywords)


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

    # generate_cl_talking_points: reuses the Insta Digital Cloud Architect
    # JD from FINDINGS.md's "Finnish buried in a sentence" known gap.
    # relevant_chunks comes from the real ChromaDB lookup (retriever.py),
    # same as analyzer.py would use; verdict_text is a representative
    # verdict in the same format the model produces in V1/V2/V3.
    print()
    insta_digital_jd = (
        "Cloud Architect - Insta Digital\n\n"
        "We are looking for a Cloud Architect to design and operate our "
        "Azure-based infrastructure, including Terraform-driven network "
        "architecture and CI/CD pipelines. Strong hands-on experience with "
        "Azure, Terraform, and container orchestration is required. Good "
        "communication skills in English and Finnish are expected, as you "
        "will work closely with local teams."
    )
    insta_digital_chunks = retrieve_relevant_chunks(insta_digital_jd)
    insta_digital_verdict = (
        "Match score: 7/10\n"
        "Matching points: Strong Azure/Terraform experience, hands-on "
        "container orchestration knowledge.\n"
        "Gaps: Finnish communication expectation, limited multi-year "
        "industry experience.\n"
        "Recommendation: Worth applying given the strong technical match."
    )

    insta_digital_talking_points = generate_cl_talking_points(
        insta_digital_jd, insta_digital_chunks, insta_digital_verdict
    )
    print(insta_digital_talking_points)

    # mock_save_to_drive: reuses the same Insta Digital JD/verdict/talking
    # points from the test above -- this function only saves, it doesn't
    # re-decide whether the verdict qualifies as "recommend to apply".
    print()
    mock_save_to_drive(
        insta_digital_jd,
        insta_digital_verdict,
        insta_digital_talking_points,
        "Insta_Digital_Cloud_Architect",
    )

    # guess_job_title_and_company: the Insta Digital JD has the
    # "<Title> - <Company>" shape, a plain JD with no such first line
    # doesn't -- it should fall back to placeholders, not crash.
    print()
    print(guess_job_title_and_company(insta_digital_jd))
    print(guess_job_title_and_company("We are hiring for a great team."))

    # is_recommend_to_apply: a clearly positive Recommendation line, a
    # clearly negative one, and a Gaps section that mentions "apply" but
    # whose Recommendation line does not -- this should NOT count as a
    # false positive.
    print()
    print(is_recommend_to_apply("Recommendation: Worth applying given the strong match."))
    print(is_recommend_to_apply("Recommendation: Skip this role, the gaps are too large."))
    print(is_recommend_to_apply("Gaps: candidate should apply to more senior roles.\nRecommendation: Skip."))
