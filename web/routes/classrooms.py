"""Classroom management routes."""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app, Response,
)

from omr.csv_handler import (
    parse_and_validate, generate_template, export_classroom_csv,
)

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


@classrooms_bp.route("/classrooms/template")
def download_template():
    """Download a CSV template for classroom import."""
    csv_content = generate_template()
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=assessflow_classroom_template.csv",
        },
    )


@classrooms_bp.route("/classrooms/import", methods=["GET", "POST"])
def import_classroom():
    """Import a classroom from a CSV file."""
    if request.method == "POST":
        # --------------------------------------------------
        # Step 1: Get uploaded file.
        # --------------------------------------------------
        file = request.files.get("csv_file")
        if not file or file.filename == "":
            flash("Please select a CSV file.", "error")
            return render_template("classrooms/import.html")

        csv_content = file.read()
        if not csv_content:
            flash("The uploaded file is empty.", "error")
            return render_template("classrooms/import.html")

        # --------------------------------------------------
        # Step 2: Parse and validate.
        # --------------------------------------------------
        existing_names = set()
        with current_app.db._connect() as connection:
            rows = connection.execute(
                "SELECT name FROM classrooms"
            ).fetchall()
            existing_names = {row["name"] for row in rows}

        result = parse_and_validate(csv_content, existing_names)

        # --------------------------------------------------
        # Step 3: If confirmation requested, create records.
        # --------------------------------------------------
        confirm = request.form.get("confirm")
        if confirm == "yes" and result["valid"]:
            try:
                classroom_id = current_app.db.import_classroom(
                    result["classroom_name"],
                    result["students"],
                )
                flash(
                    f"Classroom '{result['classroom_name']}' imported "
                    f"with {len(result['students'])} students.",
                    "success",
                )
                return redirect(
                    url_for("classrooms.view_classroom",
                            classroom_id=classroom_id)
                )
            except ValueError as e:
                flash(str(e), "error")
                return render_template("classrooms/import.html")
            except Exception as e:
                flash(f"Import failed: {e}", "error")
                return render_template("classrooms/import.html")

        # --------------------------------------------------
        # Step 4: Show preview or errors.
        # --------------------------------------------------
        return render_template(
            "classrooms/import.html",
            result=result,
            filename=file.filename,
        )

    return render_template("classrooms/import.html")


@classrooms_bp.route("/classrooms/<int:classroom_id>/export")
def export_classroom(classroom_id):
    """Export a classroom and its students as CSV."""
    with current_app.db._connect() as connection:
        classroom = connection.execute(
            "SELECT id, name FROM classrooms WHERE id = ?",
            (classroom_id,),
        ).fetchone()
        if classroom is None:
            flash("Classroom not found.", "error")
            return redirect(url_for("classrooms.list_classrooms"))

        students = connection.execute(
            """SELECT name, student_identifier
               FROM students
               WHERE classroom_id = ?
               ORDER BY name""",
            (classroom_id,),
        ).fetchall()

    csv_content = export_classroom_csv(
        classroom["name"],
        [dict(s) for s in students],
    )

    safe_name = classroom["name"].replace(" ", "_").replace("/", "-")
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                f"attachment; filename={safe_name}.csv",
        },
    )
