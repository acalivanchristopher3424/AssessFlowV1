"""Start the AssessFlow V1 web application."""

from web import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
