import cv2
import tempfile
import unittest
from pathlib import Path

from omr.bulk_processor import bulk_process, bulk_process_with_context, process_scan
from omr.database import AssessFlowDatabase
from omr.detect_scan import align_scan, detect_question_answer, load_image
from omr.generate_sheet import generate_answer_sheet
from omr.grade_answers import create_grading_result, load_answer_key
from omr.layout import get_student_id_bubble_position


class TestBulkProcessorStatusClassification(unittest.TestCase):
    def test_classify_blank(self):
        """All BLANK answers -> 'blank' status."""
        answers = {q: "BLANK" for q in range(1, 51)}
        status = self._classify(answers)
        self.assertEqual(status, "blank")

    def test_classify_success(self):
        """All correct answers -> 'success' status."""
        answers = {q: "A" for q in range(1, 51)}
        status = self._classify(answers)
        self.assertEqual(status, "success")

    def test_classify_success_with_blanks(self):
        """Some BLANK answers among 50 -> 'success_with_blanks'."""
        answers = {q: "A" if q != 50 else "BLANK" for q in range(1, 51)}
        status = self._classify(answers)
        self.assertEqual(status, "success_with_blanks")

    def test_classify_multiple_marks(self):
        """At least one MULTIPLE -> 'multiple-marks' status."""
        answers = {q: "MULTIPLE" if q == 1 else "A" for q in range(1, 51)}
        status = self._classify(answers)
        self.assertEqual(status, "multiple-marks")

    def test_classify_failed_empty(self):
        """Empty answers dict -> 'failed' status."""
        status = self._classify({})
        self.assertEqual(status, "failed")

    def _classify(self, answers):
        from omr.bulk_processor import classify_answer_count
        return classify_answer_count(answers)


class TestProcessScan(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.sheet_path = Path(self.td.name) / "sheet.png"
        generate_answer_sheet(self.sheet_path)

    def tearDown(self):
        self.td.cleanup()

    def test_process_blank_sheet(self):
        """Blank sheet returns 'blank' status."""
        result = process_scan(self.sheet_path)
        self.assertEqual(result["status"], "blank")
        self.assertIsNone(result["score_info"])

    def test_process_returns_structure(self):
        """process_scan returns dict with expected keys."""
        result = process_scan(self.sheet_path)
        self.assertIn("input_file", result)
        self.assertIn("status", result)
        self.assertIn("answers", result)
        self.assertIn("score_info", result)
        self.assertIn("source_file", result)

    def test_process_with_marks(self):
        """Sheet with some marks detected and classified."""
        image = cv2.imread(str(self.sheet_path))
        # Mark question 1 as A
        x, y = 245, 1230  # Q1, choice A
        cv2.circle(image, (x, y), 19, (0, 0, 0), -1)
        marked = Path(self.td.name) / "marked.png"
        cv2.imwrite(str(marked), image)
        
        result = process_scan(marked)
        self.assertIsNotNone(result["status"])
        self.assertIsNotNone(result["answers"])


class TestBulkProcess(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.sheet1 = Path(self.td.name) / "sheet1.png"
        self.sheet2 = Path(self.td.name) / "sheet2.png"
        generate_answer_sheet(self.sheet1)
        generate_answer_sheet(self.sheet2)

    def tearDown(self):
        self.td.cleanup()

    def test_bulk_process_returns_list(self):
        """bulk_process returns a list of results."""
        results = bulk_process([self.sheet1, self.sheet2])
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)

    def test_bulk_process_all_blank(self):
        """Bulk process with all-blank sheets returns 'blank' status."""
        results = bulk_process([self.sheet1, self.sheet2])
        for r in results:
            self.assertEqual(r["status"], "blank")
            self.assertIsNone(r["score_info"])


class TestBulkProcessWithContext(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db_path = Path(self.td.name) / "test.sqlite3"
        self.database = AssessFlowDatabase(self.db_path)
        self.database.initialize()

        self.classroom_id = self.database.create_classroom("Grade 7A")
        self.student_ada = self.database.create_student(
            self.classroom_id, "Ada Lovelace", "123456"
        )
        self.student_grace = self.database.create_student(
            self.classroom_id, "Grace Hopper", "654321"
        )
        self.assessment_id = self.database.create_assessment(
            self.classroom_id, "Science Quiz", load_answer_key()
        )

    def tearDown(self):
        self.td.cleanup()

    def _make_sheet_with_student_id(self, filename, student_id_str):
        """Generate a sheet and mark the Student ID bubbles."""
        sheet_path = Path(self.td.name) / filename
        generate_answer_sheet(sheet_path)
        image = cv2.imread(str(sheet_path))
        for i, digit_char in enumerate(student_id_str):
            position = i + 1
            value = int(digit_char)
            x, y = get_student_id_bubble_position(position, value)
            cv2.circle(image, (x, y), 13, (0, 0, 0), -1)
        cv2.imwrite(str(sheet_path), image)
        return sheet_path

    def test_unknown_student_id_returns_unknown_student(self):
        """Sheet with unknown Student ID returns 'unknown_student' status."""
        sheet = self._make_sheet_with_student_id("unknown.png", "999999")
        results = bulk_process_with_context(
            [sheet], self.database, self.classroom_id, self.assessment_id
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "unknown_student")
        self.assertIsNone(results[0]["student_id"])
        self.assertIsNone(results[0]["attempt_id"])

    def test_known_student_id_returns_graded(self):
        """Sheet with known Student ID returns 'graded' status."""
        sheet = self._make_sheet_with_student_id("ada.png", "123456")
        results = bulk_process_with_context(
            [sheet], self.database, self.classroom_id, self.assessment_id
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "graded")
        self.assertEqual(results[0]["student_id"], self.student_ada)
        self.assertIsNotNone(results[0]["attempt_id"])
        self.assertIsNotNone(results[0]["grading_result"])

    def test_multiple_sheets_with_different_students(self):
        """Multiple sheets with different Student IDs are correctly associated."""
        sheet_ada = self._make_sheet_with_student_id("ada.png", "123456")
        sheet_grace = self._make_sheet_with_student_id("grace.png", "654321")
        results = bulk_process_with_context(
            [sheet_ada, sheet_grace],
            self.database,
            self.classroom_id,
            self.assessment_id,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["student_id"], self.student_ada)
        self.assertEqual(results[1]["student_id"], self.student_grace)

    def test_blank_student_id_returns_unknown_student(self):
        """Sheet with blank Student ID returns 'unknown_student' status."""
        blank_sheet = Path(self.td.name) / "blank.png"
        generate_answer_sheet(blank_sheet)
        results = bulk_process_with_context(
            [blank_sheet], self.database, self.classroom_id, self.assessment_id
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "unknown_student")
        self.assertIsNone(results[0]["student_id"])


if __name__ == "__main__":
    unittest.main()