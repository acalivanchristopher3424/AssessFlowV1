"""Start the AssessFlow V1 web application."""

import os
import socket
import sys
import webbrowser
import threading

from omr.app_config import is_frozen


def _port_in_use(port, host="127.0.0.1"):
    """Return True if the given port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


def _show_duplicate_message(port):
    """Show a user-facing message when another instance is already running."""
    url = f"http://127.0.0.1:{port}"
    if is_frozen():
        try:
            import subprocess
            message = (
                "AssessFlow is already running.\\n\\n"
                "A browser window should open automatically.\\n"
                "If not, open: " + url
            )
            subprocess.run(
                [
                    "osascript", "-e",
                    'display dialog "' + message + '" buttons {"OK"} default button "OK" '
                    'with title "AssessFlow"',
                ],
                timeout=10,
            )
        except Exception:
            print(f"AssessFlow is already running at {url}")
    else:
        print(f"AssessFlow is already running at {url}")

    webbrowser.open(url)


def main():
    """Application entry point."""
    from web import create_app

    debug = os.environ.get("FLASK_DEBUG", "0") == "1" and not is_frozen()
    port = int(os.environ.get("PORT", 5001))

    if _port_in_use(port):
        _show_duplicate_message(port)
        sys.exit(0)

    app = create_app()

    if "--no-browser" not in sys.argv:
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    app.run(debug=debug, port=port, host="127.0.0.1")


if __name__ == "__main__":
    main()
