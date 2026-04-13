"""Deductive Reasoning — Syllogism task generator.

Uses a template pool of logically verified syllogisms grouped by difficulty:
  1–2  Universal affirmative  (All A are B. X is A → X is B)
  3    Converse fallacy trap  (All A are B. Y is B → Y is necessarily A? NO)
  4    Universal negative / particular quantifier
  5    Conditional reasoning  (modus ponens / modus tollens)

Each template is a (question_text, correct_answer, form_tag) tuple.
correct_answer is always "yes" or "no".
"""
from __future__ import annotations

import random
from typing import List, Tuple

from .base import BaseTaskGenerator, TaskItem

# (question_text, correct_answer, form_tag, difficulty)
_TEMPLATES: List[Tuple[str, str, str, int]] = [
    # ---------- difficulty 1-2: universal affirmative ----------
    ("All mammals are animals. A whale is a mammal. Is a whale an animal?",
     "yes", "all_AB_xA→xB", 1),
    ("All dogs are mammals. Rex is a dog. Is Rex a mammal?",
     "yes", "all_AB_xA→xB", 1),
    ("All roses are flowers. This red rose is a rose. Is this red rose a flower?",
     "yes", "all_AB_xA→xB", 1),
    ("All birds have feathers. A penguin is a bird. Does a penguin have feathers?",
     "yes", "all_AB_xA→xB", 1),
    ("All prime numbers greater than 2 are odd. 7 is a prime number greater than 2. Is 7 odd?",
     "yes", "all_AB_xA→xB", 2),
    ("All squares are rectangles. Shape X is a square. Is Shape X a rectangle?",
     "yes", "all_AB_xA→xB", 2),
    ("All licensed pharmacists have completed a pharmacy degree. Jordan is a licensed pharmacist. "
     "Has Jordan completed a pharmacy degree?",
     "yes", "all_AB_xA→xB", 2),
    # ---------- difficulty 3: converse fallacy ----------
    ("All mammals are animals. A tuna is an animal. Is a tuna necessarily a mammal?",
     "no", "all_AB_yB↛yA", 3),
    ("All birds have feathers. This creature has feathers. Is it necessarily a bird?",
     "no", "all_AB_yB↛yA", 3),
    ("All squares are rectangles. Shape Y is a rectangle. Is Shape Y necessarily a square?",
     "no", "all_AB_yB↛yA", 3),
    ("All oak trees are plants. This organism is a plant. Is it necessarily an oak tree?",
     "no", "all_AB_yB↛yA", 3),
    # ---------- difficulty 4: universal negative / particular ----------
    ("No fish are mammals. A salmon is a fish. Is a salmon a mammal?",
     "no", "no_AB_xA→¬xB", 4),
    ("No reptiles are warm-blooded. A gecko is a reptile. Is a gecko warm-blooded?",
     "no", "no_AB_xA→¬xB", 4),
    ("Some athletes are doctors. Alex is an athlete. Is Alex necessarily a doctor?",
     "no", "some_AB_xA↛xB", 4),
    ("Some politicians are lawyers. Sam is a lawyer. Is Sam necessarily a politician?",
     "no", "some_AB_yB↛yA", 4),
    ("No even numbers are odd. 14 is an even number. Is 14 an odd number?",
     "no", "no_AB_xA→¬xB", 4),
    # ---------- difficulty 5: conditional reasoning ----------
    ("If it rains, the ground gets wet. It rained today. Is the ground wet?",
     "yes", "modus_ponens", 5),
    ("If a number is divisible by 4, it is divisible by 2. 12 is divisible by 4. Is 12 divisible by 2?",
     "yes", "modus_ponens", 5),
    ("If you study hard, you pass the exam. Alex did not pass the exam. "
     "Did Alex necessarily not study hard?",
     "yes", "modus_tollens", 5),
    ("If all sides of a triangle are equal, the triangle is equilateral. "
     "This triangle is not equilateral. Does it necessarily have unequal sides?",
     "yes", "modus_tollens", 5),
    ("If a store is open, its lights are on. The store's lights are on. "
     "Is the store necessarily open?",
     "no", "affirming_consequent_fallacy", 5),
]

# Group templates by difficulty band
_BY_DIFFICULTY: dict[int, list] = {d: [] for d in range(1, 6)}
for _t in _TEMPLATES:
    _BY_DIFFICULTY[_t[3]].append(_t)
# Difficulty 2 also draws from difficulty 1 pool for variety
_BY_DIFFICULTY[2] = _BY_DIFFICULTY[2] + _BY_DIFFICULTY[1]


class SyllogismGenerator(BaseTaskGenerator):
    ability = "deductive_reasoning"
    task_type = "syllogism"

    def generate(self, difficulty: int = 1, n: int = 1) -> List[TaskItem]:
        difficulty = max(1, min(5, difficulty))
        pool = _BY_DIFFICULTY[difficulty]
        items: List[TaskItem] = []
        chosen = random.choices(pool, k=n)
        for text, correct, form, diff in chosen:
            items.append(
                TaskItem(
                    ability=self.ability,
                    task_type=self.task_type,
                    question={"text": text, "options": ["yes", "no"]},
                    correct_answer=correct,
                    difficulty=diff,
                    metadata={"form": form},
                )
            )
        return items
