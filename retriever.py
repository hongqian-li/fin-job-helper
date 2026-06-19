# This script reads from the vector database that build_profile_db.py
# already created -- it does not build or modify that database, so it
# can be imported and called any number of times without re-running the
# one-time setup step.

import chromadb

# Connecting to the same path used in build_profile_db.py opens that
# existing database rather than creating a new one.
client = chromadb.PersistentClient(path="./chroma_db")

# get_collection (not get_or_create_collection) is intentional here: if
# candidate_profile doesn't exist yet, this should fail loudly and tell us
# to run build_profile_db.py first, rather than silently opening an empty
# collection that would return nothing useful.
collection = client.get_collection(name="candidate_profile")


def retrieve_relevant_chunks(jd_text, n_results=2):
    """
    Find the profile chunks most relevant to jd_text.

    "Querying by meaning" here means: ChromaDB runs jd_text through the
    same embedding model that was used on the profile chunks when they
    were added, turning it into a vector of numbers that represents its
    meaning. It then compares that vector against every stored chunk
    vector and measures how close they are (smaller distance = more
    similar meaning), then returns the n_results closest chunks. This is
    why a JD about "cloud infrastructure automation" can match the
    profile's "Azure, Terraform, Docker" skills chunk even though none of
    those exact words appear in the JD -- the match is on meaning, not on
    shared keywords (unlike finnish_detector.py's literal keyword search).

    Returns:
        str: the matched chunks joined with "\n\n"
    """
    results = collection.query(query_texts=[jd_text], n_results=n_results)

    # query_texts is a list (you could ask multiple questions in one
    # call), so results["documents"] is a list of lists -- one inner list
    # per query. We only passed one query, so we take the first (and only)
    # inner list.
    matched_chunks = results["documents"][0]

    return "\n\n".join(matched_chunks)


if __name__ == "__main__":
    sample_jd = (
        "We need a Cloud Engineer with strong experience in Azure, "
        "Terraform, and container orchestration to help scale our "
        "infrastructure automation."
    )

    print(retrieve_relevant_chunks(sample_jd))
