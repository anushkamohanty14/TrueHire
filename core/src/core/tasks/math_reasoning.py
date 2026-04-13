"""Mathematical Reasoning — Arithmetic word problem generator.

Templates are parameterised; values are drawn randomly within ranges
appropriate for each difficulty level.  An optional LLM hook can be
injected later by subclassing and overriding ``generate``.

Difficulty mapping
------------------
1  Single-step addition / subtraction (small integers)
2  Single-step multiplication / division (whole-number answers)
3  Two-step problems
4  Multi-step with percentage or rate
5  Multi-step with ratio / proportion / combined operations
"""
from __future__ import annotations

import random
from typing import Callable, List, Tuple

from .base import BaseTaskGenerator, TaskItem

# A template is a zero-argument callable that returns (question_str, int_answer, tag)
_TemplateFn = Callable[[], Tuple[str, int, str]]


# ── Difficulty 1 ─────────────────────────────────────────────────────────────

def _t1_add_objects() -> Tuple[str, int, str]:
    a, b = random.randint(3, 15), random.randint(2, 12)
    return (f"Sam has {a} apples. He receives {b} more. How many apples does Sam have now?",
            a + b, "add")


def _t1_sub_objects() -> Tuple[str, int, str]:
    a = random.randint(12, 30)
    b = random.randint(2, a - 1)
    return (f"A bookshelf holds {a} books. {b} books are removed. How many books remain?",
            a - b, "sub")


def _t1_add_score() -> Tuple[str, int, str]:
    a, b = random.randint(5, 20), random.randint(5, 20)
    return (f"Maria scored {a} points in the first game and {b} points in the second. "
            f"What is her total score?",
            a + b, "add")


def _t1_sub_marbles() -> Tuple[str, int, str]:
    a = random.randint(20, 50)
    b = random.randint(5, a - 1)
    return (f"A bag contains {a} marbles. {b} marbles are lost. How many marbles are left?",
            a - b, "sub")


# ── Difficulty 2 ─────────────────────────────────────────────────────────────

def _t2_mul_boxes() -> Tuple[str, int, str]:
    a, b = random.randint(3, 9), random.randint(4, 12)
    return (f"A crate holds {a} bottles. There are {b} crates. How many bottles in total?",
            a * b, "mul")


def _t2_div_groups() -> Tuple[str, int, str]:
    b = random.randint(3, 8)
    q = random.randint(4, 10)
    a = b * q
    return (f"{a} students are split equally into {b} groups. How many students are in each group?",
            q, "div")


def _t2_mul_price() -> Tuple[str, int, str]:
    price, qty = random.randint(2, 9), random.randint(3, 12)
    return (f"Each notebook costs ${price}. How much do {qty} notebooks cost?",
            price * qty, "mul")


def _t2_div_share() -> Tuple[str, int, str]:
    n = random.randint(3, 8)
    share = random.randint(4, 15)
    total = n * share
    return (f"{n} friends share ${total} equally. How much does each friend receive?",
            share, "div")


# ── Difficulty 3 ─────────────────────────────────────────────────────────────

def _t3_buy_and_change() -> Tuple[str, int, str]:
    price = random.randint(3, 9)
    qty = random.randint(2, 5)
    paid = price * qty + random.randint(1, 10)
    cost = price * qty
    change = paid - cost
    return (f"Pens cost ${price} each. You buy {qty} pens and pay ${paid}. "
            f"How much change do you receive?",
            change, "two_step_change")


def _t3_total_after_return() -> Tuple[str, int, str]:
    bought = random.randint(8, 20)
    price = random.randint(2, 6)
    returned = random.randint(1, bought - 1)
    kept = bought - returned
    total = kept * price
    return (f"You buy {bought} items at ${price} each, then return {returned} items. "
            f"How much did the items you kept cost in total?",
            total, "two_step_cost")


def _t3_distance() -> Tuple[str, int, str]:
    s1, t1 = random.randint(40, 70), random.randint(2, 4)
    s2, t2 = random.randint(30, 60), random.randint(1, 3)
    d1, d2 = s1 * t1, s2 * t2
    return (f"Car A travels at {s1} mph for {t1} hours. Car B travels at {s2} mph for {t2} hours. "
            f"How many more miles does Car A travel than Car B?",
            d1 - d2, "two_step_distance")


def _t3_workers() -> Tuple[str, int, str]:
    rate = random.randint(5, 12)
    workers = random.randint(3, 7)
    hours = random.randint(4, 8)
    total = rate * workers * hours
    return (f"{workers} workers each produce {rate} units per hour. "
            f"How many units do they produce together in {hours} hours?",
            total, "two_step_mul")


# ── Difficulty 4 ─────────────────────────────────────────────────────────────

def _t4_percent_discount() -> Tuple[str, int, str]:
    original = random.choice([20, 40, 50, 80, 100, 120, 150, 200])
    pct = random.choice([10, 20, 25, 50])
    discount = original * pct // 100
    final = original - discount
    return (f"A jacket costs ${original}. It is on sale for {pct}% off. "
            f"What is the sale price?",
            final, "percent_discount")


def _t4_percent_increase() -> Tuple[str, int, str]:
    base = random.choice([20, 40, 50, 60, 80, 100])
    pct = random.choice([10, 20, 25, 50])
    increase = base * pct // 100
    total = base + increase
    return (f"A salary of ${base} per hour is increased by {pct}%. "
            f"What is the new hourly salary?",
            total, "percent_increase")


def _t4_rate_time() -> Tuple[str, int, str]:
    rate = random.randint(30, 80)
    time = random.randint(2, 6)
    target = rate * time
    return (f"A pump fills a tank at {rate} litres per minute. "
            f"How many litres does it pump in {time} minutes?",
            target, "rate")


def _t4_combined_earnings() -> Tuple[str, int, str]:
    hourly = random.randint(10, 20)
    regular = random.randint(35, 40)
    overtime_rate = hourly * 2
    overtime = random.randint(3, 8)
    total = hourly * regular + overtime_rate * overtime
    return (f"An employee earns ${hourly}/hour for a {regular}-hour week, "
            f"and double-time for overtime. "
            f"They worked {overtime} overtime hours this week. "
            f"What are their total earnings?",
            total, "rate_overtime")


# ── Difficulty 5 ─────────────────────────────────────────────────────────────

def _t5_ratio_mix() -> Tuple[str, int, str]:
    a, b = random.randint(1, 4), random.randint(1, 4)
    total_parts = a + b
    total = total_parts * random.randint(5, 12)
    share_a = (a * total) // total_parts
    return (f"A recipe requires ingredients A and B in the ratio {a}:{b}. "
            f"You need {total} grams in total. How many grams of ingredient A do you need?",
            share_a, "ratio")


def _t5_proportion() -> Tuple[str, int, str]:
    rate = random.randint(3, 8)
    per = random.randint(2, 5)
    new_per = per * random.randint(2, 4)
    result = rate * new_per // per
    return (f"If {rate} widgets are produced every {per} hours, "
            f"how many widgets are produced in {new_per} hours?",
            result, "proportion")


def _t5_compound_purchase() -> Tuple[str, int, str]:
    price_a = random.randint(3, 8)
    price_b = random.randint(2, 6)
    qty_a = random.randint(3, 8)
    qty_b = random.randint(2, 7)
    budget = price_a * qty_a + price_b * qty_b + random.randint(5, 20)
    spent = price_a * qty_a + price_b * qty_b
    remaining = budget - spent
    return (f"You have ${budget}. You buy {qty_a} items at ${price_a} each "
            f"and {qty_b} items at ${price_b} each. How much money do you have left?",
            remaining, "compound_purchase")


def _t5_weighted_avg() -> Tuple[str, int, str]:
    s1, w1 = random.randint(60, 90), random.randint(1, 3)
    s2, w2 = random.randint(60, 90), random.randint(1, 3)
    total_weight = w1 + w2
    avg = (s1 * w1 + s2 * w2) // total_weight
    return (f"Test 1 score: {s1} (weight {w1}). Test 2 score: {s2} (weight {w2}). "
            f"What is the weighted average score (round down)?",
            avg, "weighted_avg")


# ── Template pool ─────────────────────────────────────────────────────────────

_POOL: dict[int, List[_TemplateFn]] = {
    1: [_t1_add_objects, _t1_sub_objects, _t1_add_score, _t1_sub_marbles],
    2: [_t2_mul_boxes, _t2_div_groups, _t2_mul_price, _t2_div_share],
    3: [_t3_buy_and_change, _t3_total_after_return, _t3_distance, _t3_workers],
    4: [_t4_percent_discount, _t4_percent_increase, _t4_rate_time, _t4_combined_earnings],
    5: [_t5_ratio_mix, _t5_proportion, _t5_compound_purchase, _t5_weighted_avg],
}


class MathReasoningGenerator(BaseTaskGenerator):
    ability = "mathematical_reasoning"
    task_type = "arithmetic_word_problem"

    def generate(self, difficulty: int = 1, n: int = 1) -> List[TaskItem]:
        difficulty = max(1, min(5, difficulty))
        pool = _POOL[difficulty]
        items: List[TaskItem] = []
        fns = random.choices(pool, k=n)
        for fn in fns:
            text, answer, tag = fn()
            items.append(
                TaskItem(
                    ability=self.ability,
                    task_type=self.task_type,
                    question={"text": text},
                    correct_answer=answer,
                    difficulty=difficulty,
                    metadata={"tag": tag},
                )
            )
        return items

    def score_response(self, task: TaskItem, user_answer) -> bool:
        """Accept int or string representations of the correct integer answer."""
        try:
            return int(str(user_answer).strip()) == int(task.correct_answer)
        except (ValueError, TypeError):
            return False
