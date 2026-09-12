# AssessFlow V1

Local web application for OMR (Optical Mark Recognition) assessment grading.

Teachers print answer sheets, students fill in bubbles, teachers scan and upload
the sheets, and AssessFlow automatically detects answers, identifies students,
and grades against the answer key.

AssessFlow runs entirely on your computer. No internet connection is required.

## Standalone Application (macOS)

The recommended way to run AssessFlow is the standalone macOS application.

### How to launch

1. Copy **`AssessFlow.app`** to your Applications folder (or anywhere convenient).
2. Double-click **AssessFlow.app**.
3. Your browser opens automatically to `http://127.0.0.1:5001`.
4. AssessFlow is ready to use.

No Python installation, virtual environment, or Terminal commands are needed.

### How to stop

- Close the browser tab.
- Quit AssessFlow from the dock (right-click > Quit), or
- The server stops automatically when the application is closed.

### Where data is stored (packaged app)

| Data | Location |
|------|----------|
| Database | `~/Library/Application Support/AssessFlow/assessflow.db` |
| Uploaded scans | `~/Library/Application Support/AssessFlow/uploads/` |
| Secret key | `~/Library/Application Support/AssessFlow/.secret_key` |

This directory is created automatically on first launch. Your data persists
across app updates — reinstalling AssessFlow does not delete your database
or uploaded files.

### Building from source

If you have the source code and want to build the standalone app:

```bash
# Set up the development environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

# Build the macOS .app
pyinstaller AssessFlow.spec --noconfirm
```

The built application appears in `dist/AssessFlow.app`.

**Note:** macOS may warn that the app is from an unidentified developer on
first launch. Right-click the app and select "Open" to bypass Gatekeeper.
Code signing will be addressed in a future milestone.

**Note:** Windows standalone packaging will be handled in M19.3.

## Development Mode

### Double-click to launch (recommended)

1. Double-click **`AssessFlow.command`** in the project folder.
2. A Terminal window opens and starts the server.
3. Your browser opens automatically to `http://127.0.0.1:5001`.
4. AssessFlow is ready to use.

You can also double-click **`AssessFlow.app`** in the project folder — it
does the same thing (this is the development launcher, separate from the
standalone PyInstaller build).

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

### Command-line development

```bash
# Activate the virtual environment
source .venv/bin/activate

# Start in development mode (with debug)
FLASK_DEBUG=1 python run.py

# Run the test suite
python -m pytest omr/ -v
```

## Data Storage

### Development mode

| Data | Location |
|------|----------|
| Database | `instance/assessflow.db` |
| Uploaded scans | `uploads/` |

### Standalone app

| Data | Location |
|------|----------|
| Database | `~/Library/Application Support/AssessFlow/assessflow.db` |
| Uploaded scans | `~/Library/Application Support/AssessFlow/uploads/` |

Directories are created automatically on first run and are never deleted
by the application.

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
