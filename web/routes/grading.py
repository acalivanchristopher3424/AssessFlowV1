"""Scan upload and grading routes."""

import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename

from omr.bulk_processor import bulk_process_with_context
from omr.layout import QUESTIONS

grading_bp = Blueprint("grading", __name__)


def _get_student_info(database, student_id):
    """Look up student name and identifier by primary key."""
    with database._connect() as connection:
        row = connection.execute(
            "SELECT name, student_identifier FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()
        return dict(row) if row else None


@grading_bp.route("/assessments/<int:assessment_id>/grade", methods=["GET", "POST"])
def grade_scans(assessment_id):
    """Upload scans and process them."""
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

    if request.method == "POST":
        files = request.files.getlist("scans")
        if not files or all(f.filename == "" for f in files):
            flash("Please select at least one scan file.", "error")
            return render_template("grading/upload.html", assessment=dict(assessment))

        upload_dir = current_app.config["UPLOAD_FOLDER"] / str(uuid.uuid4())
        upload_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for f in files:
            if f.filename:
                filename = secure_filename(f.filename)
                filepath = upload_dir / filename
                f.save(str(filepath))
                saved_files.append(filepath)

        if not saved_files:
            flash("No valid files uploaded.", "error")
            return render_template("grading/upload.html", assessment=dict(assessment))

        try:
            results = bulk_process_with_context(
                saved_files,
                current_app.db,
                assessment["classroom_id"],
                assessment_id,
            )
        except Exception as e:
            flash(f"Error processing scans: {e}", "error")
            return render_template("grading/upload.html", assessment=dict(assessment))

        for r in results:
            if r["student_id"]:
                info = _get_student_info(current_app.db, r["student_id"])
                r["student_name"] = info["name"] if info else None
                r["student_identifier"] = info["student_identifier"] if info else None
            else:
                r["student_name"] = None
                r["student_identifier"] = None

        graded = sum(1 for r in results if r["status"] == "graded")
        unknown = sum(1 for r in results if r["status"] == "unknown_student")
        failed = sum(1 for r in results if r["status"] == "failed")

        flash(
            f"Processed {len(results)} scans: {graded} graded, {unknown} unknown student, {failed} failed.",
            "success" if graded > 0 else "warning",
        )

        return render_template(
            "grading/results.html",
            assessment=dict(assessment),
            results=results,
        )

    return render_template("grading/upload.html", assessment=dict(assessment))
