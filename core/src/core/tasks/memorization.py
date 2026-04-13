"""Memorization — Digit Span task generator.

Shows a sequence of random digits, then asks the user to recall it in order.
Difficulty controls sequence length (difficulty 1 → 4 digits … difficulty 5 → 8 digits).
"""
from __future__ import annotations

import random
from typing import Any, List

from .base import BaseTaskGenerator, TaskItem


class DigitSpanGenerator(BaseTaskGenerator):
    ability = "memorization"
    task_type = "digit_span"

    _DISPLAY_SECONDS = {1: 2, 2: 3, 3: 3, 4: 4, 5: 4}

    def generate(self, difficulty: int = 1, n: int = 1) -> List[TaskItem]:
        difficulty = max(1, min(5, difficulty))
        length = 3 + difficulty   # 4, 5, 6, 7, 8
        items: List[TaskItem] = []
        for _ in range(n):
            sequence = [str(random.randint(0, 9)) for _ in range(length)]
            items.append(
                TaskItem(
                    ability=self.ability,
                    task_type=self.task_type,
                    question={"sequence": sequence, "display_hint": "Remember this sequence"},
                    correct_answer=" ".join(sequence),
                    difficulty=difficulty,
                    metadata={
                        "length": length,
                        "display_seconds": self._DISPLAY_SECONDS[difficulty],
                    },
                )
            )
        return items

    def score_response(self, task: TaskItem, user_answer: Any) -> bool:
        normalise = lambda s: " ".join(str(s).split())
        return normalise(user_answer) == normalise(task.correct_answer)
