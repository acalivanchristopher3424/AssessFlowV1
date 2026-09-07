from pathlib import Path

import cv2
import numpy as np


# ============================================================
# AssessFlow V1 — OMR Answer Detector
# ============================================================

PAGE_WIDTH = 2480
PAGE_HEIGHT = 3508

QUESTIONS = 20
CHOICES = ["A", "B", "C", "D"]

# These coordinates match generate_sheet.py
CHOICE_X = {
    "A": 850,
    "B": 1200,
    "C": 1550,
    "D": 1900,
}

GRID_TOP = 550
ROW_HEIGHT = 125

BUBBLE_Y_OFFSET = 90

# Area inside the bubble that we use to measure shading.
# We intentionally stay away from the black outline.
SAMPLE_RADIUS = 15

# If the percentage of dark pixels inside the bubble
# reaches this value, we consider the bubble shaded.
SHADE_THRESHOLD = 0.20


# ------------------------------------------------------------
# File locations
# ------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = PROJECT_DIR / "samples" / "answer_sheet.png"

OUTPUT_FILE = PROJECT_DIR / "samples" / "detected_answers.png"


# ============================================================
# Utility functions
# ============================================================

def load_image(path):
    """Load an image from disk."""

    image = cv2.imread(str(path))

    if image is None:
        raise FileNotFoundError(
            f"Could not open image: {path}"
        )

    return image


def convert_to_grayscale(image):
    """Convert image to grayscale."""

    return cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )


def calculate_dark_pixel_ratio(gray, center_x, center_y):
    """
    Measure how much of the inside of a bubble is dark.

    We ignore the bubble outline by sampling only the
    center portion of the circle.
    """

    x1 = center_x - SAMPLE_RADIUS
    y1 = center_y - SAMPLE_RADIUS

    x2 = center_x + SAMPLE_RADIUS
    y2 = center_y + SAMPLE_RADIUS

    roi = gray[y1:y2 + 1, x1:x2 + 1]

    if roi.size == 0:
        return 0.0

    # Pixels darker than this are considered ink/shading.
    dark_pixels = roi < 180

    return float(np.mean(dark_pixels))


def get_bubble_position(question_number, choice):
    """Return the expected center position of a bubble."""

    x = CHOICE_X[choice]

    y = (
        GRID_TOP
        + BUBBLE_Y_OFFSET
        + (question_number - 1) * ROW_HEIGHT
    )

    return x, y


def detect_question_answer(gray, question_number):
    """
    Check A/B/C/D and determine which bubble is shaded.

    Returns:
        answer
        scores
    """

    scores = {}

    for choice in CHOICES:

        x, y = get_bubble_position(
            question_number,
            choice,
        )

        ratio = calculate_dark_pixel_ratio(
            gray,
            x,
            y,
        )

        scores[choice] = ratio

    # Find the darkest bubble.
    selected_choice = max(
        scores,
        key=scores.get,
    )

    selected_score = scores[selected_choice]

    # If even the darkest bubble isn't dark enough,
    # consider the question blank.
    if selected_score < SHADE_THRESHOLD:
        return None, scores

    return selected_choice, scores


# ============================================================
# Main detector
# ============================================================

def detect_answers():

    print()
    print("=" * 60)
    print("ASSESSFLOW V1 — OMR ANSWER DETECTOR")
    print("=" * 60)
    print()

    print(f"Input image: {INPUT_FILE}")

    # --------------------------------------------------------
    # Load image
    # --------------------------------------------------------

    image = load_image(INPUT_FILE)

    print(
        f"Image size: {image.shape[1]} x {image.shape[0]}"
    )

    # --------------------------------------------------------
    # Convert to grayscale
    # --------------------------------------------------------

    gray = convert_to_grayscale(image)

    # --------------------------------------------------------
    # Detect answers
    # --------------------------------------------------------

    answers = {}

    print()
    print("Detected answers:")
    print("-" * 60)

    for question_number in range(1, QUESTIONS + 1):

        answer, scores = detect_question_answer(
            gray,
            question_number,
        )

        answers[question_number] = answer

        if answer is None:

            print(
                f"{question_number:2}. "
                f"BLANK   "
                f"A={scores['A']:.2f} "
                f"B={scores['B']:.2f} "
                f"C={scores['C']:.2f} "
                f"D={scores['D']:.2f}"
            )

        else:

            print(
                f"{question_number:2}. "
                f"{answer}       "
                f"A={scores['A']:.2f} "
                f"B={scores['B']:.2f} "
                f"C={scores['C']:.2f} "
                f"D={scores['D']:.2f}"
            )

    # --------------------------------------------------------
    # Create visual debug image
    # --------------------------------------------------------

    debug_image = image.copy()

    for question_number in range(1, QUESTIONS + 1):

        answer = answers[question_number]

        for choice in CHOICES:

            x, y = get_bubble_position(
                question_number,
                choice,
            )

            # Draw detected bubble position.
            cv2.circle(
                debug_image,
                (x, y),
                35,
                (255, 0, 0),
                2,
            )

        if answer is not None:

            x, y = get_bubble_position(
                question_number,
                answer,
            )

            # Highlight detected answer.
            cv2.circle(
                debug_image,
                (x, y),
                40,
                (0, 0, 255),
                5,
            )

    # --------------------------------------------------------
    # Save debug image
    # --------------------------------------------------------

    cv2.imwrite(
        str(OUTPUT_FILE),
        debug_image,
    )

    print()
    print("=" * 60)
    print("Detection complete.")
    print(f"Debug image: {OUTPUT_FILE}")
    print("=" * 60)
    print()


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    detect_answers()