# This is the main V1 script: read a JD -> build a prompt with the
# candidate profile -> send to Ollama -> print the verdict.

import requests  # same library used in test_ollama.py to call the local Ollama API
from profile import MY_PROFILE  # the candidate background text, kept in its own file

# A single input() call reads only one line, and it stops at the first
# Enter key press. A real job description is many lines/paragraphs, so one
# input() is not enough -- we need to keep reading lines until the user
# signals "I'm done pasting" by entering a blank line.

print("Paste the job description below.")
print("When you're done, press Enter on an empty line to finish:\n")

lines = []  # collects each line of the pasted JD

while True:
    line = input()  # read one line of text from the terminal
    if line == "":
        # an empty line means the user has finished pasting the JD
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
prompt = f"""You are screening a job description for a candidate with the
following background:

{MY_PROFILE}

Here is the job description to evaluate:

{jd_text}

Respond using exactly this format, with no extra text before or after it:

Finnish language required: Yes / No (reason: ...)
Match score: X/10
Matching points: ...
Gaps: ...
Recommendation: ...
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
