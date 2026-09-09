from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest

from omr.database import AssessFlowDatabase
from omr.grade_answers import grade_scan, load_answer_key


class AssessFlowDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = AssessFlowDatabase(
            Path(self.temporary_directory.name) / "assessflow.sqlite3"
        )
        self.database.initialize()
        self.classroom_id = self.database.create_classroom("Grade 7A")
        self.student_id = self.database.create_student(
            self.classroom_id,
            "Ada Lovelace",
            "S-001",
        )
        self.assessment_id = self.database.create_assessment(
            self.classroom_id,
            "Science Quiz",
            load_answer_key(),
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_saves_and_reads_a_real_sample_grading_result(self):
        sample_scan = Path(__file__).resolve().parent.parent / "samples" / "my_scan.jpeg"

        with redirect_stdout(None):
            result = grade_scan(sample_scan)

        attempt_id = self.database.save_grading_result(
            self.assessment_id,
            result,
            student_id=self.student_id,
        )
        saved = self.database.get_grading_result(attempt_id)

        self.assertEqual(saved["student_id"], self.student_id)
        self.assertEqual(saved["score"], 9)
        self.assertEqual(saved["percentage"], 45.0)
        self.assertEqual(saved["source_file"], str(sample_scan))
        self.assertEqual(len(saved["questions"]), 20)
        self.assertEqual(saved["questions"][0], {
            "question_number": 1,
            "student_answer": "A",
            "correct_answer": "A",
            "result": "CORRECT",
        })

    def test_rejects_a_student_from_another_classroom(self):
        other_classroom = self.database.create_classroom("Grade 7B")
        other_student = self.database.create_student(other_classroom, "Grace Hopper")
        result = {
            "source_file": None,
            "total_questions": 20,
            "score": 0,
            "percentage": 0.0,
            "correct": 0,
            "wrong": 20,
            "blank": 0,
            "multiple": 0,
            "questions": [
                {
                    "question_number": number,
                    "student_answer": "A",
                    "correct_answer": "B",
                    "result": "WRONG",
                }
                for number in range(1, 21)
            ],
        }

        with self.assertRaisesRegex(ValueError, "assessment classroom"):
            self.database.save_grading_result(
                self.assessment_id,
                result,
                student_id=other_student,
            )


if __name__ == "__main__":
    unittest.main()
