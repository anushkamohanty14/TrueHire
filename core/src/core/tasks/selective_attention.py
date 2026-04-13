"""Selective Attention — Stroop task generator.

Displays a colour word (e.g. "RED") rendered in a *different* ink colour
(e.g. blue). The user must identify the ink colour, ignoring the word meaning.

The question dict carries:
  word      — the text of the colour word (UPPER-CASE string)
  ink_color — the actual display colour (the correct answer)
  options   — shuffled list of four colour names
The UI is responsible for rendering `word` in `ink_color`.
"""
from __future__ import annotations

import random
from typing import Any, List

from .base import BaseTaskGenerator, TaskItem

COLORS = ["red", "blue", "green", "yellow", "orange", "purple"]


class StroopGenerator(BaseTaskGenerator):
    ability = "selective_attention"
    task_type = "stroop"

    def generate(self, difficulty: int = 1, n: int = 1) -> List[TaskItem]:
        difficulty = max(1, min(5, difficulty))
        items: List[TaskItem] = []
        for _ in range(n):
            word = random.choice(COLORS)
            # Always incongruent: ink ≠ word
            ink_color = random.choice([c for c in COLORS if c != word])

            # Build MCQ options: correct + 3 random wrong colours
            wrongs = random.sample([c for c in COLORS if c != ink_color], k=3)
            options = [ink_color] + wrongs
            random.shuffle(options)

            items.append(
                TaskItem(
                    ability=self.ability,
                    task_type=self.task_type,
                    question={
                        "word": word.upper(),
                        "ink_color": ink_color,
                        "prompt": "What colour is the ink? (ignore the word meaning)",
                        "options": options,
                    },
                    correct_answer=ink_color,
                    difficulty=difficulty,
                    metadata={"word": word, "ink_color": ink_color, "congruent": False},
                )
            )
        return items
