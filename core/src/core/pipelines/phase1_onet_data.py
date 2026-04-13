import csv
from pathlib import Path
from typing import Dict, List


ABILITY_COLUMNS = [
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


def load_onet_data(csv_path: str = "job_abilities_onet.csv") -> List[Dict[str, str]]:
    """Load O*NET ability CSV rows as dictionaries."""
    with Path(csv_path).open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def clean_onet_data(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Basic cleaning: keep rows with non-empty title and parse numeric ability fields."""
    cleaned: List[Dict[str, str]] = []
    for row in rows:
        title = (row.get("Title") or "").strip()
        if not title:
            continue

        normalized = {"Title": title}
        for col in ABILITY_COLUMNS:
            raw = row.get(col, "")
            try:
                normalized[col] = float(raw)
            except (TypeError, ValueError):
                normalized[col] = 0.0
        cleaned.append(normalized)
    return cleaned


def build_job_ability_matrix(rows: List[Dict[str, str]]) -> Dict[str, List[float]]:
    """Create job -> ability vector matrix from cleaned rows."""
    return {row["Title"]: [float(row[col]) for col in ABILITY_COLUMNS] for row in rows}
