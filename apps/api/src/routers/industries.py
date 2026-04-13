"""Industries router.

GET /api/industries  — list all industry buckets with job counts
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter

from core.src.core.industry_clusters import (
    ALL_INDUSTRIES,
    INDUSTRY_META,
    classify_titles,
)

router = APIRouter(prefix="/api/industries", tags=["industries"])

_MATRIX = Path(__file__).resolve().parents[4] / "Archive" / "job_abilities_matrix.csv"


def _job_counts() -> Dict[str, int]:
    titles = pd.read_csv(_MATRIX, index_col=0).index.tolist()
    mapping = classify_titles(titles)
    counts: Dict[str, int] = {ind: 0 for ind in ALL_INDUSTRIES}
    for industry in mapping.values():
        counts[industry] = counts.get(industry, 0) + 1
    return counts


@router.get("")
def list_industries() -> List[Dict[str, Any]]:
    """Return all industries with name, icon, and job count."""
    counts = _job_counts()
    return [
        {
            "id": ind_id,
            "name": INDUSTRY_META[ind_id]["name"],
            "icon": INDUSTRY_META[ind_id]["icon"],
            "count": counts.get(ind_id, 0),
        }
        for ind_id in ALL_INDUSTRIES
        if counts.get(ind_id, 0) > 0
    ]
