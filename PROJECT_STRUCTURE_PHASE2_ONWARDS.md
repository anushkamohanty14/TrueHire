# TrueHire — Project Structure Plan (Phase 2 Onwards)

This document proposes the target repository structure, module boundaries, and delivery order for **Phase 2 to Phase 13**, assuming Phase 1 (O*NET knowledge base) is already available.

---

## 1) Target Repository Layout

```text
TrueHire/
├── apps/
│   ├── api/                               # FastAPI backend
│   │   ├── src/
│   │   │   ├── main.py                    # FastAPI app entrypoint
│   │   │   ├── config.py                  # Env/settings
│   │   │   ├── deps.py                    # Dependency wiring
│   │   │   ├── middleware/
│   │   │   ├── routers/
│   │   │   │   ├── users.py               # Phase 2
│   │   │   │   ├── recommendations.py     # Phase 7/13
│   │   │   │   ├── skills.py              # Phase 8
│   │   │   │   ├── explainability.py      # Phase 9
│   │   │   │   └── assistant.py           # Phase 11
│   │   │   ├── schemas/                   # Pydantic request/response models
│   │   │   ├── services/                  # API orchestration layer
│   │   │   └── observability/             # logging/metrics/tracing
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   └── web/                               # Streamlit frontend
│       ├── app.py                         # Streamlit app entrypoint
│       ├── pages/
│       │   ├── 01_profile.py              # Phase 2
│       │   ├── 02_cognitive.py            # Phase 3
│       │   ├── 03_preferences.py          # Phase 4
│       │   ├── 04_resume.py               # Phase 5
│       │   ├── 05_recommendations.py      # Phase 7
│       │   ├── 06_skill_gap.py            # Phase 8
│       │   ├── 07_explainability.py       # Phase 9
│       │   ├── 08_visual_map.py           # Phase 10
│       │   └── 09_assistant.py            # Phase 11
│       ├── components/
│       └── pyproject.toml
│
├── core/                                  # Shared domain + ML logic
│   ├── src/core/
│   │   ├── domain/
│   │   │   ├── entities.py
│   │   │   └── enums.py
│   │   ├── pipelines/
│   │   │   ├── phase2_user_input.py
│   │   │   ├── phase3_ability_matching.py
│   │   │   ├── phase4_preference_matching.py
│   │   │   ├── phase5_resume_processing.py
│   │   │   ├── phase6_skill_matching.py
│   │   │   ├── phase7_hybrid_recommender.py
│   │   │   ├── phase8_skill_gap.py
│   │   │   ├── phase9_explainability.py
│   │   │   ├── phase10_visualization.py
│   │   │   ├── phase11_rag_assistant.py
│   │   │   └── phase13_serving.py
│   │   ├── features/
│   │   ├── models/
│   │   ├── retrieval/
│   │   ├── explainability/
│   │   ├── visualization/
│   │   └── utils/
│   ├── tests/
│   └── pyproject.toml
│
├── data/
│   ├── raw/                               # raw imports
│   ├── interim/                           # cleaned/merged intermediates
│   ├── processed/                         # model-ready matrices
│   └── artifacts/                         # persisted assets (if local)
│
├── models/
│   ├── trained/                           # sklearn/lightgbm models
│   ├── embeddings/                        # serialized vector embeddings
│   └── explainers/                        # SHAP/LIME artifacts
│
├── vectorstore/
│   ├── faiss_index/
│   └── chroma/                            # choose one provider by env
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.web
│   │   └── docker-compose.yml
│   ├── aws/
│   └── scripts/
│       ├── bootstrap.sh
│       ├── train_all.sh
│       └── deploy.sh
│
├── configs/
│   ├── base.yaml
│   ├── dev.yaml
│   ├── staging.yaml
│   └── prod.yaml
│
├── notebooks/
│   ├── exploration/
│   └── experiments/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│
├── docs/
│   ├── architecture.md
│   ├── api_contracts.md
│   ├── model_cards/
│   └── runbooks/
│
├── .env.example
├── Makefile
├── pyproject.toml                         # workspace / tooling config
└── README.md
```

---

## 2) Phase-to-Module Mapping (Phase 2–13)

## Phase 2 — User Input System
- `core/pipelines/phase2_user_input.py`
  - `create_user_profile()`
- `apps/web/pages/01_profile.py`
  - `upload_resume(file)`
  - `collect_manual_skills()`
  - `collect_interest_tags()`
- `apps/api/src/routers/users.py`
  - profile CRUD + validation
- Storage: MongoDB (`users`, `profiles`, `preferences` collections)

## Phase 3 — Cognitive Ability Matching
- `core/pipelines/phase3_ability_matching.py`
  - `collect_cognitive_test_responses()`
  - `compute_cognitive_scores(responses)`
  - `build_user_ability_vector(scores)`
  - `compute_ability_similarity(user_vector, job_matrix)`
  - `cluster_careers_by_ability()`
  - `predict_career_domain(user_vector)`
- `apps/web/pages/02_cognitive.py`
- `models/trained/ability_domain_classifier.pkl`

## Phase 4 — Work Preference Matching
- `core/pipelines/phase4_preference_matching.py`
  - `collect_activity_preferences()`
  - `build_activity_vector(responses)`
  - `compute_activity_similarity(user_vector, job_activity_matrix)`
  - `identify_preferred_careers()`
- `core/visualization/activity_plots.py`
  - `plot_activity_profile(user, job)`
- `apps/web/pages/03_preferences.py`

## Phase 5 — Resume Processing
- `core/pipelines/phase5_resume_processing.py`
  - `extract_resume_text(file)`
  - `perform_resume_ocr(image)`
  - `extract_skills_ner(text)`
  - `extract_skills_llm(text)`
  - `normalize_skills(skill_list)`
  - `build_skill_vector(skills)`
- `apps/web/pages/04_resume.py`
- `apps/api/src/routers/skills.py`

## Phase 6 — Skill Matching
- `core/pipelines/phase6_skill_matching.py`
  - `generate_skill_embeddings(skills)`
  - `generate_job_skill_embeddings()`
  - `compute_skill_similarity(user_skills, job_skills)`
  - `rank_jobs_by_skill_match()`
- `vectorstore/` (if semantic search is used for skills)

## Phase 7 — Hybrid Recommendation Engine
- `core/pipelines/phase7_hybrid_recommender.py`
  - `build_recommendation_features()`
  - `predict_career_score(features)`
  - `rank_careers(scores)`
  - `get_top_career_recommendations()`
- `apps/api/src/routers/recommendations.py`
- `apps/web/pages/05_recommendations.py`

## Phase 8 — Skill Gap Analysis
- `core/pipelines/phase8_skill_gap.py`
  - `compare_user_job_skills()`
  - `identify_skill_gaps()`
  - `generate_learning_path()`
  - `compute_readiness_score()`
- `apps/web/pages/06_skill_gap.py`

## Phase 9 — Explainability
- `core/pipelines/phase9_explainability.py`
  - `compute_shap_values()`
  - `generate_prediction_explanation()`
  - `explain_recommendation(job)`
  - `explain_non_recommendation(job)`
- `apps/api/src/routers/explainability.py`
- `apps/web/pages/07_explainability.py`

## Phase 10 — Career Visualization
- `core/pipelines/phase10_visualization.py`
  - `generate_career_clusters()`
  - `reduce_career_dimensions()`
  - `plot_career_map()`
  - `plot_skill_match()`
- `apps/web/pages/08_visual_map.py`

## Phase 11 — Career Assistant (RAG)
- `core/pipelines/phase11_rag_assistant.py`
  - `parse_user_query()`
  - `retrieve_career_documents(query)`
  - `generate_llm_answer(context)`
  - `generate_career_advice()`
- `core/retrieval/` for chunking/indexing/retrieval strategies
- `apps/api/src/routers/assistant.py`
- `apps/web/pages/09_assistant.py`

## Phase 12 — Web Application
- `apps/web/app.py`
  - `render_dashboard()`
  - `display_recommendations()`
  - `display_skill_gap_dashboard()`
- Shared Streamlit UI components in `apps/web/components/`

## Phase 13 — Deployment
- `core/pipelines/phase13_serving.py`
  - `serve_recommendation_api()`
  - `store_embeddings()`
  - `cache_queries()`
  - `build_docker_image()`
  - `manage_repository()`
  - `deploy_application()`
- Infra assets in `infra/docker/`, `infra/aws/`, `infra/scripts/`

---

## 3) Cross-Cutting Design Rules

- **Single source of ML/business logic:** keep algorithmic code under `core/`; `apps/` should orchestrate only.
- **Strict IO boundaries:** routers handle HTTP + schema validation; pipelines handle computation.
- **Artifact versioning:** persist model, embedding, and explainer versions with metadata.
- **Config-driven behavior:** model paths, vector DB provider, and API keys via `configs/*.yaml` + environment variables.
- **Deterministic pipelines:** each phase module exposes pure, testable functions where possible.

---

## 4) Incremental Delivery Plan (from Phase 2)

1. **Milestone A (Phases 2–4):** end-to-end onboarding + cognitive + preference matching in Streamlit.
2. **Milestone B (Phases 5–6):** resume extraction and skill matching integrated into recommendations.
3. **Milestone C (Phases 7–8):** hybrid scorer + skill gap roadmap.
4. **Milestone D (Phases 9–10):** explainability + visualization dashboards.
5. **Milestone E (Phases 11–13):** RAG assistant, production API hardening, deployment stack.

---

## 5) Suggested First Scaffolding Tickets

- Create base package skeleton (`apps/api`, `apps/web`, `core`).
- Define shared domain schemas (`UserProfile`, `JobProfile`, `RecommendationResult`).
- Implement `phase2_user_input.py` + `users.py` router + profile page.
- Add test harness (`pytest`, unit + integration folder conventions).
- Add Docker Compose for API + web + Mongo + Redis.

