# This check lives in its own file/function instead of inside analyzer.py
# for two reasons:
#
# 1. V1 testing (see FINDINGS.md) showed llama3.2 is unreliable at judging
#    whether a JD requires Finnish -- it sometimes contradicts itself or
#    misses an explicit mention. A keyword check is deterministic: the same
#    input always gives the same output, so it can act as a backstop that
#    catches what the model misses (or overrides the model if they
#    disagree).
# 2. Keeping it as a standalone function means any future caller (V3's RAG
#    version, a V4 agent tool, a test script) can import and reuse this one
#    function without re-implementing the rule check every time the model
#    layer changes.

import re

# Keyword patterns that strongly indicate a JD requires Finnish. English
# phrasing covers JDs written in English that still state the requirement
# explicitly; the Finnish and Swedish phrasing covers JDs that switch into
# the local language specifically to state language requirements (common
# in Finland, which has Swedish as a second official language).
FINNISH_REQUIREMENT_PATTERNS = [
    "native Finnish",
    "Finnish required",
    "Finnish language required",
    "fluent Finnish",
    "sujuva suomi",
    "suomen kielen taito",
    "äidinkieli suomi",
    "finska krävs",
]

# Some JDs mention Finnish but only as a "nice to have", not a requirement
# (e.g. "Finnish is an advantage"). Treating these the same as a hard
# requirement would wrongly screen out roles the candidate could actually
# take. This list is checked separately so that case is reported on its
# own instead of being silently lumped in with "not mentioned at all".
FINNISH_ADVANTAGE_PATTERNS = [
    "Finnish is an advantage",
    "Finnish is a plus",
    "Finnish is a bonus",
    "Finnish is beneficial",
    "Finnish is considered an asset",
    "suomen kieli on eduksi",
    "suomen kielen taito katsotaan eduksi",
]


def _find_first_match(jd_text, patterns):
    for pattern in patterns:
        # re.escape treats the pattern as a literal string rather than a
        # regex, since we want a plain case-insensitive substring match,
        # not regex syntax (in case a future pattern contains characters
        # like "." or "+").
        match = re.search(re.escape(pattern), jd_text, re.IGNORECASE)
        if match:
            # match.group(0) returns the actual substring as it appears in
            # jd_text (original casing), not the canonical pattern from our
            # list -- this preserves the real quote from the JD for the
            # history log we'll add in the next V2 step.
            return match.group(0)
    return None


def detect_finnish_requirement(jd_text):
    """
    Scan jd_text for known Finnish-language phrases, distinguishing a hard
    requirement from a "nice to have" mention.

    Returns:
        dict: {
            "required": bool,
            "matched_phrase": str or None,
            "mentioned_as_advantage": bool,
            "advantage_phrase": str or None,
        }
    """
    required_match = _find_first_match(jd_text, FINNISH_REQUIREMENT_PATTERNS)
    if required_match:
        # A hard requirement takes priority: if a JD somehow states both
        # "Finnish required" and "Finnish is a plus" elsewhere, the
        # stricter statement is the one that should drive the screening.
        return {
            "required": True,
            "matched_phrase": required_match,
            "mentioned_as_advantage": False,
            "advantage_phrase": None,
        }

    advantage_match = _find_first_match(jd_text, FINNISH_ADVANTAGE_PATTERNS)
    if advantage_match:
        return {
            "required": False,
            "matched_phrase": None,
            "mentioned_as_advantage": True,
            "advantage_phrase": advantage_match,
        }

    return {
        "required": False,
        "matched_phrase": None,
        "mentioned_as_advantage": False,
        "advantage_phrase": None,
    }


if __name__ == "__main__":
    # Quick manual test: a clear English match, a Finnish match in a
    # different case, a "nice to have" mention, and a JD with no Finnish
    # mention at all.
    samples = [
        "We require native Finnish speakers for this customer-facing role.",
        "Hakijalta edellytetään SUOMEN KIELEN TAITOA ja hyvää englannin taitoa.",
        "Finnish is an advantage but not a requirement for this role.",
        "This role is fully remote and English is the working language.",
    ]

    for sample in samples:
        result = detect_finnish_requirement(sample)
        print(f"JD snippet: {sample}")
        print(f"Result: {result}\n")
