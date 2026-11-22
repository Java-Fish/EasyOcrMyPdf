# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Beschreibung für OCRmyPDF GUI.

Aufruf (aus dem Projektverzeichnis):
    pyinstaller packaging/ocrmypdf_gui.spec --noconfirm

Das Ergebnis liegt unter ``dist/``:
  * macOS   -> OCRmyPDF GUI.app
  * Windows -> OCRmyPDF GUI/OCRmyPDF GUI.exe
"""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# SPECPATH wird von PyInstaller gesetzt und zeigt auf packaging/.
PROJECT_ROOT = Path(SPECPATH).resolve().parent  # noqa: F821
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = not IS_WINDOWS and not IS_MACOS

APP_NAME = "OCRmyPDF GUI"
# Unter Linux sind Leerzeichen in Programmnamen unüblich und erschweren den
# Aufruf aus der Shell; dort heißt die Datei deshalb "ocrmypdf-gui".
BINARY_NAME = "ocrmypdf-gui" if IS_LINUX else APP_NAME
BUNDLE_ID = "de.ocrmypdfgui.app"
VERSION = "0.0.2"

# --- Mitgelieferte Dateien ------------------------------------------------
datas = []

# OCRmyPDF und seine Abhängigkeiten bringen Daten und Metadaten mit, die zur
# Laufzeit gelesen werden (Versionsabfragen, Plugin-Registrierung).
for package in ("ocrmypdf", "pikepdf", "img2pdf", "pypdfium2", "pdfminer", "fpdf", "certifi"):
    try:
        datas += collect_data_files(package)
    except Exception:
        pass
for distribution in (
    "ocrmypdf", "pikepdf", "img2pdf", "pillow", "pluggy", "packaging",
    "pypdfium2", "pdfminer.six", "rich", "fpdf2", "pydantic", "certifi",
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

# Ein vorhandener vendor-Ordner wird sonst auch dann eingebunden, wenn dieser
# Build bewusst ohne mitgelieferte Programme entstehen soll. Die Build-Skripte
# setzen die Variable, wenn ohne "--vendor" gebaut wird.
skip_vendor = os.environ.get("OCRMYPDF_GUI_NO_VENDOR") == "1"

vendor_dir = PROJECT_ROOT / "vendor" / ("windows" if IS_WINDOWS else ("macos" if IS_MACOS else "linux"))
if not skip_vendor and vendor_dir.is_dir() and any(vendor_dir.iterdir()):
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
    # Stammzertifikate für das Nachladen von Sprachdateien über HTTPS.
    "certifi",
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

# --- Ungenutzte Qt-Bestandteile entfernen ----------------------------------
# PyInstaller nimmt über den PySide6-Hook das halbe Qt mit, auch Module, die
# diese Anwendung nie verwendet. Das sind rund 24 MB, die das fertige Paket
# unnötig aufblähen. Die Anwendung benutzt ausschließlich QtCore, QtGui und
# QtWidgets; alles rund um QML, Quick, die Bildschirmtastatur und den
# PDF-Betrachter von Qt kann entfallen.
# Qt-Module, die diese Anwendung nicht verwendet. Angegeben ohne Präfix, weil
# jede Plattform anders benennt:
#   macOS    QtQuick.framework/Versions/A/QtQuick
#   Linux    libQt6Quick.so.6
#   Windows  Qt6Quick.dll
UNUSED_QT_MODULES = {
    "Pdf", "PdfQuick", "PdfWidgets",
    "Quick", "Quick3D", "QuickControls2", "QuickWidgets", "QuickShapes",
    "QuickTest", "QuickLayouts", "QuickDialogs2", "QuickTemplates2",
    "QuickVectorImage", "QuickVectorImageGenerator",
    "Qml", "QmlMeta", "QmlModels", "QmlWorkerScript", "QmlCore", "QmlLocalStorage",
    "VirtualKeyboard", "VirtualKeyboardQml", "VirtualKeyboardSettings",
}
# Nicht entfernen, auch wenn es verlockend aussieht: QtGui verweist auf QtDBus,
# ohne das die Anwendung nicht mehr startet. QtSvg und QtOpenGL brächten im
# fertigen Paket praktisch nichts, weil sie sich sehr gut komprimieren lassen.

# Einzelne Plugins, die ohne die oben entfernten Bibliotheken nutzlos sind.
# Bleiben sie liegen, versucht Qt beim Start vergeblich, sie zu laden.
UNUSED_QT_PLUGINS = (
    "platforminputcontexts/libqtvirtualkeyboardplugin",
    "imageformats/libqpdf",
    "imageformats/qpdf",
)


def _qt_module_name(part):
    """Schält den reinen Modulnamen aus einem Dateinamen, sonst None.

    Beispiele: "libQt6Quick.so.6" -> "Quick", "Qt6Qml.dll" -> "Qml",
    "QtQuick.framework" -> "Quick".
    """
    name = str(part).split(".")[0]
    if name.startswith("lib"):
        name = name[3:]
    for praefix in ("Qt6", "Qt5", "Qt"):
        if name.startswith(praefix) and len(name) > len(praefix):
            return name[len(praefix):]
    return None


def _is_unused_qt(destination):
    """True, wenn der Zielpfad zu einem nicht benötigten Qt-Modul gehört."""
    text = str(destination).replace("\\", "/")
    parts = Path(str(destination)).parts
    if "qml" in parts:
        return True
    if any(marker in text for marker in UNUSED_QT_PLUGINS):
        return True
    return any(_qt_module_name(part) in UNUSED_QT_MODULES for part in parts)


_before = len(analysis.binaries) + len(analysis.datas)
analysis.binaries = [entry for entry in analysis.binaries if not _is_unused_qt(entry[0])]
analysis.datas = [entry for entry in analysis.datas if not _is_unused_qt(entry[0])]
print(f"Vendor mitgeliefert: {not skip_vendor and vendor_dir.is_dir()}")
print(f"Qt-Filter: {_before - len(analysis.binaries) - len(analysis.datas)} Einträge entfernt")

pyz = PYZ(analysis.pure)  # noqa: F821

executable = EXE(  # noqa: F821
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=BINARY_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,  # kein Konsolenfenster, die Anwendung ist rein grafisch
    disable_windowed_traceback=False,
    argv_emulation=IS_MACOS,  # macOS: per "Öffnen mit" übergebene Dateien annehmen
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # ELF-Dateien tragen kein Symbol in sich; unter Linux übernimmt das die
    # .desktop-Datei. PyInstaller würde eine fehlende Datei bemängeln.
    icon=None if IS_LINUX else str(resources / ("icon.ico" if IS_WINDOWS else "icon.icns")),
)

collection = COLLECT(  # noqa: F821
    executable,
    analysis.binaries,
    analysis.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name=BINARY_NAME,
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
