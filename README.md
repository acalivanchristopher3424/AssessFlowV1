# AssessFlow V1

Local web application for OMR (Optical Mark Recognition) assessment grading.

Teachers print answer sheets, students fill in bubbles, teachers scan and upload
the sheets, and AssessFlow automatically detects answers, identifies students,
and grades against the answer key.

AssessFlow runs entirely on your computer. No internet connection is required.

## Quick Start

```bash
# 1. Activate the virtual environment
source .venv/bin/activate

# 2. Start AssessFlow
python run.py
```

Your browser will open automatically to `http://127.0.0.1:5000`.

## Stopping

Press `Ctrl+C` in the terminal to stop the server.

## Restarting

Run `python run.py` again. All your classrooms, students, assessments,
and grading results are preserved.

## Where Data Is Stored

| Data | Location |
|------|----------|
| Database | `instance/assessflow.db` |
| Uploaded scans | `uploads/` |

These directories are created automatically on first run and are never
deleted by the application. Restarting or updating the code does not
erase your data.

## Running Tests

```bash
python -m pytest omr/ -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | dev fallback | Flask session secret key |
| `FLASK_DEBUG` | `0` | Set to `1` to enable debug mode |
| `PORT` | `5000` | Port for the local server |

## Architecture

- **Flask** — web interface
- **OpenCV + NumPy** — OMR scan detection
- **SQLite** — local database
- **Local filesystem** — uploaded scan storage
