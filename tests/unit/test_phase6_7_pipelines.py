"""Tests for Phase 6 (skill matching) and Phase 7 (hybrid recommendation)."""
import unittest

import numpy as np
import pandas as pd

from core.src.core.pipelines.phase6_skill_matching import (
    build_tech_matrix,
    compute_skill_similarity,
    _tech_weight,
)
from core.src.core.pipelines.phase7_hybrid_recommendation import (
    HybridRecommender,
    RecommendationResult,
    _normalise_weights,
    _find_best_job,
)


# ── Shared fixtures ───────────────────────────────────────────────────────────

SAMPLE_PERCENTILES = {
    "Deductive Reasoning": 80,
    "Mathematical Reasoning": 75,
    "Memorization": 55,
    "Perceptual Speed": 60,
    "Problem Sensitivity": 70,
    "Selective Attention": 65,
    "Speed of Closure": 58,
    "Time Sharing": 50,
    "Written Comprehension": 72,
}

SAMPLE_SKILLS = ["Python", "SQL", "TensorFlow", "AWS", "Docker"]


# ── Phase 6: tech weight ───────────────────────────────────────────────────────

class TestTechWeight(unittest.TestCase):

    def test_both_hot_and_demand(self):
        self.assertEqual(_tech_weight("Y", "Y"), 2.0)

    def test_hot_only(self):
        self.assertEqual(_tech_weight("Y", "N"), 1.5)

    def test_demand_only(self):
        self.assertEqual(_tech_weight("N", "Y"), 1.5)

    def test_neither(self):
        self.assertEqual(_tech_weight("N", "N"), 1.0)


# ── Phase 6: build_tech_matrix ────────────────────────────────────────────────

class TestBuildTechMatrix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.matrix = build_tech_matrix()

    def test_returns_dataframe(self):
        self.assertIsInstance(self.matrix, pd.DataFrame)

    def test_has_jobs_as_index(self):
        self.assertGreater(len(self.matrix), 0)

    def test_rows_sum_to_one(self):
        row_sums = self.matrix.sum(axis=1)
        self.assertTrue((row_sums.round(6) == 1.0).all())

    def test_no_negative_values(self):
        self.assertTrue((self.matrix >= 0).all().all())

    def test_common_job_present(self):
        self.assertIn("Software Developers", self.matrix.index)


# ── Phase 6: compute_skill_similarity ─────────────────────────────────────────

class TestComputeSkillSimilarity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.matrix = build_tech_matrix()

    def test_returns_series(self):
        result = compute_skill_similarity(SAMPLE_SKILLS, self.matrix)
        self.assertIsInstance(result, pd.Series)

    def test_index_matches_jobs(self):
        result = compute_skill_similarity(SAMPLE_SKILLS, self.matrix)
        self.assertEqual(list(result.index), list(self.matrix.index))

    def test_scores_in_0_1(self):
        result = compute_skill_similarity(SAMPLE_SKILLS, self.matrix)
        self.assertTrue((result >= 0).all())
        self.assertTrue((result <= 1).all())

    def test_empty_skills_returns_zeros(self):
        result = compute_skill_similarity([], self.matrix)
        self.assertTrue((result == 0).all())

    def test_known_skill_scores_nonzero(self):
        # Python is a common tech skill — at least some jobs should match
        result = compute_skill_similarity(["Python"], self.matrix)
        self.assertGreater(result.max(), 0)

    def test_case_insensitive_matching(self):
        upper = compute_skill_similarity(["PYTHON"], self.matrix)
        lower = compute_skill_similarity(["python"], self.matrix)
        pd.testing.assert_series_equal(upper, lower)


# ── Phase 7: _normalise_weights ───────────────────────────────────────────────

class TestNormaliseWeights(unittest.TestCase):

    def test_already_summing_to_one(self):
        w = _normalise_weights({"ability": 0.4, "activity": 0.3, "skill": 0.3})
        self.assertAlmostEqual(sum(w.values()), 1.0, places=6)

    def test_unnormalised_weights(self):
        w = _normalise_weights({"ability": 2, "activity": 1, "skill": 1})
        self.assertAlmostEqual(sum(w.values()), 1.0, places=6)
        self.assertAlmostEqual(w["ability"], 0.5, places=6)

    def test_zero_weights_returns_default(self):
        from core.src.core.pipelines.phase7_hybrid_recommendation import DEFAULT_WEIGHTS
        w = _normalise_weights({"ability": 0, "activity": 0, "skill": 0})
        self.assertEqual(w, DEFAULT_WEIGHTS)


# ── Phase 7: _find_best_job ───────────────────────────────────────────────────

class TestFindBestJob(unittest.TestCase):

    def setUp(self):
        self.index = pd.Index([
            "Software Developers",
            "Data Scientists",
            "Registered Nurses",
            "Aerospace Engineers",
        ])

    def test_exact_match(self):
        self.assertEqual(_find_best_job("Data Scientists", self.index), "Data Scientists")

    def test_case_insensitive_exact(self):
        self.assertEqual(_find_best_job("data scientists", self.index), "Data Scientists")

    def test_partial_match(self):
        result = _find_best_job("software", self.index)
        self.assertEqual(result, "Software Developers")

    def test_fuzzy_match(self):
        result = _find_best_job("data science", self.index)
        self.assertEqual(result, "Data Scientists")


# ── Phase 7: HybridRecommender ────────────────────────────────────────────────

class TestHybridRecommender(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rec = HybridRecommender()

    def test_loads_all_matrices(self):
        self.assertGreater(len(self.rec.ja_pivot), 0)
        self.assertGreater(len(self.rec.wa_final), 0)
        self.assertGreater(len(self.rec.tech_matrix), 0)
        self.assertGreater(len(self.rec.atwa_matrix), 0)

    def test_common_job_count(self):
        # All three matrices must share the same index after alignment
        self.assertEqual(len(self.rec.ja_pivot), len(self.rec.wa_final))
        self.assertEqual(len(self.rec.ja_pivot), len(self.rec.tech_matrix))

    def test_recommend_returns_list(self):
        results = self.rec.recommend(SAMPLE_PERCENTILES, SAMPLE_SKILLS, top_n=5)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 5)

    def test_results_are_recommendation_results(self):
        results = self.rec.recommend(SAMPLE_PERCENTILES, SAMPLE_SKILLS, top_n=3)
        for r in results:
            self.assertIsInstance(r, RecommendationResult)

    def test_ranks_are_sequential(self):
        results = self.rec.recommend(SAMPLE_PERCENTILES, SAMPLE_SKILLS, top_n=5)
        ranks = [r.rank for r in results]
        self.assertEqual(ranks, list(range(1, 6)))

    def test_sorted_descending_by_score(self):
        results = self.rec.recommend(SAMPLE_PERCENTILES, SAMPLE_SKILLS, top_n=10)
        scores = [r.total_score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_scores_in_valid_range(self):
        results = self.rec.recommend(SAMPLE_PERCENTILES, SAMPLE_SKILLS, top_n=5)
        for r in results:
            self.assertGreaterEqual(r.total_score, -1.0)
            self.assertLessEqual(r.total_score, 1.0)

    def test_strength_activities_are_strings(self):
        results = self.rec.recommend(SAMPLE_PERCENTILES, SAMPLE_SKILLS, top_n=3)
        for r in results:
            for act in r.strength_activities:
                self.assertIsInstance(act, str)

    def test_dynamic_weights_change_results(self):
        ability_heavy = self.rec.recommend(
            SAMPLE_PERCENTILES, SAMPLE_SKILLS,
            weights={"ability": 1.0, "activity": 0.0, "skill": 0.0}, top_n=10
        )
        skill_heavy = self.rec.recommend(
            SAMPLE_PERCENTILES, SAMPLE_SKILLS,
            weights={"ability": 0.0, "activity": 0.0, "skill": 1.0}, top_n=10
        )
        top_ability = {r.job_title for r in ability_heavy[:3]}
        top_skill = {r.job_title for r in skill_heavy[:3]}
        # Different weight profiles should produce at least partially different top-3
        self.assertNotEqual(top_ability, top_skill)

    def test_empty_skills_still_returns_results(self):
        results = self.rec.recommend(SAMPLE_PERCENTILES, [], top_n=5)
        self.assertEqual(len(results), 5)

    def test_explain_job_returns_dict(self):
        detail = self.rec.explain_job("Software Developers", SAMPLE_PERCENTILES)
        self.assertIsInstance(detail, dict)
        self.assertIn("job", detail)
        self.assertIn("match_percent", detail)
        self.assertIn("strength_activities", detail)
        self.assertIn("gap_activities", detail)

    def test_explain_job_fuzzy_resolution(self):
        detail = self.rec.explain_job("software developer", SAMPLE_PERCENTILES)
        self.assertIn("Software", detail["job"])

    def test_match_percent_in_range(self):
        detail = self.rec.explain_job("Data Scientists", SAMPLE_PERCENTILES)
        self.assertGreaterEqual(detail["match_percent"], 0)
        self.assertLessEqual(detail["match_percent"], 100)


if __name__ == "__main__":
    unittest.main()
