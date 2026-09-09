from pathlib import Path

import cv2


# ============================================================
# AssessFlow V1 — Multiple Mark Test
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_DIR
    / "samples"
    / "aligned_scan.png"
)

OUTPUT_FILE = (
    PROJECT_DIR
    / "samples"
    / "multiple_mark_test.png"
)


# ============================================================
# Same bubble positions used by detect_scan.py
# ============================================================

CHOICE_X = {
    "A": 850,
    "B": 1200,
    "C": 1550,
    "D": 1900,
}

GRID_TOP = 550
ROW_HEIGHT = 125
BUBBLE_Y_OFFSET = 90


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
    # We will deliberately add A to Question 7.
    #
    # Question 7 already has B shaded.
    #
    # Therefore:
    #
    # Q7 = A + B
    #
    # The detector should report MULTIPLE.
    # --------------------------------------------------------

    question_number = 7
    choice = "A"

    x = CHOICE_X[choice]

    y = (
        GRID_TOP
        + BUBBLE_Y_OFFSET
        + (
            question_number - 1
        ) * ROW_HEIGHT
    )

    # --------------------------------------------------------
    # Fill the A bubble.
    #
    # The original sheet uses a bubble radius of about 24.
    # We use 17 so the mark resembles the existing shading.
    # --------------------------------------------------------

    cv2.circle(
        image,
        (x, y),
        17,
        (70, 70, 70),
        -1,
    )

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
        "Question 7 has been given an additional A mark."
    )

    print(
        "Original Q7: B"
    )

    print(
        "Test Q7:     A + B"
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