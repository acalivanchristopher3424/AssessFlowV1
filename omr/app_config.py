"""Application configuration for frozen (packaged) and development modes."""

import secrets
import sys
from pathlib import Path


def is_frozen():
    """Return True if running as a PyInstaller frozen application."""
    return getattr(sys, "frozen", False)


def get_bundle_dir():
    """Return the bundle directory (read-only resources).

    In frozen mode this is sys._MEIPASS (the temp extraction directory).
    In development this is the project root.
    """
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_data_dir():
    """Return the writable user data directory.

    macOS:  ~/Library/Application Support/AssessFlow/
    Other:  ~/.assessflow/
    """
    if is_frozen():
        import platform
        if platform.system() == "Darwin":
            return Path.home() / "Library" / "Application Support" / "AssessFlow"
        return Path.home() / ".assessflow"
    # Development mode: use the project's instance/ and uploads/ directories.
    return Path(__file__).resolve().parent.parent


def get_database_path():
    """Return the path to the SQLite database."""
    data_dir = get_data_dir()
    if is_frozen():
        return data_dir / "assessflow.db"
    return data_dir / "instance" / "assessflow.db"


def get_upload_folder():
    """Return the path to the uploads directory."""
    data_dir = get_data_dir()
    if is_frozen():
        return data_dir / "uploads"
    return data_dir / "uploads"


def ensure_data_dirs():
    """Create the writable data directories if they do not exist."""
    data_dir = get_data_dir()
    if is_frozen():
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "uploads").mkdir(parents=True, exist_ok=True)
    else:
        (data_dir / "instance").mkdir(parents=True, exist_ok=True)
        (data_dir / "uploads").mkdir(parents=True, exist_ok=True)


def get_or_create_secret_key():
    """Return a persistent SECRET_KEY for the application.

    In frozen mode, generates a random key on first launch and stores it
    in the data directory so it remains stable across app restarts and
    updates.

    In development mode, returns the environment variable or a default.
    """
    if is_frozen():
        key_file = get_data_dir() / ".secret_key"
        if key_file.exists():
            return key_file.read_text().strip()
        key = secrets.token_hex(32)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(key)
        return key

    import os
    return os.environ.get(
        "SECRET_KEY",
        "assessflow-local-dev-key-change-in-production",
    )
