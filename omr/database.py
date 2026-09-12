"""SQLite persistence for AssessFlow classrooms and grading results."""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


class AssessFlowDatabase:
    """Provide the local database operations used by future app layers."""

    def __init__(self, database_file):
        self.database_file = Path(database_file)

    def initialize(self):
        """Create the schema if this local database has not been initialized."""

        self.database_file.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS classrooms (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY,
                    classroom_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    student_identifier TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(classroom_id, student_identifier),
                    FOREIGN KEY (classroom_id) REFERENCES classrooms(id)
                );

                CREATE TABLE IF NOT EXISTS assessments (
                    id INTEGER PRIMARY KEY,
                    classroom_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    question_count INTEGER NOT NULL CHECK(question_count > 0),
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (classroom_id) REFERENCES classrooms(id)
                );

                CREATE TABLE IF NOT EXISTS assessment_questions (
                    assessment_id INTEGER NOT NULL,
                    question_number INTEGER NOT NULL CHECK(question_number > 0),
                    correct_answer TEXT NOT NULL,
                    PRIMARY KEY (assessment_id, question_number),
                    FOREIGN KEY (assessment_id) REFERENCES assessments(id)
                );

                CREATE TABLE IF NOT EXISTS grading_attempts (
                    id INTEGER PRIMARY KEY,
                    assessment_id INTEGER NOT NULL,
                    student_id INTEGER,
                    source_file TEXT,
                    score INTEGER NOT NULL,
                    percentage REAL NOT NULL,
                    correct_count INTEGER NOT NULL,
                    wrong_count INTEGER NOT NULL,
                    blank_count INTEGER NOT NULL,
                    multiple_count INTEGER NOT NULL,
                    graded_at TEXT NOT NULL,
                    FOREIGN KEY (assessment_id) REFERENCES assessments(id),
                    FOREIGN KEY (student_id) REFERENCES students(id)
                );

                CREATE TABLE IF NOT EXISTS grading_question_results (
                    grading_attempt_id INTEGER NOT NULL,
                    question_number INTEGER NOT NULL CHECK(question_number > 0),
                    student_answer TEXT,
                    correct_answer TEXT,
                    result TEXT NOT NULL,
                    PRIMARY KEY (grading_attempt_id, question_number),
                    FOREIGN KEY (grading_attempt_id) REFERENCES grading_attempts(id)
                );
            """)

    def create_classroom(self, name):
        """Create a classroom and return its ID."""

        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO classrooms (name, created_at) VALUES (?, ?)",
                (name, self._now()),
            )
            return cursor.lastrowid

    def create_student(self, classroom_id, name, student_identifier=None):
        """Create a student."""

        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO students
                   (classroom_id, name, student_identifier, created_at)
                   VALUES (?, ?, ?, ?)""",
                (classroom_id, name, student_identifier, self._now()),
            )
            return cursor.lastrowid

    def find_student_by_identifier(self, classroom_id, student_identifier):
        """Find a student by classroom and Student ID OMR identifier.

        Returns the student row as a dict, or None if not found.
        """

        with self._connect() as connection:
            row = connection.execute(
                """SELECT id, classroom_id, name, student_identifier, created_at
                   FROM students
                   WHERE classroom_id = ? AND student_identifier = ?""",
                (classroom_id, student_identifier),
            ).fetchone()

            if row is None:
                return None

            return dict(row)

    def get_assessment(self, assessment_id):
        """Get an assessment by ID.

        Returns the assessment row as a dict, or None if not found.
        """

        with self._connect() as connection:
            row = connection.execute(
                """SELECT id, classroom_id, name, question_count, created_at
                   FROM assessments
                   WHERE id = ?""",
                (assessment_id,),
            ).fetchone()

            if row is None:
                return None

            return dict(row)

    def get_assessment_answer_key(self, assessment_id):
        """Get the answer key for an assessment as {question_number: answer}.

        Returns a dict mapping question numbers to correct answers,
        or None if the assessment does not exist.
        """

        with self._connect() as connection:
            rows = connection.execute(
                """SELECT question_number, correct_answer
                   FROM assessment_questions
                   WHERE assessment_id = ?
                   ORDER BY question_number""",
                (assessment_id,),
            ).fetchall()

            if not rows:
                return None

            return {row["question_number"]: row["correct_answer"]
                    for row in rows}

    def create_assessment(self, classroom_id, name, answer_key):
        """Create an assessment and persist its answer key by question."""

        if not answer_key:
            raise ValueError("An assessment needs at least one answer-key entry.")

        question_numbers = sorted(answer_key)
        expected_numbers = list(range(1, len(question_numbers) + 1))

        if question_numbers != expected_numbers:
            raise ValueError("Answer-key question numbers must start at 1 and be consecutive.")

        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO assessments
                   (classroom_id, name, question_count, created_at)
                   VALUES (?, ?, ?, ?)""",
                (classroom_id, name, len(answer_key), self._now()),
            )
            assessment_id = cursor.lastrowid
            connection.executemany(
                """INSERT INTO assessment_questions
                   (assessment_id, question_number, correct_answer)
                   VALUES (?, ?, ?)""",
                [
                    (assessment_id, question_number, answer_key[question_number])
                    for question_number in question_numbers
                ],
            )
            return assessment_id

    def save_grading_result(self, assessment_id, grading_result, student_id=None):
        """Persist one structured grading result and all of its question results."""

        questions = grading_result["questions"]

        with self._connect() as connection:
            assessment = connection.execute(
                "SELECT question_count FROM assessments WHERE id = ?",
                (assessment_id,),
            ).fetchone()

            if assessment is None:
                raise ValueError(f"Assessment {assessment_id} does not exist.")

            if assessment["question_count"] != grading_result["total_questions"]:
                raise ValueError("Grading result question count does not match the assessment.")

            if len(questions) != grading_result["total_questions"]:
                raise ValueError("Grading result is missing question details.")

            if student_id is not None:
                student = connection.execute(
                    "SELECT classroom_id FROM students WHERE id = ?",
                    (student_id,),
                ).fetchone()
                classroom = connection.execute(
                    "SELECT classroom_id FROM assessments WHERE id = ?",
                    (assessment_id,),
                ).fetchone()
                if student is None or student["classroom_id"] != classroom["classroom_id"]:
                    raise ValueError("Student must belong to the assessment classroom.")

            cursor = connection.execute(
                """INSERT INTO grading_attempts (
                    assessment_id, student_id, source_file, score, percentage,
                    correct_count, wrong_count, blank_count, multiple_count, graded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    assessment_id,
                    student_id,
                    grading_result["source_file"],
                    grading_result["score"],
                    grading_result["percentage"],
                    grading_result["correct"],
                    grading_result["wrong"],
                    grading_result["blank"],
                    grading_result["multiple"],
                    self._now(),
                ),
            )
            attempt_id = cursor.lastrowid
            connection.executemany(
                """INSERT INTO grading_question_results (
                    grading_attempt_id, question_number, student_answer,
                    correct_answer, result
                ) VALUES (?, ?, ?, ?, ?)""",
                [
                    (
                        attempt_id,
                        question["question_number"],
                        question["student_answer"],
                        question["correct_answer"],
                        question["result"],
                    )
                    for question in questions
                ],
            )
            return attempt_id

    def get_grading_result(self, attempt_id):
        """Read a saved grading attempt in the same shape as the grading result."""

        with self._connect() as connection:
            attempt = connection.execute(
                """SELECT grading_attempts.*, assessments.question_count
                   FROM grading_attempts
                   JOIN assessments ON assessments.id = grading_attempts.assessment_id
                   WHERE grading_attempts.id = ?""",
                (attempt_id,),
            ).fetchone()

            if attempt is None:
                return None

            questions = connection.execute(
                """SELECT question_number, student_answer, correct_answer, result
                   FROM grading_question_results
                   WHERE grading_attempt_id = ?
                   ORDER BY question_number""",
                (attempt_id,),
            ).fetchall()

            return {
                "id": attempt["id"],
                "assessment_id": attempt["assessment_id"],
                "student_id": attempt["student_id"],
                "source_file": attempt["source_file"],
                "total_questions": attempt["question_count"],
                "score": attempt["score"],
                "percentage": attempt["percentage"],
                "correct": attempt["correct_count"],
                "wrong": attempt["wrong_count"],
                "blank": attempt["blank_count"],
                "multiple": attempt["multiple_count"],
                "graded_at": attempt["graded_at"],
                "questions": [dict(question) for question in questions],
            }

    def get_classroom(self, classroom_id):
        """Get a classroom by ID. Returns a dict or None."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, created_at FROM classrooms WHERE id = ?",
                (classroom_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_classroom_by_name(self, name):
        """Get a classroom by name. Returns a dict or None."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, created_at FROM classrooms WHERE name = ?",
                (name,),
            ).fetchone()
            return dict(row) if row else None

    def get_classroom_students(self, classroom_id):
        """Get all students in a classroom, ordered by name."""

        with self._connect() as connection:
            rows = connection.execute(
                """SELECT id, classroom_id, name, student_identifier, created_at
                   FROM students
                   WHERE classroom_id = ?
                   ORDER BY name""",
                (classroom_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def import_classroom(self, classroom_name, students):
        """Atomically create a classroom and all its students.

        Args:
            classroom_name: The classroom name (must be unique).
            students: List of dicts with 'student_id' and 'student_name' keys.

        Returns:
            The new classroom ID.

        Raises:
            ValueError: If the classroom name already exists.
        """
        existing = self.get_classroom_by_name(classroom_name)
        if existing is not None:
            raise ValueError(
                f"Classroom '{classroom_name}' already exists."
            )

        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO classrooms (name, created_at) VALUES (?, ?)",
                (classroom_name, self._now()),
            )
            classroom_id = cursor.lastrowid

            connection.executemany(
                """INSERT INTO students
                   (classroom_id, name, student_identifier, created_at)
                   VALUES (?, ?, ?, ?)""",
                [
                    (classroom_id, s["student_name"], s["student_id"], self._now())
                    for s in students
                ],
            )

            return classroom_id

    # ------------------------------------------------------------------
    # Results export queries
    # ------------------------------------------------------------------

    _EXPORT_QUERY = """
        SELECT
            c.name AS classroom,
            s.student_identifier AS student_id,
            s.name AS student_name,
            a.name AS assessment,
            a.question_count AS question_count,
            ga.score AS score,
            ga.percentage AS percentage,
            ga.wrong_count AS wrong,
            ga.blank_count AS blank,
            ga.multiple_count AS multiple,
            SUBSTR(ga.graded_at, 1, 10) AS date
        FROM grading_attempts ga
        JOIN assessments a ON a.id = ga.assessment_id
        JOIN classrooms c ON c.id = a.classroom_id
        JOIN students s ON s.id = ga.student_id
    """

    def get_assessment_export_rows(self, assessment_id):
        """Return export-ready rows for one assessment."""

        with self._connect() as connection:
            rows = connection.execute(
                self._EXPORT_QUERY + " WHERE ga.assessment_id = ? ORDER BY s.name",
                (assessment_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_classroom_export_rows(self, classroom_id):
        """Return export-ready rows for all assessments in a classroom."""

        with self._connect() as connection:
            rows = connection.execute(
                self._EXPORT_QUERY + " WHERE a.classroom_id = ? ORDER BY a.name, s.name",
                (classroom_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_student_export_rows(self, classroom_id, student_id):
        """Return export-ready rows for one student in one classroom."""

        with self._connect() as connection:
            rows = connection.execute(
                self._EXPORT_QUERY
                + " WHERE ga.student_id = ? AND a.classroom_id = ? ORDER BY ga.graded_at",
                (student_id, classroom_id),
            ).fetchall()
            return [dict(row) for row in rows]

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_file)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()
