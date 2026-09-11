"""Assessment history routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

history_bp = Blueprint("history", __name__)


@history_bp.route("/history")
def assessment_history():
    """Show assessment history across all classrooms with optional filtering."""
    with current_app.db._connect() as connection:
        classrooms = connection.execute(
            "SELECT id, name FROM classrooms ORDER BY name"
        ).fetchall()

        classroom_id = request.args.get("classroom_id", type=int)

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

    return render_template(
        "history/list.html",
        assessments=[dict(a) for a in assessments],
        classrooms=[dict(c) for c in classrooms],
        selected_classroom_id=classroom_id,
    )
