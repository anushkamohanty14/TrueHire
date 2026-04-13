"""Cognitive ability scoring pipeline.

Converts a list of TaskResponse objects into an AbilityProfile whose
scores are **NCPT-normalised percentiles** (0–100).

Pipeline
--------
1. Group TaskResponses by ability.
2. Per ability compute a composite score [0, 1]:
       composite = 0.7 × accuracy_mean  +  0.3 × speed_mean
   where
       accuracy_mean = fraction of responses with is_correct == True
       speed_mean    = mean of  1 / (1 + rt_ms / RT_HALF_LIFE_MS)
                       (RT_HALF_LIFE_MS = 10 000 ms → speed = 0.5 at 10 s)
3. Map composite [0, 1] → pseudo-z-score:
       z = (composite − 0.5) × 6         →  z ∈ [−3, +3]
4. Find the percentile of z in the NCPT empirical distribution for that
   ability using scipy.stats.percentileofscore (kind="rank").
   Result is a float in [0, 100].

AbilityProfile is the canonical data object consumed by all downstream
pipelines (job matching, skill gap analysis, interview question selection).
Never pass raw composites to those pipelines; always use percentiles.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

from .tasks.base import ABILITIES, TaskResponse

# ── Constants ─────────────────────────────────────────────────────────────────

# Half-life for reaction-time speed scoring (ms).
# A response at exactly RT_HALF_LIFE_MS receives speed_score = 0.5.
RT_HALF_LIFE_MS: float = 10_000.0

# Accuracy weight in the composite formula.
ACCURACY_WEIGHT: float = 0.7
SPEED_WEIGHT: float = 0.3

# Multiplier that converts composite [0,1] → pseudo-z-score.
# Maps: composite=0 → z=−3,  composite=0.5 → z=0,  composite=1 → z=+3.
Z_SCALE: float = 6.0

# Default path to the NCPT reference dataset (relative to repo root).
_REPO_ROOT = Path(__file__).resolve().parents[3]  # core/src/core/ → repo root
DEFAULT_NCPT_PATH = str(_REPO_ROOT / "person_abilities_ncpt.csv")

# Column name mapping: snake_case ability → NCPT CSV header
NCPT_COLUMN: Dict[str, str] = {
    "deductive_reasoning":    "Deductive Reasoning",
    "mathematical_reasoning": "Mathematical Reasoning",
    "memorization":           "Memorization",
    "perceptual_speed":       "Perceptual Speed",
    "problem_sensitivity":    "Problem Sensitivity",
    "selective_attention":    "Selective Attention",
    "speed_of_closure":       "Speed of Closure",
    "time_sharing":           "Time Sharing",
    "written_comprehension":  "Written Comprehension",
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class AbilityProfile:
    """Canonical user ability representation for all downstream pipelines.

    All downstream logic (job matching, skill gap, interview selection)
    MUST consume ``ability_percentiles``, not ``ability_composites``.

    Attributes
    ----------
    user_id : str
        Opaque user identifier.
    ability_percentiles : Dict[str, float]
        NCPT-normalised percentile per ability.  Range: 0–100.
        Only abilities that were assessed appear here.
    ability_composites : Dict[str, float]
        Raw composite score per ability.  Range: 0–1.
        Retained for diagnostics / audit only.
    assessed_at : datetime
        UTC timestamp of when the profile was generated.
    """
    user_id: str
    ability_percentiles: Dict[str, float]
    ability_composites: Dict[str, float]
    assessed_at: datetime = field(default_factory=datetime.utcnow)

    def percentile_vector(self, ability_order: Optional[List[str]] = None) -> List[float]:
        """Return percentiles as an ordered list (0–100), defaulting to ABILITIES order.

        Abilities not present in the profile are filled with 50.0 (population median).
        """
        order = ability_order or ABILITIES
        return [self.ability_percentiles.get(ab, 50.0) for ab in order]


# ── Scoring engine ────────────────────────────────────────────────────────────

class ScoringEngine:
    """Converts a list of TaskResponse objects into an AbilityProfile.

    Parameters
    ----------
    ncpt_path : str | None
        Path to ``person_abilities_ncpt.csv``.  Defaults to the repo-root copy.

    Usage
    -----
    >>> engine = ScoringEngine()
    >>> profile = engine.score_session(user_id="u001", responses=task_responses)
    >>> profile.ability_percentiles
    {'deductive_reasoning': 72.3, 'memorization': 55.1, ...}
    """

    def __init__(self, ncpt_path: Optional[str] = None) -> None:
        path = ncpt_path or DEFAULT_NCPT_PATH
        df = pd.read_csv(path)
        # Pre-extract sorted numpy arrays per ability for fast percentile lookup
        self._ncpt: Dict[str, np.ndarray] = {}
        for ability, col in NCPT_COLUMN.items():
            if col in df.columns:
                values = df[col].dropna().to_numpy(dtype=float)
                self._ncpt[ability] = np.sort(values)

    # ── Public API ────────────────────────────────────────────────────────────

    def score_session(
        self,
        user_id: str,
        responses: List[TaskResponse],
    ) -> AbilityProfile:
        """Full pipeline: TaskResponses → AbilityProfile with NCPT percentiles."""
        composites = self.compute_composites(responses)
        percentiles = {
            ab: self.composite_to_percentile(ab, c)
            for ab, c in composites.items()
        }
        return AbilityProfile(
            user_id=user_id,
            ability_percentiles=percentiles,
            ability_composites=composites,
        )

    def compute_composites(
        self,
        responses: List[TaskResponse],
    ) -> Dict[str, float]:
        """Compute per-ability composite scores in [0, 1].

        composite = ACCURACY_WEIGHT × accuracy_mean
                  + SPEED_WEIGHT    × speed_mean

        Only abilities with at least one response are included.
        """
        grouped: Dict[str, List[TaskResponse]] = {}
        for r in responses:
            grouped.setdefault(r.task_item.ability, []).append(r)

        composites: Dict[str, float] = {}
        for ability, rlist in grouped.items():
            accuracy_mean = float(np.mean([r.is_correct for r in rlist]))
            speed_mean = float(np.mean([_speed_score(r.reaction_time_ms) for r in rlist]))
            composites[ability] = (
                ACCURACY_WEIGHT * accuracy_mean + SPEED_WEIGHT * speed_mean
            )
        return composites

    def composite_to_percentile(self, ability: str, composite: float) -> float:
        """Map a composite score [0, 1] to an NCPT percentile [0, 100].

        Steps:
          1. composite → pseudo-z-score via linear scaling.
          2. Percentile of z in the NCPT empirical CDF for that ability.
        """
        z = (composite - 0.5) * Z_SCALE
        ncpt_values = self._ncpt.get(ability)
        if ncpt_values is None or len(ncpt_values) == 0:
            # Fallback: use standard normal CDF if no NCPT data for this ability
            from scipy.stats import norm
            return float(norm.cdf(z) * 100.0)
        return float(percentileofscore(ncpt_values, z, kind="rank"))

    def onet_score_to_percentile(self, ability: str, onet_z: float) -> float:
        """Convert an O*NET ability z-score to an NCPT percentile [0, 100].

        O*NET job-requirement scores are on the same z-score scale as NCPT,
        so we can look them up in the same NCPT empirical CDF.
        This lets downstream matching compare user_percentile vs job_percentile
        on a common scale.
        """
        ncpt_values = self._ncpt.get(ability)
        if ncpt_values is None or len(ncpt_values) == 0:
            from scipy.stats import norm
            return float(norm.cdf(onet_z) * 100.0)
        return float(percentileofscore(ncpt_values, onet_z, kind="rank"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _speed_score(rt_ms: float) -> float:
    """Convert reaction time (ms) to a speed score in (0, 1].

    Uses a harmonic decay: speed = 1 / (1 + rt_ms / RT_HALF_LIFE_MS).
    Returns 1.0 for instantaneous responses and approaches 0 for very slow ones.
    """
    if rt_ms <= 0:
        return 1.0
    return 1.0 / (1.0 + rt_ms / RT_HALF_LIFE_MS)
