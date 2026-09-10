"""Assessment management routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from omr.layout import QUESTIONS

assessments_bp = Blueprint("assessments", __name__)


@assessments_bp.route("/classrooms/<int:classroom_id>/assessments")
def list_assessments(classroom_id):
    """List assessments in a classroom."""
    with current_app.db._connect() as connection:
        classroom = connection.execute(
            "SELECT id, name FROM classrooms WHERE id = ?",
            (classroom_id,),
        ).fetchone()
        if classroom is None:
            flash("Classroom not found.", "error")
            return redirect(url_for("classrooms.list_classrooms"))

        assessments = connection.execute(
            "SELECT id, name, question_count, created_at FROM assessments WHERE classroom_id = ? ORDER BY name",
            (classroom_id,),
        ).fetchall()

    return render_template(
        "assessments/list.html",
        classroom=dict(classroom),
        assessments=[dict(a) for a in assessments],
    )


@assessments_bp.route("/classrooms/<int:classroom_id>/assessments/new", methods=["GET", "POST"])
def new_assessment(classroom_id):
    """Create a new assessment."""
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
        if not name:
            flash("Assessment name is required.", "error")
            return render_template("assessments/new.html", classroom=dict(classroom))

        answer_key = {}
        for q in range(1, QUESTIONS + 1):
            answer = request.form.get(f"q{q}", "").strip().upper()
            if answer:
                answer_key[q] = answer

        if not answer_key:
            flash("At least one answer is required.", "error")
            return render_template("assessments/new.html", classroom=dict(classroom))

        if len(answer_key) < QUESTIONS:
            flash(f"Warning: Only {len(answer_key)} of {QUESTIONS} questions have answers.", "warning")

        try:
            assessment_id = current_app.db.create_assessment(
                classroom_id, name, answer_key
            )
            flash(f"Assessment '{name}' created with {len(answer_key)} answers.", "success")
            return redirect(url_for("assessments.view_assessment", assessment_id=assessment_id))
        except Exception as e:
            flash(f"Error creating assessment: {e}", "error")

    return render_template("assessments/new.html", classroom=dict(classroom))


@assessments_bp.route("/assessments/<int:assessment_id>")
def view_assessment(assessment_id):
    """View assessment details."""
    with current_app.db._connect() as connection:
        assessment = connection.execute(
            """SELECT a.id, a.name, a.question_count, a.created_at, c.id as classroom_id, c.name as classroom_name
               FROM assessments a
               JOIN classrooms c ON c.id = a.classroom_id
               WHERE a.id = ?""",
            (assessment_id,),
        ).fetchone()
        if assessment is None:
            flash("Assessment not found.", "error")
            return redirect(url_for("classrooms.list_classrooms"))

        questions = connection.execute(
            "SELECT question_number, correct_answer FROM assessment_questions WHERE assessment_id = ? ORDER BY question_number",
            (assessment_id,),
        ).fetchall()

    return render_template(
        "assessments/view.html",
        assessment=dict(assessment),
        questions=[dict(q) for q in questions],
    )


@assessments_bp.route("/assessments/<int:assessment_id>/answer-key", methods=["GET", "POST"])
def edit_answer_key(assessment_id):
    """Edit answer key for an assessment."""
    with current_app.db._connect() as connection:
        assessment = connection.execute(
            "SELECT id, name, question_count, classroom_id FROM assessments WHERE id = ?",
            (assessment_id,),
        ).fetchone()
        if assessment is None:
            flash("Assessment not found.", "error")
            return redirect(url_for("classrooms.list_classrooms"))

        questions = connection.execute(
            "SELECT question_number, correct_answer FROM assessment_questions WHERE assessment_id = ? ORDER BY question_number",
            (assessment_id,),
        ).fetchall()
        current_answers = {q["question_number"]: q["correct_answer"] for q in questions}

    if request.method == "POST":
        answer_key = {}
        for q in range(1, QUESTIONS + 1):
            answer = request.form.get(f"q{q}", "").strip().upper()
            if answer:
                answer_key[q] = answer

        if not answer_key:
            flash("At least one answer is required.", "error")
            return render_template(
                "assessments/answer_key.html",
                assessment=dict(assessment),
                current_answers=current_answers,
                questions_range=range(1, QUESTIONS + 1),
            )

        try:
            with current_app.db._connect() as connection:
                connection.execute(
                    "DELETE FROM assessment_questions WHERE assessment_id = ?",
                    (assessment_id,),
                )
                connection.executemany(
                    "INSERT INTO assessment_questions (assessment_id, question_number, correct_answer) VALUES (?, ?, ?)",
                    [(assessment_id, q, answer_key[q]) for q in sorted(answer_key)],
                )
                connection.execute(
                    "UPDATE assessments SET question_count = ? WHERE id = ?",
                    (len(answer_key), assessment_id),
                )
            flash(f"Answer key updated with {len(answer_key)} answers.", "success")
            return redirect(url_for("assessments.view_assessment", assessment_id=assessment_id))
        except Exception as e:
            flash(f"Error updating answer key: {e}", "error")

    return render_template(
        "assessments/answer_key.html",
        assessment=dict(assessment),
        current_answers=current_answers,
        questions_range=range(1, QUESTIONS + 1),
    )
