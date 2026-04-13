"""Page 1 — Resume & Skill Analysis (Cognitive Blueprint Analysis)."""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st

from core.src.core.pipelines.phase2_user_input import (
    collect_interest_tags,
    collect_manual_skills,
    create_user_profile,
    load_job_titles_from_onet,
    merge_resume_skills,
    suggest_jobs_from_interest_tags,
    upload_resume,
)
from core.src.core.pipelines.phase5_resume_processing import process_resume

st.set_page_config(
    page_title="CogniHire — Resume Analysis",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styles + Layout ───────────────────────────────────────────────────────────

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _styles import inject_styles, layout_html  # noqa: E402

inject_styles()
st.markdown(layout_html("resume"), unsafe_allow_html=True)

# ── Page header ───────────────────────────────────────────────────────────────

st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;
            margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px solid #eceef1;">
  <div>
    <div style="font-family:Inter,sans-serif;font-size:11px;font-weight:700;
                text-transform:uppercase;letter-spacing:0.15em;color:#40484e;margin-bottom:0.25rem;">
      Profile
    </div>
    <h1 style="font-family:Manrope,sans-serif;font-size:1.75rem;font-weight:800;
               letter-spacing:-0.03em;color:#191c1e;margin:0;">
      Cognitive Blueprint Analysis
    </h1>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Bento grid layout ─────────────────────────────────────────────────────────

left_col, right_col = st.columns([5, 7])

with left_col:
    # Upload zone
    st.markdown("""
    <div style="background:#ffffff;border-radius:12px;border:1px solid #eceef1;
                padding:1.5rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
      <div style="font-family:Manrope,sans-serif;font-size:14px;font-weight:700;
                  color:#191c1e;margin-bottom:1rem;display:flex;align-items:center;gap:0.5rem;">
        <span class="material-symbols-outlined" style="font-size:1.125rem;color:#006a6a;">upload_file</span>
        Upload Resume
      </div>
      <div style="background:#f8f9fd;border:2px dashed #c0c7ce;border-radius:10px;
                  padding:1.5rem;text-align:center;margin-bottom:1rem;">
        <span class="material-symbols-outlined" style="font-size:2rem;color:#c0c7ce;">description</span>
        <p style="font-family:Inter,sans-serif;font-size:12px;color:#70787e;margin-top:0.5rem;margin-bottom:0;">
          PDF, TXT, DOC, DOCX
        </p>
      </div>
    """, unsafe_allow_html=True)

    resume_file = st.file_uploader(
        "Choose file",
        type=["pdf", "txt", "doc", "docx"],
        label_visibility="collapsed",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # User ID + manual inputs
    st.markdown("""
    <div style="background:#ffffff;border-radius:12px;border:1px solid #eceef1;
                padding:1.5rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
      <div style="font-family:Manrope,sans-serif;font-size:14px;font-weight:700;
                  color:#191c1e;margin-bottom:1rem;display:flex;align-items:center;gap:0.5rem;">
        <span class="material-symbols-outlined" style="font-size:1.125rem;color:#00425e;">person</span>
        Profile Details
      </div>
    """, unsafe_allow_html=True)

    user_id = st.text_input("User ID", placeholder="Unique identifier for your profile")
    skills_raw = st.text_area(
        "Manual Skills",
        placeholder="Python, React, SQL, …",
        height=100,
    )
    tags_raw = st.text_area(
        "Interest Tags",
        placeholder="data science, design, finance, …",
        height=80,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # Education placeholder card
    st.markdown("""
    <div style="background:#ffffff;border-radius:12px;border:1px solid #eceef1;
                padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
      <div style="font-family:Manrope,sans-serif;font-size:14px;font-weight:700;
                  color:#191c1e;margin-bottom:0.75rem;display:flex;align-items:center;gap:0.5rem;">
        <span class="material-symbols-outlined" style="font-size:1.125rem;color:#40484e;">school</span>
        Education
      </div>
      <p style="font-family:Inter,sans-serif;font-size:12px;color:#70787e;margin:0;">
        Education details will be extracted automatically from your resume.
      </p>
    </div>
    """, unsafe_allow_html=True)

with right_col:
    # Skills viz card
    st.markdown("""
    <div style="background:#ffffff;border-radius:12px;border:1px solid #eceef1;
                padding:1.5rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
      <div style="font-family:Manrope,sans-serif;font-size:14px;font-weight:700;
                  color:#191c1e;margin-bottom:0.75rem;display:flex;align-items:center;gap:0.5rem;">
        <span class="material-symbols-outlined" style="font-size:1.125rem;color:#006a6a;">auto_awesome</span>
        Extracted Skills
      </div>
    """, unsafe_allow_html=True)

    # Show previously extracted skills from session state
    if "extracted_skills" in st.session_state and st.session_state.extracted_skills:
        skills_display = st.session_state.extracted_skills
        chips_html = "".join(
            f'<span class="ch-chip ch-chip-teal">{s}</span>'
            for s in skills_display
        )
        st.markdown(
            f'<div style="margin-bottom:0.5rem;">{chips_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("""
      <div style="background:#f8f9fd;border-radius:8px;padding:2rem;text-align:center;">
        <span class="material-symbols-outlined" style="font-size:2rem;color:#c0c7ce;">
          manage_search
        </span>
        <p style="font-family:Inter,sans-serif;font-size:12px;color:#70787e;margin-top:0.5rem;margin-bottom:0;">
          Upload a resume to automatically extract skills.
        </p>
      </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Experience / profile overview card
    st.markdown("""
    <div style="background:#ffffff;border-radius:12px;border:1px solid #eceef1;
                padding:1.5rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
      <div style="font-family:Manrope,sans-serif;font-size:14px;font-weight:700;
                  color:#191c1e;margin-bottom:0.75rem;display:flex;align-items:center;gap:0.5rem;">
        <span class="material-symbols-outlined" style="font-size:1.125rem;color:#00425e;">work_history</span>
        Profile Overview
      </div>
    """, unsafe_allow_html=True)

    if "profile_data" in st.session_state and st.session_state.profile_data:
        pd = st.session_state.profile_data
        tags = pd.get("interest_tags", [])
        jobs = pd.get("phase1_job_suggestions", [])
        if tags:
            chips_html = "".join(
                f'<span class="ch-chip ch-chip-blue">{t}</span>'
                for t in tags[:8]
            )
            st.markdown(
                '<div style="font-family:Inter,sans-serif;font-size:11px;font-weight:700;'
                'text-transform:uppercase;letter-spacing:0.12em;color:#40484e;margin-bottom:0.5rem;">'
                'Interest Tags</div>',
                unsafe_allow_html=True,
            )
            st.markdown(f'<div style="margin-bottom:1rem;">{chips_html}</div>', unsafe_allow_html=True)
        if jobs:
            st.markdown(
                '<div style="font-family:Inter,sans-serif;font-size:11px;font-weight:700;'
                'text-transform:uppercase;letter-spacing:0.12em;color:#40484e;margin-bottom:0.5rem;">'
                'Suggested Jobs</div>',
                unsafe_allow_html=True,
            )
            for j in jobs[:5]:
                st.markdown(
                    f'<div style="font-family:Inter,sans-serif;font-size:13px;color:#191c1e;'
                    f'padding:0.35rem 0;border-bottom:1px solid #f2f4f7;">{j}</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.markdown("""
      <p style="font-family:Inter,sans-serif;font-size:12px;color:#70787e;margin:0;">
        Create a profile to see your interest tags and suggested roles.
      </p>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Action buttons
    if st.button("Create Profile", type="primary", use_container_width=True):
        if user_id.strip():
            profile = create_user_profile(
                user_id=user_id.strip(),
                manual_skills=collect_manual_skills(skills_raw),
                interest_tags=collect_interest_tags(tags_raw),
            )
            profile["phase1_job_suggestions"] = suggest_jobs_from_interest_tags(
                profile["interest_tags"],
                load_job_titles_from_onet(),
            )
            st.session_state["profile_data"] = profile
            st.session_state["user_id"] = user_id.strip()
            st.success("Profile created successfully.")
        else:
            st.error("Please enter a User ID.")

# ── Resume processing ─────────────────────────────────────────────────────────

if resume_file is not None and user_id.strip():
    meta = upload_resume(resume_file.name, resume_file.read(), user_id.strip())
    st.info(f"Resume saved — {meta['size_bytes']:,} bytes")

    with st.spinner("Extracting skills from resume…"):
        result = process_resume(meta["saved_path"])

    if result.method == "error":
        st.warning(f"Skill extraction failed: {result.error}")
    else:
        method_label = "AI (Claude)" if result.method == "llm" else "Rule-based"
        st.success(f"Extracted {len(result.skills)} skills via {method_label}")

        if result.skills:
            st.session_state["extracted_skills"] = result.skills
            merge_resume_skills(user_id.strip(), result.skills)

            chips_html = "".join(
                f'<span class="ch-chip ch-chip-teal">{s}</span>'
                for s in result.skills
            )
            st.markdown(
                '<span class="ch-section">Extracted Skills</span>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="background:#ffffff;border-radius:12px;border:1px solid #eceef1;'
                f'padding:1.25rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">{chips_html}</div>',
                unsafe_allow_html=True,
            )
