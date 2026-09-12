import tempfile
import unittest
from pathlib import Path

import cv2

try:
    from .detect_scan import calculate_bubble_shading, detect_question_answer
    from .generate_sheet import generate_answer_sheet
    from .grade_answers import grade_scan
    from .layout import get_question_bubble_position
except ImportError:
    from detect_scan import calculate_bubble_shading, detect_question_answer
    from generate_sheet import generate_answer_sheet
    from grade_answers import grade_scan
    from layout import get_question_bubble_position


# ============================================================
# AssessFlow V1 — OMR Shading Test
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

SOURCE_FILE = PROJECT_DIR / "samples" / "answer_sheet.png"
OUTPUT_FILE = PROJECT_DIR / "samples" / "shaded_test.png"


class LightMarkDetectionTests(unittest.TestCase):
    """Regression: marks with shading scores near the detection threshold
    must still be detected. Covers the real-world scenario from my_scan_3.jpg
    where lighter pen marks produce shade scores of 0.40-0.45."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.sheet_file = Path(self.temporary_directory.name) / "sheet.png"
        generate_answer_sheet(self.sheet_file)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _mark_lightly(self, image, question, choice, gray_value=140):
        """Mark a bubble with a lighter shade to simulate faint pen marks."""
        x, y = get_question_bubble_position(question, choice)
        cv2.circle(image, (x, y), 15, (gray_value, gray_value, gray_value), -1)

    def _detect(self, image_path):
        """Detect all 50 answers from an image."""
        image = cv2.imread(str(image_path))
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        answers = {}
        for q in range(1, 51):
            answer, scores = detect_question_answer(gray, q)
            answers[q] = (answer, scores)
        return answers

    def test_light_mark_above_040_is_detected(self):
        """A light mark (shade ~0.44) must be detected, not classified as BLANK."""
        image = cv2.imread(str(self.sheet_file))
        self._mark_lightly(image, 18, "D", gray_value=140)
        marked_file = Path(self.temporary_directory.name) / "light_mark.png"
        cv2.imwrite(str(marked_file), image)

        answers = self._detect(marked_file)
        answer_18, scores_18 = answers[18]
        self.assertEqual(answer_18, "D",
                         f"Q18 light mark should be D, got {answer_18} "
                         f"(shade={scores_18['D']:.4f})")

    def test_light_mark_at_boundary_is_detected(self):
        """A mark producing shade ~0.40 must be detected."""
        image = cv2.imread(str(self.sheet_file))
        self._mark_lightly(image, 20, "C", gray_value=155)
        marked_file = Path(self.temporary_directory.name) / "boundary_mark.png"
        cv2.imwrite(str(marked_file), image)

        answer_20, scores_20 = self._detect(marked_file)[20]
        self.assertEqual(answer_20, "C",
                         f"Q20 boundary mark should be C, got {answer_20} "
                         f"(shade={scores_20['C']:.4f})")

    def test_blank_questions_remain_blank(self):
        """Unmarked bubbles with shade < 0.39 must remain BLANK."""
        image = cv2.imread(str(self.sheet_file))
        self._mark_lightly(image, 18, "D", gray_value=140)
        marked_file = Path(self.temporary_directory.name) / "partial.png"
        cv2.imwrite(str(marked_file), image)

        answers = self._detect(marked_file)
        for q in [21, 25, 30, 35, 40, 45, 50]:
            answer_q, _ = answers[q]
            self.assertEqual(answer_q, "BLANK",
                             f"Q{q} should remain BLANK, got {answer_q}")

    def test_multiple_marks_still_detected(self):
        """Two dark marks in the same question must return MULTIPLE."""
        image = cv2.imread(str(self.sheet_file))
        for choice in ["A", "B"]:
            x, y = get_question_bubble_position(12, choice)
            cv2.circle(image, (x, y), 15, (0, 0, 0), -1)
        marked_file = Path(self.temporary_directory.name) / "multi.png"
        cv2.imwrite(str(marked_file), image)

        answer_12, _ = self._detect(marked_file)[12]
        self.assertEqual(answer_12, "MULTIPLE")

    def test_strong_mark_above_040_is_detected(self):
        """A dark, solid mark must still be detected."""
        image = cv2.imread(str(self.sheet_file))
        for choice in ["A", "D"]:
            x, y = get_question_bubble_position(17, choice)
            cv2.circle(image, (x, y), 17, (0, 0, 0), -1)
        # Mark only D more strongly
        x, y = get_question_bubble_position(17, "D")
        cv2.circle(image, (x, y), 17, (0, 0, 0), -1)
        marked_file = Path(self.temporary_directory.name) / "multi_strong.png"
        cv2.imwrite(str(marked_file), image)

        answer_17, _ = self._detect(marked_file)[17]
        self.assertEqual(answer_17, "MULTIPLE")

    def test_offset_mark_detected_by_robust_search(self):
        """A mark offset from bubble center must be detected.

        This covers the real-world scenario from my_scan_3.jpg and
        my_scan_4.jpg where hand-marking produces marks shifted
        from the expected center. The robust wider-area search
        finds the mark at its actual position.
        """
        from .student_id import detect_student_id

        scan_file = (
            PROJECT_DIR / "resources" / "samples" / "my_scan_3.jpg"
        )
        if not scan_file.exists():
            self.skipTest(
                f"Scan file not found: {scan_file}"
            )

        sid = detect_student_id(scan_file)
        self.assertEqual(sid, "123456",
                         f"SID should be 123456, got {sid}")

        result = grade_scan(scan_file, question_count=50)
        qs = {
            a["question_number"]: a
            for a in result["questions"]
        }

        for q in [17, 18, 19, 20]:
            self.assertIsNotNone(
                qs[q]["student_answer"],
                f"Q{q} should not be BLANK on my_scan_3.jpg",
            )
            self.assertNotEqual(
                qs[q]["student_answer"], "BLANK",
                f"Q{q} should not be BLANK on my_scan_3.jpg",
            )

        blank_21_50 = sum(
            1 for q in range(21, 51)
            if qs[q]["student_answer"] is None
            or qs[q]["student_answer"] == "BLANK"
        )
        self.assertEqual(
            blank_21_50, 30,
            f"Q21-Q50 should all be BLANK, "
            f"got {blank_21_50}/30 blank",
        )


def create_shaded_test():

    print()
    print("=" * 60)
    print("ASSESSFLOW V1 — CREATING SHADED TEST")
    print("=" * 60)
    print()

    # Load the clean answer sheet.
    image = cv2.imread(str(SOURCE_FILE))

    if image is None:
        raise FileNotFoundError(
            f"Could not open: {SOURCE_FILE}"
        )

    # --------------------------------------------------------
    # Test answers
    # --------------------------------------------------------

    test_answers = {
        1: "A",
        2: "L",
        26: "G",
        50: "B",
    }

    # --------------------------------------------------------
    # Shade the selected bubbles
    # --------------------------------------------------------

    for question, choice in test_answers.items():

        x, y = get_question_bubble_position(
            question,
            choice,
        )

        # Fill the inside of the bubble.
        cv2.circle(
            image,
            (x, y),
            17,
            (0, 0, 0),
            -1,
        )

        print(
            f"Question {question}: shaded {choice}"
        )

    # --------------------------------------------------------
    # Save test image
    # --------------------------------------------------------

    cv2.imwrite(
        str(OUTPUT_FILE),
        image,
    )

    print()
    print(f"Created: {OUTPUT_FILE}")
    print()


if __name__ == "__main__":
    create_shaded_test()
