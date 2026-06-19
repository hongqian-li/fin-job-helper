# This is the main V1 script: read a JD -> build a prompt with the
# candidate profile -> send to Ollama -> print the verdict.

import sys  # used to stop the script early, before any model call, on a hard Finnish requirement
import requests  # same library used in test_ollama.py to call the local Ollama API
from profile import MY_PROFILE  # the candidate background text, kept in its own file
from finnish_detector import detect_finnish_requirement  # deterministic keyword check, see finnish_detector.py for why this exists alongside the model
from history import save_judgment  # persists every screening result to history.json, see history.py

# A single input() call reads only one line, and it stops at the first
# Enter key press. A real job description is many lines/paragraphs, so one
# input() is not enough -- we need to keep reading lines until the user
# signals "I'm done pasting".
#
# Real JDs almost always have blank lines between paragraphs (section
# breaks, bullet groups, etc.), so using "an empty line" as the stop
# signal would cut the JD off after the first paragraph. Instead we use a
# distinct marker line ("END") that won't appear by accident in real text.

print("Paste the job description below.")
print("When you're done, type END on its own line and press Enter:\n")

lines = []  # collects each line of the pasted JD

while True:
    line = input()  # read one line of text from the terminal
    if line.strip() == "END":
        # the END marker means the user has finished pasting the JD
        break
    lines.append(line)

# join the collected lines back into one multi-line string,
# the same way it looked when it was pasted in
jd_text = "\n".join(lines)

# Run the deterministic keyword check before ever calling the model. V1
# testing (FINDINGS.md) showed llama3.2 is unreliable at this specific
# judgment, so the rule layer now owns the Finnish-language decision
# instead of the model. Three possible outcomes:
#   1. required=True   -> hard stop, no point spending a model call
#      scoring a role the candidate can't actually take.
#   2. mentioned_as_advantage=True -> just a notice; Finnish is optional
#      here, so the model evaluation still proceeds normally.
#   3. neither -> nothing to report, proceed normally.
finnish_check = detect_finnish_requirement(jd_text)

if finnish_check["required"]:
    print("\n--- Hard stop: Finnish required ---")
    print(f'Matched phrase: "{finnish_check["matched_phrase"]}"')
    print("Skipping model call -- this role requires Finnish.")
    # Logged even though the model was never called -- a hard stop is
    # still a real judgment ("skip this role"), so it belongs in the same
    # history as model-scored verdicts, not silently dropped.
    save_judgment(jd_text, finnish_check, verdict="skipped - Finnish required")
    sys.exit()

if finnish_check["mentioned_as_advantage"]:
    print("\n--- Notice ---")
    print(f'Finnish is mentioned as a nice-to-have: "{finnish_check["advantage_phrase"]}"')
    print("Continuing to model evaluation.\n")

# The prompt has three parts, in this order, because that's the order the
# model needs the information in: first WHO the candidate is (context),
# then WHAT to evaluate (the JD), then exactly HOW to answer (the output
# format). Without the format spec, the model would reply in free-form
# prose that's hard to read consistently across different JDs.
#
# The format block below is written as a literal template with placeholder
# instructions ("replace ... with") because earlier testing showed the
# model would otherwise echo the placeholders themselves instead of filling
# them in. Telling it explicitly to replace each placeholder, and to skip
# any preamble, removes the ambiguity that caused that. The Finnish-
# language line that used to live here has been removed -- that judgment
# is now made by the rule layer above, before the model is ever called.
prompt = f"""You are screening a job description for a candidate with the
following background:

{MY_PROFILE}

Here is the job description to evaluate:

{jd_text}

Your entire response must follow this exact format, do not add any
introduction or explanation:

Match score: [replace X with a number] /10
Matching points: [replace ... with the actual matching points]
Gaps: [replace ... with the actual gaps]
Recommendation: [replace ... with the actual recommendation]
"""

OLLAMA_URL = "http://localhost:11434/api/generate"  # same endpoint as test_ollama.py
MODEL_NAME = "llama3.2"

payload = {
    "model": MODEL_NAME,
    "prompt": prompt,
    "stream": False,  # get one full response instead of streamed chunks
}

response = requests.post(OLLAMA_URL, json=payload)
data = response.json()

print("\n--- Verdict ---")
print(data["response"])

save_judgment(jd_text, finnish_check, verdict=data["response"])
