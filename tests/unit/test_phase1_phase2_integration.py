import os
import tempfile
import unittest
from pathlib import Path

from apps.api.src.services.profile_service import ProfileService
from core.src.core.pipelines.phase1_onet_data import build_job_ability_matrix, clean_onet_data, load_onet_data
from core.src.core.pipelines.phase2_user_input import upload_resume
from core.src.core.storage.user_store import JsonUserStore


class Phase1Phase2IntegrationTests(unittest.TestCase):
    def test_phase1_load_clean_build_matrix(self):
        rows = load_onet_data("job_abilities_onet.csv")
        self.assertGreater(len(rows), 0)

        cleaned = clean_onet_data(rows)
        matrix = build_job_ability_matrix(cleaned)

        self.assertIn("Accountants and Auditors", matrix)
        self.assertEqual(len(matrix["Accountants and Auditors"]), 9)

    def test_profile_service_enriches_from_phase1_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "profiles.json"
            service = ProfileService(store=JsonUserStore(str(store_path)))

            profile = service.create_profile(
                user_id="u123",
                manual_skills=["Python", "SQL"],
                interest_tags=["nurse", "account"],
            )

            self.assertEqual(profile["user_id"], "u123")
            self.assertIn("phase1_job_suggestions", profile)
            self.assertGreater(len(profile["phase1_job_suggestions"]), 0)

            fetched = service.get_profile("u123")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["manual_skills"], ["python", "sql"])

    def test_resume_upload_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original = Path.cwd()
            try:
                os.chdir(tmp_dir)
                result = upload_resume("cv.txt", b"sample resume", "u999")
                self.assertEqual(result["size_bytes"], 13)
                self.assertTrue(Path(result["saved_path"]).exists())
            finally:
                os.chdir(original)


if __name__ == "__main__":
    unittest.main()
