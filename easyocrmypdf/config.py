"""Speichern und Laden der Einstellungen im Benutzerprofil.

Bewusst eine schlichte JSON-Datei statt QSettings: sie ist auf allen Systemen
gleich aufgebaut, lässt sich im Zweifel von Hand öffnen und macht ein
Zurücksetzen so einfach wie das Löschen einer Datei.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from easyocrmypdf.models import ExportSettings

CONFIG_FILENAME = "settings.json"
_APP_FOLDER = "EasyOcrMyPdf"
# Bis Version 0.0.2 hieß die Anwendung "OCRmyPDF GUI" und legte ihre Dateien
# unter diesem Namen ab.
_LEGACY_APP_FOLDER = "OCRmyPDF-GUI"


def _config_base() -> Path:
    """Plattformüblicher Elternordner für Einstellungsdateien."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def config_directory() -> Path:
    """Ordner für Einstellungen und nachgeladene Sprachen.

    Existiert nur der Ordner aus der Zeit vor der Umbenennung, wird er
    einmalig umbenannt, damit Einstellungen und Sprachen erhalten bleiben.
    """
    base = _config_base()
    current = base / _APP_FOLDER
    legacy = base / _LEGACY_APP_FOLDER
    if not current.exists() and legacy.is_dir():
        try:
            legacy.rename(current)
        except OSError:
            pass
    return current


def config_path() -> Path:
    """Vollständiger Pfad der Einstellungsdatei."""
    return config_directory() / CONFIG_FILENAME


def load_settings() -> ExportSettings:
    """Lädt die Einstellungen; bei jedem Problem gelten die Standardwerte."""
    path = config_path()
    try:
        raw = path.read_text(encoding="utf-8")
        data: Dict[str, Any] = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return ExportSettings()
    return ExportSettings.from_dict(data)


def save_settings(settings: ExportSettings) -> bool:
    """Schreibt die Einstellungen; ein Fehler darf die Anwendung nicht stören."""
    path = config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Erst in eine Nebendatei schreiben, dann umbenennen: so bleibt bei
        # einem Absturz nie eine halb geschriebene Datei zurück.
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(settings.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(path)
        return True
    except OSError:
        return False


def reset_settings() -> None:
    """Löscht die gespeicherten Einstellungen."""
    try:
        config_path().unlink(missing_ok=True)
    except OSError:
        pass
