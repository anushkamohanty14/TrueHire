# TrueHire

An AI-powered career intelligence platform that matches candidates to jobs using cognitive assessments, resume analysis, and O\*NET occupational data.

## Features

- **Auth** — signup and login with username/password; sessions persisted in MongoDB
- **Cognitive assessments** — 18 browser-based tasks across 9 ability domains, scored against NCPT normative distributions
- **Assessment history** — full per-attempt history with radar chart progress visualisation
- **Resume processing** — upload PDF/DOCX resumes; LLM-powered extraction (Groq) pulls technical skills, soft skills, education, certifications, experience years, and past job titles; falls back to rule-based extraction if unavailable
- **Hybrid job recommendations** — weighted combination of cognitive ability similarity (40%), work-activity preference (30%), and skill match (30%) against O\*NET occupational data
- **Skill gap analysis** — per-job breakdown of activity strengths/gaps and missing technology skills
- **AI interview simulation** — LLM-generated behavioral (STAR-format) and technical questions calibrated to the user's cognitive profile and target role; per-answer scoring and feedback; session summary *(frontend in progress)*
- **O\*NET data** — loads abilities, work activities, technology skills, and task statements from the full O\*NET database

## Tech stack

- **Backend:** FastAPI, Python 3.11+, MongoDB Atlas (PyMongo)
- **Frontend:** Static HTML/CSS/Vanilla JS served by FastAPI
- **AI:** Groq API (llama-3.3-70b-versatile) for resume extraction and interview simulation
- **Data:** O\*NET occupational database (local CSV/TXT files in `Archive/`)

## Setup

### Prerequisites

- Python 3.11+
- MongoDB Atlas cluster (or local MongoDB)
- Groq API key — get one free at [console.groq.com](https://console.groq.com)
- A `.env` file at the repo root:

```
MONGODB_URI=<your MongoDB connection string>
MONGODB_DB=career_recommender
GROQ_API_KEY=<your Groq API key>
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the server

```bash
uvicorn apps.api.src.main:app --reload
```

The app is available at `http://localhost:8000`.

## Project structure

```
apps/
  api/src/
    main.py               # FastAPI app, router registration, static file serving
    routers/              # auth, users, onet, cognitive, skills, recommendations,
                          # industries, interview (in progress)
  web/static/             # HTML pages and JS frontend
core/src/core/
  pipelines/
    phase5_resume_processing.py   # text extraction + LLM/rule-based skill parsing
    phase7_hybrid_recommendation.py  # weighted job ranking engine
    phase13_interview.py          # LLM interview question generation and evaluation
    ...                           # O*NET loading, skill matching, preference matching
  storage/
    mongo_store.py        # all MongoDB read/write operations
  scoring.py              # NCPT ability percentile scoring
  industry_clusters.py    # industry cluster classification
Archive/                  # O*NET dataset files (abilities, skills, activities, tasks)
data/                     # interim data (resume uploads)
scripts/                  # utility scripts (e.g. download_onet_datasets.py)
```

## Run tests

```bash
python -m pytest tests/ -v
```

## Status

| Area | Status |
|---|---|
| Auth | Complete |
| Cognitive assessment (18 tasks, 9 abilities) | Complete |
| Assessment history + results page | Complete |
| Resume upload + LLM extraction | Complete |
| Hybrid job recommendations | Complete |
| Skill gap analysis | Complete |
| AI interview simulation (pipeline) | Complete |
| Interview frontend | In progress |
