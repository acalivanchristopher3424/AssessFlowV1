import json
import unittest

from omr.grade_answers import grade_answers, create_grading_result


class VariableQuestionCountTests(unittest.TestCase):
    def test_grade_answers_20_questions_all_correct(self):
        """All 20 students answers match → 20/20."""
        student_answers = {i: "A" for i in range(1, 21)}
        answer_key = {i: "A" for i in range(1, 51)}

        (
            score, correct, wrong, blank, multiple, results,
        ) = grade_answers(student_answers, answer_key, question_count=20)

        self.assertEqual(score, 20)
        self.assertEqual(correct, 20)
        self.assertEqual(wrong, 0)
        self.assertEqual(blank, 0)
        self.assertEqual(multiple, 0)
        self.assertEqual(len(results), 20)
        self.assertIn(20, results)
        self.assertNotIn(21, results)

    def test_grade_answers_20_questions_with_wrongs(self):
        """Some wrong, some correct within 20-question window."""
        student_answers = {1: "A", 2: "B", 3: "BLANK", 4: "MULTIPLE"}
        answer_key = {i: "A" for i in range(1, 51)}
        answer_key.update({1: "A", 2: "A", 3: "A", 4: "A"})

        (
            score, correct, wrong, blank, multiple, results,
        ) = grade_answers(student_answers, answer_key, question_count=20)

        self.assertEqual(correct, 1)
        self.assertEqual(wrong, 19)
        self.assertEqual(blank, 1)
        self.assertEqual(multiple, 1)
        self.assertEqual(len(results), 20)

    def test_create_grading_result_20_questions(self):
        """total_questions=20, percentage uses 20 as denominator."""
        student_answers = {1: "A", 2: "B", 3: "C"}
        answer_key = {i: "A" for i in range(1, 51)}
        answer_key.update({1: "A", 2: "B", 3: "C"})

        result = create_grading_result(
            student_answers, answer_key,
            source_file="scan.png", question_count=20,
        )

        self.assertEqual(result["total_questions"], 20)
        self.assertEqual(result["score"], 3)
        self.assertEqual(result["correct"], 3)
        self.assertEqual(result["wrong"], 17)
        self.assertEqual(len(result["questions"]), 20)
        self.assertAlmostEqual(result["percentage"], 15.0)
        json.dumps(result)

    def test_percentage_accuracy_20_questions(self):
        """15 correct out of 20 = 75%, not 30%."""
        answer_key = {i: "A" for i in range(1, 51)}
        student_answers = {i: "A" for i in range(1, 16)}
        for q in range(16, 21):
            student_answers[q] = "B"

        result = create_grading_result(
            student_answers, answer_key, question_count=20,
        )

        self.assertEqual(result["total_questions"], 20)
        self.assertEqual(result["score"], 15)
        self.assertEqual(result["percentage"], 75.0)

    def test_50_question_assessment_unchanged(self):
        """Existing 50-question behavior preserved when question_count omitted."""
        student_answers = {1: "A", 2: "BLANK", 3: "MULTIPLE", 4: "A"}
        answer_key = {i: "A" for i in range(1, 51)}
        answer_key.update({1: "A", 2: "B", 3: "C", 4: "D"})

        result = create_grading_result(
            student_answers, answer_key, source_file="scan.png",
        )

        self.assertEqual(result["total_questions"], 50)
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["wrong"], 49)
        self.assertEqual(len(result["questions"]), 50)

    def test_50_question_explicit_matches_default(self):
        """Passing question_count=50 behaves identically to default."""
        student_answers = {1: "A", 2: "BLANK", 3: "MULTIPLE", 4: "A"}
        answer_key = {i: "A" for i in range(1, 51)}
        answer_key.update({1: "A", 2: "B", 3: "C", 4: "D"})

        result = create_grading_result(
            student_answers, answer_key,
            source_file="scan.png", question_count=50,
        )

        self.assertEqual(result["total_questions"], 50)
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["wrong"], 49)
        self.assertEqual(len(result["questions"]), 50)

    def test_questions_beyond_count_excluded(self):
        """Q21-Q50 ignored in a 20-question assessment."""
        student_answers = {i: "A" for i in range(1, 51)}
        answer_key = {i: "B" for i in range(1, 51)}

        result = create_grading_result(
            student_answers, answer_key, question_count=20,
        )

        self.assertEqual(result["total_questions"], 20)
        self.assertEqual(result["wrong"], 20)
        self.assertEqual(len(result["questions"]), 20)
        question_numbers = [q["question_number"] for q in result["questions"]]
        self.assertEqual(question_numbers, list(range(1, 21)))

    def test_20_questions_all_correct_100_percent(self):
        """20 correct out of 20 = 100%."""
        student_answers = {i: "A" for i in range(1, 21)}
        answer_key = {i: "A" for i in range(1, 51)}

        result = create_grading_result(
            student_answers, answer_key, question_count=20,
        )

        self.assertEqual(result["total_questions"], 20)
        self.assertEqual(result["score"], 20)
        self.assertEqual(result["percentage"], 100.0)
        self.assertEqual(result["wrong"], 0)

    def test_10_questions_grades_only_first_ten(self):
        """10-question assessment ignores Q11-Q50."""
        student_answers = {i: "A" for i in range(1, 11)}
        answer_key = {i: "B" for i in range(1, 51)}

        result = create_grading_result(
            student_answers, answer_key, question_count=10,
        )

        self.assertEqual(result["total_questions"], 10)
        self.assertEqual(len(result["questions"]), 10)
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["wrong"], 10)

    def test_grade_answers_returns_only_count_results(self):
        """grade_answers dict contains exactly question_count entries."""
        student_answers = {i: "A" for i in range(1, 21)}
        answer_key = {i: "A" for i in range(1, 51)}

        _, _, _, _, _, results = grade_answers(
            student_answers, answer_key, question_count=15,
        )

        self.assertEqual(len(results), 15)
        self.assertIn(15, results)
        self.assertNotIn(16, results)


if __name__ == "__main__":
    unittest.main()
