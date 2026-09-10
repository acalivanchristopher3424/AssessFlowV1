"""Classroom management routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

classrooms_bp = Blueprint("classrooms", __name__)


@classrooms_bp.route("/classrooms")
def list_classrooms():
    """List all classrooms."""
    with current_app.db._connect() as connection:
        rows = connection.execute(
            """SELECT c.id, c.name, c.created_at,
                      (SELECT COUNT(*) FROM students WHERE classroom_id = c.id) AS student_count,
                      (SELECT COUNT(*) FROM assessments WHERE classroom_id = c.id) AS assessment_count
               FROM classrooms c ORDER BY c.name"""
        ).fetchall()
        classrooms = [dict(row) for row in rows]
    return render_template("classrooms/list.html", classrooms=classrooms)


@classrooms_bp.route("/classrooms/new", methods=["GET", "POST"])
def new_classroom():
    """Create a new classroom."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Classroom name is required.", "error")
            return render_template("classrooms/new.html")
        try:
            current_app.db.create_classroom(name)
            flash(f"Classroom '{name}' created.", "success")
            return redirect(url_for("classrooms.list_classrooms"))
        except Exception as e:
            flash(f"Error creating classroom: {e}", "error")
    return render_template("classrooms/new.html")


@classrooms_bp.route("/classrooms/<int:classroom_id>")
def view_classroom(classroom_id):
    """View classroom details with students and assessments."""
    with current_app.db._connect() as connection:
        classroom = connection.execute(
            "SELECT id, name, created_at FROM classrooms WHERE id = ?",
            (classroom_id,),
        ).fetchone()
        if classroom is None:
            flash("Classroom not found.", "error")
            return redirect(url_for("classrooms.list_classrooms"))

        students = connection.execute(
            "SELECT id, name, student_identifier FROM students WHERE classroom_id = ? ORDER BY name",
            (classroom_id,),
        ).fetchall()

        assessments = connection.execute(
            "SELECT id, name, question_count, created_at FROM assessments WHERE classroom_id = ? ORDER BY name",
            (classroom_id,),
        ).fetchall()

    return render_template(
        "classrooms/view.html",
        classroom=dict(classroom),
        students=[dict(s) for s in students],
        assessments=[dict(a) for a in assessments],
    )
