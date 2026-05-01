"""System tests — end-to-end workflows hitting the live server.

Run with:
    python3.12 -m pytest tests/system/ -v

Requires the server to be running:
    uvicorn apps.api.src.main:app --reload --port 8000
"""
import os
import tempfile
import time
import unittest
import uuid

import requests

BASE = "http://localhost:8000"
_SNAKE_CASE_ABILITIES = {
    "deductive_reasoning", "mathematical_reasoning", "memorization",
    "perceptual_speed", "problem_sensitivity", "selective_attention",
    "speed_of_closure", "time_sharing", "written_comprehension",
}


def _api(path):
    return BASE + path


def _get(path, **kwargs):
    return requests.get(_api(path), **kwargs)


def _post(path, **kwargs):
    return requests.post(_api(path), **kwargs)


def _unique_user():
    return f"sys_test_{uuid.uuid4().hex[:10]}"


def _register_and_login(username=None):
    """Create a fresh user and return (username, token)."""
    username = username or _unique_user()
    r = _post("/api/auth/signup", json={
        "username": username,
        "email": f"{username}@test.example",
        "password": "TestPass123!",
        "full_name": "System Test User",
    })
    assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
    return username, r.json()["token"]


def _upload_resume(username, token, content=None):
    content = content or (
        "Experienced software engineer with Python, FastAPI, PostgreSQL, "
        "AWS, Docker, Kubernetes, React, TypeScript, Machine Learning expertise."
    )
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    with open(path, "rb") as fh:
        r = requests.post(
            _api(f"/api/users/resume?user_id={username}"),
            files={"file": ("resume.txt", fh, "text/plain")},
        )
    os.unlink(path)
    return r


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _take_assessment(username, all_correct=True, token=None):
    tasks = _get("/api/cognitive/tasks").json()
    responses = [
        {
            "ability": t["ability"],
            "is_correct": all_correct or (i % 2 == 0),
            "reaction_time_ms": 600.0,
        }
        for i, t in enumerate(tasks)
    ]
    kwargs = {"json": {"user_id": username, "responses": responses}}
    if token:
        kwargs["headers"] = _auth(token)
    return _post("/api/cognitive/assess", **kwargs)


def _start_interview(token, job_title, mode="mixed"):
    return _post(
        "/api/interview/start",
        json={"job_title": job_title, "mode": mode},
        headers=_auth(token),
    )


def _answer_question(token, session_id, question_id, answer):
    return _post(
        "/api/interview/respond",
        json={"session_id": session_id, "question_id": question_id, "answer": answer},
        headers=_auth(token),
    )


# ── 1. Complete end-to-end golden path ───────────────────────────────────────

class TestCompleteWorkflow(unittest.TestCase):
    """The full user journey: sign up → resume → assessment → jobs → interview."""

    def setUp(self):
        self.username, self.token = _register_and_login()

    def test_signup_produces_valid_token(self):
        r = _get("/api/auth/me", headers=_auth(self.token))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["user_id"], self.username)

    def test_step1_resume_upload(self):
        r = _upload_resume(self.username, self.token)
        self.assertEqual(r.status_code, 200, f"Resume upload failed: {r.text}")
        body = r.json()
        self.assertGreater(len(body.get("extracted_skills", [])), 0)

    def test_step2_cognitive_assessment(self):
        r = _take_assessment(self.username, token=self.token)
        self.assertEqual(r.status_code, 200, f"Assessment failed: {r.text}")
        body = r.json()
        self.assertIn("readiness_score", body)
        self.assertIn("ability_percentiles", body)
        self.assertIsInstance(body["readiness_score"], (int, float))
        self.assertGreaterEqual(body["readiness_score"], 0)
        self.assertLessEqual(body["readiness_score"], 100)

    def test_step3_results_visible_after_assessment(self):
        _take_assessment(self.username, token=self.token)
        r = _get(f"/api/cognitive/history/{self.username}")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertGreater(body["attempt_count"], 0, "History empty after assessment")
        attempt = body["attempts"][0]
        self.assertIn("readiness_score", attempt)
        self.assertIn("ability_percentiles", attempt)

    def test_step4_user_history_has_both_after_resume_and_assessment(self):
        _upload_resume(self.username, self.token)
        _take_assessment(self.username, token=self.token)
        r = _get(f"/api/users/history/{self.username}")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsNotNone(body["assessment"], "assessment missing from history")
        self.assertIsNotNone(body["resume"], "resume missing from history")

    def test_step5_interview_starts_after_resume_and_assessment(self):
        _upload_resume(self.username, self.token)
        _take_assessment(self.username, all_correct=False, token=self.token)
        r = _start_interview(self.token, "Software Developer", mode="behavioral")
        self.assertEqual(r.status_code, 200, f"Interview start failed: {r.text}")
        body = r.json()
        self.assertIn("session_id", body)
        self.assertIn("first_question", body)
        self.assertGreater(body["total_questions"], 0)

    def test_step6_full_interview_session_completes(self):
        _upload_resume(self.username, self.token)
        _take_assessment(self.username, all_correct=False, token=self.token)

        start_r = _start_interview(self.token, "Software Developer", mode="behavioral")
        self.assertEqual(start_r.status_code, 200)
        body = start_r.json()
        session_id = body["session_id"]
        total = body["total_questions"]

        answer = (
            "In my previous role I led a critical data pipeline migration. "
            "The outcome was a 40% reduction in latency, which directly improved "
            "customer retention metrics by 15%."
        )

        for qid in range(1, total + 1):
            r = _answer_question(self.token, session_id, qid, answer)
            self.assertEqual(r.status_code, 200, f"Answer q{qid} failed: {r.text}")
            resp = r.json()
            if qid == total:
                self.assertTrue(resp["session_complete"], "Last answer should complete session")
            else:
                self.assertFalse(resp["session_complete"])

    def test_step7_summary_after_completed_session(self):
        _upload_resume(self.username, self.token)
        _take_assessment(self.username, all_correct=False, token=self.token)

        start_r = _start_interview(self.token, "Software Developer", mode="behavioral")
        session_id = start_r.json()["session_id"]
        total = start_r.json()["total_questions"]

        answer = (
            "I improved the pipeline performance by 30% by analyzing bottlenecks "
            "and rewriting the core algorithm. The result metric was a 20% cost saving."
        )
        for qid in range(1, total + 1):
            _answer_question(self.token, session_id, qid, answer)

        r = _get(f"/api/interview/summary/{session_id}", headers=_auth(self.token))
        self.assertEqual(r.status_code, 200, f"Summary failed: {r.text}")
        summary = r.json()
        self.assertIn("overall_score", summary)
        self.assertIn("strengths", summary)
        self.assertIn("areas_to_improve", summary)
        self.assertIsInstance(summary["overall_score"], (int, float))
        self.assertGreater(summary["overall_score"], 0)


# ── 2. Interview question quality ─────────────────────────────────────────────

class TestInterviewQuestionQuality(unittest.TestCase):
    """Questions must reference job work activities, not raw cognitive ability names."""

    def setUp(self):
        self.username, self.token = _register_and_login()
        _upload_resume(self.username, self.token)
        _take_assessment(self.username, all_correct=False, token=self.token)

    def _get_questions(self, job_title, mode="behavioral"):
        r = _start_interview(self.token, job_title, mode=mode)
        self.assertEqual(r.status_code, 200, f"Interview start failed: {r.text}")
        session_id = r.json()["session_id"]
        # Retrieve the full session from the summary (won't have summary yet but we
        # can check the first question returned in the start response)
        return r.json()

    def test_no_snake_case_ability_in_first_question_judges(self):
        data = self._get_questions("Judges, Magistrate Judges, and Magistrates")
        first_q = data["first_question"]["question"].lower()
        for ability in _SNAKE_CASE_ABILITIES:
            self.assertNotIn(ability, first_q,
                             f"Raw snake_case ability '{ability}' leaked into question: {first_q}")

    def test_no_snake_case_ability_in_first_question_analyst(self):
        data = self._get_questions("Data Analyst")
        first_q = data["first_question"]["question"].lower()
        for ability in _SNAKE_CASE_ABILITIES:
            self.assertNotIn(ability, first_q,
                             f"Raw snake_case ability '{ability}' leaked into question: {first_q}")

    def test_no_title_case_raw_ability_in_first_question(self):
        """Human-readable ability titles like 'Mathematical Reasoning' also shouldn't appear as the topic."""
        raw_ability_phrases = [
            "mathematical reasoning",
            "deductive reasoning",
            "perceptual speed",
            "selective attention",
            "speed of closure",
            "time sharing",
            "written comprehension",
        ]
        data = self._get_questions("Software Developer")
        first_q = data["first_question"]["question"].lower()
        for phrase in raw_ability_phrases:
            self.assertNotIn(phrase, first_q,
                             f"Raw ability label '{phrase}' appeared in question: {first_q}")

    def test_behavioral_question_references_work_activity_for_judges(self):
        """Judges questions should reference legal/judicial work activities or scenarios."""
        data = self._get_questions("Judges, Magistrate Judges, and Magistrates", mode="behavioral")
        q_text = data["first_question"]["question"].lower()
        # Check for either O*NET activity names OR judicial scenario keywords
        # (LLM may paraphrase activities into natural judicial language)
        judicial_keywords = [
            "judging", "evaluating", "evaluate", "making decisions", "decision",
            "getting information", "resolving", "processing information", "processing",
            "identifying", "evidence", "case", "ruling", "testimony", "legal",
            "court", "precedent", "compliance", "standard", "witness", "credibility",
            "judgment", "reasoning", "thinking", "analyzing", "analysis",
        ]
        found = any(kw in q_text for kw in judicial_keywords)
        self.assertTrue(found, f"No judicial context found in question: {q_text}")

    def test_mixed_mode_produces_both_types(self):
        r = _start_interview(self.token, "Software Developer", mode="mixed")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertGreaterEqual(body["total_questions"], 4,
                                "Mixed mode should produce at least 4 questions (3 behavioral + 2 technical)")

    def test_behavioral_mode_produces_only_behavioral(self):
        r = _start_interview(self.token, "Data Analyst", mode="behavioral")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        first_type = body["first_question"]["type"]
        self.assertEqual(first_type, "behavioral")


# ── 3. Auth and security ──────────────────────────────────────────────────────

class TestAuthSecurity(unittest.TestCase):

    def test_interview_start_without_token_returns_401(self):
        r = _post("/api/interview/start",
                  json={"job_title": "Software Developer", "mode": "behavioral"})
        self.assertEqual(r.status_code, 401)

    def test_interview_start_with_invalid_token_returns_401(self):
        r = _post("/api/interview/start",
                  json={"job_title": "Software Developer", "mode": "behavioral"},
                  headers={"Authorization": "Bearer notavalidtoken"})
        self.assertEqual(r.status_code, 401)

    def test_interview_respond_cross_user_forbidden(self):
        u1, t1 = _register_and_login()
        u2, t2 = _register_and_login()

        for u, t in ((u1, t1), (u2, t2)):
            _upload_resume(u, t)
            _take_assessment(u, all_correct=False, token=t)

        r1 = _start_interview(t1, "Software Developer", mode="behavioral")
        session_id = r1.json()["session_id"]

        # User 2 tries to answer user 1's session
        r = _post(
            "/api/interview/respond",
            json={"session_id": session_id, "question_id": 1, "answer": "hacked"},
            headers=_auth(t2),
        )
        self.assertEqual(r.status_code, 403, "Cross-user session access should be forbidden")

    def test_duplicate_username_rejected(self):
        username, _ = _register_and_login()
        r = _post("/api/auth/signup", json={
            "username": username,
            "email": f"different_{username}@test.example",
            "password": "SomePass!",
        })
        self.assertEqual(r.status_code, 400)

    def test_login_wrong_password_rejected(self):
        username, _ = _register_and_login()
        r = _post("/api/auth/login", json={"username": username, "password": "WRONG"})
        self.assertEqual(r.status_code, 401)

    def test_me_endpoint_returns_correct_user(self):
        username, token = _register_and_login()
        r = _get("/api/auth/me", headers=_auth(token))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["user_id"], username)


# ── 4. Assessment scoring ─────────────────────────────────────────────────────

class TestAssessmentScoring(unittest.TestCase):

    def test_all_correct_scores_higher_than_all_wrong(self):
        u_good, tok_good = _register_and_login()
        u_bad, tok_bad = _register_and_login()

        tasks = _get("/api/cognitive/tasks").json()

        r_good = _post("/api/cognitive/assess", headers=_auth(tok_good), json={
            "user_id": u_good,
            "responses": [{"ability": t["ability"], "is_correct": True, "reaction_time_ms": 400.0}
                          for t in tasks],
        }).json()

        r_bad = _post("/api/cognitive/assess", headers=_auth(tok_bad), json={
            "user_id": u_bad,
            "responses": [{"ability": t["ability"], "is_correct": False, "reaction_time_ms": 3000.0}
                          for t in tasks],
        }).json()

        self.assertGreater(
            r_good["readiness_score"],
            r_bad["readiness_score"],
            "All-correct user should score higher than all-wrong user",
        )

    def test_percentiles_sum_to_nonzero(self):
        username, token = _register_and_login()
        tasks = _get("/api/cognitive/tasks").json()
        r = _post("/api/cognitive/assess", headers=_auth(token), json={
            "user_id": username,
            "responses": [{"ability": t["ability"], "is_correct": True, "reaction_time_ms": 600.0}
                          for t in tasks],
        }).json()
        percentile_sum = sum(r["ability_percentiles"].values())
        self.assertGreater(percentile_sum, 0, "All percentiles are zero — scoring broken")

    def test_all_9_abilities_in_percentiles(self):
        username, token = _register_and_login()
        tasks = _get("/api/cognitive/tasks").json()
        r = _post("/api/cognitive/assess", headers=_auth(token), json={
            "user_id": username,
            "responses": [{"ability": t["ability"], "is_correct": True, "reaction_time_ms": 600.0}
                          for t in tasks],
        }).json()
        for ability in _SNAKE_CASE_ABILITIES:
            self.assertIn(ability, r["ability_percentiles"],
                          f"Ability '{ability}' missing from percentiles response")

    def test_readiness_score_in_valid_range(self):
        username, token = _register_and_login()
        tasks = _get("/api/cognitive/tasks").json()
        r = _post("/api/cognitive/assess", headers=_auth(token), json={
            "user_id": username,
            "responses": [{"ability": t["ability"], "is_correct": i % 2 == 0, "reaction_time_ms": 700.0}
                          for i, t in enumerate(tasks)],
        }).json()
        score = r["readiness_score"]
        self.assertGreaterEqual(score, 0, "Readiness score below 0")
        self.assertLessEqual(score, 100, "Readiness score above 100")


# ── 5. Recommendations ────────────────────────────────────────────────────────

class TestJobRecommendations(unittest.TestCase):

    def setUp(self):
        self.username, self.token = _register_and_login()
        _upload_resume(self.username, self.token)
        _take_assessment(self.username, all_correct=True, token=self.token)

    def test_recommendations_returned(self):
        r = _get(f"/api/recommendations/{self.username}")
        self.assertEqual(r.status_code, 200, f"Recommendations failed: {r.text}")
        recs = r.json()
        self.assertIsInstance(recs, list, "Recommendations should be a list")
        self.assertGreater(len(recs), 0, "No job recommendations returned")

    def test_recommendation_has_required_fields(self):
        recs = _get(f"/api/recommendations/{self.username}").json()
        rec = recs[0]
        for field in ("job_title", "total_score", "rank"):
            self.assertIn(field, rec, f"Recommendation missing field '{field}'")

    def test_match_score_in_valid_range(self):
        recs = _get(f"/api/recommendations/{self.username}").json()
        for rec in recs:
            score = rec.get("total_score", 0)
            self.assertGreaterEqual(score, 0, f"total_score {score} below 0")
            self.assertLessEqual(score, 1.01, f"total_score {score} above 1")


# ── 6. Static page workflow continuity ───────────────────────────────────────

class TestWorkflowPageLinks(unittest.TestCase):
    """Ensure workflow pages exist and JS files reference correct API paths."""

    def _get_js(self, path):
        r = _get(path)
        self.assertEqual(r.status_code, 200, f"{path} not served")
        return r.text

    def test_resume_page_exists(self):
        self.assertEqual(_get("/resume.html").status_code, 200)

    def test_assessments_page_exists(self):
        self.assertEqual(_get("/assessments.html").status_code, 200)

    def test_results_page_removed(self):
        """results.html was merged into history.html."""
        self.assertEqual(_get("/results.html").status_code, 404)

    def test_jobs_page_exists(self):
        self.assertEqual(_get("/jobs.html").status_code, 200)

    def test_interview_page_exists(self):
        self.assertEqual(_get("/interview.html").status_code, 200)

    def test_history_page_exists(self):
        self.assertEqual(_get("/history.html").status_code, 200)

    def test_history_js_no_double_api_prefix(self):
        src = self._get_js("/js/history.js")
        self.assertNotIn("/api/users/history", src,
                         "history.js has double /api prefix — apiGet already prepends /api")

    def test_jobs_js_links_to_interview_with_job_param(self):
        src = self._get_js("/js/jobs.js")
        self.assertIn("interview.html?job=", src,
                      "jobs.js does not link to interview page with job query param")

    def test_resume_js_shows_next_step_banner(self):
        src = self._get_js("/js/resume.js")
        self.assertIn("assessments.html", src,
                      "resume.js does not reference assessments.html — next-step banner missing")

    def test_interview_js_reads_job_query_param(self):
        src = self._get_js("/js/interview.js")
        self.assertIn("URLSearchParams", src,
                      "interview.js does not read URL query params — job pre-selection broken")

    def test_history_js_has_readiness_banner(self):
        src = self._get_js("/js/history.js")
        self.assertIn("readiness", src,
                      "history.js does not render readiness section")

    def test_dashboard_js_has_workflow_progress(self):
        src = self._get_js("/js/dashboard.js")
        self.assertIn("workflow-progress", src,
                      "dashboard.js does not render workflow progress stepper")

    def test_api_js_served_and_defines_api_get(self):
        src = self._get_js("/js/api.js")
        self.assertIn("apiGet", src)
        self.assertIn("getUserId", src)
        self.assertIn("requireAuth", src)


# ── 7. Session evaluation quality ─────────────────────────────────────────────

class TestAnswerEvaluation(unittest.TestCase):
    """Verify scoring heuristics via the live API."""

    def setUp(self):
        self.username, self.token = _register_and_login()
        _upload_resume(self.username, self.token)
        _take_assessment(self.username, all_correct=False, token=self.token)

    def _run_session_with_answer(self, answer, mode="behavioral"):
        r = _start_interview(self.token, "Data Analyst", mode=mode)
        self.assertEqual(r.status_code, 200)
        session_id = r.json()["session_id"]
        total = r.json()["total_questions"]
        for qid in range(1, total + 1):
            _answer_question(self.token, session_id, qid, answer)
        summary_r = _get(f"/api/interview/summary/{session_id}", headers=_auth(self.token))
        self.assertEqual(summary_r.status_code, 200)
        return summary_r.json()

    def test_detailed_answer_scores_higher_than_vague_answer(self):
        vague = "I handled it well."
        detailed = (
            "I led a cross-functional team to diagnose a production database slowdown. "
            "After profiling queries, I identified missing indexes as the root cause. "
            "The fix improved query time by 60% and reduced server costs. "
            "The outcome was a measurable improvement in user satisfaction metrics."
        )
        vague_summary = self._run_session_with_answer(vague)
        detailed_summary = self._run_session_with_answer(detailed)
        self.assertGreater(
            detailed_summary["overall_score"],
            vague_summary["overall_score"],
            "Detailed answer should score higher than vague one-liner",
        )

    def test_summary_has_required_fields(self):
        answer = "I solved the problem by analyzing data and presenting results to stakeholders."
        summary = self._run_session_with_answer(answer)
        for field in ("overall_score", "strengths", "areas_to_improve", "recommended_focus"):
            self.assertIn(field, summary, f"Summary missing field '{field}'")

    def test_summary_score_between_0_and_5(self):
        answer = "I improved the model accuracy by 15% by tuning hyperparameters and cleaning data."
        summary = self._run_session_with_answer(answer)
        self.assertGreaterEqual(summary["overall_score"], 0.0)
        self.assertLessEqual(summary["overall_score"], 5.0)


if __name__ == "__main__":
    unittest.main()
