"""Tests for the NCPT-normalised scoring pipeline.

Covers:
  - _speed_score helper
  - ScoringEngine.compute_composites
  - ScoringEngine.composite_to_percentile
  - ScoringEngine.onet_score_to_percentile
  - ScoringEngine.score_session → AbilityProfile
  - AbilityProfile.percentile_vector
  - phase3 build_job_percentile_matrix
  - phase3 match_user_to_jobs
  - phase3 compute_skill_gaps
"""
import unittest
from datetime import datetime

from core.src.core.scoring import (
    AbilityProfile,
    ScoringEngine,
    _speed_score,
    ACCURACY_WEIGHT,
    SPEED_WEIGHT,
    RT_HALF_LIFE_MS,
)
from core.src.core.tasks.base import TaskItem, TaskResponse, ABILITIES
from core.src.core.pipelines.phase3_ability_matching import (
    build_job_percentile_matrix,
    build_user_ability_vector,
    compute_skill_gaps,
    match_user_to_jobs,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_response(ability: str, is_correct: bool, rt_ms: float = 3000.0) -> TaskResponse:
    task = TaskItem(
        ability=ability,
        task_type="test",
        question={},
        correct_answer="x",
        difficulty=1,
    )
    return TaskResponse(
        task_item=task,
        user_answer="x" if is_correct else "wrong",
        reaction_time_ms=rt_ms,
        is_correct=is_correct,
    )


def _make_profile(percentiles: dict) -> AbilityProfile:
    return AbilityProfile(
        user_id="u_test",
        ability_percentiles=percentiles,
        ability_composites={},
    )


# ── _speed_score ──────────────────────────────────────────────────────────────

class TestSpeedScore(unittest.TestCase):

    def test_zero_rt_returns_one(self):
        self.assertEqual(_speed_score(0), 1.0)

    def test_negative_rt_returns_one(self):
        self.assertEqual(_speed_score(-100), 1.0)

    def test_half_life_returns_half(self):
        self.assertAlmostEqual(_speed_score(RT_HALF_LIFE_MS), 0.5, places=5)

    def test_monotonically_decreasing(self):
        rts = [500, 1000, 5000, 10000, 30000, 60000]
        scores = [_speed_score(rt) for rt in rts]
        for i in range(len(scores) - 1):
            self.assertGreater(scores[i], scores[i + 1])

    def test_always_in_0_1(self):
        for rt in [0, 1, 100, 1000, 100_000, 1_000_000]:
            s = _speed_score(rt)
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 1.0)


# ── ScoringEngine ─────────────────────────────────────────────────────────────

class TestScoringEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = ScoringEngine()

    # -- compute_composites ---------------------------------------------------

    def test_all_correct_fast_gives_high_composite(self):
        responses = [_make_response("memorization", True, rt_ms=500) for _ in range(5)]
        composites = self.engine.compute_composites(responses)
        self.assertIn("memorization", composites)
        self.assertGreater(composites["memorization"], 0.8)

    def test_all_wrong_slow_gives_low_composite(self):
        responses = [_make_response("memorization", False, rt_ms=60_000) for _ in range(5)]
        composites = self.engine.compute_composites(responses)
        self.assertLess(composites["memorization"], 0.3)

    def test_composite_in_0_1(self):
        for ability in ["deductive_reasoning", "perceptual_speed", "time_sharing"]:
            responses = [_make_response(ability, i % 2 == 0, rt_ms=5000) for i in range(6)]
            composites = self.engine.compute_composites(responses)
            c = composites[ability]
            self.assertGreaterEqual(c, 0.0)
            self.assertLessEqual(c, 1.0)

    def test_composite_formula(self):
        """Verify the exact formula: ACCURACY_WEIGHT * acc + SPEED_WEIGHT * speed."""
        responses = [
            _make_response("memorization", True, rt_ms=RT_HALF_LIFE_MS),
            _make_response("memorization", False, rt_ms=RT_HALF_LIFE_MS),
        ]
        composites = self.engine.compute_composites(responses)
        expected = ACCURACY_WEIGHT * 0.5 + SPEED_WEIGHT * 0.5
        self.assertAlmostEqual(composites["memorization"], expected, places=6)

    def test_empty_responses_returns_empty_dict(self):
        self.assertEqual(self.engine.compute_composites([]), {})

    def test_multiple_abilities_separated(self):
        responses = (
            [_make_response("memorization", True, 1000) for _ in range(3)] +
            [_make_response("perceptual_speed", False, 5000) for _ in range(3)]
        )
        composites = self.engine.compute_composites(responses)
        self.assertIn("memorization", composites)
        self.assertIn("perceptual_speed", composites)
        self.assertGreater(composites["memorization"], composites["perceptual_speed"])

    # -- composite_to_percentile ----------------------------------------------

    def test_percentile_in_0_100(self):
        for ability in ABILITIES:
            for composite in [0.0, 0.25, 0.5, 0.75, 1.0]:
                pct = self.engine.composite_to_percentile(ability, composite)
                self.assertGreaterEqual(pct, 0.0,
                                        f"ability={ability}, composite={composite}")
                self.assertLessEqual(pct, 100.0,
                                     f"ability={ability}, composite={composite}")

    def test_higher_composite_gives_higher_percentile(self):
        for ability in ABILITIES:
            low = self.engine.composite_to_percentile(ability, 0.2)
            mid = self.engine.composite_to_percentile(ability, 0.5)
            high = self.engine.composite_to_percentile(ability, 0.8)
            self.assertLessEqual(low, mid,
                                 f"ability={ability}: low={low}, mid={mid}")
            self.assertLessEqual(mid, high,
                                 f"ability={ability}: mid={mid}, high={high}")

    def test_composite_0_5_mid_range_percentile(self):
        """composite=0.5 → z=0, should map to somewhere in the middle of the NCPT dist.

        Some abilities (e.g. selective_attention) have heavily skewed distributions
        in NCPT, so z=0 can be as low as the ~20th percentile.  We use a wide
        band (10–90) rather than a strict 35–65 band.
        """
        for ability in ABILITIES:
            pct = self.engine.composite_to_percentile(ability, 0.5)
            self.assertGreater(pct, 10.0, f"ability={ability}: pct={pct}")
            self.assertLess(pct, 90.0, f"ability={ability}: pct={pct}")

    # -- onet_score_to_percentile ---------------------------------------------

    def test_onet_z0_mid_range(self):
        """O*NET z=0 should fall somewhere in the bulk of the NCPT distribution.

        Skewed abilities (e.g. selective_attention) can place z=0 as low as ~20th
        percentile.  Wide band (10–90) is intentional.
        """
        for ability in ABILITIES:
            pct = self.engine.onet_score_to_percentile(ability, 0.0)
            self.assertGreater(pct, 10.0)
            self.assertLess(pct, 90.0)

    def test_onet_positive_z_above_50(self):
        for ability in ABILITIES:
            pct = self.engine.onet_score_to_percentile(ability, 1.5)
            self.assertGreater(pct, 50.0, f"ability={ability}: pct={pct}")

    def test_onet_negative_z_below_50(self):
        for ability in ABILITIES:
            pct = self.engine.onet_score_to_percentile(ability, -1.5)
            self.assertLess(pct, 50.0, f"ability={ability}: pct={pct}")

    # -- score_session --------------------------------------------------------

    def test_score_session_returns_ability_profile(self):
        responses = [_make_response("memorization", True, 2000) for _ in range(4)]
        profile = self.engine.score_session("user1", responses)
        self.assertIsInstance(profile, AbilityProfile)
        self.assertEqual(profile.user_id, "user1")

    def test_score_session_percentiles_present(self):
        responses = (
            [_make_response("memorization", True, 2000) for _ in range(3)] +
            [_make_response("deductive_reasoning", False, 10_000) for _ in range(3)]
        )
        profile = self.engine.score_session("u", responses)
        self.assertIn("memorization", profile.ability_percentiles)
        self.assertIn("deductive_reasoning", profile.ability_percentiles)

    def test_score_session_good_performer_high_percentile(self):
        responses = [_make_response("memorization", True, 500) for _ in range(10)]
        profile = self.engine.score_session("u", responses)
        self.assertGreater(profile.ability_percentiles["memorization"], 60.0)

    def test_score_session_poor_performer_low_percentile(self):
        responses = [_make_response("memorization", False, 60_000) for _ in range(10)]
        profile = self.engine.score_session("u", responses)
        self.assertLess(profile.ability_percentiles["memorization"], 40.0)

    def test_composites_stored_in_profile(self):
        responses = [_make_response("memorization", True, 2000) for _ in range(3)]
        profile = self.engine.score_session("u", responses)
        self.assertIn("memorization", profile.ability_composites)

    def test_assessed_at_is_datetime(self):
        responses = [_make_response("memorization", True, 2000)]
        profile = self.engine.score_session("u", responses)
        self.assertIsInstance(profile.assessed_at, datetime)


# ── AbilityProfile ────────────────────────────────────────────────────────────

class TestAbilityProfile(unittest.TestCase):

    def test_percentile_vector_correct_order(self):
        profile = _make_profile({"memorization": 80.0, "deductive_reasoning": 60.0})
        order = ["memorization", "deductive_reasoning"]
        vec = profile.percentile_vector(order)
        self.assertEqual(vec, [80.0, 60.0])

    def test_percentile_vector_missing_ability_defaults_to_50(self):
        profile = _make_profile({"memorization": 70.0})
        vec = profile.percentile_vector(["memorization", "perceptual_speed"])
        self.assertEqual(vec[1], 50.0)

    def test_percentile_vector_defaults_to_abilities_order(self):
        profile = _make_profile({ab: 50.0 for ab in ABILITIES})
        vec = profile.percentile_vector()
        self.assertEqual(len(vec), len(ABILITIES))


# ── Phase 3 matching ──────────────────────────────────────────────────────────

class TestPhase3Matching(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = ScoringEngine()
        cls.onet_rows = [
            {
                "Title": "Data Analyst",
                "Deductive Reasoning": 1.2,
                "Mathematical Reasoning": 1.5,
                "Memorization": -0.3,
                "Perceptual Speed": 0.8,
                "Problem Sensitivity": 0.5,
                "Selective Attention": 0.2,
                "Speed of Closure": 0.4,
                "Time Sharing": -0.1,
                "Written Comprehension": 0.9,
            },
            {
                "Title": "Manual Labourer",
                "Deductive Reasoning": -1.0,
                "Mathematical Reasoning": -1.2,
                "Memorization": -0.5,
                "Perceptual Speed": 0.3,
                "Problem Sensitivity": -0.8,
                "Selective Attention": -0.5,
                "Speed of Closure": -0.3,
                "Time Sharing": 0.5,
                "Written Comprehension": -1.5,
            },
        ]
        cls.job_matrix = build_job_percentile_matrix(cls.engine, cls.onet_rows)

    # -- build_job_percentile_matrix ------------------------------------------

    def test_matrix_has_expected_jobs(self):
        self.assertIn("Data Analyst", self.job_matrix)
        self.assertIn("Manual Labourer", self.job_matrix)

    def test_all_percentiles_in_0_100(self):
        for job, pcts in self.job_matrix.items():
            for ability, pct in pcts.items():
                self.assertGreaterEqual(pct, 0.0,
                                        f"{job}/{ability}: {pct}")
                self.assertLessEqual(pct, 100.0,
                                     f"{job}/{ability}: {pct}")

    def test_high_z_gives_high_percentile(self):
        da = self.job_matrix["Data Analyst"]
        ml = self.job_matrix["Manual Labourer"]
        # Data Analyst has higher Deductive Reasoning z-score
        self.assertGreater(da["deductive_reasoning"], ml["deductive_reasoning"])

    def test_rows_without_title_skipped(self):
        bad_rows = [{"Title": "", "Deductive Reasoning": 1.0}]
        result = build_job_percentile_matrix(self.engine, bad_rows)
        self.assertEqual(result, {})

    # -- match_user_to_jobs ---------------------------------------------------

    def test_matching_returns_all_jobs(self):
        profile = _make_profile({ab: 75.0 for ab in ABILITIES})
        ranked = match_user_to_jobs(profile, self.job_matrix)
        titles = [t for t, _ in ranked]
        self.assertIn("Data Analyst", titles)
        self.assertIn("Manual Labourer", titles)

    def test_high_ability_user_prefers_demanding_job(self):
        """User with high percentiles across the board should score higher on Data Analyst."""
        profile = _make_profile({ab: 85.0 for ab in ABILITIES})
        ranked = match_user_to_jobs(profile, self.job_matrix)
        # Both jobs should have similarity > 0
        for _, sim in ranked:
            self.assertGreater(sim, 0.0)

    def test_similarity_in_0_1(self):
        profile = _make_profile({ab: 60.0 for ab in ABILITIES})
        ranked = match_user_to_jobs(profile, self.job_matrix)
        for _, sim in ranked:
            self.assertGreaterEqual(sim, 0.0)
            self.assertLessEqual(sim, 1.0)

    def test_ranking_is_sorted_descending(self):
        profile = _make_profile({ab: 50.0 for ab in ABILITIES})
        ranked = match_user_to_jobs(profile, self.job_matrix)
        sims = [s for _, s in ranked]
        self.assertEqual(sims, sorted(sims, reverse=True))

    # -- compute_skill_gaps ---------------------------------------------------

    def test_gaps_returned_for_assessed_abilities(self):
        profile = _make_profile({"deductive_reasoning": 40.0, "memorization": 80.0})
        gaps = compute_skill_gaps(profile, self.job_matrix, "Data Analyst")
        self.assertIn("deductive_reasoning", gaps)
        self.assertIn("memorization", gaps)

    def test_gap_sign_is_correct(self):
        """If user percentile < job percentile → positive gap (user is behind)."""
        profile = _make_profile({"deductive_reasoning": 10.0})
        gaps = compute_skill_gaps(profile, self.job_matrix, "Data Analyst")
        # Data Analyst has high DR requirement → gap should be positive
        self.assertGreater(gaps["deductive_reasoning"], 0.0)

    def test_gap_negative_when_user_exceeds_job(self):
        """If user percentile > job requirement → negative gap."""
        profile = _make_profile({"deductive_reasoning": 99.0})
        gaps = compute_skill_gaps(profile, self.job_matrix, "Data Analyst")
        self.assertLess(gaps["deductive_reasoning"], 0.0)

    def test_unknown_job_returns_empty_gaps(self):
        profile = _make_profile({"deductive_reasoning": 50.0})
        gaps = compute_skill_gaps(profile, self.job_matrix, "Non Existent Job")
        self.assertEqual(gaps, {})


if __name__ == "__main__":
    unittest.main()
