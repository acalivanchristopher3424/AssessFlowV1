from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import sys

import cv2

try:
    from .detect_scan import (
        align_scan,
        load_image,
        detect_question_answer,
        QUESTIONS,
    )
except ImportError:
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


def grade_answers(student_answers, answer_key, question_count=None):
    """Compare student answers with the answer key.

    Only grades questions 1 through question_count.
    Questions beyond question_count are ignored.
    """

    if question_count is None:
        question_count = QUESTIONS

    score = 0
    correct = 0
    wrong = 0
    blank = 0
    multiple = 0

    results = {}

    for question_number in range(
        1,
        question_count + 1,
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


def create_grading_result(student_answers, answer_key, source_file=None, question_count=None):
    """Return a JSON-serializable grading result for storage or an API.

    Only grades questions 1 through question_count.
    """

    if question_count is None:
        question_count = QUESTIONS

    (
        score,
        correct,
        wrong,
        blank,
        multiple,
        question_results,
    ) = grade_answers(student_answers, answer_key, question_count)

    questions = []

    for question_number in range(1, question_count + 1):
        question = question_results[question_number]

        questions.append({
            "question_number": question_number,
            "student_answer": question["student"],
            "correct_answer": question["correct"],
            "result": question["result"],
        })

    return {
        "source_file": str(source_file) if source_file else None,
        "total_questions": question_count,
        "score": score,
        "percentage": (score / question_count) * 100,
        "correct": correct,
        "wrong": wrong,
        "blank": blank,
        "multiple": multiple,
        "questions": questions,
    }


def grade_scan(input_file, answer_key=None, question_count=None):
    """Detect and grade one scan, returning a structured result."""

    if answer_key is None:
        answer_key = load_answer_key()

    student_answers = detect_student_answers(input_file)

    return create_grading_result(
        student_answers,
        answer_key,
        source_file=input_file,
        question_count=question_count,
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

    arguments = [argument for argument in sys.argv[1:] if argument != "--json"]

    if arguments:

        input_file = Path(
            arguments[0]
        )

    else:

        input_file = (
            Path(__file__).resolve().parent.parent
            / "samples"
            / "my_scan.jpeg"
        )

    json_output = "--json" in sys.argv

    if json_output:
        with redirect_stdout(io.StringIO()):
            structured_result = grade_scan(input_file)
        print(json.dumps(structured_result, indent=2))
        return

    print()
    print(
        f"Processing: {input_file}"
    )

    print(
        f"Answer key: {ANSWER_KEY_FILE}"
    )

    structured_result = grade_scan(input_file)

    student_answers = {
        question["question_number"]: question["student_answer"]
        for question in structured_result["questions"]
    }

    display_results(student_answers, load_answer_key())


if __name__ == "__main__":
    main()
