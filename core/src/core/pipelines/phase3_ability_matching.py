"""Phase 3 — Ability matching pipeline.

All matching is performed on **NCPT-normalised percentile scores** (0–100).
Raw composites are intentionally not exposed here; consume AbilityProfile
from core.src.core.scoring instead.

Public API
----------
build_job_percentile_matrix(engine, onet_rows)
    Convert O*NET job z-scores → percentile matrix using the same NCPT
    reference distribution as user scores.

match_user_to_jobs(profile, job_percentile_matrix, ability_order)
    Cosine similarity of user percentile vector vs each job percentile vector.
    Returns a ranked list of (job_title, similarity_score).

compute_skill_gaps(profile, job_percentile_matrix, job_title)
    Per-ability gap = job_percentile − user_percentile.
    Positive values indicate abilities where the user is below the job requirement.
"""
from __future__ import annotations

from math import sqrt
from typing import Dict, Iterable, List, Optional, Tuple

from ..scoring import AbilityProfile, ScoringEngine
from ..tasks.base import ABILITIES

# ── Job percentile matrix ─────────────────────────────────────────────────────

# O*NET column names  →  snake_case ability key
_ONET_COLUMN: Dict[str, str] = {
    "Deductive Reasoning":    "deductive_reasoning",
    "Mathematical Reasoning": "mathematical_reasoning",
    "Memorization":           "memorization",
    "Perceptual Speed":       "perceptual_speed",
    "Problem Sensitivity":    "problem_sensitivity",
    "Selective Attention":    "selective_attention",
    "Speed of Closure":       "speed_of_closure",
    "Time Sharing":           "time_sharing",
    "Written Comprehension":  "written_comprehension",
}


def build_job_percentile_matrix(
    engine: ScoringEngine,
    onet_rows: List[Dict],
) -> Dict[str, Dict[str, float]]:
    """Convert O*NET ability z-scores to NCPT percentiles for every job.

    Parameters
    ----------
    engine : ScoringEngine
        Initialised scoring engine (holds the NCPT reference distributions).
    onet_rows : list of dicts
        Cleaned rows from ``phase1_onet_data.clean_onet_data()``.

    Returns
    -------
    Dict[job_title, Dict[ability, percentile]]
        Percentile requirements (0–100) per job, per ability.
    """
    matrix: Dict[str, Dict[str, float]] = {}
    for row in onet_rows:
        title = row.get("Title", "").strip()
        if not title:
            continue
        pcts: Dict[str, float] = {}
        for col, ability in _ONET_COLUMN.items():
            raw = row.get(col)
            if raw is not None:
                try:
                    pcts[ability] = engine.onet_score_to_percentile(ability, float(raw))
                except (TypeError, ValueError):
                    pass
        matrix[title] = pcts
    return matrix


# ── Job matching ──────────────────────────────────────────────────────────────

def match_user_to_jobs(
    profile: AbilityProfile,
    job_percentile_matrix: Dict[str, Dict[str, float]],
    ability_order: Optional[List[str]] = None,
) -> List[Tuple[str, float]]:
    """Rank jobs by cosine similarity of percentile vectors.

    Both user and job vectors are normalised to [0, 1] (divide by 100)
    before computing cosine similarity so the scale is consistent.

    Parameters
    ----------
    profile : AbilityProfile
        User ability profile with NCPT percentiles.
    job_percentile_matrix : dict
        Output of ``build_job_percentile_matrix``.
    ability_order : list[str] | None
        Ordered list of ability keys to use.  Defaults to ABILITIES.

    Returns
    -------
    List of (job_title, cosine_similarity) sorted descending.
    """
    order = ability_order or ABILITIES
    user_vec = [profile.ability_percentiles.get(ab, 50.0) / 100.0 for ab in order]
    results: List[Tuple[str, float]] = []
    for title, pcts in job_percentile_matrix.items():
        job_vec = [pcts.get(ab, 50.0) / 100.0 for ab in order]
        results.append((title, _cosine(user_vec, job_vec)))
    return sorted(results, key=lambda x: x[1], reverse=True)


def compute_skill_gaps(
    profile: AbilityProfile,
    job_percentile_matrix: Dict[str, Dict[str, float]],
    job_title: str,
) -> Dict[str, float]:
    """Return per-ability gaps between job requirement and user percentile.

    gap = job_percentile − user_percentile

    Positive gap  → user is below the job requirement for that ability.
    Negative gap  → user exceeds the job requirement.
    Zero          → exact match.

    Only abilities present in both the profile and the job are included.
    """
    job_pcts = job_percentile_matrix.get(job_title, {})
    gaps: Dict[str, float] = {}
    for ability in ABILITIES:
        if ability in profile.ability_percentiles and ability in job_pcts:
            gaps[ability] = job_pcts[ability] - profile.ability_percentiles[ability]
    return gaps


def build_user_ability_vector(
    scores: Dict[str, float],
    ability_order: Iterable[str],
) -> List[float]:
    """Build an ordered vector from a scores dict.

    Accepts any numeric scores dict (e.g. percentiles or raw values).
    Missing abilities default to 0.0.
    """
    return [float(scores.get(name, 0.0)) for name in ability_order]


def compute_ability_similarity(
    user_vector: List[float],
    job_matrix: Dict[str, List[float]],
) -> List[Tuple[str, float]]:
    """Cosine similarity of a user vector against each job vector.

    Works with any numeric vectors (percentile-based recommended).
    """
    scores = [(job, _cosine(user_vector, vec)) for job, vec in job_matrix.items()]
    return sorted(scores, key=lambda x: x[1], reverse=True)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a))
    nb = sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
