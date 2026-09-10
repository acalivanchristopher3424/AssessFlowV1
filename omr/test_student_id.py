"""Tests for Student ID detection from scanned answer sheets."""

import tempfile
import unittest
from pathlib import Path

import cv2

from omr.generate_sheet import generate_answer_sheet
from omr.layout import get_student_id_bubble_position
from omr.student_id import detect_student_id


class StudentIDDetectionTests(unittest.TestCase):

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.sheet_file = Path(self.temporary_directory.name) / "sheet.png"
        generate_answer_sheet(self.sheet_file)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _mark_student_id(self, image, digits):
        """Mark specific Student ID bubbles on the image.

        digits: dict mapping digit_position (1-6) to digit_value (0-9)
        """
        for position, value in digits.items():
            x, y = get_student_id_bubble_position(position, value)
            cv2.circle(image, (x, y), 13, (0, 0, 0), -1)
        return image

    def test_blank_student_id_returns_none(self):
        """Blank Student ID (all bubbles empty) returns None."""
        result = detect_student_id(self.sheet_file)
        self.assertIsNone(result)

    def test_single_digit_per_column_returns_correct_id(self):
        """One digit marked per column returns correct 6-digit string."""
        image = cv2.imread(str(self.sheet_file))
        self._mark_student_id(image, {
            1: 1, 2: 2, 3: 3,
            4: 4, 5: 5, 6: 6,
        })
        marked_file = Path(self.temporary_directory.name) / "marked.png"
        cv2.imwrite(str(marked_file), image)

        result = detect_student_id(marked_file)
        self.assertEqual(result, "123456")

    def test_all_zeros_returns_correct_id(self):
        """Marking digit 0 in all columns returns '000000'."""
        image = cv2.imread(str(self.sheet_file))
        self._mark_student_id(image, {
            1: 0, 2: 0, 3: 0,
            4: 0, 5: 0, 6: 0,
        })
        marked_file = Path(self.temporary_directory.name) / "marked.png"
        cv2.imwrite(str(marked_file), image)

        result = detect_student_id(marked_file)
        self.assertEqual(result, "000000")

    def test_all_nines_returns_correct_id(self):
        """Marking digit 9 in all columns returns '999999'."""
        image = cv2.imread(str(self.sheet_file))
        self._mark_student_id(image, {
            1: 9, 2: 9, 3: 9,
            4: 9, 5: 9, 6: 9,
        })
        marked_file = Path(self.temporary_directory.name) / "marked.png"
        cv2.imwrite(str(marked_file), image)

        result = detect_student_id(marked_file)
        self.assertEqual(result, "999999")

    def test_mixed_digits_returns_correct_id(self):
        """Marking different digits in each column returns correct string."""
        image = cv2.imread(str(self.sheet_file))
        self._mark_student_id(image, {
            1: 0, 2: 3, 3: 7,
            4: 2, 5: 8, 6: 5,
        })
        marked_file = Path(self.temporary_directory.name) / "marked.png"
        cv2.imwrite(str(marked_file), image)

        result = detect_student_id(marked_file)
        self.assertEqual(result, "037285")

    def test_multiple_marks_in_column_returns_none(self):
        """Multiple marks in same column returns None (invalid)."""
        image = cv2.imread(str(self.sheet_file))
        x1, y1 = get_student_id_bubble_position(1, 1)
        x2, y2 = get_student_id_bubble_position(1, 5)
        cv2.circle(image, (x1, y1), 13, (0, 0, 0), -1)
        cv2.circle(image, (x2, y2), 13, (0, 0, 0), -1)
        marked_file = Path(self.temporary_directory.name) / "marked.png"
        cv2.imwrite(str(marked_file), image)

        result = detect_student_id(marked_file)
        self.assertIsNone(result)

    def test_returns_none_for_nonexistent_file(self):
        """Non-existent file returns None."""
        result = detect_student_id(Path("nonexistent.png"))
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
