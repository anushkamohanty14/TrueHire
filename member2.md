TrueHire — Member 2 Implementation Instructions
Backend + Frontend tasks required to complete the interview simulation and resume enhancement features.
All AI/ML pipeline code (Member 1) is already done. Your job is to wire it up.
────────────────────────────────────────────────────────────
What Member 1 Built (Your Inputs)
phase5_resume_processing.py — process_resume() now returns:
skills              list[str]   technical skills
soft_skills         list[str]   soft skills  (NEW)
education           list[str]   degree strings
certifications      list[str]   cert names
experience_years    float|None
past_job_titles     list[str]   previous job titles  (NEW)
method              str         "llm" or "rules"
phase13_interview.py — four functions ready to import:
generate_behavioral_questions(job_title, top_work_activities, user_ability_gaps, n=5)
  → list[{question, ability_focus, type:"behavioral"}]

generate_technical_questions(job_title, user_skills, required_skills, user_gaps, n=5)
  → list[{question, skill_focus, difficulty:1-3, type:"technical"}]

evaluate_answer(question, answer, question_type, job_context, ability_focus=None)
  → {score:1-5, feedback, strength, improvement}

generate_session_summary(session)
  → {overall_score, strengths, areas_to_improve, recommended_focus}
mongo_store.get_interview_context(user_id) already exists and returns:
{
  "cognitive_profile": {
    "ability_percentiles": {...},
    "areas_for_improvement": ["Mathematical Reasoning", ...]  ← pass to behavioral questions
  },
  "technical_profile": {
    "skills": [...]   ← pass to technical questions as user_skills
  }
}
────────────────────────────────────────────────────────────
Files to Create / Modify
File	Action
core/src/core/storage/mongo_store.py	Add soft_skills/past_job_titles to save_resume_extraction + add _get_auth_collection() helper
apps/api/src/routers/users.py	Pass new fields to save_resume_extraction
apps/web/static/js/resume.js	Render soft skills and past job titles
apps/web/static/js/assessments.js	Redirect to results.html after assessment completion
apps/api/src/routers/interview.py	CREATE — 4 endpoints (start, respond, summary, history)
apps/api/src/main.py	Register interview router
apps/web/static/interview.html	Replace coming-soon content with 3-screen layout
apps/web/static/js/interview.js	CREATE — full Q&A state machine
All HTML pages	Add My Results nav link; fix Interview link to /interview.html

────────────────────────────────────────────────────────────
Task 1 — Update mongo_store.save_resume_extraction()
File: core/src/core/storage/mongo_store.py
Add soft_skills and past_job_titles to the method signature and the $set block:
def save_resume_extraction(
    self,
    user_id: str,
    file_name: str,
    skills: List[str],
    education: List[str],
    certifications: List[str],
    experience_years: Optional[float],
    soft_skills: List[str] = None,        # ADD
    past_job_titles: List[str] = None,    # ADD
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    resume_doc = {
        "uploaded_at": now,
        "file_name": file_name,
        "skills": skills,
        "education": education,
        "certifications": certifications,
        "experience_years": experience_years,
        "soft_skills": soft_skills or [],          # ADD
        "past_job_titles": past_job_titles or [],  # ADD
    }
    self._col.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "latest_resume": resume_doc,
                "resume_skills": skills,
                "resume_education": education,
                "resume_certifications": certifications,
                "resume_experience_years": experience_years,
                "resume_soft_skills": soft_skills or [],          # ADD
                "resume_past_job_titles": past_job_titles or [],  # ADD
            },
            # $setOnInsert stays the same
        },
        upsert=True,
    )
Also add this helper function near the top of the file (alongside _get_collection):
def _get_auth_collection() -> Collection:
    uri = os.environ.get("MONGODB_URI")
    db_name = os.environ.get("MONGODB_DB", "career_recommender")
    return MongoClient(uri)[db_name]["auth_users"]
────────────────────────────────────────────────────────────
Task 2 — Update the Resume Upload Router
File: apps/api/src/routers/users.py  (POST /users/resume endpoint)
After result = process_resume(...), add the two new fields and pass them to save_resume_extraction:
result = process_resume(metadata["saved_path"])
metadata["extracted_skills"] = result.skills
metadata["extraction_method"] = result.method
metadata["education"] = result.education
metadata["certifications"] = result.certifications
metadata["experience_years"] = result.experience_years
metadata["soft_skills"] = result.soft_skills          # ADD
metadata["past_job_titles"] = result.past_job_titles  # ADD

store.save_resume_extraction(
    user_id=user_id,
    file_name=file.filename or "resume.bin",
    skills=result.skills,
    education=result.education,
    certifications=result.certifications,
    experience_years=result.experience_years,
    soft_skills=result.soft_skills,          # ADD
    past_job_titles=result.past_job_titles,  # ADD
)
────────────────────────────────────────────────────────────
Task 3 — Update resume.js to Display New Fields
File: apps/web/static/js/resume.js
After rendering skills, add sections for the two new fields. The data comes from resume_soft_skills and resume_past_job_titles on the profile object:
const softSkills = profile.resume_soft_skills || [];
const jobTitles = profile.resume_past_job_titles || [];

// Render soft skills as chips (same style as technical skills)
if (softSkills.length) {
  // add a section header + chip list
}

// Render past job titles as a simple list
if (jobTitles.length) {
  // add a section header + bullet list
}
────────────────────────────────────────────────────────────
Task 4 — Fix Assessment Completion Redirect
File: apps/web/static/js/assessments.js
Find where POST /api/cognitive/assess succeeds. Change the redirect from jobs.html to results.html:
// After successful assess POST:
const score = Math.round(data.readiness_score);
setTimeout(() => {
  window.location.href = '/results.html?score=' + score;
}, 3000);
────────────────────────────────────────────────────────────
Task 5 — Create the Interview Router
New file: apps/api/src/routers/interview.py
Full implementation:
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
    ability_gaps = ctx["cognitive_profile"]["areas_for_improvement"]
    user_skills = ctx["technical_profile"]["skills"]
    ability_percentiles = ctx["cognitive_profile"]["ability_percentiles"]

    job_info = recommender.explain_job(payload.job_title, ability_percentiles)
    top_work_activities = job_info.get("top_job_activities", [])

    try:
        tech_matrix = build_tech_matrix()
        from rapidfuzz import process as fuzz_process
        match = fuzz_process.extractOne(payload.job_title, tech_matrix.columns.tolist())
        matched_job = match[0] if match else payload.job_title
        required_skills = tech_matrix[matched_job].dropna().index.tolist()[:15]
        user_gaps = [s for s in required_skills if s.lower() not in [u.lower() for u in user_skills]][:8]
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
    col = _sessions_col()
    session = col.find_one({"session_id": payload.session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
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
    all_answered = all(q["user_answer"] for q in questions)
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
    session = _sessions_col().find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
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
    sessions = list(_sessions_col().find(
        {"user_id": user_doc["username"]},
        {"_id": 0, "questions": 0},
        sort=[("started_at", -1)],
        limit=20,
    ))
    return {"sessions": sessions}
────────────────────────────────────────────────────────────
Task 6 — Register Interview Router in main.py
File: apps/api/src/main.py
Add two lines:
from .routers.interview import router as interview_router  # ADD with other imports

app.include_router(interview_router)  # ADD after the other include_router calls
────────────────────────────────────────────────────────────
Task 7 — Complete interview.html
File: apps/web/static/interview.html
Keep the existing topnav and sidebar unchanged. Replace the entire <main> block (currently the coming-soon content) with a 3-screen layout:
Screen 1: Setup (#screen-setup)
•	Dropdown populated from GET /api/recommendations/{user_id} (top 5 jobs)
•	Mode selector: Mixed / Behavioral / Technical buttons
•	Start Interview button → calls POST /api/interview/start
Screen 2: Q&A (#screen-qa)
•	Progress indicator: "Question 2 of 5"
•	Type badge: Behavioral / Technical
•	Question text + focus label (ability or skill)
•	Textarea for answer
•	Submit Answer button → calls POST /api/interview/respond
•	Feedback panel slides in after submit: score badge, feedback, strength, improvement
•	Next Question button (or "View Summary" on last question)
Screen 3: Summary (#screen-summary)
•	Overall score (e.g. 3.8 / 5)
•	Strengths list
•	Areas to Improve list
•	Recommended Focus statement
•	Practice Again + Back to Jobs buttons
Shared: Loading spinner (#loading)
•	Shown during API calls with a message (e.g. "Generating questions…")
Also remove the badge-soon CSS class and the coming-soon badge from the file.
Add <script src="/js/interview.js"></script> before </body>.
────────────────────────────────────────────────────────────
Task 8 — Create interview.js
New file: apps/web/static/js/interview.js
State machine: setup → qa → summary. Full implementation:
let sessionId = null;
let currentQuestionId = null;
let selectedMode = 'mixed';
let jobTitle = null;

function show(screenId) {
  ['screen-setup','screen-qa','screen-summary','loading'].forEach(id => {
    document.getElementById(id).style.display = id === screenId ? '' : 'none';
  });
}

function showLoading(msg) {
  document.getElementById('loading-msg').textContent = msg || 'Loading...';
  show('loading');
}

async function loadJobOptions() {
  try {
    const data = await apiGet(\`/recommendations/${getUserId()}?limit=5\`);
    const select = document.getElementById('job-select');
    (data.recommendations || data).slice(0, 5).forEach(job => {
      const opt = document.createElement('option');
      opt.value = job.job_title;
      opt.textContent = job.job_title;
      select.appendChild(opt);
    });
  } catch {
    document.getElementById('job-select').innerHTML =
      '<option>Software Developers</option><option>Data Scientists</option>';
  }
}

document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedMode = btn.dataset.mode;
  });
});

document.getElementById('btn-start').addEventListener('click', async () => {
  jobTitle = document.getElementById('job-select').value;
  if (!jobTitle) return;
  showLoading('Generating interview questions…');
  try {
    const data = await apiPost(\`/interview/start?token=${getToken()}\`,
      { job_title: jobTitle, mode: selectedMode });
    sessionId = data.session_id;
    showQuestion(data.first_question, 1, data.total_questions);
  } catch (e) {
    show('screen-setup');
    const err = document.getElementById('setup-error');
    err.textContent = e.message || 'Failed to start. Try again.';
    err.style.display = '';
  }
});

function showQuestion(q, num, total) {
  show('screen-qa');
  currentQuestionId = q.id;
  document.getElementById('qa-progress').textContent = \`Question ${num} of ${total}\`;
  document.getElementById('qa-type-badge').textContent = q.type;
  document.getElementById('qa-question').textContent = q.question;
  document.getElementById('qa-focus').textContent = q.ability_focus || q.skill_focus || '';
  document.getElementById('qa-answer').value = '';
  document.getElementById('feedback-panel').style.display = 'none';
  document.getElementById('btn-submit').style.display = '';
}

document.getElementById('btn-submit').addEventListener('click', async () => {
  const answer = document.getElementById('qa-answer').value.trim();
  if (!answer) return;
  document.getElementById('btn-submit').disabled = true;
  document.getElementById('btn-submit').textContent = 'Evaluating…';
  try {
    const data = await apiPost(\`/interview/respond?token=${getToken()}\`, {
      session_id: sessionId, question_id: currentQuestionId, answer,
    });
    document.getElementById('fb-score').textContent = data.score;
    document.getElementById('fb-feedback').textContent = data.feedback;
    document.getElementById('fb-strength').textContent = data.strength ? '✓ ' + data.strength : '';
    document.getElementById('fb-improvement').textContent = data.improvement ? '→ ' + data.improvement : '';
    document.getElementById('feedback-panel').style.display = '';
    document.getElementById('btn-submit').style.display = 'none';

    if (data.session_complete) {
      document.getElementById('btn-next').textContent = 'View Summary';
      document.getElementById('btn-next').onclick = loadSummary;
    } else {
      const prog = document.getElementById('qa-progress').textContent;
      const total = prog.split(' ').pop();
      const nextNum = parseInt(prog.split(' ')[1]) + 1;
      document.getElementById('btn-next').textContent = 'Next Question';
      document.getElementById('btn-next').onclick = () => showQuestion(data.next_question, nextNum, total);
    }
  } catch (e) {
    alert(e.message || 'Error evaluating answer.');
  } finally {
    document.getElementById('btn-submit').disabled = false;
    document.getElementById('btn-submit').textContent = 'Submit Answer';
  }
});

async function loadSummary() {
  showLoading('Generating session summary…');
  try {
    const data = await apiGet(\`/interview/summary/${sessionId}\`);
    document.getElementById('sum-score').textContent = (data.overall_score||0).toFixed(1) + ' / 5';
    document.getElementById('sum-job').textContent = jobTitle;
    document.getElementById('sum-strengths').innerHTML =
      (data.strengths||[]).map(s => \`<li>${s}</li>\`).join('');
    document.getElementById('sum-improve').innerHTML =
      (data.areas_to_improve||[]).map(s => \`<li>${s}</li>\`).join('');
    document.getElementById('sum-focus').textContent = data.recommended_focus || '';
    show('screen-summary');
  } catch (e) {
    alert('Could not load summary. ' + e.message);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  requireAuth();
  populateNavUser();
  loadJobOptions();
});
────────────────────────────────────────────────────────────
Task 9 — Add Nav Links to All Pages
In every HTML page (index.html, assessments.html, resume.html, jobs.html, skills.html, results.html), make two changes to the sidebar nav:
1. Add "My Results" link after the Assessments link:
<a href="/results.html" class="nav-item">
  <span class="material-symbols-outlined">bar_chart</span>My Results
</a>
2. Fix the Interview link — change /coming-soon.html to /interview.html in all pages:
<!-- BEFORE -->
<a href="/coming-soon.html" class="nav-item">

<!-- AFTER -->
<a href="/interview.html" class="nav-item">
