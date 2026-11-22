"""Einstiegspunkt der Anwendung.

Enthält außerdem die Weiche für den ``--ocr-worker``-Modus: im gebündelten
Programm startet sich die Anwendung selbst noch einmal und arbeitet dann als
OCRmyPDF-Kommandozeile. So braucht der Rechner keine separate
OCRmyPDF-Installation.
"""

from __future__ import annotations

import multiprocessing
import sys
from typing import List, Optional

from easyocrmypdf import __app_name__, __version__

# Argument, mit dem sich die Anwendung selbst als OCR-Arbeiter aufruft.
OCR_WORKER_FLAG = "--ocr-worker"


def run_ocr_worker(arguments: List[str]) -> int:
    """Führt OCRmyPDF mit den übergebenen Argumenten aus.

    Die Oberfläche setzt zwar bereits PATH und TESSDATA_PREFIX für den
    Unterprozess. Der Arbeiter richtet sich die Umgebung zusätzlich selbst ein,
    damit er auch bei direktem Aufruf die mitgelieferten Programme findet.
    """
    import os

    from easyocrmypdf.dependencies import process_environment

    os.environ.update(process_environment())

    try:
        from ocrmypdf.__main__ import run as ocrmypdf_run
    except ImportError as error:  # pragma: no cover - nur bei kaputtem Paket
        print(f"OCRmyPDF is not available: {error}", file=sys.stderr)
        return 3
    sys.argv = ["ocrmypdf", *arguments]
    return int(ocrmypdf_run() or 0)


def main(argv: Optional[List[str]] = None) -> int:
    """Startet entweder die Oberfläche oder den OCR-Arbeiter."""
    argv = list(sys.argv[1:] if argv is None else argv)

    # PyInstaller-Programme müssen multiprocessing früh absichern, sonst
    # starten Kindprozesse die Oberfläche erneut.
    multiprocessing.freeze_support()

    if argv and argv[0] == OCR_WORKER_FLAG:
        return run_ocr_worker(argv[1:])

    if argv and argv[0] in ("--version", "-V"):
        print(f"{__app_name__} {__version__}")
        return 0

    return _run_gui(argv)


def _run_gui(argv: List[str]) -> int:
    """Baut die Qt-Anwendung auf und zeigt das Hauptfenster."""
    # Der Import geschieht bewusst spät: der OCR-Arbeiter braucht kein Qt.
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QDialog

    from easyocrmypdf import config
    from easyocrmypdf.dependencies import check_dependencies
    from easyocrmypdf.i18n import tr
    from easyocrmypdf.ui.main_window import MainWindow
    from easyocrmypdf.ui.setup_dialog import SetupDialog
    from easyocrmypdf.ui.style import apply_theme

    QApplication.setApplicationName(__app_name__)
    QApplication.setApplicationDisplayName(__app_name__)
    QApplication.setApplicationVersion(__version__)
    QApplication.setOrganizationName(__app_name__)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

    application = QApplication([sys.argv[0]])
    colors = apply_theme(application)

    settings = config.load_settings()
    tr.set_language(settings.ui_language)

    # Fehlt ein Hilfsprogramm, erklärt der Einrichtungsdialog die Installation.
    report = check_dependencies()
    if not report.ok:
        dialog = SetupDialog(report, colors)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return 1

    window = MainWindow(settings, colors)
    window.show()

    # Beim Start übergebene PDF-Dateien direkt in die Warteschlange legen
    # (z. B. beim Öffnen per "Öffnen mit" aus dem Dateimanager).
    startup_files = [argument for argument in argv if not argument.startswith("-")]
    if startup_files:
        from pathlib import Path

        from easyocrmypdf.ui.drop_area import split_pdf_paths

        accepted, _rejected = split_pdf_paths([Path(name) for name in startup_files])
        if accepted:
            window.add_files(accepted)

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
