# This is a one-time setup script: it builds a local vector database from
# the candidate profile. Run it once; later scripts (the V3 retrieval
# step) will only read from the database this script creates, not rebuild
# it every time.
#
# What a vector database is, and why we need one here:
# A normal database finds rows by an exact match (e.g. WHERE id = 5). A
# vector database instead finds text by *meaning*: it converts each piece
# of text into a list of numbers (an "embedding") that captures its
# semantic content, then finds other pieces of text whose numbers are
# close together. This lets V3 ask "which parts of the profile are most
# relevant to this specific JD?" instead of always stuffing the entire
# profile into every prompt, the way V1/V2's analyzer.py does today.
#
# Why we chunk the profile instead of embedding it as one block:
# Embedding the whole profile as a single vector would only let us
# retrieve "the whole profile" or nothing -- there's no way to pull out
# just the skills section for a JD that only cares about tech stack.
# Splitting into smaller, topic-coherent chunks (one per paragraph) means
# each chunk gets its own embedding, so retrieval can return only the
# chunks that are actually relevant to a given JD.

import chromadb
from profile import MY_PROFILE

# MY_PROFILE is written as separate paragraphs (intro, skills, experience,
# constraints) with a blank line between each. Splitting on that blank
# line ("\n\n") gives us one chunk per paragraph for free, without having
# to manually mark section boundaries. strip() removes the leading/
# trailing newlines that the triple-quoted string in profile.py has, and
# the "if chunk.strip()" filter drops any empty pieces that splitting
# could produce.
chunks = [chunk.strip() for chunk in MY_PROFILE.split("\n\n") if chunk.strip()]

# PersistentClient writes the database to disk at this path (created
# automatically if it doesn't exist yet), so the embeddings survive
# between runs -- an EphemeralClient would lose everything when the
# script exits, which defeats the point of building this once.
client = chromadb.PersistentClient(path="./chroma_db")

# get_or_create_collection means this script is safe to run again without
# wiping an existing database, but note that add() below will still fail
# on a second run because chunk_0, chunk_1, etc. would already exist --
# that's expected for a script that's meant to build the database once.
collection = client.get_or_create_collection(name="candidate_profile")

collection.add(
    documents=chunks,
    ids=[f"chunk_{i}" for i in range(len(chunks))],
)

print(f"Added {len(chunks)} chunks to the 'candidate_profile' collection.\n")
for i, chunk in enumerate(chunks):
    print(f"chunk_{i}: {chunk[:80]}...")
