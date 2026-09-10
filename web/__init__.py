"""AssessFlow V1 web application."""

from pathlib import Path

from flask import Flask

from omr.database import AssessFlowDatabase


def create_app(config=None):
    """Create and configure the Flask application."""

    app = Flask(
        __name__,
        instance_relative_config=True,
    )

    app.config.from_mapping(
        SECRET_KEY="assessflow-dev-key",
        DATABASE=Path(app.instance_path) / "assessflow.db",
        UPLOAD_FOLDER=Path(app.root_path).parent / "uploads",
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    )

    if config:
        app.config.from_mapping(config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db = AssessFlowDatabase(app.config["DATABASE"])
    db.initialize()
    app.db = db

    from web.routes.classrooms import classrooms_bp
    from web.routes.students import students_bp
    from web.routes.assessments import assessments_bp
    from web.routes.grading import grading_bp
    from web.routes.results import results_bp

    app.register_blueprint(classrooms_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(assessments_bp)
    app.register_blueprint(grading_bp)
    app.register_blueprint(results_bp)

    @app.route("/")
    def index():
        from flask import render_template
        classrooms = _list_classrooms(app.db)
        return render_template("index.html", classrooms=classrooms)

    return app


def _list_classrooms(db):
    """List all classrooms."""
    with db._connect() as connection:
        rows = connection.execute(
            """SELECT c.id, c.name, c.created_at,
                      (SELECT COUNT(*) FROM students WHERE classroom_id = c.id) AS student_count,
                      (SELECT COUNT(*) FROM assessments WHERE classroom_id = c.id) AS assessment_count
               FROM classrooms c ORDER BY c.name"""
        ).fetchall()
        return [dict(row) for row in rows]
