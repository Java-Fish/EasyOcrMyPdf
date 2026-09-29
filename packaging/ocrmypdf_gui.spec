# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Beschreibung für OCRmyPDF GUI.

Aufruf (aus dem Projektverzeichnis):
    pyinstaller packaging/ocrmypdf_gui.spec --noconfirm

Das Ergebnis liegt unter ``dist/``:
  * macOS   -> OCRmyPDF GUI.app
  * Windows -> OCRmyPDF GUI/OCRmyPDF GUI.exe
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# SPECPATH wird von PyInstaller gesetzt und zeigt auf packaging/.
PROJECT_ROOT = Path(SPECPATH).resolve().parent  # noqa: F821
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

APP_NAME = "OCRmyPDF GUI"
BUNDLE_ID = "de.ocrmypdfgui.app"
VERSION = "1.0.0"

# --- Mitgelieferte Dateien ------------------------------------------------
datas = []

# OCRmyPDF und seine Abhängigkeiten bringen Daten und Metadaten mit, die zur
# Laufzeit gelesen werden (Versionsabfragen, Plugin-Registrierung).
for package in ("ocrmypdf", "pikepdf", "img2pdf", "pypdfium2", "pdfminer", "fpdf"):
    try:
        datas += collect_data_files(package)
    except Exception:
        pass
for distribution in (
    "ocrmypdf", "pikepdf", "img2pdf", "pillow", "pluggy", "packaging",
    "pypdfium2", "pdfminer.six", "rich", "fpdf2", "pydantic",
):
    try:
        datas += copy_metadata(distribution)
    except Exception:
        # Fehlt ein optionales Paket, soll der Build trotzdem durchlaufen.
        pass

# Anwendungssymbol und, falls vorhanden, die mitgelieferten Binaries.
resources = PROJECT_ROOT / "resources"
if (resources / "icon.png").is_file():
    datas.append((str(resources / "icon.png"), "resources"))

vendor_dir = PROJECT_ROOT / "vendor" / ("windows" if IS_WINDOWS else ("macos" if IS_MACOS else "linux"))
if vendor_dir.is_dir() and any(vendor_dir.iterdir()):
    # Zielpfad muss zu dependencies.vendor_root() passen.
    datas.append((str(vendor_dir), f"vendor/{vendor_dir.name}"))

# --- Versteckte Importe ---------------------------------------------------
# OCRmyPDF lädt seine Plugins über pluggy erst zur Laufzeit; PyInstaller kann
# das nicht selbst erkennen.
hiddenimports = [
    *collect_submodules("ocrmypdf"),
    "ocrmypdf.builtin_plugins.concurrency",
    "ocrmypdf.builtin_plugins.default_filters",
    "ocrmypdf.builtin_plugins.ghostscript",
    "ocrmypdf.builtin_plugins.null_ocr",
    "ocrmypdf.builtin_plugins.optimize",
    "ocrmypdf.builtin_plugins.pypdfium",
    "ocrmypdf.builtin_plugins.tesseract_ocr",
    "PIL.Image",
    "PIL.ImageOps",
    "img2pdf",
    "pikepdf",
    "pypdfium2",
    "multiprocessing.pool",
]

# --- Nicht benötigte Pakete ausschließen, damit das Paket kleiner wird ----
excludes = [
    "streamlit", "watchfiles", "altair", "tornado",        # nur für ocrmypdf-Weboberfläche
    "tkinter", "matplotlib", "numpy.distutils", "pytest", "IPython", "notebook",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQuick",
    "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtBluetooth",
    "PySide6.QtPositioning", "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtWebSockets", "PySide6.QtWebChannel", "PySide6.QtTest",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtSql", "PySide6.QtOpenGL",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtNetworkAuth",
]

analysis = Analysis(  # noqa: F821
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)  # noqa: F821

executable = EXE(  # noqa: F821
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # kein Konsolenfenster, die Anwendung ist rein grafisch
    disable_windowed_traceback=False,
    argv_emulation=IS_MACOS,  # macOS: per "Öffnen mit" übergebene Dateien annehmen
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(resources / ("icon.ico" if IS_WINDOWS else "icon.icns")),
)

collection = COLLECT(  # noqa: F821
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

if IS_MACOS:
    app = BUNDLE(  # noqa: F821
        collection,
        name=f"{APP_NAME}.app",
        icon=str(resources / "icon.icns"),
        bundle_identifier=BUNDLE_ID,
        version=VERSION,
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            # Die Anwendung erscheint im "Öffnen mit"-Menü für PDF-Dateien.
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "PDF Document",
                    "CFBundleTypeRole": "Editor",
                    "LSHandlerRank": "Alternate",
                    "LSItemContentTypes": ["com.adobe.pdf"],
                }
            ],
        },
    )
