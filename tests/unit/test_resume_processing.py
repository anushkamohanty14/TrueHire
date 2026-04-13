"""Tests for Phase 5 — resume text extraction and skill identification."""
import os
import tempfile
import unittest

from core.src.core.pipelines.phase5_resume_processing import (
    SkillExtractionResult,
    _normalise,
    extract_skills,
    extract_skills_rules,
    extract_text,
    process_resume,
)
from core.src.core.pipelines.phase2_user_input import merge_resume_skills, get_user_profile, save_user_profile


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_txt(content: str) -> str:
    """Write content to a temp .txt file, return path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                     delete=False, encoding="utf-8")
    tmp.write(content)
    tmp.close()
    return tmp.name


SAMPLE_RESUME = """\
John Doe — Software Engineer

Skills: Python, Django, FastAPI, PostgreSQL, Docker, AWS, Git, React

Experience:
- Built REST APIs with FastAPI and PostgreSQL.
- Deployed microservices on Kubernetes using Terraform.
- Implemented CI/CD pipelines with GitHub Actions.
- Data analysis using Pandas and NumPy.

Education: BSc Computer Science
"""


# ── _normalise ────────────────────────────────────────────────────────────────

class TestNormalise(unittest.TestCase):

    def test_deduplicates_case_insensitive(self):
        result = _normalise(["Python", "python", "PYTHON"])
        self.assertEqual(len(result), 1)

    def test_preserves_first_seen_casing(self):
        result = _normalise(["Python", "python"])
        self.assertIn("Python", result)

    def test_sorted_alphabetically(self):
        skills = _normalise(["Rust", "AWS", "Docker"])
        self.assertEqual(skills, sorted(skills, key=str.lower))

    def test_strips_whitespace(self):
        result = _normalise(["  Python  ", "  SQL "])
        for s in result:
            self.assertEqual(s, s.strip())

    def test_empty_strings_excluded(self):
        result = _normalise(["", "  ", "Python"])
        self.assertNotIn("", result)


# ── extract_text ──────────────────────────────────────────────────────────────

class TestExtractText(unittest.TestCase):

    def test_txt_file(self):
        path = _write_txt("Python developer with AWS experience")
        try:
            text = extract_text(path)
            self.assertIn("Python", text)
            self.assertIn("AWS", text)
        finally:
            os.unlink(path)

    def test_txt_returns_string(self):
        path = _write_txt("some content")
        try:
            self.assertIsInstance(extract_text(path), str)
        finally:
            os.unlink(path)


# ── extract_skills_rules ──────────────────────────────────────────────────────

class TestExtractSkillsRules(unittest.TestCase):

    def test_detects_python(self):
        self.assertIn("Python", extract_skills_rules("Experienced Python developer"))

    def test_detects_multiple_skills(self):
        skills = extract_skills_rules(SAMPLE_RESUME)
        for expected in ["Python", "Django", "FastAPI", "PostgreSQL", "Docker", "AWS"]:
            self.assertIn(expected, skills, f"Expected '{expected}' in {skills}")

    def test_case_insensitive_match(self):
        skills = extract_skills_rules("proficient in PYTHON and javascript")
        self.assertIn("Python", skills)
        self.assertIn("JavaScript", skills)

    def test_returns_list(self):
        self.assertIsInstance(extract_skills_rules("Python"), list)

    def test_no_false_positives_on_empty(self):
        skills = extract_skills_rules("")
        self.assertEqual(skills, [])

    def test_no_partial_word_match(self):
        # "Rust" should not match "frustrated"
        skills = extract_skills_rules("I was frustrated by the deadline")
        self.assertNotIn("Rust", skills)

    def test_deduplication(self):
        text = "Python Python Python"
        skills = extract_skills_rules(text)
        self.assertEqual(skills.count("Python"), 1)


# ── extract_skills ────────────────────────────────────────────────────────────

class TestExtractSkills(unittest.TestCase):

    def test_always_uses_rules(self):
        result = extract_skills(SAMPLE_RESUME)
        self.assertEqual(result.method, "rules")
        self.assertIsInstance(result.skills, list)
        self.assertGreater(len(result.skills), 0)

    def test_result_has_correct_fields(self):
        result = extract_skills(SAMPLE_RESUME)
        self.assertIsInstance(result, SkillExtractionResult)
        self.assertIsInstance(result.skills, list)
        self.assertIsInstance(result.raw_text_length, int)
        self.assertEqual(result.raw_text_length, len(SAMPLE_RESUME))


# ── process_resume ────────────────────────────────────────────────────────────

class TestProcessResume(unittest.TestCase):

    def test_txt_resume_extracts_skills(self):
        path = _write_txt(SAMPLE_RESUME)
        try:
            result = process_resume(path)
            self.assertNotEqual(result.method, "error")
            self.assertGreater(len(result.skills), 0)
        finally:
            os.unlink(path)

    def test_empty_file_returns_error(self):
        path = _write_txt("   ")
        try:
            result = process_resume(path)
            self.assertEqual(result.method, "error")
            self.assertIsNotNone(result.error)
            self.assertEqual(result.skills, [])
        finally:
            os.unlink(path)

    def test_nonexistent_file_returns_error(self):
        result = process_resume("/tmp/does_not_exist_xyz.txt")
        self.assertEqual(result.method, "error")
        self.assertIsNotNone(result.error)

    def test_raw_text_length_populated(self):
        path = _write_txt(SAMPLE_RESUME)
        try:
            result = process_resume(path)
            self.assertGreater(result.raw_text_length, 0)
        finally:
            os.unlink(path)


# ── merge_resume_skills ───────────────────────────────────────────────────────

class TestMergeResumeSkills(unittest.TestCase):

    def test_skills_saved_to_profile(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            profile = {"user_id": "u1", "manual_skills": [], "interest_tags": []}
            save_user_profile(profile, path)
            merge_resume_skills("u1", ["Python", "SQL", "Docker"], storage_path=path)
            updated = get_user_profile("u1", path)
            self.assertIn("resume_skills", updated)
            self.assertIn("python", updated["resume_skills"])
            self.assertIn("sql", updated["resume_skills"])
        finally:
            os.unlink(path)

    def test_noop_when_no_profile_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        os.unlink(path)
        try:
            merge_resume_skills("nonexistent", ["Python"], storage_path=path)
            # should not raise
        except Exception as exc:
            self.fail(f"merge_resume_skills raised unexpectedly: {exc}")

    def test_manual_skills_unchanged(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            profile = {"user_id": "u2", "manual_skills": ["java"], "interest_tags": []}
            save_user_profile(profile, path)
            merge_resume_skills("u2", ["Python"], storage_path=path)
            updated = get_user_profile("u2", path)
            self.assertIn("java", updated["manual_skills"])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
