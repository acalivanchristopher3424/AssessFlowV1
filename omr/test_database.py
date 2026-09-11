from pathlib import Path
import tempfile
import unittest

from omr.database import AssessFlowDatabase
from omr.grade_answers import create_grading_result, load_answer_key
from omr.layout import QUESTIONS


class AssessFlowDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = AssessFlowDatabase(Path(self.temporary_directory.name) / "assessflow.sqlite3")
        self.database.initialize()
        self.classroom_id = self.database.create_classroom("Grade 7A")
        self.student_id = self.database.create_student(self.classroom_id, "Ada Lovelace", "S-001")
        self.assessment_id = self.database.create_assessment(
            self.classroom_id, "Science Quiz", load_answer_key()
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_saves_and_reads_all_fifty_question_results(self):
        answers = {number: "A" for number in range(1, QUESTIONS + 1)}
        result = create_grading_result(answers, load_answer_key(), source_file="samples/generated.png")
        attempt_id = self.database.save_grading_result(self.assessment_id, result, self.student_id)
        saved = self.database.get_grading_result(attempt_id)

        self.assertEqual(saved["student_id"], self.student_id)
        self.assertEqual(saved["total_questions"], 50)
        self.assertEqual(len(saved["questions"]), 50)
        self.assertEqual(saved["questions"][0]["question_number"], 1)
        self.assertEqual(saved["questions"][-1]["question_number"], 50)

    def test_rejects_a_student_from_another_classroom(self):
        other_classroom = self.database.create_classroom("Grade 7B")
        other_student = self.database.create_student(other_classroom, "Grace Hopper")
        result = create_grading_result({}, load_answer_key())

        with self.assertRaisesRegex(ValueError, "assessment classroom"):
            self.database.save_grading_result(self.assessment_id, result, other_student)

    def test_find_student_by_identifier_returns_correct_student(self):
        """find_student_by_identifier returns the correct student in the classroom."""
        student = self.database.find_student_by_identifier(self.classroom_id, "S-001")
        self.assertIsNotNone(student)
        self.assertEqual(student["name"], "Ada Lovelace")
        self.assertEqual(student["student_identifier"], "S-001")
        self.assertEqual(student["classroom_id"], self.classroom_id)

    def test_find_student_by_identifier_returns_none_for_unknown(self):
        """find_student_by_identifier returns None for unknown identifier."""
        result = self.database.find_student_by_identifier(self.classroom_id, "999999")
        self.assertIsNone(result)

    def test_find_student_by_identifier_is_classroom_scoped(self):
        """Same student_identifier in different classroom returns different student."""
        other_classroom = self.database.create_classroom("Grade 7B")
        other_student = self.database.create_student(
            other_classroom, "Bob Smith", "S-001"
        )

        found_in_a = self.database.find_student_by_identifier(self.classroom_id, "S-001")
        found_in_b = self.database.find_student_by_identifier(other_classroom, "S-001")

        self.assertIsNotNone(found_in_a)
        self.assertIsNotNone(found_in_b)
        self.assertEqual(found_in_a["name"], "Ada Lovelace")
        self.assertEqual(found_in_b["name"], "Bob Smith")


class QuestionCountSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = AssessFlowDatabase(Path(self.temporary_directory.name) / "assessflow.sqlite3")
        self.database.initialize()
        self.classroom_id = self.database.create_classroom("Grade 7A")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _get_question_count(self, assessment_id):
        assessment = self.database.get_assessment(assessment_id)
        return assessment["question_count"]

    def _simulate_edit_answer_key(self, assessment_id, new_answer_key):
        """Simulate what web/routes/assessments.py edit_answer_key() does."""
        with self.database._connect() as connection:
            connection.execute(
                "DELETE FROM assessment_questions WHERE assessment_id = ?",
                (assessment_id,),
            )
            connection.executemany(
                "INSERT INTO assessment_questions (assessment_id, question_number, correct_answer) VALUES (?, ?, ?)",
                [(assessment_id, q, new_answer_key[q]) for q in sorted(new_answer_key)],
            )
            connection.execute(
                "UPDATE assessments SET question_count = ? WHERE id = ?",
                (len(new_answer_key), assessment_id),
            )

    def test_create_20_question_assessment_sets_question_count_20(self):
        """Creating with 20 answers sets question_count = 20."""
        answer_key = {i: "A" for i in range(1, 21)}
        assessment_id = self.database.create_assessment(self.classroom_id, "Quiz 20", answer_key)
        self.assertEqual(self._get_question_count(assessment_id), 20)

    def test_create_50_question_assessment_sets_question_count_50(self):
        """Creating with 50 answers sets question_count = 50."""
        answer_key = {i: "A" for i in range(1, 51)}
        assessment_id = self.database.create_assessment(self.classroom_id, "Quiz 50", answer_key)
        self.assertEqual(self._get_question_count(assessment_id), 50)

    def test_edit_from_21_to_20_updates_question_count(self):
        """Editing 21 answers down to 20 changes question_count from 21 to 20."""
        answer_key_21 = {i: "A" for i in range(1, 22)}
        assessment_id = self.database.create_assessment(self.classroom_id, "Quiz", answer_key_21)
        self.assertEqual(self._get_question_count(assessment_id), 21)

        answer_key_20 = {i: "A" for i in range(1, 21)}
        self._simulate_edit_answer_key(assessment_id, answer_key_20)
        self.assertEqual(self._get_question_count(assessment_id), 20)

    def test_edit_answer_key_persists_new_answers(self):
        """Editing the answer key stores the new correct answers."""
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {1: "A", 2: "B"}
        )
        new_key = {1: "C", 2: "D", 3: "E"}
        self._simulate_edit_answer_key(assessment_id, new_key)

        with self.database._connect() as connection:
            questions = connection.execute(
                "SELECT question_number, correct_answer FROM assessment_questions WHERE assessment_id = ? ORDER BY question_number",
                (assessment_id,),
            ).fetchall()
        stored = {q["question_number"]: q["correct_answer"] for q in questions}
        self.assertEqual(stored, {1: "C", 2: "D", 3: "E"})
        self.assertEqual(self._get_question_count(assessment_id), 3)

    def test_grading_20_question_assessment_ignores_q21_to_q50(self):
        """Grading a 20-question assessment does not include Q21-Q50."""
        student_id = self.database.create_student(self.classroom_id, "Test Student", "T-001")
        answer_key = {i: "A" for i in range(1, 51)}
        assessment_id = self.database.create_assessment(self.classroom_id, "Quiz 20", {i: "A" for i in range(1, 21)})

        student_answers = {i: "A" for i in range(1, 21)}
        result = create_grading_result(student_answers, answer_key, question_count=20)
        attempt_id = self.database.save_grading_result(assessment_id, result, student_id)
        saved = self.database.get_grading_result(attempt_id)

        self.assertEqual(saved["total_questions"], 20)
        self.assertEqual(saved["score"], 20)
        self.assertEqual(len(saved["questions"]), 20)
        self.assertEqual(saved["questions"][-1]["question_number"], 20)

    def test_grading_20_question_percentage_out_of_20(self):
        """Percentage for 20-question assessment is calculated out of 20."""
        student_id = self.database.create_student(self.classroom_id, "Test Student", "T-002")
        answer_key = {i: "A" for i in range(1, 51)}
        assessment_id = self.database.create_assessment(self.classroom_id, "Quiz 20", {i: "A" for i in range(1, 21)})

        student_answers = {i: "A" for i in range(1, 16)}
        for q in range(16, 21):
            student_answers[q] = "B"
        result = create_grading_result(student_answers, answer_key, question_count=20)
        attempt_id = self.database.save_grading_result(assessment_id, result, student_id)
        saved = self.database.get_grading_result(attempt_id)

        self.assertEqual(saved["score"], 15)
        self.assertEqual(saved["percentage"], 75.0)


class ResultsDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = AssessFlowDatabase(Path(self.temporary_directory.name) / "assessflow.sqlite3")
        self.database.initialize()
        self.classroom_id = self.database.create_classroom("Grade 7A")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _get_stats(self, assessment_id):
        """Get aggregate stats the same way the results route does."""
        with self.database._connect() as connection:
            stats = connection.execute(
                """SELECT
                      COUNT(*) as students_graded,
                      ROUND(AVG(score), 1) as avg_score,
                      ROUND(AVG(percentage), 1) as avg_percentage
                   FROM grading_attempts
                   WHERE assessment_id = ?""",
                (assessment_id,),
            ).fetchone()
            return dict(stats)

    def test_empty_results_returns_zero_stats(self):
        """No grading results means zero stats."""
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {1: "A"}
        )
        stats = self._get_stats(assessment_id)
        self.assertEqual(stats["students_graded"], 0)
        self.assertIsNone(stats["avg_score"])
        self.assertIsNone(stats["avg_percentage"])

    def test_one_graded_student(self):
        """One student graded shows correct stats."""
        student_id = self.database.create_student(self.classroom_id, "Ada", "S-001")
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}
        student_answers = {i: "A" for i in range(1, 21)}
        result = create_grading_result(student_answers, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result, student_id)

        stats = self._get_stats(assessment_id)
        self.assertEqual(stats["students_graded"], 1)
        self.assertEqual(stats["avg_score"], 20.0)
        self.assertEqual(stats["avg_percentage"], 100.0)

    def test_multiple_graded_students_average(self):
        """Multiple students produce correct averages."""
        student1 = self.database.create_student(self.classroom_id, "Ada", "S-001")
        student2 = self.database.create_student(self.classroom_id, "Grace", "S-002")
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}

        # Student 1: 20/20
        result1 = create_grading_result({i: "A" for i in range(1, 21)}, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result1, student1)

        # Student 2: 10/20
        student_answers = {i: "A" for i in range(1, 11)}
        for q in range(11, 21):
            student_answers[q] = "B"
        result2 = create_grading_result(student_answers, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result2, student2)

        stats = self._get_stats(assessment_id)
        self.assertEqual(stats["students_graded"], 2)
        self.assertEqual(stats["avg_score"], 15.0)
        self.assertEqual(stats["avg_percentage"], 75.0)

    def test_50_question_assessment_average(self):
        """50-question assessment calculates average correctly."""
        student1 = self.database.create_student(self.classroom_id, "Ada", "S-001")
        student2 = self.database.create_student(self.classroom_id, "Grace", "S-002")
        answer_key = {i: "A" for i in range(1, 51)}
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz 50", answer_key
        )

        # Student 1: 50/50
        result1 = create_grading_result({i: "A" for i in range(1, 51)}, answer_key)
        self.database.save_grading_result(assessment_id, result1, student1)

        # Student 2: 40/50
        student_answers = {i: "A" for i in range(1, 41)}
        for q in range(41, 51):
            student_answers[q] = "B"
        result2 = create_grading_result(student_answers, answer_key)
        self.database.save_grading_result(assessment_id, result2, student2)

        stats = self._get_stats(assessment_id)
        self.assertEqual(stats["students_graded"], 2)
        self.assertEqual(stats["avg_score"], 45.0)
        self.assertEqual(stats["avg_percentage"], 90.0)

    def test_zero_score_included_in_average(self):
        """A student with 0/20 is included in the average calculation."""
        student1 = self.database.create_student(self.classroom_id, "Ada", "S-001")
        student2 = self.database.create_student(self.classroom_id, "Grace", "S-002")
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}

        # Student 1: 20/20
        result1 = create_grading_result({i: "A" for i in range(1, 21)}, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result1, student1)

        # Student 2: 0/20
        result2 = create_grading_result({}, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result2, student2)

        stats = self._get_stats(assessment_id)
        self.assertEqual(stats["students_graded"], 2)
        self.assertEqual(stats["avg_score"], 10.0)
        self.assertEqual(stats["avg_percentage"], 50.0)

    def test_classroom_results_query(self):
        """Classroom results query returns assessment summaries."""
        student1 = self.database.create_student(self.classroom_id, "Ada", "S-001")
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}
        result = create_grading_result({i: "A" for i in range(1, 21)}, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result, student1)

        with self.database._connect() as connection:
            assessments = connection.execute(
                """SELECT a.id, a.name, a.question_count,
                          (SELECT COUNT(*) FROM grading_attempts WHERE assessment_id = a.id) as students_graded,
                          (SELECT ROUND(AVG(score), 1) FROM grading_attempts WHERE assessment_id = a.id) as avg_score,
                          (SELECT ROUND(AVG(percentage), 1) FROM grading_attempts WHERE assessment_id = a.id) as avg_percentage
                   FROM assessments a
                   WHERE a.classroom_id = ?
                   ORDER BY a.name""",
                (self.classroom_id,),
            ).fetchall()

        self.assertEqual(len(assessments), 1)
        a = dict(assessments[0])
        self.assertEqual(a["name"], "Quiz")
        self.assertEqual(a["students_graded"], 1)
        self.assertEqual(a["avg_score"], 20.0)
        self.assertEqual(a["avg_percentage"], 100.0)


class AssessmentHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = AssessFlowDatabase(Path(self.temporary_directory.name) / "assessflow.sqlite3")
        self.database.initialize()
        self.classroom_id = self.database.create_classroom("Grade 7A")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _get_history(self, classroom_id=None):
        """Get assessment history the same way the route does."""
        with self.database._connect() as connection:
            if classroom_id:
                assessments = connection.execute(
                    """SELECT a.id, a.name, a.question_count, a.created_at,
                              c.name as classroom_name,
                              (SELECT COUNT(*) FROM grading_attempts WHERE assessment_id = a.id) as students_graded,
                              (SELECT ROUND(AVG(score), 1) FROM grading_attempts WHERE assessment_id = a.id) as avg_score,
                              (SELECT ROUND(AVG(percentage), 1) FROM grading_attempts WHERE assessment_id = a.id) as avg_percentage
                       FROM assessments a
                       JOIN classrooms c ON c.id = a.classroom_id
                       WHERE a.classroom_id = ?
                       ORDER BY a.created_at DESC""",
                    (classroom_id,),
                ).fetchall()
            else:
                assessments = connection.execute(
                    """SELECT a.id, a.name, a.question_count, a.created_at,
                              c.name as classroom_name,
                              (SELECT COUNT(*) FROM grading_attempts WHERE assessment_id = a.id) as students_graded,
                              (SELECT ROUND(AVG(score), 1) FROM grading_attempts WHERE assessment_id = a.id) as avg_score,
                              (SELECT ROUND(AVG(percentage), 1) FROM grading_attempts WHERE assessment_id = a.id) as avg_percentage
                       FROM assessments a
                       JOIN classrooms c ON c.id = a.classroom_id
                       ORDER BY a.created_at DESC"""
                ).fetchall()
            return [dict(a) for a in assessments]

    def test_no_assessments(self):
        """No assessments returns empty list."""
        history = self._get_history()
        self.assertEqual(len(history), 0)

    def test_one_assessment(self):
        """One assessment appears in history."""
        self.database.create_assessment(self.classroom_id, "Quiz", {i: "A" for i in range(1, 21)})
        history = self._get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["name"], "Quiz")
        self.assertEqual(history[0]["question_count"], 20)
        self.assertEqual(history[0]["classroom_name"], "Grade 7A")

    def test_multiple_assessments_most_recent_first(self):
        """Multiple assessments sorted most recent first."""
        self.database.create_assessment(self.classroom_id, "First", {1: "A"})
        self.database.create_assessment(self.classroom_id, "Second", {1: "A"})
        self.database.create_assessment(self.classroom_id, "Third", {1: "A"})
        history = self._get_history()
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["name"], "Third")
        self.assertEqual(history[1]["name"], "Second")
        self.assertEqual(history[2]["name"], "First")

    def test_classroom_filtering(self):
        """Filtering by classroom returns only that classroom's assessments."""
        classroom2 = self.database.create_classroom("Grade 7B")
        self.database.create_assessment(self.classroom_id, "Quiz A", {1: "A"})
        self.database.create_assessment(classroom2, "Quiz B", {1: "A"})
        history_a = self._get_history(classroom_id=self.classroom_id)
        history_b = self._get_history(classroom_id=classroom2)
        self.assertEqual(len(history_a), 1)
        self.assertEqual(history_a[0]["name"], "Quiz A")
        self.assertEqual(len(history_b), 1)
        self.assertEqual(history_b[0]["name"], "Quiz B")

    def test_correct_question_count(self):
        """Question count is displayed correctly."""
        self.database.create_assessment(self.classroom_id, "Quiz 10", {i: "A" for i in range(1, 11)})
        self.database.create_assessment(self.classroom_id, "Quiz 20", {i: "A" for i in range(1, 21)})
        self.database.create_assessment(self.classroom_id, "Quiz 50", {i: "A" for i in range(1, 51)})
        history = self._get_history()
        counts = {a["name"]: a["question_count"] for a in history}
        self.assertEqual(counts["Quiz 10"], 10)
        self.assertEqual(counts["Quiz 20"], 20)
        self.assertEqual(counts["Quiz 50"], 50)

    def test_assessment_with_no_graded_results(self):
        """Assessment with no graded results shows 0 students, None averages."""
        self.database.create_assessment(self.classroom_id, "Quiz", {i: "A" for i in range(1, 21)})
        history = self._get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["students_graded"], 0)
        self.assertIsNone(history[0]["avg_score"])
        self.assertIsNone(history[0]["avg_percentage"])

    def test_assessment_with_graded_results(self):
        """Assessment with graded results shows correct stats."""
        student = self.database.create_student(self.classroom_id, "Ada", "S-001")
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}
        result = create_grading_result({i: "A" for i in range(1, 21)}, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result, student)
        history = self._get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["students_graded"], 1)
        self.assertEqual(history[0]["avg_score"], 20.0)
        self.assertEqual(history[0]["avg_percentage"], 100.0)

    def test_average_score_multiple_students(self):
        """Average score is correct with multiple students."""
        student1 = self.database.create_student(self.classroom_id, "Ada", "S-001")
        student2 = self.database.create_student(self.classroom_id, "Grace", "S-002")
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}
        result1 = create_grading_result({i: "A" for i in range(1, 21)}, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result1, student1)
        result2 = create_grading_result({}, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result2, student2)
        history = self._get_history()
        self.assertEqual(history[0]["students_graded"], 2)
        self.assertEqual(history[0]["avg_score"], 10.0)
        self.assertEqual(history[0]["avg_percentage"], 50.0)

    def test_created_at_date_shown(self):
        """Assessment shows created_at date."""
        self.database.create_assessment(self.classroom_id, "Quiz", {1: "A"})
        history = self._get_history()
        self.assertIsNotNone(history[0]["created_at"])


class StudentPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = AssessFlowDatabase(Path(self.temporary_directory.name) / "assessflow.sqlite3")
        self.database.initialize()
        self.classroom_id = self.database.create_classroom("Grade 7A")
        self.student_id = self.database.create_student(self.classroom_id, "Alice", "S-001")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _get_student_performance(self, classroom_id, student_id):
        """Get student performance the same way the route does."""
        with self.database._connect() as connection:
            attempts = connection.execute(
                """SELECT ga.id, ga.score, ga.percentage, ga.correct_count, ga.wrong_count,
                          ga.blank_count, ga.multiple_count, ga.graded_at,
                          a.name as assessment_name, a.question_count
                   FROM grading_attempts ga
                   JOIN assessments a ON a.id = ga.assessment_id
                   WHERE ga.student_id = ? AND ga.assessment_id IN (
                       SELECT id FROM assessments WHERE classroom_id = ?
                   )
                   ORDER BY ga.graded_at DESC""",
                (student_id, classroom_id),
            ).fetchall()

            stats = connection.execute(
                """SELECT
                      COUNT(*) as assessments_taken,
                      ROUND(AVG(percentage), 1) as avg_percentage,
                      MAX(percentage) as highest_percentage,
                      MIN(percentage) as lowest_percentage
                   FROM grading_attempts
                   WHERE student_id = ? AND assessment_id IN (
                       SELECT id FROM assessments WHERE classroom_id = ?
                   )""",
                (student_id, classroom_id),
            ).fetchone()

        return [dict(a) for a in attempts], dict(stats) if stats else None

    def test_student_with_no_results(self):
        """Student with no graded assessments has empty attempts and 0 stats."""
        attempts, stats = self._get_student_performance(self.classroom_id, self.student_id)
        self.assertEqual(len(attempts), 0)
        self.assertEqual(stats["assessments_taken"], 0)
        self.assertIsNone(stats["avg_percentage"])
        self.assertIsNone(stats["highest_percentage"])
        self.assertIsNone(stats["lowest_percentage"])

    def test_student_with_one_result(self):
        """Student with one graded assessment shows correct data."""
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}
        result = create_grading_result({i: "A" for i in range(1, 21)}, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result, self.student_id)

        attempts, stats = self._get_student_performance(self.classroom_id, self.student_id)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["assessment_name"], "Quiz")
        self.assertEqual(attempts[0]["question_count"], 20)
        self.assertEqual(attempts[0]["score"], 20)
        self.assertEqual(attempts[0]["percentage"], 100.0)
        self.assertEqual(stats["assessments_taken"], 1)
        self.assertEqual(stats["avg_percentage"], 100.0)
        self.assertEqual(stats["highest_percentage"], 100.0)
        self.assertEqual(stats["lowest_percentage"], 100.0)

    def test_student_with_multiple_results(self):
        """Student with multiple graded assessments shows correct stats."""
        assessment1 = self.database.create_assessment(
            self.classroom_id, "Quiz 1", {i: "A" for i in range(1, 21)}
        )
        assessment2 = self.database.create_assessment(
            self.classroom_id, "Quiz 2", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}

        result1 = create_grading_result({i: "A" for i in range(1, 21)}, answer_key, question_count=20)
        self.database.save_grading_result(assessment1, result1, self.student_id)

        result2 = create_grading_result({i: "A" for i in range(1, 11)}, answer_key, question_count=20)
        self.database.save_grading_result(assessment2, result2, self.student_id)

        attempts, stats = self._get_student_performance(self.classroom_id, self.student_id)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(stats["assessments_taken"], 2)
        self.assertEqual(stats["avg_percentage"], 75.0)
        self.assertEqual(stats["highest_percentage"], 100.0)
        self.assertEqual(stats["lowest_percentage"], 50.0)

    def test_variable_question_count_20(self):
        """20-question assessment score is out of 20."""
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz 20", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}
        result = create_grading_result({i: "A" for i in range(1, 19)}, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result, self.student_id)

        attempts, _ = self._get_student_performance(self.classroom_id, self.student_id)
        self.assertEqual(attempts[0]["score"], 18)
        self.assertEqual(attempts[0]["question_count"], 20)
        self.assertEqual(attempts[0]["percentage"], 90.0)

    def test_variable_question_count_50(self):
        """50-question assessment score is out of 50."""
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz 50", {i: "A" for i in range(1, 51)}
        )
        answer_key = {i: "A" for i in range(1, 51)}
        result = create_grading_result({i: "A" for i in range(1, 43)}, answer_key, question_count=50)
        self.database.save_grading_result(assessment_id, result, self.student_id)

        attempts, _ = self._get_student_performance(self.classroom_id, self.student_id)
        self.assertEqual(attempts[0]["score"], 42)
        self.assertEqual(attempts[0]["question_count"], 50)
        self.assertEqual(attempts[0]["percentage"], 84.0)

    def test_multiple_assessments_sorted_newest_first(self):
        """Assessment attempts are sorted by graded_at descending."""
        assessment1 = self.database.create_assessment(
            self.classroom_id, "First", {1: "A"}
        )
        assessment2 = self.database.create_assessment(
            self.classroom_id, "Second", {1: "A"}
        )
        answer_key = {i: "A" for i in range(1, 51)}

        result1 = create_grading_result({1: "A"}, answer_key, question_count=1)
        self.database.save_grading_result(assessment1, result1, self.student_id)

        result2 = create_grading_result({1: "A"}, answer_key, question_count=1)
        self.database.save_grading_result(assessment2, result2, self.student_id)

        attempts, _ = self._get_student_performance(self.classroom_id, self.student_id)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0]["assessment_name"], "Second")
        self.assertEqual(attempts[1]["assessment_name"], "First")

    def test_classroom_scoped_results(self):
        """Student results are scoped to their classroom."""
        classroom2 = self.database.create_classroom("Grade 7B")
        student2 = self.database.create_student(classroom2, "Bob", "S-001")

        assessment1 = self.database.create_assessment(
            self.classroom_id, "Quiz A", {1: "A"}
        )
        assessment2 = self.database.create_assessment(
            classroom2, "Quiz B", {1: "A"}
        )
        answer_key = {i: "A" for i in range(1, 51)}

        result1 = create_grading_result({1: "A"}, answer_key, question_count=1)
        self.database.save_grading_result(assessment1, result1, self.student_id)

        result2 = create_grading_result({1: "A"}, answer_key, question_count=1)
        self.database.save_grading_result(assessment2, result2, student2)

        attempts_a, stats_a = self._get_student_performance(self.classroom_id, self.student_id)
        attempts_b, stats_b = self._get_student_performance(classroom2, student2)

        self.assertEqual(len(attempts_a), 1)
        self.assertEqual(attempts_a[0]["assessment_name"], "Quiz A")
        self.assertEqual(stats_a["assessments_taken"], 1)

        self.assertEqual(len(attempts_b), 1)
        self.assertEqual(attempts_b[0]["assessment_name"], "Quiz B")
        self.assertEqual(stats_b["assessments_taken"], 1)

    def test_same_student_id_different_classrooms(self):
        """Same student ID in different classrooms are separate records."""
        classroom2 = self.database.create_classroom("Grade 7B")
        student2 = self.database.create_student(classroom2, "Alice", "S-001")

        assessment1 = self.database.create_assessment(
            self.classroom_id, "Quiz A", {i: "A" for i in range(1, 21)}
        )
        assessment2 = self.database.create_assessment(
            classroom2, "Quiz B", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}

        result1 = create_grading_result({i: "A" for i in range(1, 21)}, answer_key, question_count=20)
        self.database.save_grading_result(assessment1, result1, self.student_id)

        result2 = create_grading_result({}, answer_key, question_count=20)
        self.database.save_grading_result(assessment2, result2, student2)

        attempts1, stats1 = self._get_student_performance(self.classroom_id, self.student_id)
        attempts2, stats2 = self._get_student_performance(classroom2, student2)

        self.assertEqual(attempts1[0]["percentage"], 100.0)
        self.assertEqual(attempts2[0]["percentage"], 0.0)

    def test_unknown_and_failed_attempts_excluded(self):
        """Unknown student (student_id=None) attempts are not included."""
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {1: "A"}
        )
        answer_key = {i: "A" for i in range(1, 51)}

        result_unknown = create_grading_result({1: "A"}, answer_key, question_count=1)
        self.database.save_grading_result(assessment_id, result_unknown, student_id=None)

        result_known = create_grading_result({1: "A"}, answer_key, question_count=1)
        self.database.save_grading_result(assessment_id, result_known, self.student_id)

        attempts, stats = self._get_student_performance(self.classroom_id, self.student_id)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(stats["assessments_taken"], 1)

    def test_zero_percentage_included(self):
        """Student with 0% result is correctly included in stats."""
        assessment_id = self.database.create_assessment(
            self.classroom_id, "Quiz", {i: "A" for i in range(1, 21)}
        )
        answer_key = {i: "A" for i in range(1, 51)}
        result = create_grading_result({}, answer_key, question_count=20)
        self.database.save_grading_result(assessment_id, result, self.student_id)

        attempts, stats = self._get_student_performance(self.classroom_id, self.student_id)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["score"], 0)
        self.assertEqual(attempts[0]["percentage"], 0.0)
        self.assertEqual(stats["avg_percentage"], 0.0)
        self.assertEqual(stats["highest_percentage"], 0.0)
        self.assertEqual(stats["lowest_percentage"], 0.0)


class ClassroomStudentsViewTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = AssessFlowDatabase(Path(self.temporary_directory.name) / "assessflow.sqlite3")
        self.database.initialize()
        self.classroom_id = self.database.create_classroom("Grade 7A")
        self.student_id = self.database.create_student(self.classroom_id, "Alice", "S-001")
        self.student_id2 = self.database.create_student(self.classroom_id, "Bob", "S-002")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _get_classroom_students_page(self):
        """Get the classroom view page and extract the Students section."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from web import create_app
        app = create_app({"DATABASE": self.database.database_file})
        with app.test_client() as client:
            return client.get(f"/classrooms/{self.classroom_id}").data.decode()

    def test_classroom_view_has_view_results_for_each_student(self):
        """Classroom Students section contains View Results link for each student."""
        html = self._get_classroom_students_page()
        self.assertIn("View Results", html)
        self.assertIn(f"/classrooms/{self.classroom_id}/students/{self.student_id}", html)
        self.assertIn(f"/classrooms/{self.classroom_id}/students/{self.student_id2}", html)

    def test_classroom_view_view_results_links_to_student_performance(self):
        """Each View Results link points to the student performance page."""
        html = self._get_classroom_students_page()
        self.assertIn(f"/classrooms/{self.classroom_id}/students/{self.student_id}", html)
        self.assertIn(f"/classrooms/{self.classroom_id}/students/{self.student_id2}", html)

    def test_classroom_view_preserves_existing_student_info(self):
        """Classroom view still shows student names and IDs."""
        html = self._get_classroom_students_page()
        self.assertIn("Alice", html)
        self.assertIn("S-001", html)
        self.assertIn("Bob", html)
        self.assertIn("S-002", html)

    def test_classroom_view_preserves_add_student_button(self):
        """Classroom view still has the + Add Student button."""
        html = self._get_classroom_students_page()
        self.assertIn("+ Add Student", html)


if __name__ == "__main__":
    unittest.main()
