"""Phase 6 — Technology skill matching.

Builds a job × tech-skill matrix from O*NET Technology Skills data and
computes cosine similarity between a user's skill set and each job's
weighted technology profile.

Public API
----------
build_tech_matrix(csv_path)
    Load Technology Skills CSV → normalised job × skill DataFrame.

compute_skill_similarity(user_skills, tech_matrix)
    Binary user skill vector → cosine similarity per job (pd.Series).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

_DEFAULT_CSV = str(Path(__file__).resolve().parents[4] / "Archive" / "Technology Skills.csv")


# ── Weight helper (from notebook) ────────────────────────────────────────────

def _tech_weight(hot: str, demand: str) -> float:
    """Higher weight for technologies that are both hot and in demand."""
    if hot == "Y" and demand == "Y":
        return 2.0
    if hot == "Y" or demand == "Y":
        return 1.5
    return 1.0


# ── Matrix builder ────────────────────────────────────────────────────────────

def build_tech_matrix(csv_path: str = _DEFAULT_CSV) -> pd.DataFrame:
    """Load Technology Skills CSV and return a normalised job × skill matrix.

    Each cell is the weight of that technology for that job, normalised so
    each job's total weight sums to 1.0.

    Returns
    -------
    pd.DataFrame
        Index: job titles (str).
        Columns: technology names (str).
    """
    df = pd.read_csv(csv_path)
    df["weight"] = df.apply(
        lambda r: _tech_weight(str(r.get("Hot Technology", "N")),
                               str(r.get("In Demand", "N"))),
        axis=1,
    )

    # Aggregate duplicates (same job + same tech) by summing weights
    agg = df.groupby(["Title", "Example"])["weight"].sum().reset_index()

    # Pivot to job × skill matrix
    matrix = agg.pivot_table(index="Title", columns="Example",
                              values="weight", fill_value=0.0)

    # Normalise per job so total weight = 1
    row_sums = matrix.sum(axis=1).replace(0, 1)
    matrix = matrix.div(row_sums, axis=0)

    return matrix


# ── Skill similarity ──────────────────────────────────────────────────────────

def compute_skill_similarity(
    user_skills: List[str],
    tech_matrix: pd.DataFrame,
) -> pd.Series:
    """Cosine similarity between user skill set and each job's tech profile.

    Matching is case-insensitive and checks if the user skill appears as a
    substring of the O*NET technology name (handles abbreviations like
    "PyTorch" matching "PyTorch (Machine learning library)").

    Parameters
    ----------
    user_skills : list[str]
        Combined resume + manual skills.
    tech_matrix : pd.DataFrame
        Output of ``build_tech_matrix()``.

    Returns
    -------
    pd.Series
        Cosine similarity score per job title.  Range: [0, 1].
    """
    if tech_matrix.empty or not user_skills:
        return pd.Series(0.0, index=tech_matrix.index)

    cols_lower = {col: col.lower() for col in tech_matrix.columns}

    # Build binary user vector: 1.0 if user has that skill
    user_vec = np.zeros(len(tech_matrix.columns))
    for skill in user_skills:
        s_lower = skill.strip().lower()
        for i, col in enumerate(tech_matrix.columns):
            if s_lower in cols_lower[col] or cols_lower[col] in s_lower:
                user_vec[i] = 1.0

    if user_vec.sum() == 0:
        return pd.Series(0.0, index=tech_matrix.index)

    sims = cosine_similarity(user_vec.reshape(1, -1), tech_matrix.values)[0]
    return pd.Series(sims, index=tech_matrix.index)
