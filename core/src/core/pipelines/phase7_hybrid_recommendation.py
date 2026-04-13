"""Phase 7 — Hybrid job recommendation with explainability.

Combines three signals with dynamic weights:
    final_score = w_ability * ability_sim
                + w_activity * activity_sim
                + w_skill    * skill_sim

Explainability is powered by the O*NET Abilities → Work Activities crosswalk:
instead of exposing raw cognitive ability names, every match surfaces the
*work activities* that the user's abilities support — e.g. "Analyzing Data
or Information" rather than "Deductive Reasoning".

Public API
----------
HybridRecommender
    Load-once object.  Call recommend() for a ranked list with explanations.

RecommendationResult
    Per-job result dataclass with scores + activity explanations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process
from scipy.stats import norm
from sklearn.metrics.pairwise import cosine_similarity

from .phase6_skill_matching import build_tech_matrix, compute_skill_similarity

_ARCHIVE = Path(__file__).resolve().parents[4] / "Archive"
_NCPT_PATH = Path(__file__).resolve().parents[4] / "person_abilities_ncpt.csv"

_ABILITIES = [
    "Deductive Reasoning",
    "Mathematical Reasoning",
    "Memorization",
    "Perceptual Speed",
    "Problem Sensitivity",
    "Selective Attention",
    "Speed of Closure",
    "Time Sharing",
    "Written Comprehension",
]

# Maps MongoDB snake_case keys → Title Case ability names
_ABILITIES_SNAKE: Dict[str, str] = {
    a.lower().replace(" ", "_"): a for a in _ABILITIES
}

DEFAULT_WEIGHTS: Dict[str, float] = {
    "ability": 0.4,
    "activity": 0.3,
    "skill": 0.3,
}


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class RecommendationResult:
    """Per-job recommendation with score breakdown and activity explanations."""
    rank: int
    job_title: str
    total_score: float
    ability_score: float
    activity_score: float
    skill_score: float
    # Work activities the user's abilities support for this role
    strength_activities: List[str] = field(default_factory=list)
    # Work activities where the user has the largest gap vs job requirement
    gap_activities: List[str] = field(default_factory=list)
    # Per-ability comparison: user percentile vs O*NET job-requirement percentile
    ability_breakdown: List[Dict] = field(default_factory=list)


# ── Data loaders ─────────────────────────────────────────────────────────────

def _load_ja_pivot(archive: Path) -> pd.DataFrame:
    """Job × ability z-score matrix."""
    return pd.read_csv(archive / "job_abilities_matrix.csv", index_col=0)


def _load_wa_final(archive: Path) -> pd.DataFrame:
    """Job × work-activity score matrix (pivoted from long format)."""
    wa_long = pd.read_csv(archive / "workactivity_job.csv", index_col=0)
    return wa_long.pivot_table(
        index="Title",
        columns="Element Name",
        values="activity_score",
        fill_value=0.0,
    )


def _load_atwa_matrix(archive: Path, abilities: List[str]) -> pd.DataFrame:
    """Binary ability × work-activity crosswalk matrix.

    Rows = abilities, columns = work activities, values = 0/1.
    """
    atwa = pd.read_csv(archive / "Abilities to Work Activities.csv")
    matrix = (
        atwa
        .assign(value=1)
        .pivot_table(
            index="Abilities Element Name",
            columns="Work Activities Element Name",
            values="value",
            fill_value=0,
        )
    )
    # Keep only our 9 tested abilities
    present = [a for a in abilities if a in matrix.index]
    return matrix.loc[present]


# ── Fuzzy job name resolver ───────────────────────────────────────────────────

def _find_best_job(job_name: str, job_index: pd.Index) -> str:
    """Resolve a free-text job name to the closest O*NET title."""
    name_lower = job_name.lower()
    for job in job_index:
        if job.lower() == name_lower:
            return job
    for job in job_index:
        if name_lower in job.lower():
            return job
    match = process.extractOne(job_name, list(job_index),
                               scorer=fuzz.token_sort_ratio)
    return match[0] if match else job_index[0]


# ── Recommender ───────────────────────────────────────────────────────────────

class HybridRecommender:
    """Load-once recommender.  Instantiate once, call recommend() many times.

    Parameters
    ----------
    archive_dir : str | None
        Path to the Archive folder containing O*NET CSVs.
        Defaults to ``<repo_root>/Archive``.

    Example
    -------
    >>> rec = HybridRecommender()
    >>> results = rec.recommend(
    ...     ability_percentiles={"Deductive Reasoning": 80, "Memorization": 55, ...},
    ...     user_skills=["Python", "SQL", "TensorFlow"],
    ...     weights={"ability": 0.5, "activity": 0.3, "skill": 0.2},
    ... )
    >>> results[0].job_title
    'Data Scientists'
    """

    def __init__(self, archive_dir: Optional[str] = None) -> None:
        archive = Path(archive_dir) if archive_dir else _ARCHIVE

        self.ja_pivot = _load_ja_pivot(archive)
        self.wa_final = _load_wa_final(archive)
        self.atwa_matrix = _load_atwa_matrix(archive, _ABILITIES)
        self.tech_matrix = build_tech_matrix(str(archive / "Technology Skills.csv"))

        # Common job set across all three matrices
        common = (
            self.ja_pivot.index
            .intersection(self.wa_final.index)
            .intersection(self.tech_matrix.index)
        )
        self.ja_pivot = self.ja_pivot.loc[common]
        self.wa_final = self.wa_final.loc[common]
        self.tech_matrix = self.tech_matrix.loc[common]

    # ── Public API ────────────────────────────────────────────────────────────

    def recommend(
        self,
        ability_percentiles: Dict[str, float],
        user_skills: List[str],
        weights: Optional[Dict[str, float]] = None,
        top_n: int = 10,
        top_k_activities: int = 3,
        job_filter: Optional[List[str]] = None,
    ) -> List[RecommendationResult]:
        """Rank all jobs and return the top-N with explanations.

        Parameters
        ----------
        ability_percentiles : dict
            NCPT-normalised percentiles (0–100) per ability, from AbilityProfile.
        user_skills : list[str]
            Combined resume_skills + manual_skills (lowercased strings).
        weights : dict | None
            ``{"ability": float, "activity": float, "skill": float}``.
            Values are normalised to sum to 1.  Defaults to 0.4 / 0.3 / 0.3.
        top_n : int
            Number of jobs to return.
        top_k_activities : int
            Number of work activities to surface per job explanation.
        """
        w = _normalise_weights(weights or DEFAULT_WEIGHTS)

        # Restrict scoring to a subset of jobs if a filter is provided
        if job_filter is not None:
            valid = [j for j in job_filter if j in self.ja_pivot.index]
            ja_pivot = self.ja_pivot.loc[valid]
            wa_final = self.wa_final.reindex(valid).fillna(0)
            tech_matrix = self.tech_matrix.reindex(valid).fillna(0)
        else:
            ja_pivot = self.ja_pivot
            wa_final = self.wa_final
            tech_matrix = self.tech_matrix

        user_z = self._percentiles_to_z(ability_percentiles)
        ability_sims = self._ability_similarity(user_z, ja_pivot)
        activity_sims = self._activity_similarity(user_z, wa_final)
        skill_sims = compute_skill_similarity(user_skills, tech_matrix)

        # Align all three series on the common job index
        idx = ja_pivot.index
        ability_sims = ability_sims.reindex(idx).fillna(0)
        activity_sims = activity_sims.reindex(idx).fillna(0)
        skill_sims = skill_sims.reindex(idx).fillna(0)

        final = (
            w["ability"] * ability_sims
            + w["activity"] * activity_sims
            + w["skill"] * skill_sims
        )

        top_jobs = final.nlargest(top_n)

        # Pre-build normalised percentiles (Title Case keys, 0–100)
        norm_percentiles = _normalise_percentile_keys(ability_percentiles)

        results: List[RecommendationResult] = []
        for rank, (job_title, score) in enumerate(top_jobs.items(), start=1):
            strengths, gaps = self._explain(job_title, user_z, top_k_activities)
            breakdown = self._ability_breakdown(norm_percentiles)
            results.append(RecommendationResult(
                rank=rank,
                job_title=job_title,
                total_score=round(float(score), 4),
                ability_score=round(float(ability_sims[job_title]), 4),
                activity_score=round(float(activity_sims[job_title]), 4),
                skill_score=round(float(skill_sims[job_title]), 4),
                strength_activities=strengths,
                gap_activities=gaps,
                ability_breakdown=breakdown,
            ))

        return results

    def explain_job(
        self,
        job_name: str,
        ability_percentiles: Dict[str, float],
        top_k: int = 5,
    ) -> Dict:
        """Detailed match breakdown for a specific job title.

        Returns strengths, gaps, match percent, and top work activities
        for the job — all expressed as work activities, not raw ability names.
        """
        job_title = _find_best_job(job_name, self.wa_final.index)
        user_z = self._percentiles_to_z(ability_percentiles)

        # --- user activity profile ---
        atwa = self.atwa_matrix.reindex(_ABILITIES).fillna(0)
        user_vec = pd.Series(user_z).reindex(atwa.index).fillna(0)
        user_activity = atwa.T.dot(user_vec)

        # --- job activity profile ---
        if job_title not in self.wa_final.index:
            return {"job": job_title, "error": "No activity data for this job."}

        job_activity = self.wa_final.loc[job_title].fillna(0)
        common = user_activity.index.intersection(job_activity.index)
        user_activity = user_activity.loc[common]
        job_activity = job_activity.loc[common]

        # Normalise to [0, 1] range
        ua_norm = user_activity / (user_activity.abs().max() + 1e-6)
        ja_norm = job_activity / (job_activity.abs().max() + 1e-6)

        # Strengths: activities where user capacity × job requirement is highest
        strengths = (ua_norm * ja_norm).nlargest(top_k).index.tolist()

        # Gaps: activities where job requirement >> user capacity
        activity_counts = self.atwa_matrix.sum(axis=0).reindex(common).replace(0, 1)
        ua_scaled = user_activity / activity_counts.values
        ua_scaled = ua_scaled / (ua_scaled.abs().max() + 1e-6)
        gaps_series = ja_norm * (ja_norm - ua_scaled)
        gaps = gaps_series.nlargest(top_k).index.tolist()

        sim = cosine_similarity(
            user_activity.values.reshape(1, -1),
            job_activity.values.reshape(1, -1),
        )[0][0]
        match_pct = round((sim + 1) / 2 * 100, 1)

        top_job_activities = job_activity.nlargest(top_k).index.tolist()

        return {
            "job": job_title,
            "match_percent": match_pct,
            "strength_activities": strengths,
            "gap_activities": gaps,
            "top_job_activities": top_job_activities,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _percentiles_to_z(self, percentiles: Dict[str, float]) -> Dict[str, float]:
        """Convert NCPT percentiles (0–100) → standard normal z-scores.

        Accepts keys in either Title Case or snake_case format.
        """
        normalised = _normalise_percentile_keys(percentiles)
        z: Dict[str, float] = {}
        for ability in _ABILITIES:
            p = normalised.get(ability, 50.0)
            p_clipped = max(0.5, min(99.5, p))  # avoid ±inf at boundaries
            z[ability] = float(norm.ppf(p_clipped / 100.0))
        return z

    def _ability_breakdown(self, norm_percentiles: Dict[str, float]) -> List[Dict]:
        """User's NCPT percentile per ability (0–100 from the assessment)."""
        return [
            {"ability": ability, "user_pct": round(norm_percentiles.get(ability, 50.0), 1)}
            for ability in _ABILITIES
        ]

    def _ability_similarity(self, user_z: Dict[str, float], ja_pivot: pd.DataFrame) -> pd.Series:
        user_vec = np.array([user_z.get(a, 0.0) for a in ja_pivot.columns])
        sims = cosine_similarity(user_vec.reshape(1, -1), ja_pivot.values)[0]
        return pd.Series(sims, index=ja_pivot.index)

    def _activity_similarity(self, user_z: Dict[str, float], wa_final: pd.DataFrame) -> pd.Series:
        atwa = self.atwa_matrix.reindex(_ABILITIES).fillna(0)
        user_vec = pd.Series(user_z).reindex(atwa.index).fillna(0)
        user_activity = atwa.T.dot(user_vec)

        common_acts = user_activity.index.intersection(wa_final.columns)
        if common_acts.empty:
            return pd.Series(0.0, index=wa_final.index)

        u = user_activity.loc[common_acts].values.reshape(1, -1)
        J = wa_final[common_acts].values
        sims = cosine_similarity(u, J)[0]
        return pd.Series(sims, index=wa_final.index)

    def _explain(
        self,
        job_title: str,
        user_z: Dict[str, float],
        top_k: int,
    ):
        """Return (strength_activities, gap_activities) for one job."""
        if job_title not in self.wa_final.index:
            return [], []

        atwa = self.atwa_matrix.reindex(_ABILITIES).fillna(0)
        user_vec = pd.Series(user_z).reindex(atwa.index).fillna(0)
        user_activity = atwa.T.dot(user_vec)
        job_activity = self.wa_final.loc[job_title].fillna(0)

        common = user_activity.index.intersection(job_activity.index)
        ua = user_activity.loc[common]
        ja = job_activity.loc[common]

        strengths = (ua * ja).nlargest(top_k).index.tolist()
        gaps = (ja * (ja - ua)).nlargest(top_k).index.tolist()
        return strengths, gaps


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_percentile_keys(percentiles: Dict[str, float]) -> Dict[str, float]:
    """Return a copy of *percentiles* with all keys normalised to Title Case.

    Supports both Title Case (``"Deductive Reasoning"``) and snake_case
    (``"deductive_reasoning"``) input so that MongoDB-stored profiles and
    in-memory profiles are both handled correctly.
    """
    result: Dict[str, float] = {}
    for k, v in percentiles.items():
        title_key = _ABILITIES_SNAKE.get(k, k)
        result[title_key] = v
    return result


def _normalise_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Ensure ability/activity/skill weights sum to 1.0."""
    keys = ["ability", "activity", "skill"]
    total = sum(weights.get(k, 0.0) for k in keys)
    if total == 0:
        return DEFAULT_WEIGHTS.copy()
    return {k: weights.get(k, 0.0) / total for k in keys}
