# fin-job-helper
Agentic job-search assistant: RAG + hybrid rule/LLM screening + tool calling, built for the Finnish AI/cloud job market.

## Setup
```
pip install -r requirements.txt
ollama pull llama3.2
```

See [FINDINGS.md](FINDINGS.md) for what V1 testing surfaced and why V2 is designed the way it is.

## How to use

Run `python analyzer.py`, paste a job description, type `END` on a new line, and press Enter.
The tool will:

- Check for Finnish language requirements first (rule-based, no model call)
- Hard stop if Finnish is required, with the matched phrase shown
- Flag Finnish as nice-to-have if mentioned as an advantage
- Retrieve the most relevant chunks of your profile (`profile.py`, indexed via `build_profile_db.py`) for this specific JD, then run a match score and recommendation against those chunks
- Save every judgment to `history.json` (local only, gitignored)

## Progress

- [x] Step 0 — confirm Ollama runs locally
- [x] V1 step 1 — `test_ollama.py`: send hardcoded text to Ollama, print reply
- [x] V1 step 2 — `profile.py`: candidate background as a reusable variable
- [x] V1 step 3 — `analyzer.py`: accept a pasted JD via terminal input
- [x] V1 step 4 — build the combined prompt (profile + JD + output format)
- [x] V1 step 5 — tune the prompt until output format is stable
- [x] V1 step 6 — tested against a real job description (M-Files AI Systems Specialist); confirmed the model is unreliable at detecting explicit Finnish-language requirements, motivating the V2 rule-based layer
- [x] V2 step 1 — `finnish_detector.py`: keyword scan for Finnish requirements, separates hard requirement from nice-to-have
- [x] V2 step 2 — Finnish detector wired into `analyzer.py`; runs before the model, hard stop exits without a model call
- [x] V2 step 3 — `history.py`: saves every judgment to `history.json` (gitignored)
- [x] V3 step 1 — `build_profile_db.py`: chunk profile into ChromaDB vector index
- [x] V3 step 2 — `retriever.py`: semantic chunk retrieval against JD
- [x] V3 step 3 — RAG wired into `analyzer.py`; model now sees only the most relevant profile chunks
- [x] V3 fix — negation handling in `finnish_detector.py` ("No Finnish required" no longer false-positives)
- [x] V3.5 — Streamlit web UI with terminal aesthetic (`app.py`)
- [x] V3.5 fix — UI polish: expander icon font, label clipping, profile-chunk font-size consistency, verdict line wrapping (no horizontal scroll)
- [ ] V4 — agent + tool calling (fetch JD by URL, draft cover letter)
- [ ] V5 — evaluation harness + observability
