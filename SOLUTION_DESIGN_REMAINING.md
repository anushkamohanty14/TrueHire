# TrueHire — Revised Solution Design (Reevaluated 2026-04-08)

## What This Document Covers

A ground-truth reevaluation of remaining work, ordered by dependency and MVP priority.  
Deferred items are explicitly called out at the end.

---

## Ground Truth: Current State

### What Actually Works
| Area | Reality |
|---|---|
| Auth (signup/login/logout) | Complete |
| Cognitive assessment (18 tasks, 9 abilities) | Complete — scoring, NCPT percentile normalization |
| Assessment results storage | **Partial** — only latest attempt saved, no history |
| Resume upload + text extraction | Complete |
| Resume skill extraction | **Weak** — 130-skill hardcoded regex taxonomy only; no LLM; no education/certs/experience |
| Job recommendations (hybrid: ability + activity + skill) | Complete |
| Skill gap analysis | Complete |
| Frontend HTML pages | All exist and are styled |
| Frontend JS wiring | **Mostly complete** — assessments, dashboard, jobs, skills, resume all wired |
| Interview page | **Stub only** — redirects to coming-soon |
| Results / history page | **Missing entirely** |
| LLM integration | **None** — no Claude API calls anywhere in codebase |
| RAG pipeline | **None** |

### O*NET Data On Disk
| File | Content |
|---|---|
| `Archive/Abilities.csv` | Job × cognitive ability (raw O*NET, importance/level scales) |
| `Archive/Technology Skills.csv` | Job × tech skill commodity (thousands of skills, hot/in-demand flags) |
| `Archive/Work Activities.csv` | Job × 332 work activities with importance scores |
| `Archive/Abilities to Work Activities.csv` | Crosswalk: cognitive ability → work activities |
| `job_abilities_onet.csv` | Pre-pivoted: job × 9 ability scores (already used) |
| `person_abilities_ncpt.csv` | NCPT normative distribution (already used) |
| `Archive/workactivity_job.csv` | Pre-computed job × activity relevance scores (already used) |

**Missing O*NET data:** education requirements, certification requirements, salary/experience ranges — not available in current data set.

---

## Step 1 — Assessment Results: Persistence & History

### Problem
`POST /api/cognitive/assess` overwrites the user profile with the latest scores. There is no history. Users cannot revisit their results.

### What to Build

#### 1a. MongoDB Schema Change

Add `assessment_history` array to the `user_profiles` document:

```json
{
  "user_id": "...",
  "ability_percentiles": { ... },
  "readiness_score": 72.3,
  "assessment_history": [
    {
      "taken_at": "2026-04-08T10:30:00Z",
      "ability_percentiles": { "deductive_reasoning": 75, ... },
      "readiness_score": 72.3,
      "task_responses": [ { "ability": "...", "score": 1, "reaction_time_ms": 1200 } ]
    }
  ]
}
```

`ability_percentiles` at the top level stays as the latest snapshot (used by recommendations).  
`assessment_history` is an append-only log.

**Change in `mongo_store.py`:**  
`upsert_profile()` already uses `$set`. Add a second `$push` operation to append to `assessment_history` when cognitive results are saved. Keep upsert for the top-level `ability_percentiles` and `readiness_score`.

#### 1b. New API Endpoint

Add to `apps/api/src/routers/cognitive.py`:

```
GET /api/cognitive/history/{user_id}
Response: {
  "attempts": [
    {
      "taken_at": "ISO datetime",
      "readiness_score": float,
      "ability_percentiles": { ability: percentile }
    }
  ]
}
```

#### 1c. New Frontend Page: Results History

**New file:** `apps/web/static/results.html`  
**New file:** `apps/web/static/js/results.js`

Layout:
- Summary card: latest readiness score + date taken
- Per-attempt row in a table: date, readiness score, expand to see per-ability breakdown
- Radar chart (using Chart.js CDN) showing latest ability profile vs. first attempt (progress visualization)
- "Retake Assessment" button → `assessments.html`

Add "My Results" link to the nav sidebar in all HTML pages.

---

## Step 2 — Resume Extraction: Make It Thorough

### Problem
Current extraction is a 130-skill regex taxonomy — it misses skills not in the list, extracts no education, no experience, no job titles. This is the data foundation for both RAG and interview simulation, so it must be solid before building those.

### 2a. Expand Skill Taxonomy Using O*NET

`Archive/Technology Skills.csv` contains thousands of skills indexed by job code. Use it to build a comprehensive skill taxonomy:

**New utility:** `core/src/core/pipelines/phase5_resume_processing.py` — add function:

```python
def build_onet_skill_taxonomy(tech_skills_csv_path: str) -> set[str]:
    """
    Reads Archive/Technology Skills.csv.
    Extracts the 'Example' column (actual skill/tool names like 'Python', 'Docker', etc.)
    Deduplicates and normalizes.
    Returns a set of skill strings to use for matching.
    """
```

**Load at startup**, merge with the existing hardcoded taxonomy. This gives coverage over the full O*NET tech skill universe without manual maintenance.

### 2b. LLM-Based Extraction (Claude)

The codebase already has `extraction_method: "llm" | "rules"` in the schema — it was planned, never built.

**Add to `phase5_resume_processing.py`:**

```python
def extract_skills_llm(resume_text: str) -> SkillExtractionResult:
    """
    Calls Claude (claude-haiku-4-5-20251001) with a structured prompt.
    Returns skills, education, experience_years, past_job_titles, certifications.
    """
```

**Prompt design:**

```
You are a resume parser. Extract structured information from the resume below.
Return ONLY valid JSON matching this schema:

{
  "technical_skills": ["Python", "AWS", "React", ...],
  "soft_skills": ["communication", "leadership", ...],
  "education": [
    { "degree": "B.S. Computer Science", "institution": "MIT", "year": 2020 }
  ],
  "certifications": ["AWS Solutions Architect", "PMP"],
  "years_of_experience": 5,
  "past_job_titles": ["Software Engineer", "Backend Developer"]
}

Rules:
- Only include skills explicitly mentioned; do not infer
- Normalize skill names (e.g. "JS" → "JavaScript")
- If a field is not present in the resume, return an empty array or null
- Return only the JSON object, no explanation

Resume:
{resume_text}
```

**Fallback:** If the LLM call fails, fall back to rules-based extraction. The `extraction_method` field in the result indicates which path was used.

### 2c. Updated Output Schema

Extend `SkillExtractionResult` to include the new fields:

```python
@dataclass
class SkillExtractionResult:
    skills: list[str]                    # technical skills (existing)
    soft_skills: list[str]               # new
    education: list[dict]                # new: [{degree, institution, year}]
    certifications: list[str]            # new
    years_of_experience: int | None      # new
    past_job_titles: list[str]           # new
    method: str                          # "llm" | "rules" | "error"
    raw_text_length: int
    error: str | None
```

### 2d. MongoDB Profile Update

Add new fields to the user profile document:

```json
{
  "resume_skills": ["Python", "AWS"],
  "soft_skills": ["leadership"],
  "education": [{ "degree": "B.S. CS", "institution": "Stanford", "year": 2019 }],
  "certifications": ["AWS SAA"],
  "years_of_experience": 4,
  "past_job_titles": ["SWE", "Backend Engineer"],
  "resume_extraction_method": "llm",
  "resume_uploaded_at": "ISO datetime"
}
```

**Update `mongo_store.py`** to `$set` these fields during resume processing.

### 2e. Validation Against O*NET

After LLM extraction, run a normalization pass:

```python
def normalize_and_validate_skills(raw_skills: list[str], onet_taxonomy: set[str]) -> list[str]:
    """
    For each extracted skill, check if it (case-insensitively) exists in the O*NET taxonomy.
    Skills not in O*NET are kept but flagged as 'user-reported' (not normalized against O*NET jobs).
    This allows downstream matching to distinguish O*NET-verified skills from free-text ones.
    """
```

This step ensures that skill matching in the recommendation pipeline uses normalized names that align with O*NET job requirements.

---

## Step 3 — RAG Pipeline

### Prerequisite
Steps 1 and 2 must be complete. The RAG system uses:
- Cognitive ability percentiles (from Step 1, persisted)
- Technical skills, education, experience, job titles (from Step 2, persisted)
- O*NET job data (already on disk)

### 3a. Dataset Inventory (verified 2026-04-08)

All datasets confirmed present in `Archive/` after running `scripts/download_onet_datasets.py`.

| File | Rows | Content | RAG role |
|---|---|---|---|
| `Occupation Data.txt` | 1,016 | 1-2 sentence job description per occupation | Primary job context |
| `Task Statements.txt` | 18,796 | ~20 task sentences per occupation | Richest job content for retrieval |
| `Skills.txt` | 61,530 | 35 cognitive/behavioural skills per occupation (importance + level) | Skills context |
| `Knowledge.txt` | 58,014 | 33 knowledge domains per occupation | Domain context |
| `Education, Training, and Experience.txt` | 36,209 | Education level requirements per occupation | Education context |
| `Technology Skills.csv` | 32,772 | Tech tools per occupation (hot/in-demand flags) | Tech skills context |
| `Work Activities.csv` | 73,307 | 332 work activities per occupation | Activity context |
| `Abilities.csv` | 92,976 | Cognitive abilities per occupation (O*NET raw) | Ability context |

**To refresh datasets:** `python scripts/download_onet_datasets.py` (auto-detects latest O*NET release).

### 3b. Knowledge Base: What to Index

**Chunk strategy — 1 chunk per occupation (~900 chunks total):**

Combine all sources into a single rich text document per job code at index-build time:

```
[Job Code: 15-1252.00]
Title: Software Developers
Description: {Occupation Data.txt description}
Key Tasks: {top 8 tasks from Task Statements.txt}
Top Skills: {top 5 skills by importance from Skills.txt}
Key Knowledge: {top 5 knowledge domains from Knowledge.txt}
Technology Tools: {top 10 tech examples from Technology Skills.csv}
Education Required: {most common education level from Education...txt}
Work Activities: {top 5 activities from Work Activities.csv}
```

This single-chunk-per-job design keeps retrieval simple and prevents context fragmentation. At ~400 tokens per chunk × 900 jobs = ~360k tokens total — small enough to build in under 2 minutes and query in milliseconds.

**No user data is pre-indexed.** User context (cognitive scores, resume data) is injected at query time as a system prompt prefix.

**New file:** `core/src/core/retrieval/knowledge_base.py`

```python
def build_knowledge_base(
    jobs_df: pd.DataFrame,
    activities_df: pd.DataFrame,
    tech_skills_df: pd.DataFrame,
    persist_dir: str = "vectorstore/chroma/"
) -> chromadb.Collection:
    """
    Chunks, embeds, and persists all O*NET documents.
    Uses ChromaDB's default embedding (sentence-transformers/all-MiniLM-L6-v2).
    Idempotent — skips rebuild if collection already exists and is not stale.
    Returns the collection handle.
    """

def retrieve(query: str, collection, top_k: int = 6) -> list[str]:
    """Semantic search over the indexed O*NET chunks. Returns raw text chunks."""
```

**Build trigger:** Run once at API startup (`main.py` lifespan event). Persist to `vectorstore/chroma/`. Subsequent startups load from disk; rebuild only if source data changes.

### 3b. User Context Assembly

At query time, assemble the user's current context from their profile:

```python
def build_user_context(profile: dict) -> str:
    """
    Returns a structured text block summarizing the user's profile for injection into prompts.
    Example output:
      Cognitive profile: Deductive Reasoning 88th pct, Written Comprehension 74th pct, ...
      Technical skills: Python, AWS, FastAPI, PostgreSQL
      Education: B.S. Computer Science (Stanford, 2019)
      Certifications: AWS Solutions Architect
      Years of experience: 4
      Past roles: Software Engineer, Backend Developer
      Top recommended jobs: Software Developers (0.82), Data Scientists (0.79)
    """
```

### 3c. RAG Query Pipeline

**New file:** `core/src/core/pipelines/phase11_rag_assistant.py`

```python
def answer_query(
    user_id: str,
    query: str,
    history: list[dict],         # [{role: "user"|"assistant", content: str}]
    collection: chromadb.Collection,
    profile: dict
) -> str:
    """
    1. Retrieve top-k O*NET chunks relevant to the query
    2. Assemble user context from profile
    3. Call Claude with system prompt + context + history + query
    4. Return the assistant's response string
    """
```

**System prompt:**

```
You are TrueHire's career advisor. You have access to O*NET career data and the user's 
cognitive assessment results and resume analysis.

Your role:
- Answer career questions with specificity — reference the user's actual ability percentiles,
  skills, and top job matches by name
- Give actionable advice on skill gaps and learning priorities  
- Keep responses concise (3-5 sentences unless the user asks for detail)
- Never fabricate job data; only reference information in the provided context

User Profile:
{user_context}

Relevant O*NET Data:
{retrieved_chunks}
```

**History handling:** Pass last 6 turns of conversation history to Claude for coherence. Do not summarize history in v1.

### 3d. Suggested Questions

On first load, generate 3 personalized starter questions:

```python
def generate_starter_questions(profile: dict) -> list[str]:
    """
    Calls Claude with the user context only (no retrieval needed).
    Returns 3 questions the user would likely find most useful given their specific profile.
    Example: "Why is Deductive Reasoning so important for Software Developers?"
    """
```

### 3e. API Endpoints

**New router:** `apps/api/src/routers/assistant.py`

```
POST /api/assistant/chat
Body:    { "message": str, "history": [{role, content}] }
Headers: Authorization: Bearer <token>  (user_id extracted server-side)
Response: { "response": str }

GET  /api/assistant/starter-questions
Headers: Authorization: Bearer <token>
Response: { "questions": [str, str, str] }
```

### 3f. Frontend

**New page:** `apps/web/static/assistant.html`  
**New file:** `apps/web/static/js/assistant.js`

UI layout:
- Greeting with user's name
- 3 starter question chips (fetched on load, clickable to auto-fill input)
- Chat history area (user bubbles right, assistant bubbles left)
- Input box + Send button
- Request/response is blocking (no streaming in v1) — show a loading spinner

Add "Career Assistant" nav link to the sidebar in all pages.

---

## Step 4 — Interview Simulation Pipeline

### Design Principles
- Uses **cognitive profile** to calibrate question difficulty and ability-specific framing
- Uses **technical skills** from resume to generate relevant technical questions
- Uses **O*NET work activities** for the target job to generate behavioral questions
- Two modes: **Behavioral** (STAR-format, activity-based) and **Technical** (skill/role-based)
- No audio/video in v1 — text Q&A only
- LLM generates questions and evaluates answers

### 4a. Interview Session Model

```json
{
  "session_id": "uuid",
  "user_id": "...",
  "job_code": "15-1252.00",
  "job_title": "Software Developers",
  "mode": "behavioral" | "technical" | "mixed",
  "status": "active" | "complete",
  "questions": [
    {
      "id": 1,
      "question": "Tell me about a time you debugged a complex system under pressure.",
      "ability_focus": "Problem Sensitivity",
      "type": "behavioral",
      "user_answer": "...",
      "feedback": "...",
      "score": 4
    }
  ],
  "overall_score": null,
  "summary": null,
  "started_at": "ISO datetime",
  "completed_at": null
}
```

Sessions are stored in a new MongoDB collection: `interview_sessions`.

### 4b. Question Generation

**New file:** `core/src/core/pipelines/phase13_interview.py`

```python
def generate_behavioral_questions(
    job_title: str,
    top_work_activities: list[str],   # top 5 from O*NET work activities for this job
    user_ability_gaps: list[str],     # abilities where user is below job requirement
    n: int = 5
) -> list[dict]:
    """
    Calls Claude to generate STAR-format behavioral questions.
    Questions target the job's top work activities and probe the user's identified ability gaps.

    Prompt signals:
    - Job: {job_title}
    - Key work activities: {activities}
    - User's weaker abilities: {gaps} — questions should gently probe these
    - Format: return JSON list of { question, ability_focus, rationale }
    """

def generate_technical_questions(
    job_title: str,
    user_skills: list[str],          # from resume extraction
    required_skills: list[str],      # from O*NET tech skills for this job
    user_gaps: list[str],            # skills required but not in user profile
    n: int = 5
) -> list[dict]:
    """
    Calls Claude to generate technical questions.
    Mix: ~60% on skills user has (validate depth), ~40% on gap skills (assess awareness).

    Prompt signals:
    - Job: {job_title}
    - User has: {user_skills}
    - Role requires: {required_skills}
    - Gaps to probe: {user_gaps}
    - Format: return JSON list of { question, skill_focus, difficulty (1-3) }
    """
```

### 4c. Answer Evaluation

```python
def evaluate_answer(
    question: str,
    answer: str,
    question_type: str,              # "behavioral" | "technical"
    job_context: str,
    ability_focus: str | None
) -> dict:
    """
    Calls Claude to score and provide feedback.
    Returns: { score (1-5), feedback (str), strength (str), improvement (str) }

    Scoring rubric (embedded in prompt):
    Behavioral: STAR structure, relevance, specificity, outcome
    Technical: accuracy, depth, awareness of tradeoffs
    """
```

### 4d. Session Summary

```python
def generate_session_summary(session: dict) -> dict:
    """
    After all questions answered, calls Claude once with the full Q&A transcript.
    Returns: {
      overall_score: float,
      strengths: [str],
      areas_to_improve: [str],
      recommended_focus: str   // e.g., "Practice explaining system design tradeoffs"
    }
    """
```

### 4e. API Endpoints

**New router:** `apps/api/src/routers/interview.py`

```
POST /api/interview/start
Body:    { "job_code": str, "mode": "behavioral"|"technical"|"mixed" }
Headers: Authorization: Bearer <token>
Response: { "session_id": str, "job_title": str, "first_question": {id, question, type} }

POST /api/interview/respond
Body:    { "session_id": str, "question_id": int, "answer": str }
Response: { "feedback": str, "score": int, "next_question": {id, question, type} | null }
  // next_question is null when session is complete

GET  /api/interview/summary/{session_id}
Response: { "overall_score": float, "strengths": [str], "areas_to_improve": [str],
            "recommended_focus": str, "questions": [...] }

GET  /api/interview/history
Headers: Authorization: Bearer <token>
Response: { "sessions": [{ session_id, job_title, mode, overall_score, completed_at }] }
```

### 4f. Frontend

Complete `apps/web/static/interview.html` — replace coming-soon content entirely.  
**New file:** `apps/web/static/js/interview.js`

**Flow:**

```
Step 1: Setup
  - Job selector (populated from user's top 5 recommendations)
  - Mode selector: Behavioral / Technical / Mixed
  - "Start Interview" button

Step 2: Q&A Loop
  - Question displayed prominently
  - Label showing type (Behavioral / Technical) + ability/skill focus
  - Large textarea for answer
  - "Submit Answer" button
  - Progress indicator: "Question 2 of 5"
  - After submit: feedback panel slides in below (score badge + feedback text)
  - "Next Question" button to advance

Step 3: Summary Screen
  - Overall score (out of 5)
  - Strength highlights (2-3 bullets)
  - Improvement areas (2-3 bullets)
  - Recommended focus statement
  - "Practice Again" + "Back to Jobs" buttons
```

Remove the redirect to `coming-soon.html` from `interview.html:74-76`.

---

## Step 5 — Frontend Gaps (Non-Interview)

The frontend JS is mostly wired. The remaining gaps are:

### 5a. Results / History Page (new)
Described in Step 1c above. Needed before any other page references historical data.

### 5b. Nav Link Additions
Add to the sidebar nav in **all** HTML pages:
- "My Results" → `results.html` (Step 1)
- "Career Assistant" → `assistant.html` (Step 3)
- "Interview Practice" → `interview.html` (Step 4) — already in nav but redirects to coming-soon; fix this

### 5c. Assessment Completion Flow
After `POST /api/cognitive/assess` succeeds in `assessments.js`, the current behavior is unknown. Ensure it:
1. Shows a success message with the overall readiness score
2. Automatically redirects to `results.html` after 3 seconds (not `jobs.html`)

### 5d. Profile Page: Display Extracted Resume Data
`resume.html` shows extracted skills but does not display education, certifications, or experience after Step 2 adds those fields. Update `resume.js` to render the new fields from the profile response.

---

## Implementation Order

Work in this exact sequence — each step is a prerequisite for the next:

| # | Step | Why This Order |
|---|---|---|
| 1 | Assessment persistence + history page | Foundation for results; needed before RAG has good user context |
| 2 | Resume extraction enhancement (O*NET taxonomy + LLM) | Data quality gate; RAG and interview both depend on complete profile |
| 3 | RAG pipeline + assistant frontend | Requires complete user profile from Steps 1 & 2 |
| 4 | Interview simulation | Requires cognitive profile (Step 1) + skills (Step 2) + O*NET job data |
| 5 | Frontend gaps (nav links, completion flows, resume display) | Wire UI to completed backend endpoints |

---

## Dependencies to Add

```
anthropic         # Claude API — Steps 2, 3, 4
chromadb          # Vector store — Step 3
sentence-transformers  # Embeddings for ChromaDB — Step 3
```

Add to `requirements.txt`. No build tooling changes needed.

---

## Deferred to Next Stage (Not MVP)

The following were in the original plan but have no compelling MVP case:

| Feature | Reason to Defer |
|---|---|
| SHAP/LIME explainability | Recommender is rule-based; SHAP requires a trained ML model. No model to explain yet. |
| Career visualization map (UMAP) | Useful but not in the user journey flow; adds heavy deps. |
| Observability / structured logging | Add when there are real users to monitor. |
| Docker / deployment infra | Out of scope until the product is feature-complete. |
| Preference matching enhancement (Phase 4) | Activity similarity already feeds into hybrid recommender; no user-facing gap. |
| Settings / profile edit page | Resume re-upload achieves the same thing. |
| Admin dashboard | No admin users yet. |
