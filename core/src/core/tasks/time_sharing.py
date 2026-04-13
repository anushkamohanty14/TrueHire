"""Time Sharing — Dual-task cognitive assessment generator.

O*NET definition: the ability to shift back and forth between two or more
activities or sources of information (such as speech, sounds, touch, or other
sources).

Since the platform runs in a browser UI (not a real-time environment), we
simulate time-sharing via *concurrent presentation*: the user sees TWO
independent mini-tasks at the same time and must answer both correctly.

question structure
------------------
{
    "instruction": str,         # e.g. "Answer both tasks below."
    "task_a": {
        "label": str,           # e.g. "Task A"
        "text":  str,           # the question text
        "options": list[str] | None  # None for free-input tasks
    },
    "task_b": {
        "label": str,
        "text":  str,
        "options": list[str] | None
    }
}

correct_answer
--------------
{"a": <answer_a>, "b": <answer_b>}

Difficulty mapping
------------------
1  Both tasks are simple (single-step arithmetic + yes/no fact)
2  One task is slightly harder (two-step) + one easy
3  Both tasks are moderate; one is MCQ, one is numeric
4  Both tasks are harder; one involves a short passage + inference
5  Both tasks are hard; response requires holding context from both tasks
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from .base import BaseTaskGenerator, TaskItem


# ── Sub-task building blocks ──────────────────────────────────────────────────

def _easy_arithmetic() -> Tuple[str, int]:
    """Single-step addition or subtraction."""
    a, b = random.randint(3, 15), random.randint(2, 10)
    op = random.choice(["add", "sub"])
    if op == "add":
        return f"{a} + {b} = ?", a + b
    else:
        a = max(a, b)
        return f"{a} − {b} = ?", a - b


def _medium_arithmetic() -> Tuple[str, int]:
    """Two-step problem."""
    a, b, c = random.randint(3, 8), random.randint(2, 6), random.randint(1, 5)
    return (f"({a} × {b}) − {c} = ?", a * b - c)


def _hard_arithmetic() -> Tuple[str, int]:
    """Multi-step with percentage."""
    base = random.choice([20, 40, 50, 60, 80, 100])
    pct = random.choice([10, 20, 25, 50])
    discount = base * pct // 100
    return (f"A ${base} item is discounted {pct}%. What is the final price?",
            base - discount)


def _easy_yn_fact() -> Tuple[str, List[str], str]:
    """Simple yes/no factual question."""
    facts = [
        ("Is 7 a prime number?", "yes"),
        ("Is the sum of angles in a triangle equal to 180°?", "yes"),
        ("Does a square have 5 sides?", "no"),
        ("Is 4 an odd number?", "no"),
        ("Is water (H₂O) composed of hydrogen and oxygen?", "yes"),
        ("Is the Earth closer to the Sun than Mars?", "yes"),
    ]
    q, a = random.choice(facts)
    return q, ["yes", "no"], a


def _medium_mcq() -> Tuple[str, List[str], str]:
    """Single-step inference MCQ."""
    items = [
        (
            "All birds have wings. Penguins are birds. Do penguins have wings?",
            ["yes", "no", "sometimes"],
            "yes",
        ),
        (
            "No fish are mammals. A salmon is a fish. Is a salmon a mammal?",
            ["yes", "no", "maybe"],
            "no",
        ),
        (
            "A store opens at 9 AM and closes 8 hours later. What time does it close?",
            ["4 PM", "5 PM", "6 PM", "7 PM"],
            "5 PM",
        ),
        (
            "If today is Wednesday, what day is it in two days?",
            ["Thursday", "Friday", "Saturday", "Sunday"],
            "Friday",
        ),
    ]
    q, opts, a = random.choice(items)
    shuffled = opts[:]
    random.shuffle(shuffled)
    return q, shuffled, a


def _hard_mcq() -> Tuple[str, List[str], str]:
    """Inference requiring multi-step reasoning."""
    items = [
        (
            "A train travels 60 mph for 2 hours, then 80 mph for 1 hour. "
            "What is the total distance?",
            ["180 miles", "200 miles", "240 miles", "140 miles"],
            "200 miles",
        ),
        (
            "If all A are B and some B are C, can we conclude that some A are C?",
            ["yes, definitely", "no, not necessarily", "only if A equals C"],
            "no, not necessarily",
        ),
        (
            "A rope is 10 m long. A 2.5 m piece is cut off. The remainder is divided equally "
            "into 5 pieces. How long is each piece?",
            ["1.5 m", "2 m", "1 m", "2.5 m"],
            "1.5 m",
        ),
    ]
    q, opts, a = random.choice(items)
    shuffled = opts[:]
    random.shuffle(shuffled)
    return q, shuffled, a


def _sequence_tracking() -> Tuple[str, List[str], str]:
    """Identify the next item in a short sequence (held in working memory)."""
    patterns = [
        ("2, 4, 6, 8, ___", ["9", "10", "12", "16"], "10"),
        ("3, 6, 12, 24, ___", ["36", "48", "30", "52"], "48"),
        ("A, C, E, G, ___", ["H", "I", "J", "K"], "I"),
        ("1, 4, 9, 16, ___", ["20", "25", "23", "36"], "25"),
    ]
    seq, opts, a = random.choice(patterns)
    q = f"What comes next? {seq}"
    shuffled = opts[:]
    random.shuffle(shuffled)
    return q, shuffled, a


# ── Dual-task composers per difficulty ────────────────────────────────────────

def _compose_d1() -> Tuple[Dict, Dict[str, Any]]:
    """D1: easy arithmetic + easy yes/no."""
    q_text_a, ans_a = _easy_arithmetic()
    q_text_b, opts_b, ans_b = _easy_yn_fact()
    question = {
        "instruction": "Answer both tasks below.",
        "task_a": {"label": "Task A — Arithmetic", "text": q_text_a, "options": None},
        "task_b": {"label": "Task B — True or False", "text": q_text_b, "options": opts_b},
    }
    return question, {"a": ans_a, "b": ans_b}


def _compose_d2() -> Tuple[Dict, Dict[str, Any]]:
    """D2: medium arithmetic + easy yes/no."""
    q_text_a, ans_a = _medium_arithmetic()
    q_text_b, opts_b, ans_b = _easy_yn_fact()
    question = {
        "instruction": "Answer both tasks below.",
        "task_a": {"label": "Task A — Arithmetic", "text": q_text_a, "options": None},
        "task_b": {"label": "Task B — True or False", "text": q_text_b, "options": opts_b},
    }
    return question, {"a": ans_a, "b": ans_b}


def _compose_d3() -> Tuple[Dict, Dict[str, Any]]:
    """D3: medium arithmetic + medium MCQ."""
    q_text_a, ans_a = _medium_arithmetic()
    q_text_b, opts_b, ans_b = _medium_mcq()
    question = {
        "instruction": "Answer both tasks below.",
        "task_a": {"label": "Task A — Calculation", "text": q_text_a, "options": None},
        "task_b": {"label": "Task B — Reasoning", "text": q_text_b, "options": opts_b},
    }
    return question, {"a": ans_a, "b": ans_b}


def _compose_d4() -> Tuple[Dict, Dict[str, Any]]:
    """D4: hard arithmetic + sequence tracking."""
    q_text_a, ans_a = _hard_arithmetic()
    q_text_b, opts_b, ans_b = _sequence_tracking()
    question = {
        "instruction": "Answer both tasks below.",
        "task_a": {"label": "Task A — Word Problem", "text": q_text_a, "options": None},
        "task_b": {"label": "Task B — Pattern", "text": q_text_b, "options": opts_b},
    }
    return question, {"a": ans_a, "b": ans_b}


def _compose_d5() -> Tuple[Dict, Dict[str, Any]]:
    """D5: hard arithmetic + hard MCQ (reasoning)."""
    q_text_a, ans_a = _hard_arithmetic()
    q_text_b, opts_b, ans_b = _hard_mcq()
    question = {
        "instruction": "Answer both tasks below.",
        "task_a": {"label": "Task A — Word Problem", "text": q_text_a, "options": None},
        "task_b": {"label": "Task B — Reasoning", "text": q_text_b, "options": opts_b},
    }
    return question, {"a": ans_a, "b": ans_b}


_COMPOSERS = {
    1: _compose_d1,
    2: _compose_d2,
    3: _compose_d3,
    4: _compose_d4,
    5: _compose_d5,
}


class TimeShareGenerator(BaseTaskGenerator):
    ability = "time_sharing"
    task_type = "dual_task"

    def generate(self, difficulty: int = 1, n: int = 1) -> List[TaskItem]:
        difficulty = max(1, min(5, difficulty))
        composer = _COMPOSERS[difficulty]
        items: List[TaskItem] = []
        for _ in range(n):
            question, correct_answer = composer()
            items.append(
                TaskItem(
                    ability=self.ability,
                    task_type=self.task_type,
                    question=question,
                    correct_answer=correct_answer,
                    difficulty=difficulty,
                    metadata={},
                )
            )
        return items

    def score_response(self, task: TaskItem, user_answer: Any) -> bool:
        """Both sub-tasks must be correct for the item to count as correct.

        user_answer should be a dict {"a": ..., "b": ...}.
        Task A (numeric) is compared as int; Task B (MCQ) is compared
        case-insensitively as string.
        """
        if not isinstance(user_answer, dict):
            return False
        correct: dict = task.correct_answer

        # Score sub-task A (numeric)
        try:
            a_ok = int(str(user_answer.get("a", "")).strip()) == int(correct["a"])
        except (ValueError, TypeError):
            a_ok = False

        # Score sub-task B (string MCQ)
        b_ok = (
            str(user_answer.get("b", "")).strip().lower()
            == str(correct["b"]).strip().lower()
        )

        return a_ok and b_ok

    def score_partial(self, task: TaskItem, user_answer: Any) -> float:
        """Returns 0.0, 0.5, or 1.0 — partial credit when one sub-task is correct."""
        if not isinstance(user_answer, dict):
            return 0.0
        correct: dict = task.correct_answer

        try:
            a_ok = int(str(user_answer.get("a", "")).strip()) == int(correct["a"])
        except (ValueError, TypeError):
            a_ok = False

        b_ok = (
            str(user_answer.get("b", "")).strip().lower()
            == str(correct["b"]).strip().lower()
        )

        return (0.5 * a_ok) + (0.5 * b_ok)
