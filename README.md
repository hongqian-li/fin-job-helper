# fin-job-helper
Agentic job-search assistant: RAG + hybrid rule/LLM screening + tool calling, built for the Finnish AI/cloud job market.

## Setup
```
pip install -r requirements.txt
ollama pull llama3.2
```

## Progress

- [x] Step 0 — confirm Ollama runs locally
- [x] V1 step 1 — `test_ollama.py`: send hardcoded text to Ollama, print reply
- [x] V1 step 2 — `profile.py`: candidate background as a reusable variable
- [x] V1 step 3 — `analyzer.py`: accept a pasted JD via terminal input
- [x] V1 step 4 — build the combined prompt (profile + JD + output format)
- [x] V1 step 5 — tune the prompt until output format is stable
- [x] V1 step 6 — tested against a real job description (M-Files AI Systems Specialist); confirmed the model is unreliable at detecting explicit Finnish-language requirements, motivating the V2 rule-based layer
- [ ] V2 — rule-based Finnish-language backstop + save judgment history
- [ ] V3 — RAG over profile/resume with ChromaDB
- [ ] V4 — agent + tool calling (fetch JD by URL, draft cover letter)
- [ ] V5 — evaluation harness + observability
