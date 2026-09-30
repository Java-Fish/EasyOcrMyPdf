"""Sehr kleine Übersetzungsschicht für Deutsch und Englisch.

Absichtlich ohne Qt-Linguist: eine flache Tabelle ist für den Umfang dieser
Anwendung ausreichend und lässt sich ohne zusätzliche Build-Schritte pflegen.
"""

from __future__ import annotations

import locale
import os
import sys
from typing import Dict

# Unterstützte Sprachen der Oberfläche (nicht zu verwechseln mit OCR-Sprachen).
SUPPORTED_UI_LANGUAGES: Dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
}

DEFAULT_UI_LANGUAGE = "de"

# Tabelle: Schlüssel -> {Sprachcode: Text}. Fehlt ein Schlüssel, wird er
# unverändert ausgegeben, damit die Oberfläche nie leer bleibt.
_STRINGS: Dict[str, Dict[str, str]] = {
    # --- Fenster und Kopfbereich ---------------------------------------
    "app.title": {"de": "OCRmyPDF GUI", "en": "OCRmyPDF GUI"},
    "app.subtitle": {
        "de": "PDFs durchsuchbar machen, ganz ohne Kommandozeile",
        "en": "Make PDFs searchable, no command line needed",
    },
    # --- Ablagebereich --------------------------------------------------
    "drop.title": {"de": "PDF-Dateien hierher ziehen", "en": "Drag PDF files here"},
    "drop.subtitle": {
        "de": "oder klicken, um Dateien auszuwählen",
        "en": "or click to choose files",
    },
    "drop.hint": {"de": "Nur PDF-Dateien", "en": "PDF files only"},
    "drop.active": {"de": "Loslassen zum Hinzufügen", "en": "Release to add"},
    "drop.rejected": {
        "de": "Nur PDF-Dateien werden unterstützt",
        "en": "Only PDF files are supported",
    },
    "drop.dialog.title": {"de": "PDF-Dateien auswählen", "en": "Select PDF files"},
    "drop.dialog.filter": {"de": "PDF-Dateien (*.pdf)", "en": "PDF files (*.pdf)"},
    # --- Dateiliste -----------------------------------------------------
    "list.header": {"de": "Warteschlange", "en": "Queue"},
    "list.empty": {"de": "Noch keine Dateien ausgewählt.", "en": "No files selected yet."},
    "list.count.one": {"de": "1 Datei", "en": "1 file"},
    "list.count.many": {"de": "{count} Dateien", "en": "{count} files"},
    "list.remove": {"de": "Entfernen", "en": "Remove"},
    "list.clear": {"de": "Liste leeren", "en": "Clear list"},
    "list.add": {"de": "Dateien hinzufügen", "en": "Add files"},
    "list.duplicate": {"de": "Bereits in der Liste", "en": "Already in the list"},
    # --- Status pro Datei -----------------------------------------------
    "status.pending": {"de": "Wartet", "en": "Waiting"},
    "status.running": {"de": "Wird verarbeitet", "en": "Processing"},
    "status.done": {"de": "Fertig", "en": "Done"},
    "status.failed": {"de": "Fehlgeschlagen", "en": "Failed"},
    "status.skipped": {"de": "Übersprungen", "en": "Skipped"},
    "status.cancelled": {"de": "Abgebrochen", "en": "Cancelled"},
    # --- Einstellungen: Grundlagen --------------------------------------
    "settings.title": {"de": "Export-Einstellungen", "en": "Export settings"},
    "settings.pdftype": {"de": "PDF-Typ", "en": "PDF type"},
    "settings.pdftype.help": {
        "de": "PDF/A ist für die Langzeitarchivierung gedacht und wird von Behörden häufig verlangt.",
        "en": "PDF/A is meant for long-term archiving and is often required by public authorities.",
    },
    "settings.language": {"de": "Sprache des OCR-Scans", "en": "OCR language"},
    "settings.language.help": {
        "de": "Mehrere Sprachen lassen sich kombinieren, das kostet aber Zeit.",
        "en": "Several languages can be combined, but this costs time.",
    },
    "settings.language.choose": {"de": "Sprachen auswählen ...", "en": "Choose languages ..."},
    "settings.language.none": {"de": "Keine Sprache gewählt", "en": "No language selected"},
    "settings.language.search": {"de": "Sprache suchen", "en": "Search language"},
    "settings.language.selected": {
        "de": "{count} ausgewählt",
        "en": "{count} selected",
    },
    "settings.output": {"de": "Speicherort", "en": "Output folder"},
    "settings.output.browse": {"de": "Ordner wählen ...", "en": "Choose folder ..."},
    "settings.output.dialog": {"de": "Zielordner wählen", "en": "Select target folder"},
    "settings.output.sameAsSource": {
        "de": "Unterordner „OCR“ neben der Originaldatei",
        "en": "Subfolder “OCR” next to the original file",
    },
    "settings.output.custom": {"de": "Fester Ordner", "en": "Fixed folder"},
    "settings.output.open": {"de": "Ordner öffnen", "en": "Open folder"},
    # --- PDF-Typen ------------------------------------------------------
    "pdftype.pdf": {"de": "PDF (Standard)", "en": "PDF (standard)"},
    "pdftype.pdf.desc": {
        "de": "Normale PDF-Datei. Kleinste Dateien, für den täglichen Gebrauch.",
        "en": "Ordinary PDF file. Smallest files, for everyday use.",
    },
    "pdftype.pdfa": {"de": "PDF/A (empfohlen)", "en": "PDF/A (recommended)"},
    "pdftype.pdfa.desc": {
        "de": "Archivformat nach PDF/A-2b. Gute Wahl für Ablage und Behörden.",
        "en": "Archive format based on PDF/A-2b. A good choice for filing and authorities.",
    },
    "pdftype.pdfa-1": {"de": "PDF/A-1b", "en": "PDF/A-1b"},
    "pdftype.pdfa-1.desc": {
        "de": "Ältester Archivstandard. Nur wählen, wenn eine Stelle ihn ausdrücklich verlangt.",
        "en": "Oldest archive standard. Only choose it if an institution explicitly requires it.",
    },
    "pdftype.pdfa-2": {"de": "PDF/A-2b", "en": "PDF/A-2b"},
    "pdftype.pdfa-2.desc": {
        "de": "Archivstandard mit besserer Komprimierung als PDF/A-1b.",
        "en": "Archive standard with better compression than PDF/A-1b.",
    },
    "pdftype.pdfa-3": {"de": "PDF/A-3b", "en": "PDF/A-3b"},
    "pdftype.pdfa-3.desc": {
        "de": "Wie PDF/A-2b, erlaubt zusätzlich eingebettete Dateien (z. B. ZUGFeRD-Rechnungen).",
        "en": "Like PDF/A-2b, but also allows embedded files (e.g. ZUGFeRD invoices).",
    },
    # --- Einstellungen: erweitert ---------------------------------------
    "advanced.title": {"de": "Erweiterte Einstellungen", "en": "Advanced settings"},
    "advanced.show": {"de": "Erweiterte Einstellungen anzeigen", "en": "Show advanced settings"},
    "advanced.mode": {"de": "Wenn bereits Text vorhanden ist", "en": "If text already exists"},
    "advanced.mode.skip": {"de": "Seite überspringen (Standard)", "en": "Skip the page (default)"},
    "advanced.mode.redo": {"de": "Vorhandene Texterkennung erneuern", "en": "Redo existing OCR"},
    "advanced.mode.force": {"de": "Alles neu erkennen (rastert Text)", "en": "Force OCR (rasterises text)"},
    "advanced.mode.help": {
        "de": "„Seite überspringen“ ist für die meisten Dokumente die sicherste Wahl.",
        "en": "“Skip the page” is the safest choice for most documents.",
    },
    "advanced.optimize": {"de": "Dateigröße optimieren", "en": "Optimise file size"},
    "advanced.optimize.0": {"de": "Aus", "en": "Off"},
    "advanced.optimize.1": {
        "de": "Sicher, verlustfrei (Standard)",
        "en": "Safe, lossless (default)",
    },
    "advanced.optimize.2": {"de": "Stark", "en": "Strong"},
    "advanced.optimize.3": {"de": "Maximal (verlustbehaftet)", "en": "Maximum (lossy)"},
    "advanced.optimize.unavailable": {
        "de": "{level} (nicht verfügbar, benötigt {tools})",
        "en": "{level} (not available, requires {tools})",
    },
    "advanced.optimize.hint": {
        "de": "Die stärkeren Stufen benötigen die Zusatzprogramme pngquant und jbig2enc.",
        "en": "The stronger levels require the extra programs pngquant and jbig2enc.",
    },
    "advanced.deskew": {"de": "Schiefe Seiten gerade ziehen", "en": "Straighten skewed pages"},
    "advanced.rotate": {"de": "Seiten automatisch drehen", "en": "Rotate pages automatically"},
    "advanced.clean": {"de": "Bild vor der Erkennung säubern", "en": "Clean image before recognition"},
    "advanced.cleanFinal": {
        "de": "Gesäubertes Bild auch ins Ergebnis übernehmen",
        "en": "Keep the cleaned image in the result",
    },
    "advanced.removeBackground": {"de": "Hintergrund entfernen", "en": "Remove background"},
    "advanced.sidecar": {"de": "Erkannten Text als .txt speichern", "en": "Save recognised text as .txt"},
    "advanced.overwrite": {
        "de": "Vorhandene Dateien überschreiben",
        "en": "Overwrite existing files",
    },
    "advanced.suffix": {"de": "Namenszusatz", "en": "Filename suffix"},
    "advanced.suffix.placeholder": {"de": "z. B. _ocr", "en": "e.g. _ocr"},
    "advanced.jobs": {"de": "Parallele Prozesse je Datei", "en": "Parallel processes per file"},
    "advanced.jobs.auto": {"de": "Automatisch", "en": "Automatic"},
    "advanced.dpi": {"de": "Auflösung für Bilder ohne DPI-Angabe", "en": "Resolution for images without DPI"},
    "advanced.timeout": {"de": "Zeitlimit je Seite (Sekunden)", "en": "Time limit per page (seconds)"},
    "advanced.timeout.none": {"de": "Kein Limit", "en": "No limit"},
    "advanced.uiLanguage": {"de": "Sprache der Oberfläche", "en": "Interface language"},
    "advanced.restartHint": {
        "de": "Die Sprache wird sofort übernommen.",
        "en": "The language is applied immediately.",
    },
    "advanced.reset": {"de": "Auf Standard zurücksetzen", "en": "Reset to defaults"},
    # --- Aktionen -------------------------------------------------------
    "action.start": {"de": "OCR starten", "en": "Start OCR"},
    "action.cancel": {"de": "Abbrechen", "en": "Cancel"},
    "action.openOutput": {"de": "Zielordner öffnen", "en": "Open target folder"},
    "action.ok": {"de": "OK", "en": "OK"},
    "action.close": {"de": "Schließen", "en": "Close"},
    "action.details": {"de": "Details", "en": "Details"},
    "action.retry": {"de": "Erneut prüfen", "en": "Check again"},
    "action.quit": {"de": "Beenden", "en": "Quit"},
    "action.continueAnyway": {"de": "Trotzdem fortfahren", "en": "Continue anyway"},
    "action.copy": {"de": "Kopieren", "en": "Copy"},
    "action.copied": {"de": "Kopiert", "en": "Copied"},
    # --- Fortschritt ----------------------------------------------------
    "progress.idle": {"de": "Bereit", "en": "Ready"},
    "progress.file": {
        "de": "Datei {current} von {total}: {name}",
        "en": "File {current} of {total}: {name}",
    },
    "progress.page": {"de": "Seite {page} von {pages}", "en": "Page {page} of {pages}"},
    "progress.summary": {
        "de": "{done} erfolgreich, {failed} fehlgeschlagen",
        "en": "{done} succeeded, {failed} failed",
    },
    "progress.summary.cancelled": {
        "de": ", {count} abgebrochen",
        "en": ", {count} cancelled",
    },
    "progress.summary.skipped": {
        "de": ", {count} übersprungen",
        "en": ", {count} skipped",
    },
    "progress.finished": {"de": "Verarbeitung abgeschlossen", "en": "Processing finished"},
    "progress.cancelling": {"de": "Wird abgebrochen ...", "en": "Cancelling ..."},
    "log.title": {"de": "Protokoll", "en": "Log"},
    "log.show": {"de": "Protokoll anzeigen", "en": "Show log"},
    "log.save": {"de": "Protokoll speichern", "en": "Save log"},
    "log.showAll": {"de": "Alle Details anzeigen", "en": "Show all details"},
    "log.saveDialog": {"de": "Protokoll speichern", "en": "Save log"},
    "log.savedTo": {"de": "Protokoll gespeichert: {path}", "en": "Log saved: {path}"},
    "progress.elapsed": {"de": "{seconds} s", "en": "{seconds} s"},
    "progress.allDone": {
        "de": "Alle {count} Dateien wurden verarbeitet.",
        "en": "All {count} files have been processed.",
    },
    # --- Sprachen nachladen ---------------------------------------------
    "settings.language.manage": {"de": "Weitere Sprachen laden ...", "en": "Get more languages ..."},
    "download.title": {"de": "Sprachen verwalten", "en": "Manage languages"},
    "download.intro": {
        "de": "Hier lassen sich weitere Sprachen für die Texterkennung herunterladen. "
              "Sie stammen aus dem offiziellen Projekt von Tesseract.",
        "en": "Download additional languages for text recognition here. "
              "They come from the official Tesseract project.",
    },
    "download.variant": {"de": "Modellqualität", "en": "Model quality"},
    "download.variant.fast": {"de": "Schnell (kleine Dateien)", "en": "Fast (small files)"},
    "download.variant.best": {"de": "Genau (große Dateien)", "en": "Accurate (large files)"},
    "download.variant.help": {
        "de": "„Schnell“ genügt für saubere Scans und ist die mitgelieferte Variante. "
              "„Genau“ erkennt schwierige Vorlagen besser, braucht aber mehr Platz und Zeit.",
        "en": "“Fast” is enough for clean scans and is the bundled variant. "
              "“Accurate” handles difficult originals better but needs more space and time.",
    },
    "download.search": {"de": "Sprache suchen", "en": "Search language"},
    "download.state.installed": {"de": "installiert", "en": "installed"},
    "download.action.download": {"de": "Laden", "en": "Get"},
    "download.action.remove": {"de": "Entfernen", "en": "Remove"},
    "download.loading": {"de": "Liste wird geladen ...", "en": "Loading list ..."},
    "download.count": {
        "de": "{installed} von {total} Sprachen installiert",
        "en": "{installed} of {total} languages installed",
    },
    "download.progress": {"de": "{name} wird geladen ...", "en": "Downloading {name} ..."},
    "download.done": {"de": "{name} wurde installiert.", "en": "{name} has been installed."},
    "download.removed": {"de": "{name} wurde entfernt.", "en": "{name} has been removed."},
    "download.removeFailed": {
        "de": "{name} konnte nicht entfernt werden.",
        "en": "{name} could not be removed.",
    },
    "download.lastLanguage": {
        "de": "Die letzte Sprache lässt sich nicht entfernen.",
        "en": "The last language cannot be removed.",
    },
    "download.error.network": {
        "de": "Keine Verbindung zum Server. Prüfen Sie Ihre Internetverbindung.",
        "en": "No connection to the server. Please check your internet connection.",
    },
    "download.error.notFound": {
        "de": "Diese Sprache gibt es in der gewählten Qualität nicht.",
        "en": "This language is not available in the selected quality.",
    },
    "download.error.write": {
        "de": "Die Datei konnte nicht gespeichert werden.",
        "en": "The file could not be saved.",
    },
    "download.error.cancelled": {"de": "Abgebrochen.", "en": "Cancelled."},
    # --- Meldungen ------------------------------------------------------
    "msg.noFiles.title": {"de": "Keine Dateien", "en": "No files"},
    "msg.noFiles.text": {
        "de": "Bitte fügen Sie zuerst mindestens eine PDF-Datei hinzu.",
        "en": "Please add at least one PDF file first.",
    },
    "msg.noLanguage.title": {"de": "Keine Sprache gewählt", "en": "No language selected"},
    "msg.noLanguage.text": {
        "de": "Bitte wählen Sie mindestens eine Sprache für die Texterkennung aus.",
        "en": "Please select at least one language for text recognition.",
    },
    "msg.badOutput.title": {"de": "Speicherort ungültig", "en": "Invalid output folder"},
    "msg.badOutput.text": {
        "de": "Der gewählte Ordner konnte nicht angelegt werden:\n{error}",
        "en": "The selected folder could not be created:\n{error}",
    },
    "msg.busy.title": {"de": "Verarbeitung läuft", "en": "Processing in progress"},
    "msg.busy.text": {
        "de": "Die Texterkennung läuft noch. Möchten Sie sie abbrechen und die Anwendung schließen?",
        "en": "Text recognition is still running. Do you want to cancel it and close the application?",
    },
    "msg.rejected.title": {"de": "Datei nicht unterstützt", "en": "File not supported"},
    "msg.rejected.text": {
        "de": "Diese Dateien wurden ignoriert, weil es keine PDF-Dateien sind:\n{files}",
        "en": "These files were ignored because they are not PDF files:\n{files}",
    },
    # --- Phasen der Verarbeitung ----------------------------------------
    "phase.ocr": {"de": "Text wird erkannt", "en": "Recognising text"},
    "phase.assemble": {"de": "Textebene wird eingefügt", "en": "Adding text layer"},
    "phase.convert": {"de": "PDF wird erzeugt", "en": "Creating PDF"},
    "phase.optimize": {"de": "Datei wird optimiert", "en": "Optimising file"},
    # --- Fehlermeldungen ------------------------------------------------
    "error.badArgs": {
        "de": "Eine Einstellung passt nicht zu dieser Datei. Bitte prüfen Sie die erweiterten Einstellungen.",
        "en": "A setting does not fit this file. Please check the advanced settings.",
    },
    "error.inputFile": {
        "de": "Die Datei konnte nicht gelesen werden. Möglicherweise ist sie beschädigt.",
        "en": "The file could not be read. It may be damaged.",
    },
    "error.missingDependency": {
        "de": "Ein benötigtes Hilfsprogramm fehlt (Tesseract oder Ghostscript).",
        "en": "A required helper program is missing (Tesseract or Ghostscript).",
    },
    "error.outputFile": {
        "de": "Die Zieldatei konnte nicht geschrieben werden. Ist der Ordner beschreibbar?",
        "en": "The target file could not be written. Is the folder writable?",
    },
    "error.invalidPdfa": {
        "de": "Das Ergebnis entspricht nicht dem gewählten PDF/A-Standard. Versuchen Sie den PDF-Typ „PDF (Standard)“.",
        "en": "The result does not match the selected PDF/A standard. Try the PDF type “PDF (standard)”.",
    },
    "error.priorOcr": {
        "de": "Die Datei enthält bereits Text und wurde deshalb übersprungen.",
        "en": "The file already contains text and was therefore skipped.",
    },
    "error.childProcess": {
        "de": "Tesseract oder Ghostscript wurde unerwartet beendet.",
        "en": "Tesseract or Ghostscript stopped unexpectedly.",
    },
    "error.encrypted": {
        "de": "Die PDF-Datei ist passwortgeschützt und kann nicht verarbeitet werden.",
        "en": "The PDF file is password protected and cannot be processed.",
    },
    "error.invalidConfig": {
        "de": "Die gewählte Kombination aus Einstellungen ist nicht zulässig.",
        "en": "The selected combination of settings is not allowed.",
    },
    "error.pdfaConversion": {
        "de": "Die Umwandlung nach PDF/A ist fehlgeschlagen. Versuchen Sie den PDF-Typ „PDF (Standard)“.",
        "en": "Conversion to PDF/A failed. Try the PDF type “PDF (standard)”.",
    },
    "error.other": {
        "de": "Bei der Verarbeitung ist ein Fehler aufgetreten.",
        "en": "An error occurred during processing.",
    },
    "error.unknown": {
        "de": "Unbekannter Fehler. Einzelheiten stehen im Protokoll.",
        "en": "Unknown error. Details are in the log.",
    },
    "error.noOcrmypdf": {
        "de": "OCRmyPDF wurde nicht gefunden.",
        "en": "OCRmyPDF was not found.",
    },
    "error.inputMissing": {
        "de": "Die Datei existiert nicht mehr.",
        "en": "The file no longer exists.",
    },
    "error.outputFolder": {
        "de": "Der Zielordner konnte nicht angelegt werden.",
        "en": "The target folder could not be created.",
    },
    "error.launch": {
        "de": "Die Verarbeitung konnte nicht gestartet werden.",
        "en": "Processing could not be started.",
    },
    # --- Einrichtungsdialog ---------------------------------------------
    "setup.title": {"de": "Einrichtung", "en": "Setup"},
    "setup.intro": {
        "de": "OCRmyPDF GUI benötigt zwei Hilfsprogramme. Es fehlt noch etwas:",
        "en": "OCRmyPDF GUI needs two helper programs. Something is still missing:",
    },
    "setup.allGood": {"de": "Alles bereit.", "en": "Everything is ready."},
    "setup.found": {"de": "gefunden", "en": "found"},
    "setup.missing": {"de": "fehlt", "en": "missing"},
    "setup.tesseract.desc": {
        "de": "Tesseract erkennt den Text in Ihren Scans.",
        "en": "Tesseract recognises the text in your scans.",
    },
    "setup.ghostscript.desc": {
        "de": "Ghostscript erzeugt die fertige PDF- bzw. PDF/A-Datei.",
        "en": "Ghostscript creates the finished PDF or PDF/A file.",
    },
    "setup.ocrmypdf.desc": {
        "de": "OCRmyPDF steuert den gesamten Ablauf.",
        "en": "OCRmyPDF orchestrates the whole process.",
    },
    "setup.instructions": {"de": "So installieren Sie es:", "en": "How to install it:"},
    "setup.download": {"de": "Download-Seite öffnen", "en": "Open download page"},
    "setup.note": {
        "de": "Nach der Installation auf „Erneut prüfen“ klicken.",
        "en": "After installing, click “Check again”.",
    },
}


class Translator:
    """Hält die aktive Sprache und liefert übersetzte Texte."""

    def __init__(self, language: str = DEFAULT_UI_LANGUAGE) -> None:
        self._language = DEFAULT_UI_LANGUAGE
        self.set_language(language)

    @property
    def language(self) -> str:
        """Der aktive Sprachcode der Oberfläche."""
        return self._language

    def set_language(self, language: str) -> None:
        """Setzt die Sprache; unbekannte Codes fallen auf die Standardsprache zurück."""
        self._language = language if language in SUPPORTED_UI_LANGUAGES else DEFAULT_UI_LANGUAGE

    def __call__(self, key: str, **kwargs: object) -> str:
        return self.translate(key, **kwargs)

    def translate(self, key: str, **kwargs: object) -> str:
        """Liefert den Text zum Schlüssel, bei Bedarf mit eingesetzten Werten."""
        entry = _STRINGS.get(key)
        if entry is None:
            # Unbekannter Schlüssel: den Schlüssel selbst zeigen, damit der
            # Fehler auffällt, die Oberfläche aber weiter benutzbar bleibt.
            return key
        text = entry.get(self._language) or entry.get(DEFAULT_UI_LANGUAGE) or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text


def detect_system_language() -> str:
    """Ermittelt die Sprache des Betriebssystems, sonst Deutsch."""
    candidates: list[str] = []
    try:
        current = locale.getlocale()[0]
    except (ValueError, TypeError):
        current = None
    if current:
        candidates.append(current)
    # Umgebungsvariablen als Rückfallebene (unter macOS/Linux üblich).
    for name in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(name)
        if value:
            candidates.append(value)
    if sys.platform == "win32":
        candidates.append(_windows_ui_language())
    for candidate in candidates:
        if not candidate:
            continue
        prefix = candidate.replace("-", "_").split("_", 1)[0].split(".", 1)[0].lower()
        if prefix in SUPPORTED_UI_LANGUAGES:
            return prefix
    return DEFAULT_UI_LANGUAGE


def _windows_ui_language() -> str:
    """Fragt unter Windows die Anzeigesprache ab (dort sind LANG-Variablen leer)."""
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, 85):  # type: ignore[attr-defined]
            return buffer.value
    except Exception:  # pragma: no cover - rein defensiv
        pass
    return ""


# Globale Instanz: die gesamte Oberfläche verwendet dieses eine Objekt.
tr = Translator(detect_system_language())
