"""CSV parsing, validation, and export for AssessFlow."""

import csv
import io
import re


REQUIRED_COLUMNS = ["classroom_name", "student_id", "student_name"]

STUDENT_ID_PATTERN = re.compile(r"^\d{6}$")


def parse_and_validate(csv_content, existing_classroom_names=None):
    """Parse CSV content and validate all rows.

    Args:
        csv_content: Raw CSV content as bytes or string.
        existing_classroom_names: Set of classroom names that already
            exist in the database. If provided, imports with these
            names are rejected.

    Returns:
        A dict with:
            - 'valid': bool
            - 'errors': list of error strings
            - 'warnings': list of warning strings
            - 'classroom_name': str or None
            - 'students': list of dicts with 'student_id' and 'student_name'
            - 'row_count': int (data rows, excluding header)
    """
    if existing_classroom_names is None:
        existing_classroom_names = set()

    errors = []
    warnings = []
    students = []
    classroom_name = None

    # --------------------------------------------------------
    # Decode content.
    # --------------------------------------------------------

    if isinstance(csv_content, bytes):
        # Strip UTF-8 BOM if present.
        if csv_content.startswith(b"\xef\xbb\xbf"):
            csv_content = csv_content[3:]
        text = csv_content.decode("utf-8", errors="replace")
    else:
        text = csv_content

    # Normalize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # --------------------------------------------------------
    # Parse CSV.
    # --------------------------------------------------------

    try:
        reader = csv.DictReader(io.StringIO(text))
    except csv.Error as e:
        return {
            "valid": False,
            "errors": [f"Invalid CSV format: {e}"],
            "warnings": [],
            "classroom_name": None,
            "students": [],
            "row_count": 0,
        }

    # --------------------------------------------------------
    # Check required columns.
    # --------------------------------------------------------

    if reader.fieldnames is None:
        return {
            "valid": False,
            "errors": ["CSV file is empty or has no headers."],
            "warnings": [],
            "classroom_name": None,
            "students": [],
            "row_count": 0,
        }

    normalized_fields = [f.strip().lower() for f in reader.fieldnames]
    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in normalized_fields
    ]

    if missing:
        return {
            "valid": False,
            "errors": [
                f"Missing required column: '{col}'"
                for col in missing
            ],
            "warnings": [],
            "classroom_name": None,
            "students": [],
            "row_count": 0,
        }

    # Build a mapping from normalized name to original name.
    field_map = {
        f.strip().lower(): f for f in reader.fieldnames
    }

    # --------------------------------------------------------
    # Read and validate rows.
    # --------------------------------------------------------

    seen_ids = set()
    row_number = 1  # header is row 1

    for row in reader:
        row_number += 1

        # Skip completely blank rows.
        values = [v.strip() if v else "" for v in row.values()]
        if not any(values):
            warnings.append(f"Row {row_number}: blank row skipped.")
            continue

        # Extract fields.
        raw_name = row.get(field_map.get("classroom_name", ""), "")
        raw_id = row.get(field_map.get("student_id", ""), "")
        raw_student = row.get(field_map.get("student_name", ""), "")

        name = raw_name.strip() if raw_name else ""
        sid = raw_id.strip() if raw_id else ""
        student = raw_student.strip() if raw_student else ""

        # Classroom name.
        if not name:
            errors.append(f"Row {row_number}: classroom name is missing.")
        elif classroom_name is None:
            classroom_name = name
        elif name != classroom_name:
            errors.append(
                f"Row {row_number}: classroom name '{name}' "
                f"does not match '{classroom_name}'."
            )

        # Student ID.
        if not sid:
            errors.append(f"Row {row_number}: student ID is missing.")
        elif not STUDENT_ID_PATTERN.match(sid):
            errors.append(
                f"Row {row_number}: student ID '{sid}' must be "
                f"exactly 6 digits."
            )
        elif sid in seen_ids:
            errors.append(
                f"Row {row_number}: student ID '{sid}' is duplicated."
            )
        else:
            seen_ids.add(sid)

        # Student name.
        if not student:
            errors.append(f"Row {row_number}: student name is missing.")

        # Collect valid student entries (even if there are errors,
        # so the preview can show what was found).
        if name and sid and student and STUDENT_ID_PATTERN.match(sid):
            students.append({
                "student_id": sid,
                "student_name": student,
            })

    # --------------------------------------------------------
    # Check for existing classroom.
    # --------------------------------------------------------

    if classroom_name and classroom_name in existing_classroom_names:
        errors.append(
            f"Classroom '{classroom_name}' already exists. "
            f"Please rename the classroom in your CSV or delete "
            f"the existing classroom first."
        )

    # --------------------------------------------------------
    # Check for empty data.
    # --------------------------------------------------------

    if not students and not errors:
        errors.append("No valid student records found in the CSV.")

    # --------------------------------------------------------
    # Build result.
    # --------------------------------------------------------

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "classroom_name": classroom_name,
        "students": students,
        "row_count": row_number - 1,  # exclude header
    }


def generate_template():
    """Generate a CSV template string for classroom import.

    Returns a UTF-8 string with headers and one instructional row.
    """
    lines = [
        "classroom_name,student_id,student_name",
        "Example Class,123456,Student Name",
    ]
    return "\n".join(lines) + "\n"


def export_classroom_csv(classroom_name, students):
    """Generate a CSV export string for a classroom.

    Args:
        classroom_name: The classroom name.
        students: List of dicts with 'student_identifier' and 'name' keys.

    Returns:
        A UTF-8 CSV string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["classroom_name", "student_id", "student_name"])
    for s in students:
        writer.writerow([
            classroom_name,
            s.get("student_identifier") or "",
            s.get("name") or "",
        ])
    return output.getvalue()


# ============================================================
# Results export
# ============================================================

RESULTS_HEADERS = [
    "classroom",
    "student_id",
    "student_name",
    "assessment",
    "question_count",
    "score",
    "percentage",
    "wrong",
    "blank",
    "multiple",
    "date",
]

BOM = "\ufeff"


def export_results_csv(rows):
    """Generate a UTF-8 CSV with BOM for grading results.

    Args:
        rows: List of dicts, each with keys matching RESULTS_HEADERS.

    Returns:
        A UTF-8 encoded bytes object with BOM prefix.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=RESULTS_HEADERS)
    writer.writeheader()
    for row in rows:
        writer.writerow({
            "classroom": row.get("classroom", ""),
            "student_id": row.get("student_id", ""),
            "student_name": row.get("student_name", ""),
            "assessment": row.get("assessment", ""),
            "question_count": row.get("question_count", ""),
            "score": row.get("score", ""),
            "percentage": row.get("percentage", ""),
            "wrong": row.get("wrong", ""),
            "blank": row.get("blank", ""),
            "multiple": row.get("multiple", ""),
            "date": row.get("date", ""),
        })
    return (BOM + output.getvalue()).encode("utf-8")


def generate_results_filename(*parts):
    """Build a safe CSV filename for results export.

    Args:
        *parts: Variable number of strings to join (e.g. classroom, assessment).

    Returns:
        A filesystem-safe filename like 'AssessFlow_Grade7A_Midterm_Results.csv'.
    """
    safe_parts = []
    for part in parts:
        clean = str(part)
        for ch in r'\/:*?"<>|':
            clean = clean.replace(ch, "-")
        clean = clean.strip(". ")
        if clean:
            safe_parts.append(clean)
    name = "_".join(safe_parts) if safe_parts else ""
    if name:
        return f"AssessFlow_{name}_Results.csv"
    return "AssessFlow_Results.csv"
