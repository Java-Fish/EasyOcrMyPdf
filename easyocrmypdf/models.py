"""Datenmodelle: Export-Einstellungen, Aufträge und deren Zustände."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Name des Unterordners, der neben der Originaldatei angelegt wird.
DEFAULT_SUBFOLDER_NAME = "OCR"

# Zulässige Bereiche der Zahlenwerte. Sie stehen hier und nur hier, damit
# Oberfläche und Einlesen der Einstellungsdatei dieselben Grenzen verwenden;
# vorher wichen sie voneinander ab.
OPTIMIZE_LEVEL_RANGE = (0, 3)
JOBS_RANGE = (0, 64)            # mehr Prozesse als Kerne bringen nichts
IMAGE_DPI_RANGE = (0, 2400)     # darüber wird die Erkennung nicht besser
PAGE_TIMEOUT_RANGE = (0, 3600)  # eine Stunde je Seite ist reichlich bemessen

# Längste zulässige Ergänzung am Dateinamen.
MAX_SUFFIX_LENGTH = 32

# Obergrenze für einen Dateinamen. Praktisch alle gängigen Dateisysteme
# (APFS, HFS+, NTFS, ext4) erlauben 255 Bytes je Namensbestandteil.
MAX_FILENAME_BYTES = 255

# Voreingestellte Optimierungsstufe. Stufe 1 komprimiert verlustfrei und
# kommt ohne Zusatzprogramme aus. Dient zugleich als Ersatzwert, wenn eine
# gewählte Stufe mangels pngquant oder jbig2enc nicht nutzbar ist.
DEFAULT_OPTIMIZE_LEVEL = 1


class PdfType(Enum):
    """Ausgabeformat - entspricht ``ocrmypdf --output-type``."""

    PDF = "pdf"
    PDFA = "pdfa"
    PDFA_1 = "pdfa-1"
    PDFA_2 = "pdfa-2"
    PDFA_3 = "pdfa-3"

    @property
    def label_key(self) -> str:
        """Schlüssel der Beschriftung in der Sprachtabelle."""
        return f"pdftype.{self.value}"

    @property
    def description_key(self) -> str:
        """Schlüssel der Erläuterung in der Sprachtabelle."""
        return f"pdftype.{self.value}.desc"


class OcrMode(Enum):
    """Verhalten, wenn eine Seite bereits Text enthält."""

    SKIP_TEXT = "skip-text"
    REDO_OCR = "redo-ocr"
    FORCE_OCR = "force-ocr"

    @property
    def argument(self) -> str:
        """Der zugehörige Schalter für die Kommandozeile von OCRmyPDF."""
        return f"--{self.value}"


class OutputMode(Enum):
    """Wohin die fertigen Dateien geschrieben werden."""

    SUBFOLDER = "subfolder"  # Unterordner neben der Originaldatei
    FIXED = "fixed"  # ein fest gewählter Zielordner


class JobStatus(Enum):
    """Zustand eines einzelnen Auftrags in der Warteschlange."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

    @property
    def label_key(self) -> str:
        """Schlüssel der Beschriftung in der Sprachtabelle."""
        return f"status.{self.value}"


@dataclass
class ExportSettings:
    """Alle vom Nutzer einstellbaren Optionen eines Exports."""

    # --- Grundeinstellungen ---
    pdf_type: PdfType = PdfType.PDFA
    languages: List[str] = field(default_factory=lambda: ["deu"])
    output_mode: OutputMode = OutputMode.SUBFOLDER
    output_folder: Optional[str] = None

    # --- Erweiterte Einstellungen ---
    ocr_mode: OcrMode = OcrMode.SKIP_TEXT
    optimize_level: int = DEFAULT_OPTIMIZE_LEVEL
    deskew: bool = False
    rotate_pages: bool = False
    clean: bool = False
    clean_final: bool = False
    remove_background: bool = False
    sidecar_text: bool = False
    overwrite_existing: bool = False
    filename_suffix: str = "_ocr"
    jobs: int = 0  # 0 bedeutet: OCRmyPDF entscheidet selbst
    image_dpi: int = 0  # 0 bedeutet: keine Vorgabe
    page_timeout: int = 0  # 0 bedeutet: kein Zeitlimit
    ui_language: str = "de"

    # ------------------------------------------------------------------
    # Serialisierung
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Wandelt die Einstellungen in einfache JSON-taugliche Typen um."""
        data: Dict[str, Any] = {}
        for key, value in self.__dict__.items():
            data[key] = value.value if isinstance(value, Enum) else value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExportSettings":
        """Liest Einstellungen ein und ignoriert unbekannte oder kaputte Werte."""
        settings = cls()
        if not isinstance(data, dict):
            return settings

        def enum_value(enum_cls, raw, fallback):
            try:
                return enum_cls(raw)
            except ValueError:
                return fallback

        settings.pdf_type = enum_value(PdfType, data.get("pdf_type"), settings.pdf_type)
        settings.ocr_mode = enum_value(OcrMode, data.get("ocr_mode"), settings.ocr_mode)
        settings.output_mode = enum_value(
            OutputMode, data.get("output_mode"), settings.output_mode
        )

        languages = data.get("languages")
        if isinstance(languages, list):
            cleaned = [str(code) for code in languages if isinstance(code, str) and code]
            if cleaned:
                settings.languages = cleaned

        folder = data.get("output_folder")
        settings.output_folder = str(folder) if isinstance(folder, str) and folder else None

        for key in (
            "deskew",
            "rotate_pages",
            "clean",
            "clean_final",
            "remove_background",
            "sidecar_text",
            "overwrite_existing",
        ):
            if isinstance(data.get(key), bool):
                setattr(settings, key, data[key])

        for key, (minimum, maximum) in (
            ("optimize_level", OPTIMIZE_LEVEL_RANGE),
            ("jobs", JOBS_RANGE),
            ("image_dpi", IMAGE_DPI_RANGE),
            ("page_timeout", PAGE_TIMEOUT_RANGE),
        ):
            raw = data.get(key)
            if isinstance(raw, int) and not isinstance(raw, bool):
                setattr(settings, key, max(minimum, min(maximum, raw)))

        suffix = data.get("filename_suffix")
        if isinstance(suffix, str):
            settings.filename_suffix = sanitize_suffix(suffix)

        ui_language = data.get("ui_language")
        if isinstance(ui_language, str) and ui_language:
            settings.ui_language = ui_language

        return settings

    def copy(self) -> "ExportSettings":
        """Flache Kopie mit eigener Sprachliste."""
        return replace(self, languages=list(self.languages))

    # ------------------------------------------------------------------
    # Ableitungen
    # ------------------------------------------------------------------
    @property
    def language_argument(self) -> str:
        """Sprachen im Tesseract-Format, z. B. ``deu+eng``."""
        return "+".join(self.languages)

    def target_folder_for(self, source: Path) -> Path:
        """Zielordner für eine konkrete Quelldatei."""
        if self.output_mode is OutputMode.FIXED and self.output_folder:
            return Path(self.output_folder).expanduser()
        return source.parent / DEFAULT_SUBFOLDER_NAME

    def target_path_for(self, source: Path) -> Path:
        """Vollständiger Zielpfad inklusive Namenszusatz.

        Überschreiben ist abgeschaltet und die Datei existiert schon? Dann wird
        eine Nummer angehängt, damit nie unbemerkt etwas verloren geht.
        """
        folder = self.target_folder_for(source)
        suffix = sanitize_suffix(self.filename_suffix)
        # Platz für eine angehängte Nummer freihalten, falls nicht überschrieben
        # wird und der Name bereits vergeben ist.
        reserved = 0 if self.overwrite_existing else len(" (99)")
        stem = limit_filename(source.stem + suffix, reserved)
        candidate = folder / f"{stem}.pdf"

        # Quelle und Ziel dürfen niemals identisch sein - OCRmyPDF lehnt das ab.
        if _same_file(candidate, source):
            stem = limit_filename(f"{source.stem}{suffix or '_ocr'}", reserved)
            candidate = folder / f"{stem}.pdf"
            if _same_file(candidate, source):
                stem = limit_filename(f"{source.stem}_ocr", reserved)
                candidate = folder / f"{stem}.pdf"

        if self.overwrite_existing:
            return candidate

        counter = 2
        while candidate.exists():
            candidate = folder / f"{stem} ({counter}).pdf"
            counter += 1
        return candidate

    def build_arguments(self, source: Path, target: Path) -> List[str]:
        """Baut die Kommandozeilenargumente für OCRmyPDF zusammen."""
        args: List[str] = [
            "--output-type",
            self.pdf_type.value,
        ]
        if self.languages:
            args += ["-l", self.language_argument]

        args.append(self.ocr_mode.argument)
        args += ["--optimize", str(self.optimize_level)]

        if self.deskew:
            args.append("--deskew")
        if self.rotate_pages:
            args.append("--rotate-pages")
        if self.clean:
            args.append("--clean")
        if self.clean_final:
            # --clean-final schließt --clean mit ein; beides zu senden ist ein Fehler.
            if self.clean:
                args.remove("--clean")
            args.append("--clean-final")
        if self.remove_background:
            args.append("--remove-background")
        if self.jobs > 0:
            args += ["--jobs", str(self.jobs)]
        if self.image_dpi > 0:
            args += ["--image-dpi", str(self.image_dpi)]
        if self.page_timeout > 0:
            args += ["--tesseract-timeout", str(self.page_timeout)]
        if self.sidecar_text:
            args += ["--sidecar", str(target.with_suffix(".txt"))]

        # Fortschrittsbalken abschalten: die Ausgabe wird von uns geparst.
        args.append("--no-progress-bar")
        args += [str(source), str(target)]
        return args


def limit_filename(stem: str, reserved: int = 0, extension: str = ".pdf") -> str:
    """Kürzt den Namensstamm, damit der Dateiname ins Dateisystem passt.

    Ohne diese Begrenzung scheitert das Schreiben bei sehr langen Namen mit
    "File name too long" - einer Meldung, die dem Nutzer nichts sagt und wie
    ein Rechteproblem aussieht. Gekürzt wird byteweise, ohne ein
    Mehrbyte-Zeichen zu zerschneiden.
    """
    budget = MAX_FILENAME_BYTES - len(extension.encode("utf-8")) - reserved
    raw = stem.encode("utf-8")
    if len(raw) <= budget:
        return stem
    if budget <= 0:
        return stem[:1]
    # errors="ignore" verwirft ein am Ende angeschnittenes Zeichen.
    gekuerzt = raw[:budget].decode("utf-8", errors="ignore").rstrip()
    return gekuerzt or stem[:1]


def sanitize_suffix(suffix: str) -> str:
    """Entfernt Zeichen, die in Dateinamen Probleme machen."""
    forbidden = set('\\/:*?"<>|')
    cleaned = "".join(char for char in suffix if char not in forbidden)
    return cleaned.strip()[:MAX_SUFFIX_LENGTH]


def _same_file(first: Path, second: Path) -> bool:
    """Vergleicht zwei Pfade tolerant gegenüber Symlinks und Groß-/Kleinschreibung."""
    try:
        if first.exists() and second.exists():
            return os.path.samefile(first, second)
    except OSError:
        pass
    return os.path.normcase(str(first.absolute())) == os.path.normcase(str(second.absolute()))


@dataclass
class Job:
    """Ein einzelner Auftrag: eine Quelldatei und ihr Ergebnis."""

    source: Path
    status: JobStatus = JobStatus.PENDING
    target: Optional[Path] = None
    message: str = ""
    page_count: int = 0
    current_page: int = 0

    @property
    def name(self) -> str:
        """Der Dateiname ohne Pfad."""
        return self.source.name

    def reset(self) -> None:
        """Setzt den Auftrag für einen erneuten Durchlauf zurück."""
        self.status = JobStatus.PENDING
        self.target = None
        self.message = ""
        self.current_page = 0
