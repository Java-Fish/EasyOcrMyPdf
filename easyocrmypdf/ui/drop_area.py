"""Der Ablagebereich: Dateien hineinziehen oder anklicken."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from easyocrmypdf.i18n import tr

PDF_SUFFIX = ".pdf"


def is_pdf(path: Path) -> bool:
    """Nur echte PDF-Dateien zulassen; geprüft wird die Endung."""
    return path.suffix.lower() == PDF_SUFFIX and path.is_file()


def split_pdf_paths(paths: List[Path]) -> Tuple[List[Path], List[Path]]:
    """Trennt eine Pfadliste in PDF-Dateien und alles Übrige.

    Ordner werden eine Ebene tief durchsucht, damit das Hineinziehen eines
    Scan-Ordners funktioniert, ohne versehentlich die halbe Festplatte
    einzulesen.
    """
    accepted: List[Path] = []
    rejected: List[Path] = []
    for path in paths:
        if path.is_dir():
            found = sorted(child for child in path.iterdir() if is_pdf(child))
            if found:
                accepted.extend(found)
            else:
                rejected.append(path)
        elif is_pdf(path):
            accepted.append(path)
        else:
            rejected.append(path)
    return accepted, rejected


class DropArea(QFrame):
    """Große Fläche zum Ablegen von PDF-Dateien; ein Klick öffnet den Dateidialog."""

    filesDropped = Signal(list)  # list[Path]
    filesRejected = Signal(list)  # list[Path]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DropArea")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Feste, kompakte Höhe: der Platz darunter gehört der Warteschlange.
        self.setMinimumHeight(140)
        self.setMaximumHeight(185)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # Für Tastaturbedienung: der Bereich lässt sich anspringen und mit
        # Leertaste oder Enter auslösen.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._icon = QLabel("\U0001F4C4", self)  # Blatt Papier
        self._icon.setObjectName("DropIcon")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel(self)
        self._title.setObjectName("DropTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._subtitle = QLabel(self)
        self._subtitle.setObjectName("DropSubtitle")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._hint = QLabel(self)
        self._hint.setObjectName("Hint")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 22, 20, 22)
        layout.setSpacing(4)
        layout.addStretch(1)
        layout.addWidget(self._icon)
        layout.addSpacing(6)
        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)
        layout.addSpacing(6)
        layout.addWidget(self._hint)
        layout.addStretch(1)

        # Blendet einen kurzen Warnhinweis nach ein paar Sekunden wieder aus.
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.setInterval(2200)
        self._reset_timer.timeout.connect(self._set_state)

        self._last_directory = str(Path.home())
        self.retranslate()

    # ------------------------------------------------------------------
    def retranslate(self) -> None:
        """Beschriftungen neu setzen, etwa nach einem Sprachwechsel."""
        self._title.setText(tr("drop.title"))
        self._subtitle.setText(tr("drop.subtitle"))
        self._hint.setText(tr("drop.hint"))
        self.setToolTip(tr("drop.subtitle"))
        self.setAccessibleName(tr("drop.title"))

    def _set_state(self, state: str = "") -> None:
        """Setzt den optischen Zustand (leer, hover, active, rejected)."""
        self.setProperty("state", state)
        # Qt wendet geänderte Eigenschaften im Stylesheet nur nach einem
        # ausdrücklichen Neuaufbau des Stils an.
        self.style().unpolish(self)
        self.style().polish(self)
        if state == "active":
            self._title.setText(tr("drop.active"))
        elif state == "rejected":
            self._title.setText(tr("drop.rejected"))
        else:
            self._title.setText(tr("drop.title"))

    # --- Maus und Tastatur --------------------------------------------
    # Die folgenden Methoden überschreiben Qt-Ereignisse. Ihre Namen folgen
    # dem Schema von Qt, nicht dem von PEP 8; daher jeweils "noqa: N802".
    def enterEvent(self, event) -> None:  # noqa: N802
        """Hebt die Fläche hervor, sobald der Mauszeiger sie erreicht."""
        if not self.property("state"):
            self._set_state("hover")
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        """Nimmt die Hervorhebung zurück, wenn der Zeiger die Fläche verlässt."""
        if self.property("state") == "hover":
            self._set_state()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Öffnet bei einem Klick den Dateiauswahldialog."""
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self.open_file_dialog()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        """Leertaste und Eingabetaste öffnen ebenfalls den Dateiauswahldialog."""
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.open_file_dialog()
            return
        super().keyPressEvent(event)

    # --- Ziehen und Ablegen --------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """Entscheidet, ob die gezogenen Dateien angenommen werden."""
        paths = paths_from_mime(event)
        if not paths:
            event.ignore()
            return
        accepted, _rejected = split_pdf_paths(paths)
        if accepted:
            event.acceptProposedAction()
            self._set_state("active")
        else:
            # Ablegen zulassen, aber sichtbar machen, dass nichts passieren wird.
            event.ignore()
            self._set_state("rejected")
            self._reset_timer.start()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """Hält die Annahme aufrecht, solange der Zeiger über der Fläche bleibt."""
        if self.property("state") == "active":
            event.acceptProposedAction()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # noqa: N802
        """Setzt die Hervorhebung zurück, wenn das Ziehen die Fläche verlässt."""
        self._set_state()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """Übernimmt die abgelegten PDF-Dateien und meldet Abgelehntes."""
        self._set_state()
        paths = paths_from_mime(event)
        accepted, rejected = split_pdf_paths(paths)
        if accepted:
            event.acceptProposedAction()
            self._last_directory = str(accepted[0].parent)
            self.filesDropped.emit(accepted)
        if rejected:
            self.filesRejected.emit(rejected)

    # ------------------------------------------------------------------
    def open_file_dialog(self) -> None:
        """Öffnet den Dateiauswahldialog, beschränkt auf PDF-Dateien."""
        names, _filter = QFileDialog.getOpenFileNames(
            self,
            tr("drop.dialog.title"),
            self._last_directory,
            tr("drop.dialog.filter"),
        )
        if not names:
            return
        paths = [Path(name) for name in names]
        accepted, rejected = split_pdf_paths(paths)
        if accepted:
            self._last_directory = str(accepted[0].parent)
            self.filesDropped.emit(accepted)
        if rejected:
            self.filesRejected.emit(rejected)


def paths_from_mime(event) -> List[Path]:
    """Liest lokale Dateipfade aus einem Drag-and-Drop-Ereignis.

    Verweise ohne lokale Entsprechung, etwa aus dem Browser gezogene URLs,
    werden dabei übergangen.
    """
    mime = event.mimeData()
    if not mime.hasUrls():
        return []
    paths: List[Path] = []
    for url in mime.urls():
        if url.isLocalFile():
            paths.append(Path(url.toLocalFile()))
    return paths
