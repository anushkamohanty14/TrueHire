"""Phase 13 - Interview simulation helpers.

Question generation uses a two-layer approach:
  1. O*NET crosswalk converts user ability gaps → job-specific work activities (deterministic)
  2. Groq LLM generates natural questions grounded in those activities (with few-shot examples)
  Fallback: template-based generation if Groq is unavailable.

Answer evaluation uses a 4-dimension rubric scored by Groq (Clarity, Relevance, Depth,
Evidence — each 0–5). Overall score = mean of the 4 dimensions.
  Fallback: word-count + keyword heuristic if Groq is unavailable.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

# ── O*NET data paths ──────────────────────────────────────────────────────────

_ARCHIVE = Path(__file__).resolve().parents[4] / "Archive"

# ── LLM client ────────────────────────────────────────────────────────────────

def _llm_client():
    """Return an OpenAI-compatible Groq client, or None if key is absent."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
    except Exception:
        return None


def _llm_call(client, system: str, user: str, max_tokens: int = 1024) -> Optional[str]:
    """Call Groq and return the raw text, or None on any failure."""
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=max_tokens,
            temperature=0.4,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None


def _parse_json(raw: Optional[str]) -> Optional[Any]:
    """Strip markdown fences and parse JSON, returning None on failure."""
    if not raw:
        return None
    text = raw
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except Exception:
        return None


# ── Ability → Work Activities crosswalk (loaded once) ────────────────────────

def _build_ability_wa_lookup() -> Dict[str, List[str]]:
    try:
        import pandas as pd
        atwa = pd.read_csv(_ARCHIVE / "Abilities to Work Activities.csv")
        lookup: Dict[str, List[str]] = {}
        for _, row in atwa.iterrows():
            ab = str(row["Abilities Element Name"])
            wa = str(row["Work Activities Element Name"])
            lookup.setdefault(ab, []).append(wa)
        return lookup
    except Exception:
        return {}


def _build_job_top_activities(job_title: str, top_n: int = 12) -> List[str]:
    try:
        import pandas as pd
        from rapidfuzz import process as fuzz_process
        wa_df = pd.read_csv(_ARCHIVE / "workactivity_job.csv", index_col=0)
        titles = wa_df["Title"].unique().tolist()
        match = fuzz_process.extractOne(job_title, titles)
        if not match:
            return []
        matched = match[0]
        return (
            wa_df[wa_df["Title"] == matched]
            .sort_values("activity_score", ascending=False)
            .head(top_n)["Element Name"]
            .tolist()
        )
    except Exception:
        return []


_NCPT_TO_ONET: Dict[str, str] = {
    "deductive_reasoning":    "Deductive Reasoning",
    "mathematical_reasoning": "Mathematical Reasoning",
    "memorization":           "Memorization",
    "perceptual_speed":       "Perceptual Speed",
    "problem_sensitivity":    "Problem Sensitivity",
    "selective_attention":    "Selective Attention",
    "speed_of_closure":       "Speed of Closure",
    "time_sharing":           "Time Sharing",
    "written_comprehension":  "Written Comprehension",
}

_ABILITY_WA_LOOKUP: Dict[str, List[str]] = _build_ability_wa_lookup()

# ── Fallback templates ────────────────────────────────────────────────────────

_BEHAVIORAL_PROMPTS = [
    "Tell me about a time when {focus} was critical under pressure — what did you do and what was the outcome?",
    "Describe a situation where you had to excel at {focus} to deliver a successful result.",
    "Walk me through a specific example where {focus} made the difference between success and failure.",
    "Share a time you received feedback on your approach to {focus} — how did you adapt?",
    "Give me an example of when strong {focus} helped you navigate a particularly complex challenge.",
    "Tell me about a project where {focus} was a key factor — what steps did you take and what did you learn?",
    "Describe a moment where you had to manage competing priorities while maintaining quality in {focus}.",
]

_TECHNICAL_PROMPTS = [
    "How would you apply {skill} in a real {job_title} workflow?",
    "Explain your approach to debugging issues related to {skill}.",
    "What trade-offs do you consider when implementing solutions with {skill}?",
    "Describe a production scenario where {skill} can fail and how you would respond.",
    "How would you validate quality and reliability when working with {skill}?",
]

# ── LLM prompts ───────────────────────────────────────────────────────────────

_BEHAVIORAL_GENERATION_SYSTEM = """You are an expert interview coach generating behavioral interview questions.

Rules for a GOOD question:
- Ground it in a realistic workplace scenario, NOT an abstract cognitive ability name
- Use STAR-oriented language (describe a situation, your actions, the result)
- Be specific to what this role actually does, using the provided work activity focus
- Have a clear outcome orientation — ask what happened, what the impact was

Rules for a BAD question (never do this):
- "Tell me about a time you used Mathematical Reasoning" — naming an ability directly
- Generic questions that apply to any job
- Vague prompts with no outcome orientation

Few-shot examples:

ROLE: Data Analyst | FOCUS: Analyzing Data or Information
GOOD: "Walk me through a time you identified a non-obvious pattern in a dataset that changed a business decision — what was your analytical process and what was the outcome?"
BAD: "Tell me about a time you had to use Analytical Reasoning at work."

ROLE: Software Developer | FOCUS: Making Decisions and Solving Problems
GOOD: "Describe a situation where you had to choose between two technically valid approaches under a deadline — what factors drove your decision and how did the result validate your choice?"
BAD: "Describe a time when you demonstrated Problem Sensitivity."

ROLE: Judges, Magistrate Judges, and Magistrates | FOCUS: Evaluating Information to Determine Compliance with Standards
GOOD: "Tell me about a case where evaluating evidence against a legal standard led you to a non-obvious conclusion — how did you reason through it and what was the outcome?"
BAD: "Describe a time when you had to handle Deductive Reasoning under pressure."

Return ONLY a valid JSON array — no explanation, no markdown fences:
[
  {"question": "...", "ability_focus": "<the work activity this question targets>"},
  ...
]"""

_TECHNICAL_GENERATION_SYSTEM = """You are an expert technical interviewer generating role-specific questions.

Rules for a GOOD technical question:
- Tests practical knowledge, not textbook definitions
- Asks about trade-offs, failure modes, or production scenarios
- Is specific to how the skill is used in this particular role
- Scales in difficulty (difficulty 1 = fundamentals, 3 = production-depth)

Few-shot examples:

ROLE: Backend Engineer | SKILL: PostgreSQL | difficulty: 2
GOOD: "You're seeing intermittent slow queries under load. Walk me through how you'd diagnose and fix this in a production PostgreSQL database."
BAD: "What is a database index?"

ROLE: Data Scientist | SKILL: Machine Learning | difficulty: 3
GOOD: "Your model performs well in validation but degrades in production within two weeks. What are the three most likely causes and how would you build a monitoring system to catch this earlier?"
BAD: "Explain what overfitting is."

Return ONLY a valid JSON array — no explanation, no markdown fences:
[
  {"question": "...", "skill_focus": "<skill>", "difficulty": <1|2|3>},
  ...
]"""

_EVALUATION_SYSTEM = """You are an expert interview coach evaluating a candidate's answer.

Score the answer on exactly 4 dimensions, each an integer 0–5:

| Dimension | 0 | 3 | 5 |
|-----------|---|---|---|
| clarity | Incoherent or no structure | Generally followable | Clear STAR structure, easy to follow |
| relevance | Off-topic or ignores the question | Addresses it partially | Directly answers the question in the job context |
| depth | Surface-level with no reasoning | Some trade-offs or constraints mentioned | Shows genuine thinking: trade-offs, constraints, decisions |
| evidence | No examples or metrics | Vague reference to past work | Specific situation, concrete metric, measurable outcome |

Few-shot examples:

QUESTION: "Walk me through a time when Analyzing Data or Information made the difference between success and failure for a Data Analyst role."
WEAK ANSWER: "I analyze data at my job all the time and I'm pretty good at it. I usually use Excel."
RUBRIC: {"clarity": 2, "relevance": 1, "depth": 1, "evidence": 0, "strength": "Acknowledges the skill is part of their work.", "improvement": "Give a specific project: what the dataset was, what pattern you found, and what decision it changed — include a number."}

STRONG ANSWER: "During a quarterly review, our team saw a 15% drop in user retention. I built cohort analysis across 6 months and isolated that users who skipped the day-2 onboarding prompt churned at 80%. I presented this to product with a specific recommendation. After they added the prompt, 30-day retention rose by 22%. The key was narrowing from aggregate metrics to a specific behavioral trigger."
RUBRIC: {"clarity": 5, "relevance": 5, "depth": 4, "evidence": 5, "strength": "Excellent use of specific metrics, clear causal reasoning, and a measurable business outcome.", "improvement": "Briefly mention any stakeholder pushback you navigated or how you validated the causal direction."}

Return ONLY valid JSON — no explanation, no markdown fences:
{
  "clarity": <0-5>,
  "relevance": <0-5>,
  "depth": <0-5>,
  "evidence": <0-5>,
  "strength": "<one sentence: what the candidate did well>",
  "improvement": "<one actionable sentence: what to add or change next time>"
}"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _title_case(text: str) -> str:
    return " ".join(w.capitalize() for w in text.replace("_", " ").split())


def _gaps_to_work_activities(
    ability_gaps: List[str],
    job_top_activities: List[str],
) -> List[str]:
    """Convert NCPT ability gap names to job-relevant O*NET work activity names."""
    if not _ABILITY_WA_LOOKUP:
        return job_top_activities or ability_gaps

    gap_activities: List[str] = []
    for gap in ability_gaps:
        onet_name = _NCPT_TO_ONET.get(gap, _title_case(gap))
        gap_activities.extend(_ABILITY_WA_LOOKUP.get(onet_name, []))

    job_top_set = set(job_top_activities)
    tier1 = [a for a in gap_activities if a in job_top_set]
    seen = set(tier1)
    tier2 = [a for a in job_top_activities if a not in seen]
    seen.update(tier2)
    tier3 = [a for a in gap_activities if a not in seen]

    combined = tier1 + tier2 + tier3
    result: List[str] = []
    included: set = set()
    for a in combined:
        if a not in included:
            included.add(a)
            result.append(a)

    return result or job_top_activities or ["problem solving", "communication", "decision-making"]


# ── LLM question generation ───────────────────────────────────────────────────

def _generate_behavioral_llm(
    client,
    job_title: str,
    focus_pool: List[str],
    n: int,
) -> Optional[List[Dict[str, Any]]]:
    focus_list = ", ".join(focus_pool[:8])
    user_msg = (
        f"Generate {n} distinct behavioral interview questions for the role: {job_title}.\n"
        f"Work activity focus areas (use these as the basis for scenarios): {focus_list}.\n"
        f"Each question must target a different focus area from the list."
    )
    raw = _llm_call(client, _BEHAVIORAL_GENERATION_SYSTEM, user_msg, max_tokens=800)
    parsed = _parse_json(raw)
    if not isinstance(parsed, list) or len(parsed) == 0:
        return None
    out = []
    for i, item in enumerate(parsed[:n]):
        if not isinstance(item, dict) or "question" not in item:
            continue
        focus = item.get("ability_focus") or (focus_pool[i % len(focus_pool)] if focus_pool else "problem solving")
        out.append({
            "question": item["question"],
            "ability_focus": focus,
            "type": "behavioral",
        })
    return out if out else None


def _generate_technical_llm(
    client,
    job_title: str,
    gap_first: List[str],
    n: int,
) -> Optional[List[Dict[str, Any]]]:
    skills_list = ", ".join(gap_first[:10])
    user_msg = (
        f"Generate {n} technical interview questions for the role: {job_title}.\n"
        f"Skills to cover (prioritise in order): {skills_list}.\n"
        f"Vary the difficulty: some at 1 (fundamentals), some at 2 (applied), some at 3 (production-depth)."
    )
    raw = _llm_call(client, _TECHNICAL_GENERATION_SYSTEM, user_msg, max_tokens=800)
    parsed = _parse_json(raw)
    if not isinstance(parsed, list) or len(parsed) == 0:
        return None
    out = []
    for i, item in enumerate(parsed[:n]):
        if not isinstance(item, dict) or "question" not in item:
            continue
        skill = item.get("skill_focus") or (gap_first[i % len(gap_first)] if gap_first else "system design")
        out.append({
            "question": item["question"],
            "skill_focus": _title_case(str(skill)),
            "difficulty": max(1, min(3, int(item.get("difficulty", 1 + (i % 3))))),
            "type": "technical",
        })
    return out if out else None


# ── LLM answer evaluation ─────────────────────────────────────────────────────

def _evaluate_answer_llm(
    client,
    question: str,
    answer: str,
    job_context: str,
    ability_focus: Optional[str],
) -> Optional[Dict[str, Any]]:
    focus_line = f"Competency focus: {ability_focus}" if ability_focus else ""
    user_msg = (
        f"Role context: {job_context}\n"
        f"{focus_line}\n\n"
        f"QUESTION: {question}\n\n"
        f"CANDIDATE'S ANSWER: {answer or '(no answer provided)'}"
    )
    raw = _llm_call(client, _EVALUATION_SYSTEM, user_msg, max_tokens=300)
    parsed = _parse_json(raw)
    if not isinstance(parsed, dict):
        return None
    required = {"clarity", "relevance", "depth", "evidence", "strength", "improvement"}
    if not required.issubset(parsed.keys()):
        return None
    try:
        rubric = {
            "clarity":   max(0, min(5, int(parsed["clarity"]))),
            "relevance": max(0, min(5, int(parsed["relevance"]))),
            "depth":     max(0, min(5, int(parsed["depth"]))),
            "evidence":  max(0, min(5, int(parsed["evidence"]))),
        }
    except (TypeError, ValueError):
        return None

    overall = round(mean(rubric.values()), 2)
    return {
        "score": overall,
        "rubric": rubric,
        "feedback": _rubric_to_feedback(rubric, job_context),
        "strength": str(parsed.get("strength", "")),
        "improvement": str(parsed.get("improvement", "")),
    }


def _rubric_to_feedback(rubric: Dict[str, int], job_context: str) -> str:
    """Turn rubric dimension scores into a single narrative feedback sentence."""
    overall = mean(rubric.values())
    weak = [k for k, v in rubric.items() if v <= 2]
    if overall >= 4.0:
        return f"Strong response for {job_context}. You demonstrated clear reasoning with concrete evidence."
    if weak:
        labels = {"clarity": "structure", "relevance": "relevance to the question",
                  "depth": "depth of reasoning", "evidence": "use of specific examples"}
        weak_str = " and ".join(labels[w] for w in weak[:2])
        return f"Your answer would benefit from stronger {weak_str}."
    return "Solid answer — adding one concrete metric would push it to the next level."


# ── Heuristic fallback ────────────────────────────────────────────────────────

def _evaluate_answer_heuristic(
    question: str,
    answer: str,
    question_type: str,
    job_context: str,
    ability_focus: Optional[str],
) -> Dict[str, Any]:
    text = (answer or "").strip()
    words = text.split()
    word_count = len(words)

    score = 1
    if word_count >= 25: score = 2
    if word_count >= 45: score = 3
    if word_count >= 80: score = 4
    if word_count >= 120: score = 5

    lower = text.lower()
    signal_terms = ["impact", "result", "outcome", "metric", "improved", "trade-off"]
    signal_hits = sum(1 for term in signal_terms if term in lower)
    if signal_hits >= 3 and score < 5:
        score += 1

    focus = ability_focus or "this competency"
    strength = "Good use of measurable outcomes" if signal_hits >= 3 else "Clear, role-aware explanation"

    if score <= 2:
        feedback = (f"Your answer is brief for a {question_type} response. Add more context, "
                    "actions you personally took, and the final impact.")
        improvement = f"Use a STAR structure and tie examples back to {focus}."
    elif score == 3:
        feedback = ("Your response is directionally strong but can be more specific about "
                    "trade-offs, constraints, and measurable results.")
        improvement = f"Add one concrete metric and explicitly connect it to {focus}."
    else:
        feedback = (f"Strong answer for {job_context}. You gave useful detail and relevant "
                    "problem-solving rationale.")
        improvement = "Keep the same structure, and close with business/user impact in one sentence."

    return {
        "score": float(max(1, min(5, score))),
        "rubric": None,
        "feedback": feedback,
        "strength": strength,
        "improvement": improvement,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def generate_behavioral_questions(
    job_title: str,
    top_work_activities: List[str],
    user_ability_gaps: List[str],
    n: int = 5,
) -> List[Dict[str, Any]]:
    """Generate behavioral questions grounded in O*NET work activities.

    Uses Groq LLM with few-shot examples when available; falls back to
    deterministic templates otherwise.
    """
    job_activities = top_work_activities or _build_job_top_activities(job_title)
    focus_pool = _gaps_to_work_activities(user_ability_gaps, job_activities)

    client = _llm_client()
    if client:
        result = _generate_behavioral_llm(client, job_title, focus_pool, n)
        if result:
            return result

    # Template fallback
    out: List[Dict[str, Any]] = []
    for i in range(max(1, n)):
        focus = focus_pool[i % len(focus_pool)]
        prompt = _BEHAVIORAL_PROMPTS[i % len(_BEHAVIORAL_PROMPTS)].format(focus=focus)
        out.append({"question": f"For the role {job_title}: {prompt}", "ability_focus": focus, "type": "behavioral"})
    return out


def generate_technical_questions(
    job_title: str,
    user_skills: List[str],
    required_skills: List[str],
    user_gaps: List[str],
    n: int = 5,
) -> List[Dict[str, Any]]:
    """Generate technical questions, gap-first, using LLM with few-shot examples."""
    gap_first = [*user_gaps, *required_skills] or user_skills[:] or ["system design", "testing", "data modeling"]

    client = _llm_client()
    if client:
        result = _generate_technical_llm(client, job_title, gap_first, n)
        if result:
            return result

    # Template fallback
    out: List[Dict[str, Any]] = []
    for i in range(max(1, n)):
        skill = gap_first[i % len(gap_first)]
        prompt = _TECHNICAL_PROMPTS[i % len(_TECHNICAL_PROMPTS)].format(skill=skill, job_title=job_title)
        out.append({"question": prompt, "skill_focus": _title_case(str(skill)),
                    "difficulty": min(3, 1 + (i % 3)), "type": "technical"})
    return out


def evaluate_answer(
    question: str,
    answer: str,
    question_type: str,
    job_context: str,
    ability_focus: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate an answer with a 4-dimension LLM rubric (Clarity/Relevance/Depth/Evidence).

    Falls back to word-count heuristic if Groq is unavailable.
    """
    client = _llm_client()
    if client:
        result = _evaluate_answer_llm(client, question, answer, job_context, ability_focus)
        if result:
            return result

    return _evaluate_answer_heuristic(question, answer, question_type, job_context, ability_focus)


def generate_session_summary(session: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize an interview session with dimensional coaching where rubric data exists."""
    questions = session.get("questions", []) or []
    scored = [q for q in questions if isinstance(q.get("score"), (int, float))]

    if not scored:
        return {
            "overall_score": 0.0,
            "strengths": [],
            "areas_to_improve": ["Complete the interview to unlock feedback."],
            "recommended_focus": "Practice concise STAR-format responses.",
            "rubric_averages": None,
        }

    overall = round(mean(float(q["score"]) for q in scored), 2)

    # Aggregate rubric dimension averages if LLM evaluation was used
    rubric_scored = [q for q in scored if isinstance(q.get("rubric"), dict)]
    rubric_avgs: Optional[Dict[str, float]] = None
    if rubric_scored:
        dims = ["clarity", "relevance", "depth", "evidence"]
        rubric_avgs = {
            d: round(mean(q["rubric"].get(d, 0) for q in rubric_scored), 2)
            for d in dims
        }

    strengths = []
    improvements = []
    for q in scored:
        if q.get("strength"):
            strengths.append(str(q["strength"]))
        if q.get("score", 5) <= 3:
            if q.get("improvement"):
                improvements.append(str(q["improvement"]))
            else:
                focus = q.get("ability_focus") or q.get("skill_focus") or "communication"
                improvements.append(f"Build stronger examples around {focus}.")

    strengths = list(dict.fromkeys(strengths))[:5]
    improvements = list(dict.fromkeys(improvements))[:5]
    if not strengths:
        strengths = ["Completed the full interview and maintained answer consistency."]
    if not improvements:
        improvements = ["Continue practising with deeper examples and quantified impact."]

    # If rubric data exists, surface the weakest dimension as the recommended focus
    recommended = improvements[0]
    if rubric_avgs:
        weakest_dim = min(rubric_avgs, key=rubric_avgs.__getitem__)
        dim_advice = {
            "clarity": "Work on structuring answers with a clear Situation → Action → Result flow.",
            "relevance": "Keep answers tightly focused on the specific question and role context.",
            "depth": "Add more reasoning: explain trade-offs, constraints, and why you chose your approach.",
            "evidence": "Anchor every answer with a specific project, metric, or measurable outcome.",
        }
        recommended = dim_advice.get(weakest_dim, recommended)

    return {
        "overall_score": overall,
        "strengths": strengths,
        "areas_to_improve": improvements,
        "recommended_focus": recommended,
        "rubric_averages": rubric_avgs,
    }
