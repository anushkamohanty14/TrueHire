# CogniHire

An AI-powered career intelligence platform that matches candidates to jobs using cognitive assessments, resume analysis, and O\*NET occupational data.

## Features

- **Auth** — signup and login with username/password; sessions persisted in MongoDB
- **O\*NET job data** — loads and queries the O\*NET database for job titles, abilities, and industry clusters
- **Cognitive assessments** — NCPT-based ability scoring mapped to O\*NET ability profiles
- **Resume processing** — upload and parse resumes to extract skills and experience
- **Skill matching** — compares user skill profile against job requirements
- **Hybrid recommendations** — combines cognitive scores, skills, and preferences into ranked job suggestions
- **History** — tracks assessment and recommendation history per user

## Tech stack

- **Backend:** FastAPI, Python, MongoDB (via PyMongo)
- **Frontend:** Static HTML/CSS/JS served by FastAPI
- **Data:** O\*NET occupational database

## Setup

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas)
- A `.env` file at the repo root with:

```
MONGODB_URI=<your MongoDB connection string>
MONGODB_DB=career_recommender   # optional, defaults to this value
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the server

```bash
uvicorn apps.api.src.main:app --reload
```

The app is then available at `http://localhost:8000`.

## Project structure

```
apps/
  api/src/
    main.py               # FastAPI app, router registration, static file serving
    routers/              # auth, users, onet, cognitive, skills, recommendations, industries
  web/static/             # HTML pages and JS frontend
core/src/core/
  pipelines/              # data processing pipelines (O*NET loading, resume parsing, matching)
  storage/                # MongoDB and local storage helpers
  scoring.py              # ability scoring logic
  industry_clusters.py    # industry clustering
data/                     # raw and interim data (O*NET files, resume uploads)
tests/                    # unit and integration tests
scripts/                  # utility scripts (e.g. download O*NET datasets)
```

## Run tests

```bash
python -m pytest tests/ -v
```
