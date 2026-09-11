from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest

import cv2

from omr.detect_scan import align_scan, detect_question_answer
from omr.generate_sheet import generate_answer_sheet
from omr.grade_answers import grade_scan
from omr.layout import (CHOICES, QUESTIONS, STUDENT_ID_DIGITS, STUDENT_ID_TOP,
                         STUDENT_ID_ROW_HEIGHT, STUDENT_ID_X,
                         get_question_bubble_position, get_student_id_bubble_position)


class AnswerSheetLayoutTests(unittest.TestCase):
    def test_layout_supports_fifty_questions_twelve_choices_and_student_id_grid(self):
        self.assertEqual(QUESTIONS, 50)
        self.assertEqual(CHOICES, list("ABCDEFGHIJKL"))
        self.assertEqual(STUDENT_ID_DIGITS, 6)
        self.assertNotEqual(get_question_bubble_position(1, "A"), get_question_bubble_position(1, "L"))
        self.assertNotEqual(get_question_bubble_position(1, "A"), get_question_bubble_position(26, "A"))
        self.assertNotEqual(get_student_id_bubble_position(1, 0), get_student_id_bubble_position(6, 9))

    def test_generated_sheet_aligns_and_detects_a_through_l_marks(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            sheet_file = Path(temporary_directory) / "marked_sheet.png"
            generate_answer_sheet(sheet_file)
            image = cv2.imread(str(sheet_file))

            for question, choice in {1: "A", 2: "L", 3: "B", 26: "G"}.items():
                x, y = get_question_bubble_position(question, choice)
                cv2.circle(image, (x, y), 13, (0, 0, 0), -1)
            x, y = get_question_bubble_position(3, "C")
            cv2.circle(image, (x, y), 13, (0, 0, 0), -1)
            cv2.imwrite(str(sheet_file), image)

            with redirect_stdout(None):
                result = grade_scan(sheet_file, {number: "A" for number in range(1, 51)})

            answers = {question["question_number"]: question["student_answer"] for question in result["questions"]}
            self.assertEqual(answers[1], "A")
            self.assertEqual(answers[2], "L")
            self.assertEqual(answers[3], "MULTIPLE")
            self.assertEqual(answers[26], "G")
            self.assertEqual(answers[50], "BLANK")


class StudentIDDigitLabelRegressionTests(unittest.TestCase):
    """Regression: digit labels (0-9) must appear on all 6 Student ID columns."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.sheet_file = Path(self.temporary_directory.name) / "sheet.png"
        generate_answer_sheet(self.sheet_file)
        self.image = cv2.imread(str(self.sheet_file))

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _has_dark_pixel_near(self, x, y, radius=8):
        """Check if there is a dark pixel in a small region around (x, y)."""
        h, w = self.image.shape[:2]
        x_min = max(0, x - radius)
        x_max = min(w, x + radius + 1)
        y_min = max(0, y - radius)
        y_max = min(h, y + radius + 1)
        region = self.image[y_min:y_max, x_min:x_max]
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        return int(gray.min()) < 180

    def test_digit_labels_present_on_column_1(self):
        """Column 1 has digit labels at x=550 for each digit row."""
        for digit in range(10):
            label_x = 550
            label_y = STUDENT_ID_TOP + digit * STUDENT_ID_ROW_HEIGHT + 6
            self.assertTrue(
                self._has_dark_pixel_near(label_x, label_y),
                f"Column 1 missing digit label for digit {digit} near ({label_x}, {label_y})",
            )

    def test_digit_labels_present_on_columns_2_through_6(self):
        """Columns 2-6 have digit labels at (bubble_x - 28) for each digit row."""
        for position in range(2, STUDENT_ID_DIGITS + 1):
            bubble_x = STUDENT_ID_X[position - 1]
            label_x = bubble_x - 28
            for digit in range(10):
                label_y = STUDENT_ID_TOP + digit * STUDENT_ID_ROW_HEIGHT + 6
                self.assertTrue(
                    self._has_dark_pixel_near(label_x, label_y),
                    f"Column {position} missing digit label for digit {digit} near ({label_x}, {label_y})",
                )

    def test_column_header_labels_present_on_all_columns(self):
        """Each column header (1-6) is labeled above the digit grid."""
        for position in range(1, STUDENT_ID_DIGITS + 1):
            header_x = STUDENT_ID_X[position - 1] - 10
            header_y = STUDENT_ID_TOP - 32
            self.assertTrue(
                self._has_dark_pixel_near(header_x, header_y),
                f"Column header label for position {position} missing near ({header_x}, {header_y})",
            )


if __name__ == "__main__":
    unittest.main()
