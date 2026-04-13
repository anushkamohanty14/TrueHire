"""Page 4 — Hybrid Job Recommendations."""
import streamlit as st

from core.src.core.pipelines.phase7_hybrid_recommendation import HybridRecommender
from core.src.core.storage.mongo_store import MongoUserStore

st.header("Your Job Recommendations")

# ── Load user profile ────────────────────────────────────────────────────────

user_id = st.text_input("User ID", placeholder="Enter the same ID used on the Profile page")

if not user_id.strip():
    st.info("Enter your User ID to load your profile and cognitive results.")
    st.stop()

store = MongoUserStore()
profile = store.get_profile(user_id.strip())

if profile is None:
    st.error("No profile found for this User ID. Complete the Profile page first.")
    st.stop()

ability_percentiles = profile.get("ability_percentiles", {})
if not ability_percentiles:
    st.warning("No cognitive assessment results found. Complete the Cognitive Assessment first.")
    st.stop()

user_skills = list(set(
    profile.get("resume_skills", []) + profile.get("manual_skills", [])
))

# ── Weight controls ───────────────────────────────────────────────────────────

st.subheader("Adjust recommendation weights")
st.caption("Controls how much each signal contributes to your job match score.")

col1, col2, col3 = st.columns(3)
with col1:
    w_ability = st.slider("Cognitive ability", 0.0, 1.0, 0.4, 0.05)
with col2:
    w_activity = st.slider("Work activity fit", 0.0, 1.0, 0.3, 0.05)
with col3:
    w_skill = st.slider("Technical skills", 0.0, 1.0, 0.3, 0.05)

weights = {"ability": w_ability, "activity": w_activity, "skill": w_skill}
total = sum(weights.values())
if total == 0:
    st.error("At least one weight must be greater than 0.")
    st.stop()

st.caption(f"Effective weights — ability: {w_ability/total:.0%}  |  activity: {w_activity/total:.0%}  |  skills: {w_skill/total:.0%}")

top_n = st.slider("Number of recommendations", 5, 20, 10)

# ── Run recommender ───────────────────────────────────────────────────────────

with st.spinner("Calculating your matches…"):
    rec = HybridRecommender()
    results = rec.recommend(
        ability_percentiles=ability_percentiles,
        user_skills=user_skills,
        weights=weights,
        top_n=top_n,
    )

st.success(f"Top {len(results)} matches found")

# ── Display results ───────────────────────────────────────────────────────────

for r in results:
    with st.expander(f"#{r.rank}  {r.job_title}  —  {r.total_score * 100:.1f}% match"):

        # Score breakdown bar chart
        score_cols = st.columns(3)
        with score_cols[0]:
            st.metric("Cognitive", f"{r.ability_score * 100:.1f}%")
        with score_cols[1]:
            st.metric("Work Activity", f"{r.activity_score * 100:.1f}%")
        with score_cols[2]:
            st.metric("Skills", f"{r.skill_score * 100:.1f}%")

        # Strengths — expressed as work activities, not raw ability names
        if r.strength_activities:
            st.markdown("**Your strengths for this role:**")
            for act in r.strength_activities:
                st.markdown(f"- {act}")

        # Gaps
        if r.gap_activities:
            st.markdown("**Areas to develop:**")
            for act in r.gap_activities:
                st.markdown(f"- {act}")

        # Detailed breakdown button
        if st.button(f"Full breakdown — {r.job_title}", key=f"detail_{r.rank}"):
            detail = rec.explain_job(r.job_title, ability_percentiles)
            st.markdown(f"**Match: {detail.get('match_percent', '—')}%**")
            st.markdown("**Top work activities in this role:**")
            for act in detail.get("top_job_activities", []):
                st.markdown(f"- {act}")
