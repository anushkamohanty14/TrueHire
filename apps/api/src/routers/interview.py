import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.src.core.pipelines.phase13_interview import (
    evaluate_answer,
    generate_behavioral_questions,
    generate_session_summary,
    generate_technical_questions,
)
from core.src.core.pipelines.phase7_hybrid_recommendation import HybridRecommender
from core.src.core.pipelines.phase6_skill_matching import build_tech_matrix
from core.src.core.storage.mongo_store import MongoUserStore, _get_auth_collection

router = APIRouter(prefix="/api/interview", tags=["interview"])
recommender = HybridRecommender()


class StartRequest(BaseModel):
    job_title: str
    mode: str = "mixed"  # "behavioral" | "technical" | "mixed"


class RespondRequest(BaseModel):
    session_id: str
    question_id: int
    answer: str


def _sessions_col():
    import os
    from pymongo import MongoClient

    uri = os.environ.get("MONGODB_URI")
    db_name = os.environ.get("MONGODB_DB", "career_recommender")
    return MongoClient(uri)[db_name]["interview_sessions"]


@router.post("/start")
def start_interview(payload: StartRequest, token: str = "") -> Dict[str, Any]:
    auth_col = _get_auth_collection()
    user_doc = auth_col.find_one({"token": token})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = user_doc["username"]

    store = MongoUserStore()
    ctx = store.get_interview_context(user_id)
    ability_gaps = ctx["cognitive_profile"].get("areas_for_improvement", [])
    user_skills = ctx["technical_profile"].get("skills", [])
    ability_percentiles = ctx["cognitive_profile"].get("ability_percentiles", {})

    job_info = recommender.explain_job(payload.job_title, ability_percentiles)
    top_work_activities = job_info.get("top_job_activities", [])

    try:
        tech_matrix = build_tech_matrix()
        from rapidfuzz import process as fuzz_process

        match = fuzz_process.extractOne(payload.job_title, tech_matrix.index.tolist())
        matched_job = match[0] if match else payload.job_title
        required_skills = (
            tech_matrix.loc[matched_job]
            .sort_values(ascending=False)
            .head(15)
            .index.tolist()
        )
        user_skill_set = {u.lower() for u in user_skills}
        user_gaps = [s for s in required_skills if s.lower() not in user_skill_set][:8]
    except Exception:
        required_skills = []
        user_gaps = []

    questions = []
    if payload.mode in ("behavioral", "mixed"):
        n_b = 5 if payload.mode == "behavioral" else 3
        questions += generate_behavioral_questions(payload.job_title, top_work_activities, ability_gaps, n=n_b)
    if payload.mode in ("technical", "mixed"):
        n_t = 5 if payload.mode == "technical" else 2
        questions += generate_technical_questions(payload.job_title, user_skills, required_skills, user_gaps, n=n_t)

    if not questions:
        raise HTTPException(status_code=400, detail="Could not generate interview questions")

    for i, q in enumerate(questions):
        q["id"] = i + 1
        q["user_answer"] = None
        q["feedback"] = None
        q["score"] = None

    session = {
        "session_id": uuid.uuid4().hex,
        "user_id": user_id,
        "job_title": payload.job_title,
        "mode": payload.mode,
        "status": "active",
        "questions": questions,
        "overall_score": None,
        "summary": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }
    _sessions_col().insert_one({**session, "_id": session["session_id"]})

    return {
        "session_id": session["session_id"],
        "job_title": payload.job_title,
        "total_questions": len(questions),
        "first_question": {k: questions[0][k] for k in ("id", "question", "type")},
    }


@router.post("/respond")
def respond(payload: RespondRequest, token: str = "") -> Dict[str, Any]:
    auth_col = _get_auth_collection()
    user_doc = auth_col.find_one({"token": token})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    col = _sessions_col()
    session = col.find_one({"session_id": payload.session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("user_id") != user_doc["username"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    if session["status"] == "complete":
        raise HTTPException(status_code=400, detail="Session already complete")

    questions = session["questions"]
    q = next((q for q in questions if q["id"] == payload.question_id), None)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    result = evaluate_answer(
        question=q["question"],
        answer=payload.answer,
        question_type=q.get("type", "behavioral"),
        job_context=session["job_title"],
        ability_focus=q.get("ability_focus") or q.get("skill_focus"),
    )
    q["user_answer"] = payload.answer
    q["score"] = result["score"]
    q["feedback"] = result["feedback"]
    q["strength"] = result.get("strength", "")
    q["improvement"] = result.get("improvement", "")

    next_q = next((nq for nq in questions if nq["id"] > payload.question_id and not nq["user_answer"]), None)
    all_answered = all(item["user_answer"] for item in questions)
    status = "complete" if all_answered else "active"
    completed_at = datetime.now(timezone.utc).isoformat() if all_answered else None

    col.update_one(
        {"session_id": payload.session_id},
        {"$set": {"questions": questions, "status": status, "completed_at": completed_at}},
    )

    return {
        "feedback": result["feedback"],
        "score": result["score"],
        "strength": result.get("strength", ""),
        "improvement": result.get("improvement", ""),
        "next_question": {k: next_q[k] for k in ("id", "question", "type")} if next_q else None,
        "session_complete": all_answered,
    }


@router.get("/summary/{session_id}")
def get_summary(session_id: str, token: str = "") -> Dict[str, Any]:
    auth_col = _get_auth_collection()
    user_doc = auth_col.find_one({"token": token})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    session = _sessions_col().find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("user_id") != user_doc["username"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    session.pop("_id", None)
    if session.get("summary"):
        return session["summary"]

    summary = generate_session_summary(session)
    _sessions_col().update_one(
        {"session_id": session_id},
        {"$set": {"summary": summary, "overall_score": summary["overall_score"]}},
    )
    return summary


@router.get("/history")
def get_history(token: str = "") -> Dict[str, Any]:
    auth_col = _get_auth_collection()
    user_doc = auth_col.find_one({"token": token})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    sessions = list(
        _sessions_col().find(
            {"user_id": user_doc["username"]},
            {"_id": 0, "questions": 0},
            sort=[("started_at", -1)],
            limit=20,
        )
    )
    return {"sessions": sessions}
