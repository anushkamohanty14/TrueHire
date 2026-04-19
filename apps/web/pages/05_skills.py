"""Page 5 — Skills & Growth Path.

Loads a user's profile, lets them pick a target job, and shows:
  - Match breakdown (strengths vs gaps in work-activity language)
  - Tech skill gaps derived from O*NET Technology Skills data
  - A 3-phase learning path
"""
from __future__ import annotations

from typing import List

import streamlit as st

from core.src.core.pipelines.phase6_skill_matching import build_tech_matrix
from core.src.core.pipelines.phase7_hybrid_recommendation import HybridRecommender
from core.src.core.storage.mongo_store import MongoUserStore

st.set_page_config(
    page_title="TrueHire — Skills & Growth",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

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
    max-width: 820px !important;
}

.sk-topbar {
    background: #f8fafc;
    border-bottom: 1px solid rgba(226,232,240,0.5);
    padding: 0 1.5rem;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: -1rem -1rem 2.5rem -1rem;
}
.sk-brand  { font-size:1.125rem; font-weight:900; letter-spacing:-0.04em; color:#00425e; }
.sk-page   { font-size:10px; font-weight:700; text-transform:uppercase;
             letter-spacing:0.12em; color:#40484e; opacity:0.6; }

.sk-overline {
    font-size: 10px; text-transform: uppercase; letter-spacing: 0.2em;
    font-weight: 700; color: #40484e; opacity: 0.7;
    margin-bottom: 0.4rem; display: block;
}
.sk-section {
    font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.18em;
    font-weight: 700; color: #40484e; margin: 2rem 0 1rem; display: block;
}
.sk-heading {
    font-size: 1.875rem; font-weight: 900; letter-spacing: -0.03em;
    color: #191c1e; line-height: 1.1; margin-bottom: 1.25rem;
}

.sk-card {
    background: #f3f3f7; border-radius: 0.25rem;
    padding: 1.25rem 1.5rem; margin-bottom: 0.75rem;
}
.sk-strength-card { border-left: 3px solid #006a6a; }
.sk-gap-card      { border-left: 3px solid #b45309; }
.sk-phase-card    { border-left: 3px solid #00425e; }

.sk-activity-item {
    font-size: 0.875rem; font-weight: 500; color: #191c1e;
    padding: 0.4rem 0; border-bottom: 1px solid rgba(0,0,0,0.05);
    line-height: 1.4;
}
.sk-activity-item:last-child { border-bottom: none; }

.sk-skill-chip {
    display: inline-block; background: #e1e2e6; border-radius: 0.125rem;
    padding: 0.2rem 0.6rem; font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em; color: #40484e;
    margin-right: 0.4rem; margin-bottom: 0.4rem;
}
.sk-skill-chip-missing {
    background: #fef3c7; color: #92400e;
}

.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important; font-size: 11px !important;
    text-transform: uppercase !important; letter-spacing: 0.1em !important;
    border: none !important; border-radius: 0.25rem !important;
    padding: 0.75rem 1.25rem !important; width: 100% !important;
    background-color: #edeef1 !important; color: #191c1e !important;
}
.stButton > button[kind="primary"] {
    background-color: #00425e !important; color: #ffffff !important;
}
.stTextInput input {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    background: #edeef1 !important; border: none !important;
    border-bottom: 2px solid #c0c7ce !important; border-radius: 0 !important;
    color: #191c1e !important; padding: 0.75rem 1rem !important;
}
.stTextInput label, .stSelectbox label {
    font-family: 'Inter', sans-serif !important; font-size: 10px !important;
    font-weight: 700 !important; text-transform: uppercase !important;
    letter-spacing: 0.15em !important; color: #40484e !important;
}
</style>
""", unsafe_allow_html=True)

# ── Topbar ────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="sk-topbar">'
    '<span class="sk-brand">TrueHire</span>'
    '<span class="sk-page">Skills &amp; Growth</span>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_resource
def _get_recommender() -> HybridRecommender:
    return HybridRecommender()


@st.cache_resource
def _get_tech_matrix():
    return build_tech_matrix()


def _missing_tech_skills(job_title: str, user_skills: List[str], top_n: int = 6) -> List[str]:
    """Return top tech skills required by the job that the user does not have."""
    tech_matrix = _get_tech_matrix()
    if job_title not in tech_matrix.index:
        return []
    job_row   = tech_matrix.loc[job_title]
    u_lower   = {s.strip().lower() for s in user_skills}
    missing   = []
    for tech, weight in job_row.nlargest(30).items():
        if weight == 0:
            break
        t_lower = tech.lower()
        # Case-insensitive substring match — same logic as phase6
        has_it = any(u in t_lower or t_lower in u for u in u_lower)
        if not has_it:
            missing.append(tech)
        if len(missing) >= top_n:
            break
    return missing


# ── User ID ───────────────────────────────────────────────────────────────────

_, mid, _ = st.columns([1, 4, 1])
with mid:
    uid = st.text_input(
        "User ID",
        value=st.session_state.get("user_id", ""),
        placeholder="Enter your User ID",
        key="sk_uid",
    )

if uid.strip():
    st.session_state["user_id"] = uid.strip()
else:
    st.info("Enter your User ID to load your profile.")
    st.stop()

user_id = uid.strip()

# ── Load profile ──────────────────────────────────────────────────────────────

store   = MongoUserStore()
profile = store.get_profile(user_id)

if profile is None:
    st.error("No profile found. Complete the Profile page first.")
    st.stop()

ability_percentiles = profile.get("ability_percentiles", {})
if not ability_percentiles:
    st.warning("No cognitive assessment results found. Complete the Cognitive Assessment first.")
    st.stop()

user_skills   = list(set(profile.get("resume_skills", []) + profile.get("manual_skills", [])))
readiness     = profile.get("readiness_score", 50.0)

# ── Get top recommendations for job selector ──────────────────────────────────

with st.spinner("Loading your job matches…"):
    rec     = _get_recommender()
    top10   = rec.recommend(ability_percentiles=ability_percentiles, user_skills=user_skills, top_n=10)

job_options = [r.job_title for r in top10]

# ── Job selector ──────────────────────────────────────────────────────────────

st.markdown('<span class="sk-section">Select a Target Role</span>', unsafe_allow_html=True)

selected_job = st.selectbox(
    "Target job",
    options=job_options,
    index=0,
    help="Choose a job from your top matches to explore skills and growth areas.",
)

# ── Detailed breakdown for selected job ──────────────────────────────────────

detail = rec.explain_job(selected_job, ability_percentiles, top_k=5)
match_pct     = detail.get("match_percent", 0)
strengths     = detail.get("strength_activities", [])
gaps          = detail.get("gap_activities", [])
top_acts      = detail.get("top_job_activities", [])
missing_tech  = _missing_tech_skills(selected_job, user_skills)

# ── Match score header ────────────────────────────────────────────────────────

match_bar = min(float(match_pct), 100)
st.markdown(f"""
<div style="margin:1.5rem 0 2rem;">
    <span class="sk-overline">{selected_job}</span>
    <div style="display:flex; align-items:baseline; gap:0.75rem; margin-bottom:0.5rem;">
        <span style="font-size:2.5rem; font-weight:900; color:#00425e;
                     font-family:Inter,sans-serif; line-height:1;">{match_pct:.0f}%</span>
        <span style="font-size:0.875rem; font-weight:600; color:#40484e;">Activity match</span>
    </div>
    <div style="height:5px; background:#e1e2e6; border-radius:3px; overflow:hidden;">
        <div style="height:100%; width:{match_bar:.1f}%; background:#00425e;
                    border-radius:3px; transition:width 0.5s;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Strengths & Gaps columns ──────────────────────────────────────────────────

st.markdown('<span class="sk-section">Your Strengths vs Growth Areas</span>', unsafe_allow_html=True)

col_str, col_gap = st.columns(2)

with col_str:
    items_html = "".join(
        f'<div class="sk-activity-item">✓ &nbsp;{a}</div>'
        for a in (strengths or ["—"])
    )
    st.markdown(f"""
    <div class="sk-card sk-strength-card">
        <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                     letter-spacing:0.12em; color:#006a6a; display:block; margin-bottom:0.75rem;">
            Your Strengths
        </span>
        <p style="font-size:0.8rem; color:#40484e; margin-bottom:0.75rem; font-family:Inter,sans-serif;">
            Work activities your cognitive profile supports in this role.
        </p>
        {items_html}
    </div>
    """, unsafe_allow_html=True)

with col_gap:
    items_html = "".join(
        f'<div class="sk-activity-item">△ &nbsp;{a}</div>'
        for a in (gaps or ["—"])
    )
    st.markdown(f"""
    <div class="sk-card sk-gap-card">
        <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                     letter-spacing:0.12em; color:#b45309; display:block; margin-bottom:0.75rem;">
            Growth Areas
        </span>
        <p style="font-size:0.8rem; color:#40484e; margin-bottom:0.75rem; font-family:Inter,sans-serif;">
            Activities the role demands more than your current profile supports.
        </p>
        {items_html}
    </div>
    """, unsafe_allow_html=True)

# ── Top activities in this role ───────────────────────────────────────────────

if top_acts:
    acts_html = "".join(
        f'<div class="sk-activity-item">'
        f'<span style="font-size:10px; font-weight:700; color:#00425e; margin-right:0.5rem;">'
        f'{i+1}</span>{a}</div>'
        for i, a in enumerate(top_acts)
    )
    st.markdown(f"""
    <div class="sk-card" style="margin-top:1rem;">
        <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                     letter-spacing:0.12em; color:#40484e; display:block; margin-bottom:0.75rem;">
            Top Activities in This Role
        </span>
        {acts_html}
    </div>
    """, unsafe_allow_html=True)

# ── Learning path ─────────────────────────────────────────────────────────────

st.markdown('<span class="sk-section">Learning Path</span>', unsafe_allow_html=True)

# Phase 1 — Cognitive strengths to leverage
phase1_items = strengths[:3] if strengths else []
phase1_html  = "".join(f"<li>{a}</li>" for a in phase1_items) if phase1_items else "<li>Complete the cognitive assessment to personalise this phase.</li>"

st.markdown(f"""
<div class="sk-card sk-phase-card">
    <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                 letter-spacing:0.12em; color:#00425e; display:block; margin-bottom:0.25rem;">
        Phase 1 — Leverage Your Cognitive Strengths
    </span>
    <p style="font-size:0.8125rem; color:#40484e; font-family:Inter,sans-serif; margin-bottom:0.5rem;">
        Seek roles and projects that tap into your highest-scoring work activities.
        These are where you'll build momentum fastest.
    </p>
    <ul style="font-size:0.875rem; color:#191c1e; font-family:Inter,sans-serif;
               padding-left:1.25rem; margin:0; line-height:2;">
        {phase1_html}
    </ul>
</div>
""", unsafe_allow_html=True)

# Phase 2 — Close cognitive gaps through practice
phase2_items = gaps[:3] if gaps else []
phase2_html  = "".join(f"<li>{a}</li>" for a in phase2_items) if phase2_items else "<li>No significant cognitive gaps detected for this role.</li>"

st.markdown(f"""
<div class="sk-card sk-gap-card">
    <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                 letter-spacing:0.12em; color:#b45309; display:block; margin-bottom:0.25rem;">
        Phase 2 — Build Capability in Gap Areas
    </span>
    <p style="font-size:0.8125rem; color:#40484e; font-family:Inter,sans-serif; margin-bottom:0.5rem;">
        These work activities are where the role demands more than your current
        cognitive profile. Targeted practice in these areas will raise your match score.
    </p>
    <ul style="font-size:0.875rem; color:#191c1e; font-family:Inter,sans-serif;
               padding-left:1.25rem; margin:0; line-height:2;">
        {phase2_html}
    </ul>
</div>
""", unsafe_allow_html=True)

# Phase 3 — Tech skill acquisition
if missing_tech:
    chips_html = "".join(
        f'<span class="sk-skill-chip sk-skill-chip-missing">{t}</span>'
        for t in missing_tech
    )
    tech_body = f"""
    <p style="font-size:0.8125rem; color:#40484e; font-family:Inter,sans-serif; margin-bottom:0.75rem;">
        These are the highest-weighted technologies for <em>{selected_job}</em>
        that are not yet in your skill profile.
    </p>
    <div>{chips_html}</div>
    """
else:
    # User already has all top tech skills for this job
    user_chips = "".join(
        f'<span class="sk-skill-chip">{s}</span>'
        for s in user_skills[:8]
    )
    tech_body = f"""
    <p style="font-size:0.8125rem; color:#006a6a; font-family:Inter,sans-serif; margin-bottom:0.5rem;">
        Your tech skill profile already covers the top technologies for this role.
    </p>
    <div>{user_chips}</div>
    """

st.markdown(f"""
<div class="sk-card" style="border-left:3px solid #40484e; margin-bottom:1rem;">
    <span style="font-size:10px; font-weight:700; text-transform:uppercase;
                 letter-spacing:0.12em; color:#40484e; display:block; margin-bottom:0.25rem;">
        Phase 3 — Acquire In-Demand Technical Skills
    </span>
    {tech_body}
</div>
""", unsafe_allow_html=True)

# ── CTA ───────────────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
_, c_mid, _ = st.columns([2, 3, 2])
with c_mid:
    if st.button("View All Job Matches →", type="primary", use_container_width=True):
        st.switch_page("pages/04_results.py")
