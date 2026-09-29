"""Das Hauptfenster: Ablagebereich, Warteschlange, Einstellungen und Start."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QDesktopServices,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ocrmypdf_gui import __app_name__, config
from ocrmypdf_gui.i18n import tr
from ocrmypdf_gui.models import ExportSettings, JobStatus, OutputMode
from ocrmypdf_gui.runner import JobResult, OcrRunner
from ocrmypdf_gui.ui.drop_area import DropArea, split_pdf_paths, paths_from_mime
from ocrmypdf_gui.ui.file_list import FileListPanel
from ocrmypdf_gui.ui.settings_panel import SettingsPanel
from ocrmypdf_gui.ui.widgets import Card, CollapsibleSection, value_label

# Wie viele Protokollzeilen höchstens vorgehalten werden.
_MAX_LOG_LINES = 4000


class MainWindow(QMainWindow):
    """Bringt alle Bausteine zusammen und steuert den Ablauf."""

    languageChanged = Signal(str)

    def __init__(self, settings: ExportSettings, colors: Dict[str, str]) -> None:
        super().__init__()
        self._settings = settings
        self._colors = colors
        self._runner: Optional[OcrRunner] = None
        # Eigenes Kennzeichen statt QThread.isRunning(): das liefert direkt
        # nach start() noch kurz False und würde die Oberfläche freigeben.
        self._running = False
        self._results: List[JobResult] = []
        self._current_index = -1
        self._log_buffer: List[str] = []

        self.setWindowTitle(__app_name__)
        self.setMinimumSize(1000, 700)
        self.resize(1120, 780)
        # Dateien dürfen überall im Fenster abgelegt werden, nicht nur auf der
        # gestrichelten Fläche; siehe dragEnterEvent/dropEvent weiter unten.
        self.setAcceptDrops(True)

        self._build_ui()
        self._retranslate()
        self._update_controls()

    # ------------------------------------------------------------------
    # Aufbau
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Setzt das Fenster aus Kopfbereich, Spalten, Protokoll und Aktionsleiste zusammen."""
        central = QWidget(self)
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(14)
        outer.addWidget(self._build_header())

        columns = QHBoxLayout()
        columns.setSpacing(16)
        columns.addWidget(self._build_left_column(), 3)
        columns.addWidget(self._build_right_column(), 2)
        outer.addLayout(columns, 1)

        outer.addWidget(self._build_log_section())
        outer.addWidget(self._build_action_bar())

    def _build_header(self) -> QWidget:
        """Baut den Kopfbereich mit Titel und Untertitel."""
        header = QWidget(self)
        self._header_title = QLabel(__app_name__, header)
        self._header_title.setObjectName("HeaderTitle")
        self._header_subtitle = QLabel(header)
        self._header_subtitle.setObjectName("HeaderSubtitle")

        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._header_title)
        layout.addWidget(self._header_subtitle)
        return header

    def _build_left_column(self) -> QWidget:
        """Baut die linke Spalte aus Ablagebereich und Warteschlange."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # --- Ablagebereich ---
        self._drop_area = DropArea(container)
        self._drop_area.filesDropped.connect(self.add_files)
        self._drop_area.filesRejected.connect(self._warn_rejected)
        layout.addWidget(self._drop_area)

        # --- Warteschlange ---
        self._queue_card = Card(tr("list.header"), container)
        self._file_list = FileListPanel(self._colors, self._queue_card)
        self._file_list.countChanged.connect(self._on_count_changed)

        self._count_label = value_label("", self._queue_card)
        self._add_button = QPushButton(self._queue_card)
        self._add_button.clicked.connect(self._drop_area.open_file_dialog)
        self._clear_button = QPushButton(self._queue_card)
        self._clear_button.setObjectName("Danger")
        self._clear_button.clicked.connect(self._file_list.clear)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        controls.addWidget(self._count_label, 1)
        controls.addWidget(self._add_button)
        controls.addWidget(self._clear_button)

        self._queue_card.body.addWidget(self._file_list, 1)
        self._queue_card.body.addLayout(controls)
        layout.addWidget(self._queue_card, 1)
        return container

    def _build_right_column(self) -> QWidget:
        # Die Einstellungen können durch die erweiterten Optionen hoch werden,
        # deshalb stecken sie in einem scrollbaren Bereich.
        """Baut die rechte Spalte mit den Export-Einstellungen."""
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        holder = QWidget(scroll)
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 4, 0)
        holder_layout.setSpacing(12)

        self._settings_panel = SettingsPanel(self._settings, holder)
        self._settings_panel.settingsChanged.connect(self._on_settings_changed)
        self._settings_panel.uiLanguageChanged.connect(self._on_ui_language_changed)
        holder_layout.addWidget(self._settings_panel)

        self._target_preview = value_label("", holder)
        holder_layout.addWidget(self._target_preview)
        holder_layout.addStretch(1)

        scroll.setWidget(holder)
        return scroll

    def _build_log_section(self) -> QWidget:
        """Baut den aufklappbaren Protokollbereich."""
        self._log_section = CollapsibleSection(tr("log.show"), self)

        self._log_view = QPlainTextEdit(self)
        self._log_view.setObjectName("Log")
        self._log_view.setReadOnly(True)
        # Ohne Obergrenze wüchse das Anzeigefeld bei vielen Dateien unbegrenzt.
        self._log_view.setMaximumBlockCount(_MAX_LOG_LINES)
        self._log_view.setMaximumHeight(170)
        self._log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self._log_verbose = QCheckBox(self)
        self._log_verbose.toggled.connect(self._rebuild_log_view)

        self._log_save = QPushButton(self)
        self._log_save.setObjectName("Link")
        self._log_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self._log_save.clicked.connect(self._save_log)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(10)
        controls.addWidget(self._log_verbose)
        controls.addStretch(1)
        controls.addWidget(self._log_save)

        self._log_section.content.addWidget(self._log_view)
        self._log_section.content.addLayout(controls)
        return self._log_section

    def _build_action_bar(self) -> QWidget:
        """Baut die Leiste mit Statuszeile, Fortschritt und Startknopf."""
        bar = QWidget(self)

        self._status_label = QLabel(bar)
        self._status_label.setObjectName("StatusText")

        self._progress = QProgressBar(bar)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)

        self._start_button = QPushButton(bar)
        self._start_button.setObjectName("Primary")
        self._start_button.setMinimumWidth(170)
        self._start_button.clicked.connect(self._on_start_clicked)

        self._open_output_button = QPushButton(bar)
        self._open_output_button.clicked.connect(self._open_output_folder)
        self._open_output_button.setVisible(False)

        texts = QVBoxLayout()
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(6)
        texts.addWidget(self._status_label)
        texts.addWidget(self._progress)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addLayout(texts, 1)
        layout.addWidget(self._open_output_button)
        layout.addWidget(self._start_button)
        return bar

    # ------------------------------------------------------------------
    # Dateien
    # ------------------------------------------------------------------
    def add_files(self, paths: List[Path]) -> None:
        """Legt PDF-Dateien in die Warteschlange."""
        added = self._file_list.add_paths(list(paths))
        if added == 0 and paths:
            self._status_label.setText(tr("list.duplicate"))
        self._update_controls()

    def _warn_rejected(self, paths: List[Path]) -> None:
        """Weist freundlich darauf hin, dass nur PDF-Dateien verarbeitet werden."""
        names = "\n".join(f"• {path.name}" for path in paths[:8])
        if len(paths) > 8:
            names += f"\n… (+{len(paths) - 8})"
        QMessageBox.information(
            self, tr("msg.rejected.title"), tr("msg.rejected.text", files=names)
        )

    def _on_count_changed(self, _count: int) -> None:
        """Reagiert auf eine geänderte Anzahl von Aufträgen."""
        self._update_controls()

    # ------------------------------------------------------------------
    # Einstellungen
    # ------------------------------------------------------------------
    def _on_settings_changed(self) -> None:
        """Übernimmt geänderte Einstellungen und sichert sie sofort."""
        self._settings = self._settings_panel.settings
        config.save_settings(self._settings)
        self._update_target_preview()

    def _on_ui_language_changed(self, _code: str) -> None:
        """Sprache der Oberfläche wurde umgestellt, alles neu beschriften."""
        self._retranslate()

    def _update_target_preview(self) -> None:
        """Zeigt beispielhaft, wo die erste Datei landen wird."""
        jobs = self._file_list.jobs
        if not jobs:
            if self._settings.output_mode is OutputMode.SUBFOLDER:
                self._target_preview.setText(tr("settings.output.sameAsSource"))
            else:
                self._target_preview.setText(self._settings.output_folder or "")
            return
        target = self._settings.target_path_for(jobs[0].source)
        self._target_preview.setText(f"→  {_shorten_path(target)}")

    # ------------------------------------------------------------------
    # Verarbeitung
    # ------------------------------------------------------------------
    def _on_start_clicked(self) -> None:
        """Startet die Verarbeitung oder bricht eine laufende ab."""
        if self._running:
            self._cancel_run()
        else:
            self._start_run()

    def _start_run(self) -> None:
        """Prüft die Voraussetzungen und startet die Verarbeitung."""
        jobs = self._file_list.jobs
        if not jobs:
            QMessageBox.information(self, tr("msg.noFiles.title"), tr("msg.noFiles.text"))
            return

        self._settings = self._settings_panel.settings
        if not self._settings.languages:
            QMessageBox.warning(self, tr("msg.noLanguage.title"), tr("msg.noLanguage.text"))
            return

        # Zielordner früh anlegen, damit Rechteprobleme sofort auffallen.
        if self._settings.output_mode is OutputMode.FIXED:
            folder = Path(self._settings.output_folder or "")
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError as error:
                QMessageBox.critical(
                    self, tr("msg.badOutput.title"), tr("msg.badOutput.text", error=str(error))
                )
                return

        config.save_settings(self._settings)
        self._results.clear()
        self._log_buffer.clear()
        self._log_view.clear()
        self._file_list.reset_statuses()
        self._open_output_button.setVisible(False)

        self._progress.setRange(0, len(jobs))
        self._progress.setValue(0)

        self._runner = OcrRunner(jobs, self._settings, self)
        self._runner.jobStarted.connect(self._on_job_started)
        self._runner.jobProgress.connect(self._on_job_progress)
        self._runner.jobFinished.connect(self._on_job_finished)
        self._runner.logLine.connect(self._on_log_line)
        self._runner.runFinished.connect(self._on_run_finished)
        self._running = True
        self._runner.start()
        self._update_controls()

    def _cancel_run(self) -> None:
        """Fordert den Abbruch der laufenden Verarbeitung an."""
        if self._runner is not None:
            self._status_label.setText(tr("progress.cancelling"))
            self._start_button.setEnabled(False)
            self._runner.cancel()

    def _on_job_started(self, index: int, page_count: int) -> None:
        """Vermerkt den Beginn eines Auftrags in Liste und Statuszeile."""
        jobs = self._file_list.jobs
        if index >= len(jobs):
            return
        self._current_index = index
        job = jobs[index]
        job.status = JobStatus.RUNNING
        job.page_count = page_count
        job.message = ""
        self._file_list.refresh_job(index)
        self._file_list.scroll_to(index)
        self._status_label.setText(
            tr("progress.file", current=index + 1, total=len(jobs), name=job.name)
        )

    def _on_job_progress(self, index: int, current: int, total: int, phase_key: str) -> None:
        """Reicht den Fortschritt an die Zeile des Auftrags weiter."""
        self._file_list.set_progress(index, current, total, phase_key)

    def _on_job_finished(self, result: JobResult) -> None:
        """Übernimmt das Ergebnis eines Auftrags."""
        jobs = self._file_list.jobs
        if result.index >= len(jobs):
            return
        job = jobs[result.index]
        job.status = result.status
        job.target = result.target
        job.message = _result_message(result)
        self._file_list.refresh_job(result.index)
        self._results.append(result)
        self._progress.setValue(len(self._results))

    def _on_run_finished(self, cancelled: bool) -> None:
        """Fasst den Durchlauf zusammen und gibt die Bedienelemente frei."""
        self._running = False
        self._runner = None
        self._current_index = -1
        done = sum(1 for r in self._results if r.status is JobStatus.DONE)
        failed = sum(1 for r in self._results if r.status is JobStatus.FAILED)
        skipped = sum(1 for r in self._results if r.status is JobStatus.SKIPPED)
        stopped = sum(1 for r in self._results if r.status is JobStatus.CANCELLED)

        # Abgebrochen und übersprungen sind verschiedene Dinge und werden nur
        # genannt, wenn sie tatsächlich vorkommen.
        summary = tr("progress.summary", done=done, failed=failed)
        if skipped:
            summary += tr("progress.summary.skipped", count=skipped)
        if stopped:
            summary += tr("progress.summary.cancelled", count=stopped)
        prefix = tr("action.cancel") if cancelled else tr("progress.finished")
        self._status_label.setText(f"{prefix}: {summary}")
        self._open_output_button.setVisible(done > 0)
        self._start_button.setEnabled(True)
        self._update_controls()

    # ------------------------------------------------------------------
    # Protokoll
    # ------------------------------------------------------------------
    def _on_log_line(self, line: str, noise: bool) -> None:
        """Nimmt eine Protokollzeile entgegen und zeigt sie bei Bedarf an."""
        self._log_buffer.append(f"{'~' if noise else ' '}{line}")
        del self._log_buffer[:-_MAX_LOG_LINES]
        if noise and not self._log_verbose.isChecked():
            return
        self._append_log_line(line)

    def _append_log_line(self, line: str) -> None:
        """Hängt eine Zeile an; rollt nur mit, wenn der Nutzer unten steht."""
        scrollbar = self._log_view.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 4
        self._log_view.appendPlainText(line)
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _rebuild_log_view(self) -> None:
        """Baut die Anzeige neu auf, wenn zwischen kurz und ausführlich gewechselt wird."""
        verbose = self._log_verbose.isChecked()
        lines = [
            entry[1:] for entry in self._log_buffer if verbose or not entry.startswith("~")
        ]
        self._log_view.setPlainText("\n".join(lines))
        scrollbar = self._log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _save_log(self) -> None:
        """Schreibt das vollständige Protokoll in eine Datei."""
        name, _filter = QFileDialog.getSaveFileName(
            self, tr("log.saveDialog"), str(Path.home() / "ocrmypdf-gui-log.txt"), "*.txt"
        )
        if not name:
            return
        try:
            Path(name).write_text(
                "\n".join(entry[1:] for entry in self._log_buffer), encoding="utf-8"
            )
            self._status_label.setText(tr("log.savedTo", path=name))
        except OSError as error:
            QMessageBox.warning(self, tr("log.saveDialog"), str(error))

    # ------------------------------------------------------------------
    # Zustand der Bedienelemente
    # ------------------------------------------------------------------
    def _update_controls(self) -> None:
        """Stellt alle Bedienelemente auf den aktuellen Zustand ein."""
        running = self._running
        count = len(self._file_list.jobs)

        self._start_button.setText(tr("action.cancel") if running else tr("action.start"))
        self._start_button.setEnabled(running or count > 0)
        self._settings_panel.setEnabled(not running)
        self._drop_area.setEnabled(not running)
        self._add_button.setEnabled(not running)
        self._clear_button.setEnabled(not running and count > 0)
        self._file_list.set_editable(not running)

        if count == 1:
            self._count_label.setText(tr("list.count.one"))
        elif count:
            self._count_label.setText(tr("list.count.many", count=count))
        else:
            self._count_label.setText("")

        if not running and not self._results:
            self._status_label.setText(tr("progress.idle"))
            self._progress.setValue(0)

        self._update_target_preview()

    def _open_output_folder(self) -> None:
        """Öffnet den Ordner der zuletzt erzeugten Datei."""
        for result in reversed(self._results):
            if result.status is JobStatus.DONE and result.target is not None:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(result.target.parent)))
                return

    # ------------------------------------------------------------------
    # Sprache und Schließen
    # ------------------------------------------------------------------
    def _retranslate(self) -> None:
        """Setzt sämtliche Beschriftungen neu, etwa nach einem Sprachwechsel."""
        self._header_subtitle.setText(tr("app.subtitle"))
        self._drop_area.retranslate()
        self._queue_card.set_title(tr("list.header"))
        self._add_button.setText(tr("list.add"))
        self._clear_button.setText(tr("list.clear"))
        self._file_list.retranslate()
        self._settings_panel.retranslate()
        self._log_section.set_title(tr("log.show"))
        self._log_verbose.setText(tr("log.showAll"))
        self._log_save.setText(tr("log.save"))
        self._open_output_button.setText(tr("action.openOutput"))
        self._update_controls()

    # ------------------------------------------------------------------
    # Ziehen und Ablegen im gesamten Fenster
    # ------------------------------------------------------------------
    # Die folgenden Methoden überschreiben Qt-Ereignisse. Ihre Namen folgen
    # dem Schema von Qt, nicht dem von PEP 8; daher jeweils "noqa: N802".
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """Nimmt PDF-Dateien an, die irgendwo im Fenster abgelegt werden."""
        if self._running:
            event.ignore()
            return
        paths = paths_from_mime(event)
        accepted, _rejected = split_pdf_paths(paths) if paths else ([], [])
        if accepted:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802
        """Hält die Annahme aufrecht, solange das Fenster Dateien entgegennimmt."""
        if not self._running and paths_from_mime(event):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """Übernimmt Dateien, die irgendwo im Fenster abgelegt wurden."""
        if self._running:
            event.ignore()
            return
        accepted, rejected = split_pdf_paths(paths_from_mime(event))
        if accepted:
            event.acceptProposedAction()
            self.add_files(accepted)
        if rejected:
            self._warn_rejected(rejected)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Fragt nach, wenn beim Schließen noch eine Verarbeitung läuft."""
        if self._running and self._runner is not None:
            answer = QMessageBox.question(
                self,
                tr("msg.busy.title"),
                tr("msg.busy.text"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._runner.cancel()
            self._runner.wait(5000)

        config.save_settings(self._settings_panel.settings)
        super().closeEvent(event)


def _shorten_path(path: Path, max_length: int = 64) -> str:
    """Kürzt einen Pfad für die Anzeige, ohne den Dateinamen zu verlieren.

    Das persönliche Verzeichnis wird zu ``~``; ist der Pfad dann immer noch
    lang, entfallen die mittleren Ordner. Der Dateiname bleibt stets sichtbar,
    denn er ist die Information, auf die es hier ankommt.
    """
    try:
        text = "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        text = str(path)
    if len(text) <= max_length:
        return text

    parts = Path(text).parts
    if len(parts) <= 3:
        return text
    # Anfang und Ende behalten, die Mitte durch ein Auslassungszeichen ersetzen.
    head = parts[0].rstrip("/")
    shortened = f"{head}/…/{parts[-2]}/{parts[-1]}"
    return shortened if len(shortened) < len(text) else text


def _result_message(result: JobResult) -> str:
    """Baut die Meldung, die unter dem Dateinamen erscheint."""
    if result.status is JobStatus.DONE:
        seconds = int(result.duration)
        return f"{tr('status.done')} ({tr('progress.elapsed', seconds=seconds)})"
    if not result.message_key:
        return ""
    text = tr(result.message_key)
    detail = _short_detail(result.message_detail)
    if detail:
        return f"{text} ({detail})"
    return text


def _short_detail(message_detail: str) -> str:
    """Wählt aus der technischen Meldung die aussagekräftigste Zeile.

    Vollständige Tracebacks stehen im Protokoll; in der Liste ist nur Platz für
    einen knappen Hinweis.
    """
    lines = [line.strip() for line in message_detail.splitlines() if line.strip()]
    if not lines:
        return ""
    # Eine Zeile der Form "SomeError: Beschreibung" ist am hilfreichsten.
    for line in reversed(lines):
        if ":" in line and not line.endswith(":"):
            _, _, remainder = line.partition(":")
            remainder = remainder.strip()
            if remainder:
                return remainder[:120]
    # Sonst bleibt der Name der Ausnahme - ohne den Modulpfad davor, der für
    # den Nutzer keinerlei Bedeutung hat.
    return lines[-1].rsplit(".", 1)[-1][:120]
