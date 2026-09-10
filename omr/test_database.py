from pathlib import Path
import tempfile
import unittest

from omr.database import AssessFlowDatabase
from omr.grade_answers import create_grading_result, load_answer_key
from omr.layout import QUESTIONS


class AssessFlowDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = AssessFlowDatabase(Path(self.temporary_directory.name) / "assessflow.sqlite3")
        self.database.initialize()
        self.classroom_id = self.database.create_classroom("Grade 7A")
        self.student_id = self.database.create_student(self.classroom_id, "Ada Lovelace", "S-001")
        self.assessment_id = self.database.create_assessment(
            self.classroom_id, "Science Quiz", load_answer_key()
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_saves_and_reads_all_fifty_question_results(self):
        answers = {number: "A" for number in range(1, QUESTIONS + 1)}
        result = create_grading_result(answers, load_answer_key(), source_file="samples/generated.png")
        attempt_id = self.database.save_grading_result(self.assessment_id, result, self.student_id)
        saved = self.database.get_grading_result(attempt_id)

        self.assertEqual(saved["student_id"], self.student_id)
        self.assertEqual(saved["total_questions"], 50)
        self.assertEqual(len(saved["questions"]), 50)
        self.assertEqual(saved["questions"][0]["question_number"], 1)
        self.assertEqual(saved["questions"][-1]["question_number"], 50)

    def test_rejects_a_student_from_another_classroom(self):
        other_classroom = self.database.create_classroom("Grade 7B")
        other_student = self.database.create_student(other_classroom, "Grace Hopper")
        result = create_grading_result({}, load_answer_key())

        with self.assertRaisesRegex(ValueError, "assessment classroom"):
            self.database.save_grading_result(self.assessment_id, result, other_student)

    def test_find_student_by_identifier_returns_correct_student(self):
        """find_student_by_identifier returns the correct student in the classroom."""
        student = self.database.find_student_by_identifier(self.classroom_id, "S-001")
        self.assertIsNotNone(student)
        self.assertEqual(student["name"], "Ada Lovelace")
        self.assertEqual(student["student_identifier"], "S-001")
        self.assertEqual(student["classroom_id"], self.classroom_id)

    def test_find_student_by_identifier_returns_none_for_unknown(self):
        """find_student_by_identifier returns None for unknown identifier."""
        result = self.database.find_student_by_identifier(self.classroom_id, "999999")
        self.assertIsNone(result)

    def test_find_student_by_identifier_is_classroom_scoped(self):
        """Same student_identifier in different classroom returns different student."""
        other_classroom = self.database.create_classroom("Grade 7B")
        other_student = self.database.create_student(
            other_classroom, "Bob Smith", "S-001"
        )

        found_in_a = self.database.find_student_by_identifier(self.classroom_id, "S-001")
        found_in_b = self.database.find_student_by_identifier(other_classroom, "S-001")

        self.assertIsNotNone(found_in_a)
        self.assertIsNotNone(found_in_b)
        self.assertEqual(found_in_a["name"], "Ada Lovelace")
        self.assertEqual(found_in_b["name"], "Bob Smith")


if __name__ == "__main__":
    unittest.main()
