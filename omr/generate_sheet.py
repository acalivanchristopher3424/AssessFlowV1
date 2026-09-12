from pathlib import Path

import cv2
import numpy as np

try:
    from .layout import (ANSWER_TOP, BUBBLE_RADIUS, CHOICES, PAGE_HEIGHT, PAGE_WIDTH,
                         QUESTIONS, QUESTIONS_PER_COLUMN, STUDENT_ID_DIGITS, STUDENT_ID_TOP,
                         get_question_bubble_position, get_student_id_bubble_position)
except ImportError:
    from layout import (ANSWER_TOP, BUBBLE_RADIUS, CHOICES, PAGE_HEIGHT, PAGE_WIDTH,
                        QUESTIONS, QUESTIONS_PER_COLUMN, STUDENT_ID_DIGITS, STUDENT_ID_TOP,
                        get_question_bubble_position, get_student_id_bubble_position)


MARGIN = 180
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "resources" / "answer_sheets"
OUTPUT_FILE = OUTPUT_DIR / "AssessFlow_V1_Answer_Sheet.png"


def draw_text(image, text, position, font_scale=1.0, thickness=2):
    """Draw consistent sheet text."""
    cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                (0, 0, 0), thickness, cv2.LINE_AA)


def draw_registration_markers(image):
    """Draw the four unchanged markers used for perspective alignment."""
    marker_size = 70
    marker_margin = 70
    for x, y in [
        (marker_margin, marker_margin),
        (PAGE_WIDTH - marker_margin - marker_size, marker_margin),
        (PAGE_WIDTH - marker_margin - marker_size, PAGE_HEIGHT - marker_margin - marker_size),
        (marker_margin, PAGE_HEIGHT - marker_margin - marker_size),
    ]:
        cv2.rectangle(image, (x, y), (x + marker_size, y + marker_size), (0, 0, 0), -1)


def generate_answer_sheet(output_file=OUTPUT_FILE):
    """Generate the 50-question, A–L, Student ID-ready OMR answer sheet."""
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((PAGE_HEIGHT, PAGE_WIDTH, 3), 255, dtype=np.uint8)

    draw_registration_markers(image)
    draw_text(image, "ASSESSFLOW", (MARGIN, 180), font_scale=2.0, thickness=5)
    draw_text(image, "OMR ANSWER SHEET", (MARGIN, 255), font_scale=1.1, thickness=3)
    draw_text(image, "Name:", (MARGIN, 360), font_scale=0.8, thickness=2)
    cv2.line(image, (MARGIN + 105, 365), (1180, 365), (0, 0, 0), 2)
    draw_text(image, "Section:", (1320, 360), font_scale=0.8, thickness=2)
    cv2.line(image, (1455, 365), (2240, 365), (0, 0, 0), 2)

    draw_text(image, f"STUDENT ID ({STUDENT_ID_DIGITS} digits)", (MARGIN, 475), font_scale=0.85, thickness=2)
    draw_text(image, "Shade one bubble in each column.", (MARGIN, 520), font_scale=0.6, thickness=1)
    for position in range(1, STUDENT_ID_DIGITS + 1):
        x, _ = get_student_id_bubble_position(position, 0)
        draw_text(image, str(position), (x - 10, STUDENT_ID_TOP - 32), font_scale=0.65, thickness=2)
        for digit in range(10):
            bubble_x, bubble_y = get_student_id_bubble_position(position, digit)
            if position == 1:
                draw_text(image, str(digit), (550, bubble_y + 6), font_scale=0.55, thickness=1)
            else:
                draw_text(image, str(digit), (bubble_x - 28, bubble_y + 6), font_scale=0.55, thickness=1)
            cv2.circle(image, (bubble_x, bubble_y), BUBBLE_RADIUS, (0, 0, 0), 2)

    draw_text(image, "ANSWERS — shade ONE answer per question.", (MARGIN, 1120), font_scale=0.8, thickness=2)
    for column in range(2):
        first_question = column * QUESTIONS_PER_COLUMN + 1
        for choice in CHOICES:
            x, _ = get_question_bubble_position(first_question, choice)
            draw_text(image, choice, (x - 8, ANSWER_TOP - 35), font_scale=0.65, thickness=2)

    for question in range(1, QUESTIONS + 1):
        _, y = get_question_bubble_position(question, "A")
        question_x = 245 if question <= QUESTIONS_PER_COLUMN else 1300
        draw_text(image, f"{question:02}", (question_x, y + 7), font_scale=0.55, thickness=1)
        for choice in CHOICES:
            bubble_x, bubble_y = get_question_bubble_position(question, choice)
            cv2.circle(image, (bubble_x, bubble_y), BUBBLE_RADIUS, (0, 0, 0), 2)

    draw_text(image, "Use dark, complete marks. Do not mark more than one answer per question.",
              (MARGIN, PAGE_HEIGHT - 130), font_scale=0.6, thickness=1)
    cv2.imwrite(str(output_file), image)
    return output_file


if __name__ == "__main__":
    created = generate_answer_sheet()
    print(f"Answer sheet created: {created}")
    print(f"Questions: {QUESTIONS}")
    print(f"Choices: {', '.join(CHOICES)}")
