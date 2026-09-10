from pathlib import Path

import cv2

from omr.detect_scan import align_scan, detect_question_answer, load_image
from omr.grade_answers import create_grading_result, grade_scan, load_answer_key
from omr.layout import QUESTIONS
from omr.student_id import detect_student_id


def classify_answer_count(answers):
    """Classify a scan based on the number of answered questions.

    Returns one of:
        - 'success'         : all 50 questions answered (no blanks, no multiples)
        - 'success_with_blanks': all 50 questions answered, some blank
        - 'blank'           : all answers are BLANK
        - 'multiple-marks'  : at least one question has MULTIPLE marks
        - 'failed'          : detection failed (empty answers dict)
    """
    if not answers:
        return "failed"

    total = len(answers)
    if total != 50:
        return "failed"

    blank_count = sum(1 for a in answers.values() if a == "BLANK")
    multiple_count = sum(1 for a in answers.values() if a == "MULTIPLE")

    if multiple_count > 0:
        return "multiple-marks"

    if blank_count > 0 and blank_count < 50:
        return "success_with_blanks"

    if blank_count == 50:
        return "blank"

    return "success"


def process_scan(input_file):
    """Process a single scanned answer sheet.

    Returns a dict with:
        - input_file: str
        - status: one of 'success', 'success_with_blanks', 'blank',
          'multiple-marks', 'failed'
        - answers: {question_number: answer, ...} or None
        - score_info: dict with score, percentage, correct, wrong, blank, multiple
        - source_file: str
    """
    try:
        image = load_image(input_file)
    except FileNotFoundError:
        return {
            "input_file": str(input_file),
            "status": "failed",
            "answers": None,
            "score_info": None,
            "source_file": str(input_file),
        }

    aligned_image = align_scan(image)
    gray = cv2.cvtColor(
        aligned_image,
        cv2.COLOR_BGR2GRAY,
    )

    raw_answers = {}
    for question_number in range(1, QUESTIONS + 1):
        answer, scores = detect_question_answer(gray, question_number)
        raw_answers[question_number] = answer

    if not raw_answers:
        return {
            "input_file": str(input_file),
            "status": "failed",
            "answers": None,
            "score_info": None,
            "source_file": str(input_file),
        }

    classification = classify_answer_count(raw_answers)

    answer_key = load_answer_key()
    grade_result = None
    if classification in ("success", "success_with_blanks"):
        grade_result = create_grading_result(
            raw_answers,
            answer_key,
            source_file=input_file,
        )

    score_info = None
    if grade_result:
        score_info = {
            "score": grade_result["score"],
            "percentage": grade_result["percentage"],
            "correct": grade_result["correct"],
            "wrong": grade_result["wrong"],
            "blank": grade_result["blank"],
            "multiple": grade_result["multiple"],
        }

    return {
        "input_file": str(input_file),
        "status": classification,
        "answers": raw_answers,
        "score_info": score_info,
        "source_file": str(input_file),
    }


def bulk_process(input_files):
    """Process a batch of scanned answer sheets.

    Returns a list of per-sheet result dicts (see process_scan).
    Each file is processed independently; errors in one file
    do not prevent processing of others.
    """
    results = []
    for input_file in input_files:
        result = process_scan(input_file)
        results.append(result)
    return results


def bulk_process_with_context(
    input_files,
    database,
    classroom_id,
    assessment_id,
):
    """Process a batch of scans and associate results with students.

    For each scan:
    1. Detect Student ID from the scanned sheet
    2. Look up the student in the database (classroom-scoped)
    3. Grade the answers
    4. Save the grading result linked to the student

    Returns a list of per-sheet result dicts with:
        - input_file: str
        - status: str (scan classification or 'unknown_student')
        - student_id: int or None
        - attempt_id: int or None (saved grading attempt ID)
        - grading_result: dict or None
    """
    results = []

    for input_file in input_files:

        try:
            detected_id = detect_student_id(input_file)
        except Exception:
            detected_id = None

        if detected_id is None:
            results.append({
                "input_file": str(input_file),
                "status": "unknown_student",
                "student_id": None,
                "attempt_id": None,
                "grading_result": None,
            })
            continue

        student = database.find_student_by_identifier(
            classroom_id,
            detected_id,
        )

        if student is None:
            results.append({
                "input_file": str(input_file),
                "status": "unknown_student",
                "student_id": None,
                "attempt_id": None,
                "grading_result": None,
            })
            continue

        try:
            assessment = database.get_assessment(assessment_id)
            question_count = assessment["question_count"] if assessment else None
            grading_result = grade_scan(input_file, question_count=question_count)
        except Exception:
            grading_result = None

        if grading_result is None:
            results.append({
                "input_file": str(input_file),
                "status": "failed",
                "student_id": student["id"],
                "attempt_id": None,
                "grading_result": None,
            })
            continue

        try:
            attempt_id = database.save_grading_result(
                assessment_id,
                grading_result,
                student_id=student["id"],
            )
        except Exception:
            attempt_id = None

        results.append({
            "input_file": str(input_file),
            "status": "graded",
            "student_id": student["id"],
            "attempt_id": attempt_id,
            "grading_result": grading_result,
        })

    return results