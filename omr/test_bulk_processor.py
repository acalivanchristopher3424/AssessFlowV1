import cv2
import tempfile
import unittest
from pathlib import Path

from omr.bulk_processor import bulk_process, process_scan
from omr.detect_scan import align_scan, detect_question_answer, load_image
from omr.generate_sheet import generate_answer_sheet
from omr.grade_answers import create_grading_result, load_answer_key


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


if __name__ == "__main__":
    unittest.main()