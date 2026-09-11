"""Student management routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

students_bp = Blueprint("students", __name__)


@students_bp.route("/classrooms/<int:classroom_id>/students")
def list_students(classroom_id):
    """List students in a classroom."""
    with current_app.db._connect() as connection:
        classroom = connection.execute(
            "SELECT id, name FROM classrooms WHERE id = ?",
            (classroom_id,),
        ).fetchone()
        if classroom is None:
            flash("Classroom not found.", "error")
            return redirect(url_for("classrooms.list_classrooms"))

        students = connection.execute(
            "SELECT id, name, student_identifier FROM students WHERE classroom_id = ? ORDER BY name",
            (classroom_id,),
        ).fetchall()

    return render_template(
        "students/list.html",
        classroom=dict(classroom),
        students=[dict(s) for s in students],
    )


@students_bp.route("/classrooms/<int:classroom_id>/students/<int:student_id>")
def student_performance(classroom_id, student_id):
    """Show an individual student's performance and assessment history."""
    with current_app.db._connect() as connection:
        classroom = connection.execute(
            "SELECT id, name FROM classrooms WHERE id = ?",
            (classroom_id,),
        ).fetchone()
        if classroom is None:
            flash("Classroom not found.", "error")
            return redirect(url_for("classrooms.list_classrooms"))

        student = connection.execute(
            "SELECT id, name, student_identifier FROM students WHERE id = ? AND classroom_id = ?",
            (student_id, classroom_id),
        ).fetchone()
        if student is None:
            flash("Student not found.", "error")
            return redirect(url_for("students.list_students", classroom_id=classroom_id))

        attempts = connection.execute(
            """SELECT ga.id, ga.assessment_id, ga.score, ga.percentage, ga.correct_count, ga.wrong_count,
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

    stats_dict = dict(stats) if stats else {
        "assessments_taken": 0,
        "avg_percentage": None,
        "highest_percentage": None,
        "lowest_percentage": None,
    }

    return render_template(
        "students/performance.html",
        classroom=dict(classroom),
        student=dict(student),
        attempts=[dict(a) for a in attempts],
        stats=stats_dict,
    )


@students_bp.route("/classrooms/<int:classroom_id>/students/new", methods=["GET", "POST"])
def new_student(classroom_id):
    """Add a student to a classroom."""
    with current_app.db._connect() as connection:
        classroom = connection.execute(
            "SELECT id, name FROM classrooms WHERE id = ?",
            (classroom_id,),
        ).fetchone()
        if classroom is None:
            flash("Classroom not found.", "error")
            return redirect(url_for("classrooms.list_classrooms"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        student_identifier = request.form.get("student_identifier", "").strip() or None

        if not name:
            flash("Student name is required.", "error")
            return render_template("students/new.html", classroom=dict(classroom))

        try:
            current_app.db.create_student(classroom_id, name, student_identifier)
            flash(f"Student '{name}' added.", "success")
            return redirect(url_for("classrooms.view_classroom", classroom_id=classroom_id))
        except Exception as e:
            flash(f"Error adding student: {e}", "error")

    return render_template("students/new.html", classroom=dict(classroom))
