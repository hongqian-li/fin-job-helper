# Streamlit frontend for fin-job-helper. This is an alternative entry
# point to analyzer.py's terminal interface -- it reuses the same building
# blocks (finnish_detector.py, retriever.py, history.py) but drives them
# from a browser UI instead of input()/print().

import html
import streamlit as st
import requests
from finnish_detector import detect_finnish_requirement
from retriever import retrieve_relevant_chunks
from history import save_judgment
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


def to_safe_html(text):
    # html.escape neutralizes "<"/"&" so the model's own output can't
    # break our markup. Converting "\n" to "<br>" (rather than relying on
    # CSS white-space: pre-wrap alone) matters for a different reason:
    # Streamlit's underlying Markdown parser treats a <div> with no blank
    # line after it as one literal "raw HTML block" -- but a blank LINE
    # inside that block ends raw mode and resumes Markdown parsing for
    # everything after it. If the model's verdict happens to have a blank
    # line before "Gaps:", those "- " lines get parsed into real <li>
    # bullets (with browser-default spacing) while earlier "- " lines
    # stay literal text -- the inconsistent spacing seen in testing.
    # Replacing newlines with <br> removes the blank lines from the
    # source entirely, so the whole block stays raw HTML throughout.
    return html.escape(text).replace("\n", "<br>")

# Terminal aesthetic: injected once, before any other Streamlit calls, so
# the whole page (including widgets rendered below) picks it up. Hidden
# chrome (#MainMenu, footer, header) uses tag/id selectors that are stable
# across Streamlit versions; widget styling uses the "st<WidgetName>"
# class names Streamlit attaches to each widget's wrapper div.
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0a0a0a;
        color: #f0f0f0;
    }
    .stApp, .stApp * {
        font-family: 'Courier New', Courier, monospace;
        color: #f0f0f0;
    }

    /* Streamlit's built-in icons (e.g. the expander's arrow) are ligature
    glyphs in the "Material Symbols Rounded" icon font -- forcing
    monospace on them above breaks the ligature and renders the literal
    icon name as clipped text (e.g. "keyboard_arrow_right" showing as a
    stray "ar"). Naming the icon font explicitly restores the glyph
    ("revert" doesn't work here: it skips every author-origin rule,
    including Streamlit's own icon-font declaration, not just ours). */
    [data-testid="stIconMaterial"] {
        font-family: 'Material Symbols Rounded' !important;
    }

    /* Text area */
    .stTextArea textarea {
        background-color: #111111;
        color: #f0f0f0;
        font-family: 'Courier New', Courier, monospace;
        border-radius: 0;
        border: 1px solid #333;
    }
    .stTextArea textarea::placeholder {
        color: #555555 !important;
    }

    /* Button. The broad ".stApp *" rule above sets every descendant's
    text to #f0f0f0, which would otherwise make the button's own label
    (an inner <p>/<div>, not the <button> itself) invisible against its
    light background -- "button *" re-targets those descendants directly
    so they win on specificity. */
    .stButton button, .stButton button * {
        background-color: #f0f0f0;
        color: #0a0a0a;
        border-radius: 0;
        border: none;
        text-transform: uppercase;
        width: 100%;
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
    }
    .stButton {
        width: 100% !important;
    }

    /* Alert boxes (st.error, etc.) */
    .stAlert, [data-testid="stAlert"] {
        border-radius: 0 !important;
    }

    /* Expander */
    .streamlit-expanderHeader, [data-testid="stExpander"] summary {
        background-color: #111111;
        color: #f0f0f0;
        font-family: 'Courier New', Courier, monospace;
    }
    .streamlit-expanderContent, [data-testid="stExpander"] div {
        background-color: #111111;
        color: #f0f0f0;
    }

    /* Code blocks (st.code) */
    .stCodeBlock, pre, code {
        background-color: #111111 !important;
        color: #f0f0f0 !important;
        font-family: 'Courier New', Courier, monospace !important;
    }

    /* Hard-stop / advantage notice boxes */
    .hard-stop-box {
        background-color: #2a0000;
        color: #ff4d4d;
        border: 1px solid #ff4d4d;
        padding: 12px;
        font-weight: bold;
        margin-bottom: 12px;
    }
    .advantage-box {
        background-color: #2a2400;
        color: #ffd24d;
        border: 1px solid #ffd24d;
        padding: 12px;
        font-weight: bold;
        margin-bottom: 12px;
    }

    /* V4 agent decision notices -- neutral styling (not a warning or an
    error, just "here's what the agent chose to do") so these read
    differently from the hard-stop/advantage boxes above. */
    .agent-notice-box {
        background-color: #1a1a1a;
        color: #f0f0f0;
        border: 1px solid #555;
        padding: 12px;
        margin-bottom: 12px;
    }

    /* Remove Streamlit's default hamburger menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("# FIN-JOB-HELPER")
st.markdown("Paste a JD. Get a verdict.")

jd_text = st.text_area(
    "JD input",
    placeholder="PASTE JD HERE",
    height=300,
    label_visibility="collapsed",
)

col = st.columns(1)[0]
with col:
    clicked = st.button("[ SCREEN ]", use_container_width=True)

if clicked:
    if not jd_text.strip():
        st.error("Paste a job description first.")
        st.stop()

    # Same rule-before-model decision flow as analyzer.py: a hard
    # requirement stops here, an advantage mention is just a notice.
    finnish_check = detect_finnish_requirement(jd_text)

    if finnish_check["required"]:
        st.markdown(
            f'<div class="hard-stop-box">'
            f'⛔ FINNISH REQUIRED — {finnish_check["matched_phrase"]}'
            f"</div>",
            unsafe_allow_html=True,
        )
        save_judgment(jd_text, finnish_check, verdict="skipped - Finnish required")
        st.stop()

    if finnish_check["mentioned_as_advantage"]:
        st.markdown(
            f'<div class="advantage-box">'
            f'⚠ Finnish mentioned as nice-to-have: {finnish_check["advantage_phrase"]}'
            f"</div>",
            unsafe_allow_html=True,
        )

    relevant_chunks = retrieve_relevant_chunks(jd_text)
    with st.expander("PROFILE CHUNKS", expanded=False):
        st.markdown(
            f'<div style="font-family: Courier New, monospace; color: #f0f0f0; '
            f'font-size: 14px; white-space: pre-wrap; word-wrap: break-word; '
            f'padding: 8px;">'
            f'{to_safe_html(relevant_chunks)}</div>',
            unsafe_allow_html=True,
        )

    # Same prompt template as analyzer.py's RAG version (V3 step 3) --
    # only the most relevant profile chunks are sent, not the full
    # profile.
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

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL_NAME = "llama3.2"

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }

    with st.spinner("Running analysis..."):
        response = requests.post(OLLAMA_URL, json=payload)
        data = response.json()

    verdict = data["response"]
    # A plain wrapping div instead of st.code: st.code never wraps long
    # lines, forcing a horizontal scrollbar to read the full verdict --
    # pre-wrap/break-word lets it wrap within the page width instead.
    st.markdown(
        f'<div style="font-family: Courier New, monospace; color: #f0f0f0; '
        f'font-size: 14px; white-space: pre-wrap; word-wrap: break-word; '
        f'background-color: #111111; border: 1px solid #333; padding: 12px;">'
        f'{to_safe_html(verdict)}</div>',
        unsafe_allow_html=True,
    )

    # V4: once a verdict exists, the agent decides which extra tools (if
    # any) are worth calling based on what's actually in the verdict and
    # the JD -- not every JD triggers every tool. Same decision logic as
    # analyzer.py's terminal version (see agent.py for why each condition
    # was chosen), shown here as notice boxes instead of printed lines.
    job_title, company_name = guess_job_title_and_company(jd_text)

    score = parse_match_score(verdict)
    if score is not None and should_search_company(score):
        st.markdown(
            f'<div class="agent-notice-box">'
            f"Score is ambiguous — would search company info: {company_name}"
            f"</div>",
            unsafe_allow_html=True,
        )
        mock_web_search(company_name)

    deadline = extract_deadline(jd_text)
    if deadline:
        st.markdown(
            f'<div class="agent-notice-box">'
            f"Deadline found: {deadline} — would create calendar reminder"
            f"</div>",
            unsafe_allow_html=True,
        )
        mock_create_calendar_reminder(deadline, job_title)

    if is_recommend_to_apply(score):
        talking_points = generate_cl_talking_points(jd_text, relevant_chunks, verdict)
        with st.expander("COVER LETTER TALKING POINTS", expanded=False):
            st.markdown(
                f'<div style="font-family: Courier New, monospace; color: #f0f0f0; '
                f'font-size: 14px; white-space: pre-wrap; word-wrap: break-word; '
                f'padding: 8px;">'
                f'{to_safe_html(talking_points)}</div>',
                unsafe_allow_html=True,
            )
        mock_save_to_drive(jd_text, verdict, talking_points, job_title)
        st.markdown(
            f'<div class="agent-notice-box">'
            f"Saved analysis to Google Drive: {job_title}_analysis.md"
            f"</div>",
            unsafe_allow_html=True,
        )

    save_judgment(jd_text, finnish_check, verdict=verdict)
