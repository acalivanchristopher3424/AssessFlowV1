#!/bin/bash
# ============================================================
# AssessFlow V1 — Local Launcher
# ============================================================
# Double-click this file (or its .app wrapper) to start
# AssessFlow. The browser opens automatically.
#
# To stop: close the terminal window that opens, or press
# Ctrl+C in that window.
# ============================================================

# --------------------------------------------------------
# Find the project directory (where this script lives).
# --------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --------------------------------------------------------
# Configuration.
# --------------------------------------------------------

PORT=5001
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
URL="http://127.0.0.1:$PORT"

# --------------------------------------------------------
# Check that the virtual environment exists.
# --------------------------------------------------------

if [ ! -f "$VENV_PYTHON" ]; then
    echo ""
    echo "AssessFlow cannot start."
    echo ""
    echo "The Python environment was not found at:"
    echo "  $VENV_PYTHON"
    echo ""
    echo "Please set up the virtual environment first:"
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/pip install -r requirements.txt"
    echo ""
    echo "Press Enter to close."
    read
    exit 1
fi

# --------------------------------------------------------
# Check that Flask and dependencies are installed.
# --------------------------------------------------------

"$VENV_PYTHON" -c "import flask, cv2, numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo "AssessFlow cannot start."
    echo ""
    echo "Some dependencies are missing. Installing now..."
    echo ""
    "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"
    if [ $? -ne 0 ]; then
        echo ""
        echo "Installation failed. Please check your network connection"
        echo "and try again."
        echo ""
        echo "Press Enter to close."
        read
        exit 1
    fi
    echo ""
    echo "Dependencies installed successfully."
    echo ""
fi

# --------------------------------------------------------
# Check if the server is already running on this port.
# --------------------------------------------------------

if lsof -i :"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo ""
    echo "AssessFlow is already running on port $PORT."
    echo ""
    echo "Opening the browser..."
    open "$URL"
    echo ""
    echo "Press Enter to close this window."
    read
    exit 0
fi

# --------------------------------------------------------
# Start the Flask server.
# --------------------------------------------------------

echo ""
echo "Starting AssessFlow on port $PORT..."
echo ""

"$VENV_PYTHON" "$SCRIPT_DIR/run.py" &
SERVER_PID=$!

# --------------------------------------------------------
# Wait for the server to become available.
# --------------------------------------------------------

echo "Waiting for server to be ready..."

TRIES=0
MAX_TRIES=30

while [ $TRIES -lt $MAX_TRIES ]; do
    if curl -s -o /dev/null -w "" "$URL" 2>/dev/null; then
        break
    fi
    sleep 0.5
    TRIES=$((TRIES + 1))
done

if [ $TRIES -ge $MAX_TRIES ]; then
    echo ""
    echo "AssessFlow took too long to start."
    echo ""
    echo "Press Enter to close."
    kill $SERVER_PID 2>/dev/null
    read
    exit 1
fi

# --------------------------------------------------------
# Server is ready — open the browser.
# --------------------------------------------------------

echo "AssessFlow is ready!"
echo ""
open "$URL"

echo ""
echo "============================================"
echo "  AssessFlow is running"
echo "  $URL"
echo ""
echo "  To stop: close this window or press Ctrl+C"
echo "============================================"
echo ""

# --------------------------------------------------------
# Keep the script alive so the server keeps running.
# Trap Ctrl+C to clean up.
# --------------------------------------------------------

cleanup() {
    echo ""
    echo "Stopping AssessFlow..."
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    echo "AssessFlow stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for the server process to exit.
wait $SERVER_PID 2>/dev/null
