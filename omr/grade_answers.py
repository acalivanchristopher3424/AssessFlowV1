from pathlib import Path
import sys

import cv2

from detect_scan import (
    align_scan,
    load_image,
    detect_question_answer,
    QUESTIONS,
)


# ============================================================
# AssessFlow V1 — OMR + Grading
# ============================================================

ANSWER_KEY_FILE = (
    Path(__file__).resolve().parent
    / "answer_key.txt"
)


def load_answer_key():
    """Load the answer key from answer_key.txt."""

    answer_key = {}

    with open(ANSWER_KEY_FILE, "r") as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) != 2:
                continue

            question_number = int(parts[0])
            answer = parts[1].upper()

            answer_key[question_number] = answer

    return answer_key


def detect_student_answers(input_file):
    """Scan and detect all student answers."""

    image = load_image(input_file)

    aligned_image = align_scan(image)

    gray = cv2.cvtColor(
        aligned_image,
        cv2.COLOR_BGR2GRAY,
    )

    answers = {}

    for question_number in range(
        1,
        QUESTIONS + 1,
    ):

        answer, scores = detect_question_answer(
            gray,
            question_number,
        )

        answers[question_number] = answer

    return answers


def grade_answers(student_answers, answer_key):
    """Compare student answers with the answer key."""

    score = 0
    correct = 0
    wrong = 0
    blank = 0
    multiple = 0

    results = {}

    for question_number in range(
        1,
        QUESTIONS + 1,
    ):

        student_answer = student_answers.get(
            question_number
        )

        correct_answer = answer_key.get(
            question_number
        )

        if student_answer == correct_answer:

            result = "CORRECT"

            score += 1
            correct += 1

        elif student_answer == "BLANK":

            result = "BLANK"

            wrong += 1
            blank += 1

        elif student_answer == "MULTIPLE":

            result = "MULTIPLE"

            wrong += 1
            multiple += 1

        else:

            result = "WRONG"

            wrong += 1

        results[question_number] = {
            "student": student_answer,
            "correct": correct_answer,
            "result": result,
        }

    return (
        score,
        correct,
        wrong,
        blank,
        multiple,
        results,
    )


def display_results(student_answers, answer_key):
    """Display the final grading results."""

    (
        score,
        correct,
        wrong,
        blank,
        multiple,
        results,
    ) = grade_answers(
        student_answers,
        answer_key,
    )

    percentage = (
        score / QUESTIONS
    ) * 100

    print()
    print("=" * 60)
    print("ASSESSFLOW V1 — FINAL RESULTS")
    print("=" * 60)

    print()

    print(
        f"Score:      {score} / {QUESTIONS}"
    )

    print(
        f"Percentage: {percentage:.1f}%"
    )

    print()

    print(
        f"Correct:    {correct}"
    )

    print(
        f"Wrong:      {wrong}"
    )

    print(
        f"Blank:      {blank}"
    )

    print(
        f"Multiple:   {multiple}"
    )

    print()
    print("Question Results:")
    print("-" * 60)

    for question_number in range(
        1,
        QUESTIONS + 1,
    ):

        result = results[
            question_number
        ]

        student = result["student"]

        if student is None:
            student = "UNKNOWN"

        print(
            f"{question_number:2}. "
            f"Student: {student:8} "
            f"Correct: {result['correct']}   "
            f"{result['result']}"
        )

    print()
    print("=" * 60)


def main():

    if len(sys.argv) > 1:

        input_file = Path(
            sys.argv[1]
        )

    else:

        input_file = (
            Path(__file__).resolve().parent.parent
            / "samples"
            / "my_scan.jpeg"
        )

    print()
    print(
        f"Processing: {input_file}"
    )

    print(
        f"Answer key: {ANSWER_KEY_FILE}"
    )

    answer_key = load_answer_key()

    student_answers = detect_student_answers(
        input_file
    )

    display_results(
        student_answers,
        answer_key,
    )


if __name__ == "__main__":
    main()