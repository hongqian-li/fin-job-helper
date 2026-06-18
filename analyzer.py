# This is the main V1 script: read a JD -> build a prompt with the
# candidate profile -> send to Ollama -> print the verdict.

import requests  # same library used in test_ollama.py to call the local Ollama API
from profile import MY_PROFILE  # the candidate background text, kept in its own file

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

# The prompt has three parts, in this order, because that's the order the
# model needs the information in: first WHO the candidate is (context),
# then WHAT to evaluate (the JD), then exactly HOW to answer (the output
# format). Without the format spec, the model would reply in free-form
# prose that's hard to read consistently across different JDs.
#
# The format block below is written as a literal template with placeholder
# instructions ("replace ... with", "replace Yes / No with exactly one
# word") because earlier testing showed the model would otherwise echo the
# placeholders themselves (e.g. print "Yes / No" instead of picking one).
# Telling it explicitly to replace each placeholder, and to skip any
# preamble, removes the ambiguity that caused that.
prompt = f"""You are screening a job description for a candidate with the
following background:

{MY_PROFILE}

Here is the job description to evaluate:

{jd_text}

Your entire response must follow this exact format, do not add any
introduction or explanation:

Finnish language required (does the JD itself explicitly ask for Finnish, ignore the candidate's own language skills): [Yes or No] (reason: [quote the exact phrase from the JD that mentions Finnish, or say "not mentioned"])
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
