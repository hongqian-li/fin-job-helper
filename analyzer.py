# This file will grow into the main V1 script: read a JD -> build a prompt
# with the candidate profile -> send to Ollama -> print the verdict.
# Step 3 only covers the first part: getting the JD text from the user.

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

# for now we just print it back, to confirm the input was captured correctly
print("\n--- JD received ---")
print(jd_text)
