"""Tests for classroom import/export (Milestone 17)."""

import csv
import io
import tempfile
import unittest
from pathlib import Path

from omr.csv_handler import (
    generate_template,
    parse_and_validate,
    export_classroom_csv,
)
from omr.database import AssessFlowDatabase


# ============================================================
# CSV handler tests (no database)
# ============================================================


class CSVHandlerTests(unittest.TestCase):
    """Tests for the CSV parsing and validation module."""

    def test_generate_template_returns_valid_csv(self):
        """Template can be parsed by the CSV reader."""
        template = generate_template()
        reader = csv.DictReader(io.StringIO(template))
        self.assertEqual(reader.fieldnames, [
            "classroom_name", "student_id", "student_name",
        ])

    def test_parse_valid_csv(self):
        """A valid CSV parses without errors."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,123456,Alice\n"
            "Grade 7A,234567,Bob\n"
        )
        result = parse_and_validate(csv_content)
        self.assertTrue(result["valid"])
        self.assertEqual(result["classroom_name"], "Grade 7A")
        self.assertEqual(len(result["students"]), 2)
        self.assertEqual(result["students"][0]["student_id"], "123456")
        self.assertEqual(result["students"][1]["student_name"], "Bob")

    def test_parse_with_utf8_bom(self):
        """BOM is stripped and CSV still parses."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,123456,Alice\n"
        ).encode("utf-8")
        bom_csv = b"\xef\xbb\xbf" + csv_content
        result = parse_and_validate(bom_csv)
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["students"]), 1)

    def test_parse_with_windows_line_endings(self):
        """Windows CRLF line endings are handled."""
        csv_content = "classroom_name,student_id,student_name\r\nGrade 7A,123456,Alice\r\n"
        result = parse_and_validate(csv_content)
        self.assertTrue(result["valid"])

    def test_rejects_missing_column(self):
        """CSV missing required columns is invalid."""
        csv_content = "student_id,student_name\n123456,Alice\n"
        result = parse_and_validate(csv_content)
        self.assertFalse(result["valid"])
        self.assertTrue(any("classroom_name" in e for e in result["errors"]))

    def test_rejects_short_student_id(self):
        """Student IDs must be exactly 6 digits."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,12345,Alice\n"
        )
        result = parse_and_validate(csv_content)
        self.assertFalse(result["valid"])
        self.assertTrue(any("6 digits" in e for e in result["errors"]))

    def test_rejects_long_student_id(self):
        """Student IDs must be exactly 6 digits."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,1234567,Alice\n"
        )
        result = parse_and_validate(csv_content)
        self.assertFalse(result["valid"])

    def test_rejects_non_numeric_student_id(self):
        """Student IDs must be numeric."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,ABCDEF,Alice\n"
        )
        result = parse_and_validate(csv_content)
        self.assertFalse(result["valid"])

    def test_rejects_duplicate_student_ids(self):
        """Duplicate student IDs in the same file are rejected."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,123456,Alice\n"
            "Grade 7A,123456,Bob\n"
        )
        result = parse_and_validate(csv_content)
        self.assertFalse(result["valid"])
        self.assertTrue(any("duplicated" in e for e in result["errors"]))

    def test_rejects_mismatched_classroom_names(self):
        """Different classroom names in the same file are rejected."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,123456,Alice\n"
            "Grade 7B,234567,Bob\n"
        )
        result = parse_and_validate(csv_content)
        self.assertFalse(result["valid"])
        self.assertTrue(any("does not match" in e for e in result["errors"]))

    def test_rejects_existing_classroom_name(self):
        """Import with an existing classroom name is rejected."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,123456,Alice\n"
        )
        result = parse_and_validate(
            csv_content, existing_classroom_names={"Grade 7A"}
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("already exists" in e for e in result["errors"]))

    def test_rejects_empty_csv(self):
        """Empty CSV is invalid."""
        csv_content = ""
        result = parse_and_validate(csv_content)
        self.assertFalse(result["valid"])

    def test_rejects_blank_rows_only(self):
        """CSV with only blank rows is invalid."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "\n"
            "\n"
        )
        result = parse_and_validate(csv_content)
        self.assertFalse(result["valid"])

    def test_blank_row_in_data_is_skipped(self):
        """Blank rows between data are skipped; students still parsed."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,123456,Alice\n"
            "\n"
            "Grade 7A,234567,Bob\n"
        )
        result = parse_and_validate(csv_content)
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["students"]), 2)
        self.assertEqual(result["students"][0]["student_id"], "123456")
        self.assertEqual(result["students"][1]["student_id"], "234567")

    def test_missing_student_id_field(self):
        """Missing student_id in a row is an error."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,,Alice\n"
        )
        result = parse_and_validate(csv_content)
        self.assertFalse(result["valid"])

    def test_missing_student_name_field(self):
        """Missing student_name in a row is an error."""
        csv_content = (
            "classroom_name,student_id,student_name\n"
            "Grade 7A,123456,\n"
        )
        result = parse_and_validate(csv_content)
        self.assertFalse(result["valid"])

    def test_quoted_fields_handled(self):
        """Quoted fields with commas are parsed correctly."""
        csv_content = (
            'classroom_name,student_id,student_name\n'
            'Grade 7A,123456,"Smith, Alice"\n'
        )
        result = parse_and_validate(csv_content)
        self.assertTrue(result["valid"])
        self.assertEqual(result["students"][0]["student_name"], "Smith, Alice")

    def test_bytes_input(self):
        """Raw bytes input is decoded and parsed."""
        csv_content = b"classroom_name,student_id,student_name\nGrade 7A,123456,Alice\n"
        result = parse_and_validate(csv_content)
        self.assertTrue(result["valid"])

    def test_export_classroom_csv_roundtrip(self):
        """Export and re-import produces valid data."""
        students = [
            {"name": "Alice", "student_identifier": "123456"},
            {"name": "Bob", "student_identifier": "234567"},
        ]
        exported = export_classroom_csv("Grade 7A", students)
        result = parse_and_validate(exported)
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["students"]), 2)

    def test_export_csv_with_empty_student_id(self):
        """Export handles students without student_identifier."""
        students = [
            {"name": "Alice", "student_identifier": None},
        ]
        exported = export_classroom_csv("Grade 7A", students)
        self.assertIn("Grade 7A", exported)
        self.assertIn("Alice", exported)


# ============================================================
# Database import tests (with database)
# ============================================================


class ClassroomImportTests(unittest.TestCase):
    """Tests for database import_classroom and related methods."""

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = AssessFlowDatabase(
            Path(self.temporary_directory.name) / "assessflow.sqlite3"
        )
        self.database.initialize()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_import_classroom_creates_classroom(self):
        """import_classroom creates the classroom record."""
        students = [{"student_id": "123456", "student_name": "Alice"}]
        classroom_id = self.database.import_classroom("Grade 7A", students)
        classroom = self.database.get_classroom(classroom_id)
        self.assertIsNotNone(classroom)
        self.assertEqual(classroom["name"], "Grade 7A")

    def test_import_classroom_creates_students(self):
        """import_classroom creates all student records."""
        students = [
            {"student_id": "123456", "student_name": "Alice"},
            {"student_id": "234567", "student_name": "Bob"},
        ]
        classroom_id = self.database.import_classroom("Grade 7A", students)
        result = self.database.get_classroom_students(classroom_id)
        self.assertEqual(len(result), 2)
        names = {s["name"] for s in result}
        self.assertEqual(names, {"Alice", "Bob"})

    def test_import_classroom_sets_student_identifiers(self):
        """import_classroom assigns the correct student_identifier."""
        students = [{"student_id": "123456", "student_name": "Alice"}]
        classroom_id = self.database.import_classroom("Grade 7A", students)
        result = self.database.get_classroom_students(classroom_id)
        self.assertEqual(result[0]["student_identifier"], "123456")

    def test_import_classroom_rejects_duplicate_name(self):
        """import_classroom raises ValueError for duplicate names."""
        students = [{"student_id": "123456", "student_name": "Alice"}]
        self.database.import_classroom("Grade 7A", students)
        with self.assertRaises(ValueError):
            self.database.import_classroom("Grade 7A", students)

    def test_import_classroom_empty_student_list(self):
        """import_classroom creates a classroom with zero students."""
        classroom_id = self.database.import_classroom("Grade 7A", [])
        students = self.database.get_classroom_students(classroom_id)
        self.assertEqual(len(students), 0)

    def test_import_classroom_with_many_students(self):
        """import_classroom handles a large batch of students."""
        students = [
            {"student_id": f"{i:06d}", "student_name": f"Student {i}"}
            for i in range(1, 51)
        ]
        classroom_id = self.database.import_classroom("Grade 7A", students)
        result = self.database.get_classroom_students(classroom_id)
        self.assertEqual(len(result), 50)

    def test_get_classroom_returns_none_for_missing(self):
        """get_classroom returns None for nonexistent ID."""
        self.assertIsNone(self.database.get_classroom(999))

    def test_get_classroom_by_name_returns_none_for_missing(self):
        """get_classroom_by_name returns None for nonexistent name."""
        self.assertIsNone(self.database.get_classroom_by_name("No such class"))

    def test_get_classroom_by_name_returns_classroom(self):
        """get_classroom_by_name returns the correct classroom."""
        self.database.create_classroom("Grade 7A")
        result = self.database.get_classroom_by_name("Grade 7A")
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Grade 7A")

    def test_same_student_id_in_different_classrooms(self):
        """Same student_id can exist in different classrooms."""
        students = [{"student_id": "123456", "student_name": "Alice"}]
        self.database.import_classroom("Grade 7A", students)
        self.database.import_classroom("Grade 7B", students)
        # Both classrooms should exist with the same student_id
        c1 = self.database.get_classroom_by_name("Grade 7A")
        c2 = self.database.get_classroom_by_name("Grade 7B")
        s1 = self.database.get_classroom_students(c1["id"])
        s2 = self.database.get_classroom_students(c2["id"])
        self.assertEqual(s1[0]["student_identifier"], "123456")
        self.assertEqual(s2[0]["student_identifier"], "123456")

    def test_duplicate_student_id_in_same_classroom_rejected(self):
        """Database rejects duplicate student_id within the same classroom."""
        with self.assertRaises(Exception):
            with self.database._connect() as connection:
                classroom_id = self.database.import_classroom(
                    "Grade 7A",
                    [{"student_id": "123456", "student_name": "Alice"}],
                )
                # Try to insert duplicate
                connection.execute(
                    """INSERT INTO students
                       (classroom_id, name, student_identifier, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (classroom_id, "Bob", "123456", "2026-01-01 00:00:00"),
                )


if __name__ == "__main__":
    unittest.main()
