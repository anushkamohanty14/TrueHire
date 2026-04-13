"""Recommendations router.

GET /api/recommendations/{user_id}?industry=technology
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from core.src.core.pipelines.phase7_hybrid_recommendation import HybridRecommender
from core.src.core.storage.mongo_store import MongoUserStore
from core.src.core.industry_clusters import classify_title

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/{user_id}")
def get_recommendations(
    user_id: str,
    w_ability: float = 0.4,
    w_activity: float = 0.3,
    w_skill: float = 0.3,
    top_n: int = 10,
    industry: Optional[str] = Query(None),
    token: str = "",
) -> List[Dict[str, Any]]:
    """Return ranked job recommendations for a user, optionally filtered by industry."""
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

    # Filter job set to the requested industry before scoring
    job_filter: Optional[List[str]] = None
    if industry:
        all_titles = rec.ja_pivot.index.tolist()
        job_filter = [t for t in all_titles if classify_title(t) == industry]
        if not job_filter:
            return []

    results = rec.recommend(
        ability_percentiles=ability_percentiles,
        user_skills=user_skills,
        weights={"ability": w_ability, "activity": w_activity, "skill": w_skill},
        top_n=top_n,
        job_filter=job_filter,
    )

    return [
        {
            "rank": r.rank,
            "job_title": r.job_title,
            "total_score": r.total_score,
            "ability_score": r.ability_score,
            "activity_score": r.activity_score,
            "skill_score": r.skill_score,
            "strength_activities": r.strength_activities,
            "gap_activities": r.gap_activities,
            "ability_breakdown": r.ability_breakdown,
        }
        for r in results
    ]
