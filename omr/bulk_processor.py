from pathlib import Path

import cv2

from omr.detect_scan import align_scan, detect_question_answer, load_image
from omr.grade_answers import create_grading_result, grade_scan, load_answer_key
from omr.layout import QUESTIONS


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