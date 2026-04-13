# Software Design Specifications
## AI-Powered Career Preparation Platform — CogniHire

| Field | Value |
|---|---|
| **Title** | SDS for AI-Powered Career Preparation Platform (CogniHire) |
| **Project** | CogniHire — Team 61 |
| **Document Version** | 1.1 |
| **Version Date** | 09/04/2026 |
| **Prepared By** | Team 61 |
| **Preparation Date** | 06/04/2026 |

---

### Version History

| Ver. No. | Ver. Date | Revised By | Description | Filename |
|---|---|---|---|---|
| 1.0 | 06/04/2026 | Team 61 | Initial draft | SDS.doc |
| 1.1 | 09/04/2026 | Team 61 | Corrected tech stack; aligned with actual implementation; expanded domain model and data dictionary | SDS_completed.md |

---

## Table of Contents

1. [Introduction](#1-introduction)
   - 1.1 [Purpose](#11-purpose)
   - 1.2 [Scope](#12-scope)
   - 1.3 [Definitions, Acronyms, and Abbreviations](#13-definitions-acronyms-and-abbreviations)
   - 1.4 [References](#14-references)
2. [Use Case View](#2-use-case-view)
   - 2.1 [Use Cases](#21-use-cases)
3. [Design Overview](#3-design-overview)
   - 3.1 [Design Goals and Constraints](#31-design-goals-and-constraints)
   - 3.2 [Design Assumptions](#32-design-assumptions)
   - 3.3 [Significant Design Packages](#33-significant-design-packages)
   - 3.4 [Dependent External Interfaces](#34-dependent-external-interfaces)
   - 3.5 [Implemented Application External Interfaces](#35-implemented-application-external-interfaces)
4. [Logical View](#4-logical-view)
   - 4.1 [Design Model](#41-design-model)
   - 4.2 [Use Case Realization](#42-use-case-realization)
5. [Data View](#5-data-view)
   - 5.1 [Domain Model](#51-domain-model)
   - 5.2 [Data Model (Persistent Data View)](#52-data-model-persistent-data-view)
     - 5.2.1 [Data Dictionary](#521-data-dictionary)
6. [Exception Handling](#6-exception-handling)
7. [Configurable Parameters](#7-configurable-parameters)
8. [Quality of Service](#8-quality-of-service)
   - 8.1 [Availability](#81-availability)
   - 8.2 [Security and Authorization](#82-security-and-authorization)
   - 8.3 [Load and Performance Implications](#83-load-and-performance-implications)
   - 8.4 [Monitoring and Control](#84-monitoring-and-control)

---

## 1. Introduction

### 1.1 Purpose

The purpose of this Software Design Specification (SDS) is to define the architectural and detailed design for CogniHire — an AI-powered career preparation platform. This document translates the functional and non-functional requirements established in the SRS into a comprehensive software architecture covering cognitive ability assessment, resume analysis, hybrid job recommendation, skill gap analysis, and (planned) LLM-based career guidance and interview simulation.

The intended audience is the development team (to guide implementation), project stakeholders, and instructors reviewing the system's structural integrity.

### 1.2 Scope

This document applies to the entire CogniHire platform, a web-based application built on **FastAPI** (Python), a **static HTML/CSS/JavaScript** frontend served by the same process, and **MongoDB Atlas** as the persistent data store. It covers:

- User registration and session-token-based authentication
- Cognitive ability assessment (18 tasks across 9 ability domains, NCPT percentile normalisation)
- Resume upload, text extraction, and rule-based skill/education/certification identification
- Hybrid job recommendation engine combining ability similarity, work-activity preference matching, and skill matching
- Skill gap analysis against O\*NET occupational data
- Assessment result history tracking
- Planned: LLM-based career assistant (RAG pipeline using Claude) and AI interview simulation

The platform does **not** currently include voice/audio capture, video processing, or third-party identity providers.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| COMET | Concurrent Object Modeling and Architectural Design Method |
| LLM | Large Language Model |
| NER | Named Entity Recognition |
| NLP | Natural Language Processing |
| NCPT | Neurocognitive Performance Test (normative distribution used for ability percentile scoring) |
| O\*NET | Occupational Information Network — the US Department of Labor occupational data database |
| RAG | Retrieval-Augmented Generation |
| SDS | Software Design Specification |
| SRS | Software Requirements Specification |
| UML | Unified Modeling Language |
| UUID | Universally Unique Identifier |
| JWT | JSON Web Token (loosely used; CogniHire uses opaque UUID tokens stored in MongoDB) |
| SHAP | SHapley Additive exPlanations (deferred to post-MVP) |

### 1.4 References

1. Software Requirements Specification for CogniHire — AI-Powered Career Preparation Platform, Version 1.0.
2. O\*NET Online: [https://www.onetcenter.org/database.html](https://www.onetcenter.org/database.html) — source of occupational ability, activity, skill, and task data.
3. Anthropic Claude API Documentation — planned integration for LLM features (Steps 2–4 of SOLUTION_DESIGN_REMAINING.md).
4. FastAPI Documentation: [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)
5. MongoDB Atlas Documentation: [https://www.mongodb.com/docs/atlas](https://www.mongodb.com/docs/atlas)
6. Gomaa, H. (2011). *Software Modeling and Design: UML, Use Cases, Patterns, and Software Architectures*.
7. IEEE Recommended Practice for Software Requirements Specifications (IEEE 830).
8. `SOLUTION_DESIGN_REMAINING.md` — ground-truth reevaluation of remaining work (internal, 2026-04-08).
9. `PROJECT_STRUCTURE_PHASE2_ONWARDS.md` — phase-to-module mapping and repository layout plan (internal).

---

## 2. Use Case View

### 2.1 Use Cases

The platform's design is driven by the following core use cases:

**U0 — Register and Authenticate**
Users create an account (username, email, password, full name). On login, the server issues an opaque session token stored client-side in `localStorage`. All subsequent API calls include this token as a query parameter.

**U1 — Upload Resume**
Users upload a resume file (PDF or DOCX). The system extracts plain text, identifies technical skills (via built-in taxonomy + O\*NET in-demand technology list), education credentials, certifications, and estimated years of experience. Extracted data is stored in the user's MongoDB profile document.

**U2 — Take Cognitive Assessment**
Users complete 18 browser-based tasks (2 per ability domain) covering: Deductive Reasoning, Mathematical Reasoning, Memorisation, Perceptual Speed, Problem Sensitivity, Selective Attention, Speed of Closure, Time Sharing, and Written Comprehension. Each response (correct/incorrect + reaction time) is sent to the backend, which scores the session against NCPT normative distributions to produce per-ability percentile scores and an overall readiness score. Results are persisted in the user's profile and appended to an assessment history log.

**U3 — Get Job Recommendations**
The system produces a ranked list of O\*NET occupations using a weighted hybrid score combining:
- **Ability similarity** (40 %): cosine similarity between user NCPT percentiles and job O\*NET ability requirements.
- **Work-activity preference** (30 %): dot-product between user activity vector and job work-activity matrix.
- **Skill match** (30 %): overlap between user's extracted/manual skills and O\*NET tech skill requirements.
Results can be filtered by industry cluster.

**U4 — Analyse Skill Gap**
For a selected target job, the system returns the top work activities where the user is strong or deficient, and lists the top required technology skills the user has not demonstrated.

**U5 — View Assessment History** *(implemented)*
Users can retrieve a chronological log of all past assessment attempts, including per-ability percentiles and readiness score for each attempt. A radar chart overlays the latest profile against the first attempt to visualise progress.

**U6 — Career Assistant (RAG)** *(planned — Step 3)*
A conversational interface backed by a ChromaDB vector store of O\*NET occupation documents and Claude (claude-haiku-4-5) answering user career questions in the context of their personal cognitive and skill profile.

**U7 — Interview Simulation** *(planned — Step 4)*
An LLM-driven interview session. The system generates behavioural (STAR-format) and technical questions calibrated to the user's ability gaps and skill set for a chosen target role. Claude evaluates each answer and produces a session summary.

---

## 3. Design Overview

### 3.1 Design Goals and Constraints

| Goal / Constraint | Detail |
|---|---|
| **Design Methodology** | COMET for component decomposition; UML for logical and data model notation. |
| **Technology Stack** | Python 3.11+, FastAPI (ASGI), Uvicorn, MongoDB Atlas (pymongo), Static HTML/JS/CSS frontend. All frontend assets are served by FastAPI's `StaticFiles` mount — no separate web server. |
| **AI Integration** | Rule-based pipelines are operational. LLM integration (Anthropic Claude API) is planned for resume extraction enhancement (Step 2), RAG assistant (Step 3), and interview simulation (Step 4). |
| **Data Constraints** | O\*NET datasets (Abilities, Work Activities, Technology Skills, Task Statements, etc.) are loaded from the `Archive/` directory at startup. No streaming ingestion pipeline. |
| **Latency Targets** | Resume text extraction: ≤ 5 s. Cognitive scoring: ≤ 2 s. Recommendation generation: ≤ 3 s. Planned LLM response: ≤ 10 s (non-streaming v1). |
| **Dependency Management** | All Python dependencies declared in `requirements.txt`. No build tooling (webpack, etc.) for the frontend — plain ES2020 JavaScript. |
| **Deferred** | SHAP/LIME explainability, UMAP career visualisation, Docker deployment stack, admin dashboard — not MVP. |

### 3.2 Design Assumptions

1. MongoDB Atlas is reachable via `MONGODB_URI` environment variable at startup.
2. Users submit resumes in standard parsable formats (PDF, DOCX, plain text).
3. The O\*NET dataset files in `Archive/` are current and complete; `scripts/download_onet_datasets.py` can refresh them.
4. When the Claude API is integrated, Anthropic will maintain acceptable availability and response latency for non-streaming requests.
5. Users have stable internet access for browser-based cognitive task delivery.
6. The normative NCPT percentile distribution (`person_abilities_ncpt.csv`) remains valid across the user base.

### 3.3 Significant Design Packages

The application is logically partitioned into four layers:

**Presentation Layer**
Static HTML pages (`apps/web/static/`) paired with vanilla JavaScript modules (`apps/web/static/js/`). Pages: `index.html` (dashboard), `assessments.html`, `results.html`, `jobs.html`, `skills.html`, `resume.html`. All pages share a common sidebar navigation. Client state (user_id, token) is stored in `localStorage`.

**Application Services Layer (API)**
FastAPI routers (`apps/api/src/routers/`) handle HTTP request validation, orchestrate calls to core pipeline modules, and return JSON responses. Routers:
- `auth.py` — signup, login, logout, token validation (`/api/auth/`)
- `users.py` — profile CRUD, resume upload (`/api/users/`)
- `cognitive.py` — task generation, session scoring, history retrieval (`/api/cognitive/`)
- `recommendations.py` — hybrid job ranking (`/api/recommendations/`)
- `skills.py` — skill gap analysis (`/api/skills/`)
- `onet.py` — O\*NET data query endpoints (`/api/onet/`)
- `industries.py` — industry cluster listing (`/api/industries/`)

**Core Domain & Pipeline Layer**
All ML, scoring, and extraction logic resides in `core/src/core/`:
- `tasks/` — per-ability task generators (18 tasks across 9 generators)
- `scoring.py` — `ScoringEngine`: converts raw task responses to NCPT percentiles
- `pipelines/phase5_resume_processing.py` — text extraction + rule-based skill/education/cert/experience identification
- `pipelines/phase7_hybrid_recommendation.py` — `HybridRecommender`: weighted ability + activity + skill scoring
- `pipelines/phase6_skill_matching.py` — tech skill matrix and similarity computation
- `pipelines/phase4_preference_matching.py` — work-activity vector construction
- `industry_clusters.py` — maps job titles to industry clusters

**Data Access Layer**
`core/src/core/storage/mongo_store.py` — `MongoUserStore`: all MongoDB read/write operations. Single collection `user_profiles` for profile, assessment history, and resume extraction data. Separate collection `auth_users` for credentials.

### 3.4 Dependent External Interfaces

The table below lists public interfaces this design depends upon from external systems.

| External Application | Interface Name | Module Using the Interface | Description |
|---|---|---|---|
| MongoDB Atlas | pymongo MongoClient | `MongoUserStore` (`mongo_store.py`) | All persistent read/write for user profiles, assessment history, and credentials. Accessed via `MONGODB_URI` environment variable. |
| O\*NET Database (local files) | CSV / TSV file reads | `phase5_resume_processing.py`, `phase7_hybrid_recommendation.py`, `phase6_skill_matching.py`, `phase4_preference_matching.py`, `phase1_onet_data.py` | Job ability matrix, work-activity matrix, technology skills taxonomy, occupation data. Loaded from `Archive/` and `data/` at import time. |
| Anthropic Claude API *(planned)* | `anthropic` Python SDK | `phase5_resume_processing.py` (LLM extraction), `phase11_rag_assistant.py` (RAG), `phase13_interview.py` (interview) | LLM calls for resume parsing, career Q&A, and interview question generation/evaluation. |
| ChromaDB *(planned)* | `chromadb` Python client | `core/src/core/retrieval/knowledge_base.py` | Local vector store for O\*NET occupation document embeddings; used by the RAG pipeline. |

### 3.5 Implemented Application External Interfaces

The table below lists public interfaces this application exposes.

| Interface Name | Module Implementing | Description |
|---|---|---|
| `POST /api/auth/signup` | `auth.py` | Creates a new user account. Returns `user_id`, session `token`, `full_name`, `email`. |
| `POST /api/auth/login` | `auth.py` | Validates credentials, rotates and returns a new session token. |
| `GET /api/auth/me?token=` | `auth.py` | Returns the authenticated user's profile fields from the token. |
| `POST /api/auth/logout?token=` | `auth.py` | Invalidates the session token. |
| `POST /api/users/profile` | `users.py` | Creates or updates a user profile (manual skills, interest tags). |
| `GET /api/users/profile/{user_id}` | `users.py` | Returns a user's profile (excluding history arrays). |
| `POST /api/users/resume?user_id=` | `users.py` | Accepts a resume file upload, runs extraction, persists results. |
| `GET /api/users/history/{user_id}` | `users.py` | Returns latest assessment + latest resume extraction as a combined snapshot. |
| `GET /api/users/interview-context/{user_id}` | `users.py` | Returns structured cognitive + technical profile ready for LLM pipeline injection. |
| `GET /api/cognitive/tasks` | `cognitive.py` | Generates 18 task items (2 per ability). |
| `POST /api/cognitive/assess` | `cognitive.py` | Scores a completed assessment session; persists latest scores and appends to history. |
| `GET /api/cognitive/history/{user_id}` | `cognitive.py` | Returns all past assessment attempts, newest first. |
| `GET /api/recommendations/{user_id}` | `recommendations.py` | Returns ranked job recommendations with optional industry filter and configurable weights. |
| `GET /api/skills/gaps/{user_id}?target_job=` | `skills.py` | Returns activity strengths/gaps and technology skill gaps for a target job. |
| `GET /health` | `main.py` | Liveness probe. |

---

## 4. Logical View

### 4.1 Design Model

CogniHire follows a **layered client-server architecture** with a clear separation of concerns:

```
Browser (HTML + Vanilla JS)
      │  HTTP JSON (fetch API)
      ▼
FastAPI Application (Uvicorn ASGI)
├── CORS Middleware
├── Routers (auth, users, cognitive, recommendations, skills, onet, industries)
│       │
│       ▼
│   Services / Pipelines  (core/src/core/)
│   ├── ScoringEngine          (cognitive percentile computation)
│   ├── HybridRecommender      (ability + activity + skill ranking)
│   ├── phase5_resume_processing (text extraction + rule-based NER)
│   ├── phase6_skill_matching   (tech skill matrix + similarity)
│   └── phase4_preference_matching (work-activity vector)
│       │
│       ▼
│   MongoUserStore (mongo_store.py)
│
└── StaticFiles mount  →  apps/web/static/  (HTML, JS, CSS)
          │
          ▼
    MongoDB Atlas
    ├── auth_users collection
    └── user_profiles collection
```

**Auth Controller** (`auth.py`): Manages signup (SHA-256 + salt password hashing, UUID token generation) and login (token rotation). Tokens are opaque UUID hex strings stored in the `auth_users` MongoDB collection and passed by the client as a query parameter `?token=`.

**Analysis Controller** (`users.py` + `phase5_resume_processing.py`): Orchestrates resume ingestion, multi-format text extraction (pypdf for PDF, python-docx for DOCX), and the rule-based NER pipeline (built-in taxonomy + O\*NET in-demand skill matching, degree pattern matching, certification regex matching, and date-range experience estimation). Writes results to the `latest_resume` subdocument and backward-compatible top-level fields.

**Cognitive Controller** (`cognitive.py` + `scoring.py` + `tasks/`): Generates task items via per-ability `Generator` classes, then scores submitted responses against the NCPT normative distribution to produce per-ability percentiles. Uses atomic MongoDB `$set` + `$push` to update the latest snapshot while preserving the complete history log.

**Recommendation Controller** (`recommendations.py` + `phase7_hybrid_recommendation.py`): `HybridRecommender` loads pre-pivoted O\*NET matrices at instantiation and computes a weighted composite score for each occupation.

**Skills Controller** (`skills.py`): Uses `HybridRecommender.explain_job()` for activity-level breakdown and `phase6_skill_matching.build_tech_matrix()` for technology skill gap computation using fuzzy job title matching (`rapidfuzz`).

### 4.2 Use Case Realization

**U0 — Register and Authenticate:**
Browser posts `{ username, email, password, full_name }` to `POST /api/auth/signup`. `auth.py` generates a random salt (UUID hex), hashes `SHA-256(salt + password)`, inserts into `auth_users`, and creates a minimal stub in `user_profiles` via `$setOnInsert`. Returns `{ user_id, token, full_name, email }`. Client stores these in `localStorage`. Subsequent page loads call `GET /api/auth/me?token=` to re-hydrate identity.

**U1 — Upload Resume:**
Browser posts a multipart file to `POST /api/users/resume?user_id=`. `users.py` reads the file bytes, calls `upload_resume()` (saves to `data/interim/resumes/`), then `process_resume()`. `process_resume` calls `extract_text()` (format-dispatched to pypdf or python-docx), then the unified extraction pipeline: `extract_skills_rules()` against the 130+ built-in taxonomy, `extract_skills_onet()` against O\*NET in-demand tech, `extract_education()`, `extract_certifications()`, and `extract_experience_years()`. Results are written to `latest_resume` in MongoDB and returned in the `ResumeUploadResponse`.

**U2 — Take Cognitive Assessment:**
Browser fetches `GET /api/cognitive/tasks` to receive 18 task objects. On completion, posts a list of `{ ability, is_correct, reaction_time_ms }` to `POST /api/cognitive/assess`. `ScoringEngine.score_session()` maps each ability's correct/incorrect ratio and reaction time to the NCPT normative distribution to produce a percentile. The mean of all percentiles is the `readiness_score`. `MongoUserStore.save_assessment()` atomically `$set`s the latest scores and `$push`es a timestamped entry to `assessment_history`.

**U3 — Get Job Recommendations:**
Browser calls `GET /api/recommendations/{user_id}?industry=<cluster>`. `HybridRecommender.recommend()` normalises the user's NCPT percentile vector, computes cosine similarity against the `job_abilities_onet.csv` matrix (ability score), dot-product against `workactivity_job.csv` (activity score), and Jaccard-like overlap against the tech skill matrix (skill score). A weighted sum produces the final ranking. If `industry` is supplied, the job set is pre-filtered using `classify_title()`.

**U4 — Analyse Skill Gap:**
Browser calls `GET /api/skills/gaps/{user_id}?target_job=<title>`. `HybridRecommender.explain_job()` identifies the top and bottom work activities for the user relative to that job. `build_tech_matrix()` builds the O\*NET technology skill pivot; `rapidfuzz` fuzzy-matches the title; the top 15 job skills not present in the user's profile are returned as `tech_skill_gaps`.

**U5 — View Assessment History:**
Browser calls `GET /api/cognitive/history/{user_id}`. `MongoUserStore.get_assessment_history()` projects the `assessment_history` array from the document, reverses it (newest first), and returns it. The frontend `results.js` renders a summary card with the latest readiness score and a per-attempt table with expandable ability breakdowns. A radar chart (Chart.js) overlays the latest and earliest ability profiles.

---

## 5. Data View

### 5.1 Domain Model

The domain model consists of the following primary entities:

**User** — Identity and credential entity. Stored in the `auth_users` MongoDB collection. Fields: username (serves as `user_id`), email, full_name, salt, password_hash, token. Managed entirely by the auth subsystem.

**UserProfile** — Career data aggregation entity linked to a User by `user_id`. Stored in `user_profiles`. Holds manual skills, interest tags, cognitive assessment results (latest snapshot), resume extraction data (latest snapshot), and phase-1 job suggestions.

**AssessmentAttempt** — A timestamped record of a single cognitive assessment session: taken_at, per-ability percentiles map, overall readiness score, and raw task responses. Stored as embedded documents in the `assessment_history` array within `UserProfile`.

**ResumeExtraction** — The parsed output of the latest resume upload: file_name, uploaded_at, extracted technical skills list, education strings, certifications, and estimated experience years. Stored as the `latest_resume` embedded subdocument within `UserProfile`.

**JobRecommendation** *(computed, not persisted)* — A scored occupation: job_title, total_score, ability_score, activity_score, skill_score, strength_activities, gap_activities, ability_breakdown. Returned on-demand by the recommendations endpoint.

**InterviewSession** *(planned — Step 4)* — Stored in new collection `interview_sessions`. Fields: session_id, user_id, job_code, job_title, mode, status, questions (embedded array of QA pairs with feedback and scores), overall_score, summary, started_at, completed_at.

### 5.2 Data Model (Persistent Data View)

Data is stored in **MongoDB Atlas** (document store). There are two collections in the `career_recommender` database.

**Collection: `auth_users`**
One document per registered user.

```json
{
  "username": "jsmith",
  "email": "j@example.com",
  "full_name": "Jane Smith",
  "salt": "<uuid4-hex>",
  "password_hash": "<sha256-hex>",
  "token": "<uuid4-hex>"
}
```

**Collection: `user_profiles`**
One document per user (keyed by `user_id = username`).

```json
{
  "user_id": "jsmith",
  "full_name": "Jane Smith",
  "manual_skills": ["Python", "SQL"],
  "interest_tags": ["data science", "analytics"],
  "phase1_job_suggestions": ["Data Scientists", "Statisticians"],

  // Latest cognitive assessment snapshot (from save_assessment)
  "ability_percentiles": {
    "deductive_reasoning": 82.0,
    "mathematical_reasoning": 74.0,
    "memorization": 61.0,
    "perceptual_speed": 55.0,
    "problem_sensitivity": 78.0,
    "selective_attention": 66.0,
    "speed_of_closure": 70.0,
    "time_sharing": 58.0,
    "written_comprehension": 88.0
  },
  "readiness_score": 70.22,
  "latest_assessment_at": "2026-04-09T10:30:00.000Z",

  // Append-only assessment log
  "assessment_history": [
    {
      "taken_at": "2026-04-09T10:30:00.000Z",
      "readiness_score": 70.22,
      "ability_percentiles": { "deductive_reasoning": 82.0, "...": "..." },
      "task_responses": [
        { "ability": "deductive_reasoning", "is_correct": true, "reaction_time_ms": 1240 }
      ]
    }
  ],

  // Latest resume extraction snapshot
  "resume_skills": ["Python", "FastAPI", "MongoDB"],
  "resume_education": ["B.S. Computer Science MIT 2022"],
  "resume_certifications": ["AWS Certified Solutions Architect"],
  "resume_experience_years": 3.0,
  "latest_resume": {
    "file_name": "resume.pdf",
    "uploaded_at": "2026-04-08T09:00:00.000Z",
    "skills": ["Python", "FastAPI", "MongoDB"],
    "education": ["B.S. Computer Science MIT 2022"],
    "certifications": ["AWS Certified Solutions Architect"],
    "experience_years": 3.0
  }
}
```

#### 5.2.1 Data Dictionary

| Field | Type | Collection | Description |
|---|---|---|---|
| `username` | String | auth_users | Primary identifier; also used as `user_id` across the system. |
| `email` | String | auth_users | Unique user email. |
| `full_name` | String | auth_users | Display name. |
| `salt` | String (hex) | auth_users | Random UUID hex used as the password hash salt. Generated at signup. |
| `password_hash` | String (hex) | auth_users | SHA-256 of `(salt + plaintext_password)`. |
| `token` | String (hex) | auth_users | Opaque session token (UUID hex). Rotated on every login. Cleared on logout. |
| `user_id` | String | user_profiles | Foreign key to `auth_users.username`. Primary key of user_profiles. |
| `manual_skills` | Array[String] | user_profiles | Skills entered manually by the user during profile creation. |
| `interest_tags` | Array[String] | user_profiles | Career interest tags for initial Phase 1 lexical job matching. |
| `phase1_job_suggestions` | Array[String] | user_profiles | Job titles matched from O\*NET via lexical overlap with interest_tags. |
| `ability_percentiles` | Object{String→Float} | user_profiles | Latest NCPT percentile score (0–100) for each of the 9 cognitive ability domains. |
| `readiness_score` | Float | user_profiles | Mean of all `ability_percentiles` values; overall cognitive readiness indicator. |
| `latest_assessment_at` | ISO 8601 String | user_profiles | UTC timestamp of the most recent completed assessment. |
| `assessment_history` | Array[Object] | user_profiles | Append-only log of all assessment attempts. Each entry: `{ taken_at, readiness_score, ability_percentiles, task_responses }`. |
| `task_responses` | Array[Object] | user_profiles (embedded) | Per-task records: `{ ability, is_correct, reaction_time_ms }`. One entry per task (18 per session). |
| `resume_skills` | Array[String] | user_profiles | Technical skills extracted from the latest resume (backward-compatibility flat field). |
| `resume_education` | Array[String] | user_profiles | Education credential strings extracted from the latest resume. |
| `resume_certifications` | Array[String] | user_profiles | Certification names extracted from the latest resume. |
| `resume_experience_years` | Float \| null | user_profiles | Estimated total years of professional experience from the latest resume. |
| `latest_resume` | Object | user_profiles | Full latest resume extraction result as a subdocument: `{ file_name, uploaded_at, skills, education, certifications, experience_years }`. |

---

## 6. Exception Handling

| Exception | Trigger | Handling |
|---|---|---|
| **UsernameConflict** (HTTP 400) | `POST /api/auth/signup` when username already exists in `auth_users`. | Returns `{ "detail": "Username already taken" }`. Frontend displays inline validation error. |
| **EmailConflict** (HTTP 400) | `POST /api/auth/signup` when email already registered. | Returns `{ "detail": "Email already registered" }`. |
| **AuthenticationFailure** (HTTP 401) | `POST /api/auth/login` when username not found or password hash mismatch. `GET /api/auth/me` with an invalid or expired token. | Returns `{ "detail": "Invalid username or password" }` or `{ "detail": "Invalid or expired token" }`. Frontend redirects to `index.html`. |
| **ProfileNotFound** (HTTP 404) | `GET /api/users/profile/{user_id}` when no document exists in `user_profiles`. | Returns `{ "detail": "profile not found" }`. |
| **AssessmentNotCompleted** (HTTP 422) | `GET /api/recommendations/{user_id}` or `GET /api/skills/gaps/{user_id}` when `ability_percentiles` is empty. | Returns `{ "detail": "No ability scores found. Complete the cognitive assessment first." }`. |
| **EmptyResponseBody** (HTTP 400) | `POST /api/cognitive/assess` with an empty `responses` array. | Returns `{ "detail": "No responses provided" }`. |
| **UnsupportedResumeFormat / TextExtractionFailure** | Resume file fails text extraction (corrupt PDF, unsupported format, or empty output). | `process_resume()` returns a `ResumeExtractionResult` with `method="error"` and an `error` field. The API still returns HTTP 200 with `extraction_method="error"` and empty skill/education lists; the frontend informs the user that extraction failed and prompts re-upload or manual skill entry. |
| **MongoConnectionFailure** | `MONGODB_URI` not set or Atlas unreachable at startup. | `_get_collection()` raises `EnvironmentError("MONGODB_URI is not set")`. The process exits immediately; no silently degraded state. |
| **IndustryFilterReturnsEmpty** (returns `[]`) | `GET /api/recommendations/{user_id}?industry=<cluster>` when no jobs match the given industry. | Returns HTTP 200 with an empty array. The frontend renders a "no results for this industry" message. |

---

## 7. Configurable Parameters

The following environment variables are loaded from a `.env` file via `python-dotenv` at startup.

| Configuration Parameter | Definition and Usage | Dynamic? |
|---|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string (e.g. `mongodb+srv://user:pass@cluster.mongodb.net/`). Required. Used by `MongoUserStore` and `auth.py` to open a `MongoClient`. | No — requires restart. |
| `MONGODB_DB` | Name of the MongoDB database. Default: `career_recommender`. | No — requires restart. |
| `ONET_ARCHIVE_DIR` | Path to the directory containing O\*NET CSV/TXT files. Implicit default: `Archive/` relative to the repo root. Currently hardcoded in pipeline modules; promote to env var if the data path needs to vary across environments. | No. |
| `ANTHROPIC_API_KEY` *(planned)* | API key for the Anthropic Claude API. Required for Steps 2–4 (LLM resume extraction, RAG assistant, interview simulation). Not yet consumed by the codebase. | No — requires restart. |
| `CHROMA_PERSIST_DIR` *(planned)* | Directory for ChromaDB vector store persistence. Default intended: `vectorstore/chroma/`. | No. |

---

## 8. Quality of Service

### 8.1 Availability

The system is designed for high availability in a single-node deployment typical of a university/prototype environment. The FastAPI + Uvicorn process is stateless with respect to user sessions (tokens are verified against MongoDB on each request), meaning a process restart does not invalidate sessions.

MongoDB Atlas provides its own replication and availability SLA. In a production deployment, Atlas M10+ tiers with replica sets would target ≥ 99.95 % uptime. For the current phase, a free-tier Atlas cluster is sufficient.

O\*NET data is loaded into in-process Pandas DataFrames at startup. A startup failure (missing O\*NET files or bad `MONGODB_URI`) prevents the server from starting cleanly, ensuring no partially functional state is served.

### 8.2 Security and Authorization

**Authentication:** Custom username/password auth. Passwords are never stored in plaintext — each is stored as `SHA-256(salt + password)` where the salt is a randomly generated UUID hex per user. Session tokens are opaque UUID hex strings generated at signup and rotated on every login. Tokens are invalidated (set to empty string) on logout.

**Data Isolation:** All profile, assessment, and resume data is keyed by `user_id`. API endpoints that operate on user data accept `user_id` as a path or query parameter. In the current implementation the token is validated for identity (`GET /api/auth/me`) but is not enforced as an authorisation gate on every endpoint — this is a known limitation to be addressed before production deployment by adding a FastAPI dependency that validates the token and injects the authenticated `user_id`.

**Communication:** All client-server communication should be served over HTTPS in production. In development, plain HTTP over localhost is used.

**Resume Files:** Uploaded files are saved to `data/interim/resumes/` on the local filesystem, scoped to `{user_id}/` subdirectories. No file is served back to the browser — only the extracted metadata.

**Known Limitation:** The token is currently passed as a URL query parameter, which exposes it in server access logs. A production hardening step should move token transport to the `Authorization: Bearer` header.

### 8.3 Load and Performance Implications

| Operation | Expected Latency | Notes |
|---|---|---|
| Cognitive task generation (`GET /api/cognitive/tasks`) | < 50 ms | Pure in-memory; no I/O. |
| Assessment scoring (`POST /api/cognitive/assess`) | < 200 ms | In-memory + one MongoDB `update_one`. |
| Resume extraction (PDF/DOCX) | 1–5 s | Dominated by pypdf/python-docx parsing; scales with file size. |
| Recommendation generation | 200 ms – 2 s | In-memory matrix operations on pre-loaded Pandas DataFrames. One MongoDB `find_one`. |
| Skill gap analysis | 200 ms – 1 s | In-memory fuzzy match + matrix lookup. |
| LLM calls *(planned)* | 3–10 s | Non-streaming; will require frontend loading spinner. |

O\*NET DataFrames are loaded once at module import (effectively singleton per process). There is no caching layer beyond Python's `@lru_cache` for the O\*NET skill taxonomy loader. For high-concurrency deployments, running multiple Uvicorn workers (or a Gunicorn process manager) is recommended, as FastAPI is thread-safe for these read-heavy operations.

### 8.4 Monitoring and Control

In the current development phase, FastAPI's default access logging (Uvicorn) provides HTTP-level visibility: method, path, status code, and latency.

For the planned production phase, the following monitoring points are identified:

- **Assessment endpoint response time** — SLA: ≤ 2 s p95.
- **Resume extraction latency** — SLA: ≤ 5 s p95; alert if > 10 s.
- **MongoDB query latency** — Atlas Performance Advisor will surface slow queries.
- **LLM API calls** *(planned)* — track token usage, generation latency, and timeout/error rates against the Anthropic API. Log each call with `user_id`, prompt token count, completion token count, and duration.
- **Health probe** — `GET /health` returns `{ "status": "ok" }`. Suitable for use as a container/load-balancer liveness probe.

Structured logging (JSON-formatted, with `user_id` and `request_id` correlation fields) is deferred to the post-MVP observability milestone.
