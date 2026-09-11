"""Start the AssessFlow V1 web application."""

import os
import sys
import webbrowser
import threading

from web import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 5000))

    if "--no-browser" not in sys.argv:
        def open_browser():
            import time
            time.sleep(1.0)
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    app.run(debug=debug, port=port)
