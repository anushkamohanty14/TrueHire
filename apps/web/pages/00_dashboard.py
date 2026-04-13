"""Page 0 — CogniHire Dashboard.

Shows readiness ring, top-3 job matches, and skill/ability snapshots
for the logged-in user.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st

from core.src.core.pipelines.phase7_hybrid_recommendation import HybridRecommender
from core.src.core.storage.mongo_store import MongoUserStore

st.set_page_config(
    page_title="CogniHire — Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styles + Layout ───────────────────────────────────────────────────────────

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _styles import inject_styles, layout_html, readiness_ring_svg  # noqa: E402

inject_styles()
st.markdown(layout_html("dashboard"), unsafe_allow_html=True)

# ── User ID ───────────────────────────────────────────────────────────────────

uid = st.text_input(
    "User ID",
    value=st.session_state.get("user_id", ""),
    placeholder="Enter your User ID",
    key="dash_uid",
)

if uid.strip():
    st.session_state["user_id"] = uid.strip()
else:
    st.markdown("""
    <div style="text-align:center;padding:4rem 0;max-width:480px;margin:0 auto;">
      <div style="width:64px;height:64px;border-radius:16px;background:#c6e7ff;
                  display:flex;align-items:center;justify-content:center;margin:0 auto 1.5rem;">
        <span class="material-symbols-outlined" style="font-size:2rem;color:#00425e;">dashboard</span>
      </div>
      <h2 style="font-family:Manrope,sans-serif;font-size:1.75rem;font-weight:800;
                 letter-spacing:-0.03em;color:#191c1e;margin-bottom:0.75rem;">Your Career Dashboard</h2>
      <p style="font-family:Inter,sans-serif;font-size:0.9375rem;color:#40484e;line-height:1.6;">
        Enter your User ID above to load your cognitive profile and job matches.
      </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

user_id = uid.strip()

# ── Load profile ──────────────────────────────────────────────────────────────

store   = MongoUserStore()
profile = store.get_profile(user_id)

if profile is None:
    st.error("No profile found. Complete the Profile page first.")
    st.stop()

ability_percentiles = profile.get("ability_percentiles", {})
readiness           = profile.get("readiness_score")
resume_skills       = profile.get("resume_skills", [])
manual_skills       = profile.get("manual_skills", [])
user_skills         = list(set(resume_skills + manual_skills))
assessed_at         = profile.get("assessed_at", "")

# ── Hero — greeting + readiness ring ─────────────────────────────────────────

readiness_pct = float(readiness) if readiness is not None else None

if readiness_pct is not None:
    if readiness_pct >= 67:
        tier, tier_col = "High Readiness", "#006a6a"
    elif readiness_pct >= 33:
        tier, tier_col = "Mid Readiness",  "#00425e"
    else:
        tier, tier_col = "Developing",     "#70787e"

    ring_html = readiness_ring_svg(readiness_pct, size=160)

    st.markdown(f"""
    <div style="background:#ffffff;border-radius:16px;border:1px solid #eceef1;
                padding:2rem;margin-bottom:1.5rem;
                display:flex;align-items:center;gap:2rem;
                box-shadow:0 1px 3px rgba(0,0,0,0.04);">
      <div style="flex-shrink:0;">{ring_html}</div>
      <div>
        <div style="font-family:Inter,sans-serif;font-size:11px;font-weight:700;
                    text-transform:uppercase;letter-spacing:0.15em;color:#40484e;margin-bottom:0.25rem;">
          Welcome back
        </div>
        <h2 style="font-family:Manrope,sans-serif;font-size:1.5rem;font-weight:800;
                   color:#191c1e;margin-bottom:0.5rem;letter-spacing:-0.02em;">{user_id}</h2>
        <span style="font-size:11px;font-weight:700;text-transform:uppercase;
                     letter-spacing:0.12em;color:{tier_col};
                     background:{'#e8f5f0' if tier_col=='#006a6a' else '#e8f0f5'};
                     padding:0.2rem 0.6rem;border-radius:4px;">{tier}</span>
        <p style="font-family:Inter,sans-serif;font-size:0.8125rem;color:#40484e;
                  margin-top:0.75rem;line-height:1.5;">
          Cognitive percentile vs 9,000+ test-takers.<br>
          {len(user_skills)} skills tracked &nbsp;·&nbsp; {len(ability_percentiles)} abilities assessed.
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:#ffffff;border-radius:16px;border:1px solid #eceef1;
                padding:2rem;margin-bottom:1.5rem;text-align:center;">
      <span class="material-symbols-outlined" style="font-size:2.5rem;color:#c0c7ce;">psychology</span>
      <p style="font-family:Inter,sans-serif;font-size:0.9375rem;color:#40484e;margin-top:0.5rem;">
        No assessment results yet. Complete the <strong>Cognitive Assessment</strong> to see your readiness score.
      </p>
    </div>
    """, unsafe_allow_html=True)

# ── Quick action cards ────────────────────────────────────────────────────────

st.markdown('<span class="ch-section">Quick Actions</span>', unsafe_allow_html=True)

qc1, qc2, qc3 = st.columns(3)

with qc1:
    st.markdown("""
    <div style="background:#00425e;border-radius:12px;padding:1.5rem;margin-bottom:0.5rem;
                min-height:130px;display:flex;flex-direction:column;justify-content:space-between;">
      <span class="material-symbols-outlined" style="font-size:1.75rem;color:#c6e7ff;">psychology</span>
      <div>
        <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;
                    color:#ffffff;margin-bottom:0.25rem;">Cognitive Assessment</div>
        <div style="font-family:Inter,sans-serif;font-size:12px;color:rgba(255,255,255,0.7);">
          27 tasks · 15-20 min
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Start Assessment", key="qa_cognitive", type="primary", use_container_width=True):
        st.switch_page("pages/02_cognitive.py")

with qc2:
    st.markdown("""
    <div style="background:#ffffff;border-radius:12px;padding:1.5rem;margin-bottom:0.5rem;
                border:1px solid #eceef1;min-height:130px;
                display:flex;flex-direction:column;justify-content:space-between;">
      <span class="material-symbols-outlined" style="font-size:1.75rem;color:#006a6a;">description</span>
      <div>
        <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;
                    color:#191c1e;margin-bottom:0.25rem;">Analyze Resume</div>
        <div style="font-family:Inter,sans-serif;font-size:12px;color:#40484e;">
          Extract skills automatically
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Upload Resume", key="qa_resume", use_container_width=True):
        st.switch_page("pages/01_profile.py")

with qc3:
    st.markdown("""
    <div style="background:#ffffff;border-radius:12px;padding:1.5rem;margin-bottom:0.5rem;
                border:1px solid #eceef1;min-height:130px;
                display:flex;flex-direction:column;justify-content:space-between;">
      <span class="material-symbols-outlined" style="font-size:1.75rem;color:#40484e;">record_voice_over</span>
      <div>
        <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;
                    color:#191c1e;margin-bottom:0.25rem;">Practice Interview</div>
        <div style="font-family:Inter,sans-serif;font-size:12px;color:#40484e;">
          AI-powered mock sessions
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Coming Soon", key="qa_interview", use_container_width=True, disabled=True):
        pass

# ── Skill Growth Tracking ─────────────────────────────────────────────────────

st.markdown('<span class="ch-section">Skill Growth Tracking</span>', unsafe_allow_html=True)

sg_col1, sg_col2 = st.columns([1, 1])

with sg_col1:
    st.markdown(f"""
    <div class="ch-card" style="height:100%;">
      <div style="font-family:Inter,sans-serif;font-size:11px;font-weight:700;
                  text-transform:uppercase;letter-spacing:0.12em;color:#40484e;margin-bottom:1rem;">
        Technical Skills
      </div>
      <div style="font-family:Manrope,sans-serif;font-size:2.5rem;font-weight:800;
                  color:#00425e;line-height:1;margin-bottom:0.5rem;">
        {len(user_skills)}
      </div>
      <div style="font-family:Inter,sans-serif;font-size:0.8125rem;color:#40484e;margin-bottom:1rem;">
        {len(resume_skills)} from resume &nbsp;·&nbsp; {len(manual_skills)} manually added
      </div>
      <div>
        {"".join(f'<span class="ch-chip">{s}</span>' for s in user_skills[:8])}
        {"" if len(user_skills) <= 8 else f'<span class="ch-chip">+{len(user_skills)-8} more</span>'}
      </div>
    </div>
    """, unsafe_allow_html=True)

with sg_col2:
    st.markdown(f"""
    <div class="ch-card" style="height:100%;">
      <div style="font-family:Inter,sans-serif;font-size:11px;font-weight:700;
                  text-transform:uppercase;letter-spacing:0.12em;color:#40484e;margin-bottom:1rem;">
        Ability Scores
      </div>
      <div style="font-family:Manrope,sans-serif;font-size:2.5rem;font-weight:800;
                  color:#00425e;line-height:1;margin-bottom:1rem;">
        {len(ability_percentiles)}<span style="font-size:1rem;font-weight:600;color:#40484e;"> / 9</span>
      </div>
    """, unsafe_allow_html=True)

    if ability_percentiles:
        for label, pct in list(ability_percentiles.items())[:6]:
            short = label.split()[0]
            pct_f = float(pct)
            st.markdown(f"""
      <div style="margin-bottom:0.6rem;">
        <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
          <span style="font-family:Inter,sans-serif;font-size:12px;font-weight:500;color:#40484e;">{short}</span>
          <span style="font-family:Inter,sans-serif;font-size:12px;font-weight:700;color:#191c1e;">{pct_f:.0f}</span>
        </div>
        <div class="ch-progress-track">
          <div class="ch-progress-fill" style="width:{min(pct_f,100):.1f}%;"></div>
        </div>
      </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
      <p style="font-family:Inter,sans-serif;font-size:0.875rem;color:#40484e;">
        Complete the cognitive assessment to see ability scores.
      </p>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ── Top Job Matches ───────────────────────────────────────────────────────────

st.markdown('<span class="ch-section">Top Job Matches</span>', unsafe_allow_html=True)

if not ability_percentiles:
    st.info("Complete the Cognitive Assessment to see job matches.")
else:
    @st.cache_resource
    def _get_recommender() -> HybridRecommender:
        return HybridRecommender()

    with st.spinner("Loading matches…"):
        rec  = _get_recommender()
        top3 = rec.recommend(
            ability_percentiles=ability_percentiles,
            user_skills=user_skills,
            top_n=3,
        )

    jm_cols = st.columns(3)
    for i, r in enumerate(top3):
        acts = ", ".join(r.strength_activities[:2]) if r.strength_activities else "—"
        score_pct = min(r.total_score * 100, 100)
        ability_pct = min(r.ability_score * 100, 100)
        activity_pct = min(r.activity_score * 100, 100)
        skill_pct = min(r.skill_score * 100, 100)

        with jm_cols[i]:
            st.markdown(f"""
            <div class="ch-card" style="height:100%;">
              <div style="font-family:Inter,sans-serif;font-size:10px;font-weight:700;
                          text-transform:uppercase;letter-spacing:0.12em;color:#00425e;
                          margin-bottom:0.25rem;">#{r.rank} Match</div>
              <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;
                          color:#191c1e;margin-bottom:0.5rem;line-height:1.2;">{r.job_title}</div>
              <div style="font-family:Manrope,sans-serif;font-size:1.5rem;font-weight:800;
                          color:#00425e;margin-bottom:0.5rem;">{score_pct:.0f}%</div>
              <div class="ch-progress-track" style="margin-bottom:0.75rem;">
                <div class="ch-progress-fill" style="width:{score_pct:.1f}%;"></div>
              </div>
              <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
                <span style="font-family:Inter,sans-serif;font-size:11px;color:#40484e;">
                  <strong style="color:#006a6a;">Cog</strong> {ability_pct:.0f}%
                </span>
                <span style="font-family:Inter,sans-serif;font-size:11px;color:#40484e;">
                  <strong style="color:#00425e;">Activity</strong> {activity_pct:.0f}%
                </span>
                <span style="font-family:Inter,sans-serif;font-size:11px;color:#40484e;">
                  <strong style="color:#40484e;">Skills</strong> {skill_pct:.0f}%
                </span>
              </div>
              <p style="font-family:Inter,sans-serif;font-size:11px;color:#70787e;
                        margin-top:0.5rem;line-height:1.4;">{acts}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, c_mid, _ = st.columns([2, 3, 2])
    with c_mid:
        if st.button("View All Job Matches →", type="primary", use_container_width=True):
            st.switch_page("pages/04_results.py")

# ── Recent Activity ───────────────────────────────────────────────────────────

st.markdown('<span class="ch-section">Recent Activity</span>', unsafe_allow_html=True)

activity_items = [
    ("psychology",  "#c6e7ff", "#00425e", "Cognitive Assessment",  assessed_at[:10] if assessed_at else "—",      "Completed"),
    ("description", "#ccfbf1", "#006a6a", "Resume Uploaded",       f"{len(resume_skills)} skills extracted",       "Done"),
    ("auto_stories","#eceef1", "#40484e", "Skills & Growth",       "Check your learning path",                      "View"),
]

for icon, bg, fg, title, subtitle, badge in activity_items:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:1rem;
                padding:0.875rem 1rem;background:#ffffff;border-radius:10px;
                border:1px solid #eceef1;margin-bottom:0.5rem;">
      <div style="width:40px;height:40px;border-radius:10px;background:{bg};
                  display:flex;align-items:center;justify-content:center;flex-shrink:0;">
        <span class="material-symbols-outlined" style="font-size:1.25rem;color:{fg};">{icon}</span>
      </div>
      <div style="flex:1;">
        <div style="font-family:Inter,sans-serif;font-size:13px;font-weight:600;
                    color:#191c1e;">{title}</div>
        <div style="font-family:Inter,sans-serif;font-size:11px;color:#70787e;">{subtitle}</div>
      </div>
      <span style="font-family:Inter,sans-serif;font-size:11px;font-weight:600;
                   color:#40484e;background:#f2f4f7;padding:0.2rem 0.6rem;border-radius:4px;">
        {badge}
      </span>
    </div>
    """, unsafe_allow_html=True)

# ── Navigation CTAs ───────────────────────────────────────────────────────────

st.markdown('<span class="ch-section">Continue</span>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Cognitive Assessment", use_container_width=True):
        st.switch_page("pages/02_cognitive.py")
with c2:
    if st.button("Update Profile", use_container_width=True):
        st.switch_page("pages/01_profile.py")
with c3:
    if st.button("Skills & Growth", use_container_width=True):
        st.switch_page("pages/05_skills.py")
