"""Direct detector for a generated, already-aligned answer sheet."""

from pathlib import Path

import cv2

try:
    from .detect_scan import create_debug_image, detect_question_answer, load_image
    from .layout import CHOICES, QUESTIONS
except ImportError:
    from detect_scan import create_debug_image, detect_question_answer, load_image
    from layout import CHOICES, QUESTIONS


PROJECT_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_DIR / "resources" / "answer_sheets" / "AssessFlow_V1_Answer_Sheet.png"
OUTPUT_FILE = PROJECT_DIR / "resources" / "samples" / "detected_answers.png"


def detect_answers(input_file=INPUT_FILE, output_file=OUTPUT_FILE):
    """Detect all A–L answer marks from an aligned image."""
    image = load_image(input_file)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    answers = {}

    for question_number in range(1, QUESTIONS + 1):
        answer, scores = detect_question_answer(gray, question_number)
        answers[question_number] = answer
        score_text = " ".join(f"{choice}={scores[choice]:.2f}" for choice in CHOICES)
        print(f"{question_number:02}. {answer:8} {score_text}")

    cv2.imwrite(str(output_file), create_debug_image(image, answers))
    return answers


if __name__ == "__main__":
    detect_answers()
