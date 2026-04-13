"""Tests for rule-based cognitive task generators (Steps 1-3).

Each test class covers one generator and verifies:
  - correct number of items returned
  - ability / task_type fields set correctly
  - correct_answer is valid (in allowed set or mathematically correct)
  - difficulty clamping (values outside 1-5 are handled)
  - metadata consistency with the question / correct_answer
  - BaseTaskGenerator.score_response works correctly
"""
import unittest

from core.src.core.tasks import (
    DigitSpanGenerator,
    MathReasoningGenerator,
    SequenceCompletionGenerator,
    StroopGenerator,
    SyllogismGenerator,
    SymbolSearchGenerator,
    RuleViolationGenerator,
    TaskItem,
    TimeShareGenerator,
    WrittenComprehensionGenerator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dummy_task(ability="test", task_type="test", question=None,
                     correct_answer="x", difficulty=1):
    return TaskItem(
        ability=ability, task_type=task_type,
        question=question or {}, correct_answer=correct_answer,
        difficulty=difficulty,
    )


# ---------------------------------------------------------------------------
# BaseTaskGenerator.score_response (via a concrete subclass)
# ---------------------------------------------------------------------------

class TestBaseScoreResponse(unittest.TestCase):

    def setUp(self):
        self.gen = DigitSpanGenerator()

    def test_exact_match(self):
        task = _make_dummy_task(correct_answer="7 2 9")
        self.assertTrue(self.gen.score_response(task, "7 2 9"))

    def test_extra_whitespace_ignored(self):
        task = _make_dummy_task(correct_answer="7 2 9")
        self.assertTrue(self.gen.score_response(task, "  7  2  9 "))

    def test_wrong_answer(self):
        task = _make_dummy_task(correct_answer="7 2 9")
        self.assertFalse(self.gen.score_response(task, "7 2 8"))


# ---------------------------------------------------------------------------
# DigitSpanGenerator
# ---------------------------------------------------------------------------

class TestDigitSpanGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = DigitSpanGenerator()

    def test_ability_and_task_type(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertEqual(item.ability, "memorization")
        self.assertEqual(item.task_type, "digit_span")

    def test_returns_n_items(self):
        for n in (1, 3, 5):
            with self.subTest(n=n):
                self.assertEqual(len(self.gen.generate(n=n)), n)

    def test_sequence_length_scales_with_difficulty(self):
        for diff in range(1, 6):
            item = self.gen.generate(difficulty=diff, n=1)[0]
            expected_length = 3 + diff
            self.assertEqual(item.metadata["length"], expected_length)
            seq = item.question["sequence"]
            self.assertEqual(len(seq), expected_length)

    def test_correct_answer_matches_sequence(self):
        for _ in range(20):
            item = self.gen.generate(difficulty=3, n=1)[0]
            expected = " ".join(item.question["sequence"])
            self.assertEqual(item.correct_answer, expected)

    def test_all_elements_are_digits(self):
        item = self.gen.generate(difficulty=5, n=1)[0]
        for ch in item.question["sequence"]:
            self.assertTrue(ch.isdigit(), f"Expected digit, got {ch!r}")

    def test_difficulty_clamping_low(self):
        item = self.gen.generate(difficulty=0, n=1)[0]
        self.assertEqual(item.metadata["length"], 4)  # clamped to 1

    def test_difficulty_clamping_high(self):
        item = self.gen.generate(difficulty=99, n=1)[0]
        self.assertEqual(item.metadata["length"], 8)  # clamped to 5

    def test_score_correct_answer(self):
        item = self.gen.generate(difficulty=2, n=1)[0]
        self.assertTrue(self.gen.score_response(item, item.correct_answer))

    def test_score_wrong_answer(self):
        item = self.gen.generate(difficulty=2, n=1)[0]
        self.assertFalse(self.gen.score_response(item, "0 0 0 0 0"))


# ---------------------------------------------------------------------------
# SymbolSearchGenerator
# ---------------------------------------------------------------------------

class TestSymbolSearchGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = SymbolSearchGenerator()

    def test_ability_and_task_type(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertEqual(item.ability, "perceptual_speed")
        self.assertEqual(item.task_type, "symbol_search")

    def test_returns_n_items(self):
        self.assertEqual(len(self.gen.generate(n=5)), 5)

    def test_correct_answer_matches_target_presence(self):
        for _ in range(50):
            item = self.gen.generate(difficulty=2, n=1)[0]
            target = item.question["target"]
            grid = item.question["grid"]
            actually_present = target in grid
            expected_answer = "yes" if actually_present else "no"
            self.assertEqual(item.correct_answer, expected_answer,
                             f"target={target}, grid={grid}")

    def test_metadata_target_present_consistent(self):
        for _ in range(30):
            item = self.gen.generate(difficulty=3, n=1)[0]
            target = item.question["target"]
            grid = item.question["grid"]
            self.assertEqual(item.metadata["target_present"], target in grid)

    def test_correct_answer_is_yes_or_no(self):
        for _ in range(20):
            item = self.gen.generate(n=1)[0]
            self.assertIn(item.correct_answer, ("yes", "no"))

    def test_options_in_question(self):
        item = self.gen.generate(n=1)[0]
        self.assertIn("yes", item.question["options"])
        self.assertIn("no", item.question["options"])

    def test_grid_size_scales_with_difficulty(self):
        for diff in range(1, 6):
            item = self.gen.generate(difficulty=diff, n=1)[0]
            expected = 4 + diff
            self.assertEqual(item.metadata["grid_size"], expected,
                             f"difficulty={diff}")


# ---------------------------------------------------------------------------
# StroopGenerator
# ---------------------------------------------------------------------------

class TestStroopGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = StroopGenerator()

    def test_ability_and_task_type(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertEqual(item.ability, "selective_attention")
        self.assertEqual(item.task_type, "stroop")

    def test_returns_n_items(self):
        self.assertEqual(len(self.gen.generate(n=4)), 4)

    def test_always_incongruent(self):
        for _ in range(30):
            item = self.gen.generate(n=1)[0]
            word = item.metadata["word"]
            ink = item.metadata["ink_color"]
            self.assertNotEqual(word, ink, "Stroop task must be incongruent")

    def test_correct_answer_is_ink_color(self):
        for _ in range(30):
            item = self.gen.generate(n=1)[0]
            self.assertEqual(item.correct_answer, item.question["ink_color"])

    def test_correct_answer_in_options(self):
        for _ in range(20):
            item = self.gen.generate(n=1)[0]
            self.assertIn(item.correct_answer, item.question["options"])

    def test_options_has_four_entries(self):
        item = self.gen.generate(n=1)[0]
        self.assertEqual(len(item.question["options"]), 4)

    def test_word_not_in_correct_answer(self):
        # The word is never the correct answer (always incongruent)
        for _ in range(30):
            item = self.gen.generate(n=1)[0]
            self.assertNotEqual(item.question["word"].lower(), item.correct_answer)


# ---------------------------------------------------------------------------
# SequenceCompletionGenerator
# ---------------------------------------------------------------------------

class TestSequenceCompletionGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = SequenceCompletionGenerator()

    def test_ability_and_task_type(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertEqual(item.ability, "speed_of_closure")
        self.assertEqual(item.task_type, "sequence_completion")

    def test_returns_n_items(self):
        self.assertEqual(len(self.gen.generate(n=6)), 6)

    def test_correct_answer_matches_full_sequence_at_gap(self):
        """Verify correct_answer == full_sequence[gap_index] for all patterns."""
        for diff in range(1, 6):
            for _ in range(10):
                item = self.gen.generate(difficulty=diff, n=1)[0]
                full = item.metadata["full_sequence"]
                gap = item.metadata["gap_index"]
                self.assertEqual(
                    item.correct_answer, full[gap],
                    f"diff={diff}, full={full}, gap={gap}, answer={item.correct_answer}"
                )

    def test_question_has_exactly_one_gap(self):
        for diff in range(1, 6):
            item = self.gen.generate(difficulty=diff, n=1)[0]
            seq = item.question["sequence"]
            self.assertEqual(seq.count("?"), 1, f"Expected one gap, got: {seq}")

    def test_arithmetic_correctness(self):
        for _ in range(20):
            item = self.gen.generate(difficulty=1, n=1)[0]
            full = [int(x) for x in item.metadata["full_sequence"]]
            step = item.metadata["step"]
            for i in range(1, len(full)):
                self.assertEqual(full[i] - full[i - 1], step)

    def test_geometric_correctness(self):
        for _ in range(20):
            item = self.gen.generate(difficulty=3, n=1)[0]
            full = [int(x) for x in item.metadata["full_sequence"]]
            ratio = item.metadata["ratio"]
            for i in range(1, len(full)):
                self.assertEqual(full[i], full[i - 1] * ratio)

    def test_alphabetical_correctness(self):
        for _ in range(20):
            item = self.gen.generate(difficulty=4, n=1)[0]
            full = item.metadata["full_sequence"]
            step = item.metadata["step"]
            for i in range(1, len(full)):
                diff = (ord(full[i]) - ord(full[i - 1])) % 26
                self.assertEqual(diff, step)

    def test_additive_correctness(self):
        for _ in range(20):
            item = self.gen.generate(difficulty=5, n=1)[0]
            full = [int(x) for x in item.metadata["full_sequence"]]
            for i in range(2, len(full)):
                self.assertEqual(full[i], full[i - 1] + full[i - 2])


# ---------------------------------------------------------------------------
# RuleViolationGenerator
# ---------------------------------------------------------------------------

class TestRuleViolationGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = RuleViolationGenerator()

    def test_ability_and_task_type(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertEqual(item.ability, "problem_sensitivity")
        self.assertEqual(item.task_type, "rule_violation")

    def test_returns_n_items(self):
        self.assertEqual(len(self.gen.generate(n=5)), 5)

    def test_correct_answer_matches_violated_flag(self):
        for _ in range(50):
            item = self.gen.generate(difficulty=2, n=1)[0]
            expected = "yes" if item.metadata["violated"] else "no"
            self.assertEqual(item.correct_answer, expected)

    def test_correct_answer_is_yes_or_no(self):
        for _ in range(20):
            item = self.gen.generate(n=1)[0]
            self.assertIn(item.correct_answer, ("yes", "no"))

    def test_options_present(self):
        item = self.gen.generate(n=1)[0]
        self.assertIn("yes", item.question["options"])
        self.assertIn("no", item.question["options"])

    def test_rule_is_non_empty_string(self):
        for _ in range(10):
            item = self.gen.generate(n=1)[0]
            self.assertIsInstance(item.question["rule"], str)
            self.assertGreater(len(item.question["rule"]), 0)

    def test_higher_difficulty_adds_distractors(self):
        # Difficulty 1 scenario should be shorter than difficulty 5 (distractors added)
        short_items = [self.gen.generate(difficulty=1, n=1)[0] for _ in range(10)]
        long_items = [self.gen.generate(difficulty=5, n=1)[0] for _ in range(10)]
        avg_short = sum(len(i.question["scenario"]) for i in short_items) / 10
        avg_long = sum(len(i.question["scenario"]) for i in long_items) / 10
        self.assertGreater(avg_long, avg_short)


# ---------------------------------------------------------------------------
# SyllogismGenerator
# ---------------------------------------------------------------------------

class TestSyllogismGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = SyllogismGenerator()

    def test_ability_and_task_type(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertEqual(item.ability, "deductive_reasoning")
        self.assertEqual(item.task_type, "syllogism")

    def test_returns_n_items(self):
        self.assertEqual(len(self.gen.generate(n=7)), 7)

    def test_correct_answer_is_yes_or_no(self):
        for diff in range(1, 6):
            for _ in range(10):
                item = self.gen.generate(difficulty=diff, n=1)[0]
                self.assertIn(item.correct_answer, ("yes", "no"),
                              f"difficulty={diff}, got {item.correct_answer!r}")

    def test_options_always_yes_and_no(self):
        for _ in range(20):
            item = self.gen.generate(n=1)[0]
            self.assertIn("yes", item.question["options"])
            self.assertIn("no", item.question["options"])

    def test_known_templates_correct_answer(self):
        """Spot-check specific known templates for logical correctness."""
        all_items = [self.gen.generate(difficulty=d, n=20) for d in range(1, 6)]
        found = {}
        for items in all_items:
            for item in items:
                form = item.metadata["form"]
                found[form] = item.correct_answer

        # Universal affirmative must always be yes
        if "all_AB_xA→xB" in found:
            self.assertEqual(found["all_AB_xA→xB"], "yes")

        # Converse fallacy must always be no
        if "all_AB_yB↛yA" in found:
            self.assertEqual(found["all_AB_yB↛yA"], "no")

        # Universal negative must always be no
        if "no_AB_xA→¬xB" in found:
            self.assertEqual(found["no_AB_xA→¬xB"], "no")

        # Modus ponens must always be yes
        if "modus_ponens" in found:
            self.assertEqual(found["modus_ponens"], "yes")

        # Affirming the consequent fallacy must be no
        if "affirming_consequent_fallacy" in found:
            self.assertEqual(found["affirming_consequent_fallacy"], "no")

    def test_difficulty_5_draws_from_conditional_pool(self):
        items = self.gen.generate(difficulty=5, n=30)
        forms = {i.metadata["form"] for i in items}
        conditional_forms = {"modus_ponens", "modus_tollens", "affirming_consequent_fallacy"}
        self.assertTrue(forms & conditional_forms,
                        f"Expected at least one conditional form, got: {forms}")

    def test_question_text_is_non_empty(self):
        for _ in range(10):
            item = self.gen.generate(n=1)[0]
            self.assertIsInstance(item.question["text"], str)
            self.assertGreater(len(item.question["text"]), 10)


# ---------------------------------------------------------------------------
# MathReasoningGenerator
# ---------------------------------------------------------------------------

class TestMathReasoningGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = MathReasoningGenerator()

    def test_ability_and_task_type(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertEqual(item.ability, "mathematical_reasoning")
        self.assertEqual(item.task_type, "arithmetic_word_problem")

    def test_returns_n_items(self):
        for n in (1, 3, 5):
            with self.subTest(n=n):
                self.assertEqual(len(self.gen.generate(n=n)), n)

    def test_correct_answer_is_integer(self):
        for diff in range(1, 6):
            for _ in range(10):
                item = self.gen.generate(difficulty=diff, n=1)[0]
                self.assertIsInstance(item.correct_answer, int,
                                      f"difficulty={diff}, got {item.correct_answer!r}")

    def test_question_has_text_key(self):
        for diff in range(1, 6):
            item = self.gen.generate(difficulty=diff, n=1)[0]
            self.assertIn("text", item.question)
            self.assertIsInstance(item.question["text"], str)
            self.assertGreater(len(item.question["text"]), 10)

    def test_score_correct_answer(self):
        for _ in range(20):
            item = self.gen.generate(difficulty=3, n=1)[0]
            self.assertTrue(self.gen.score_response(item, item.correct_answer))

    def test_score_string_correct_answer(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertTrue(self.gen.score_response(item, str(item.correct_answer)))

    def test_score_wrong_answer(self):
        item = self.gen.generate(difficulty=2, n=1)[0]
        self.assertFalse(self.gen.score_response(item, item.correct_answer + 999))

    def test_difficulty_clamping(self):
        lo = self.gen.generate(difficulty=0, n=1)[0]
        hi = self.gen.generate(difficulty=99, n=1)[0]
        self.assertIn(lo.difficulty, range(1, 6))
        self.assertIn(hi.difficulty, range(1, 6))

    def test_metadata_has_tag(self):
        for diff in range(1, 6):
            item = self.gen.generate(difficulty=diff, n=1)[0]
            self.assertIn("tag", item.metadata)
            self.assertIsInstance(item.metadata["tag"], str)


# ---------------------------------------------------------------------------
# WrittenComprehensionGenerator
# ---------------------------------------------------------------------------

class TestWrittenComprehensionGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = WrittenComprehensionGenerator()

    def test_ability_and_task_type(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertEqual(item.ability, "written_comprehension")
        self.assertEqual(item.task_type, "passage_mcq")

    def test_returns_n_items(self):
        for n in (1, 4, 6):
            with self.subTest(n=n):
                self.assertEqual(len(self.gen.generate(n=n)), n)

    def test_question_has_required_keys(self):
        for diff in range(1, 6):
            item = self.gen.generate(difficulty=diff, n=1)[0]
            for key in ("passage", "question", "options"):
                self.assertIn(key, item.question,
                              f"Missing key '{key}' at difficulty {diff}")

    def test_correct_answer_in_options(self):
        for diff in range(1, 6):
            for _ in range(10):
                item = self.gen.generate(difficulty=diff, n=1)[0]
                self.assertIn(
                    item.correct_answer, item.question["options"],
                    f"correct_answer not in options at difficulty {diff}"
                )

    def test_options_are_shuffled_across_runs(self):
        """Options should not always be in the same order (probabilistic)."""
        first_options = [
            tuple(self.gen.generate(difficulty=1, n=1)[0].question["options"])
            for _ in range(20)
        ]
        self.assertGreater(len(set(first_options)), 1,
                           "Options appear to never be shuffled")

    def test_score_correct_answer(self):
        for _ in range(20):
            item = self.gen.generate(difficulty=2, n=1)[0]
            self.assertTrue(self.gen.score_response(item, item.correct_answer))

    def test_score_wrong_answer(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        wrong = [o for o in item.question["options"] if o != item.correct_answer][0]
        self.assertFalse(self.gen.score_response(item, wrong))

    def test_difficulty_clamping(self):
        lo = self.gen.generate(difficulty=0, n=1)[0]
        hi = self.gen.generate(difficulty=99, n=1)[0]
        self.assertIn(lo.difficulty, range(1, 6))
        self.assertIn(hi.difficulty, range(1, 6))

    def test_passage_is_non_empty(self):
        for diff in range(1, 6):
            item = self.gen.generate(difficulty=diff, n=1)[0]
            self.assertGreater(len(item.question["passage"]), 20,
                               f"Passage too short at difficulty {diff}")


# ---------------------------------------------------------------------------
# TimeShareGenerator
# ---------------------------------------------------------------------------

class TestTimeShareGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = TimeShareGenerator()

    def test_ability_and_task_type(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertEqual(item.ability, "time_sharing")
        self.assertEqual(item.task_type, "dual_task")

    def test_returns_n_items(self):
        for n in (1, 3, 5):
            with self.subTest(n=n):
                self.assertEqual(len(self.gen.generate(n=n)), n)

    def test_question_has_required_keys(self):
        for diff in range(1, 6):
            item = self.gen.generate(difficulty=diff, n=1)[0]
            for key in ("instruction", "task_a", "task_b"):
                self.assertIn(key, item.question,
                              f"Missing key '{key}' at difficulty {diff}")
            for sub in ("task_a", "task_b"):
                for sub_key in ("label", "text"):
                    self.assertIn(sub_key, item.question[sub])

    def test_correct_answer_has_a_and_b(self):
        for diff in range(1, 6):
            item = self.gen.generate(difficulty=diff, n=1)[0]
            self.assertIn("a", item.correct_answer,
                          f"Missing 'a' key at difficulty {diff}")
            self.assertIn("b", item.correct_answer,
                          f"Missing 'b' key at difficulty {diff}")

    def test_task_a_answer_is_numeric(self):
        for diff in range(1, 6):
            for _ in range(10):
                item = self.gen.generate(difficulty=diff, n=1)[0]
                ans_a = item.correct_answer["a"]
                self.assertIsInstance(ans_a, int,
                                      f"Task A answer should be int, got {type(ans_a)} at d={diff}")

    def test_task_b_answer_is_string(self):
        for diff in range(1, 6):
            for _ in range(10):
                item = self.gen.generate(difficulty=diff, n=1)[0]
                ans_b = item.correct_answer["b"]
                self.assertIsInstance(ans_b, str,
                                      f"Task B answer should be str, got {type(ans_b)} at d={diff}")

    def test_score_both_correct(self):
        for _ in range(20):
            item = self.gen.generate(difficulty=1, n=1)[0]
            correct = item.correct_answer
            self.assertTrue(self.gen.score_response(item, correct))

    def test_score_one_wrong_returns_false(self):
        for _ in range(20):
            item = self.gen.generate(difficulty=1, n=1)[0]
            bad_answer = {"a": item.correct_answer["a"] + 999,
                          "b": item.correct_answer["b"]}
            self.assertFalse(self.gen.score_response(item, bad_answer))

    def test_score_partial_both_correct_is_1(self):
        for _ in range(10):
            item = self.gen.generate(difficulty=2, n=1)[0]
            self.assertEqual(self.gen.score_partial(item, item.correct_answer), 1.0)

    def test_score_partial_one_correct_is_half(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        half_answer = {"a": item.correct_answer["a"] + 1,
                       "b": item.correct_answer["b"]}
        self.assertEqual(self.gen.score_partial(item, half_answer), 0.5)

    def test_score_non_dict_returns_false(self):
        item = self.gen.generate(difficulty=1, n=1)[0]
        self.assertFalse(self.gen.score_response(item, "wrong"))
        self.assertEqual(self.gen.score_partial(item, None), 0.0)

    def test_difficulty_clamping(self):
        lo = self.gen.generate(difficulty=0, n=1)[0]
        hi = self.gen.generate(difficulty=99, n=1)[0]
        self.assertIn(lo.difficulty, range(1, 6))
        self.assertIn(hi.difficulty, range(1, 6))


if __name__ == "__main__":
    unittest.main()
