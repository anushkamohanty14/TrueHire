"""Cognitive assessment router.

GET  /api/cognitive/tasks   — generate 18 task items (2 per ability)
POST /api/cognitive/assess  — score responses and store results
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from statistics import mean
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.src.core.scoring import ScoringEngine
from core.src.core.storage.mongo_store import MongoUserStore
from core.src.core.tasks import (
    DigitSpanGenerator,
    MathReasoningGenerator,
    RuleViolationGenerator,
    SequenceCompletionGenerator,
    StroopGenerator,
    SyllogismGenerator,
    SymbolSearchGenerator,
    TimeShareGenerator,
    WrittenComprehensionGenerator,
)
from core.src.core.tasks.base import TaskItem, TaskResponse

router = APIRouter(prefix="/api/cognitive", tags=["cognitive"])

# ── Generators ────────────────────────────────────────────────────────────────

_GENERATORS = [
    SyllogismGenerator(),
    MathReasoningGenerator(),
    DigitSpanGenerator(),
    SymbolSearchGenerator(),
    RuleViolationGenerator(),
    StroopGenerator(),
    SequenceCompletionGenerator(),
    TimeShareGenerator(),
    WrittenComprehensionGenerator(),
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class ResponseItem(BaseModel):
    ability: str
    is_correct: bool
    reaction_time_ms: float


class AssessRequest(BaseModel):
    user_id: str
    responses: List[ResponseItem]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _task_to_dict(task: TaskItem) -> Dict[str, Any]:
    return {
        "ability": task.ability,
        "task_type": task.task_type,
        "question": task.question,
        "correct_answer": task.correct_answer,
        "difficulty": task.difficulty,
        "metadata": task.metadata,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/tasks")
def get_tasks(token: str = "") -> List[Dict[str, Any]]:
    """Generate 2 tasks per ability = 18 total."""
    tasks: List[Dict[str, Any]] = []
    for gen in _GENERATORS:
        items = gen.generate(difficulty=2, n=2)
        tasks.extend(_task_to_dict(t) for t in items)
    return tasks


@router.post("/assess")
def assess(payload: AssessRequest, token: str = "") -> Dict[str, Any]:
    """Score user responses and persist to MongoDB."""
    if not payload.responses:
        raise HTTPException(status_code=400, detail="No responses provided")

    # Build minimal TaskResponse objects
    task_responses: List[TaskResponse] = []
    for r in payload.responses:
        task_item = TaskItem(
            ability=r.ability,
            task_type="",
            question={},
            correct_answer="",
            difficulty=1,
        )
        tr = TaskResponse(
            task_item=task_item,
            user_answer="",
            reaction_time_ms=r.reaction_time_ms,
            is_correct=r.is_correct,
        )
        task_responses.append(tr)

    engine = ScoringEngine()
    profile_obj = engine.score_session(
        user_id=payload.user_id,
        responses=task_responses,
    )

    ability_percentiles = profile_obj.ability_percentiles
    readiness_score = mean(ability_percentiles.values()) if ability_percentiles else 0.0

    raw_responses = [
        {"ability": r.ability, "is_correct": r.is_correct, "reaction_time_ms": r.reaction_time_ms}
        for r in payload.responses
    ]

    # Atomically update latest scores + append to history
    store = MongoUserStore()
    store.save_assessment(
        user_id=payload.user_id,
        ability_percentiles=ability_percentiles,
        readiness_score=readiness_score,
        task_responses=raw_responses,
    )

    return {
        "user_id": payload.user_id,
        "ability_percentiles": ability_percentiles,
        "readiness_score": round(readiness_score, 2),
    }


@router.get("/history/{user_id}")
def get_history(user_id: str, token: str = "") -> Dict[str, Any]:
    """Return all past assessment attempts for a user, newest first."""
    store = MongoUserStore()
    history = store.get_assessment_history(user_id)
    return {"user_id": user_id, "attempt_count": len(history), "attempts": history}
