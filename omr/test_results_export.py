"""Tests for results export (Milestone 18)."""

import csv
import io
import tempfile
import unittest
from pathlib import Path

from omr.csv_handler import (
    export_results_csv,
    generate_results_filename,
    RESULTS_HEADERS,
)
from omr.database import AssessFlowDatabase
from omr.grade_answers import load_answer_key


# ============================================================
# CSV handler tests
# ============================================================


class ResultsCSVHandlerTests(unittest.TestCase):
    """Tests for the results CSV export functions."""

    def test_headers_are_correct_and_ordered(self):
        """CSV headers match the required column order."""
        self.assertEqual(RESULTS_HEADERS, [
            "classroom", "student_id", "student_name", "assessment",
            "question_count", "score", "percentage", "wrong", "blank",
            "multiple", "date",
        ])

    def test_export_results_csv_has_headers(self):
        """Exported CSV starts with the correct header row."""
        csv_bytes = export_results_csv([])
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        self.assertEqual(header, RESULTS_HEADERS)

    def test_export_results_csv_empty_rows(self):
        """Empty rows list produces headers only."""
        csv_bytes = export_results_csv([])
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        self.assertEqual(len(rows), 1)  # header only

    def test_export_results_csv_single_row(self):
        """A single row is written correctly."""
        row = {
            "classroom": "Grade 7A",
            "student_id": "123456",
            "student_name": "Alice",
            "assessment": "Midterm",
            "question_count": 50,
            "score": 42,
            "percentage": 84.0,
            "wrong": 8,
            "blank": 5,
            "multiple": 3,
            "date": "2026-09-10",
        }
        csv_bytes = export_results_csv([row])
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["classroom"], "Grade 7A")
        self.assertEqual(rows[0]["student_id"], "123456")
        self.assertEqual(rows[0]["student_name"], "Alice")
        self.assertEqual(rows[0]["assessment"], "Midterm")
        self.assertEqual(rows[0]["question_count"], "50")
        self.assertEqual(rows[0]["score"], "42")
        self.assertEqual(rows[0]["percentage"], "84.0")
        self.assertEqual(rows[0]["wrong"], "8")
        self.assertEqual(rows[0]["blank"], "5")
        self.assertEqual(rows[0]["multiple"], "3")
        self.assertEqual(rows[0]["date"], "2026-09-10")

    def test_student_id_stays_text(self):
        """Student ID with leading zeros is preserved as text."""
        row = {
            "classroom": "Grade 7A",
            "student_id": "012345",
            "student_name": "Alice",
            "assessment": "Midterm",
            "question_count": 50,
            "score": 42,
            "percentage": 84.0,
            "wrong": 8,
            "blank": 5,
            "multiple": 3,
            "date": "2026-09-10",
        }
        csv_bytes = export_results_csv([row])
        text = csv_bytes.decode("utf-8-sig")
        self.assertIn("012345", text)
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        self.assertEqual(rows[0]["student_id"], "012345")

    def test_utf8_bom_present(self):
        """Exported CSV starts with UTF-8 BOM."""
        csv_bytes = export_results_csv([])
        self.assertTrue(csv_bytes.startswith(b"\xef\xbb\xbf"))

    def test_csv_parseable(self):
        """Exported CSV can be parsed by Python csv module."""
        rows_data = [
            {
                "classroom": "Grade 7A",
                "student_id": "123456",
                "student_name": "Alice",
                "assessment": "Midterm",
                "question_count": 50,
                "score": 42,
                "percentage": 84.0,
                "wrong": 8,
                "blank": 5,
                "multiple": 3,
                "date": "2026-09-10",
            },
            {
                "classroom": "Grade 7A",
                "student_id": "234567",
                "student_name": "Bob",
                "assessment": "Midterm",
                "question_count": 50,
                "score": 35,
                "percentage": 70.0,
                "wrong": 15,
                "blank": 10,
                "multiple": 5,
                "date": "2026-09-10",
            },
        ]
        csv_bytes = export_results_csv(rows_data)
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        parsed = list(reader)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["student_name"], "Alice")
        self.assertEqual(parsed[1]["student_name"], "Bob")

    def test_date_format_is_yyyy_mm_dd(self):
        """Date values are in YYYY-MM-DD format."""
        row = {
            "classroom": "Grade 7A",
            "student_id": "123456",
            "student_name": "Alice",
            "assessment": "Midterm",
            "question_count": 50,
            "score": 42,
            "percentage": 84.0,
            "wrong": 8,
            "blank": 5,
            "multiple": 3,
            "date": "2026-09-10",
        }
        csv_bytes = export_results_csv([row])
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        self.assertRegex(rows[0]["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_percentage_one_decimal(self):
        """Percentage has one decimal place."""
        row = {
            "classroom": "Grade 7A",
            "student_id": "123456",
            "student_name": "Alice",
            "assessment": "Midterm",
            "question_count": 50,
            "score": 42,
            "percentage": 84.0,
            "wrong": 8,
            "blank": 5,
            "multiple": 3,
            "date": "2026-09-10",
        }
        csv_bytes = export_results_csv([row])
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        self.assertEqual(rows[0]["percentage"], "84.0")


class ResultsFilenameTests(unittest.TestCase):
    """Tests for the results filename generator."""

    def test_basic_filename(self):
        """Basic filename with classroom and assessment."""
        name = generate_results_filename("Grade 7A", "Midterm")
        self.assertEqual(name, "AssessFlow_Grade 7A_Midterm_Results.csv")

    def test_single_part(self):
        """Filename with just one part."""
        name = generate_results_filename("Grade 7A")
        self.assertEqual(name, "AssessFlow_Grade 7A_Results.csv")

    def test_unsafe_characters_replaced(self):
        """Unsafe filesystem characters are replaced."""
        name = generate_results_filename('Grade: 7/A', "Mid?term")
        self.assertNotIn(":", name)
        self.assertNotIn("/", name)
        self.assertNotIn("?", name)
        self.assertTrue(name.endswith(".csv"))

    def test_empty_parts(self):
        """Empty parts are skipped gracefully."""
        name = generate_results_filename("", "Midterm", "")
        self.assertEqual(name, "AssessFlow_Midterm_Results.csv")

    def test_all_empty(self):
        """All-empty parts produce a default name."""
        name = generate_results_filename()
        self.assertEqual(name, "AssessFlow_Results.csv")

    def test_leading_trailing_dots_stripped(self):
        """Leading/trailing dots and spaces are stripped from parts."""
        name = generate_results_filename("  Grade 7A  ", " Midterm ")
        self.assertEqual(name, "AssessFlow_Grade 7A_Midterm_Results.csv")


# ============================================================
# Database export query tests
# ============================================================


class ResultsExportQueryTests(unittest.TestCase):
    """Tests for the database export query methods."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = AssessFlowDatabase(
            Path(self.temporary_directory.name) / "test.sqlite3"
        )
        self.database.initialize()
        self.classroom_id = self.database.create_classroom("Grade 7A")
        self.student1_id = self.database.create_student(
            self.classroom_id, "Alice", "123456"
        )
        self.student2_id = self.database.create_student(
            self.classroom_id, "Bob", "234567"
        )
        self.assessment_id = self.database.create_assessment(
            self.classroom_id, "Midterm", load_answer_key()
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _save_result(self, student_id, score=42, percentage=84.0):
        """Helper to save a grading result for a student."""
        answers = {i: "A" for i in range(1, 51)}
        questions = [
            {
                "question_number": i,
                "student_answer": "A",
                "correct_answer": "A",
                "result": "CORRECT",
            }
            for i in range(1, score + 1)
        ] + [
            {
                "question_number": i,
                "student_answer": "B",
                "correct_answer": "A",
                "result": "WRONG",
            }
            for i in range(score + 1, 51)
        ]
        result = {
            "source_file": "test.png",
            "total_questions": 50,
            "score": score,
            "percentage": percentage,
            "correct": score,
            "wrong": 50 - score,
            "blank": 0,
            "multiple": 0,
            "questions": questions,
        }
        return self.database.save_grading_result(
            self.assessment_id, result, student_id
        )

    def test_assessment_export_returns_correct_rows(self):
        """Assessment export returns one row per student attempt."""
        self._save_result(self.student1_id, score=42)
        self._save_result(self.student2_id, score=35)
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertEqual(len(rows), 2)

    def test_assessment_export_excludes_unknown_students(self):
        """Attempts with student_id=NULL are excluded."""
        self._save_result(self.student1_id, score=42)
        # Save an attempt with no student_id
        answers = {i: "A" for i in range(1, 51)}
        questions = [
            {"question_number": i, "student_answer": "A", "correct_answer": "A", "result": "CORRECT"}
            for i in range(1, 43)
        ] + [
            {"question_number": i, "student_answer": "B", "correct_answer": "A", "result": "WRONG"}
            for i in range(43, 51)
        ]
        result = {
            "source_file": "test.png",
            "total_questions": 50,
            "score": 42,
            "percentage": 84.0,
            "correct": 42,
            "wrong": 8,
            "blank": 0,
            "multiple": 0,
            "questions": questions,
        }
        self.database.save_grading_result(self.assessment_id, result, None)
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["student_id"], "123456")

    def test_assessment_export_excludes_other_assessments(self):
        """Only attempts for the specified assessment are returned."""
        self._save_result(self.student1_id, score=42)
        other_assessment = self.database.create_assessment(
            self.classroom_id, "Final", load_answer_key()
        )
        questions = [
            {"question_number": i, "student_answer": "A", "correct_answer": "A", "result": "CORRECT"}
            for i in range(1, 51)
        ]
        result = {
            "source_file": "test.png",
            "total_questions": 50,
            "score": 50,
            "percentage": 100.0,
            "correct": 50,
            "wrong": 0,
            "blank": 0,
            "multiple": 0,
            "questions": questions,
        }
        self.database.save_grading_result(other_assessment, result, self.student1_id)
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["assessment"], "Midterm")

    def test_classroom_export_returns_all_classroom_results(self):
        """Classroom export returns results for all assessments."""
        self._save_result(self.student1_id, score=42)
        other_assessment = self.database.create_assessment(
            self.classroom_id, "Final", load_answer_key()
        )
        questions = [
            {"question_number": i, "student_answer": "A", "correct_answer": "A", "result": "CORRECT"}
            for i in range(1, 51)
        ]
        result = {
            "source_file": "test.png",
            "total_questions": 50,
            "score": 50,
            "percentage": 100.0,
            "correct": 50,
            "wrong": 0,
            "blank": 0,
            "multiple": 0,
            "questions": questions,
        }
        self.database.save_grading_result(other_assessment, result, self.student2_id)
        rows = self.database.get_classroom_export_rows(self.classroom_id)
        self.assertEqual(len(rows), 2)

    def test_classroom_export_excludes_other_classrooms(self):
        """Results from other classrooms are excluded."""
        self._save_result(self.student1_id, score=42)
        other_classroom = self.database.create_classroom("Grade 7B")
        other_student = self.database.create_student(
            other_classroom, "Charlie", "345678"
        )
        other_assessment = self.database.create_assessment(
            other_classroom, "Other Test", load_answer_key()
        )
        questions = [
            {"question_number": i, "student_answer": "A", "correct_answer": "A", "result": "CORRECT"}
            for i in range(1, 51)
        ]
        result = {
            "source_file": "test.png",
            "total_questions": 50,
            "score": 50,
            "percentage": 100.0,
            "correct": 50,
            "wrong": 0,
            "blank": 0,
            "multiple": 0,
            "questions": questions,
        }
        self.database.save_grading_result(other_assessment, result, other_student)
        rows = self.database.get_classroom_export_rows(self.classroom_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["classroom"], "Grade 7A")

    def test_student_export_returns_only_that_student(self):
        """Student export returns only the specified student's attempts."""
        self._save_result(self.student1_id, score=42)
        self._save_result(self.student2_id, score=35)
        rows = self.database.get_student_export_rows(
            self.classroom_id, self.student1_id
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["student_id"], "123456")

    def test_student_export_excludes_other_students(self):
        """Other students' attempts are not included."""
        self._save_result(self.student1_id, score=42)
        self._save_result(self.student1_id, score=35)
        self._save_result(self.student2_id, score=50)
        rows = self.database.get_student_export_rows(
            self.classroom_id, self.student1_id
        )
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["student_id"], "123456")

    def test_empty_results_produce_empty_list(self):
        """No graded attempts returns an empty list."""
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertEqual(rows, [])

    def test_student_id_leading_zeros_preserved(self):
        """Student ID 012345 remains text in export rows."""
        student = self.database.create_student(
            self.classroom_id, "Fhebe", "012345"
        )
        questions = [
            {"question_number": i, "student_answer": "A", "correct_answer": "A", "result": "CORRECT"}
            for i in range(1, 51)
        ]
        result = {
            "source_file": "test.png",
            "total_questions": 50,
            "score": 50,
            "percentage": 100.0,
            "correct": 50,
            "wrong": 0,
            "blank": 0,
            "multiple": 0,
            "questions": questions,
        }
        self.database.save_grading_result(self.assessment_id, result, student)
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertEqual(rows[0]["student_id"], "012345")

    def test_percentage_is_correct(self):
        """Percentage value is a float with correct precision."""
        self._save_result(self.student1_id, score=42, percentage=84.0)
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertIsInstance(rows[0]["percentage"], float)
        self.assertAlmostEqual(rows[0]["percentage"], 84.0, places=1)

    def test_date_format_in_export_rows(self):
        """Date in export rows is YYYY-MM-DD format."""
        self._save_result(self.student1_id, score=42)
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertRegex(rows[0]["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_classroom_name_in_export_rows(self):
        """Export row contains the human-readable classroom name."""
        self._save_result(self.student1_id, score=42)
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertEqual(rows[0]["classroom"], "Grade 7A")

    def test_assessment_name_in_export_rows(self):
        """Export row contains the human-readable assessment name."""
        self._save_result(self.student1_id, score=42)
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertEqual(rows[0]["assessment"], "Midterm")

    def test_score_represents_correct_count(self):
        """Score equals the number of correct answers."""
        self._save_result(self.student1_id, score=42)
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertEqual(rows[0]["score"], 42)

    def test_wrong_includes_blank_and_multiple(self):
        """Wrong count includes blank and multiple per existing convention."""
        questions = [
            {"question_number": i, "student_answer": "A", "correct_answer": "A", "result": "CORRECT"}
            for i in range(1, 46)
        ] + [
            {"question_number": 46, "student_answer": "B", "correct_answer": "A", "result": "WRONG"},
            {"question_number": 47, "student_answer": "BLANK", "correct_answer": "A", "result": "BLANK"},
            {"question_number": 48, "student_answer": "MULTIPLE", "correct_answer": "A", "result": "MULTIPLE"},
            {"question_number": 49, "student_answer": "C", "correct_answer": "A", "result": "WRONG"},
            {"question_number": 50, "student_answer": "D", "correct_answer": "A", "result": "WRONG"},
        ]
        result = {
            "source_file": "test.png",
            "total_questions": 50,
            "score": 45,
            "percentage": 90.0,
            "correct": 45,
            "wrong": 5,
            "blank": 1,
            "multiple": 1,
            "questions": questions,
        }
        self.database.save_grading_result(self.assessment_id, result, self.student1_id)
        rows = self.database.get_assessment_export_rows(self.assessment_id)
        self.assertEqual(rows[0]["wrong"], 5)
        self.assertEqual(rows[0]["blank"], 1)
        self.assertEqual(rows[0]["multiple"], 1)


# ============================================================
# Route tests (Flask test client)
# ============================================================


class ResultsExportRouteTests(unittest.TestCase):
    """Tests for the export routes."""

    def setUp(self):
        from web import create_app
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "DATABASE": Path(self.temporary_directory.name) / "test.sqlite3",
        })
        self.client = self.app.test_client()

        # Set up test data
        with self.app.db._connect() as conn:
            conn.execute(
                "INSERT INTO classrooms (name, created_at) VALUES (?, ?)",
                ("Grade 7A", "2026-01-01 00:00:00"),
            )
            conn.execute(
                "INSERT INTO students (classroom_id, name, student_identifier, created_at) VALUES (?, ?, ?, ?)",
                (1, "Alice", "123456", "2026-01-01 00:00:00"),
            )
            conn.execute(
                "INSERT INTO assessments (classroom_id, name, question_count, created_at) VALUES (?, ?, ?, ?)",
                (1, "Midterm", 50, "2026-01-01 00:00:00"),
            )
            conn.execute(
                "INSERT INTO grading_attempts (assessment_id, student_id, score, percentage, correct_count, wrong_count, blank_count, multiple_count, graded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (1, 1, 42, 84.0, 42, 8, 5, 3, "2026-09-10T12:00:00"),
            )
            conn.commit()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_assessment_export_returns_200(self):
        """Assessment export route returns 200."""
        resp = self.client.get("/assessments/1/results/export")
        self.assertEqual(resp.status_code, 200)

    def test_assessment_export_content_type(self):
        """Assessment export has CSV content type."""
        resp = self.client.get("/assessments/1/results/export")
        self.assertIn("text/csv", resp.content_type)

    def test_assessment_export_has_headers(self):
        """Assessment export CSV contains correct headers."""
        resp = self.client.get("/assessments/1/results/export")
        text = resp.data.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        self.assertEqual(header, RESULTS_HEADERS)

    def test_assessment_export_has_data(self):
        """Assessment export CSV contains the graded attempt."""
        resp = self.client.get("/assessments/1/results/export")
        text = resp.data.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["student_id"], "123456")
        self.assertEqual(rows[0]["student_name"], "Alice")
        self.assertEqual(rows[0]["assessment"], "Midterm")
        self.assertEqual(rows[0]["classroom"], "Grade 7A")

    def test_assessment_export_nonexistent(self):
        """Nonexistent assessment redirects to classroom list."""
        resp = self.client.get("/assessments/999/results/export")
        self.assertEqual(resp.status_code, 302)

    def test_classroom_export_returns_200(self):
        """Classroom export route returns 200."""
        resp = self.client.get("/classrooms/1/results/export")
        self.assertEqual(resp.status_code, 200)

    def test_classroom_export_content_type(self):
        """Classroom export has CSV content type."""
        resp = self.client.get("/classrooms/1/results/export")
        self.assertIn("text/csv", resp.content_type)

    def test_classroom_export_has_data(self):
        """Classroom export CSV contains the graded attempt."""
        resp = self.client.get("/classrooms/1/results/export")
        text = resp.data.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["classroom"], "Grade 7A")

    def test_classroom_export_nonexistent(self):
        """Nonexistent classroom redirects to classroom list."""
        resp = self.client.get("/classrooms/999/results/export")
        self.assertEqual(resp.status_code, 302)

    def test_student_export_returns_200(self):
        """Student export route returns 200."""
        resp = self.client.get("/classrooms/1/students/1/export")
        self.assertEqual(resp.status_code, 200)

    def test_student_export_content_type(self):
        """Student export has CSV content type."""
        resp = self.client.get("/classrooms/1/students/1/export")
        self.assertIn("text/csv", resp.content_type)

    def test_student_export_has_data(self):
        """Student export CSV contains only that student's results."""
        resp = self.client.get("/classrooms/1/students/1/export")
        text = resp.data.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["student_id"], "123456")
        self.assertEqual(rows[0]["student_name"], "Alice")

    def test_student_export_nonexistent_classroom(self):
        """Nonexistent classroom redirects."""
        resp = self.client.get("/classrooms/999/students/1/export")
        self.assertEqual(resp.status_code, 302)

    def test_student_export_nonexistent_student(self):
        """Nonexistent student redirects."""
        resp = self.client.get("/classrooms/1/students/999/export")
        self.assertEqual(resp.status_code, 302)


if __name__ == "__main__":
    unittest.main()
