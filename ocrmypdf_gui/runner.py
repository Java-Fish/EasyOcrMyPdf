"""Ausführung der OCR-Aufträge in einem Hintergrund-Thread.

OCRmyPDF läuft bewusst als eigener Prozess und nicht als Bibliothek im
GUI-Prozess. Das hat drei Vorteile: die Oberfläche bleibt in jedem Fall
bedienbar, ein Absturz der Verarbeitung reißt die Anwendung nicht mit, und ein
Abbruch ist jederzeit sauber möglich.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from PySide6.QtCore import QThread, Signal

from ocrmypdf_gui import dependencies
from ocrmypdf_gui.models import ExportSettings, Job, JobStatus

# Verhindert das kurze Aufblitzen eines Konsolenfensters unter Windows.
_CREATION_FLAGS = 0x08000000 if sys.platform == "win32" else 0

# Exit-Codes von OCRmyPDF, übersetzt in Schlüssel der Sprachtabelle.
EXIT_CODE_KEYS = {
    1: "error.badArgs",
    2: "error.inputFile",
    3: "error.missingDependency",
    4: "error.outputFile",
    5: "error.invalidPdfa",
    6: "error.priorOcr",
    7: "error.childProcess",
    8: "error.encrypted",
    9: "error.invalidConfig",
    10: "error.pdfaConversion",
    15: "error.other",
}

# Zeilen, die OCRmyPDF bei "-v 1" ausgibt und die niemanden interessieren.
_NOISE = re.compile(
    r"""(?x)
    ^\s*(Running:|os\.symlink|stdout/stderr\s*=)   # interne Aufrufe
    | ^\s*\d+\s+(Running:|os\.symlink|OCR\ image\ needs)
    | ^script/                                      # Tesseract-Skriptmodelle
    | ^[a-z]{2,4}(_[A-Za-z]+)?$                     # nackte Sprachcodes
    | ^-\s                                          # Größenaufstellung
    | ocrmypdf\.io\.                                # temporäre Arbeitsdateien
    """
)

# "    2 Rasterizing page 2 with the pypdfium2 rasterizer" -> Seitennummer 2
_PAGE_LINE = re.compile(r"^\s+(\d+)\s+\S")
# Gesamtseitenzahl, falls sie nicht vorab ermittelt werden konnte.
_TOTAL_PAGES = re.compile(r"(?:Parsing|Processing)\s+(\d+)\s+pages|pages\s+1\s+through\s+(\d+)")

# Zeilen eines Python-Tracebacks: Dateiangaben und die Markierungszeilen aus
# Zirkumflexen und Tilden. Für den Nutzer sind sie wertlos.
_TRACEBACK_NOISE = re.compile(
    r"""(?x)
    ^\s*File\s+"           # File "/pfad/zu/modul.py", line 42, in ...
    | ^\s*Traceback\s*\(
    | ^[\s~^|+-]*$          # reine Markierungs- oder Leerzeilen
    """
)


def _useful_error_line(line: str) -> bool:
    """Taugt die Zeile als Hinweis in einer Fehlermeldung?"""
    stripped = line.strip()
    if not stripped or _TRACEBACK_NOISE.search(line):
        return False
    # Der eingerückte Quelltext eines Tracebacks hilft ebenfalls nicht weiter.
    return not (line.startswith("    ") and not stripped.endswith(":"))


@dataclass
class JobResult:
    """Ergebnis eines einzelnen Auftrags."""

    index: int
    status: JobStatus
    target: Optional[Path]
    message_key: str = ""
    message_detail: str = ""
    duration: float = 0.0


def count_pages(pdf_path: Path) -> int:
    """Ermittelt die Seitenzahl einer PDF-Datei; 0, wenn das nicht gelingt."""
    try:
        import pikepdf  # OCRmyPDF bringt pikepdf ohnehin mit.

        with pikepdf.open(pdf_path) as document:
            return len(document.pages)
    except Exception:
        # Ohne pikepdf (z. B. bei reiner CLI-Installation) fällt der
        # Fortschrittsbalken auf die Anzeige aus dem Protokoll zurück.
        return 0


class OcrRunner(QThread):
    """Arbeitet die Warteschlange nacheinander ab."""

    jobStarted = Signal(int, int)  # Index, Seitenzahl (0 = unbekannt)
    jobProgress = Signal(int, int, int, str)  # Index, Seite, Seiten gesamt, Phase
    jobFinished = Signal(object)  # JobResult
    logLine = Signal(str, bool)  # Text, ist_rauschen
    runFinished = Signal(bool)  # True, wenn abgebrochen wurde

    def __init__(self, jobs: Sequence[Job], settings: ExportSettings, parent=None) -> None:
        super().__init__(parent)
        self._jobs: List[Job] = list(jobs)
        self._settings = settings.copy()
        self._cancelled = False
        self._process: Optional[subprocess.Popen] = None

    # ------------------------------------------------------------------
    def cancel(self) -> None:
        """Bricht die Verarbeitung ab; der laufende Prozess wird beendet."""
        self._cancelled = True
        process = self._process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    @property
    def cancelled(self) -> bool:
        """True, wenn ein Abbruch angefordert wurde."""
        return self._cancelled

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Arbeitet die Warteschlange ab; wird von QThread beim Start aufgerufen."""
        command = dependencies.ocrmypdf_command()
        if command is None:
            for index, _job in enumerate(self._jobs):
                self.jobFinished.emit(
                    JobResult(index, JobStatus.FAILED, None, "error.noOcrmypdf")
                )
            self.runFinished.emit(False)
            return

        environment = dependencies.process_environment()
        for index, job in enumerate(self._jobs):
            if self._cancelled:
                self.jobFinished.emit(JobResult(index, JobStatus.CANCELLED, None))
                continue
            self._run_single(index, job, command, environment)

        self.runFinished.emit(self._cancelled)

    # ------------------------------------------------------------------
    def _run_single(self, index: int, job: Job, command: List[str], environment) -> None:
        """Verarbeitet eine Datei und meldet Fortschritt sowie Ergebnis."""
        started = time.monotonic()

        if not job.source.is_file():
            self.jobFinished.emit(JobResult(index, JobStatus.FAILED, None, "error.inputMissing"))
            return

        target = self._settings.target_path_for(job.source)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.jobFinished.emit(
                JobResult(index, JobStatus.FAILED, None, "error.outputFolder", str(error))
            )
            return

        total_pages = count_pages(job.source)
        self.jobStarted.emit(index, total_pages)

        arguments = [*command, "-v", "1", *self._settings.build_arguments(job.source, target)]
        self.logLine.emit(f"$ ocrmypdf {' '.join(arguments[len(command) + 2:])}", False)

        try:
            self._process = subprocess.Popen(
                arguments,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=environment,
                creationflags=_CREATION_FLAGS,
            )
        except OSError as error:
            self.jobFinished.emit(
                JobResult(index, JobStatus.FAILED, None, "error.launch", str(error))
            )
            return

        seen_pages: set[int] = set()
        phase = "phase.ocr"
        last_lines: List[str] = []

        assert self._process.stdout is not None
        for raw_line in self._process.stdout:
            line = raw_line.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue

            noise = bool(_NOISE.search(line))
            self.logLine.emit(line, noise)
            if not noise and _useful_error_line(line):
                last_lines.append(line)
                del last_lines[:-8]  # nur die letzten Zeilen für die Fehlermeldung behalten

            # --- Gesamtseitenzahl nachtragen, falls sie noch fehlt ---
            if total_pages == 0:
                match = _TOTAL_PAGES.search(line)
                if match:
                    total_pages = int(match.group(1) or match.group(2))

            # --- Phase und Seitenfortschritt ableiten ---
            new_phase = _phase_for(line)
            if new_phase is not None:
                phase = new_phase

            page_match = _PAGE_LINE.match(line)
            if page_match:
                seen_pages.add(int(page_match.group(1)))

            self.jobProgress.emit(index, len(seen_pages), total_pages, phase)

        return_code = self._process.wait()
        self._process = None
        duration = time.monotonic() - started

        if self._cancelled:
            # Halbfertige Ausgabedatei entfernen, damit nichts Kaputtes zurückbleibt.
            _remove_quietly(target)
            self.jobFinished.emit(JobResult(index, JobStatus.CANCELLED, None, duration=duration))
            return

        if return_code == 0:
            self.jobFinished.emit(
                JobResult(index, JobStatus.DONE, target, duration=duration)
            )
            return

        if return_code == 6:
            # Datei enthielt bereits Text - kein Fehler, sondern ein Hinweis.
            # Tritt derzeit nicht auf, weil build_arguments() immer einen der
            # Modi --skip-text/--redo-ocr/--force-ocr setzt; die Behandlung
            # bleibt als Absicherung für künftige Änderungen bestehen.
            self.jobFinished.emit(
                JobResult(index, JobStatus.SKIPPED, None, "error.priorOcr", duration=duration)
            )
            return

        _remove_quietly(target)
        self.jobFinished.emit(
            JobResult(
                index,
                JobStatus.FAILED,
                None,
                EXIT_CODE_KEYS.get(return_code, "error.unknown"),
                "\n".join(last_lines[-4:]),
                duration,
            )
        )


def _phase_for(line: str) -> Optional[str]:
    """Ordnet eine Protokollzeile einer Verarbeitungsphase zu."""
    lowered = line.lower()
    if "rasteriz" in lowered or "tesseract" in lowered:
        return "phase.ocr"
    if "hocrparser" in lowered or "grafting" in lowered or "parsing" in lowered:
        return "phase.assemble"
    if "postprocess" in lowered or "pdfa" in lowered or "ghostscript" in lowered:
        return "phase.convert"
    if "optimiz" in lowered:
        return "phase.optimize"
    return None


def _remove_quietly(path: Path) -> None:
    """Löscht eine Datei, ohne bei Fehlern zu stören."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
