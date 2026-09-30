"""Dialog zum Nachladen weiterer Sprachen für die Texterkennung."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QSize, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ocrmypdf_gui import dependencies, tessdata
from ocrmypdf_gui import languages as language_names
from ocrmypdf_gui.i18n import tr
from ocrmypdf_gui.ui.widgets import Field


class IndexWorker(QThread):
    """Holt die Liste der verfügbaren Sprachen im Hintergrund."""

    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, variant: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._variant = variant

    def run(self) -> None:
        """Ruft die Liste ab und meldet Ergebnis oder Fehler."""
        try:
            self.finished_ok.emit(tessdata.fetch_index(self._variant))
        except tessdata.DownloadError as fehler:
            self.failed.emit(fehler.message_key)


class DownloadWorker(QThread):
    """Lädt eine einzelne Sprachdatei im Hintergrund."""

    progress = Signal(int, int)
    finished_ok = Signal(str)
    failed = Signal(str, str)

    def __init__(self, code: str, variant: str, target: Path,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._code = code
        self._variant = variant
        self._target = target
        self._cancelled = False

    def cancel(self) -> None:
        """Bricht den laufenden Download ab."""
        self._cancelled = True

    def run(self) -> None:
        """Lädt die Datei und meldet Fortschritt, Ergebnis oder Fehler."""
        try:
            tessdata.download_language(
                self._code, self._variant, self._target,
                progress=lambda geladen, gesamt: self.progress.emit(geladen, gesamt),
                cancelled=lambda: self._cancelled,
            )
            self.finished_ok.emit(self._code)
        except tessdata.DownloadError as fehler:
            self.failed.emit(self._code, fehler.message_key)


class LanguageRow(QWidget):
    """Eine Zeile der Sprachliste mit Größe und Schaltfläche."""

    actionRequested = Signal(str, bool)  # Sprachcode, installieren?

    def __init__(self, code: str, size: int, installed: bool,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._code = code

        self._name = QLabel(language_names.display_name(code, tr.language), self)
        self._size = QLabel(f"{size / 1048576:.1f} MB" if size else "", self)
        self._size.setObjectName("Hint")
        self._size.setFixedWidth(70)
        self._size.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._state = QLabel(self)
        self._state.setObjectName("Hint")
        self._state.setFixedWidth(80)

        self._button = QPushButton(self)
        self._button.setFixedWidth(100)
        self._button.clicked.connect(
            lambda: self.actionRequested.emit(self._code, not self._installed)
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 8, 5)
        layout.setSpacing(10)
        layout.addWidget(self._name, 1)
        layout.addWidget(self._size)
        layout.addWidget(self._state)
        layout.addWidget(self._button)

        self._installed = installed
        self.set_installed(installed)

    @property
    def code(self) -> str:
        """Der Sprachcode dieser Zeile."""
        return self._code

    @property
    def text(self) -> str:
        """Der angezeigte Name, für die Suche."""
        return self._name.text()

    def set_installed(self, installed: bool) -> None:
        """Stellt Zustandstext und Schaltfläche auf installiert oder nicht."""
        self._installed = installed
        self._state.setText(tr("download.state.installed") if installed else "")
        self._button.setText(
            tr("download.action.remove") if installed else tr("download.action.download")
        )
        self._button.setObjectName("Danger" if installed else "")
        self._button.style().unpolish(self._button)
        self._button.style().polish(self._button)

    def set_busy(self, busy: bool) -> None:
        """Sperrt die Schaltfläche, solange etwas läuft."""
        self._button.setEnabled(not busy)


class DownloadDialog(QDialog):
    """Listet alle verfügbaren Sprachen auf und lädt sie auf Wunsch herunter."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("download.title"))
        self.setMinimumSize(560, 560)

        self._index: Dict[str, int] = {}
        self._rows: List[LanguageRow] = []
        self._index_worker: Optional[IndexWorker] = None
        self._download_worker: Optional[DownloadWorker] = None
        self._changed = False

        intro = QLabel(tr("download.intro"), self)
        intro.setObjectName("Hint")
        intro.setWordWrap(True)

        self._variant = QComboBox(self)
        for schluessel in ("fast", "best"):
            self._variant.addItem(tr(f"download.variant.{schluessel}"), schluessel)
        self._variant.currentIndexChanged.connect(self._reload_index)
        variant_field = Field(tr("download.variant"), self._variant, tr("download.variant.help"))

        self._search = QLineEdit(self)
        self._search.setPlaceholderText(tr("download.search"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)

        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self._status = QLabel(tr("download.loading"), self)
        self._status.setObjectName("Hint")
        self._status.setWordWrap(True)

        self._progress = QProgressBar(self)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.hide()

        self._close = QPushButton(tr("action.close"), self)
        self._close.setObjectName("Primary")
        self._close.clicked.connect(self.accept)

        unten = QHBoxLayout()
        unten.setContentsMargins(0, 0, 0, 0)
        unten.addStretch(1)
        unten.addWidget(self._close)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(intro)
        layout.addWidget(variant_field)
        layout.addWidget(self._search)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._status)
        layout.addWidget(self._progress)
        layout.addLayout(unten)

        self._reload_index()

    # ------------------------------------------------------------------
    @property
    def changed(self) -> bool:
        """True, wenn Sprachen hinzugekommen oder entfernt wurden."""
        return self._changed

    def _current_variant(self) -> str:
        """Der Schlüssel der gewählten Modellqualität."""
        return str(self._variant.currentData())

    def _installed(self) -> List[str]:
        """Aktuell verfügbare Sprachen, egal aus welchem Ordner."""
        return dependencies.available_languages()

    # ------------------------------------------------------------------
    def _reload_index(self) -> None:
        """Holt die Sprachliste für die gewählte Modellqualität."""
        self._list.clear()
        self._rows.clear()
        self._status.setText(tr("download.loading"))
        self._set_busy(True)

        self._index_worker = IndexWorker(self._current_variant(), self)
        self._index_worker.finished_ok.connect(self._on_index)
        self._index_worker.failed.connect(self._on_index_failed)
        self._index_worker.start()

    def _on_index(self, index: Dict[str, int]) -> None:
        """Baut die Liste aus der abgerufenen Übersicht auf."""
        self._index = index
        vorhanden = set(self._installed())
        codes = language_names.order_for_display(list(index), tr.language)

        for code in codes:
            zeile = LanguageRow(code, index.get(code, 0), code in vorhanden)
            zeile.actionRequested.connect(self._on_action)
            eintrag = QListWidgetItem(self._list)
            eintrag.setSizeHint(QSize(0, zeile.sizeHint().height()))
            self._list.addItem(eintrag)
            self._list.setItemWidget(eintrag, zeile)
            self._rows.append(zeile)

        self._set_busy(False)
        self._update_status()
        self._apply_filter(self._search.text())

    def _on_index_failed(self, message_key: str) -> None:
        """Zeigt an, dass die Liste nicht geladen werden konnte."""
        self._status.setText(tr(message_key))
        self._set_busy(False)

    def _update_status(self) -> None:
        """Schreibt fort, wie viele Sprachen installiert sind."""
        installiert = len([z for z in self._rows if z.code in set(self._installed())])
        self._status.setText(
            tr("download.count", installed=installiert, total=len(self._rows))
        )

    # ------------------------------------------------------------------
    def _on_action(self, code: str, install: bool) -> None:
        """Lädt eine Sprache herunter oder entfernt sie wieder."""
        if install:
            self._start_download(code)
        else:
            self._remove(code)

    def _start_download(self, code: str) -> None:
        # Vor dem ersten Download den Bestand ins Benutzerprofil übernehmen,
        # weil der Ordner im Programmpaket schreibgeschützt ist.
        """Startet den Download einer Sprache im Hintergrund."""
        ziel = tessdata.ensure_user_dir(dependencies.effective_tessdata_dir())
        self._set_busy(True)
        self._progress.setRange(0, 0)
        self._progress.show()
        self._status.setText(tr("download.progress", name=language_names.display_name(code, tr.language)))

        self._download_worker = DownloadWorker(code, self._current_variant(), ziel, self)
        self._download_worker.progress.connect(self._on_progress)
        self._download_worker.finished_ok.connect(self._on_downloaded)
        self._download_worker.failed.connect(self._on_download_failed)
        self._download_worker.start()

    def _on_progress(self, geladen: int, gesamt: int) -> None:
        """Zeigt den Fortschritt des laufenden Downloads."""
        if gesamt > 0:
            self._progress.setRange(0, gesamt)
            self._progress.setValue(geladen)
        else:
            self._progress.setRange(0, 0)

    def _on_downloaded(self, code: str) -> None:
        """Übernimmt eine fertig geladene Sprache in die Anzeige."""
        dependencies.clear_cache()
        self._changed = True
        self._progress.hide()
        self._set_busy(False)
        self._refresh_rows()
        self._status.setText(
            tr("download.done", name=language_names.display_name(code, tr.language))
        )

    def _on_download_failed(self, code: str, message_key: str) -> None:
        """Meldet einen fehlgeschlagenen Download."""
        self._progress.hide()
        self._set_busy(False)
        self._status.setText(tr(message_key))

    def _remove(self, code: str) -> None:
        """Entfernt eine nachinstallierte Sprache."""
        name = language_names.display_name(code, tr.language)
        # Hilfsmodelle wie "osd" stehen nicht zur Auswahl und werden von
        # Einstellungen wie "Seiten automatisch drehen" gebraucht.
        if not language_names.is_selectable(code):
            return
        # Ohne Sprache wäre die Texterkennung nicht mehr startbar.
        if len([c for c in self._installed() if language_names.is_selectable(c)]) <= 1:
            self._status.setText(tr("download.lastLanguage"))
            return
        # Nur was im Benutzerprofil liegt, lässt sich löschen.
        tessdata.ensure_user_dir(dependencies.effective_tessdata_dir())
        if tessdata.remove_language(code):
            dependencies.clear_cache()
            self._changed = True
            self._refresh_rows()
            self._status.setText(tr("download.removed", name=name))
        else:
            self._status.setText(tr("download.removeFailed", name=name))

    def _refresh_rows(self) -> None:
        """Gleicht den Zustand aller Zeilen mit dem Dateisystem ab."""
        vorhanden = set(self._installed())
        for zeile in self._rows:
            zeile.set_installed(zeile.code in vorhanden)
        self._update_status()

    def _set_busy(self, busy: bool) -> None:
        """Sperrt Bedienelemente, solange eine Netzanfrage läuft."""
        self._variant.setEnabled(not busy)
        for zeile in self._rows:
            zeile.set_busy(busy)

    def _apply_filter(self, text: str) -> None:
        """Blendet Zeilen aus, die nicht zum Suchbegriff passen."""
        suche = text.strip().lower()
        for zeile, reihe in zip(self._rows, range(self._list.count())):
            eintrag = self._list.item(reihe)
            if eintrag is not None:
                eintrag.setHidden(bool(suche) and suche not in zeile.text.lower())

    def closeEvent(self, event) -> None:  # noqa: N802
        """Bricht einen laufenden Download ab, bevor das Fenster schließt."""
        for arbeiter in (self._index_worker, self._download_worker):
            if arbeiter is not None and arbeiter.isRunning():
                if isinstance(arbeiter, DownloadWorker):
                    arbeiter.cancel()
                arbeiter.wait(4000)
        super().closeEvent(event)
