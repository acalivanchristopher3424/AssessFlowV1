"""Results viewing and export routes."""

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, Response

from omr.csv_handler import export_results_csv, generate_results_filename

results_bp = Blueprint("results", __name__)


@results_bp.route("/assessments/<int:assessment_id>/results")
def list_results(assessment_id):
    """List all grading results for an assessment with dashboard stats."""
    with current_app.db._connect() as connection:
        assessment = connection.execute(
            """SELECT a.id, a.name, a.question_count, c.id as classroom_id, c.name as classroom_name
               FROM assessments a
               JOIN classrooms c ON c.id = a.classroom_id
               WHERE a.id = ?""",
            (assessment_id,),
        ).fetchone()
        if assessment is None:
            flash("Assessment not found.", "error")
            return redirect(url_for("classrooms.list_classrooms"))

        results = connection.execute(
            """SELECT ga.id, ga.score, ga.percentage, ga.correct_count, ga.wrong_count,
                      ga.blank_count, ga.multiple_count, ga.source_file, ga.graded_at,
                      s.name as student_name, s.student_identifier
               FROM grading_attempts ga
               LEFT JOIN students s ON s.id = ga.student_id
               WHERE ga.assessment_id = ?
               ORDER BY ga.graded_at DESC""",
            (assessment_id,),
        ).fetchall()

        stats = connection.execute(
            """SELECT
                  COUNT(*) as students_graded,
                  ROUND(AVG(score), 1) as avg_score,
                  ROUND(AVG(percentage), 1) as avg_percentage
               FROM grading_attempts
               WHERE assessment_id = ?""",
            (assessment_id,),
        ).fetchone()

    return render_template(
        "results/list.html",
        assessment=dict(assessment),
        results=[dict(r) for r in results],
        stats=dict(stats) if stats else {"students_graded": 0, "avg_score": 0, "avg_percentage": 0},
    )


@results_bp.route("/classrooms/<int:classroom_id>/results")
def classroom_results(classroom_id):
    """Show a summary of results for all assessments in a classroom."""
    with current_app.db._connect() as connection:
        classroom = connection.execute(
            "SELECT id, name FROM classrooms WHERE id = ?",
            (classroom_id,),
        ).fetchone()
        if classroom is None:
            flash("Classroom not found.", "error")
            return redirect(url_for("classrooms.list_classrooms"))

        assessments = connection.execute(
            """SELECT a.id, a.name, a.question_count,
                      (SELECT COUNT(*) FROM grading_attempts WHERE assessment_id = a.id) as students_graded,
                      (SELECT ROUND(AVG(score), 1) FROM grading_attempts WHERE assessment_id = a.id) as avg_score,
                      (SELECT ROUND(AVG(percentage), 1) FROM grading_attempts WHERE assessment_id = a.id) as avg_percentage
               FROM assessments a
               WHERE a.classroom_id = ?
               ORDER BY a.name""",
            (classroom_id,),
        ).fetchall()

    return render_template(
        "results/classroom_results.html",
        classroom=dict(classroom),
        assessments=[dict(a) for a in assessments],
    )


@results_bp.route("/results/<int:attempt_id>")
def view_result(attempt_id):
    """View a single grading attempt."""
    result = current_app.db.get_grading_result(attempt_id)
    if result is None:
        flash("Grading result not found.", "error")
        return redirect(url_for("classrooms.list_classrooms"))

    with current_app.db._connect() as connection:
        assessment = connection.execute(
            "SELECT id, name, classroom_id FROM assessments WHERE id = ?",
            (result["assessment_id"],),
        ).fetchone()

    return render_template(
        "results/view.html",
        result=result,
        assessment=dict(assessment) if assessment else None,
    )


@results_bp.route("/assessments/<int:assessment_id>/results/export")
def export_assessment_results(assessment_id):
    """Export all graded results for an assessment as CSV."""
    assessment = current_app.db.get_assessment(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("classrooms.list_classrooms"))

    with current_app.db._connect() as connection:
        classroom = connection.execute(
            "SELECT name FROM classrooms WHERE id = ?",
            (assessment["classroom_id"],),
        ).fetchone()

    classroom_name = classroom["name"] if classroom else "Unknown"
    rows = current_app.db.get_assessment_export_rows(assessment_id)

    filename = generate_results_filename(classroom_name, assessment["name"])
    csv_bytes = export_results_csv(rows)

    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@results_bp.route("/classrooms/<int:classroom_id>/results/export")
def export_classroom_results(classroom_id):
    """Export all graded results for a classroom as CSV."""
    classroom = current_app.db.get_classroom(classroom_id)
    if classroom is None:
        flash("Classroom not found.", "error")
        return redirect(url_for("classrooms.list_classrooms"))

    rows = current_app.db.get_classroom_export_rows(classroom_id)

    filename = generate_results_filename(classroom["name"])
    csv_bytes = export_results_csv(rows)

    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
