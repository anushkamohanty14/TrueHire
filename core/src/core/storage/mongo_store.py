"""MongoDB-backed user profile store.

Reads connection details from environment variables (loaded from .env):
    MONGODB_URI  — Atlas connection string
    MONGODB_DB   — database name (default: career_recommender)

Implements the same interface as JsonUserStore so it can be swapped in
anywhere JsonUserStore is used.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection

load_dotenv()


def _get_collection() -> Collection:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise EnvironmentError("MONGODB_URI is not set. Add it to your .env file.")
    db_name = os.environ.get("MONGODB_DB", "career_recommender")
    client = MongoClient(uri)
    return client[db_name]["user_profiles"]


def _get_auth_collection() -> Collection:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise EnvironmentError("MONGODB_URI is not set. Add it to your .env file.")
    db_name = os.environ.get("MONGODB_DB", "career_recommender")
    return MongoClient(uri)[db_name]["auth_users"]


class MongoUserStore:
    """MongoDB-backed profile store (production)."""

    def __init__(self) -> None:
        self._col: Collection = _get_collection()

    # ── Profile ───────────────────────────────────────────────────────────────

    def upsert_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update a user profile using $set — preserves assessment_history."""
        user_id = profile["user_id"]
        fields = {k: v for k, v in profile.items() if k != "user_id"}
        self._col.update_one(
            {"user_id": user_id},
            {"$set": fields},
            upsert=True,
        )
        return profile

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Return the stored profile (excluding history arrays) or None."""
        doc = self._col.find_one(
            {"user_id": user_id},
            {"_id": 0, "assessment_history": 0},
        )
        return doc or None

    # ── Cognitive assessment ──────────────────────────────────────────────────

    def save_assessment(
        self,
        user_id: str,
        ability_percentiles: Dict[str, float],
        readiness_score: float,
        task_responses: List[Dict[str, Any]],
    ) -> None:
        """Store latest scores and append a timestamped history entry."""
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "taken_at": now,
            "readiness_score": round(readiness_score, 2),
            "ability_percentiles": ability_percentiles,
            "task_responses": task_responses,
        }
        self._col.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "ability_percentiles": ability_percentiles,
                    "readiness_score": round(readiness_score, 2),
                    "latest_assessment_at": now,
                },
                "$push": {"assessment_history": entry},
                "$setOnInsert": {
                    "user_id": user_id,
                    "manual_skills": [],
                    "interest_tags": [],
                    "resume_skills": [],
                    "phase1_job_suggestions": [],
                },
            },
            upsert=True,
        )

    def get_assessment_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Return all past assessment attempts, newest first."""
        doc = self._col.find_one(
            {"user_id": user_id},
            {"_id": 0, "assessment_history": 1},
        )
        if not doc:
            return []
        return list(reversed(doc.get("assessment_history", [])))

    # ── Resume extraction ─────────────────────────────────────────────────────

    def save_resume_extraction(
        self,
        user_id: str,
        file_name: str,
        skills: List[str],
        education: List[str],
        certifications: List[str],
        experience_years: Optional[float],
        soft_skills: List[str] = None,
        past_job_titles: List[str] = None,
    ) -> None:
        """Overwrite the latest resume extraction for the user."""
        now = datetime.now(timezone.utc).isoformat()
        resume_doc = {
            "uploaded_at": now,
            "file_name": file_name,
            "skills": skills,
            "education": education,
            "certifications": certifications,
            "experience_years": experience_years,
            "soft_skills": soft_skills or [],
            "past_job_titles": past_job_titles or [],
        }
        self._col.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "latest_resume": resume_doc,
                    "resume_skills": skills,          # kept for backward compat
                    "resume_education": education,
                    "resume_certifications": certifications,
                    "resume_experience_years": experience_years,
                    "resume_soft_skills": soft_skills or [],
                    "resume_past_job_titles": past_job_titles or [],
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "manual_skills": [],
                    "interest_tags": [],
                    "phase1_job_suggestions": [],
                    "assessment_history": [],
                },
            },
            upsert=True,
        )

    # ── History snapshot ──────────────────────────────────────────────────────

    def get_user_snapshot(self, user_id: str) -> Dict[str, Any]:
        """Return the user's latest assessment + latest resume extraction."""
        doc = self._col.find_one(
            {"user_id": user_id},
            {"_id": 0, "assessment_history": 0},
        )
        if not doc:
            return {"user_id": user_id, "assessment": None, "resume": None}

        assessment: Optional[Dict[str, Any]] = None
        if doc.get("ability_percentiles"):
            assessment = {
                "taken_at": doc.get("latest_assessment_at"),
                "readiness_score": doc.get("readiness_score"),
                "ability_percentiles": doc.get("ability_percentiles", {}),
            }

        resume: Optional[Dict[str, Any]] = doc.get("latest_resume")

        return {
            "user_id": user_id,
            "assessment": assessment,
            "resume": resume,
        }

    # ── Interview context (LLM pipeline input) ────────────────────────────────

    def get_interview_context(self, user_id: str) -> Dict[str, Any]:
        """Return structured data ready for LLM interview pipeline injection.

        The returned dict contains:
        - ``cognitive_profile``: readiness score, per-ability percentiles,
          derived strengths and improvement areas.
        - ``technical_profile``: skills, education, certifications, experience.

        This is the single source of truth consumed by the interview pipeline.
        """
        snapshot = self.get_user_snapshot(user_id)
        assessment = snapshot.get("assessment") or {}
        resume = snapshot.get("resume") or {}

        ability_percentiles: Dict[str, float] = assessment.get("ability_percentiles", {})
        strengths = [ab for ab, pct in ability_percentiles.items() if pct >= 70]
        improvements = [ab for ab, pct in ability_percentiles.items() if pct < 40]

        # Human-readable ability labels for LLM prompts
        _labels = {
            "deductive_reasoning": "Deductive Reasoning",
            "mathematical_reasoning": "Mathematical Reasoning",
            "memorization": "Memorization",
            "perceptual_speed": "Perceptual Speed",
            "problem_sensitivity": "Problem Sensitivity",
            "selective_attention": "Selective Attention",
            "speed_of_closure": "Speed of Closure",
            "time_sharing": "Time Sharing",
            "written_comprehension": "Written Comprehension",
        }

        return {
            "user_id": user_id,
            "cognitive_profile": {
                "readiness_score": assessment.get("readiness_score"),
                "ability_percentiles": ability_percentiles,
                "strengths": [_labels.get(a, a) for a in strengths],
                "areas_for_improvement": [_labels.get(a, a) for a in improvements],
                "assessed_at": assessment.get("taken_at"),
            },
            "technical_profile": {
                "skills": resume.get("skills", []),
                "education": resume.get("education", []),
                "certifications": resume.get("certifications", []),
                "experience_years": resume.get("experience_years"),
                "resume_uploaded_at": resume.get("uploaded_at"),
            },
        }
