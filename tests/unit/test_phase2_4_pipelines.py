import unittest

from core.src.core.pipelines.phase2_user_input import create_user_profile
from core.src.core.pipelines.phase3_ability_matching import (
    build_user_ability_vector,
    compute_ability_similarity,
)
from core.src.core.pipelines.phase4_preference_matching import (
    compute_activity_similarity,
    identify_preferred_careers,
)


class PhasePipelineTests(unittest.TestCase):
    def test_create_user_profile_normalizes_lists(self):
        profile = create_user_profile(" u1 ", ["Python", "python", " SQL "], ["Data", "data"])
        self.assertEqual(profile["user_id"], "u1")
        self.assertEqual(profile["manual_skills"], ["python", "sql"])
        self.assertEqual(profile["interest_tags"], ["data"])

    def test_build_user_ability_vector_ordering(self):
        vec = build_user_ability_vector({"x": 75, "y": 50}, ["x", "y", "z"])
        self.assertEqual(vec, [75.0, 50.0, 0.0])

    def test_compute_ability_similarity_ranks(self):
        user = build_user_ability_vector({"x": 1, "y": 0}, ["x", "y"])
        ranked = compute_ability_similarity(user, {"job1": [1, 0], "job2": [0, 1]})
        self.assertEqual(ranked[0][0], "job1")

    def test_activity_preference_threshold(self):
        sims = compute_activity_similarity([1, 0], {"A": [1, 0], "B": [0, 1]})
        preferred = identify_preferred_careers(sims, threshold=0.5)
        self.assertIn("A", preferred)


if __name__ == "__main__":
    unittest.main()
