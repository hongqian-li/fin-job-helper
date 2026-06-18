# Profile lives in its own file (not hardcoded inside test_ollama.py or any
# other script) because every future version of this tool needs to reuse it:
# the V1 prompt, the V2 history logger, and the V3 RAG chunker all read the
# same background text. Keeping it in one place means updating the resume
# or constraints only requires editing this file once.

MY_PROFILE = """
AI & Cloud Engineer based in Tampere, Finland, graduating June 2026 (BBA
in DevOps/Delivering Software Products, HAMK, GPA 4.98/5), with an
exchange semester in IT Infrastructure & Cloud Computing in Vienna. Open
to hybrid or remote roles across the EU.

Skills: Azure, Terraform, Docker, Kubernetes (working knowledge), Python,
Flask, SQL, Linux, Git, CI/CD with GitHub Actions. Applied AI tooling:
RAG pipelines, ChromaDB, Ollama, MCP servers, LangChain, prompt
engineering.

Experience: Thesis "Security by Design for Enterprise AI Chatbots" (5/5),
a defense-in-depth architecture combining keyword detection, prompt-
injection filtering, and LLM fallback for GDPR Article 9 compliance.
Built a privacy-conscious AI support system (RAG + MCP + Ollama) for the
HAMK service desk, with a deterministic classifier routing sensitive
queries to humans before any LLM call. Also built an Azure private-
network file-sharing system with Terraform (three-tier network,
Application Gateway). Prior client-facing experience in education
advising and customer service.

Constraints: Finnish is A2 on paper but not functional for real work
communication, so treat as effectively not speaking Finnish; any role
that lists Finnish as required or expects working-level Finnish is out
of reach. Fresh graduate with no multi-year industry experience.
"""
