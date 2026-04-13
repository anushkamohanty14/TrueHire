"""Interview context builder — LLM pipeline input.

This module is the single entry point for preparing user data for the
interview simulation pipeline. It reads from MongoDB and returns a
structured dict (and a formatted prompt preamble) ready for LLM injection.

Usage
-----
    from core.src.core.interview_context import build_interview_context

    ctx = build_interview_context(user_id="alice@example.com")
    # ctx["prompt_preamble"] → ready-to-inject system prompt fragment
    # ctx["raw"]             → full structured dict for fine-tuning / logging

The context is intentionally flat and human-readable so it works both as a
system-prompt injection AND as a fine-tuning example record.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.src.core.storage.mongo_store import MongoUserStore


# ── Ability metadata ──────────────────────────────────────────────────────────

_ABILITY_META = {
    "deductive_reasoning": {
        "label": "Deductive Reasoning",
        "description": "draws logical conclusions from given premises",
    },
    "mathematical_reasoning": {
        "label": "Mathematical Reasoning",
        "description": "solves quantitative and numerical problems",
    },
    "memorization": {
        "label": "Memorization",
        "description": "retains and recalls information accurately",
    },
    "perceptual_speed": {
        "label": "Perceptual Speed",
        "description": "processes and compares visual information quickly",
    },
    "problem_sensitivity": {
        "label": "Problem Sensitivity",
        "description": "identifies issues and potential problems early",
    },
    "selective_attention": {
        "label": "Selective Attention",
        "description": "focuses on relevant information and filters distractions",
    },
    "speed_of_closure": {
        "label": "Speed of Closure",
        "description": "rapidly integrates partial information into a whole picture",
    },
    "time_sharing": {
        "label": "Time Sharing",
        "description": "manages multiple tasks or information streams simultaneously",
    },
    "written_comprehension": {
        "label": "Written Comprehension",
        "description": "understands written text and instructions accurately",
    },
}

_PERCENTILE_TIER = {
    (80, 101): ("strong", "a notable strength"),
    (60, 80):  ("good",   "above average"),
    (40, 60):  ("moderate", "around average"),
    (0,  40):  ("developing", "an area for growth"),
}


def _tier_label(percentile: float) -> tuple[str, str]:
    for (lo, hi), labels in _PERCENTILE_TIER.items():
        if lo <= percentile < hi:
            return labels
    return ("developing", "an area for growth")


# ── Main builder ──────────────────────────────────────────────────────────────

def build_interview_context(user_id: str) -> Dict[str, Any]:
    """Build a complete interview context dict for *user_id*.

    Returns
    -------
    dict with keys:
        ``raw``            — full structured data (for logging / fine-tuning)
        ``prompt_preamble``— ready-to-inject LLM system prompt fragment
        ``has_assessment`` — bool: cognitive data is available
        ``has_resume``     — bool: resume data is available
        ``is_complete``    — bool: both assessment and resume are present
    """
    store = MongoUserStore()
    ctx = store.get_interview_context(user_id)

    cognitive = ctx["cognitive_profile"]
    technical = ctx["technical_profile"]

    has_assessment = cognitive.get("readiness_score") is not None
    has_resume = bool(technical.get("skills"))
    is_complete = has_assessment and has_resume

    prompt_preamble = _build_prompt_preamble(user_id, cognitive, technical)

    return {
        "raw": ctx,
        "prompt_preamble": prompt_preamble,
        "has_assessment": has_assessment,
        "has_resume": has_resume,
        "is_complete": is_complete,
    }


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt_preamble(
    user_id: str,
    cognitive: Dict[str, Any],
    technical: Dict[str, Any],
) -> str:
    """Return a system-prompt fragment that personalises the interview session."""
    lines: list[str] = []

    lines.append("## Candidate Profile")
    lines.append(f"User ID: {user_id}")
    lines.append("")

    # ── Cognitive section ──
    if cognitive.get("readiness_score") is not None:
        score = round(cognitive["readiness_score"])
        lines.append(f"### Cognitive Readiness Score: {score}%")

        percentiles = cognitive.get("ability_percentiles", {})
        if percentiles:
            lines.append("#### Cognitive Ability Breakdown")
            for key, meta in _ABILITY_META.items():
                pct = percentiles.get(key)
                if pct is None:
                    continue
                tier, tier_desc = _tier_label(pct)
                lines.append(
                    f"- **{meta['label']}** ({pct:.0f}th percentile, {tier_desc}): "
                    f"{meta['description']}"
                )

        strengths = cognitive.get("strengths", [])
        improvements = cognitive.get("areas_for_improvement", [])
        if strengths:
            lines.append(f"\n**Cognitive Strengths:** {', '.join(strengths)}")
        if improvements:
            lines.append(f"**Areas for Development:** {', '.join(improvements)}")
    else:
        lines.append("### Cognitive Profile: Not yet assessed")

    lines.append("")

    # ── Technical section ──
    lines.append("### Technical Profile")

    skills = technical.get("skills", [])
    if skills:
        lines.append(f"**Skills ({len(skills)}):** {', '.join(skills)}")
    else:
        lines.append("**Skills:** Not yet extracted from resume")

    education = technical.get("education", [])
    if education:
        lines.append(f"**Education:** {'; '.join(education)}")

    certifications = technical.get("certifications", [])
    if certifications:
        lines.append(f"**Certifications:** {', '.join(certifications)}")

    exp_years = technical.get("experience_years")
    if exp_years is not None:
        lines.append(f"**Estimated Experience:** {exp_years} year(s)")

    lines.append("")

    # ── Interviewer instructions ──
    lines.append("### Interview Guidance")
    lines.append(
        "Use the cognitive profile above to calibrate question complexity. "
        "For abilities flagged as 'developing', probe with supportive follow-up questions. "
        "For abilities flagged as 'strong', challenge with deeper technical or analytical questions. "
        "Tailor technical questions to the candidate's skill set listed above."
    )

    if not skills and cognitive.get("readiness_score") is None:
        lines.append(
            "\n**Note:** No cognitive or resume data is available yet. "
            "Conduct a general exploratory interview."
        )

    return "\n".join(lines)
