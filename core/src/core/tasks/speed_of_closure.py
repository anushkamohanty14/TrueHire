"""Speed of Closure — Sequence Completion task generator.

Presents a number or letter sequence with one element replaced by "?".
The user must identify the missing element.

Difficulty → pattern type:
  1–2  arithmetic  (e.g.  2, 4, 6, ?, 10)
  3    geometric   (e.g.  2, 4, 8, ?, 32)
  4    alphabetical (e.g. A, C, E, ?, I)
  5    additive (Fibonacci-style)  (e.g. 1, 1, 2, 3, ?, 8)

metadata stores `full_sequence` and `gap_index` so tests can verify
correctness without re-implementing the generation logic.
"""
from __future__ import annotations

import random
from typing import List

from .base import BaseTaskGenerator, TaskItem


class SequenceCompletionGenerator(BaseTaskGenerator):
    ability = "speed_of_closure"
    task_type = "sequence_completion"

    def generate(self, difficulty: int = 1, n: int = 1) -> List[TaskItem]:
        difficulty = max(1, min(5, difficulty))
        dispatch = {1: self._arithmetic, 2: self._arithmetic,
                    3: self._geometric, 4: self._alphabetical, 5: self._additive}
        items: List[TaskItem] = []
        for _ in range(n):
            items.append(dispatch[difficulty]())
        return items

    # ------------------------------------------------------------------
    def _arithmetic(self) -> TaskItem:
        start = random.randint(1, 10)
        step = random.randint(2, 6)
        seq = [start + i * step for i in range(6)]
        gap = random.randint(1, 4)
        answer = seq[gap]
        displayed = [str(x) if i != gap else "?" for i, x in enumerate(seq)]
        return TaskItem(
            ability=self.ability, task_type=self.task_type,
            question={"sequence": displayed, "text": ", ".join(displayed)},
            correct_answer=str(answer),
            difficulty=1,
            metadata={"pattern": "arithmetic", "step": step,
                      "full_sequence": [str(x) for x in seq], "gap_index": gap},
        )

    def _geometric(self) -> TaskItem:
        start = random.randint(1, 3)
        ratio = random.randint(2, 3)
        seq = [start * (ratio ** i) for i in range(5)]
        gap = random.randint(1, 3)
        answer = seq[gap]
        displayed = [str(x) if i != gap else "?" for i, x in enumerate(seq)]
        return TaskItem(
            ability=self.ability, task_type=self.task_type,
            question={"sequence": displayed, "text": ", ".join(displayed)},
            correct_answer=str(answer),
            difficulty=3,
            metadata={"pattern": "geometric", "ratio": ratio,
                      "full_sequence": [str(x) for x in seq], "gap_index": gap},
        )

    def _alphabetical(self) -> TaskItem:
        start = random.randint(0, 18)
        step = random.randint(1, 3)
        seq = [chr(ord("A") + (start + i * step) % 26) for i in range(5)]
        gap = random.randint(1, 3)
        answer = seq[gap]
        displayed = [x if i != gap else "?" for i, x in enumerate(seq)]
        return TaskItem(
            ability=self.ability, task_type=self.task_type,
            question={"sequence": displayed, "text": ", ".join(displayed)},
            correct_answer=answer,
            difficulty=4,
            metadata={"pattern": "alphabetical", "step": step,
                      "full_sequence": seq, "gap_index": gap},
        )

    def _additive(self) -> TaskItem:
        a, b = random.randint(1, 3), random.randint(1, 3)
        seq = [a, b]
        while len(seq) < 6:
            seq.append(seq[-1] + seq[-2])
        gap = random.randint(2, 4)
        answer = seq[gap]
        displayed = [str(x) if i != gap else "?" for i, x in enumerate(seq)]
        return TaskItem(
            ability=self.ability, task_type=self.task_type,
            question={"sequence": displayed, "text": ", ".join(displayed)},
            correct_answer=str(answer),
            difficulty=5,
            metadata={"pattern": "additive", "seed": [a, b],
                      "full_sequence": [str(x) for x in seq], "gap_index": gap},
        )
