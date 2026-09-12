# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for AssessFlow V1 — macOS standalone application."""

import os
import sys
from pathlib import Path

block_cipher = None
project_root = os.path.abspath(SPECPATH)

a = Analysis(
    [os.path.join(project_root, "run.py")],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(project_root, "web", "templates"), os.path.join("web", "templates")),
        (os.path.join(project_root, "web", "static"), os.path.join("web", "static")),
    ],
    hiddenimports=[
        "web",
        "web.routes",
        "web.routes.classrooms",
        "web.routes.students",
        "web.routes.assessments",
        "web.routes.grading",
        "web.routes.results",
        "web.routes.history",
        "omr",
        "omr.app_config",
        "omr.database",
        "omr.csv_handler",
        "omr.bulk_processor",
        "omr.detect_scan",
        "omr.detect_answers",
        "omr.student_id",
        "omr.grade_answers",
        "omr.layout",
        "omr.generate_sheet",
        "cv2",
        "numpy",
        "flask",
        "jinja2",
        "werkzeug",
        "werkzeug.serving",
        "werkzeug.debug",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "PIL",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AssessFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AssessFlow",
)

app = BUNDLE(
    coll,
    name="AssessFlow.app",
    icon=None,
    bundle_identifier="com.assessflow.app",
    info_plist={
        "CFBundleName": "AssessFlow",
        "CFBundleDisplayName": "AssessFlow",
        "CFBundleVersion": "1.0",
        "CFBundleShortVersionString": "1.0",
        "LSMinimumSystemVersion": "10.15",
        "NSHighResolutionCapable": True,
    },
)
