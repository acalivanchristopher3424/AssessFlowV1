from pathlib import Path

import cv2


# ============================================================
# AssessFlow V1 — OMR Shading Test
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

SOURCE_FILE = PROJECT_DIR / "samples" / "answer_sheet.png"
OUTPUT_FILE = PROJECT_DIR / "samples" / "shaded_test.png"


# These coordinates must match generate_sheet.py
CHOICE_X = {
    "A": 850,
    "B": 1200,
    "C": 1550,
    "D": 1900,
}

GRID_TOP = 550
ROW_HEIGHT = 125
BUBBLE_Y_OFFSET = 90


def get_bubble_position(question_number, choice):
    """Return the center of a bubble."""

    x = CHOICE_X[choice]

    y = (
        GRID_TOP
        + BUBBLE_Y_OFFSET
        + (question_number - 1) * ROW_HEIGHT
    )

    return x, y


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
        2: "B",
        3: "C",
        4: "D",
    }

    # --------------------------------------------------------
    # Shade the selected bubbles
    # --------------------------------------------------------

    for question, choice in test_answers.items():

        x, y = get_bubble_position(
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