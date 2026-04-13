"""Skills gap router.

GET /api/skills/gaps/{user_id}?target_job=<job_title>
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from core.src.core.pipelines.phase6_skill_matching import build_tech_matrix, compute_skill_similarity
from core.src.core.pipelines.phase7_hybrid_recommendation import HybridRecommender
from core.src.core.storage.mongo_store import MongoUserStore

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("/gaps/{user_id}")
def get_skill_gaps(
    user_id: str,
    target_job: str = Query(..., description="Target job title"),
    token: str = "",
) -> Dict[str, Any]:
    """Return strength/gap activities and tech skill gaps for a target job."""
    store = MongoUserStore()
    profile = store.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    ability_percentiles: Dict[str, float] = profile.get("ability_percentiles", {})
    resume_skills: List[str] = profile.get("resume_skills", [])
    manual_skills: List[str] = profile.get("manual_skills", [])
    user_skills = list(set(resume_skills + manual_skills))

    if not ability_percentiles:
        raise HTTPException(
            status_code=422,
            detail="No ability scores found. Complete the cognitive assessment first.",
        )

    rec = HybridRecommender()
    explanation = rec.explain_job(target_job, ability_percentiles)

    # Tech skill gap analysis
    tech_matrix = build_tech_matrix()
    skill_sims = compute_skill_similarity(user_skills, tech_matrix)

    # Find missing skills for the target job
    tech_skill_gaps: List[str] = []
    skill_match_score: float = 0.0

    try:
        from rapidfuzz import fuzz, process as fuzz_process
        match = fuzz_process.extractOne(target_job, list(tech_matrix.index), scorer=fuzz.token_sort_ratio)
        if match:
            matched_job = match[0]
            job_skills_series = tech_matrix.loc[matched_job]
            top_job_skills = job_skills_series.nlargest(15).index.tolist()
            user_skills_lower = {s.strip().lower() for s in user_skills}
            for skill in top_job_skills:
                skill_lower = skill.lower()
                has_it = any(
                    u in skill_lower or skill_lower in u
                    for u in user_skills_lower
                )
                if not has_it:
                    tech_skill_gaps.append(skill)

            if matched_job in skill_sims.index:
                skill_match_score = round(float(skill_sims[matched_job]) * 100, 1)
    except Exception:
        pass

    return {
        "job_title": explanation.get("job", target_job),
        "match_percent": explanation.get("match_percent", 0.0),
        "strength_activities": explanation.get("strength_activities", []),
        "gap_activities": explanation.get("gap_activities", []),
        "top_job_activities": explanation.get("top_job_activities", []),
        "tech_skill_gaps": tech_skill_gaps[:10],
        "skill_match_score": skill_match_score,
    }
