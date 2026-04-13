"""Written Comprehension — Passage + multiple-choice question generator.

Each template is a (passage, question, options, correct_answer, difficulty, tag) tuple.
correct_answer is always one of the option strings (verbatim).

Difficulty mapping
------------------
1  Very short passage (2-3 sentences); literal recall
2  Short passage; simple one-step inference
3  Medium passage; inference requiring integration of two sentences
4  Medium passage; vocabulary-in-context or implicit-cause inference
5  Longer passage; evaluation, author-intent, or multi-step reasoning
"""
from __future__ import annotations

import random
from typing import List, Tuple

from .base import BaseTaskGenerator, TaskItem

# (passage, question, options, correct_answer, difficulty, tag)
_TEMPLATES: List[Tuple[str, str, List[str], str, int, str]] = [

    # ── Difficulty 1: literal recall ─────────────────────────────────────────
    (
        "The library opens at 9 AM and closes at 6 PM on weekdays. "
        "On weekends it opens two hours later.",
        "What time does the library open on weekdays?",
        ["7 AM", "9 AM", "11 AM", "6 PM"],
        "9 AM", 1, "literal_time"
    ),
    (
        "Maria packed three apples, two sandwiches, and a bottle of water for her hike.",
        "How many food items did Maria pack in total?",
        ["3", "4", "5", "6"],
        "5", 1, "literal_count"
    ),
    (
        "The train leaves Platform 4 at 08:15 and arrives at Central Station at 09:45.",
        "From which platform does the train depart?",
        ["1", "2", "4", "Central"],
        "4", 1, "literal_fact"
    ),
    (
        "Jake has been learning piano for three years. He practises every day for thirty minutes.",
        "How long does Jake practise piano each day?",
        ["Three hours", "One hour", "Thirty minutes", "Fifteen minutes"],
        "Thirty minutes", 1, "literal_duration"
    ),

    # ── Difficulty 2: simple inference ───────────────────────────────────────
    (
        "The museum is free for children under 12. Adult tickets cost $15. "
        "Senior citizens receive a 50% discount.",
        "How much does an adult ticket cost after a 50% senior discount?",
        ["$5", "$7.50", "$10", "$15"],
        "$7.50", 2, "inference_arithmetic"
    ),
    (
        "Every morning, the bakery sells out of croissants within two hours of opening. "
        "The bakery opens at 7 AM.",
        "By what time are the croissants usually sold out?",
        ["7 AM", "8 AM", "9 AM", "10 AM"],
        "9 AM", 2, "inference_time"
    ),
    (
        "Sofia reads 40 pages per hour. She has 120 pages left in her book.",
        "How long will it take Sofia to finish the book?",
        ["1 hour", "2 hours", "3 hours", "4 hours"],
        "3 hours", 2, "inference_rate"
    ),
    (
        "The recipe requires twice as much flour as sugar. If you use 2 cups of sugar, "
        "you also need butter equal to half the amount of flour.",
        "How many cups of butter does the recipe require?",
        ["1", "2", "3", "4"],
        "2", 2, "inference_ratio"
    ),

    # ── Difficulty 3: two-sentence integration ───────────────────────────────
    (
        "The city council voted to reduce bus fares by 20% to encourage public transport use. "
        "However, the transit authority warned that lower fares would reduce maintenance funding.",
        "What concern did the transit authority raise about the fare reduction?",
        [
            "Buses would become overcrowded.",
            "Maintenance funding would decrease.",
            "Drivers would go on strike.",
            "Fares would need to rise again soon.",
        ],
        "Maintenance funding would decrease.", 3, "inference_consequence"
    ),
    (
        "Rainforests cover only 6% of the Earth's surface yet house more than half of all "
        "plant and animal species. Deforestation destroys approximately 80,000 acres of forest daily.",
        "Which conclusion is best supported by the passage?",
        [
            "Deforestation has no effect on biodiversity.",
            "Rainforests are the least important biome.",
            "Rapid deforestation threatens a disproportionately large share of species.",
            "Only 6% of species live outside rainforests.",
        ],
        "Rapid deforestation threatens a disproportionately large share of species.", 3,
        "inference_implication"
    ),
    (
        "Studies show that students who sleep fewer than seven hours perform worse on memory tests. "
        "Elena slept only five hours before her exam.",
        "What does the passage suggest about Elena's likely exam performance?",
        [
            "She will perform above average.",
            "Sleep has no effect on her results.",
            "Her memory performance may be impaired.",
            "She studied for five hours.",
        ],
        "Her memory performance may be impaired.", 3, "inference_prediction"
    ),

    # ── Difficulty 4: vocabulary-in-context / implicit cause ─────────────────
    (
        "Despite the team's tenacious defence, the opposing striker found a gap and scored "
        "in the final minute, ending the home side's unbeaten run.",
        "In this context, 'tenacious' most nearly means:",
        ["Weak", "Persistent", "Careless", "Slow"],
        "Persistent", 4, "vocab_in_context"
    ),
    (
        "The new policy mandates that all suppliers disclose their environmental impact annually. "
        "Critics argue this places an undue burden on small businesses with limited reporting capacity.",
        "Why do critics oppose the policy?",
        [
            "They prefer no environmental regulations.",
            "Annual reporting is too infrequent.",
            "Small businesses may struggle to meet the reporting requirements.",
            "Large suppliers already disclose environmental data.",
        ],
        "Small businesses may struggle to meet the reporting requirements.", 4,
        "implicit_cause"
    ),
    (
        "After the product recall, the company issued an unequivocal apology and pledged "
        "full refunds. Analysts noted this swift response helped mitigate reputational damage.",
        "What does 'unequivocal' most likely mean as used here?",
        ["Reluctant", "Clear and unconditional", "Delayed", "Private"],
        "Clear and unconditional", 4, "vocab_in_context"
    ),

    # ── Difficulty 5: evaluation / author intent / multi-step reasoning ───────
    (
        "Proponents of a four-day work week argue that productivity per hour increases when "
        "employees are less fatigued. Opponents counter that client-facing industries cannot "
        "reduce availability without losing business. A pilot programme in Iceland found that "
        "output remained stable while worker well-being improved significantly.",
        "Which statement best describes the overall purpose of the passage?",
        [
            "To prove that a four-day week always increases productivity.",
            "To argue that opponents are wrong.",
            "To present multiple perspectives on the four-day work week using evidence.",
            "To explain why Iceland changed its labour laws.",
        ],
        "To present multiple perspectives on the four-day work week using evidence.", 5,
        "author_purpose"
    ),
    (
        "Classical economists assume that individuals act rationally to maximise utility. "
        "Behavioural economists, however, have documented systematic biases—such as loss aversion "
        "and anchoring—that cause people to deviate from purely rational choices. These findings "
        "have led some policymakers to design 'nudges': subtle changes in how choices are presented "
        "that steer people toward better decisions without restricting freedom.",
        "What is the main implication of behavioural economics for policy design?",
        [
            "Rational choice theory should be abandoned entirely.",
            "People always make better decisions when given more options.",
            "Understanding cognitive biases can inform more effective policy interventions.",
            "Nudges are more effective than laws.",
        ],
        "Understanding cognitive biases can inform more effective policy interventions.", 5,
        "multi_step_reasoning"
    ),
    (
        "While renewable energy sources have grown rapidly, critics point out that solar and "
        "wind power are intermittent—they generate electricity only when the sun shines or the "
        "wind blows. Battery storage technology has improved, but costs remain high. Some "
        "engineers advocate for a diversified grid that combines renewables with reliable "
        "baseload sources such as nuclear or hydroelectric power.",
        "According to the passage, what is the primary challenge facing renewable energy?",
        [
            "Renewable energy is too expensive to build.",
            "Solar and wind power are not consistent power sources.",
            "Nuclear power is more popular than renewables.",
            "Battery storage is no longer needed.",
        ],
        "Solar and wind power are not consistent power sources.", 5, "identify_challenge"
    ),
]

# Group by difficulty
_BY_DIFFICULTY: dict[int, list] = {d: [] for d in range(1, 6)}
for _t in _TEMPLATES:
    _BY_DIFFICULTY[_t[4]].append(_t)
# Lower difficulties draw from adjacent pools for variety
_BY_DIFFICULTY[2] = _BY_DIFFICULTY[2] + _BY_DIFFICULTY[1]


class WrittenComprehensionGenerator(BaseTaskGenerator):
    ability = "written_comprehension"
    task_type = "passage_mcq"

    def generate(self, difficulty: int = 1, n: int = 1) -> List[TaskItem]:
        difficulty = max(1, min(5, difficulty))
        pool = _BY_DIFFICULTY[difficulty]
        items: List[TaskItem] = []
        chosen = random.choices(pool, k=n)
        for passage, question, options, correct, diff, tag in chosen:
            shuffled = options[:]
            random.shuffle(shuffled)
            items.append(
                TaskItem(
                    ability=self.ability,
                    task_type=self.task_type,
                    question={
                        "passage": passage,
                        "question": question,
                        "options": shuffled,
                    },
                    correct_answer=correct,
                    difficulty=diff,
                    metadata={"tag": tag},
                )
            )
        return items
