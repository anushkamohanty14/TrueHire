"""Unit tests for history persistence: MongoUserStore.save_resume_extraction,
get_user_snapshot, and get_interview_context.

All MongoDB calls are mocked so no live database is required.
"""
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_store(mock_col):
    """Return a MongoUserStore with its _col replaced by mock_col."""
    with patch("core.src.core.storage.mongo_store._get_collection", return_value=mock_col):
        from core.src.core.storage.mongo_store import MongoUserStore
        store = MongoUserStore()
    store._col = mock_col
    return store


# ── save_resume_extraction ────────────────────────────────────────────────────

class TestSaveResumeExtraction(unittest.TestCase):

    def _make_store(self):
        col = MagicMock()
        return _make_store(col), col

    def test_calls_update_one(self):
        store, col = self._make_store()
        store.save_resume_extraction(
            user_id="u1",
            file_name="resume.pdf",
            skills=["Python", "AWS"],
            education=["B.S. Computer Science"],
            certifications=["AWS Certified"],
            experience_years=5.0,
        )
        col.update_one.assert_called_once()

    def test_latest_resume_doc_structure(self):
        store, col = self._make_store()
        store.save_resume_extraction(
            user_id="u1",
            file_name="cv.pdf",
            skills=["Python"],
            education=["PhD Computer Science"],
            certifications=["PMP"],
            experience_years=10.0,
        )
        _, kwargs = col.update_one.call_args
        # Not using keyword args — get positional
        args = col.update_one.call_args[0]
        update_doc = args[1]

        set_doc = update_doc["$set"]
        self.assertIn("latest_resume", set_doc)
        resume = set_doc["latest_resume"]
        self.assertEqual(resume["file_name"], "cv.pdf")
        self.assertEqual(resume["skills"], ["Python"])
        self.assertEqual(resume["education"], ["PhD Computer Science"])
        self.assertEqual(resume["certifications"], ["PMP"])
        self.assertEqual(resume["experience_years"], 10.0)
        self.assertIn("uploaded_at", resume)

    def test_resume_skills_also_updated(self):
        """resume_skills top-level field must be updated for backward compat."""
        store, col = self._make_store()
        store.save_resume_extraction(
            user_id="u1", file_name="r.pdf",
            skills=["Go", "Docker"], education=[], certifications=[], experience_years=None,
        )
        args = col.update_one.call_args[0]
        set_doc = args[1]["$set"]
        self.assertEqual(set_doc["resume_skills"], ["Go", "Docker"])

    def test_upsert_true(self):
        store, col = self._make_store()
        store.save_resume_extraction(
            user_id="u1", file_name="r.pdf",
            skills=[], education=[], certifications=[], experience_years=None,
        )
        _, kw = col.update_one.call_args
        self.assertTrue(kw.get("upsert", False))

    def test_none_experience_years_stored(self):
        """None experience_years should be stored without error."""
        store, col = self._make_store()
        store.save_resume_extraction(
            user_id="u1", file_name="r.pdf",
            skills=[], education=[], certifications=[], experience_years=None,
        )
        args = col.update_one.call_args[0]
        resume = args[1]["$set"]["latest_resume"]
        self.assertIsNone(resume["experience_years"])


# ── get_user_snapshot ─────────────────────────────────────────────────────────

class TestGetUserSnapshot(unittest.TestCase):

    def test_returns_none_for_missing_user(self):
        col = MagicMock()
        col.find_one.return_value = None
        store = _make_store(col)
        result = store.get_user_snapshot("ghost_user")
        self.assertIsNone(result["assessment"])
        self.assertIsNone(result["resume"])
        self.assertEqual(result["user_id"], "ghost_user")

    def test_returns_assessment_when_present(self):
        col = MagicMock()
        col.find_one.return_value = {
            "user_id": "u1",
            "ability_percentiles": {"deductive_reasoning": 75.0},
            "readiness_score": 75.0,
            "latest_assessment_at": "2024-01-15T10:00:00+00:00",
        }
        store = _make_store(col)
        result = store.get_user_snapshot("u1")
        self.assertIsNotNone(result["assessment"])
        self.assertEqual(result["assessment"]["readiness_score"], 75.0)
        self.assertEqual(result["assessment"]["taken_at"], "2024-01-15T10:00:00+00:00")

    def test_returns_resume_when_present(self):
        col = MagicMock()
        col.find_one.return_value = {
            "user_id": "u1",
            "latest_resume": {
                "uploaded_at": "2024-01-14T09:00:00+00:00",
                "file_name": "my_cv.pdf",
                "skills": ["Python", "AWS"],
                "education": ["B.S. CS"],
                "certifications": ["AWS Certified"],
                "experience_years": 3.0,
            },
        }
        store = _make_store(col)
        result = store.get_user_snapshot("u1")
        self.assertIsNotNone(result["resume"])
        self.assertEqual(result["resume"]["file_name"], "my_cv.pdf")
        self.assertEqual(result["resume"]["skills"], ["Python", "AWS"])

    def test_assessment_none_when_no_percentiles(self):
        """Doc exists but no cognitive assessment taken yet."""
        col = MagicMock()
        col.find_one.return_value = {
            "user_id": "u1",
            "resume_skills": ["Python"],
            "latest_resume": {"skills": ["Python"]},
        }
        store = _make_store(col)
        result = store.get_user_snapshot("u1")
        self.assertIsNone(result["assessment"])

    def test_both_present(self):
        col = MagicMock()
        col.find_one.return_value = {
            "user_id": "u2",
            "ability_percentiles": {"deductive_reasoning": 80, "mathematical_reasoning": 60},
            "readiness_score": 70.0,
            "latest_assessment_at": "2024-03-01T12:00:00+00:00",
            "latest_resume": {
                "uploaded_at": "2024-03-01T11:00:00+00:00",
                "file_name": "cv.pdf",
                "skills": ["Java"],
                "education": [],
                "certifications": [],
                "experience_years": 7.0,
            },
        }
        store = _make_store(col)
        result = store.get_user_snapshot("u2")
        self.assertIsNotNone(result["assessment"])
        self.assertIsNotNone(result["resume"])


# ── get_interview_context ─────────────────────────────────────────────────────

class TestGetInterviewContext(unittest.TestCase):

    def _doc_with_both(self):
        return {
            "user_id": "u3",
            "ability_percentiles": {
                "deductive_reasoning": 85.0,
                "mathematical_reasoning": 72.0,
                "memorization": 30.0,
                "perceptual_speed": 25.0,
                "problem_sensitivity": 60.0,
                "selective_attention": 55.0,
                "speed_of_closure": 70.0,
                "time_sharing": 45.0,
                "written_comprehension": 90.0,
            },
            "readiness_score": 59.1,
            "latest_assessment_at": "2024-03-01T12:00:00+00:00",
            "latest_resume": {
                "uploaded_at": "2024-03-01T11:00:00+00:00",
                "file_name": "cv.pdf",
                "skills": ["Python", "FastAPI"],
                "education": ["B.S. Computer Science"],
                "certifications": ["AWS Certified Solutions Architect"],
                "experience_years": 4.0,
            },
        }

    def test_returns_user_id(self):
        col = MagicMock()
        col.find_one.return_value = self._doc_with_both()
        store = _make_store(col)
        ctx = store.get_interview_context("u3")
        self.assertEqual(ctx["user_id"], "u3")

    def test_strengths_above_70(self):
        col = MagicMock()
        col.find_one.return_value = self._doc_with_both()
        store = _make_store(col)
        ctx = store.get_interview_context("u3")
        strengths = ctx["cognitive_profile"]["strengths"]
        # deductive_reasoning (85), written_comprehension (90), speed_of_closure (70) qualify
        self.assertGreater(len(strengths), 0)
        self.assertIn("Deductive Reasoning", strengths)
        self.assertIn("Written Comprehension", strengths)

    def test_improvements_below_40(self):
        col = MagicMock()
        col.find_one.return_value = self._doc_with_both()
        store = _make_store(col)
        ctx = store.get_interview_context("u3")
        improvements = ctx["cognitive_profile"]["areas_for_improvement"]
        self.assertIn("Memorization", improvements)
        self.assertIn("Perceptual Speed", improvements)

    def test_technical_profile_fields(self):
        col = MagicMock()
        col.find_one.return_value = self._doc_with_both()
        store = _make_store(col)
        ctx = store.get_interview_context("u3")
        tp = ctx["technical_profile"]
        self.assertEqual(tp["skills"], ["Python", "FastAPI"])
        self.assertEqual(tp["education"], ["B.S. Computer Science"])
        self.assertEqual(tp["certifications"], ["AWS Certified Solutions Architect"])
        self.assertEqual(tp["experience_years"], 4.0)

    def test_empty_user_returns_empty_profiles(self):
        col = MagicMock()
        col.find_one.return_value = None
        store = _make_store(col)
        ctx = store.get_interview_context("nobody")
        self.assertEqual(ctx["cognitive_profile"]["strengths"], [])
        self.assertEqual(ctx["technical_profile"]["skills"], [])
        self.assertIsNone(ctx["cognitive_profile"]["readiness_score"])

    def test_ability_percentiles_present_in_context(self):
        col = MagicMock()
        col.find_one.return_value = self._doc_with_both()
        store = _make_store(col)
        ctx = store.get_interview_context("u3")
        self.assertIn("ability_percentiles", ctx["cognitive_profile"])
        self.assertEqual(ctx["cognitive_profile"]["ability_percentiles"]["deductive_reasoning"], 85.0)


# ── save_assessment timestamp ─────────────────────────────────────────────────

class TestSaveAssessmentTimestamp(unittest.TestCase):
    """save_assessment must write latest_assessment_at for snapshot to work."""

    def test_latest_assessment_at_set(self):
        col = MagicMock()
        store = _make_store(col)
        store.save_assessment(
            user_id="u1",
            ability_percentiles={"deductive_reasoning": 60.0},
            readiness_score=60.0,
            task_responses=[],
        )
        args = col.update_one.call_args[0]
        set_doc = args[1]["$set"]
        self.assertIn("latest_assessment_at", set_doc)
        # Should be a valid ISO timestamp string
        ts = set_doc["latest_assessment_at"]
        self.assertIsInstance(ts, str)
        datetime.fromisoformat(ts)  # raises if not valid


if __name__ == "__main__":
    unittest.main()
