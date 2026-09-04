from pathlib import Path

import cv2
import numpy as np


# ============================================================
# AssessFlow V1 — OMR Answer Sheet Generator
# ============================================================

PAGE_WIDTH = 2480
PAGE_HEIGHT = 3508

MARGIN = 180

QUESTIONS = 20
CHOICES = ["A", "B", "C", "D"]

BUBBLE_RADIUS = 24

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "samples"
OUTPUT_FILE = OUTPUT_DIR / "answer_sheet.png"


def draw_text(image, text, position, font_scale=1.0, thickness=2):
    """Draw text on the answer sheet."""
    cv2.putText(
        image,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (0, 0, 0),
        thickness,
        cv2.LINE_AA,
    )


def generate_answer_sheet():
    """Generate a clean A4-style OMR answer sheet."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # Create white A4 canvas
    # --------------------------------------------------------

    image = np.ones(
        (PAGE_HEIGHT, PAGE_WIDTH, 3),
        dtype=np.uint8,
    ) * 255

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    draw_text(
        image,
        "ASSESSFLOW",
        (MARGIN, 180),
        font_scale=2.2,
        thickness=5,
    )

    draw_text(
        image,
        "OMR ANSWER SHEET",
        (MARGIN, 260),
        font_scale=1.2,
        thickness=3,
    )

    # --------------------------------------------------------
    # Student information
    # --------------------------------------------------------

    draw_text(
        image,
        "Name:",
        (MARGIN, 380),
        font_scale=0.9,
        thickness=2,
    )

    cv2.line(
        image,
        (MARGIN + 130, 385),
        (1200, 385),
        (0, 0, 0),
        2,
    )

    draw_text(
        image,
        "Section:",
        (1350, 380),
        font_scale=0.9,
        thickness=2,
    )

    cv2.line(
        image,
        (1500, 385),
        (2250, 385),
        (0, 0, 0),
        2,
    )

    # --------------------------------------------------------
    # Registration markers
    #
    # These help the OMR engine identify the page.
    # --------------------------------------------------------

    marker_size = 70

    # Separate positioning for the corner markers
    # so they don't overlap the title or footer.
    marker_margin = 70

    markers = [
        # Top-left
        (marker_margin, marker_margin),

        # Top-right
        (
            PAGE_WIDTH - marker_margin - marker_size,
            marker_margin,
        ),

        # Bottom-left
        (
            marker_margin,
            PAGE_HEIGHT - marker_margin - marker_size,
        ),

        # Bottom-right
        (
            PAGE_WIDTH - marker_margin - marker_size,
            PAGE_HEIGHT - marker_margin - marker_size,
        ),
    ]

    for x, y in markers:
        cv2.rectangle(
            image,
            (x, y),
            (x + marker_size, y + marker_size),
            (0, 0, 0),
            -1,
        )

    # --------------------------------------------------------
    # Answer grid
    # --------------------------------------------------------

    grid_top = 550

    question_x = 260

    choice_x = {
        "A": 850,
        "B": 1200,
        "C": 1550,
        "D": 1900,
    }

    row_height = 125

    # --------------------------------------------------------
    # Column headings
    # --------------------------------------------------------

    for choice, x in choice_x.items():
        draw_text(
            image,
            choice,
            (x - 15, grid_top),
            font_scale=1.0,
            thickness=3,
        )

    # --------------------------------------------------------
    # Questions and bubbles
    # --------------------------------------------------------

    for question in range(1, QUESTIONS + 1):

        y = grid_top + 90 + (question - 1) * row_height

        draw_text(
            image,
            f"{question}.",
            (question_x, y + 10),
            font_scale=0.8,
            thickness=2,
        )

        for choice, x in choice_x.items():

            center = (x, y)

            cv2.circle(
                image,
                center,
                BUBBLE_RADIUS,
                (0, 0, 0),
                3,
            )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    draw_text(
        image,
        "Shade ONE answer per question.",
        (MARGIN, PAGE_HEIGHT - 130),
        font_scale=0.8,
        thickness=2,
    )

    # --------------------------------------------------------
    # Save image
    # --------------------------------------------------------

    cv2.imwrite(
        str(OUTPUT_FILE),
        image,
    )

    print(f"Answer sheet created: {OUTPUT_FILE}")
    print(f"Questions: {QUESTIONS}")
    print("Choices: A, B, C, D")


# ============================================================
# Run generator
# ============================================================

if __name__ == "__main__":
    generate_answer_sheet()