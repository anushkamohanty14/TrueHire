from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class UserProfile:
    user_id: str
    manual_skills: List[str] = field(default_factory=list)
    interest_tags: List[str] = field(default_factory=list)
    cognitive_scores: Dict[str, float] = field(default_factory=dict)
    activity_preferences: Dict[str, float] = field(default_factory=dict)
