"""Shared geometry for the AssessFlow V1 answer sheet and OMR scanner."""

PAGE_WIDTH = 2480
PAGE_HEIGHT = 3508
QUESTIONS = 50
CHOICES = list("ABCDEFGHIJKL")

STUDENT_ID_DIGITS = 6
STUDENT_ID_VALUES = list(range(10))

DARK_PIXEL_THRESHOLD = 180
BUBBLE_RADIUS = 19
SAMPLE_RADIUS = 9

QUESTION_COLUMNS = 2
QUESTIONS_PER_COLUMN = QUESTIONS // QUESTION_COLUMNS
ANSWER_TOP = 1230
ANSWER_ROW_HEIGHT = 78
QUESTION_X = [245, 1300]
CHOICE_X = [[370 + 62 * index for index in range(12)], [1425 + 62 * index for index in range(12)]]

STUDENT_ID_TOP = 545
STUDENT_ID_ROW_HEIGHT = 54
STUDENT_ID_X = [675 + 150 * index for index in range(STUDENT_ID_DIGITS)]


def get_question_bubble_position(question_number, choice):
    """Return the center point of one answer bubble."""
    if not 1 <= question_number <= QUESTIONS:
        raise ValueError(f"Question number must be between 1 and {QUESTIONS}.")
    if choice not in CHOICES:
        raise ValueError(f"Choice must be one of: {', '.join(CHOICES)}.")
    column = (question_number - 1) // QUESTIONS_PER_COLUMN
    row = (question_number - 1) % QUESTIONS_PER_COLUMN
    choice_index = CHOICES.index(choice)
    return CHOICE_X[column][choice_index], ANSWER_TOP + row * ANSWER_ROW_HEIGHT


def get_student_id_bubble_position(digit_position, digit_value):
    """Return the center point of a Student ID bubble."""
    if not 1 <= digit_position <= STUDENT_ID_DIGITS:
        raise ValueError(f"Student ID position must be between 1 and {STUDENT_ID_DIGITS}.")
    if digit_value not in STUDENT_ID_VALUES:
        raise ValueError("Student ID digit must be between 0 and 9.")
    return STUDENT_ID_X[digit_position - 1], STUDENT_ID_TOP + digit_value * STUDENT_ID_ROW_HEIGHT
