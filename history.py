# Why this is a separate function instead of writing JSON directly inline
# in analyzer.py: every future caller (a V3 RAG version, a V4 agent loop, a
# future "list past judgments" command) needs to log results the same way,
# so the file format and the read-modify-write logic should only be
# defined once, in one place.

import json
import os
from datetime import datetime

HISTORY_FILE = "history.json"


def save_judgment(jd_text, finnish_check, verdict):
    """
    Append one screening result to HISTORY_FILE.

    jd_text: the full pasted job description (only a snippet is stored)
    finnish_check: the dict returned by detect_finnish_requirement()
    verdict: the model's full output string, or a marker string like
        "skipped - Finnish required" if the model was never called
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        # Only the first 200 characters are kept, not the full JD -- JDs
        # can be hundreds of lines long, and storing all of them would
        # make history.json slow to skim. A snippet is enough to recognize
        # which JD an entry refers to later.
        "jd_snippet": jd_text[:200],
        "finnish_required": finnish_check["required"],
        "finnish_matched_phrase": finnish_check["matched_phrase"],
        "finnish_advantage": finnish_check["mentioned_as_advantage"],
        "verdict": verdict,
    }

    # A JSON file can't be appended to in place the way a plain text log
    # can -- the whole file is one JSON array, so we read the existing
    # array, add the new entry in memory, and write the whole array back
    # out. os.path.exists covers the first-ever run, when there's no file
    # yet to read.
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    history.append(entry)

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        # indent=2 keeps the file readable for a quick manual look.
        # ensure_ascii=False keeps Finnish/Swedish characters (e.g. "ä")
        # as real characters instead of escaped \uXXXX sequences.
        json.dump(history, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Quick manual test: save one fake entry, then print the file back out
    # so we can see exactly what got written.
    fake_finnish_check = {
        "required": False,
        "matched_phrase": None,
        "mentioned_as_advantage": True,
        "advantage_phrase": "Finnish is an advantage",
    }
    save_judgment(
        jd_text="This is a fake job description used only to test save_judgment().",
        finnish_check=fake_finnish_check,
        verdict="Match score: 8/10\nMatching points: ...\nGaps: ...\nRecommendation: Apply",
    )

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        print(f.read())
