# fin-job-helper
Agentic job-search assistant: RAG + hybrid rule/LLM screening + tool calling, built for the Finnish AI/cloud job market.

![fin-job-helper screenshot](docs/screenshot.png)

## Setup
```
pip install -r requirements.txt
ollama pull llama3.2
```

See [FINDINGS.md](FINDINGS.md) for the testing notes and design rationale behind each version, from V1's model-reliability issues through the V2 rule layer, V3's RAG architecture, the V3.5 UI rationale, and V4's conditional agent decision layer.

## How to use

**Web UI (recommended):**
```
streamlit run app.py
```
Open http://localhost:8501, paste a JD, click `[ SCREEN ]`.

**Terminal:**
```
python analyzer.py
```
Paste a job description, type `END` on a new line, and press Enter.

Both interfaces run the same checks: Finnish-language requirement detection first (rule-based, no model call; hard stop if required, notice if mentioned as a nice-to-have), then RAG retrieval of the most relevant profile chunks, a match score and recommendation, and every judgment saved to `history.json` (local only, gitignored).

After the verdict, an agent layer (`agent.py`) decides which extra tools are worth calling based on what's actually in the verdict and the JD: an ambiguous match score (5-7/10) triggers a company web search, an explicit deadline in the JD triggers a calendar reminder, and a strong match (7+/10) generates cover-letter talking points (a structured outline, not full prose) and saves the full analysis. Google Calendar, Google Drive, and the web search are currently mocked — printed, not real API calls yet. See [FINDINGS.md](FINDINGS.md)'s "How V4 works" for details.

**Note:** The candidate profile in `profile.py` and the ChromaDB index in `chroma_db/` are personalised to the author. To use this tool for your own job search, update `profile.py` with your own background and re-run `python build_profile_db.py` to rebuild the index.

## Progress

- [x] Step 0 — confirm Ollama runs locally
- [x] V1 step 1 — `test_ollama.py`: send hardcoded text to Ollama, print reply
- [x] V1 step 2 — `profile.py`: candidate background as a reusable variable
- [x] V1 step 3 — `analyzer.py`: accept a pasted JD via terminal input
- [x] V1 step 4 — build the combined prompt (profile + JD + output format)
- [x] V1 step 5 — tune the prompt until output format is stable
- [x] V1 step 6 — tested against a real job description; confirmed the model is unreliable at detecting explicit Finnish-language requirements, motivating the V2 rule-based layer
- [x] V2 step 1 — `finnish_detector.py`: keyword scan for Finnish requirements, separates hard requirement from nice-to-have
- [x] V2 step 2 — Finnish detector wired into `analyzer.py`; runs before the model, hard stop exits without a model call
- [x] V2 step 3 — `history.py`: saves every judgment to `history.json` (gitignored)
- [x] V3 step 1 — `build_profile_db.py`: chunk profile into ChromaDB vector index
- [x] V3 step 2 — `retriever.py`: semantic chunk retrieval against JD
- [x] V3 step 3 — RAG wired into `analyzer.py`; model now sees only the most relevant profile chunks
- [x] V3 fix — negation handling in `finnish_detector.py` ("No Finnish required" no longer false-positives)
- [x] V3.5 — Streamlit web UI with terminal aesthetic (`app.py`)
- [x] V3.5 fix — UI polish: expander icon font, label clipping, profile-chunk font-size consistency, verdict line wrapping (no horizontal scroll)
- [x] V4 step 1 — `agent.py`: parse the match score out of the model's verdict text
- [x] V4 step 2 — ambiguous-score detection (5-7/10) + mocked company web search
- [x] V4 step 3 — JD deadline extraction + mocked Google Calendar reminder
- [x] V4 step 4 — cover-letter talking points (structured outline, not full prose)
- [x] V4 step 5 — mocked Google Drive save for recommend-to-apply verdicts
- [x] V4 step 6 — agent decisions wired into both `analyzer.py` and `app.py`
- [x] V4 fix — replaced the keyword-based "recommend to apply" check with a `score >= 7` threshold after live testing showed the keyword check never fired on real verdicts
- [x] V4 fix — negation check in `finnish_detector.py` no longer false-triggers on "no" embedded inside unrelated words (e.g. "technologies"), found by running a real JD through the live app
- [ ] V5 — evaluation harness + observability
