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


# ============================================================
# Import workflow integration tests (Flask test client)
# ============================================================


class ImportWorkflowTests(unittest.TestCase):
    """Tests for the full upload → preview → confirm workflow."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        from web import create_app

        self.temporary_directory = tempfile.TemporaryDirectory()
        db_path = Path(self.temporary_directory.name) / "test.sqlite3"
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "DATABASE": db_path,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _upload_csv(self, csv_content, confirm=None):
        """Upload a CSV and optionally confirm the import."""
        import io
        data = {}
        if csv_content is not None:
            data["csv_file"] = (io.BytesIO(csv_content.encode("utf-8")), "test.csv")
        if confirm:
            data["confirm"] = "yes"
        return self.client.post(
            "/classrooms/import",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )

    def test_upload_and_preview(self):
        """A valid CSV shows the preview page."""
        csv = "classroom_name,student_id,student_name\nPreview Test,123456,Alice\n"
        resp = self._upload_csv(csv)
        html = resp.data.decode()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Preview Import", html)
        self.assertIn("Alice", html)
        self.assertIn("Confirm Import", html)

    def test_confirm_creates_classroom(self):
        """Confirming a valid preview creates the classroom."""
        csv = (
            "classroom_name,student_id,student_name\n"
            "Confirm Test,123456,Alice\n"
            "Confirm Test,234567,Bob\n"
        )
        # Step 1: upload → preview
        resp = self._upload_csv(csv)
        self.assertIn("Preview Import", resp.data.decode())

        # Step 2: confirm
        resp = self._upload_csv(csv, confirm="yes")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/classrooms/", resp.headers["Location"])

        # Verify classroom exists
        with self.app.db._connect() as conn:
            row = conn.execute(
                "SELECT id, name FROM classrooms WHERE name = 'Confirm Test'"
            ).fetchone()
            self.assertIsNotNone(row)

    def test_confirm_creates_all_students(self):
        """Confirming creates all students from the CSV."""
        csv = (
            "classroom_name,student_id,student_name\n"
            "Students Test,123456,Alice\n"
            "Students Test,234567,Bob\n"
            "Students Test,345678,Charlie\n"
        )
        self._upload_csv(csv)
        self._upload_csv(csv, confirm="yes")

        with self.app.db._connect() as conn:
            classroom = conn.execute(
                "SELECT id FROM classrooms WHERE name = 'Students Test'"
            ).fetchone()
            self.assertIsNotNone(classroom)
            students = conn.execute(
                "SELECT name FROM students WHERE classroom_id = ?",
                (classroom["id"],),
            ).fetchall()
            self.assertEqual(len(students), 3)

    def test_student_id_leading_zeros_preserved(self):
        """Student ID 012345 is preserved as text, not converted to integer."""
        csv = (
            "classroom_name,student_id,student_name\n"
            "Leading Zero Test,012345,Fhebe\n"
        )
        self._upload_csv(csv)
        self._upload_csv(csv, confirm="yes")

        with self.app.db._connect() as conn:
            classroom = conn.execute(
                "SELECT id FROM classrooms WHERE name = 'Leading Zero Test'"
            ).fetchone()
            self.assertIsNotNone(classroom)
            student = conn.execute(
                "SELECT student_identifier FROM students WHERE classroom_id = ?",
                (classroom["id"],),
            ).fetchone()
            self.assertEqual(student["student_identifier"], "012345")

    def test_no_file_shows_error(self):
        """Submitting without a file shows an error."""
        resp = self._upload_csv(None)
        html = resp.data.decode()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Please select a CSV file", html)

    def test_confirm_without_session_data_shows_error(self):
        """Confirming without a prior preview session shows an error."""
        resp = self._upload_csv(None, confirm="yes")
        html = resp.data.decode()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Please select a CSV file", html)

    def test_validation_errors_still_shown(self):
        """Invalid CSV still shows validation errors on preview."""
        csv = "student_id,student_name\n123456,Alice\n"
        resp = self._upload_csv(csv)
        html = resp.data.decode()
        self.assertIn("Validation Errors", html)

    def test_existing_classroom_rejected(self):
        """Importing a CSV with an existing classroom name shows error."""
        with self.app.db._connect() as conn:
            conn.execute(
                "INSERT INTO classrooms (name, created_at) VALUES (?, ?)",
                ("Existing Class", "2026-01-01 00:00:00"),
            )
            conn.commit()
        csv = (
            "classroom_name,student_id,student_name\n"
            "Existing Class,123456,Alice\n"
        )
        resp = self._upload_csv(csv)
        html = resp.data.decode()
        self.assertIn("already exists", html)

    def test_full_export_edit_import_roundtrip(self):
        """Export → edit name → import creates a new classroom."""
        # Create original classroom via import
        csv = (
            "classroom_name,student_id,student_name\n"
            "Roundtrip Original,123456,Alice\n"
            "Roundtrip Original,234567,Bob\n"
        )
        self._upload_csv(csv)
        resp = self._upload_csv(csv, confirm="yes")
        self.assertEqual(resp.status_code, 302)

        # Find the classroom ID
        with self.app.db._connect() as conn:
            row = conn.execute(
                "SELECT id FROM classrooms WHERE name = 'Roundtrip Original'"
            ).fetchone()
            classroom_id = row["id"]

        # Export it
        resp = self.client.get(f"/classrooms/{classroom_id}/export")
        exported = resp.data.decode()
        self.assertIn("Roundtrip Original", exported)

        # Edit the name in the exported CSV
        edited = exported.replace("Roundtrip Original", "Roundtrip New Name")
        # Import the edited CSV
        import io
        data = {
            "csv_file": (io.BytesIO(edited.encode("utf-8")), "edited.csv"),
        }
        resp = self.client.post(
            "/classrooms/import",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        self.assertIn("Preview Import", resp.data.decode())

        # Confirm without re-uploading file (uses session data — the bug scenario)
        resp = self.client.post(
            "/classrooms/import",
            data={"confirm": "yes"},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/classrooms/", resp.headers["Location"])


if __name__ == "__main__":
    unittest.main()
