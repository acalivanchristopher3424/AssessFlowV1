from pathlib import Path
import sys

import cv2
import numpy as np

try:
    from .layout import (
        CHOICES,
        PAGE_HEIGHT as REFERENCE_HEIGHT,
        PAGE_WIDTH as REFERENCE_WIDTH,
        QUESTIONS,
        SAMPLE_RADIUS,
        get_question_bubble_position,
    )
except ImportError:
    from layout import (
        CHOICES,
        PAGE_HEIGHT as REFERENCE_HEIGHT,
        PAGE_WIDTH as REFERENCE_WIDTH,
        QUESTIONS,
        SAMPLE_RADIUS,
        get_question_bubble_position,
    )


# ============================================================
# AssessFlow V1 — Scanned OMR Detector
#
# Features:
# - Registration marker detection
# - Perspective alignment
# - Inner bubble sampling
# - Blank detection
# - Single-answer detection
# - Multiple-mark detection
# ============================================================


# ============================================================
# STANDARD ANSWER SHEET
# ============================================================

DARK_PIXEL_THRESHOLD = 180


# ============================================================
# MULTIPLE-MARK DETECTION
# ============================================================

# A bubble needs at least this much shading to be considered
# a possible marked bubble.
MIN_MARK_SCORE = 0.40


# The bubble must also be sufficiently darker than the
# background level of the other bubbles.
MIN_BACKGROUND_GAP = 0.12


# ============================================================
# ROBUST BUBBLE SAMPLING
# ============================================================

# When sampling a bubble, search within this radius for the
# darkest point and sample there. This handles marks that
# are offset from the expected bubble center due to
# hand-marking variation.
BUBBLE_SEARCH_RADIUS = 25


# ============================================================
# DEBUG
# ============================================================

DEBUG_SAMPLE_RADIUS = SAMPLE_RADIUS


# ============================================================
# REGISTRATION MARKERS
# ============================================================

REFERENCE_MARKERS = np.float32([
    [105, 105],
    [2375, 105],
    [2375, 3433],
    [105, 3433],
])


# ============================================================
# FILE PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_INPUT = (
    PROJECT_DIR
    / "samples"
    / "answer_sheet.png"
)

ALIGNED_FILE = (
    PROJECT_DIR
    / "samples"
    / "aligned_scan.png"
)

OUTPUT_FILE = (
    PROJECT_DIR
    / "samples"
    / "scan_result.png"
)


# ============================================================
# IMAGE LOADING
# ============================================================

def load_image(path):
    """Load an image from disk."""

    image = cv2.imread(str(path))

    if image is None:
        raise FileNotFoundError(
            f"Could not open image:\n{path}"
        )

    return image


# ============================================================
# FIND ONE REGISTRATION MARKER
# ============================================================

def find_marker_in_corner(
    gray,
    corner_name,
):
    """Find one registration marker near a page corner."""

    image_height, image_width = gray.shape

    search_width = int(
        image_width * 0.15
    )

    search_height = int(
        image_height * 0.12
    )

    if corner_name == "top_left":

        x1 = 0
        y1 = 0
        x2 = search_width
        y2 = search_height

    elif corner_name == "top_right":

        x1 = image_width - search_width
        y1 = 0
        x2 = image_width
        y2 = search_height

    elif corner_name == "bottom_right":

        x1 = image_width - search_width
        y1 = image_height - search_height
        x2 = image_width
        y2 = image_height

    elif corner_name == "bottom_left":

        x1 = 0
        y1 = image_height - search_height
        x2 = search_width
        y2 = image_height

    else:

        raise ValueError(
            f"Unknown corner: {corner_name}"
        )

    corner = gray[
        y1:y2,
        x1:x2
    ]

    if corner.size == 0:
        return None

    _, binary = cv2.threshold(
        corner,
        200,
        255,
        cv2.THRESH_BINARY_INV,
    )

    kernel = np.ones(
        (3, 3),
        np.uint8,
    )

    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_CLOSE,
        kernel,
    )

    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    candidates = []

    for contour in contours:

        bx, by, width, height = (
            cv2.boundingRect(contour)
        )

        area = cv2.contourArea(contour)

        if width <= 0 or height <= 0:
            continue

        if area < 100:
            continue

        if area > 15000:
            continue

        aspect_ratio = width / height

        if not 0.50 <= aspect_ratio <= 1.50:
            continue

        rectangle_area = width * height

        if rectangle_area <= 0:
            continue

        fill_ratio = (
            area / rectangle_area
        )

        if fill_ratio < 0.35:
            continue

        center_x = (
            x1
            + bx
            + width / 2
        )

        center_y = (
            y1
            + by
            + height / 2
        )

        if corner_name == "top_left":

            corner_x = 0
            corner_y = 0

        elif corner_name == "top_right":

            corner_x = image_width
            corner_y = 0

        elif corner_name == "bottom_right":

            corner_x = image_width
            corner_y = image_height

        else:

            corner_x = 0
            corner_y = image_height

        distance = (
            (center_x - corner_x) ** 2
            +
            (center_y - corner_y) ** 2
        )

        candidates.append(
            {
                "x": center_x,
                "y": center_y,
                "width": width,
                "height": height,
                "area": area,
                "distance": distance,
            }
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item["distance"]
    )

    return candidates[0]


# ============================================================
# FIND ALL REGISTRATION MARKERS
# ============================================================

def find_registration_markers(image):
    """Find all four registration markers."""

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    print()
    print(
        "Searching for registration markers..."
    )

    corner_names = [
        "top_left",
        "top_right",
        "bottom_right",
        "bottom_left",
    ]

    found = {}

    for corner_name in corner_names:

        marker = find_marker_in_corner(
            gray,
            corner_name,
        )

        if marker is None:

            print(
                f"  {corner_name:12}: NOT FOUND"
            )

        else:

            found[corner_name] = marker

            print(
                f"  {corner_name:12}: "
                f"x={marker['x']:.1f}, "
                f"y={marker['y']:.1f}, "
                f"size={marker['width']}x"
                f"{marker['height']}"
            )

    if len(found) != 4:

        missing = [
            name
            for name in corner_names
            if name not in found
        ]

        raise RuntimeError(
            "Could not find all four registration "
            "markers.\n"
            f"Missing: {', '.join(missing)}"
        )

    markers = np.float32([
        [
            found["top_left"]["x"],
            found["top_left"]["y"],
        ],

        [
            found["top_right"]["x"],
            found["top_right"]["y"],
        ],

        [
            found["bottom_right"]["x"],
            found["bottom_right"]["y"],
        ],

        [
            found["bottom_left"]["x"],
            found["bottom_left"]["y"],
        ],
    ])

    return markers


# ============================================================
# ALIGN SCAN
# ============================================================

def align_scan(image):
    """Align the scan using the four registration markers."""

    markers = find_registration_markers(
        image
    )

    print()
    print(
        "Registration markers successfully found."
    )

    print()
    print(
        "Applying perspective correction..."
    )

    transformation_matrix = (
        cv2.getPerspectiveTransform(
            markers,
            REFERENCE_MARKERS,
        )
    )

    aligned = cv2.warpPerspective(
        image,
        transformation_matrix,
        (
            REFERENCE_WIDTH,
            REFERENCE_HEIGHT,
        ),
    )

    return aligned


# ============================================================
# BUBBLE POSITION
# ============================================================

def get_bubble_position(
    question_number,
    choice,
):
    """Return the center of a bubble in the shared sheet layout."""

    return get_question_bubble_position(question_number, choice)


# ============================================================
# CIRCULAR MASK
# ============================================================

def create_circular_mask(radius):
    """Create a circular sampling mask."""

    diameter = (
        radius * 2
        + 1
    )

    center = radius

    y, x = np.ogrid[
        :diameter,
        :diameter
    ]

    distance_squared = (
        (x - center) ** 2
        +
        (y - center) ** 2
    )

    return (
        distance_squared
        <= radius ** 2
    )


# ============================================================
# BUBBLE SHADING
# ============================================================

def calculate_bubble_shading(
    gray,
    center_x,
    center_y,
):
    """
    Measure shading inside a bubble, robust to mark offset.

    First samples at the expected center. If the shading is
    in the ambiguous zone (near the detection threshold),
    searches within BUBBLE_SEARCH_RADIUS for the darkest
    point and re-samples there. This handles marks that are
    shifted from the expected bubble center due to normal
    hand-marking variation.

    The search is skipped when standard shading is very low
    (clearly blank) to avoid picking up adjacent labels or
    features.
    """

    radius = SAMPLE_RADIUS

    # --------------------------------------------------------
    # Standard shading at the expected center.
    # --------------------------------------------------------

    standard = _sample_shading(
        gray, center_x, center_y, radius
    )

    # --------------------------------------------------------
    # If standard shading is very low, the bubble is clearly
    # blank. Skip the wider search to avoid picking up
    # adjacent labels or text on the answer sheet.
    # --------------------------------------------------------

    if standard < 0.10:
        return standard

    # --------------------------------------------------------
    # Search for the darkest pixel within the search radius.
    # This catches marks that are offset from the expected
    # center due to hand-marking variation.
    # --------------------------------------------------------

    sr = BUBBLE_SEARCH_RADIUS

    y1 = max(0, center_y - sr)
    y2 = min(gray.shape[0], center_y + sr + 1)
    x1 = max(0, center_x - sr)
    x2 = min(gray.shape[1], center_x + sr + 1)

    region = gray[y1:y2, x1:x2]

    if region.size == 0:
        return standard

    min_loc = np.unravel_index(
        region.argmin(), region.shape
    )

    dark_x = x1 + min_loc[1]
    dark_y = y1 + min_loc[0]

    # --------------------------------------------------------
    # If the darkest point is essentially at the center,
    # the standard result is already optimal.
    # --------------------------------------------------------

    offset = np.sqrt(
        (dark_x - center_x) ** 2
        +
        (dark_y - center_y) ** 2
    )

    if offset < 3:
        return standard

    # --------------------------------------------------------
    # Sample shading at the darkest point.
    # --------------------------------------------------------

    at_darkest = _sample_shading(
        gray, dark_x, dark_y, radius
    )

    return max(standard, at_darkest)


def _sample_shading(gray, center_x, center_y, radius):
    """Sample shading at a specific point (internal helper)."""

    x1 = center_x - radius
    y1 = center_y - radius

    x2 = center_x + radius
    y2 = center_y + radius

    if (
        x1 < 0
        or y1 < 0
        or x2 >= gray.shape[1]
        or y2 >= gray.shape[0]
    ):
        return 0.0

    roi = gray[
        y1:y2 + 1,
        x1:x2 + 1
    ]

    mask = create_circular_mask(
        radius
    )

    pixels = roi[mask]

    if pixels.size == 0:
        return 0.0

    dark_pixels = (
        pixels
        < DARK_PIXEL_THRESHOLD
    )

    return float(
        np.mean(dark_pixels)
    )


# ============================================================
# DETECT ONE QUESTION
# ============================================================

def detect_question_answer(
    gray,
    question_number,
):
    """
    Detect:

        - BLANK
        - A/B/C/D
        - MULTIPLE
    """

    scores = {}

    # --------------------------------------------------------
    # Measure all four bubbles.
    # --------------------------------------------------------

    for choice in CHOICES:

        x, y = get_bubble_position(
            question_number,
            choice,
        )

        scores[choice] = (
            calculate_bubble_shading(
                gray,
                x,
                y,
            )
        )

    # --------------------------------------------------------
    # Sort from darkest to lightest.
    # --------------------------------------------------------

    sorted_choices = sorted(
        CHOICES,
        key=lambda choice: scores[choice],
        reverse=True,
    )

    # --------------------------------------------------------
    # Determine background level.
    #
    # The median is useful because it represents the normal
    # appearance of the mostly-unmarked bubbles.
    # --------------------------------------------------------

    score_values = [
        scores[choice]
        for choice in CHOICES
    ]

    background_level = float(
        np.median(score_values)
    )

    # --------------------------------------------------------
    # Determine which bubbles are genuinely marked.
    #
    # A bubble must:
    #
    # 1. Have enough absolute shading.
    #
    # AND
    #
    # 2. Be sufficiently darker than the background.
    # --------------------------------------------------------

    marked_choices = []

    for choice in CHOICES:

        score = scores[choice]

        if (
            score >= MIN_MARK_SCORE
            and
            score >= (
                background_level
                + MIN_BACKGROUND_GAP
            )
        ):

            marked_choices.append(
                choice
            )

    # --------------------------------------------------------
    # BLANK
    # --------------------------------------------------------

    if len(marked_choices) == 0:

        return "BLANK", scores

    # --------------------------------------------------------
    # MULTIPLE MARK
    # --------------------------------------------------------

    if len(marked_choices) >= 2:

        return "MULTIPLE", scores

    # --------------------------------------------------------
    # SINGLE ANSWER
    # --------------------------------------------------------

    return marked_choices[0], scores


# ============================================================
# DEBUG IMAGE
# ============================================================

def create_debug_image(
    image,
    answers,
):
    """
    Blue = actual sampling area.

    Red = single detected answer.

    Orange = multiple-mark question.
    """

    debug_image = image.copy()

    for question_number in range(
        1,
        QUESTIONS + 1,
    ):

        answer = answers[
            question_number
        ]

        # ----------------------------------------------------
        # Draw all sampling areas.
        # ----------------------------------------------------

        for choice in CHOICES:

            x, y = get_bubble_position(
                question_number,
                choice,
            )

            # Blue = actual sampling area.
            cv2.circle(
                debug_image,
                (x, y),
                DEBUG_SAMPLE_RADIUS,
                (255, 0, 0),
                2,
            )

            # Center point.
            cv2.circle(
                debug_image,
                (x, y),
                2,
                (255, 0, 0),
                -1,
            )

        # ----------------------------------------------------
        # Single answer.
        # ----------------------------------------------------

        if answer in CHOICES:

            x, y = get_bubble_position(
                question_number,
                answer,
            )

            cv2.circle(
                debug_image,
                (x, y),
                DEBUG_SAMPLE_RADIUS + 4,
                (0, 0, 255),
                3,
            )

        # ----------------------------------------------------
        # Multiple mark.
        # ----------------------------------------------------

        elif answer == "MULTIPLE":

            for choice in CHOICES:

                x, y = get_bubble_position(
                    question_number,
                    choice,
                )

                # Yellow/orange outline around the question's
                # bubble locations.
                cv2.circle(
                    debug_image,
                    (x, y),
                    DEBUG_SAMPLE_RADIUS + 4,
                    (0, 165, 255),
                    2,
                )

    return debug_image


# ============================================================
# MAIN DETECTOR
# ============================================================

def detect_scan(input_file):

    print()
    print("=" * 60)
    print(
        "ASSESSFLOW V1 — SCANNED OMR DETECTOR"
    )
    print("=" * 60)
    print()

    print(
        f"Input: {input_file}"
    )

    # --------------------------------------------------------
    # Load image.
    # --------------------------------------------------------

    image = load_image(
        input_file
    )

    image_height, image_width = (
        image.shape[:2]
    )

    print(
        f"Image size: "
        f"{image_width} x {image_height}"
    )

    print(
        f"Reference size: "
        f"{REFERENCE_WIDTH} x "
        f"{REFERENCE_HEIGHT}"
    )

    # --------------------------------------------------------
    # Align.
    # --------------------------------------------------------

    aligned_image = align_scan(
        image
    )

    # --------------------------------------------------------
    # Save aligned image.
    # --------------------------------------------------------

    cv2.imwrite(
        str(ALIGNED_FILE),
        aligned_image,
    )

    print()
    print(
        "Aligned image saved:"
    )

    print(
        ALIGNED_FILE
    )

    # --------------------------------------------------------
    # Grayscale.
    # --------------------------------------------------------

    gray = cv2.cvtColor(
        aligned_image,
        cv2.COLOR_BGR2GRAY,
    )

    # --------------------------------------------------------
    # Detect.
    # --------------------------------------------------------

    answers = {}

    print()
    print(
        "Detected answers:"
    )

    print(
        "-" * 60
    )

    for question_number in range(
        1,
        QUESTIONS + 1,
    ):

        answer, scores = (
            detect_question_answer(
                gray,
                question_number,
            )
        )

        answers[
            question_number
        ] = answer

        print(
            f"{question_number:2}. "
            f"{answer:8} "
            f"A={scores['A']:.2f} "
            f"B={scores['B']:.2f} "
            f"C={scores['C']:.2f} "
            f"D={scores['D']:.2f}"
        )

    # --------------------------------------------------------
    # Debug image.
    # --------------------------------------------------------

    debug_image = create_debug_image(
        aligned_image,
        answers,
    )

    cv2.imwrite(
        str(OUTPUT_FILE),
        debug_image,
    )

    # --------------------------------------------------------
    # Summary.
    # --------------------------------------------------------

    single_answers = sum(
        1
        for answer in answers.values()
        if answer in CHOICES
    )

    blank_answers = sum(
        1
        for answer in answers.values()
        if answer == "BLANK"
    )

    multiple_answers = sum(
        1
        for answer in answers.values()
        if answer == "MULTIPLE"
    )

    print()
    print(
        "=" * 60
    )

    print(
        "SCAN SUMMARY"
    )

    print(
        "-" * 60
    )

    print(
        f"Single answers : {single_answers}"
    )

    print(
        f"Blank answers  : {blank_answers}"
    )

    print(
        f"Multiple marks : {multiple_answers}"
    )

    print()
    print(
        f"Aligned image: {ALIGNED_FILE}"
    )

    print(
        f"Debug image:   {OUTPUT_FILE}"
    )

    print(
        "=" * 60
    )

    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) > 1:

        input_file = Path(
            sys.argv[1]
        )

    else:

        input_file = DEFAULT_INPUT

    detect_scan(
        input_file
    )
