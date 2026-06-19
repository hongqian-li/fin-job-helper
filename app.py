# Streamlit frontend for fin-job-helper. This is an alternative entry
# point to analyzer.py's terminal interface -- it reuses the same building
# blocks (finnish_detector.py, retriever.py, history.py) but drives them
# from a browser UI instead of input()/print().

import streamlit as st
import requests
from finnish_detector import detect_finnish_requirement
from retriever import retrieve_relevant_chunks
from history import save_judgment

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
            f'{relevant_chunks}</div>',
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
        f'{verdict}</div>',
        unsafe_allow_html=True,
    )

    save_judgment(jd_text, finnish_check, verdict=verdict)
