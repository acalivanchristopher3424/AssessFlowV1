# AssessFlow V1

Local web application for OMR (Optical Mark Recognition) assessment grading.

Teachers print answer sheets, students fill in bubbles, teachers scan and upload
the sheets, and AssessFlow automatically detects answers, identifies students,
and grades against the answer key.

AssessFlow runs entirely on your computer. No internet connection is required.

## Starting AssessFlow

### Double-click to launch (recommended)

1. Double-click **`AssessFlow.command`** in the project folder.
2. A Terminal window opens and starts the server.
3. Your browser opens automatically to `http://127.0.0.1:5001`.
4. AssessFlow is ready to use.

You can also double-click **`AssessFlow.app`** — it does the same thing.

### What happens on launch

- The launcher finds the project's Python environment automatically.
- If dependencies are missing, they are installed automatically.
- If AssessFlow is already running, the browser opens without starting a duplicate.
- The server runs in the Terminal window until you stop it.

### Stopping AssessFlow

- Close the Terminal window, or
- Press `Ctrl+C` in the Terminal window.

All your data (classrooms, students, assessments, grading results, uploaded
scans) is preserved. Restarting AssessFlow does not erase anything.

### If the launcher reports an error

- **"Python environment was not found"** — Run `python3 -m venv .venv` then
  `.venv/bin/pip install -r requirements.txt` from the project folder.
- **"Dependencies are missing"** — The launcher will try to install them
  automatically. Check your internet connection if it fails.
- **"Took too long to start"** — Another process may be using port 5001.
  Close other applications and try again.

## Developer Setup

```bash
# Activate the virtual environment
source .venv/bin/activate

# Start in development mode (with debug)
FLASK_DEBUG=1 python run.py

# Run the test suite
python -m pytest omr/ -v
```

## Where Data Is Stored

| Data | Location |
|------|----------|
| Database | `instance/assessflow.db` |
| Uploaded scans | `uploads/` |

These directories are created automatically on first run and are never
deleted by the application.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | dev fallback | Flask session secret key |
| `FLASK_DEBUG` | `0` | Set to `1` to enable debug mode |
| `PORT` | `5001` | Port for the local server |

## Architecture

- **Flask** — web interface
- **OpenCV + NumPy** — OMR scan detection
- **SQLite** — local database
- **Local filesystem** — uploaded scan storage
