# This is the main V1 script: read a JD -> build a prompt with the
# candidate profile -> send to Ollama -> print the verdict.

import sys  # used to stop the script early, before any model call, on a hard Finnish requirement
import requests  # same library used in test_ollama.py to call the local Ollama API
from finnish_detector import detect_finnish_requirement  # deterministic keyword check, see finnish_detector.py for why this exists alongside the model
from history import save_judgment  # persists every screening result to history.json, see history.py
from retriever import retrieve_relevant_chunks  # RAG lookup against the ChromaDB profile index, see retriever.py
from agent import (  # V4 decision layer -- see agent.py for why each function exists
    parse_match_score,
    should_search_company,
    mock_web_search,
    extract_deadline,
    mock_create_calendar_reminder,
    is_recommend_to_apply,
    generate_cl_talking_points,
    mock_save_to_drive,
    guess_job_title_and_company,
)

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

# This is RAG (retrieval-augmented generation): instead of sending the
# model the entire candidate profile every time (V1/V2's approach), we
# first look up which profile chunks are most relevant to this specific
# JD and send only those. This keeps the prompt shorter and more focused
# as the profile grows (e.g. once it has many projects/experiences, most
# of them won't be relevant to any one JD), and is the same lookup
# retriever.py's own test demonstrates.
relevant_chunks = retrieve_relevant_chunks(jd_text)

print("\n--- Retrieved profile chunks ---")
print(relevant_chunks)

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
prompt = f"""You are screening a job description for a candidate. Here are
the most relevant parts of the candidate's background for this specific
role (retrieved from their full profile, not the whole profile):

{relevant_chunks}

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
verdict_text = data["response"]

print("\n--- Verdict ---")
print(verdict_text)

# V4: once a verdict exists, the agent decides which extra tools (if
# any) are worth calling based on what's actually in the verdict and the
# JD -- not every JD triggers every tool. See agent.py for why each
# condition below was chosen. Printed section headers make it visually
# clear in the terminal which steps the agent took vs skipped.
print("\n--- Agent decisions ---")

job_title, company_name = guess_job_title_and_company(jd_text)

score = parse_match_score(verdict_text)
if score is None:
    print("Could not parse a match score from the verdict -- skipping company search.")
elif should_search_company(score):
    print(f"Score {score}/10 is ambiguous -- searching company.")
    mock_web_search(company_name)
else:
    print(f"Score {score}/10 is not ambiguous -- skipping company search.")

deadline = extract_deadline(jd_text)
if deadline:
    print(f"Deadline found: {deadline} -- creating calendar reminder.")
    mock_create_calendar_reminder(deadline, job_title)
else:
    print("No deadline found in JD -- skipping calendar reminder.")

if is_recommend_to_apply(score):
    print("Verdict recommends applying -- generating cover letter talking points.")
    talking_points = generate_cl_talking_points(jd_text, relevant_chunks, verdict_text)
    print(talking_points)
    mock_save_to_drive(jd_text, verdict_text, talking_points, job_title)
else:
    print("Verdict does not recommend applying -- skipping talking points and Drive save.")

save_judgment(jd_text, finnish_check, verdict=verdict_text)
