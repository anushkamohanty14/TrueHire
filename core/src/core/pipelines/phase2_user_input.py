import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List


def create_user_profile(
    user_id: str,
    manual_skills: List[str] | None = None,
    interest_tags: List[str] | None = None,
) -> Dict[str, Any]:
    """Create a normalized user profile payload for persistence."""
    if not user_id or not user_id.strip():
        raise ValueError("user_id is required")

    cleaned_skills = sorted({s.strip().lower() for s in (manual_skills or []) if s and s.strip()})
    cleaned_tags = sorted({t.strip().lower() for t in (interest_tags or []) if t and t.strip()})

    return {
        "user_id": user_id.strip(),
        "manual_skills": cleaned_skills,
        "interest_tags": cleaned_tags,
    }


def save_user_profile(profile: Dict[str, Any], storage_path: str = "data/interim/user_profiles.json") -> Dict[str, Any]:
    """Persist a normalized profile in local JSON storage."""
    path = Path(storage_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: Dict[str, Dict[str, Any]] = {}
    if path.exists():
        existing = json.loads(path.read_text() or "{}")
    existing[profile["user_id"]] = profile
    path.write_text(json.dumps(existing, indent=2))
    return profile


def get_user_profile(user_id: str, storage_path: str = "data/interim/user_profiles.json") -> Dict[str, Any] | None:
    path = Path(storage_path)
    if not path.exists():
        return None
    existing = json.loads(path.read_text() or "{}")
    return existing.get(user_id)


def sanitize_user_identifier(user_id: str) -> str:
    """Allow only safe path-friendly user IDs."""
    candidate = (user_id or "").strip()
    if not candidate:
        raise ValueError("user_id is required")
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate)
    return safe[:80]


def upload_resume(file_name: str, content: bytes, user_id: str) -> Dict[str, Any]:
    """Save uploaded resume to local storage and return metadata."""
    safe_user_id = sanitize_user_identifier(user_id)
    safe_name = Path(file_name).name
    output_dir = Path("data/interim/resumes") / safe_user_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / safe_name
    output_path.write_bytes(content)
    return {
        "user_id": safe_user_id,
        "file_name": safe_name,
        "saved_path": str(output_path),
        "size_bytes": len(content),
    }


def merge_resume_skills(
    user_id: str,
    resume_skills: List[str],
    storage_path: str = "data/interim/user_profiles.json",
) -> None:
    """Persist extracted resume skills into the user's stored profile.

    Stores skills under the key ``"resume_skills"`` — kept separate from
    ``"manual_skills"`` so the two sources remain distinguishable downstream.
    Silently does nothing if no profile exists for *user_id*.
    """
    profile = get_user_profile(user_id, storage_path)
    if profile is None:
        return
    normalised = sorted({s.strip().lower() for s in resume_skills if s.strip()})
    profile["resume_skills"] = normalised
    save_user_profile(profile, storage_path)


def collect_manual_skills(raw_skills: str) -> List[str]:
    """Parse comma-separated skills from UI input."""
    return [item.strip() for item in raw_skills.split(",") if item.strip()]


def collect_interest_tags(raw_tags: str) -> List[str]:
    """Parse comma-separated career-interest tags from UI input."""
    return [item.strip() for item in raw_tags.split(",") if item.strip()]


def load_job_titles_from_onet(csv_path: str = "job_abilities_onet.csv") -> List[str]:
    """Load job titles from the O*NET abilities CSV."""
    path = Path(csv_path)
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        keys = reader.fieldnames or []
        title_key = "Title" if "Title" in keys else (keys[0] if keys else "")
        if not title_key:
            return []
        titles = sorted({(row.get(title_key) or "").strip() for row in reader if (row.get(title_key) or "").strip()})
    return titles


def suggest_jobs_from_interest_tags(interest_tags: List[str], job_titles: List[str], top_k: int = 10) -> List[str]:
    """Simple lexical matching from user interest tags to O*NET job titles."""
    tags = [t.lower().strip() for t in interest_tags if t.strip()]
    if not tags:
        return []
    ranked: List[tuple[str, int]] = []
    for title in job_titles:
        lower_title = title.lower()
        score = sum(1 for tag in tags if tag in lower_title)
        if score > 0:
            ranked.append((title, score))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return [title for title, _ in ranked[:top_k]]
