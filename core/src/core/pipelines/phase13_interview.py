"""Phase 13 - Interview simulation helpers.

This module provides lightweight generation/evaluation helpers used by the
interview router. It intentionally keeps logic deterministic and dependency-free
so it can run in all environments.
"""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Optional


_BEHAVIORAL_PROMPTS = [
    "Tell me about a time you had to handle {focus} in a high-pressure situation.",
    "Describe a project where {focus} was critical to the outcome.",
    "Share an example of when you improved your approach to {focus} after feedback.",
    "Walk me through a time you had to prioritize while managing {focus}.",
    "Tell me about a challenge where {focus} helped you deliver results.",
]

_TECHNICAL_PROMPTS = [
    "How would you apply {skill} in a real {job_title} workflow?",
    "Explain your approach to debugging issues related to {skill}.",
    "What trade-offs do you consider when implementing solutions with {skill}?",
    "Describe a production scenario where {skill} can fail and how you would respond.",
    "How would you validate quality and reliability when working with {skill}?",
]


def _title_case(text: str) -> str:
    return " ".join(w.capitalize() for w in text.replace("_", " ").split())


def generate_behavioral_questions(
    job_title: str,
    top_work_activities: List[str],
    user_ability_gaps: List[str],
    n: int = 5,
) -> List[Dict[str, Any]]:
    """Generate behavioral questions grounded in activities and ability gaps."""
    focus_pool = [*user_ability_gaps, *top_work_activities]
    if not focus_pool:
        focus_pool = ["problem solving", "communication", "collaboration"]

    out: List[Dict[str, Any]] = []
    for i in range(max(1, n)):
        focus = focus_pool[i % len(focus_pool)]
        prompt = _BEHAVIORAL_PROMPTS[i % len(_BEHAVIORAL_PROMPTS)].format(focus=focus)
        out.append(
            {
                "question": f"For the role {job_title}, {prompt}",
                "ability_focus": _title_case(str(focus)),
                "type": "behavioral",
            }
        )
    return out


def generate_technical_questions(
    job_title: str,
    user_skills: List[str],
    required_skills: List[str],
    user_gaps: List[str],
    n: int = 5,
) -> List[Dict[str, Any]]:
    """Generate technical questions from gap-first skill priorities."""
    gap_first = [*user_gaps, *required_skills]
    if not gap_first:
        gap_first = user_skills[:]
    if not gap_first:
        gap_first = ["system design", "testing", "data modeling"]

    out: List[Dict[str, Any]] = []
    for i in range(max(1, n)):
        skill = gap_first[i % len(gap_first)]
        prompt = _TECHNICAL_PROMPTS[i % len(_TECHNICAL_PROMPTS)].format(
            skill=skill,
            job_title=job_title,
        )
        out.append(
            {
                "question": prompt,
                "skill_focus": _title_case(str(skill)),
                "difficulty": min(3, 1 + (i % 3)),
                "type": "technical",
            }
        )
    return out


def evaluate_answer(
    question: str,
    answer: str,
    question_type: str,
    job_context: str,
    ability_focus: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate an answer with simple quality heuristics.

    Returns a 1-5 score and targeted feedback fields.
    """
    text = (answer or "").strip()
    words = text.split()
    word_count = len(words)

    score = 1
    if word_count >= 25:
        score = 2
    if word_count >= 45:
        score = 3
    if word_count >= 80:
        score = 4
    if word_count >= 120:
        score = 5

    lower = text.lower()
    signal_terms = ["impact", "result", "outcome", "metric", "improved", "trade-off"]
    signal_hits = sum(1 for term in signal_terms if term in lower)
    if signal_hits >= 3 and score < 5:
        score += 1

    focus = ability_focus or "this competency"
    strength = "Clear, role-aware explanation"
    if signal_hits >= 3:
        strength = "Good use of measurable outcomes and decision reasoning"

    if score <= 2:
        feedback = (
            f"Your answer is brief for a {question_type} response. Add more context, "
            "actions you personally took, and the final impact."
        )
        improvement = f"Use a STAR structure and tie examples back to {focus}."
    elif score == 3:
        feedback = (
            "Your response is directionally strong but can be more specific about "
            "trade-offs, constraints, and measurable results."
        )
        improvement = f"Add one concrete metric and explicitly connect it to {focus}."
    else:
        feedback = (
            f"Strong answer for {job_context}. You gave useful detail and relevant "
            "problem-solving rationale."
        )
        improvement = "Keep the same structure, and close with business/user impact in one sentence."

    return {
        "score": max(1, min(5, score)),
        "feedback": feedback,
        "strength": strength,
        "improvement": improvement,
    }


def generate_session_summary(session: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize an interview session into score and coaching pointers."""
    questions = session.get("questions", []) or []
    scored = [q for q in questions if isinstance(q.get("score"), (int, float))]

    if not scored:
        return {
            "overall_score": 0.0,
            "strengths": [],
            "areas_to_improve": ["Complete the interview to unlock feedback."],
            "recommended_focus": "Practice concise STAR-format responses.",
        }

    overall = round(mean(float(q["score"]) for q in scored), 2)

    strengths = []
    improvements = []
    for q in scored:
        if q.get("strength"):
            strengths.append(str(q["strength"]))
        if q.get("score", 0) <= 3:
            if q.get("improvement"):
                improvements.append(str(q["improvement"]))
            else:
                focus = q.get("ability_focus") or q.get("skill_focus") or "communication"
                improvements.append(f"Build stronger examples around {focus}.")

    # Keep summary concise and deduplicated while preserving order.
    strengths = list(dict.fromkeys(strengths))[:5]
    improvements = list(dict.fromkeys(improvements))[:5]
    if not strengths:
        strengths = ["Completed the full interview flow and maintained answer consistency."]
    if not improvements:
        improvements = ["Continue practicing with deeper examples and quantified impact."]

    recommended_focus = improvements[0]

    return {
        "overall_score": overall,
        "strengths": strengths,
        "areas_to_improve": improvements,
        "recommended_focus": recommended_focus,
    }
