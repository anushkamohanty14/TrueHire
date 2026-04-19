"""Page 3 — How TrueHire Works.

Explains the cognitive science and O*NET methodology behind
the ability-to-job matching pipeline.
"""
import streamlit as st

st.set_page_config(
    page_title="TrueHire — How It Works",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

#MainMenu, footer, header { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #f8f9fc !important;
    color: #191c1e !important;
}
.block-container {
    padding-top: 0 !important;
    padding-bottom: 5rem !important;
    max-width: 780px !important;
}
.hw-topbar {
    background: #f8fafc;
    border-bottom: 1px solid rgba(226,232,240,0.5);
    padding: 0 1.5rem; height: 64px;
    display: flex; align-items: center; justify-content: space-between;
    margin: -1rem -1rem 2.5rem -1rem;
}
.hw-brand { font-size:1.125rem; font-weight:900; letter-spacing:-0.04em; color:#00425e; }
.hw-page  { font-size:10px; font-weight:700; text-transform:uppercase;
            letter-spacing:0.12em; color:#40484e; opacity:0.6; }

.hw-heading {
    font-size:1.875rem; font-weight:900; letter-spacing:-0.03em;
    color:#191c1e; line-height:1.1; margin-bottom:0.5rem;
}
.hw-lead {
    font-size:1rem; color:#40484e; line-height:1.7;
    font-family:Inter,sans-serif; margin-bottom:2rem;
}
.hw-section {
    font-size:0.6875rem; text-transform:uppercase; letter-spacing:0.18em;
    font-weight:700; color:#40484e; margin:2.5rem 0 1rem; display:block;
}
.hw-step {
    display:flex; gap:1.25rem; align-items:flex-start;
    margin-bottom:1.25rem;
}
.hw-step-num {
    min-width:2.5rem; height:2.5rem; border-radius:50%;
    background:#00425e; color:#fff;
    display:flex; align-items:center; justify-content:center;
    font-size:0.875rem; font-weight:900; font-family:Inter,sans-serif;
    flex-shrink:0;
}
.hw-step-body { flex:1; }
.hw-step-title {
    font-size:0.9375rem; font-weight:800; color:#191c1e;
    font-family:Inter,sans-serif; margin-bottom:0.25rem;
}
.hw-step-desc {
    font-size:0.875rem; color:#40484e; line-height:1.6;
    font-family:Inter,sans-serif;
}
.hw-card {
    background:#f3f3f7; border-radius:0.25rem;
    padding:1.25rem 1.5rem; margin-bottom:0.75rem;
    border-left:3px solid #00425e;
}
.hw-ability-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:0.5rem 0; border-bottom:1px solid rgba(0,0,0,0.05);
    font-family:Inter,sans-serif;
}
.hw-ability-row:last-child { border-bottom:none; }
.hw-ability-name  { font-size:0.875rem; font-weight:600; color:#191c1e; }
.hw-ability-arrow { font-size:0.8rem; color:#40484e; font-style:italic; }

.stButton > button {
    font-family:'Inter',sans-serif !important; font-weight:700 !important;
    font-size:11px !important; text-transform:uppercase !important;
    letter-spacing:0.1em !important; border:none !important;
    border-radius:0.25rem !important; padding:0.75rem 1.25rem !important;
    width:100% !important; background-color:#edeef1 !important; color:#191c1e !important;
}
.stButton > button[kind="primary"] {
    background-color:#00425e !important; color:#ffffff !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="hw-topbar">'
    '<span class="hw-brand">TrueHire</span>'
    '<span class="hw-page">How It Works</span>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("""
<h2 class="hw-heading">Science-backed career matching</h2>
<p class="hw-lead">
    TrueHire doesn't ask you to guess what kind of worker you are.
    Instead, it measures <em>what your brain actually does well</em> — then maps that
    to the real cognitive demands of hundreds of careers using O*NET data from the
    US Department of Labor.
</p>
""", unsafe_allow_html=True)

# ── How the pipeline works ────────────────────────────────────────────────────

st.markdown('<span class="hw-section">The Matching Pipeline</span>', unsafe_allow_html=True)

steps = [
    (
        "Cognitive Assessment",
        "27 tasks across 9 ability domains. Scored against NCPT norms from 9,000+ "
        "test-takers to produce a percentile for each ability.",
    ),
    (
        "Ability → Work Activity Crosswalk",
        "Your ability percentiles are projected onto 332 O*NET Work Activities via "
        "a published ability-to-activity crosswalk. Instead of showing raw scores, "
        "we surface activities like 'Analysing Data' or 'Coordinating Work' — "
        "language employers and candidates both understand.",
    ),
    (
        "Hybrid Scoring",
        "Each job receives a weighted composite of three signals: cognitive ability "
        "fit (cosine similarity), work activity fit, and technical skill overlap. "
        "You control the weights on the Results page.",
    ),
    (
        "Explainability",
        "Every recommendation surfaces your strength activities (where your abilities "
        "align with the job) and gap activities (where the job demands more). "
        "The Skills & Growth page turns gaps into a 3-phase learning path.",
    ),
]

for i, (title, desc) in enumerate(steps, 1):
    st.markdown(f"""
    <div class="hw-step">
        <div class="hw-step-num">{i}</div>
        <div class="hw-step-body">
            <div class="hw-step-title">{title}</div>
            <div class="hw-step-desc">{desc}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── The 9 cognitive abilities ─────────────────────────────────────────────────

st.markdown('<span class="hw-section">The 9 Measured Abilities</span>', unsafe_allow_html=True)

ABILITY_MAP = [
    ("Deductive Reasoning",    "Drawing conclusions from rules and premises"),
    ("Mathematical Reasoning", "Solving quantitative problems without a calculator"),
    ("Memorization",           "Retaining and recalling sequences under load"),
    ("Perceptual Speed",       "Rapid visual scanning and pattern detection"),
    ("Problem Sensitivity",    "Identifying when something is wrong or at risk"),
    ("Selective Attention",    "Filtering relevant from irrelevant information"),
    ("Speed of Closure",       "Completing patterns from incomplete information"),
    ("Time Sharing",           "Managing two cognitive tasks simultaneously"),
    ("Written Comprehension",  "Extracting meaning from written text"),
]

rows_html = "".join(
    f'<div class="hw-ability-row">'
    f'<span class="hw-ability-name">{name}</span>'
    f'<span class="hw-ability-arrow">{desc}</span>'
    f'</div>'
    for name, desc in ABILITY_MAP
)
st.markdown(f'<div class="hw-card">{rows_html}</div>', unsafe_allow_html=True)

# ── Scoring formula ───────────────────────────────────────────────────────────

st.markdown('<span class="hw-section">The Scoring Formula</span>', unsafe_allow_html=True)

st.markdown("""
<div class="hw-card" style="border-left-color:#006a6a;">
    <p style="font-family:'Courier New',monospace; font-size:0.9375rem;
              font-weight:700; color:#191c1e; margin-bottom:0.5rem;">
        score = w<sub>ability</sub> × ability_sim<br>
              + w<sub>activity</sub> × activity_sim<br>
              + w<sub>skill</sub> × skill_sim
    </p>
    <p style="font-size:0.8125rem; color:#40484e; font-family:Inter,sans-serif; margin:0;">
        All similarities are cosine similarities (range −1 to +1, displayed as 0–100%).
        Default weights: 40% ability · 30% activity · 30% technical skills.
        Adjust them on the Job Matches page.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Data sources ──────────────────────────────────────────────────────────────

st.markdown('<span class="hw-section">Data Sources</span>', unsafe_allow_html=True)

sources = [
    ("O*NET Abilities Database",         "Job × ability requirement profiles for 894 occupations"),
    ("O*NET Work Activities Database",   "Job × work activity scores for 332 activities"),
    ("O*NET Technology Skills Database", "In-demand and hot technologies per occupation"),
    ("Ability → Work Activity Crosswalk","Maps each of the 9 abilities to the work activities it supports"),
    ("NCPT Population Dataset",          "9,000+ test-taker scores used to normalise your percentile rank"),
]

for name, desc in sources:
    st.markdown(f"""
    <div style="display:flex; gap:0.75rem; padding:0.6rem 0;
                border-bottom:1px solid rgba(0,0,0,0.05); font-family:Inter,sans-serif;">
        <span style="font-size:0.875rem; font-weight:700; color:#191c1e; min-width:220px;">{name}</span>
        <span style="font-size:0.875rem; color:#40484e;">{desc}</span>
    </div>
    """, unsafe_allow_html=True)

# ── CTA ───────────────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    if st.button("Take the Assessment", type="primary", use_container_width=True):
        st.switch_page("pages/02_cognitive.py")
with c2:
    if st.button("View Job Matches", use_container_width=True):
        st.switch_page("pages/04_results.py")
