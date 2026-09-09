from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest

import cv2

from omr.detect_scan import align_scan, detect_question_answer
from omr.generate_sheet import generate_answer_sheet
from omr.grade_answers import grade_scan
from omr.layout import CHOICES, QUESTIONS, STUDENT_ID_DIGITS, get_question_bubble_position, get_student_id_bubble_position


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


if __name__ == "__main__":
    unittest.main()
