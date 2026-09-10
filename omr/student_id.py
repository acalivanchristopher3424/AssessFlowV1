"""Detect 6-digit Student ID from a scanned OMR answer sheet."""

from pathlib import Path

import cv2

try:
    from .detect_scan import (
        align_scan,
        calculate_bubble_shading,
        load_image,
    )
    from .layout import (
        STUDENT_ID_DIGITS,
        STUDENT_ID_VALUES,
        get_student_id_bubble_position,
    )
except ImportError:
    from detect_scan import (
        align_scan,
        calculate_bubble_shading,
        load_image,
    )
    from layout import (
        STUDENT_ID_DIGITS,
        STUDENT_ID_VALUES,
        get_student_id_bubble_position,
    )


MIN_MARK_SCORE = 0.15


def detect_student_id(input_file):
    """Detect the 6-digit Student ID from a scanned answer sheet.

    Returns the student ID as a string of 6 digits, or None if
    detection fails for any digit position.

    Detection failure reasons:
    - Column has no marked bubbles (blank)
    - Column has multiple marked bubbles (invalid/multiple-marked)
    - Image file cannot be loaded or aligned
    """

    try:
        image = load_image(input_file)
    except FileNotFoundError:
        return None

    aligned = align_scan(image)

    gray = cv2.cvtColor(
        aligned,
        cv2.COLOR_BGR2GRAY,
    )

    student_id_digits = []

    for digit_position in range(1, STUDENT_ID_DIGITS + 1):

        scores = {}

        for digit_value in STUDENT_ID_VALUES:

            x, y = get_student_id_bubble_position(
                digit_position,
                digit_value,
            )

            scores[digit_value] = (
                calculate_bubble_shading(
                    gray,
                    x,
                    y,
                )
            )

        marked_digits = [
            value
            for value in STUDENT_ID_VALUES
            if scores[value] >= MIN_MARK_SCORE
        ]

        if len(marked_digits) != 1:
            return None

        student_id_digits.append(
            str(marked_digits[0])
        )

    return "".join(student_id_digits)
