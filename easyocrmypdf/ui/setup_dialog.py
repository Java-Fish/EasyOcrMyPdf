"""Einrichtungsdialog: zeigt fehlende Hilfsprogramme und erklärt die Installation."""

from __future__ import annotations

import sys
from typing import Dict, List

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from easyocrmypdf.dependencies import DependencyReport, ToolStatus, check_dependencies
from easyocrmypdf.i18n import tr
from easyocrmypdf.ui.widgets import Card, horizontal_separator

# Installationshinweise je Werkzeug und Betriebssystem.
# Erste Zeile: Befehl zum Kopieren. Zweite: Seite zum Herunterladen.
_INSTALL_HINTS: Dict[str, Dict[str, Dict[str, str]]] = {
    "tesseract": {
        "darwin": {
            "command": "brew install tesseract tesseract-lang",
            "url": "https://formulae.brew.sh/formula/tesseract",
        },
        "win32": {
            "command": "winget install -e --id UB-Mannheim.TesseractOCR",
            "url": "https://github.com/UB-Mannheim/tesseract/wiki",
        },
        "linux": {
            "command": "sudo apt install tesseract-ocr tesseract-ocr-deu",
            "url": "https://tesseract-ocr.github.io/tessdoc/Installation.html",
        },
    },
    "ghostscript": {
        "darwin": {
            "command": "brew install ghostscript",
            "url": "https://formulae.brew.sh/formula/ghostscript",
        },
        "win32": {
            "command": "winget install -e --id ArtifexSoftware.GhostScript",
            "url": "https://ghostscript.com/releases/gsdnld.html",
        },
        "linux": {
            "command": "sudo apt install ghostscript",
            "url": "https://ghostscript.com/releases/gsdnld.html",
        },
    },
    "ocrmypdf": {
        "darwin": {
            "command": "brew install ocrmypdf",
            "url": "https://ocrmypdf.readthedocs.io/en/latest/installation.html",
        },
        "win32": {
            "command": "pip install ocrmypdf",
            "url": "https://ocrmypdf.readthedocs.io/en/latest/installation.html",
        },
        "linux": {
            "command": "sudo apt install ocrmypdf",
            "url": "https://ocrmypdf.readthedocs.io/en/latest/installation.html",
        },
    },
}


def _platform_key() -> str:
    """Schlüssel des laufenden Betriebssystems für die Hinweistabelle."""
    if sys.platform == "win32":
        return "win32"
    if sys.platform == "darwin":
        return "darwin"
    return "linux"


class ToolRow(QWidget):
    """Eine Zeile pro Werkzeug: Zustand, Beschreibung und Installationshilfe."""

    def __init__(self, tool: ToolStatus, colors: Dict[str, str], parent: QWidget | None = None):
        super().__init__(parent)
        available = tool.available
        color = colors["success"] if available else colors["danger"]

        marker = QLabel("✓" if available else "✗", self)
        marker.setFixedWidth(18)
        marker.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: 600;")
        marker.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        name = QLabel(tool.label, self)
        name.setObjectName("FieldLabel")

        state = QLabel(tr("setup.found") if available else tr("setup.missing"), self)
        state.setStyleSheet(f"color: {color};")

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        header.addWidget(name)
        header.addWidget(state)
        header.addStretch(1)

        details = QVBoxLayout()
        details.setContentsMargins(0, 0, 0, 0)
        details.setSpacing(5)
        details.addLayout(header)

        description = QLabel(tr(f"setup.{tool.key}.desc"), self)
        description.setObjectName("Hint")
        description.setWordWrap(True)
        details.addWidget(description)

        if available:
            info = tool.version or str(tool.path or "")
            version = QLabel(info, self)
            version.setObjectName("Hint")
            version.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            details.addWidget(version)
        else:
            details.addLayout(self._build_install_help(tool.key, colors))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(marker)
        layout.addLayout(details, 1)

    def _build_install_help(self, key: str, colors: Dict[str, str]) -> QVBoxLayout:
        """Zeigt den Installationsbefehl zum Kopieren und einen Link zur Downloadseite."""
        hints = _INSTALL_HINTS.get(key, {}).get(_platform_key(), {})
        box = QVBoxLayout()
        box.setContentsMargins(0, 4, 0, 0)
        box.setSpacing(6)

        title = QLabel(tr("setup.instructions"), self)
        title.setObjectName("Hint")
        box.addWidget(title)

        command_text = hints.get("command", "")
        if command_text:
            command = QLabel(command_text, self)
            command.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            command.setStyleSheet(
                f"background: {colors['surfaceAlt']}; border: 1px solid {colors['border']};"
                f" border-radius: 6px; padding: 6px 8px; font-family: monospace;"
            )
            copy_button = QPushButton(tr("action.copy"), self)
            copy_button.clicked.connect(lambda: self._copy(command_text, copy_button))

            line = QHBoxLayout()
            line.setContentsMargins(0, 0, 0, 0)
            line.setSpacing(8)
            line.addWidget(command, 1)
            line.addWidget(copy_button)
            box.addLayout(line)

        url = hints.get("url", "")
        if url:
            link = QPushButton(tr("setup.download"), self)
            link.setObjectName("Link")
            link.setCursor(Qt.CursorShape.PointingHandCursor)
            link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
            box.addWidget(link, 0, Qt.AlignmentFlag.AlignLeft)
        return box

    @staticmethod
    def _copy(text: str, button: QPushButton) -> None:
        """Befehl in die Zwischenablage legen und kurz Rückmeldung geben."""
        QGuiApplication.clipboard().setText(text)
        button.setText(tr("action.copied"))
        button.setEnabled(False)


class SetupDialog(QDialog):
    """Wird beim Start gezeigt, solange etwas fehlt."""

    def __init__(self, report: DependencyReport, colors: Dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self._colors = colors
        self._report = report
        self.setWindowTitle(tr("setup.title"))
        self.setMinimumWidth(520)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(14)
        self._rows_container: QWidget | None = None
        self._rebuild()

    # ------------------------------------------------------------------
    def _rebuild(self) -> None:
        """Baut den Inhalt neu auf, auch nach einer erneuten Prüfung."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        intro = QLabel(
            tr("setup.allGood") if self._report.ok else tr("setup.intro"), self
        )
        intro.setObjectName("CardTitle")
        intro.setWordWrap(True)
        self._layout.addWidget(intro)

        card = Card(parent=self)
        rows: List[ToolRow] = []
        for tool in self._report.tools:
            rows.append(ToolRow(tool, self._colors, card))
        for position, row_widget in enumerate(rows):
            if position:
                card.body.addWidget(horizontal_separator(card))
            card.body.addWidget(row_widget)
        self._layout.addWidget(card)

        note = QLabel(tr("setup.note"), self)
        note.setObjectName("Hint")
        note.setWordWrap(True)
        self._layout.addWidget(note)

        buttons = QWidget(self)
        button_layout = QHBoxLayout(buttons)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        quit_button = QPushButton(tr("action.quit"), buttons)
        quit_button.clicked.connect(self.reject)
        button_layout.addWidget(quit_button)
        button_layout.addStretch(1)

        recheck = QPushButton(tr("action.retry"), buttons)
        recheck.clicked.connect(self._recheck)
        button_layout.addWidget(recheck)

        continue_button = QPushButton(
            tr("action.close") if self._report.ok else tr("action.continueAnyway"), buttons
        )
        continue_button.setObjectName("Primary" if self._report.ok else "")
        continue_button.clicked.connect(self.accept)
        button_layout.addWidget(continue_button)

        self._layout.addWidget(buttons)

    def _recheck(self) -> None:
        """Prüft erneut, ob die Programme inzwischen installiert wurden."""
        self._report = check_dependencies()
        self._rebuild()
        if self._report.ok:
            self.accept()

    @property
    def report(self) -> DependencyReport:
        """Das Ergebnis der zuletzt durchgeführten Prüfung."""
        return self._report
