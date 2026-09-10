"""Results viewing routes."""

from flask import Blueprint, render_template, redirect, url_for, flash, current_app

results_bp = Blueprint("results", __name__)


@results_bp.route("/assessments/<int:assessment_id>/results")
def list_results(assessment_id):
    """List all grading results for an assessment."""
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

    return render_template(
        "results/list.html",
        assessment=dict(assessment),
        results=[dict(r) for r in results],
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
