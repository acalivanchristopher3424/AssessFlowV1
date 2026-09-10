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
