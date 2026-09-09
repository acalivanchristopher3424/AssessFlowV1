from pathlib import Path

import cv2

try:
    from .layout import get_question_bubble_position
except ImportError:
    from layout import get_question_bubble_position


# ============================================================
# AssessFlow V1 — Multiple Mark Test
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_DIR
    / "samples"
    / "answer_sheet.png"
)

OUTPUT_FILE = (
    PROJECT_DIR
    / "samples"
    / "multiple_mark_test.png"
)


# ============================================================
# Create multiple-mark test
# ============================================================

def create_test():

    image = cv2.imread(
        str(INPUT_FILE)
    )

    if image is None:

        raise FileNotFoundError(
            f"Could not open:\n{INPUT_FILE}"
        )

    # --------------------------------------------------------
    # Add A and L to Question 7. The detector should report MULTIPLE.
    # --------------------------------------------------------

    question_number = 7
    choices = ["A", "L"]

    # --------------------------------------------------------
    # Fill the A bubble.
    #
    # The original sheet uses a bubble radius of about 24.
    # We use 17 so the mark resembles the existing shading.
    # --------------------------------------------------------

    for choice in choices:
        x, y = get_question_bubble_position(question_number, choice)
        cv2.circle(image, (x, y), 13, (70, 70, 70), -1)

    # --------------------------------------------------------
    # Save separate test image.
    # --------------------------------------------------------

    cv2.imwrite(
        str(OUTPUT_FILE),
        image,
    )

    print()
    print("=" * 60)
    print("MULTIPLE-MARK TEST CREATED")
    print("=" * 60)
    print()

    print(
        "Question 7 has been given A and L marks."
    )

    print(
        "Test Q7:     A + L"
    )

    print()

    print(
        f"Test image:"
    )

    print(
        OUTPUT_FILE
    )

    print()
    print("=" * 60)


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    create_test()
