"""Integration tests — hit the live server at localhost:8000.

Run with:
    python3.12 -m pytest tests/integration/ -v

Requires the server to be running:
    uvicorn apps.api.src.main:app --reload --port 8000
"""
import json
import os
import tempfile
import time
import unittest

import requests

BASE = "http://localhost:8000"

# ── helpers ───────────────────────────────────────────────────────────────────

def _api(path):
    return BASE + path


def _post(path, **kwargs):
    return requests.post(_api(path), **kwargs)


def _get(path, **kwargs):
    return requests.get(_api(path), **kwargs)


# ── 1. Cognitive tasks endpoint ───────────────────────────────────────────────

class TestCognitiveTasks(unittest.TestCase):

    def setUp(self):
        r = _get("/api/cognitive/tasks")
        self.assertEqual(r.status_code, 200, f"Tasks endpoint failed: {r.text}")
        self.tasks = r.json()

    def test_returns_18_tasks(self):
        self.assertEqual(len(self.tasks), 18, f"Expected 18 tasks, got {len(self.tasks)}")

    def test_all_9_abilities_present(self):
        abilities = {t["ability"] for t in self.tasks}
        expected = {
            "deductive_reasoning", "mathematical_reasoning", "memorization",
            "perceptual_speed", "problem_sensitivity", "selective_attention",
            "speed_of_closure", "time_sharing", "written_comprehension",
        }
        self.assertEqual(abilities, expected, f"Missing abilities: {expected - abilities}")

    def test_digit_span_has_required_fields(self):
        """Digit span tasks must have sequence + display_seconds for the countdown timer."""
        ds_tasks = [t for t in self.tasks if t["task_type"] == "digit_span"]
        self.assertGreater(len(ds_tasks), 0, "No digit_span tasks found")
        for t in ds_tasks:
            q = t["question"]
            self.assertIn("sequence", q, "digit_span question missing 'sequence'")
            self.assertIsInstance(q["sequence"], list, "'sequence' should be a list")
            self.assertGreater(len(q["sequence"]), 0, "'sequence' is empty")
            meta = t.get("metadata", {})
            self.assertIn("display_seconds", meta,
                          "digit_span metadata missing 'display_seconds' — frontend countdown will break")
            self.assertGreater(meta["display_seconds"], 0, "display_seconds must be > 0")

    def test_digit_span_correct_answer_is_space_separated(self):
        """Correct answer must be space-separated so checkAnswer digit comparison works."""
        ds_tasks = [t for t in self.tasks if t["task_type"] == "digit_span"]
        for t in ds_tasks:
            ca = t["correct_answer"]
            seq = t["question"]["sequence"]
            self.assertEqual(ca, " ".join(seq),
                             f"correct_answer '{ca}' doesn't match space-joined sequence '{' '.join(seq)}'")

    def test_digit_span_answer_normalisation(self):
        """Simulate what checkAnswer does: strip non-digits and compare."""
        ds_tasks = [t for t in self.tasks if t["task_type"] == "digit_span"]
        for t in ds_tasks:
            correct_digits = "".join(d for d in t["correct_answer"] if d.isdigit())
            # Simulate user typing without spaces
            user_nospaces = "".join(t["question"]["sequence"])
            # Simulate user typing with spaces
            user_spaced = " ".join(t["question"]["sequence"])
            user_digits_nospace = "".join(d for d in user_nospaces if d.isdigit())
            user_digits_spaced = "".join(d for d in user_spaced if d.isdigit())
            self.assertEqual(correct_digits, user_digits_nospace,
                             "No-space answer should match after digit normalisation")
            self.assertEqual(correct_digits, user_digits_spaced,
                             "Spaced answer should match after digit normalisation")

    def test_no_task_requires_llm(self):
        """No task should reference LLM or API keys."""
        for t in self.tasks:
            for key in ("api_key", "llm", "openai", "anthropic"):
                self.assertNotIn(key, json.dumps(t).lower(),
                                 f"Task references '{key}': {t}")


# ── 2. Cognitive assess + history persistence ─────────────────────────────────

class TestAssessAndHistory(unittest.TestCase):

    TEST_USER = f"integration_test_user_{int(time.time())}"

    def _make_responses(self, tasks):
        return [
            {"ability": t["ability"], "is_correct": True, "reaction_time_ms": 1000.0}
            for t in tasks
        ]

    def test_assess_returns_percentiles(self):
        tasks_r = _get("/api/cognitive/tasks")
        self.assertEqual(tasks_r.status_code, 200)
        tasks = tasks_r.json()
        payload = {"user_id": self.TEST_USER, "responses": self._make_responses(tasks)}
        r = _post("/api/cognitive/assess", json=payload)
        self.assertEqual(r.status_code, 200, f"Assess failed: {r.text}")
        body = r.json()
        self.assertIn("ability_percentiles", body)
        self.assertIn("readiness_score", body)
        self.assertIsInstance(body["readiness_score"], (int, float))

    def test_assess_persists_to_history(self):
        """After assess, history endpoint must return ≥1 attempt."""
        tasks_r = _get("/api/cognitive/tasks")
        tasks = tasks_r.json()
        payload = {"user_id": self.TEST_USER, "responses": self._make_responses(tasks)}
        _post("/api/cognitive/assess", json=payload)

        hist_r = _get(f"/api/cognitive/history/{self.TEST_USER}")
        self.assertEqual(hist_r.status_code, 200, f"History endpoint failed: {hist_r.text}")
        body = hist_r.json()
        self.assertGreater(body["attempt_count"], 0,
                           "History is empty after completing an assessment — persistence is broken")

    def test_history_entry_has_required_fields(self):
        tasks_r = _get("/api/cognitive/tasks")
        tasks = tasks_r.json()
        payload = {"user_id": self.TEST_USER, "responses": self._make_responses(tasks)}
        _post("/api/cognitive/assess", json=payload)

        body = _get(f"/api/cognitive/history/{self.TEST_USER}").json()
        attempt = body["attempts"][0]
        self.assertIn("taken_at", attempt)
        self.assertIn("readiness_score", attempt)
        self.assertIn("ability_percentiles", attempt)

    def test_multiple_attempts_accumulate(self):
        tasks_r = _get("/api/cognitive/tasks")
        tasks = tasks_r.json()
        payload = {"user_id": self.TEST_USER, "responses": self._make_responses(tasks)}
        _post("/api/cognitive/assess", json=payload)
        _post("/api/cognitive/assess", json=payload)

        body = _get(f"/api/cognitive/history/{self.TEST_USER}").json()
        self.assertGreaterEqual(body["attempt_count"], 2,
                                "Second attempt not saved — history overwrites instead of appends")


# ── 3. Resume upload ──────────────────────────────────────────────────────────

class TestResumeUpload(unittest.TestCase):

    TEST_USER = "integration_resume_test"

    def _upload(self, content: str, user_id: str = None):
        uid = user_id or self.TEST_USER
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                         delete=False, encoding="utf-8") as f:
            f.write(content)
            path = f.name
        with open(path, "rb") as fh:
            # user_id MUST be a query param, not a form field
            r = requests.post(
                _api(f"/api/users/resume?user_id={uid}"),
                files={"file": ("resume.txt", fh, "text/plain")},
            )
        os.unlink(path)
        return r

    def test_upload_succeeds(self):
        r = self._upload("Python Django FastAPI AWS Docker Kubernetes")
        self.assertEqual(r.status_code, 200, f"Resume upload failed: {r.text}")

    def test_upload_without_query_param_fails(self):
        """Sending user_id as a form field (old bug) must return 422."""
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                         delete=False, encoding="utf-8") as f:
            f.write("Python AWS")
            path = f.name
        with open(path, "rb") as fh:
            r = requests.post(
                _api("/api/users/resume"),      # no user_id in query string
                files={"file": ("resume.txt", fh, "text/plain")},
                data={"user_id": self.TEST_USER},  # sent as form field instead — old broken way
            )
        os.unlink(path)
        self.assertEqual(r.status_code, 422,
                         "Expected 422 when user_id is a form field (not query param) — "
                         f"got {r.status_code}: {r.text}")

    def test_upload_extracts_skills(self):
        r = self._upload("Experienced with Python, PostgreSQL, AWS, Docker and Kubernetes.")
        body = r.json()
        skills = body.get("extracted_skills", [])
        self.assertGreater(len(skills), 0, "No skills extracted from resume")
        skills_lower = [s.lower() for s in skills]
        self.assertIn("python", skills_lower, "Python not extracted")

    def test_upload_does_not_require_api_key(self):
        """Resume parsing must work without any LLM/API key — pure rule-based."""
        r = self._upload("Python Java AWS Docker Kubernetes")
        self.assertNotEqual(r.status_code, 401, "Upload returned 401 — auth/key required")
        self.assertNotEqual(r.status_code, 500,
                            f"Upload returned 500 — possible LLM/API key error: {r.text}")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body.get("extraction_method"), "rules",
                         f"Extraction method should be 'rules', got: {body.get('extraction_method')}")

    def test_upload_response_schema(self):
        r = self._upload("Python AWS Docker")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for field in ("user_id", "file_name", "saved_path", "size_bytes", "extracted_skills", "extraction_method"):
            self.assertIn(field, body, f"Response missing field '{field}'")


# ── 4. Static frontend files ──────────────────────────────────────────────────

class TestStaticFrontend(unittest.TestCase):

    def test_login_page_served(self):
        r = requests.get(f"{BASE}/login.html")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers.get("content-type", ""))

    def test_assessments_page_served(self):
        r = requests.get(f"{BASE}/assessments.html")
        self.assertEqual(r.status_code, 200)

    def test_assessments_js_served(self):
        r = requests.get(f"{BASE}/js/assessments.js")
        self.assertEqual(r.status_code, 200, "assessments.js not served — check static mount")

    def test_assessments_js_has_digit_span_countdown(self):
        r = requests.get(f"{BASE}/js/assessments.js")
        src = r.text
        self.assertIn("digit_span", src, "digit_span handling missing from assessments.js")
        self.assertIn("display_seconds", src,
                      "display_seconds not used in assessments.js — countdown timer missing")
        self.assertIn("setInterval", src,
                      "setInterval missing — countdown timer not implemented")
        self.assertIn("type = 'text'", src,
                      "Input type not switched to text for digit_span — user can't type spaced digits")

    def test_assessments_js_digit_span_answer_normalisation(self):
        r = requests.get(f"{BASE}/js/assessments.js")
        src = r.text
        self.assertIn("replace(/\\D/g", src,
                      "Digit-only normalisation missing from checkAnswer — "
                      "spaced answers like '4 7 1 2 9' will fail strict compare")

    def test_resume_js_user_id_is_query_param(self):
        r = requests.get(f"{BASE}/js/resume.js")
        src = r.text
        self.assertNotIn("form.append('user_id'", src,
                         "resume.js still sends user_id as form field (old bug) — must be query param")
        self.assertIn("user_id=", src,
                      "resume.js does not include user_id in query string")

    def test_results_page_exists(self):
        r = requests.get(f"{BASE}/results.html")
        self.assertEqual(r.status_code, 200, "results.html not found — history page missing")

    def test_results_js_served(self):
        r = requests.get(f"{BASE}/js/results.js")
        self.assertEqual(r.status_code, 200, "results.js not served")

    def test_history_page_served(self):
        r = requests.get(f"{BASE}/history.html")
        self.assertEqual(r.status_code, 200, "history.html not found")
        self.assertIn("text/html", r.headers.get("content-type", ""))

    def test_history_js_served(self):
        r = requests.get(f"{BASE}/js/history.js")
        self.assertEqual(r.status_code, 200, "history.js not served")

    def test_history_js_fetches_users_history_endpoint(self):
        r = requests.get(f"{BASE}/js/history.js")
        src = r.text
        self.assertIn("/api/users/history/", src,
                      "history.js does not call /api/users/history/ endpoint")

    def test_history_page_has_history_nav_link(self):
        r = requests.get(f"{BASE}/history.html")
        self.assertIn('href="/history.html"', r.text,
                      "history.html missing self nav-link")


# ── 5. User history endpoint ──────────────────────────────────────────────────

class TestUserHistory(unittest.TestCase):

    TEST_USER = f"integration_history_test_{int(time.time())}"

    def test_history_empty_for_new_user(self):
        """Brand-new user should return nulls, not 404."""
        r = _get(f"/api/users/history/{self.TEST_USER}_fresh")
        self.assertEqual(r.status_code, 200,
                         f"Expected 200 for unknown user, got {r.status_code}: {r.text}")
        body = r.json()
        self.assertIsNone(body["assessment"], "New user should have null assessment")
        self.assertIsNone(body["resume"], "New user should have null resume")

    def test_history_schema(self):
        """Response must always include user_id, assessment, resume keys."""
        r = _get(f"/api/users/history/{self.TEST_USER}_schema")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for key in ("user_id", "assessment", "resume"):
            self.assertIn(key, body, f"History response missing key '{key}'")

    def test_history_has_assessment_after_assess(self):
        """After completing an assessment, history.assessment must be populated."""
        tasks_r = _get("/api/cognitive/tasks")
        self.assertEqual(tasks_r.status_code, 200)
        tasks = tasks_r.json()
        responses = [
            {"ability": t["ability"], "is_correct": True, "reaction_time_ms": 500.0}
            for t in tasks
        ]
        _post("/api/cognitive/assess",
              json={"user_id": self.TEST_USER, "responses": responses})

        r = _get(f"/api/users/history/{self.TEST_USER}")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsNotNone(body["assessment"],
                             "assessment should be non-null after cognitive test")
        assessment = body["assessment"]
        self.assertIn("readiness_score", assessment)
        self.assertIn("ability_percentiles", assessment)
        self.assertIn("taken_at", assessment)
        self.assertIsInstance(assessment["readiness_score"], (int, float))

    def test_history_has_resume_after_upload(self):
        """After uploading a resume, history.resume must be populated."""
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                         delete=False, encoding="utf-8") as f:
            f.write("Python FastAPI PostgreSQL AWS Docker Kubernetes React TypeScript")
            path = f.name

        with open(path, "rb") as fh:
            requests.post(
                _api(f"/api/users/resume?user_id={self.TEST_USER}"),
                files={"file": ("resume.txt", fh, "text/plain")},
            )
        os.unlink(path)

        r = _get(f"/api/users/history/{self.TEST_USER}")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsNotNone(body["resume"],
                             "resume should be non-null after upload")
        resume = body["resume"]
        self.assertIn("skills", resume)
        self.assertIn("uploaded_at", resume)
        self.assertIn("file_name", resume)
        self.assertGreater(len(resume["skills"]), 0, "skills list should not be empty")

    def test_history_resume_overwrites_on_second_upload(self):
        """Second upload should replace the previous resume, not append."""
        uid = self.TEST_USER + "_overwrite"
        for content in [
            "Python Django PostgreSQL",
            "React TypeScript Node.js",
        ]:
            with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                             delete=False, encoding="utf-8") as f:
                f.write(content)
                path = f.name
            with open(path, "rb") as fh:
                requests.post(
                    _api(f"/api/users/resume?user_id={uid}"),
                    files={"file": ("resume.txt", fh, "text/plain")},
                )
            os.unlink(path)

        r = _get(f"/api/users/history/{uid}")
        resume = r.json()["resume"]
        skills_lower = [s.lower() for s in resume["skills"]]
        # Second upload content should dominate; first content skills absent or minimal
        self.assertIn("react", skills_lower,
                      "Second resume skills (React) should be present after overwrite")

    def test_assessment_overwrites_on_retake(self):
        """Retaking the assessment should update the latest_assessment_at timestamp."""
        uid = self.TEST_USER + "_retake"
        tasks = _get("/api/cognitive/tasks").json()
        responses = [
            {"ability": t["ability"], "is_correct": True, "reaction_time_ms": 500.0}
            for t in tasks
        ]
        payload = {"user_id": uid, "responses": responses}
        _post("/api/cognitive/assess", json=payload)
        first_snapshot = _get(f"/api/users/history/{uid}").json()

        time.sleep(1)  # ensure timestamps differ
        _post("/api/cognitive/assess", json=payload)
        second_snapshot = _get(f"/api/users/history/{uid}").json()

        t1 = first_snapshot["assessment"]["taken_at"]
        t2 = second_snapshot["assessment"]["taken_at"]
        self.assertNotEqual(t1, t2,
                            "taken_at should update on retake — latest_assessment_at not being saved")


# ── 6. Interview context endpoint ─────────────────────────────────────────────

class TestInterviewContext(unittest.TestCase):

    TEST_USER = f"integration_interview_ctx_{int(time.time())}"

    def _seed_user(self):
        """Upload resume + take assessment to fully populate the user."""
        tasks = _get("/api/cognitive/tasks").json()
        responses = [
            {"ability": t["ability"], "is_correct": i % 2 == 0, "reaction_time_ms": 600.0}
            for i, t in enumerate(tasks)
        ]
        _post("/api/cognitive/assess",
              json={"user_id": self.TEST_USER, "responses": responses})

        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                         delete=False, encoding="utf-8") as f:
            f.write("Python FastAPI AWS Docker PostgreSQL Machine Learning")
            path = f.name
        with open(path, "rb") as fh:
            requests.post(
                _api(f"/api/users/resume?user_id={self.TEST_USER}"),
                files={"file": ("resume.txt", fh, "text/plain")},
            )
        os.unlink(path)

    def test_interview_context_schema(self):
        self._seed_user()
        r = _get(f"/api/users/interview-context/{self.TEST_USER}")
        self.assertEqual(r.status_code, 200, f"Interview context failed: {r.text}")
        body = r.json()
        self.assertIn("user_id", body)
        self.assertIn("cognitive_profile", body)
        self.assertIn("technical_profile", body)

    def test_cognitive_profile_fields(self):
        self._seed_user()
        body = _get(f"/api/users/interview-context/{self.TEST_USER}").json()
        cp = body["cognitive_profile"]
        for field in ("readiness_score", "ability_percentiles", "strengths",
                      "areas_for_improvement", "assessed_at"):
            self.assertIn(field, cp, f"cognitive_profile missing '{field}'")

    def test_technical_profile_fields(self):
        self._seed_user()
        body = _get(f"/api/users/interview-context/{self.TEST_USER}").json()
        tp = body["technical_profile"]
        for field in ("skills", "education", "certifications",
                      "experience_years", "resume_uploaded_at"):
            self.assertIn(field, tp, f"technical_profile missing '{field}'")

    def test_strengths_are_human_readable(self):
        """Strengths should use human labels like 'Deductive Reasoning', not snake_case."""
        self._seed_user()
        body = _get(f"/api/users/interview-context/{self.TEST_USER}").json()
        for strength in body["cognitive_profile"]["strengths"]:
            self.assertNotIn("_", strength,
                             f"Strength '{strength}' is snake_case — should be human-readable")

    def test_context_has_skills(self):
        self._seed_user()
        body = _get(f"/api/users/interview-context/{self.TEST_USER}").json()
        skills = body["technical_profile"]["skills"]
        self.assertGreater(len(skills), 0, "Interview context should include extracted skills")
        skills_lower = [s.lower() for s in skills]
        self.assertIn("python", skills_lower, "Python should be in extracted skills")


if __name__ == "__main__":
    unittest.main()
