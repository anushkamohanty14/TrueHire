from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List

ABILITIES = [
    "deductive_reasoning",
    "mathematical_reasoning",
    "memorization",
    "perceptual_speed",
    "problem_sensitivity",
    "selective_attention",
    "speed_of_closure",
    "time_sharing",
    "written_comprehension",
]


@dataclass
class TaskItem:
    ability: str
    task_type: str
    question: Any          # dict or primitive — rendered by the UI
    correct_answer: Any    # compared against user_answer at scoring time
    difficulty: int        # 1–5
    metadata: dict = field(default_factory=dict)


@dataclass
class TaskResponse:
    task_item: TaskItem
    user_answer: Any
    reaction_time_ms: float
    is_correct: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BaseTaskGenerator(ABC):
    ability: str
    task_type: str

    @abstractmethod
    def generate(self, difficulty: int = 1, n: int = 1) -> List[TaskItem]:
        """Generate *n* task items at the given difficulty level (1–5)."""
        ...

    def score_response(self, task: TaskItem, user_answer: Any) -> bool:
        """Default exact-match scoring (case-insensitive string comparison)."""
        return (
            str(user_answer).strip().lower()
            == str(task.correct_answer).strip().lower()
        )
