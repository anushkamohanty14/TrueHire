"""Problem Sensitivity — Rule Violation Detection task generator.

Presents a rule and a scenario. The user answers whether the rule was violated.
Higher difficulty adds irrelevant distractor sentences to the scenario.

metadata["violated"] (bool) is the ground truth so tests can verify without
re-reading the correct_answer string.
"""
from __future__ import annotations

import random
from typing import List

from .base import BaseTaskGenerator, TaskItem

# Each entry: (rule, violating_scenario, compliant_scenario)
_RULE_SCENARIOS = [
    (
        "All employees must wear ID badges when entering the building.",
        "Alex entered the building without an ID badge.",
        "Maria showed her ID badge before entering the building.",
    ),
    (
        "Packages weighing more than 10 kg must be labelled 'heavy'.",
        "A 15 kg package was shipped without a 'heavy' label.",
        "An 8 kg package was shipped without any special label.",
    ),
    (
        "No food or drinks are allowed in the computer lab.",
        "A student brought a water bottle into the computer lab.",
        "Students left their lunch boxes outside before entering the lab.",
    ),
    (
        "Only licensed drivers may operate company vehicles.",
        "An intern without a driving licence drove the company car.",
        "The licensed manager used the company van for a delivery.",
    ),
    (
        "All financial reports must be reviewed by two managers before submission.",
        "The quarterly report was submitted after review by only one manager.",
        "The annual report was reviewed by three managers before submission.",
    ),
    (
        "Chemicals must be stored in sealed containers at all times.",
        "A bottle of cleaning solution was left open on the storage shelf.",
        "All chemicals were properly sealed and labelled in the storage room.",
    ),
    (
        "Users must log out of the system after each session.",
        "An employee left the terminal without logging out.",
        "The librarian logged out before leaving the computer station.",
    ),
    (
        "Late submissions will not be accepted after the deadline.",
        "A student submitted their assignment two days late and it was accepted.",
        "All students submitted their work before the deadline.",
    ),
    (
        "Meeting rooms must be booked at least 24 hours in advance.",
        "A team reserved a conference room only 2 hours before the meeting.",
        "The project team booked the boardroom three days in advance.",
    ),
    (
        "All visitors must sign the guest register upon arrival.",
        "A visitor walked directly to the third floor without signing in.",
        "Every visitor signed the guest register before being escorted upstairs.",
    ),
    (
        "Equipment borrowed from the lab must be returned within 48 hours.",
        "A researcher kept the spectrometer for an entire week without returning it.",
        "The student returned the borrowed microscope the following afternoon.",
    ),
    (
        "No personal calls are permitted on the factory floor.",
        "A technician answered a personal phone call while operating machinery.",
        "Workers stepped outside the factory to take personal calls.",
    ),
]

_DISTRACTORS = [
    "It was a busy Monday morning.",
    "Several colleagues were nearby at the time.",
    "The weather was overcast that day.",
    "There was a company-wide meeting scheduled for later.",
    "The building was undergoing routine maintenance.",
]


class RuleViolationGenerator(BaseTaskGenerator):
    ability = "problem_sensitivity"
    task_type = "rule_violation"

    def generate(self, difficulty: int = 1, n: int = 1) -> List[TaskItem]:
        difficulty = max(1, min(5, difficulty))
        items: List[TaskItem] = []
        used = set()
        pool = list(range(len(_RULE_SCENARIOS)))
        random.shuffle(pool)

        for i in range(n):
            idx = pool[i % len(pool)]
            rule, violation_scenario, compliant_scenario = _RULE_SCENARIOS[idx]
            violated = random.choice([True, False])
            scenario = violation_scenario if violated else compliant_scenario

            if difficulty >= 3:
                # Add one irrelevant distractor sentence
                scenario = scenario + " " + random.choice(_DISTRACTORS)
            if difficulty == 5:
                # Add a second distractor
                scenario = scenario + " " + random.choice(_DISTRACTORS)

            correct = "yes" if violated else "no"
            items.append(
                TaskItem(
                    ability=self.ability,
                    task_type=self.task_type,
                    question={
                        "rule": rule,
                        "scenario": scenario,
                        "prompt": "Was the rule violated?",
                        "options": ["yes", "no"],
                    },
                    correct_answer=correct,
                    difficulty=difficulty,
                    metadata={"violated": violated, "scenario_index": idx},
                )
            )
        return items
