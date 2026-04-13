"""Perceptual Speed — Symbol Search task generator.

Displays a target symbol and a row of symbols. The user answers whether
the target is present in the row. Difficulty increases the row size.
"""
from __future__ import annotations

import random
from typing import Any, List

from .base import BaseTaskGenerator, TaskItem

SYMBOLS = ["@", "#", "$", "%", "&", "*", "!", "?", "+", "=", "~", "^", ">", "<", "/", "|"]


class SymbolSearchGenerator(BaseTaskGenerator):
    ability = "perceptual_speed"
    task_type = "symbol_search"

    def generate(self, difficulty: int = 1, n: int = 1) -> List[TaskItem]:
        difficulty = max(1, min(5, difficulty))
        grid_size = 4 + difficulty   # 5–9 symbols in the search row
        items: List[TaskItem] = []
        for _ in range(n):
            target = random.choice(SYMBOLS)
            present = random.choice([True, False])
            non_targets = [s for s in SYMBOLS if s != target]

            if present:
                filler = random.choices(non_targets, k=grid_size - 1)
                grid = filler[:]
                grid.insert(random.randint(0, len(grid)), target)
            else:
                grid = random.choices(non_targets, k=grid_size)

            correct = "yes" if present else "no"
            items.append(
                TaskItem(
                    ability=self.ability,
                    task_type=self.task_type,
                    question={
                        "target": target,
                        "grid": grid,
                        "prompt": f"Is '{target}' present in the row?",
                        "options": ["yes", "no"],
                    },
                    correct_answer=correct,
                    difficulty=difficulty,
                    metadata={"grid_size": len(grid), "target_present": present},
                )
            )
        return items
