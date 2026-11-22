"""Die Warteschlange: zeigt alle ausgewählten PDF-Dateien und ihren Zustand."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from easyocrmypdf.i18n import tr
from easyocrmypdf.models import Job, JobStatus

# Symbol je Zustand, bewusst ohne Bilddateien, damit das Paket klein bleibt.
_STATUS_ICON = {
    JobStatus.PENDING: "○",  # leerer Kreis
    JobStatus.RUNNING: "◔",  # teilweise gefüllter Kreis
    JobStatus.DONE: "✓",  # Haken
    JobStatus.FAILED: "✗",  # Kreuz
    JobStatus.SKIPPED: "\u2298",  # durchgestrichener Kreis
    JobStatus.CANCELLED: "\u2298",
}

_STATUS_COLOR_TOKEN = {
    JobStatus.DONE: "success",
    JobStatus.FAILED: "danger",
    JobStatus.RUNNING: "accent",
}


class JobItemWidget(QWidget):
    """Eine Zeile der Warteschlange."""

    removeRequested = Signal(object)  # Job
    openRequested = Signal(object)  # Path der fertigen Datei

    def __init__(self, job: Job, colors: Dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._job = job
        self._colors = colors

        self._icon = QLabel(self)
        self._icon.setFixedWidth(20)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._name = QLabel(job.name, self)
        self._name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self._status = QLabel(self)
        self._status.setObjectName("Hint")

        self._progress = QProgressBar(self)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.hide()

        self._remove = QPushButton("✕", self)
        self._remove.setObjectName("Link")
        self._remove.setFixedSize(26, 26)
        self._remove.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove.clicked.connect(lambda: self.removeRequested.emit(self._job))

        self._open = QPushButton(tr("settings.output.open"), self)
        self._open.setObjectName("Link")
        self._open.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open.clicked.connect(self._open_result)
        self._open.hide()

        texts = QVBoxLayout()
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(2)
        texts.addWidget(self._name)
        texts.addWidget(self._status)
        texts.addWidget(self._progress)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 8)
        layout.setSpacing(10)
        layout.addWidget(self._icon)
        layout.addLayout(texts, 1)
        layout.addWidget(self._open)
        layout.addWidget(self._remove)

        self.refresh()

    # ------------------------------------------------------------------
    @property
    def job(self) -> Job:
        """Der in dieser Zeile dargestellte Auftrag."""
        return self._job

    def set_removable(self, removable: bool) -> None:
        """Während der Verarbeitung darf nichts aus der Liste verschwinden."""
        self._remove.setVisible(removable)

    def set_progress(self, current: int, total: int, phase_key: str) -> None:
        """Aktualisiert Fortschrittsbalken und Statuszeile eines laufenden Auftrags."""
        self._progress.show()
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(min(current, total))
            detail = tr("progress.page", page=min(max(current, 1), total), pages=total)
            self._status.setText(f"{tr(phase_key)}, {detail}")
        else:
            # Seitenzahl unbekannt: laufender Balken statt falscher Prozentzahl.
            self._progress.setRange(0, 0)
            self._status.setText(tr(phase_key))

    def refresh(self) -> None:
        """Stellt Symbol, Text und Schaltflächen passend zum Zustand ein."""
        job = self._job
        self._icon.setText(_STATUS_ICON.get(job.status, ""))
        token = _STATUS_COLOR_TOKEN.get(job.status)
        color = self._colors.get(token or "muted", self._colors["muted"])
        self._icon.setStyleSheet(f"color: {color}; font-size: 14px;")

        if job.status is JobStatus.RUNNING:
            self._name.setStyleSheet("font-weight: 600;")
        else:
            self._name.setStyleSheet("")
            self._progress.hide()

        if job.message:
            self._status.setText(job.message)
        else:
            self._status.setText(tr(job.status.label_key))

        if job.status is JobStatus.FAILED:
            self._status.setStyleSheet(f"color: {self._colors['danger']}; font-size: 12px;")
        else:
            self._status.setStyleSheet("")

        self._open.setVisible(job.status is JobStatus.DONE and job.target is not None)
        self._open.setText(tr("settings.output.open"))

    def _open_result(self) -> None:
        """Meldet den Wunsch, den Ordner der fertigen Datei zu öffnen."""
        if self._job.target is not None:
            self.openRequested.emit(self._job.target)


class FileListPanel(QWidget):
    """Verwaltet die Liste der Aufträge."""

    countChanged = Signal(int)

    def __init__(self, colors: Dict[str, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._colors = colors
        self._jobs: List[Job] = []

        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._empty = QLabel(tr("list.empty"), self)
        self._empty.setObjectName("Hint")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._empty)
        layout.addWidget(self._list, 1)
        self._update_empty_state()

    # ------------------------------------------------------------------
    @property
    def jobs(self) -> List[Job]:
        """Die Aufträge in der Reihenfolge der Anzeige."""
        return self._jobs

    def add_paths(self, paths: List[Path]) -> int:
        """Fügt Dateien hinzu und überspringt bereits vorhandene. Liefert die Anzahl neuer Dateien."""
        known = {job.source.resolve() for job in self._jobs}
        added = 0
        for path in paths:
            # Immer absolut speichern. Ein relativer Pfad wie "-datei.pdf" würde
            # von OCRmyPDF sonst als Schalter statt als Dateiname gelesen.
            absolut = Path(os.path.abspath(path))
            try:
                resolved = absolut.resolve()
            except OSError:
                resolved = absolut
            if resolved in known:
                continue
            known.add(resolved)
            job = Job(source=absolut)
            self._jobs.append(job)
            self._append_widget(job)
            added += 1
        if added:
            self._update_empty_state()
            self.countChanged.emit(len(self._jobs))
        return added

    def _append_widget(self, job: Job) -> None:
        """Hängt eine neue Zeile für einen Auftrag an die Liste an."""
        widget = JobItemWidget(job, self._colors)
        widget.removeRequested.connect(self.remove_job)
        widget.openRequested.connect(_reveal_in_file_manager)
        item = QListWidgetItem(self._list)
        self._list.addItem(item)
        self._list.setItemWidget(item, widget)
        self._sync_item_height(self._list.count() - 1)

    def _sync_item_height(self, row: int) -> None:
        """Passt die Zeilenhöhe an den tatsächlichen Platzbedarf an.

        Nötig, weil der Fortschrittsbalken erst während der Verarbeitung
        eingeblendet wird. Ohne diese Anpassung behielte die Zeile ihre beim
        Anlegen berechnete Höhe, und Name, Status und Balken würden einander
        überlappen.
        """
        item = self._list.item(row)
        widget = self._widget_at(row)
        if item is None or widget is None:
            return
        layout = widget.layout()
        if layout is not None:
            layout.activate()
        height = widget.sizeHint().height()
        if item.sizeHint().height() != height:
            item.setSizeHint(QSize(0, height))

    def remove_job(self, job: Job) -> None:
        """Entfernt einen Auftrag aus der Liste."""
        for row in range(self._list.count()):
            widget = self._widget_at(row)
            if widget is not None and widget.job is job:
                self._list.takeItem(row)
                break
        if job in self._jobs:
            self._jobs.remove(job)
        self._update_empty_state()
        self.countChanged.emit(len(self._jobs))

    def clear(self) -> None:
        """Leert die gesamte Warteschlange."""
        self._list.clear()
        self._jobs.clear()
        self._update_empty_state()
        self.countChanged.emit(0)

    def reset_statuses(self) -> None:
        """Setzt alle Aufträge vor einem neuen Durchlauf zurück."""
        for job in self._jobs:
            job.reset()
        self.refresh_all()

    def refresh_all(self) -> None:
        """Zeichnet alle Zeilen neu."""
        for row in range(self._list.count()):
            widget = self._widget_at(row)
            if widget is not None:
                widget.refresh()
                self._sync_item_height(row)

    def refresh_job(self, index: int) -> None:
        """Zeichnet die Zeile eines einzelnen Auftrags neu."""
        widget = self._widget_at(index)
        if widget is not None:
            widget.refresh()
            self._sync_item_height(index)

    def set_progress(self, index: int, current: int, total: int, phase_key: str) -> None:
        """Aktualisiert Fortschrittsbalken und Statuszeile eines Auftrags."""
        widget = self._widget_at(index)
        if widget is not None:
            widget.set_progress(current, total, phase_key)
            self._sync_item_height(index)

    def set_editable(self, editable: bool) -> None:
        """Schaltet die Entfernen-Schaltflächen an oder aus."""
        for row in range(self._list.count()):
            widget = self._widget_at(row)
            if widget is not None:
                widget.set_removable(editable)
                self._sync_item_height(row)

    def scroll_to(self, index: int) -> None:
        """Rollt die Liste zu einem bestimmten Auftrag."""
        item = self._list.item(index)
        if item is not None:
            self._list.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)

    def retranslate(self) -> None:
        """Setzt alle Beschriftungen neu, etwa nach einem Sprachwechsel."""
        self._empty.setText(tr("list.empty"))
        self.refresh_all()

    # ------------------------------------------------------------------
    def _widget_at(self, row: int) -> Optional[JobItemWidget]:
        """Liefert das Zeilenwidget einer Zeilennummer, sonst None."""
        item = self._list.item(row)
        if item is None:
            return None
        widget = self._list.itemWidget(item)
        return widget if isinstance(widget, JobItemWidget) else None

    def _update_empty_state(self) -> None:
        """Zeigt je nach Füllstand die Liste oder den Hinweistext."""
        has_jobs = bool(self._jobs)
        self._list.setVisible(has_jobs)
        self._empty.setVisible(not has_jobs)


def _reveal_in_file_manager(path: Path) -> None:
    """Öffnet den Ordner der fertigen Datei im Dateimanager."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
